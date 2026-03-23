#uvicorn main:app --reload
from sqlalchemy.orm import Session
from fastapi import Depends
from app.core.database import get_db
from app.models.camera import Camera as DBCamera
from app.schemas.camera_schema import CameraCreate, CameraResponse
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import json
import base64
import uuid
from datetime import datetime
import cv2
import threading
import time

# 引入你的原有模块 (如果不用数据库可暂时注释前两行)
from app.api.router import api_router
from app.core.database import engine, Base
from app.services.llm_client import SecurityVLMClient

Base.metadata.create_all(bind=engine)
app = FastAPI(title="AI Security Monitor API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")
llm_client = SecurityVLMClient()

# ==========================================
# 1. 支持“热插拔”的视频流引擎
# ==========================================
class StreamManager:
    def __init__(self):
        self.frames = {}       # 存放最新帧 { id: bytes }
        self.threads = {}      # 存放线程对象 { id: Thread }
        self.running = {}      # 线程运行标志 { id: bool } 控制停止

    def start_camera(self, cam_id: int, name: str, url: str):
        """动态启动一个摄像头的拉流线程"""
        if cam_id in self.running and self.running[cam_id]:
            self.stop_camera(cam_id) # 如果已存在，先停止
            
        self.running[cam_id] = True
        t = threading.Thread(target=self._capture_loop, args=(cam_id, name, url), daemon=True)
        self.threads[cam_id] = t
        t.start()
        print(f"✅ [StreamManager] 已启动摄像头: {name}")

    def stop_camera(self, cam_id: int):
        """动态停止一个摄像头的拉流线程并清理内存"""
        if cam_id in self.running:
            self.running[cam_id] = False # 通知线程内部退出循环
        if cam_id in self.frames:
            del self.frames[cam_id]
        print(f"🛑 [StreamManager] 已停止摄像头 ID: {cam_id}")

    def _capture_loop(self, cam_id, name, url):
        while self.running.get(cam_id, False):
            cap = cv2.VideoCapture(url)
            if not cap.isOpened():
                time.sleep(3)
                continue
            
            # 核心：每次读帧前检查 running 标志，如果为False立即跳出销毁
            while cap.isOpened() and self.running.get(cam_id, False):
                ret, frame = cap.read()
                if ret:
                    ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                    self.frames[cam_id] = buffer.tobytes()
                    if url.endswith('.mp4'): time.sleep(0.03)
                else:
                    break 
            cap.release()
            
            if self.running.get(cam_id, False):
                time.sleep(2) # 仅在非主动停止时尝试重连

stream_manager = StreamManager()

# ==========================================
# 2. WebSocket 与 AI 后台分析
# ==========================================
class ConnectionManager:
    def __init__(self): self.active_connections = []
    async def connect(self, ws: WebSocket): await ws.accept(); self.active_connections.append(ws)
    def disconnect(self, ws: WebSocket): self.active_connections.remove(ws) if ws in self.active_connections else None
    async def broadcast(self, msg: str):
        for ws in self.active_connections:
            try: await ws.send_text(msg)
            except: pass

manager = ConnectionManager()

@app.websocket("/ws/alerts")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True: await websocket.receive_text()
    except WebSocketDisconnect: manager.disconnect(websocket)

async def ai_analysis_task():
    """后台任务：根据每个摄像头的抽帧时间独立进行分析"""
    while True:
        await asyncio.sleep(1) # 每秒醒来一次，检查谁该抽帧了
        
        # 为了不频繁查库，我们可以每次通过独立的 Session 查询配置
        db = next(get_db())
        cameras = db.query(DBCamera).filter(DBCamera.is_active == True).all()
        current_time = int(time.time())
        
        for cam in cameras:
            # 只有当当前时间是 capture_interval 的整数倍时才执行抽帧
            if current_time % cam.capture_interval == 0:
                frame_bytes = stream_manager.frames.get(cam.id)
                if not frame_bytes: 
                    continue
                
                loop = asyncio.get_event_loop()
                try:
                    result = await loop.run_in_executor(None, llm_client.analyze_frame, frame_bytes, cam.name)
                    if result and result.get("has_issue"):
                        base64_img = f"data:image/jpeg;base64,{base64.b64encode(frame_bytes).decode('utf-8')}"
                        for issue in result.get("alerts", []):
                            await manager.broadcast(json.dumps({
                                "type": "alert",
                                "alert": {
                                    "id": str(uuid.uuid4())[:8], "time": datetime.now().strftime("%H:%M:%S"),
                                    "camera": cam.name, "type": issue.get("issue_type", "安全隐患"),
                                    "desc": issue.get("issue_description", ""), "img": base64_img
                                }
                            }))
                except Exception as e: 
                    print(f"[{cam.name}] 分析错误: {e}")
        db.close()


@app.on_event("startup")
async def startup_event():
    # 启动时，从真实的 MySQL 数据库读取所有激活的摄像头并开始拉流！
    db = next(get_db())
    cameras = db.query(DBCamera).filter(DBCamera.is_active == True).all()
    for cam in cameras:
        stream_manager.start_camera(cam.id, cam.name, cam.stream_url)
    db.close()
    
    asyncio.create_task(ai_analysis_task())

# 查询列表 (对接数据库)
@app.get("/api/config/cameras", response_model=list[CameraResponse])
async def get_cameras(db: Session = Depends(get_db)):
    return db.query(DBCamera).all()

# 新增摄像头 (对接数据库)
@app.post("/api/config/cameras", response_model=CameraResponse)
async def add_camera(cam: CameraCreate, db: Session = Depends(get_db)):
    db_cam = DBCamera(**cam.model_dump())
    db.add(db_cam)
    db.commit()
    db.refresh(db_cam)
    
    # 热更新：启动推流
    if db_cam.is_active:
        stream_manager.start_camera(db_cam.id, db_cam.name, db_cam.stream_url)
    return db_cam

# 删除摄像头 (对接数据库)
@app.delete("/api/config/cameras/{cam_id}")
async def delete_camera(cam_id: int, db: Session = Depends(get_db)):
    db_cam = db.query(DBCamera).filter(DBCamera.id == cam_id).first()
    if not db_cam: raise HTTPException(status_code=404, detail="摄像头不存在")
    
    db.delete(db_cam)
    db.commit()
    
    # 热更新：停止推流
    stream_manager.stop_camera(cam_id)
    return {"status": "success"}

# 视频推流接口 (保持不变)
@app.get("/api/video_feed/{cam_id}")
async def video_feed(cam_id: int):
    def generate():
        while True:
            # 如果中途被删除了，退出推流
            if not stream_manager.running.get(cam_id, False): break
            frame = stream_manager.frames.get(cam_id)
            if frame:
                yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(0.04)
    return StreamingResponse(generate(), media_type="multipart/x-mixed-replace; boundary=frame")