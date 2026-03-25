from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models.camera import Camera
from app.schemas.camera_schema import CameraCreate, CameraResponse

router = APIRouter()

@router.post("/", response_model=CameraResponse)
def create_camera(camera: CameraCreate, db: Session = Depends(get_db)):
    """在后台添加一个新的摄像头配置"""
    db_camera = Camera(**camera.model_dump())
    db.add(db_camera)
    db.commit()
    db.refresh(db_camera)
    return db_camera

@router.get("/", response_model=List[CameraResponse])
def read_cameras(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """获取前端大屏需要的摄像头列表"""
    cameras = db.query(Camera).offset(skip).limit(limit).all()
    return cameras

@router.delete("/{camera_id}")
def delete_camera(camera_id: int, db: Session = Depends(get_db)):
    """删除摄像头"""
    db_camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not db_camera:
        raise HTTPException(status_code=404, detail="摄像头未找到")
    db.delete(db_camera)
    db.commit()
    return {"message": "删除成功"}
@router.put("/{camera_id}", response_model=CameraResponse)
def update_camera(camera_id: int, camera: CameraCreate, db: Session = Depends(get_db)):
    """编辑/更新摄像头"""
    # 1. 在数据库中查找要修改的摄像头
    db_camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not db_camera:
        raise HTTPException(status_code=404, detail="摄像头未找到")
    
    # 2. 将前端传过来的新数据更新到数据库对象上
    update_data = camera.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_camera, key, value)
        
    # 3. 提交并保存更改
    db.commit()
    db.refresh(db_camera)
    return db_camera