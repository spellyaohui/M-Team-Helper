import asyncio
from datetime import datetime
from typing import List
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session

from database import SessionLocal
from models import Account, FilterRule, DownloadHistory, Downloader
from services.scraper import MTeamAPI, parse_torrent
from services.downloader import add_torrent, get_torrent_info, delete_torrent, get_downloading_count, get_torrent_info_with_tags
from routers.rules import match_torrent
from config import settings, TORRENT_DIR

scheduler = AsyncIOScheduler()

async def refresh_all_accounts():
    """刷新所有账号信息"""
    db = SessionLocal()
    try:
        accounts = db.query(Account).filter(Account.is_active == True).all()
        for account in accounts:
            if account.api_key:
                try:
                    api = MTeamAPI(account.api_key)
                    result = await api.get_profile()
                    if result["success"]:
                        data = result["data"]
                        member_count = data.get("memberCount", {})
                        account.upload = int(member_count.get("uploaded", 0))
                        account.download = int(member_count.get("downloaded", 0))
                        account.ratio = float(member_count.get("shareRate", 0))
                        account.bonus = float(member_count.get("bonus", 0))
                        account.last_login = datetime.utcnow()
                        print(f"[Scheduler] 刷新账号 {account.username} 成功")
                except Exception as e:
                    print(f"[Scheduler] 刷新账号 {account.username} 失败: {e}")
        db.commit()
    finally:
        db.close()

async def auto_download_torrents():
    """根据规则自动下载种子"""
    db = SessionLocal()
    try:
        # 获取所有启用的规则
        rules = db.query(FilterRule).filter(FilterRule.is_enabled == True).all()
        
        for rule in rules:
            account = db.query(Account).filter(Account.id == rule.account_id).first()
            if not account or not account.api_key:
                continue
            
            try:
                api = MTeamAPI(account.api_key)
                
                # 构建搜索参数
                discount = None
                if rule.free_only:
                    discount = "FREE"
                elif rule.double_upload:
                    discount = "_2X"
                
                result = await api.search_torrents(
                    page=1,
                    page_size=50,
                    mode=rule.mode,  # 使用规则的模式（normal 或 adult）
                    categories=rule.categories,
                    discount=discount
                )
                
                if not result["success"]:
                    continue
                
                torrents = [parse_torrent(t) for t in result["data"].get("data", [])]
                
                for torrent in torrents:
                    # 检查是否已下载
                    existing = db.query(DownloadHistory).filter(
                        DownloadHistory.account_id == account.id,
                        DownloadHistory.torrent_id == torrent["id"]
                    ).first()
                    
                    if existing:
                        continue
                    
                    # 检查是否匹配规则
                    if not match_torrent(torrent, rule):
                        continue
                    
                    # 检查下载队列限制
                    if rule.downloader_id and rule.max_downloading:
                        downloader = db.query(Downloader).filter(
                            Downloader.id == rule.downloader_id
                        ).first()
                        
                        if downloader:
                            current_downloading = await get_downloading_count(downloader)
                            if current_downloading >= rule.max_downloading:
                                print(f"[Scheduler] 下载队列已满 ({current_downloading}/{rule.max_downloading})，跳过: {torrent['name']}")
                                continue
                    
                    print(f"[Scheduler] 匹配规则 '{rule.name}': {torrent['name']}")
                    
                    # 下载种子文件
                    torrent_content = await api.download_torrent(torrent["id"])
                    if not torrent_content:
                        print(f"[Scheduler] 下载种子文件失败: {torrent['name']}")
                        continue
                    
                    # 保存种子文件
                    torrent_path = TORRENT_DIR / f"{torrent['id']}.torrent"
                    torrent_path.write_bytes(torrent_content)
                    
                    # 推送到下载器
                    status = "downloaded"
                    info_hash = None
                    if rule.downloader_id:
                        downloader = db.query(Downloader).filter(
                            Downloader.id == rule.downloader_id
                        ).first()
                        
                        if downloader:
                            info_hash = await add_torrent(
                                downloader,
                                str(torrent_path),
                                rule.save_path,
                                rule.tags  # 传入标签
                            )
                            status = "pushing" if info_hash else "push_failed"
                            print(f"[Scheduler] 推送到下载器: {bool(info_hash)}, hash: {info_hash}")
                    
                    # 解析促销到期时间
                    discount_end_time = None
                    if torrent.get("discount_end_time"):
                        try:
                            from datetime import datetime
                            # 尝试解析时间戳（毫秒）
                            ts = torrent["discount_end_time"]
                            if isinstance(ts, (int, float)):
                                discount_end_time = datetime.fromtimestamp(ts / 1000 if ts > 1e10 else ts)
                            elif isinstance(ts, str):
                                discount_end_time = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                        except Exception as e:
                            print(f"[Scheduler] 解析促销到期时间失败: {e}")
                    
                    # 记录下载历史
                    history = DownloadHistory(
                        account_id=account.id,
                        torrent_id=torrent["id"],
                        torrent_name=torrent["name"],
                        torrent_size=torrent["size"],
                        rule_id=rule.id,
                        downloader_id=rule.downloader_id,
                        status=status,
                        info_hash=info_hash,
                        discount_type=torrent.get("discount"),
                        discount_end_time=discount_end_time
                    )
                    db.add(history)
                    db.commit()
                    
            except Exception as e:
                print(f"[Scheduler] 处理规则 '{rule.name}' 失败: {e}")
                
    finally:
        db.close()


