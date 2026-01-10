from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from sqlalchemy.orm import Session
import json

from database import SessionLocal
from models import Account, FilterRule, DownloadHistory, Downloader, SystemSettings, beijing_now
from services.scraper import MTeamAPI, parse_torrent
from services.downloader import add_torrent, get_torrent_info, delete_torrent, get_downloading_count, get_torrent_info_with_tags, get_all_torrents_with_details, get_downloader_total_size, delete_torrents_by_strategy, delete_torrents_by_free_space, get_disk_space_info, check_torrent_unregistered, get_torrent_trackers
from routers.rules import match_torrent
from config import settings, TORRENT_DIR
from utils.logger import scheduler_logger as logger

scheduler = AsyncIOScheduler()

# 到期前提前删除的时间（秒）
EXPIRE_DELETE_ADVANCE_SECONDS = 300  # 5分钟

# 记录任务上次执行时间
last_execution_times = {}


def schedule_precise_delete(history_id: int, torrent_name: str, discount_end_time: datetime, info_hash: str):
    """为单个种子调度精准删种任务
    
    使用 APScheduler 的 date 触发器，在促销到期前 5 分钟执行删除。
    APScheduler 内部使用堆结构管理任务，即使有大量任务也不会阻塞。
    
    Args:
        history_id: 下载历史记录 ID
        torrent_name: 种子名称（用于日志）
        discount_end_time: 促销到期时间
        info_hash: 种子的 info_hash
    """
    # 计算删除时间：到期前 5 分钟
    delete_time = discount_end_time - timedelta(seconds=EXPIRE_DELETE_ADVANCE_SECONDS)
    now = beijing_now()
    
    # 如果删除时间已经过了，跳过调度（让定时检查任务处理）
    if delete_time <= now:
        logger.info(f"种子 {torrent_name} 的删除时间已过，跳过精准调度")
        return
    
    # 使用 history_id 作为 job_id，确保唯一性和可追踪
    job_id = f"precise_delete_{history_id}"
    
    # 检查是否已存在相同任务，避免重复调度
    existing_job = scheduler.get_job(job_id)
    if existing_job:
        logger.debug(f"种子 {torrent_name} 的精准删种任务已存在，跳过")
        return
    
    # 添加一次性任务
    scheduler.add_job(
        execute_precise_delete,
        trigger=DateTrigger(run_date=delete_time),
        id=job_id,
        args=[history_id, torrent_name, info_hash],
        replace_existing=True,
        misfire_grace_time=60  # 允许 60 秒的延迟执行
    )
    
    logger.info(f"已调度精准删种: {torrent_name}, 将在 {delete_time.strftime('%Y-%m-%d %H:%M:%S')} 执行")


async def execute_precise_delete(history_id: int, torrent_name: str, info_hash: str):
    """执行精准删种
    
    这是 APScheduler 调度的回调函数，在促销到期前执行。
    """
    logger.info(f"执行精准删种: {torrent_name}")
    
    db = SessionLocal()
    try:
        # 获取下载历史记录
        record = db.query(DownloadHistory).filter(DownloadHistory.id == history_id).first()
        
        if not record:
            logger.warning(f"精准删种: 找不到历史记录 {history_id}")
            return
        
        # 检查状态，只删除下载中的种子
        downloading_statuses = ["downloading", "pending", "pushing", "queued", "paused"]
        if record.status not in downloading_statuses:
            logger.info(f"精准删种: 种子 {torrent_name} 状态为 {record.status}，跳过删除")
            return
        
        # 获取下载器
        if not record.downloader_id:
            logger.warning(f"精准删种: 种子 {torrent_name} 没有关联下载器")
            return
        
        downloader = db.query(Downloader).filter(Downloader.id == record.downloader_id).first()
        if not downloader:
            logger.warning(f"精准删种: 下载器不存在")
            return
        
        # 获取自动删种设置，检查是否启用
        setting = db.query(SystemSettings).filter(
            SystemSettings.key == "auto_delete_expired"
        ).first()
        
        auto_delete_config = {"enabled": True, "delete_scope": "all", "check_tags": True}
        if setting:
            try:
                auto_delete_config.update(json.loads(setting.value))
            except json.JSONDecodeError:
                pass
        
        if not auto_delete_config.get("enabled", True):
            logger.info(f"精准删种: 自动删种功能已禁用，跳过 {torrent_name}")
            return
        
        # 检查删种范围
        delete_scope = auto_delete_config.get("delete_scope", "all")
        if record.rule_id:
            rule = db.query(FilterRule).filter(FilterRule.id == record.rule_id).first()
            if rule:
                if delete_scope == "normal" and rule.mode == "adult":
                    logger.info(f"精准删种: 跳过成人种子 {torrent_name}")
                    return
                elif delete_scope == "adult" and rule.mode == "normal":
                    logger.info(f"精准删种: 跳过正常种子 {torrent_name}")
                    return
        
        # 检查种子是否还在下载器中
        torrent_info = await get_torrent_info_with_tags(downloader, info_hash)
        
        if torrent_info is None:
            record.status = "expired_deleted"
            logger.info(f"精准删种: 种子 {torrent_name} 已不存在")
            db.commit()
            return
        
        if torrent_info.get("is_completed"):
            record.status = "completed"
            logger.info(f"精准删种: 种子 {torrent_name} 已完成下载")
            db.commit()
            return
        
        # 执行删除
        progress = torrent_info.get("progress", 0)
        logger.info(f"精准删种: 删除种子 {torrent_name} (进度: {progress:.1f}%)")
        
        success = await delete_torrent(downloader, info_hash, delete_files=True)
        
        if success:
            record.status = "expired_deleted"
            logger.info(f"精准删种: 已删除种子 {torrent_name}")
        else:
            logger.warning(f"精准删种: 删除种子失败 {torrent_name}")
        
        db.commit()
        
    except Exception as e:
        logger.error(f"精准删种执行失败 {torrent_name}: {e}")
    finally:
        db.close()


