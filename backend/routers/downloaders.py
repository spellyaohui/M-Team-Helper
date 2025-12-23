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
    get_server_stats,
    get_downloading_count,
    get_seeding_count,
    get_incomplete_torrents
)
import asyncio

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


@router.get("/stats")
async def get_all_downloaders_stats(db: Session = Depends(get_db)):
    """获取所有下载器的状态信息（用于仪表盘局部刷新）"""
    downloaders = db.query(Downloader).all()
    
    async def fetch_downloader_stats_safe(downloader) -> Dict[str, Any]:
        """安全获取单个下载器状态"""
        basic_info = {
            "id": downloader.id,
            "name": downloader.name,
            "type": downloader.type,
            "is_active": downloader.is_active,
            "downloading_count": 0,
            "seeding_count": 0,
            "incomplete_torrents": [],
            "download_speed": 0,
            "upload_speed": 0,
            "connection_status": "checking" if downloader.is_active else "offline",
            "free_space_gb": 0,  # 剩余磁盘空间（GB）
            "free_space_bytes": 0  # 剩余磁盘空间（字节）
        }
        
        if not downloader.is_active:
            return basic_info
        
        try:
            # 增加超时时间到3秒，确保有足够时间获取磁盘空间信息
            downloading_count, seeding_count, incomplete_torrents, server_stats = await asyncio.wait_for(
                asyncio.gather(
                    get_downloading_count(downloader),
                    get_seeding_count(downloader),
                    get_incomplete_torrents(downloader),
                    get_server_stats(downloader),
                    return_exceptions=True
                ),
                timeout=3.0  # 增加到3秒
            )
            
            # 处理异常结果
            has_error = False
            if isinstance(downloading_count, Exception):
                downloading_count = 0
                has_error = True
            if isinstance(seeding_count, Exception):
                seeding_count = 0
                has_error = True
            if isinstance(incomplete_torrents, Exception):
                incomplete_torrents = []
                has_error = True
            if isinstance(server_stats, Exception):
                server_stats = None
                has_error = True
            
            # 更新基础信息
            basic_info.update({
                "downloading_count": downloading_count,
                "seeding_count": seeding_count,
                "incomplete_torrents": incomplete_torrents,
            })
            
            # 从服务器统计信息中提取速度和磁盘空间数据
            if server_stats and not isinstance(server_stats, Exception):
                basic_info.update({
                    "download_speed": server_stats.get("dl_info_speed", 0),
                    "upload_speed": server_stats.get("up_info_speed", 0),
                    "connection_status": server_stats.get("connection_status", "connected"),
                    "free_space_gb": server_stats.get("free_space_gb", 0),
                    "free_space_bytes": server_stats.get("free_space_bytes", 0)
                })
            elif has_error:
                basic_info["connection_status"] = "error"
            else:
                basic_info["connection_status"] = "connected"
                
        except asyncio.TimeoutError:
            print(f"[DownloaderStats] 获取下载器 {downloader.name} 数据超时（3秒）")
            basic_info["connection_status"] = "timeout"
        except Exception as e:
            print(f"[DownloaderStats] 获取下载器 {downloader.name} 数据失败: {e}")
            basic_info["connection_status"] = "error"
        
        return basic_info
    
    # 并发获取所有下载器状态
    downloader_stats = await asyncio.gather(
        *[fetch_downloader_stats_safe(d) for d in downloaders],
        return_exceptions=True
    )
    
    # 过滤掉异常结果
    valid_stats = [
        stats for stats in downloader_stats 
        if isinstance(stats, dict)
    ]
    
    return {"downloader_stats": valid_stats}
