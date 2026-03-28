from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from database import get_db
from models import Account, DownloadHistory
from services.scraper import MTeamAPI, parse_torrent
from services.downloader import get_torrent_info, normalize_torrent_status
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
    discount_end_time: Optional[str] = None
    is_free: bool
    is_2x: bool
    created_date: str
    imdb: Optional[str] = None
    imdb_rating: Optional[float] = None
    douban: Optional[str] = None
    douban_rating: Optional[float] = None
    labels: List[str]
    images: List[str] = []

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

@router.get("/categories")
async def get_categories(
    account_id: int = Query(...),
    db: Session = Depends(get_db)
):
    """获取种子分类列表"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account or not account.api_key:
        raise HTTPException(status_code=404, detail="账号不存在或未配置")
    
    api = MTeamAPI(account.api_key)
    result = await api.get_categories()
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    return {"success": True, "data": result["data"]}

@router.get("/metadata")
async def get_metadata(
    account_id: int = Query(...),
    types: str = Query("categories", description="获取的元数据类型，用逗号分隔：categories,sources,mediums,standards,videoCodecs,audioCodecs,teams,processings"),
    db: Session = Depends(get_db)
):
    """获取种子元数据（分类、来源、介质等）"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account or not account.api_key:
        raise HTTPException(status_code=404, detail="账号不存在或未配置")
    
    api = MTeamAPI(account.api_key)
    result_data = {}
    
    type_list = [t.strip() for t in types.split(",")]
    
    for metadata_type in type_list:
        try:
            if metadata_type == "categories":
                result = await api.get_categories()
            elif metadata_type == "sources":
                result = await api.get_source_list()
            elif metadata_type == "mediums":
                result = await api.get_medium_list()
            elif metadata_type == "standards":
                result = await api.get_standard_list()
            elif metadata_type == "videoCodecs":
                result = await api.get_video_codec_list()
            elif metadata_type == "audioCodecs":
                result = await api.get_audio_codec_list()
            elif metadata_type == "teams":
                result = await api.get_team_list()
            elif metadata_type == "processings":
                result = await api.get_processing_list()
            else:
                continue
            
            if result["success"]:
                result_data[metadata_type] = result["data"]
            else:
                result_data[metadata_type] = {"error": result.get("error")}
        except Exception as e:
            result_data[metadata_type] = {"error": str(e)}
    
    return {"success": True, "data": result_data}


class PushDownloadRequest(BaseModel):
    torrent_id: str
    downloader_id: int
    account_id: int
    save_path: Optional[str] = None
    tags: Optional[List[str]] = None