def cancel_precise_delete(history_id: int):
    """取消精准删种任务
    
    当种子下载完成或被手动删除时调用。
    """
    job_id = f"precise_delete_{history_id}"
    try:
        job = scheduler.get_job(job_id)
        if job:
            scheduler.remove_job(job_id)
            logger.debug(f"已取消精准删种任务: {job_id}")
    except Exception as e:
        logger.debug(f"取消精准删种任务失败: {e}")


def get_precise_delete_jobs() -> List[Dict[str, Any]]:
    """获取所有精准删种任务的信息"""
    jobs = []
    for job in scheduler.get_jobs():
        if job.id.startswith("precise_delete_"):
            jobs.append({
                "id": job.id,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "args": job.args
            })
    return jobs


def get_refresh_intervals() -> Dict[str, int]:
    """获取刷新间隔设置"""
    db = SessionLocal()
    try:
        setting = db.query(SystemSettings).filter(
            SystemSettings.key == "refresh_intervals"
        ).first()
        
        # 默认间隔设置
        default_intervals = {
            "account_refresh_interval": 300,  # 5分钟
            "torrent_check_interval": 180,   # 3分钟
            "expired_check_interval": 60     # 1分钟
        }
        
        if setting:
            try:
                intervals = json.loads(setting.value)
                # 合并默认值，确保所有必需的键都存在
                default_intervals.update(intervals)
                return default_intervals
            except json.JSONDecodeError:
                logger.warning("解析刷新间隔设置失败，使用默认值")
                return default_intervals
        
        return default_intervals
    finally:
        db.close()


def get_schedule_control() -> Dict[str, Any]:
    """获取定时运行控制设置"""
    db = SessionLocal()
    try:
        setting = db.query(SystemSettings).filter(
            SystemSettings.key == "schedule_control"
        ).first()
        
        default_settings = {
            "enabled": False,
            "time_ranges": []
        }
        
        if setting:
            try:
                return json.loads(setting.value)
            except json.JSONDecodeError:
                return default_settings
        
        return default_settings
    finally:
        db.close()


def is_task_allowed(task_name: str) -> bool:
    """检查当前时间是否允许执行指定任务
    
    task_name: auto_download, expired_check, account_refresh
    
    优先级规则：如果当前时间匹配多个时间段，取时间范围最小（最具体）的那个
    """
    control = get_schedule_control()
    
    # 如果未启用定时控制，默认允许所有任务
    if not control.get("enabled", False):
        return True
    
    time_ranges = control.get("time_ranges", [])
    if not time_ranges:
        return True
    
    # 获取当前北京时间
    now = beijing_now()
    current_minutes = now.hour * 60 + now.minute
    
    # 找出所有匹配当前时间的时间段
    matched_ranges = []
    
    for time_range in time_ranges:
        start = time_range.get("start", "00:00")
        end = time_range.get("end", "24:00")
        
        # 解析时间
        start_parts = start.split(":")
        end_parts = end.split(":")
        start_minutes = int(start_parts[0]) * 60 + int(start_parts[1])
        end_minutes = int(end_parts[0]) * 60 + int(end_parts[1])
        
        # 处理跨天的情况（如 22:00 - 06:00）
        if start_minutes <= end_minutes:
            # 正常情况
            in_range = start_minutes <= current_minutes < end_minutes
            duration = end_minutes - start_minutes
        else:
            # 跨天情况
            in_range = current_minutes >= start_minutes or current_minutes < end_minutes
            duration = (24 * 60 - start_minutes) + end_minutes
        
        if in_range:
            matched_ranges.append({
                "range": time_range,
                "duration": duration,
                "start": start,
                "end": end
            })
    
    if not matched_ranges:
        # 如果不在任何时间段内，默认允许
        return True
    
    # 按时间范围长度排序，取最小的（最具体的）
    matched_ranges.sort(key=lambda x: x["duration"])
    best_match = matched_ranges[0]
    
    result = best_match["range"].get(task_name, True)
    
    # 调试日志
    logger.debug(f"时间 {now.strftime('%H:%M')} 匹配到 {len(matched_ranges)} 个时间段，"
          f"选择最具体的 {best_match['start']}-{best_match['end']}（{best_match['duration']}分钟），{task_name}={'允许' if result else '禁用'}")
    
    return result


async def refresh_all_accounts():
    """刷新所有账号信息"""
    # 记录执行时间
    last_execution_times["refresh_accounts"] = beijing_now()
    
    # 检查是否允许执行
    if not is_task_allowed("account_refresh"):
        logger.info("账号刷新任务在当前时间段被禁用，跳过")
        return
    
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
                        account.last_login = beijing_now()
                        logger.info(f"刷新账号 {account.username} 成功")
                except Exception as e:
                    logger.error(f"刷新账号 {account.username} 失败: {e}")
        db.commit()
    finally:
        db.close()

