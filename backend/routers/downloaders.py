from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from database import get_db
from models import Downloader
from services.downloader import (
    test_downloader_connection, 
    get_tags, 
    get_disk_space_info, 
    get_server_stats
)

router = APIRouter(prefix="/downloaders", tags=["下载器管理"])

class DownloaderCreate(BaseModel):
    name: str
    type: str  # qbittorrent / transmission
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    use_ssl: bool = False  # 是否使用 HTTPS

class DownloaderResponse(BaseModel):
    id: int
    name: str
    type: str
    host: str
    port: int
    username: Optional[str]
    use_ssl: bool
    is_active: bool
    
    class Config:
        from_attributes = True

@router.get("/", response_model=List[DownloaderResponse])
async def list_downloaders(db: Session = Depends(get_db)):
    """获取所有下载器"""
    return db.query(Downloader).all()

@router.post("/", response_model=DownloaderResponse)
async def create_downloader(data: DownloaderCreate, db: Session = Depends(get_db)):
    """添加下载器"""
    downloader = Downloader(**data.model_dump())
    db.add(downloader)
    db.commit()
    db.refresh(downloader)
    return downloader

@router.post("/{downloader_id}/test")
async def test_connection(downloader_id: int, db: Session = Depends(get_db)):
    """测试下载器连接"""
    downloader = db.query(Downloader).filter(Downloader.id == downloader_id).first()
    if not downloader:
        raise HTTPException(status_code=404, detail="下载器不存在")
    
    result = await test_downloader_connection(downloader)
    return result

@router.delete("/{downloader_id}")
async def delete_downloader(downloader_id: int, db: Session = Depends(get_db)):
    """删除下载器"""
    downloader = db.query(Downloader).filter(Downloader.id == downloader_id).first()
    if not downloader:
        raise HTTPException(status_code=404, detail="下载器不存在")
    
    db.delete(downloader)
    db.commit()
    return {"success": True}


@router.get("/{downloader_id}/tags")
async def get_downloader_tags(downloader_id: int, db: Session = Depends(get_db)):
    """获取下载器的标签列表"""
    downloader = db.query(Downloader).filter(Downloader.id == downloader_id).first()
    if not downloader:
        raise HTTPException(status_code=404, detail="下载器不存在")
    
    tags = await get_tags(downloader)
    return {"tags": tags}


@router.get("/{downloader_id}/disk-space")
async def get_downloader_disk_space(downloader_id: int, db: Session = Depends(get_db)):
    """获取下载器磁盘空间信息"""
    downloader = db.query(Downloader).filter(Downloader.id == downloader_id).first()
    if not downloader:
        raise HTTPException(status_code=404, detail="下载器不存在")
    
    disk_info = await get_disk_space_info(downloader)
    if disk_info is None:
        raise HTTPException(status_code=500, detail="无法获取磁盘空间信息")
    
    return disk_info


@router.get("/{downloader_id}/stats")
async def get_downloader_stats(downloader_id: int, db: Session = Depends(get_db)):
    """获取下载器服务器统计信息"""
    downloader = db.query(Downloader).filter(Downloader.id == downloader_id).first()
    if not downloader:
        raise HTTPException(status_code=404, detail="下载器不存在")
    
    stats = await get_server_stats(downloader)
    if stats is None:
        raise HTTPException(status_code=500, detail="无法获取服务器统计信息")
    
    return stats
