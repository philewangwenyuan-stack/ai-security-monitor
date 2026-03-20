from sqlalchemy import Column, Integer, String, Boolean
from app.core.database import Base

class Camera(Base):
    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), index=True, comment="摄像头名称")
    stream_url = Column(String(255), comment="视频流地址(RTSP/RTMP)")
    capture_interval = Column(Integer, default=5, comment="抽帧间隔(秒)")
    is_active = Column(Boolean, default=True, comment="是否启用")