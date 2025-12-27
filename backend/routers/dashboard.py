from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import asyncio

from database import get_db
from models import Account, DownloadHistory, FilterRule, Downloader, beijing_now
from services.downloader import get_downloading_count, get_incomplete_torrents, get_seeding_count, get_server_stats
from utils.cache import cached, cache_key_with_params

router = APIRouter(prefix="/dashboard", tags=["仪表盘"])

class AccountStats(BaseModel):
    """账号统计信息"""
    id: int
    username: str
    upload: float
    download: float
    ratio: float
    bonus: float
    last_login: Optional[datetime]
    is_active: bool

class DownloaderStats(BaseModel):
    """下载器统计信息"""
    id: int
    name: str
    type: str
    downloading_count: int
    seeding_count: int
    incomplete_torrents: List[Dict[str, Any]]
    is_active: bool
    # 新增速度信息
    download_speed: int = 0  # 当前下载速度 (字节/秒)
    upload_speed: int = 0    # 当前上传速度 (字节/秒)
    connection_status: str = "unknown"  # 连接状态
    # 新增磁盘空间信息
    free_space_gb: float = 0  # 剩余磁盘空间（GB）
    free_space_bytes: int = 0  # 剩余磁盘空间（字节）

class SystemStats(BaseModel):
    """系统统计信息"""
    total_accounts: int
    active_accounts: int
    total_rules: int
    active_rules: int
    total_downloaders: int
    active_downloaders: int
    total_downloads: int
    recent_downloads: int  # 最近24小时

class RecentActivity(BaseModel):
    """最近活动"""
    id: int
    torrent_name: str
    account_username: str
    status: str
    created_at: datetime
    discount_type: Optional[str]

class DashboardData(BaseModel):
    """仪表盘数据"""
    system_stats: SystemStats
    account_stats: List[AccountStats]
    downloader_stats: List[DownloaderStats]
    recent_activities: List[RecentActivity]
    download_trends: Dict[str, int]  # 按日期统计的下载趋势

@router.get("/", response_model=DashboardData)
@cached(ttl=60)  # 缓存 60 秒
async def get_dashboard_data(db: Session = Depends(get_db)):
    """获取仪表盘数据"""
    
    # 优化：使用单个查询获取所有统计数据
    from sqlalchemy import func, case
    
    # 系统统计 - 合并查询
    stats_query = db.query(
        func.count(Account.id).label('total_accounts'),
        func.sum(case((Account.is_active == True, 1), else_=0)).label('active_accounts'),
        func.count(FilterRule.id).label('total_rules'),
        func.sum(case((FilterRule.is_enabled == True, 1), else_=0)).label('active_rules'),
        func.count(Downloader.id).label('total_downloaders'),
        func.sum(case((Downloader.is_active == True, 1), else_=0)).label('active_downloaders')
    ).select_from(Account).outerjoin(FilterRule).outerjoin(Downloader).first()
    
    # 下载历史统计
    total_downloads = db.query(DownloadHistory).count()
    
    # 最近24小时下载数
    yesterday = beijing_now() - timedelta(days=1)
    recent_downloads = db.query(DownloadHistory).filter(
        DownloadHistory.created_at >= yesterday
    ).count()
    
    system_stats = SystemStats(
        total_accounts=stats_query.total_accounts or 0,
        active_accounts=stats_query.active_accounts or 0,
        total_rules=stats_query.total_rules or 0,
        active_rules=stats_query.active_rules or 0,
        total_downloaders=stats_query.total_downloaders or 0,
        active_downloaders=stats_query.active_downloaders or 0,
        total_downloads=total_downloads,
        recent_downloads=recent_downloads
    )
    
    # 账号统计
    accounts = db.query(Account).all()
    account_stats = [
        AccountStats(
            id=acc.id,
            username=acc.username,
            upload=acc.upload,
            download=acc.download,
            ratio=acc.ratio,
            bonus=acc.bonus,
            last_login=acc.last_login,
            is_active=acc.is_active
        ) for acc in accounts
    ]
    
    # 下载器统计 - 仅返回基础信息，不连接下载器（避免首屏阻塞）
    downloaders = db.query(Downloader).all()
    downloader_stats = [
        DownloaderStats(
            id=d.id,
            name=d.name,
            type=d.type,
            downloading_count=0,
            seeding_count=0,
            incomplete_torrents=[],
            is_active=d.is_active,
            download_speed=0,
            upload_speed=0,
            connection_status="需要刷新" if d.is_active else "离线",
            free_space_gb=0,
            free_space_bytes=0
        ) for d in downloaders
    ]
    
    # 最近活动（最近10条下载记录）
    recent_history = db.query(DownloadHistory, Account.username).join(
        Account, DownloadHistory.account_id == Account.id
    ).order_by(DownloadHistory.created_at.desc()).limit(10).all()
    
    recent_activities = [
        RecentActivity(
            id=history.id,
            torrent_name=history.torrent_name,
            account_username=username,
            status=history.status,
            created_at=history.created_at,
            discount_type=history.discount_type
        ) for history, username in recent_history
    ]
    
    # 下载趋势（最近7天）
    download_trends = {}
    for i in range(7):
        date = beijing_now() - timedelta(days=i)
        date_str = date.strftime('%Y-%m-%d')
        
        count = db.query(DownloadHistory).filter(
            func.date(DownloadHistory.created_at) == date.date()
        ).count()
        
        download_trends[date_str] = count
    
    return DashboardData(
        system_stats=system_stats,
        account_stats=account_stats,
        downloader_stats=downloader_stats,
        recent_activities=recent_activities,
        download_trends=download_trends
    )

