from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from database import get_db
from models import Account, DownloadHistory, FilterRule, Downloader
from services.downloader import get_downloading_count, get_incomplete_torrents, get_seeding_count

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
async def get_dashboard_data(db: Session = Depends(get_db)):
    """获取仪表盘数据"""
    
    # 系统统计
    total_accounts = db.query(Account).count()
    active_accounts = db.query(Account).filter(Account.is_active == True).count()
    total_rules = db.query(FilterRule).count()
    active_rules = db.query(FilterRule).filter(FilterRule.is_enabled == True).count()
    total_downloaders = db.query(Downloader).count()
    active_downloaders = db.query(Downloader).filter(Downloader.is_active == True).count()
    total_downloads = db.query(DownloadHistory).count()
    
    # 最近24小时下载数
    yesterday = datetime.utcnow() - timedelta(days=1)
    recent_downloads = db.query(DownloadHistory).filter(
        DownloadHistory.created_at >= yesterday
    ).count()
    
    system_stats = SystemStats(
        total_accounts=total_accounts,
        active_accounts=active_accounts,
        total_rules=total_rules,
        active_rules=active_rules,
        total_downloaders=total_downloaders,
        active_downloaders=active_downloaders,
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
    
    # 下载器统计
    downloaders = db.query(Downloader).all()
    downloader_stats = []
    
    for downloader in downloaders:
        downloading_count = 0
        seeding_count = 0
        incomplete_torrents = []
        
        if downloader.is_active:
            try:
                downloading_count = await get_downloading_count(downloader)
                seeding_count = await get_seeding_count(downloader)
                incomplete_torrents = await get_incomplete_torrents(downloader)
            except Exception as e:
                print(f"获取下载器 {downloader.name} 数据失败: {e}")
        
        downloader_stats.append(DownloaderStats(
            id=downloader.id,
            name=downloader.name,
            type=downloader.type,
            downloading_count=downloading_count,
            seeding_count=seeding_count,
            incomplete_torrents=incomplete_torrents,
            is_active=downloader.is_active
        ))
    
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
        date = datetime.utcnow() - timedelta(days=i)
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