@router.post("/push")
async def push_to_downloader(
    data: PushDownloadRequest,
    db: Session = Depends(get_db)
):
    """推送种子到下载器"""
    from services.downloader import add_torrent
    from models import Downloader as DownloaderModel
    
    # 验证账号
    account = db.query(Account).filter(Account.id == data.account_id).first()
    if not account or not account.api_key:
        raise HTTPException(status_code=404, detail="账号不存在或未配置")
    
    # 验证下载器
    downloader = db.query(DownloaderModel).filter(DownloaderModel.id == data.downloader_id).first()
    if not downloader:
        raise HTTPException(status_code=404, detail="下载器不存在")
    
    if not downloader.is_active:
        raise HTTPException(status_code=400, detail="下载器未激活")

    latest_history = db.query(DownloadHistory).filter(
        DownloadHistory.account_id == data.account_id,
        DownloadHistory.torrent_id == data.torrent_id
    ).order_by(DownloadHistory.created_at.desc(), DownloadHistory.id.desc()).first()

    if latest_history:
        latest_status = latest_history.status
        if latest_history.info_hash and latest_history.downloader_id and latest_history.downloader:
            torrent_info = await get_torrent_info(latest_history.downloader, latest_history.info_hash)
            if torrent_info is None:
                latest_status = "deleted"
            else:
                latest_status = normalize_torrent_status(
                    torrent_info.get("state", ""),
                    torrent_info.get("progress", 0),
                    torrent_info.get("is_completed", False)
                )

            if latest_history.status != latest_status:
                latest_history.status = latest_status
                db.commit()
                db.refresh(latest_history)

        if latest_status not in ["deleted", "expired_deleted", "dynamic_deleted", "unregistered_deleted", "failed"]:
            raise HTTPException(status_code=409, detail=f"种子已在下载器中，当前状态：{latest_status}")
    
    api = MTeamAPI(account.api_key)
    
    # 下载种子文件
    torrent_content = await api.download_torrent(data.torrent_id)
    if not torrent_content:
        raise HTTPException(status_code=500, detail="下载种子文件失败")
    
    # 保存种子文件
    torrent_path = TORRENT_DIR / f"{data.torrent_id}.torrent"
    torrent_path.write_bytes(torrent_content)
    
    # 推送到下载器
    info_hash = await add_torrent(
        downloader,
        str(torrent_path),
        data.save_path,
        data.tags
    )
    
    if not info_hash:
        raise HTTPException(status_code=500, detail="推送到下载器失败")
    
    # 获取种子详情用于记录历史
    detail_result = await api.get_torrent_detail(data.torrent_id)
    torrent_data = {}
    if detail_result["success"]:
        torrent_data = parse_torrent(detail_result["data"])
    
    # 解析促销到期时间
    discount_end_time = None
    if torrent_data.get("discount_end_time"):
        try:
            ts = torrent_data["discount_end_time"]
            if isinstance(ts, (int, float)):
                discount_end_time = datetime.fromtimestamp(ts / 1000 if ts > 1e10 else ts)
            elif isinstance(ts, str):
                discount_end_time = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except Exception as e:
            print(f"[Push] 解析促销到期时间失败: {e}")
    
    # 记录下载历史
    history = DownloadHistory(
        account_id=data.account_id,
        torrent_id=data.torrent_id,
        torrent_name=torrent_data.get("name", f"种子_{data.torrent_id}"),
        torrent_size=torrent_data.get("size", 0),
        rule_id=None,
        downloader_id=data.downloader_id,
        status="downloading",
        info_hash=info_hash,
        discount_type=torrent_data.get("discount"),
        discount_end_time=discount_end_time,
        images=torrent_data.get("images")
    )
    db.add(history)
    db.commit()
    
    return {
        "success": True,
        "message": "推送成功",
        "info_hash": info_hash,
        "history_id": history.id
    }


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
    
    # 转换为统一格式
    torrent_data = parse_torrent(result["data"])
    # 添加详情特有字段
    torrent_data["description"] = result["data"].get("descr", "")
    torrent_data["mediainfo"] = result["data"].get("mediainfo", "")

    latest_history = db.query(DownloadHistory).filter(
        DownloadHistory.account_id == account_id,
        DownloadHistory.torrent_id == torrent_id
    ).order_by(DownloadHistory.created_at.desc(), DownloadHistory.id.desc()).first()

    torrent_data["history_id"] = None
    torrent_data["download_status"] = None
    torrent_data["downloader_id"] = None
    torrent_data["info_hash"] = None

    if latest_history:
        latest_status = latest_history.status

        if latest_history.info_hash and latest_history.downloader_id and latest_history.downloader:
            torrent_info = await get_torrent_info(latest_history.downloader, latest_history.info_hash)
            if torrent_info is None:
                latest_status = "deleted"
            else:
                latest_status = normalize_torrent_status(
                    torrent_info.get("state", ""),
                    torrent_info.get("progress", 0),
                    torrent_info.get("is_completed", False)
                )

            if latest_history.status != latest_status:
                latest_history.status = latest_status
                db.commit()
                db.refresh(latest_history)

        torrent_data["history_id"] = latest_history.id
        torrent_data["download_status"] = latest_status
        torrent_data["downloader_id"] = latest_history.downloader_id
        torrent_data["info_hash"] = latest_history.info_hash
    
    return {"success": True, "data": torrent_data}

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