@router.get("/accounts/{account_id}/stats")
async def get_account_detailed_stats(account_id: int, db: Session = Depends(get_db)):
    """获取账号详细统计"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")
    
    # 下载统计
    total_downloads = db.query(DownloadHistory).filter(
        DownloadHistory.account_id == account_id
    ).count()
    
    completed_downloads = db.query(DownloadHistory).filter(
        DownloadHistory.account_id == account_id,
        DownloadHistory.status == "completed"
    ).count()
    
    failed_downloads = db.query(DownloadHistory).filter(
        DownloadHistory.account_id == account_id,
        DownloadHistory.status.in_(["failed", "expired_deleted"])
    ).count()
    
    # 按促销类型统计
    free_downloads = db.query(DownloadHistory).filter(
        DownloadHistory.account_id == account_id,
        DownloadHistory.discount_type == "FREE"
    ).count()
    
    double_upload_downloads = db.query(DownloadHistory).filter(
        DownloadHistory.account_id == account_id,
        DownloadHistory.discount_type.like("%2X%")
    ).count()
    
    return {
        "account": AccountStats(
            id=account.id,
            username=account.username,
            upload=account.upload,
            download=account.download,
            ratio=account.ratio,
            bonus=account.bonus,
            last_login=account.last_login,
            is_active=account.is_active
        ),
        "download_stats": {
            "total": total_downloads,
            "completed": completed_downloads,
            "failed": failed_downloads,
            "success_rate": round(completed_downloads / total_downloads * 100, 2) if total_downloads > 0 else 0
        },
        "promotion_stats": {
            "free": free_downloads,
            "double_upload": double_upload_downloads
        }
    }

@router.get("/downloader-stats", response_model=List[DownloaderStats])
@cached(ttl=30)  # 缓存 30 秒
async def get_downloader_stats(db: Session = Depends(get_db)):
    """获取下载器详细状态（单独接口，避免阻塞主仪表盘）"""
    downloaders = db.query(Downloader).all()
    
    def create_basic_downloader_stats(downloader) -> DownloaderStats:
        """创建基础下载器统计信息（不连接下载器）"""
        return DownloaderStats(
            id=downloader.id,
            name=downloader.name,
            type=downloader.type,
            downloading_count=0,
            seeding_count=0,
            incomplete_torrents=[],
            is_active=downloader.is_active,
            download_speed=0,
            upload_speed=0,
            connection_status="检查中" if downloader.is_active else "离线",
            free_space_gb=0,
            free_space_bytes=0
        )
    
    async def fetch_downloader_stats_safe(downloader) -> DownloaderStats:
        """安全获取单个下载器状态，超时或失败时返回基础信息"""
        basic_stats = create_basic_downloader_stats(downloader)
        
        if not downloader.is_active:
            return basic_stats
        
        try:
            # 使用 5 秒超时时间
            downloading_count, seeding_count, incomplete_torrents, server_stats = await asyncio.wait_for(
                asyncio.gather(
                    get_downloading_count(downloader),
                    get_seeding_count(downloader),
                    get_incomplete_torrents(downloader),
                    get_server_stats(downloader),
                    return_exceptions=True
                ),
                timeout=5.0
            )
            
            # 检查是否有异常
            if isinstance(downloading_count, Exception):
                downloading_count = 0
            if isinstance(seeding_count, Exception):
                seeding_count = 0
            if isinstance(incomplete_torrents, Exception):
                incomplete_torrents = []
            if isinstance(server_stats, Exception):
                server_stats = {}
            
            # 更新统计信息
            basic_stats.downloading_count = downloading_count
            basic_stats.seeding_count = seeding_count
            basic_stats.incomplete_torrents = incomplete_torrents[:5]  # 只返回前5个
            basic_stats.connection_status = "在线"
            
            # 服务器统计信息
            if server_stats:
                basic_stats.download_speed = server_stats.get('dl_info_speed', 0)
                basic_stats.upload_speed = server_stats.get('up_info_speed', 0)
                basic_stats.free_space_bytes = server_stats.get('free_space_on_disk', 0)
                basic_stats.free_space_gb = basic_stats.free_space_bytes / (1024**3)
            
            return basic_stats
            
        except asyncio.TimeoutError:
            basic_stats.connection_status = "超时"
            return basic_stats
        except Exception as e:
            basic_stats.connection_status = f"错误: {str(e)[:20]}"
            return basic_stats
    
    # 并发获取所有下载器状态
    downloader_stats = await asyncio.gather(
        *[fetch_downloader_stats_safe(d) for d in downloaders],
        return_exceptions=True
    )
    
    # 过滤掉异常
    return [
        stats for stats in downloader_stats 
        if isinstance(stats, DownloaderStats)
    ]