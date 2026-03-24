#uvicorn main:app --reload --host 0.0.0.0 --port 8000
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
import os
from fastapi.staticfiles import StaticFiles
from app.models.alert import Alert
from app.api.router import api_router
from app.core.database import engine, Base
from app.services.llm_client import SecurityVLMClient
from sqlalchemy import desc
from app.models.alert import Alert
from sqlalchemy import desc

Base.metadata.create_all(bind=engine)
app = FastAPI(title="AI Security Monitor API")

UPLOAD_DIR = "static/alerts"
# 如果文件夹不存在，系统会自动在 backend-fastapi 目录下创建它
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 挂载静态目录：前端如果访问 http://.../static/alerts/xxx.jpg，就会直接读取本地硬盘的这个文件夹
app.mount("/static", StaticFiles(directory="static"), name="static")

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
    def __init__(self): 
        self.active_connections = []
        
    async def connect(self, ws: WebSocket): 
        await ws.accept()
        self.active_connections.append(ws)
        print(f"🔗 [WebSocket] 新前端已连接！当前总连接数: {len(self.active_connections)}")
        
    def disconnect(self, ws: WebSocket): 
        if ws in self.active_connections:
            self.active_connections.remove(ws)
            print(f"❌ [WebSocket] 前端已断开！当前总连接数: {len(self.active_connections)}")
            
    async def broadcast(self, msg: str):
        if not self.active_connections:
            print("⚠️ [WebSocket] 当前没有任何前端连接，告警消息被丢弃！(请刷新浏览器页面)")
            return
            
        for ws in self.active_connections:
            try: 
                await ws.send_text(msg)
            except Exception as e: 
                # 之前这里是 pass，导致报错了你也看不见
                print(f"🔥 [WebSocket] 消息发送失败: {e}")

manager = ConnectionManager()

@app.websocket("/ws/alerts")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True: await websocket.receive_text()
    except WebSocketDisconnect: manager.disconnect(websocket)


# 【新增】将单次大模型调用抽离成一个独立的异步函数
async def process_single_frame(cam_name: str, frame_bytes: bytes):
    """处理单个摄像头单帧图像的独立任务，不阻塞主循环"""
    loop = asyncio.get_event_loop()
    try:
        # 1. 调用大模型
        result = await loop.run_in_executor(None, llm_client.analyze_frame, frame_bytes, cam_name)
        
        if result and result.get("has_issue"):
            print(f"🚨 [{cam_name}] 检测到异常，正在保存图片并写入数据库...")
            
            # ========================================
            # 【核心1】将图片字节流直接写入本地硬盘
            # ========================================
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:6]
            # 生成文件名，例如: 副塔楼作业面监控_20260323_165600_a1b2c3.jpg
            img_filename = f"{cam_name}_{timestamp}_{unique_id}.jpg"
            img_filepath = os.path.join(UPLOAD_DIR, img_filename)
            
            # 以二进制写入模式(wb)保存到本地
            with open(img_filepath, "wb") as f:
                f.write(frame_bytes)
                
            # 供数据库和前端读取的相对路径 URL
            saved_image_url = f"/static/alerts/{img_filename}"

            # ========================================
            # 【核心2】将告警数据存入 MySQL 数据库
            # ========================================
            db = next(get_db())
            try:
                for issue in result.get("alerts", []):
                    # 把字典格式的坐标转成 JSON 字符串存入数据库
                    boxes_json = json.dumps([issue.get("box")] if issue.get("box") else [])
                    
                    new_alert = Alert(
                        camera_name=cam_name,
                        issue_type=issue.get("issue_type", "安全隐患"),
                        issue_description=issue.get("issue_description", ""),
                        scene_description=scene_desc,
                        image_url=saved_image_url,
                        boxes=boxes_json
                    )
                    db.add(new_alert)
                db.commit() # 提交到数据库
                print(f"💾 [{cam_name}] 数据已成功持久化到 MySQL！")
            except Exception as db_err:
                db.rollback()
                print(f"❌ 数据库写入失败: {db_err}")
            finally:
                db.close()

            # ========================================
            # 【核心3】仍然通过 WebSocket 实时推送给前端
            # ========================================
            base64_img = f"data:image/jpeg;base64,{base64.b64encode(frame_bytes).decode('utf-8')}"
            for issue in result.get("alerts", []):
                msg = json.dumps({
                    "type": "alert",
                    "alert": {
                        "id": str(uuid.uuid4())[:8], 
                        "time": datetime.now().strftime("%H:%M:%S"),
                        "camera": cam_name, 
                        "type": issue.get("issue_type", "安全隐患"),
                        "desc": issue.get("issue_description", ""), 
                        "img": base64_img, # 实时推送仍然用 base64 最快，历史查询用 URL
                        "boxes": [issue.get("box")] if issue.get("box") else []
                    }
                })
                await manager.broadcast(msg)

    except Exception as e: 
        print(f"❌ [{cam_name}] 任务执行错误: {e}")