async def auto_download_torrents():
    """根据规则自动下载种子"""
    # 记录执行时间
    last_execution_times["auto_download"] = beijing_now()
    
    # 检查是否允许执行
    if not is_task_allowed("auto_download"):
        logger.info("自动下载任务在当前时间段被禁用，跳过")
        return
    
    db = SessionLocal()
    try:
        # 获取所有启用的规则
        rules = db.query(FilterRule).filter(FilterRule.is_enabled == True).all()
        
        for rule in rules:
            account = db.query(Account).filter(Account.id == rule.account_id).first()
            if not account or not account.api_key:
                continue
            
            # 提前检查下载队列限制，避免不必要的网站访问
            if rule.downloader_id and rule.max_downloading:
                downloader = db.query(Downloader).filter(
                    Downloader.id == rule.downloader_id
                ).first()
                
                if downloader:
                    try:
                        current_downloading = await get_downloading_count(downloader)
                        if current_downloading >= rule.max_downloading:
                            logger.info(f"规则 '{rule.name}' 下载队列已满 ({current_downloading}/{rule.max_downloading})，跳过网站访问")
                            continue
                        else:
                            logger.info(f"规则 '{rule.name}' 下载队列状态: {current_downloading}/{rule.max_downloading}，继续检查种子")
                    except Exception as e:
                        logger.error(f"规则 '{rule.name}' 检查下载器 {downloader.name} 队列状态失败: {e}，跳过此规则")
                        continue
                else:
                    logger.warning(f"规则 '{rule.name}' 关联的下载器不存在，跳过")
                    continue
            
            try:
                api = MTeamAPI(account.api_key)
                
                # 构建搜索参数
                discount = None
                if rule.free_only:
                    discount = "FREE"
                elif rule.double_upload:
                    discount = "_2X"
                
                logger.info(f"规则 '{rule.name}' 开始访问网站搜索种子，discount={discount}")
                result = await api.search_torrents(
                    page=1,
                    page_size=50,
                    mode=rule.mode,  # 使用规则的模式（normal 或 adult）
                    categories=rule.categories,
                    discount=discount
                )
                
                if not result["success"]:
                    logger.warning(f"规则 '{rule.name}' 搜索种子失败: {result.get('message', '未知错误')}")
                    continue
                
                torrents = [parse_torrent(t) for t in result["data"].get("data", [])]
                logger.info(f"规则 '{rule.name}' 获取到 {len(torrents)} 个种子")
                
                # 批量查询这些种子在 M-Team 网站的下载历史
                tracker_history = {}
                if torrents:
                    torrent_ids = [t["id"] for t in torrents]
                    history_result = await api.query_tracker_history(torrent_ids)
                    if history_result["success"]:
                        tracker_history = history_result["data"].get("historyMap", {})
                        if tracker_history:
                            logger.info(f"规则 '{rule.name}' 查询到 {len(tracker_history)} 个种子有网站下载历史")
                
                # 本次任务已推送的种子数量（用于精确控制下载数量）
                pushed_count_this_run = 0
                
                # 统计过滤原因
                skip_local_history = 0
                skip_tracker_history = 0
                skip_rule_mismatch = 0
                
                for torrent in torrents:
                    # 检查是否已在本地下载历史中
                    existing = db.query(DownloadHistory).filter(
                        DownloadHistory.account_id == account.id,
                        DownloadHistory.torrent_id == torrent["id"]
                    ).first()
                    
                    if existing:
                        skip_local_history += 1
                        continue
                    
                    # 检查是否在 M-Team 网站有下载历史（曾经下载过）
                    if torrent["id"] in tracker_history:
                        skip_tracker_history += 1
                        continue
                    
                    # 检查是否匹配规则
                    if not match_torrent(torrent, rule):
                        skip_rule_mismatch += 1
                        continue
                    
                    # 检查下载队列限制（在推送前检查，确保不会超过限制）
                    if rule.downloader_id and rule.max_downloading:
                        downloader = db.query(Downloader).filter(
                            Downloader.id == rule.downloader_id
                        ).first()
                        
                        if downloader:
                            current_downloading = await get_downloading_count(downloader)
                            # 检查如果推送这个种子后是否会超过限制
                            # 使用 pushed_count_this_run 跟踪本次任务已推送的数量
                            effective_downloading = current_downloading + pushed_count_this_run
                            if effective_downloading >= rule.max_downloading:
                                logger.info(f"下载队列已满 ({current_downloading}+{pushed_count_this_run}/{rule.max_downloading})，停止处理更多种子")
                                break  # 跳出种子循环，但继续处理下一个规则
                    
                    # 先增加计数，再推送（确保并发安全）
                    pushed_count_this_run += 1
                    
                    logger.info(f"匹配规则 '{rule.name}': {torrent['name']}")
                    
                    # 下载种子文件
                    torrent_content = await api.download_torrent(torrent["id"])
                    if not torrent_content:
                        logger.warning(f"下载种子文件失败: {torrent['name']}")
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
                            logger.info(f"推送到下载器: {bool(info_hash)}, hash: {info_hash}")
                            
                            # 如果推送失败，回退计数
                            if not info_hash:
                                pushed_count_this_run -= 1
                    
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
                            logger.warning(f"解析促销到期时间失败: {e}")
                    
                    # 记录下载历史（包含封面图片）
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
                        discount_end_time=discount_end_time,
                        images=torrent.get("images")  # 保存封面图片 URL
                    )
                    db.add(history)
                    db.commit()
                    
                    # 如果有促销到期时间且推送成功，调度精准删种任务
                    if discount_end_time and info_hash:
                        schedule_precise_delete(
                            history_id=history.id,
                            torrent_name=torrent["name"],
                            discount_end_time=discount_end_time,
                            info_hash=info_hash
                        )
                
                # 输出过滤统计
                logger.info(f"规则 '{rule.name}' 过滤统计: 本地历史={skip_local_history}, 网站历史={skip_tracker_history}, 规则不匹配={skip_rule_mismatch}, 本次推送={pushed_count_this_run}")
                    
            except Exception as e:
                logger.error(f"处理规则 '{rule.name}' 失败: {e}")
                
    finally:
        db.close()


