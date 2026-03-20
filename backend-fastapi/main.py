from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
from datetime import datetime

# --- 新增的数据库和路由导入 ---
from app.api.router import api_router
from app.core.database import engine, Base

# 1. 自动在 MySQL 中创建表 (必须在用到数据库之前执行)
Base.metadata.create_all(bind=engine)

# 2. 初始化 FastAPI 应用 (这就是 Pylance 报错找不到的那个 "app")
app = FastAPI(
    title="AI Security Monitor API",
    description="多路视频大模型安全识别系统后端",
    version="1.0.0"
)

# 3. 配置跨域请求 (CORS) - 允许 Vue 前端访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发阶段允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. 挂载我们刚才写好的业务路由 (注意：这行必须在 app = FastAPI() 之后)
app.include_router(api_router, prefix="/api")


# --- 下面是之前写的基础测试接口和 WebSocket ---

@app.get("/")
async def root():
    return {"message": "Welcome to AI Security Monitor Backend!"}

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

# WebSocket 连接管理器
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

@app.websocket("/ws/alerts")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # 发送一条连接成功的欢迎消息
        await websocket.send_text(json.dumps({"type": "info", "message": "已连接到实时告警推送服务"}))
        while True:
            # 保持连接，等待客户端消息
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("大屏客户端已断开连接")