# 【修改】重写后台定时任务逻辑
async def ai_analysis_task():
    """后台任务：根据每个摄像头的抽帧时间独立进行分析"""
    last_analysis_time = {}  # 记录每个摄像头【上一次发起分析】的时间戳
    
    while True:
        await asyncio.sleep(1) # 每秒醒来一次，检查谁该抽帧了
        
        db = next(get_db())
        cameras = db.query(DBCamera).filter(DBCamera.is_active == True).all()
        current_time = time.time() # 使用带小数的时间戳更精准
        
        for cam in cameras:
            # 初始化该摄像头的最后分析时间
            if cam.id not in last_analysis_time:
                last_analysis_time[cam.id] = 0
                
            # 【核心修复1】使用时间差计算，不再使用取模，完美解决时间跳过导致漏帧的问题
            if current_time - last_analysis_time[cam.id] >= cam.capture_interval:
                frame_bytes = stream_manager.frames.get(cam.id)
                if not frame_bytes: 
                    continue
                
                # 更新最后分析时间 (准备进入下一个周期)
                last_analysis_time[cam.id] = current_time
                
                # 【核心修复2】使用 create_task 甩到后台执行！
                # 主循环不会在这里等待大模型返回，而是立刻去检查下一个摄像头
                asyncio.create_task(process_single_frame(cam.name, frame_bytes))
                
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

@app.on_event("shutdown")
async def shutdown_event():
    print("🛑 收到退出信号，正在强制清理后台任务和视频流...")
    
    # 将所有正在运行的摄像头标志位设为 False，打断 cv2 的死循环
    cam_ids = list(stream_manager.running.keys())
    for cam_id in cam_ids:
        stream_manager.stop_camera(cam_id)
        
    print("✅ 视频流释放指令已发送，准备退出。")

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

#历史数据查询接口
@app.get("/api/alerts/history")
async def get_alerts_history(limit: int = 50, db: Session = Depends(get_db)):
    """获取历史告警记录给前端大屏展示"""
    # 查询最近的 limit 条记录，按时间倒序排列 (最新的在最前面)
    records = db.query(Alert).order_by(desc(Alert.created_at)).limit(limit).all()
    
    result = []
    for record in records:
        try:
            # 尝试将数据库里存的 JSON 字符串转回数组
            boxes_data = json.loads(record.boxes) if record.boxes else []
        except:
            boxes_data = []
            
        result.append({
            "id": record.id,
            "time": record.created_at.strftime("%H:%M:%S"),
            "date": record.created_at.strftime("%Y-%m-%d"),
            "camera": record.camera_name,
            "type": record.issue_type,
            "desc": record.issue_description,
            # 图片路径是 /static/...，前端拿着这个路径加上域名就能访问图片
            "img": record.image_url, 
            "boxes": boxes_data
        })
    return result

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

#详情弹窗
@app.get("/api/alerts/history")
async def get_alert_history(limit: int = 50, db: Session = Depends(get_db)):
    """
    获取历史告警记录给前端大屏和详情页展示
    """
    try:
        # 按 ID 倒序查询最新的告警记录
        alerts = db.query(Alert).order_by(desc(Alert.id)).limit(limit).all()
        
        result = []
        for a in alerts:
            # 1. 尝试解析数据库中存储的 JSON 格式 bbox 坐标框
            try:
                parsed_boxes = json.loads(a.boxes) if a.boxes else []
            except Exception:
                parsed_boxes = []
                
            # 2. 尝试提取时间（适配你 models/alert.py 里的字段名）
            # 假设你的 Alert 模型有 created_at 字段，如果没有则做个兜底
            time_str = "未知时间"
            if hasattr(a, "created_at") and a.created_at:
                time_str = a.created_at.strftime("%H:%M:%S")
                
            # 3. 组装成前端 Vue 需要的字段格式
            result.append({
                "id": a.id,
                "time": time_str,
                "camera": a.camera_name,
                "type": a.issue_type,
                "desc": a.issue_description,
                "img": a.image_url,
                "boxes": parsed_boxes
            })
            
        return result
    except Exception as e:
        print(f"❌ 获取历史告警失败: {e}")
        raise HTTPException(status_code=500, detail="获取历史告警失败")