async def check_expired_torrents():
    """检查需要删除的种子：下载中且（促销过期或非免费）的种子
    
    这个功能很重要，因为 PT 网站对分享率要求很高。
    需要删除的情况（仅针对下载中的种子）：
    1. 促销已过期且未完成的种子
    2. 非免费促销（如50%、无优惠）且未完成的种子
    
    做种中的种子不需要删除，因为已经下载完成，不会产生下载量。
    """
    # 记录执行时间
    last_execution_times["check_expired"] = beijing_now()
    
    # 检查是否允许执行
    if not is_task_allowed("expired_check"):
        logger.info("过期检查任务在当前时间段被禁用，跳过")
        return
    
    db = SessionLocal()
    try:
        # 获取自动删种设置
        from models import SystemSettings
        import json
        
        setting = db.query(SystemSettings).filter(
            SystemSettings.key == "auto_delete_expired"
        ).first()
        
        # 默认设置
        auto_delete_config = {
            "enabled": True,
            "delete_scope": "all",  # all, normal, adult
            "check_tags": True
        }
        
        if setting:
            try:
                auto_delete_config.update(json.loads(setting.value))
            except json.JSONDecodeError:
                logger.info(f" 解析自动删种设置失败，使用默认配置")
        
        # 如果禁用了自动删种，直接返回
        if not auto_delete_config.get("enabled", True):
            logger.info(f" 自动删种功能已禁用")
            return
        
        now = beijing_now()
        
        # 免费促销类型列表
        FREE_DISCOUNT_TYPES = ["FREE", "_2X_FREE"]
        
        # 只查找"下载中"状态的记录
        # 下载中的状态包括：downloading, pending, pushing, queued, paused
        downloading_statuses = ["downloading", "pending", "pushing", "queued", "paused"]
        
        all_records = db.query(DownloadHistory).filter(
            DownloadHistory.status.in_(downloading_statuses),
            DownloadHistory.info_hash != None,
            DownloadHistory.downloader_id != None
        ).all()
        
        # 筛选需要删除的记录
        records_to_check = []
        for record in all_records:
            should_check = False
            reason = ""
            
            # 情况1：有促销到期时间且已过期
            if record.discount_end_time and record.discount_end_time < now:
                should_check = True
                reason = "促销已过期"
            
            # 情况2：促销类型不是免费的（非FREE和_2X_FREE）
            elif record.discount_type and record.discount_type not in FREE_DISCOUNT_TYPES:
                should_check = True
                reason = f"非免费促销({record.discount_type})"
            
            if should_check:
                records_to_check.append((record, reason))
        
        logger.info(f" 检查下载中的非免费/过期种子，找到 {len(records_to_check)} 个需要处理")
        logger.info(f" 删种设置: 启用={auto_delete_config['enabled']}, 范围={auto_delete_config['delete_scope']}, 检查标签={auto_delete_config['check_tags']}")
        
        if not records_to_check:
            return
        
        for record, reason in records_to_check:
            # 获取下载器
            downloader = db.query(Downloader).filter(
                Downloader.id == record.downloader_id
            ).first()
            
            if not downloader:
                logger.info(f" 下载器不存在: {record.torrent_name}")
                continue
            
            # 获取关联的规则（可能为空，手动上传的种子没有规则）
            rule = None
            rule_tags = set()
            rule_mode = None
            
            if record.rule_id:
                rule = db.query(FilterRule).filter(FilterRule.id == record.rule_id).first()
                if rule:
                    rule_tags = set(rule.tags) if rule.tags else set()
                    rule_mode = rule.mode
            
            # 根据删种范围设置过滤（仅对有规则的种子生效）
            delete_scope = auto_delete_config.get("delete_scope", "all")
            if rule_mode:
                if delete_scope == "normal" and rule_mode == "adult":
                    logger.info(f" 跳过成人种子（设置为仅删除正常种子）: {record.torrent_name}")
                    continue
                elif delete_scope == "adult" and rule_mode == "normal":
                    logger.info(f" 跳过正常种子（设置为仅删除成人种子）: {record.torrent_name}")
                    continue
            
            try:
                # 获取种子信息（包含标签）
                torrent_info = await get_torrent_info_with_tags(downloader, record.info_hash)
                
                if torrent_info is None:
                    # 种子不存在（可能已被手动删除）
                    record.status = "expired_deleted"
                    logger.info(f" 种子已不存在: {record.torrent_name}")
                    continue
                
                if torrent_info.get("is_completed"):
                    # 已完成，更新状态
                    record.status = "completed"
                    logger.info(f" 种子已完成: {record.torrent_name}")
                    continue
                
                # 检查标签是否匹配（根据设置决定是否检查，仅对有规则的种子生效）
                torrent_tags = set(torrent_info.get("tags", []))
                check_tags = auto_delete_config.get("check_tags", True)
                
                if check_tags and rule_tags and not rule_tags.intersection(torrent_tags):
                    # 种子没有规则指定的标签，跳过删除
                    logger.info(f" 种子标签不匹配规则，跳过删除: {record.torrent_name} (种子标签: {torrent_tags}, 规则标签: {rule_tags})")
                    continue
                
                # 删除种子（原因：促销过期或非免费）
                progress = torrent_info.get("progress", 0)
                mode_info = f"模式: {rule_mode}" if rule_mode else "手动上传"
                logger.info(f" 删除种子: {record.torrent_name} (原因: {reason}, {mode_info}, 进度: {progress:.1f}%)")
                
                success = await delete_torrent(downloader, record.info_hash, delete_files=True)
                
                if success:
                    record.status = "expired_deleted"
                    logger.info(f" 已删除种子: {record.torrent_name}")
                else:
                    logger.info(f" 删除种子失败: {record.torrent_name}")
                    
            except Exception as e:
                logger.info(f" 处理过期种子失败 {record.torrent_name}: {e}")
        
        db.commit()
        
    except Exception as e:
        logger.info(f" 检查过期种子任务失败: {e}")
    finally:
        db.close()


