# 文件路径: app/models/alert.py
from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime
from app.core.database import Base

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    camera_name = Column(String(50), index=True, comment="摄像头名称")
    issue_type = Column(String(50), index=True, comment="隐患类型")
    issue_description = Column(Text, comment="详细描述")
    image_url = Column(String(255), comment="本地静态图片访问路径")
    boxes = Column(Text, comment="检测框坐标(JSON格式字符串)")
    created_at = Column(DateTime, default=datetime.now, comment="告警时间")