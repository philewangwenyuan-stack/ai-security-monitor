from fastapi import APIRouter
from app.api.endpoints import cameras
# from app.api.endpoints import events  # 后续写了日志接口再解开注释

api_router = APIRouter()

# 注册摄像头的路由，并加上统一的 /cameras 前缀
api_router.include_router(cameras.router, prefix="/cameras", tags=["摄像头管理"])