async def check_expired_torrents():
    """检查促销过期但未完成的种子，自动删除
    
    这个功能很重要，因为 PT 网站对分享率要求很高。
    如果免费促销期过了种子还未下载完，就会计算下载量，容易导致账号被封。
    
    注意：只删除带有规则指定标签的种子，避免误删用户手动添加的收费种子。
    """
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        
        # 查找所有有促销到期时间、且已过期、且状态不是已完成的记录
        expired_records = db.query(DownloadHistory).filter(
            DownloadHistory.discount_end_time != None,
            DownloadHistory.discount_end_time < now,
            DownloadHistory.status.notin_(["completed", "expired_deleted", "failed"]),
            DownloadHistory.info_hash != None,
            DownloadHistory.rule_id != None  # 必须有关联的规则
        ).all()
        
        for record in expired_records:
            # 获取下载器
            if not record.downloader_id:
                continue
            
            downloader = db.query(Downloader).filter(
                Downloader.id == record.downloader_id
            ).first()
            
            if not downloader:
                continue
            
            # 获取关联的规则，检查标签
            rule = db.query(FilterRule).filter(FilterRule.id == record.rule_id).first()
            rule_tags = set(rule.tags) if rule and rule.tags else set()
            
            try:
                # 获取种子信息（包含标签）
                torrent_info = await get_torrent_info_with_tags(downloader, record.info_hash)
                
                if torrent_info is None:
                    # 种子不存在（可能已被手动删除）
                    record.status = "expired_deleted"
                    print(f"[Scheduler] 种子已不存在: {record.torrent_name}")
                    continue
                
                if torrent_info.get("is_completed"):
                    # 已完成，更新状态
                    record.status = "completed"
                    print(f"[Scheduler] 种子已完成: {record.torrent_name}")
                    continue
                
                # 检查标签是否匹配（只删除带有规则指定标签的种子）
                torrent_tags = set(torrent_info.get("tags", []))
                
                if rule_tags and not rule_tags.intersection(torrent_tags):
                    # 种子没有规则指定的标签，跳过删除
                    print(f"[Scheduler] 种子标签不匹配规则，跳过删除: {record.torrent_name} (种子标签: {torrent_tags}, 规则标签: {rule_tags})")
                    continue
                
                # 未完成且已过期，删除种子
                progress = torrent_info.get("progress", 0)
                print(f"[Scheduler] 促销已过期，删除未完成种子: {record.torrent_name} (进度: {progress:.1f}%, 标签: {torrent_tags})")
                
                success = await delete_torrent(downloader, record.info_hash, delete_files=True)
                
                if success:
                    record.status = "expired_deleted"
                    print(f"[Scheduler] 已删除过期种子: {record.torrent_name}")
                else:
                    print(f"[Scheduler] 删除过期种子失败: {record.torrent_name}")
                    
            except Exception as e:
                print(f"[Scheduler] 处理过期种子失败 {record.torrent_name}: {e}")
        
        db.commit()
        
    finally:
        db.close()

def start_scheduler():
    """启动定时任务"""
    # 每5分钟刷新账号信息
    scheduler.add_job(
        refresh_all_accounts,
        IntervalTrigger(seconds=settings.REFRESH_INTERVAL),
        id="refresh_accounts",
        replace_existing=True
    )
    
    # 每3分钟检查自动下载
    scheduler.add_job(
        auto_download_torrents,
        IntervalTrigger(seconds=180),
        id="auto_download",
        replace_existing=True
    )
    
    # 每1分钟检查促销过期的种子
    scheduler.add_job(
        check_expired_torrents,
        IntervalTrigger(seconds=60),
        id="check_expired",
        replace_existing=True
    )
    
    scheduler.start()
    print("[Scheduler] 定时任务已启动")

def stop_scheduler():
    """停止定时任务"""
    scheduler.shutdown()
    print("[Scheduler] 定时任务已停止")
