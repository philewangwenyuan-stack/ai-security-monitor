from pydantic import BaseModel, HttpUrl

# 供前端创建/更新摄像头时使用的数据格式
class CameraCreate(BaseModel):
    name: str
    stream_url: str
    capture_interval: int = 5
    is_active: bool = True

# 供后端返回给前端的数据格式 (多了一个 id)
class CameraResponse(CameraCreate):
    id: int

    class Config:
        from_attributes = True  # 允许从 SQLAlchemy 模型直接转换为 Pydantic 模型