async def check_dynamic_delete():
    """检查动态删种：根据容量阈值自动删除种子"""
    # 记录执行时间
    last_execution_times["dynamic_delete"] = beijing_now()
    
    db = SessionLocal()
    try:
        # 获取自动删种设置
        from models import SystemSettings
        import json
        
        setting = db.query(SystemSettings).filter(
            SystemSettings.key == "auto_delete_expired"
        ).first()
        
        # 默认设置
        auto_delete_config = {
            "enabled": True,
            "delete_scope": "all",
            "check_tags": True,
            "downloader_id": None,
            "enable_dynamic_delete": False,
            "max_capacity_gb": 1000.0,
            "min_capacity_gb": 800.0,
            "delete_strategy": "oldest_first"
        }
        
        if setting:
            try:
                auto_delete_config.update(json.loads(setting.value))
            except json.JSONDecodeError:
                logger.info(f" 解析自动删种设置失败，使用默认配置")
        
        # 如果禁用了动态删种，直接返回
        if not auto_delete_config.get("enable_dynamic_delete", False):
            return
        
        # 动态删种必须指定下载器
        if not auto_delete_config.get("downloader_id"):
            logger.info(f" 动态删种功能已启用，但未指定下载器，跳过")
            return
        
        logger.info(f" 开始检查动态删种，最大容量: {auto_delete_config['max_capacity_gb']} GB，最小容量: {auto_delete_config['min_capacity_gb']} GB")
        
        # 获取指定的下载器
        downloader = db.query(Downloader).filter(
            Downloader.id == auto_delete_config["downloader_id"],
            Downloader.is_active == True
        ).first()
        
        if not downloader:
            logger.info(f" 指定的下载器不存在或未激活: {auto_delete_config['downloader_id']}")
            return
        
        try:
            logger.info(f" 检查下载器: {downloader.name}")
            
            # 获取磁盘空间信息
            disk_info = await get_disk_space_info(downloader)
            if not disk_info or "free_space_gb" not in disk_info:
                logger.info(f" 无法获取下载器 {downloader.name} 的磁盘空间信息")
                return
            
            free_space_gb = disk_info["free_space_gb"]
            # 重命名变量以更清晰地表达含义：
            # trigger_threshold_gb: 当剩余空间低于此值时触发删种
            # target_free_space_gb: 删种后目标剩余空间
            trigger_threshold_gb = auto_delete_config["max_capacity_gb"]
            target_free_space_gb = auto_delete_config["min_capacity_gb"]
            
            logger.info(f" 下载器 {downloader.name} 剩余空间: {free_space_gb:.2f} GB")
            logger.info(f" 触发阈值: {trigger_threshold_gb} GB, 目标剩余空间: {target_free_space_gb} GB")
            
            # 检查是否需要删种：当剩余空间 >= 触发阈值时，不需要删种
            if free_space_gb >= trigger_threshold_gb:
                logger.info(f" 下载器 {downloader.name} 剩余空间充足（>= {trigger_threshold_gb} GB），跳过")
                return
            
            logger.info(f" 下载器 {downloader.name} 剩余空间不足（< {trigger_threshold_gb} GB），开始删种")
            
            # 计算需要释放的空间：目标是让剩余空间达到 target_free_space_gb
            need_to_free_gb = target_free_space_gb - free_space_gb
            
            # 安全检查：如果计算出的需要释放空间为负数或零，说明配置有问题
            if need_to_free_gb <= 0:
                logger.warning(f" 配置异常：目标剩余空间({target_free_space_gb} GB) <= 当前剩余空间({free_space_gb:.2f} GB)，跳过删种")
                return
            
            logger.info(f" 需要释放空间: {need_to_free_gb:.2f} GB")
            
            # 获取所有种子详细信息
            all_torrents = await get_all_torrents_with_details(downloader)
            if not all_torrents:
                logger.info(f" 下载器 {downloader.name} 没有种子")
                return
            
            # 过滤种子（根据删种范围和标签设置）
            filtered_torrents = []
            delete_scope = auto_delete_config.get("delete_scope", "all")
            check_tags = auto_delete_config.get("check_tags", True)
            
            for torrent in all_torrents:
                # 查找对应的下载历史记录
                history_record = db.query(DownloadHistory).filter(
                    DownloadHistory.info_hash == torrent["hash"],
                    DownloadHistory.downloader_id == downloader.id
                ).first()
                
                # 根据删种范围过滤
                if history_record and history_record.rule_id:
                    rule = db.query(FilterRule).filter(FilterRule.id == history_record.rule_id).first()
                    if rule:
                        if delete_scope == "normal" and rule.mode == "adult":
                            continue  # 跳过成人种子
                        elif delete_scope == "adult" and rule.mode == "normal":
                            continue  # 跳过正常种子
                        
                        # 检查标签匹配
                        if check_tags and rule.tags:
                            rule_tags = set(rule.tags)
                            torrent_tags = set(torrent.get("tags", []))
                            if not rule_tags.intersection(torrent_tags):
                                continue  # 标签不匹配，跳过
                
                filtered_torrents.append(torrent)
            
            if not filtered_torrents:
                logger.info(f" 下载器 {downloader.name} 没有符合删除条件的种子")
                return
            
            # 执行删种
            delete_strategy = auto_delete_config.get("delete_strategy", "oldest_first")
            deleted_hashes = await delete_torrents_by_free_space(
                downloader,
                filtered_torrents,
                need_to_free_gb,
                delete_strategy
            )
            
            # 更新下载历史状态
            if deleted_hashes:
                for hash_value in deleted_hashes:
                    history_record = db.query(DownloadHistory).filter(
                        DownloadHistory.info_hash == hash_value,
                        DownloadHistory.downloader_id == downloader.id
                    ).first()
                    if history_record:
                        history_record.status = "dynamic_deleted"
                
                db.commit()
                logger.info(f" 下载器 {downloader.name} 动态删种完成，删除了 {len(deleted_hashes)} 个种子")
            
        except Exception as e:
            logger.info(f" 处理下载器 {downloader.name} 失败: {e}")
        
    except Exception as e:
        logger.info(f" 动态删种任务失败: {e}")
    finally:
        db.close()


