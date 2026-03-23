#uvicorn main:app --reload
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
# 0. 模拟数据库表 (供动态增删改查)
# ==========================================
# 这里默认内置4个测试流，后续前端的所有增删改都在这个字典上操作
DB_CAMERAS = {
    1: {"id": 1, "name": "Cam-01 南门主干道", "url": "rtsp://admin:password@192.168.1.100:554/Streaming/Channels/101"},
    2: {"id": 2, "name": "Cam-02 生产车间A区", "url": "rtsp://admin:password@192.168.1.101:554/Streaming/Channels/101"},
    3: {"id": 3, "name": "Cam-03 西门入口", "url": "rtsp://admin:password@192.168.1.102:554/Streaming/Channels/101"},
    4: {"id": 4, "name": "Cam-04 办公区走廊", "url": "rtsp://admin:password@192.168.1.103:554/Streaming/Channels/101"}
}
NEXT_CAM_ID = 5

# Pydantic 模型用于接收前端表单数据
class CameraCreate(BaseModel):
    name: str
    url: str

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
    while True:
        await asyncio.sleep(4) 
        # 遍历所有当前正在运行的摄像头
        for cam_id, frame_bytes in list(stream_manager.frames.items()):
            if not frame_bytes: continue
            cam_info = DB_CAMERAS.get(cam_id)
            if not cam_info: continue
            
            loop = asyncio.get_event_loop()
            try:
                result = await loop.run_in_executor(None, llm_client.analyze_frame, frame_bytes, cam_info["name"])
                if result and result.get("has_issue"):
                    base64_img = f"data:image/jpeg;base64,{base64.b64encode(frame_bytes).decode('utf-8')}"
                    for issue in result.get("alerts", []):
                        await manager.broadcast(json.dumps({
                            "type": "alert",
                            "alert": {
                                "id": str(uuid.uuid4())[:8], "time": datetime.now().strftime("%H:%M:%S"),
                                "camera": cam_info["name"], "type": issue.get("issue_type", "安全隐患"),
                                "desc": issue.get("issue_description", ""), "img": base64_img
                            }
                        }))
            except Exception: pass

# ==========================================
# 3. 核心 API：真正的增删改查
# ==========================================
@app.on_event("startup")
async def startup_event():
    # 启动数据库中所有的摄像头
    for cam_id, cam in DB_CAMERAS.items():
        stream_manager.start_camera(cam_id, cam["name"], cam["url"])
    asyncio.create_task(ai_analysis_task())

# 查询列表
@app.get("/api/config/cameras")
async def get_cameras():
    return list(DB_CAMERAS.values())

# 新增摄像头
@app.post("/api/config/cameras")
async def add_camera(cam: CameraCreate):
    global NEXT_CAM_ID
    cam_id = NEXT_CAM_ID
    NEXT_CAM_ID += 1
    DB_CAMERAS[cam_id] = {"id": cam_id, "name": cam.name, "url": cam.url}
    # 热更新：立即启动流！
    stream_manager.start_camera(cam_id, cam.name, cam.url)
    return {"status": "success", "data": DB_CAMERAS[cam_id]}

# 修改摄像头
@app.put("/api/config/cameras/{cam_id}")
async def update_camera(cam_id: int, cam: CameraCreate):
    if cam_id not in DB_CAMERAS: raise HTTPException(status_code=404, detail="摄像头不存在")
    DB_CAMERAS[cam_id]["name"] = cam.name
    DB_CAMERAS[cam_id]["url"] = cam.url
    # 热更新：重启该流！
    stream_manager.start_camera(cam_id, cam.name, cam.url)
    return {"status": "success"}

# 删除摄像头
@app.delete("/api/config/cameras/{cam_id}")
async def delete_camera(cam_id: int):
    if cam_id not in DB_CAMERAS: raise HTTPException(status_code=404, detail="摄像头不存在")
    del DB_CAMERAS[cam_id]
    # 热更新：立即关闭底层的 cv2 线程！
    stream_manager.stop_camera(cam_id)
    return {"status": "success"}

# 视频推流接口 (现在使用 ID 查找)
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