from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from database import get_db
from models import Account, DownloadHistory
from services.scraper import MTeamAPI, parse_torrent
from config import TORRENT_DIR

router = APIRouter(prefix="/torrents", tags=["种子管理"])

class TorrentSearchParams(BaseModel):
    account_id: int
    page: int = 1
    page_size: int = 50
    mode: str = "normal"  # normal 或 adult
    keyword: Optional[str] = None
    categories: Optional[List[str]] = None
    discount: Optional[str] = None  # FREE, PERCENT_50, _2X_FREE, _2X_PERCENT_50, _2X
    min_size_gb: Optional[float] = None
    max_size_gb: Optional[float] = None
    min_seeders: Optional[int] = None
    max_seeders: Optional[int] = None

class TorrentResponse(BaseModel):
    id: str
    name: str
    small_descr: Optional[str]
    category: str
    size: int
    size_gb: float
    seeders: int
    leechers: int
    completed: int
    discount: str
    discount_text: str
    is_free: bool
    is_2x: bool
    created_date: str
    labels: List[str]

class TorrentListResponse(BaseModel):
    success: bool
    total: int
    page: int
    page_size: int
    data: List[TorrentResponse]

@router.post("/search", response_model=TorrentListResponse)
async def search_torrents(params: TorrentSearchParams, db: Session = Depends(get_db)):
    """搜索种子列表"""
    account = db.query(Account).filter(Account.id == params.account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")
    
    if not account.api_key:
        raise HTTPException(status_code=400, detail="账号未配置 API Token")
    
    api = MTeamAPI(account.api_key)
    result = await api.search_torrents(
        page=params.page,
        page_size=params.page_size,
        mode=params.mode,
        keyword=params.keyword,
        categories=params.categories,
        discount=params.discount
    )
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    data = result["data"]
    torrents = [parse_torrent(t) for t in data.get("data", [])]
    
    # 本地过滤（大小、做种数）
    if params.min_size_gb is not None:
        torrents = [t for t in torrents if t["size_gb"] >= params.min_size_gb]
    if params.max_size_gb is not None:
        torrents = [t for t in torrents if t["size_gb"] <= params.max_size_gb]
    if params.min_seeders is not None:
        torrents = [t for t in torrents if t["seeders"] >= params.min_seeders]
    if params.max_seeders is not None:
        torrents = [t for t in torrents if t["seeders"] <= params.max_seeders]
    
    return TorrentListResponse(
        success=True,
        total=int(data.get("total", 0)),
        page=params.page,
        page_size=params.page_size,
        data=torrents
    )

@router.get("/{torrent_id}")
async def get_torrent_detail(
    torrent_id: str,
    account_id: int = Query(...),
    db: Session = Depends(get_db)
):
    """获取种子详情"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account or not account.api_key:
        raise HTTPException(status_code=404, detail="账号不存在或未配置")
    
    api = MTeamAPI(account.api_key)
    result = await api.get_torrent_detail(torrent_id)
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    return {"success": True, "data": result["data"]}

@router.post("/{torrent_id}/download")
async def download_torrent(
    torrent_id: str,
    account_id: int = Query(...),
    db: Session = Depends(get_db)
):
    """下载种子文件"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account or not account.api_key:
        raise HTTPException(status_code=404, detail="账号不存在或未配置")
    
    api = MTeamAPI(account.api_key)
    
    # 获取下载链接
    result = await api.gen_download_token(torrent_id)
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    download_url = result["data"]
    
    # 下载种子文件
    torrent_content = await api.download_torrent(torrent_id)
    if not torrent_content:
        raise HTTPException(status_code=500, detail="下载种子文件失败")
    
    # 保存到本地
    torrent_path = TORRENT_DIR / f"{torrent_id}.torrent"
    torrent_path.write_bytes(torrent_content)
    
    return Response(
        content=torrent_content,
        media_type="application/x-bittorrent",
        headers={"Content-Disposition": f"attachment; filename={torrent_id}.torrent"}
    )

@router.get("/{torrent_id}/download-url")
async def get_download_url(
    torrent_id: str,
    account_id: int = Query(...),
    db: Session = Depends(get_db)
):
    """获取种子下载链接"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account or not account.api_key:
        raise HTTPException(status_code=404, detail="账号不存在或未配置")
    
    api = MTeamAPI(account.api_key)
    result = await api.gen_download_token(torrent_id)
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    return {"success": True, "url": result["data"]}