async def check_unregistered_torrents():
    """检查并删除被站点删除的种子（Tracker 返回 unregistered）
    
    当种子被站点删除后，Tracker 会返回 "torrent not registered" 等错误消息。
    这个任务会检查所有种子的 Tracker 状态，自动删除已被站点删除的种子。
    """
    # 记录执行时间
    last_execution_times["check_unregistered"] = beijing_now()
    
    db = SessionLocal()
    try:
        # 获取自动删种设置
        from models import SystemSettings
        import json
        
        setting = db.query(SystemSettings).filter(
            SystemSettings.key == "auto_delete_expired"
        ).first()
        
        # 默认设置
        auto_delete_config = {
            "enabled": True,
            "auto_delete_unregistered": False
        }
        
        if setting:
            try:
                auto_delete_config.update(json.loads(setting.value))
            except json.JSONDecodeError:
                logger.warning("解析自动删种设置失败，使用默认配置")
        
        # 如果未启用自动删除未注册种子，直接返回
        if not auto_delete_config.get("auto_delete_unregistered", False):
            return
        
        logger.info("开始检查被站点删除的种子（Tracker unregistered）")
        
        # 获取所有活跃的下载器
        downloaders = db.query(Downloader).filter(Downloader.is_active == True).all()
        
        if not downloaders:
            logger.info("没有活跃的下载器，跳过检查")
            return
        
        total_deleted = 0
        
        for downloader in downloaders:
            try:
                logger.info(f"检查下载器: {downloader.name}")
                
                # 获取该下载器的所有种子
                all_torrents = await get_all_torrents_with_details(downloader)
                
                if not all_torrents:
                    continue
                
                logger.info(f"下载器 {downloader.name} 共有 {len(all_torrents)} 个种子")
                
                for torrent in all_torrents:
                    try:
                        # 检查种子是否被站点删除
                        is_unregistered = await check_torrent_unregistered(downloader, torrent["hash"])
                        
                        if is_unregistered:
                            logger.info(f"发现被站点删除的种子: {torrent['name']}")
                            
                            # 删除种子（包含文件）
                            success = await delete_torrent(downloader, torrent["hash"], delete_files=True)
                            
                            if success:
                                total_deleted += 1
                                logger.info(f"已删除被站点删除的种子: {torrent['name']}")
                                
                                # 更新下载历史状态
                                history_record = db.query(DownloadHistory).filter(
                                    DownloadHistory.info_hash == torrent["hash"],
                                    DownloadHistory.downloader_id == downloader.id
                                ).first()
                                
                                if history_record:
                                    history_record.status = "unregistered_deleted"
                            else:
                                logger.warning(f"删除种子失败: {torrent['name']}")
                    
                    except Exception as e:
                        logger.error(f"检查种子 {torrent['name']} 失败: {e}")
                        continue
                
            except Exception as e:
                logger.error(f"处理下载器 {downloader.name} 失败: {e}")
                continue
        
        db.commit()
        
        if total_deleted > 0:
            logger.info(f"检查完成，共删除 {total_deleted} 个被站点删除的种子")
        else:
            logger.info("检查完成，没有发现被站点删除的种子")
        
    except Exception as e:
        logger.error(f"检查未注册种子任务失败: {e}")
    finally:
        db.close()


