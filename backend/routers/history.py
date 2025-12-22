from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from database import get_db
from models import DownloadHistory, Account

router = APIRouter(prefix="/history", tags=["下载历史"])

class HistoryResponse(BaseModel):
    id: int
    account_id: int
    torrent_id: str
    torrent_name: str
    torrent_size: float
    rule_id: Optional[int]
    downloader_id: Optional[int]
    status: str
    info_hash: Optional[str]
    discount_type: Optional[str]
    discount_end_time: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True

class HistoryListResponse(BaseModel):
    total: int
    data: List[HistoryResponse]

@router.get("/", response_model=HistoryListResponse)
async def list_history(
    account_id: Optional[int] = None,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """获取下载历史"""
    query = db.query(DownloadHistory)
    
    if account_id:
        query = query.filter(DownloadHistory.account_id == account_id)
    if status:
        query = query.filter(DownloadHistory.status == status)
    
    total = query.count()
    items = query.order_by(DownloadHistory.created_at.desc())\
        .offset((page - 1) * page_size)\
        .limit(page_size)\
        .all()
    
    return HistoryListResponse(total=total, data=items)

@router.delete("/{history_id}")
async def delete_history(history_id: int, db: Session = Depends(get_db)):
    """删除下载历史记录"""
    history = db.query(DownloadHistory).filter(DownloadHistory.id == history_id).first()
    if not history:
        raise HTTPException(status_code=404, detail="记录不存在")
    
    db.delete(history)
    db.commit()
    return {"success": True, "message": "删除成功"}

@router.delete("/")
async def clear_history(
    account_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """清空下载历史"""
    query = db.query(DownloadHistory)
    if account_id:
        query = query.filter(DownloadHistory.account_id == account_id)
    
    count = query.delete()
    db.commit()
    return {"success": True, "message": f"已删除 {count} 条记录"}