async def sync_download_status():
    """定时同步下载历史状态
    
    从下载器获取种子的实际状态，更新到下载历史记录中。
    这样用户可以在历史页面看到种子的实时状态（下载中、已完成、做种中等）。
    """
    # 记录执行时间
    last_execution_times["sync_status"] = beijing_now()
    
    db = SessionLocal()
    try:
        # 获取所有有 info_hash 且状态不是终态的记录
        records = db.query(DownloadHistory).filter(
            DownloadHistory.info_hash != None,
            DownloadHistory.downloader_id != None,
            DownloadHistory.status.notin_(["failed", "expired_deleted", "dynamic_deleted"])
        ).all()
        
        if not records:
            return
        
        updated_count = 0
        
        for record in records:
            downloader = db.query(Downloader).filter(Downloader.id == record.downloader_id).first()
            if not downloader:
                continue
                
            try:
                torrent_info = await get_torrent_info_with_tags(downloader, record.info_hash)
                
                if torrent_info is None:
                    # 种子不存在，可能已被删除
                    if record.status != "deleted":
                        record.status = "deleted"
                        updated_count += 1
                        # 取消精准删种任务
                        cancel_precise_delete(record.id)
                else:
                    # 根据种子状态更新记录状态
                    progress = torrent_info.get("progress", 0)
                    qb_state = torrent_info.get("state", "")
                    
                    new_status = None
                    
                    if progress >= 100 or torrent_info.get("is_completed", False):
                        # 已完成
                        if qb_state in ["uploading", "stalledUP", "queuedUP", "forcedUP"]:
                            new_status = "seeding"  # 做种中
                        else:
                            new_status = "completed"  # 已完成
                        # 种子已完成，取消精准删种任务
                        cancel_precise_delete(record.id)
                    elif progress > 0:
                        # 下载中
                        if qb_state in ["downloading", "stalledDL", "queuedDL", "metaDL", "forcedDL"]:
                            new_status = "downloading"  # 下载中
                        elif qb_state == "pausedDL":
                            new_status = "paused"  # 已暂停
                        else:
                            new_status = "downloading"
                    else:
                        # 未开始或其他状态
                        if qb_state == "pausedDL":
                            new_status = "paused"  # 已暂停
                        elif qb_state in ["queuedDL", "allocating"]:
                            new_status = "queued"  # 队列中
                        else:
                            new_status = "downloading"
                    
                    if new_status and record.status != new_status:
                        record.status = new_status
                        updated_count += 1
                        
            except Exception as e:
                # 静默处理错误，避免日志刷屏
                continue
        
        if updated_count > 0:
            db.commit()
            logger.info(f" 状态同步完成，更新了 {updated_count} 条记录")
        
    except Exception as e:
        logger.info(f" 状态同步任务失败: {e}")
    finally:
        db.close()


def start_scheduler():
    """启动定时任务"""
    intervals = get_refresh_intervals()
    
    # 账号信息刷新任务
    scheduler.add_job(
        refresh_all_accounts,
        IntervalTrigger(seconds=intervals["account_refresh_interval"]),
        id="refresh_accounts",
        replace_existing=True
    )
    
    # 自动下载检查任务
    scheduler.add_job(
        auto_download_torrents,
        IntervalTrigger(seconds=intervals["torrent_check_interval"]),
        id="auto_download",
        replace_existing=True
    )
    
    # 过期种子检查任务
    scheduler.add_job(
        check_expired_torrents,
        IntervalTrigger(seconds=intervals["expired_check_interval"]),
        id="check_expired",
        replace_existing=True
    )
    
    # 动态删种检查任务（每30分钟执行一次）
    scheduler.add_job(
        check_dynamic_delete,
        IntervalTrigger(seconds=1800),  # 30分钟
        id="dynamic_delete",
        replace_existing=True
    )
    
    # 下载状态同步任务（每60秒执行一次）
    scheduler.add_job(
        sync_download_status,
        IntervalTrigger(seconds=60),  # 1分钟
        id="sync_status",
        replace_existing=True
    )
    
    # 检查被站点删除的种子任务（每10分钟执行一次）
    scheduler.add_job(
        check_unregistered_torrents,
        IntervalTrigger(seconds=600),  # 10分钟
        id="check_unregistered",
        replace_existing=True
    )
    
    scheduler.start()
    logger.info(f" 定时任务已启动")
    logger.info(f" 账号刷新间隔: {intervals['account_refresh_interval']}秒")
    logger.info(f" 种子检查间隔: {intervals['torrent_check_interval']}秒")
    logger.info(f" 过期检查间隔: {intervals['expired_check_interval']}秒")
    logger.info(f" 状态同步间隔: 60秒")
    
    # 恢复精准删种任务（服务重启后需要重新调度）
    restore_precise_delete_jobs()


def restore_precise_delete_jobs():
    """恢复精准删种任务
    
    服务重启后，需要为所有下载中且有到期时间的种子重新调度精准删种任务。
    """
    db = SessionLocal()
    try:
        now = beijing_now()
        downloading_statuses = ["downloading", "pending", "pushing", "queued", "paused"]
        
        # 查找所有下载中且有到期时间的记录
        records = db.query(DownloadHistory).filter(
            DownloadHistory.status.in_(downloading_statuses),
            DownloadHistory.info_hash != None,
            DownloadHistory.discount_end_time != None
        ).all()
        
        scheduled_count = 0
        for record in records:
            # 只调度还未到期的种子
            if record.discount_end_time > now:
                schedule_precise_delete(
                    history_id=record.id,
                    torrent_name=record.torrent_name,
                    discount_end_time=record.discount_end_time,
                    info_hash=record.info_hash
                )
                scheduled_count += 1
        
        if scheduled_count > 0:
            logger.info(f"已恢复 {scheduled_count} 个精准删种任务")
    except Exception as e:
        logger.error(f"恢复精准删种任务失败: {e}")
    finally:
        db.close()


def stop_scheduler():
    """停止定时任务"""
    scheduler.shutdown()
    logger.info("定时任务已停止")


async def restart_scheduler_with_new_intervals(new_intervals: Dict[str, int]):
    """使用新的间隔设置重启调度器"""
    logger.info(f" 正在应用新的刷新间隔设置: {new_intervals}")
    
    # 更新现有任务的间隔
    if scheduler.running:
        # 更新账号刷新任务
        if "account_refresh_interval" in new_intervals:
            scheduler.reschedule_job(
                "refresh_accounts",
                trigger=IntervalTrigger(seconds=new_intervals["account_refresh_interval"])
            )
            logger.info(f" 账号刷新间隔已更新为: {new_intervals['account_refresh_interval']}秒")
        
        # 更新种子检查任务
        if "torrent_check_interval" in new_intervals:
            scheduler.reschedule_job(
                "auto_download",
                trigger=IntervalTrigger(seconds=new_intervals["torrent_check_interval"])
            )
            logger.info(f" 种子检查间隔已更新为: {new_intervals['torrent_check_interval']}秒")
        
        # 更新过期检查任务
        if "expired_check_interval" in new_intervals:
            scheduler.reschedule_job(
                "check_expired",
                trigger=IntervalTrigger(seconds=new_intervals["expired_check_interval"])
            )
            logger.info(f" 过期检查间隔已更新为: {new_intervals['expired_check_interval']}秒")
    else:
        logger.warning("调度器未运行，无法更新间隔")


def get_scheduler_status() -> Dict[str, Any]:
    """获取调度器状态信息"""
    if not scheduler.running:
        return {
            "running": False,
            "jobs": [],
            "schedule_control": {
                "enabled": False,
                "current_status": {}
            }
        }
    
    jobs = []
    for job in scheduler.get_jobs():
        next_run = job.next_run_time
        
        # 获取上次执行时间
        last_run = last_execution_times.get(job.id)
        
        jobs.append({
            "id": job.id,
            "name": job.name or job.id,
            "next_run": next_run.isoformat() if next_run else None,
            "last_run": last_run.isoformat() if last_run else None,
            "trigger": str(job.trigger)
        })
    
    # 获取时间段控制状态
    schedule_control = get_schedule_control()
    current_status = {}
    
    if schedule_control.get("enabled", False):
        # 检查当前各任务的允许状态
        current_status = {
            "auto_download": is_task_allowed("auto_download"),
            "expired_check": is_task_allowed("expired_check"),
            "account_refresh": is_task_allowed("account_refresh"),
            "current_time": beijing_now().strftime("%H:%M"),
            "current_time_range": get_current_time_range()
        }
    
    return {
        "running": True,
        "jobs": jobs,
        "current_intervals": get_refresh_intervals(),
        "schedule_control": {
            "enabled": schedule_control.get("enabled", False),
            "current_status": current_status,
            "time_ranges": schedule_control.get("time_ranges", [])
        },
        "precise_delete": {
            "advance_seconds": EXPIRE_DELETE_ADVANCE_SECONDS,
            "pending_jobs": len(get_precise_delete_jobs()),
            "jobs": get_precise_delete_jobs()
        }
    }


def get_current_time_range() -> Dict[str, Any]:
    """获取当前时间所在的时间段信息"""
    control = get_schedule_control()
    
    if not control.get("enabled", False):
        return {"in_range": False, "description": "时间段控制未启用"}
    
    time_ranges = control.get("time_ranges", [])
    if not time_ranges:
        return {"in_range": False, "description": "未配置时间段"}
    
    now = beijing_now()
    current_minutes = now.hour * 60 + now.minute
    
    for i, time_range in enumerate(time_ranges):
        start = time_range.get("start", "00:00")
        end = time_range.get("end", "24:00")
        
        # 解析时间
        start_parts = start.split(":")
        end_parts = end.split(":")
        start_minutes = int(start_parts[0]) * 60 + int(start_parts[1])
        end_minutes = int(end_parts[0]) * 60 + int(end_parts[1])
        
        # 处理跨天的情况
        if start_minutes <= end_minutes:
            in_range = start_minutes <= current_minutes < end_minutes
        else:
            in_range = current_minutes >= start_minutes or current_minutes < end_minutes
        
        if in_range:
            return {
                "in_range": True,
                "range_index": i,
                "start": start,
                "end": end,
                "description": f"当前时间段: {start} - {end}",
                "settings": {
                    "auto_download": time_range.get("auto_download", True),
                    "expired_check": time_range.get("expired_check", True),
                    "account_refresh": time_range.get("account_refresh", True)
                }
            }
    
    return {
        "in_range": False,
        "description": "当前时间不在任何配置的时间段内"
    }
