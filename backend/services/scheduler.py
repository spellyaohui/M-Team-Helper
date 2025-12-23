from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session
import json

from database import SessionLocal
from models import Account, FilterRule, DownloadHistory, Downloader, SystemSettings, beijing_now
from services.scraper import MTeamAPI, parse_torrent
from services.downloader import add_torrent, get_torrent_info, delete_torrent, get_downloading_count, get_torrent_info_with_tags, get_all_torrents_with_details, get_downloader_total_size, delete_torrents_by_strategy, delete_torrents_by_free_space, get_disk_space_info
from routers.rules import match_torrent
from config import settings, TORRENT_DIR

scheduler = AsyncIOScheduler()

# 记录任务上次执行时间
last_execution_times = {}

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
                print("[Scheduler] 解析刷新间隔设置失败，使用默认值")
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
    current_time = now.strftime("%H:%M")
    current_minutes = now.hour * 60 + now.minute
    
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
        else:
            # 跨天情况
            in_range = current_minutes >= start_minutes or current_minutes < end_minutes
        
        if in_range:
            # 在这个时间段内，检查任务是否允许
            return time_range.get(task_name, True)
    
    # 如果不在任何时间段内，默认允许
    return True


async def refresh_all_accounts():
    """刷新所有账号信息"""
    # 记录执行时间
    last_execution_times["refresh_accounts"] = beijing_now()
    
    # 检查是否允许执行
    if not is_task_allowed("account_refresh"):
        print("[Scheduler] 账号刷新任务在当前时间段被禁用，跳过")
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
                        print(f"[Scheduler] 刷新账号 {account.username} 成功")
                except Exception as e:
                    print(f"[Scheduler] 刷新账号 {account.username} 失败: {e}")
        db.commit()
    finally:
        db.close()

async def auto_download_torrents():
    """根据规则自动下载种子"""
    # 记录执行时间
    last_execution_times["auto_download"] = beijing_now()
    
    # 检查是否允许执行
    if not is_task_allowed("auto_download"):
        print("[Scheduler] 自动下载任务在当前时间段被禁用，跳过")
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
                            print(f"[Scheduler] 规则 '{rule.name}' 下载队列已满 ({current_downloading}/{rule.max_downloading})，跳过网站访问")
                            continue
                        else:
                            print(f"[Scheduler] 规则 '{rule.name}' 下载队列状态: {current_downloading}/{rule.max_downloading}，继续检查种子")
                    except Exception as e:
                        print(f"[Scheduler] 检查下载器 {downloader.name} 队列状态失败: {e}")
                        continue
                else:
                    print(f"[Scheduler] 规则 '{rule.name}' 关联的下载器不存在，跳过")
                    continue
            
            try:
                api = MTeamAPI(account.api_key)
                
                # 构建搜索参数
                discount = None
                if rule.free_only:
                    discount = "FREE"
                elif rule.double_upload:
                    discount = "_2X"
                
                print(f"[Scheduler] 规则 '{rule.name}' 开始访问网站搜索种子")
                result = await api.search_torrents(
                    page=1,
                    page_size=50,
                    mode=rule.mode,  # 使用规则的模式（normal 或 adult）
                    categories=rule.categories,
                    discount=discount
                )
                
                if not result["success"]:
                    print(f"[Scheduler] 规则 '{rule.name}' 搜索种子失败")
                    continue
                
                torrents = [parse_torrent(t) for t in result["data"].get("data", [])]
                print(f"[Scheduler] 规则 '{rule.name}' 获取到 {len(torrents)} 个种子")
                
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
                    
                    # 再次检查下载队列限制（防止在处理过程中队列状态发生变化）
                    if rule.downloader_id and rule.max_downloading:
                        downloader = db.query(Downloader).filter(
                            Downloader.id == rule.downloader_id
                        ).first()
                        
                        if downloader:
                            current_downloading = await get_downloading_count(downloader)
                            if current_downloading >= rule.max_downloading:
                                print(f"[Scheduler] 下载队列已满 ({current_downloading}/{rule.max_downloading})，停止处理更多种子")
                                break  # 跳出种子循环，但继续处理下一个规则
                    
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
        print("[Scheduler] 过期检查任务在当前时间段被禁用，跳过")
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
                print(f"[Scheduler] 解析自动删种设置失败，使用默认配置")
        
        # 如果禁用了自动删种，直接返回
        if not auto_delete_config.get("enabled", True):
            print(f"[Scheduler] 自动删种功能已禁用")
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
        
        print(f"[Scheduler] 检查下载中的非免费/过期种子，找到 {len(records_to_check)} 个需要处理")
        print(f"[Scheduler] 删种设置: 启用={auto_delete_config['enabled']}, 范围={auto_delete_config['delete_scope']}, 检查标签={auto_delete_config['check_tags']}")
        
        if not records_to_check:
            return
        
        for record, reason in records_to_check:
            # 获取下载器
            downloader = db.query(Downloader).filter(
                Downloader.id == record.downloader_id
            ).first()
            
            if not downloader:
                print(f"[Scheduler] 下载器不存在: {record.torrent_name}")
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
                    print(f"[Scheduler] 跳过成人种子（设置为仅删除正常种子）: {record.torrent_name}")
                    continue
                elif delete_scope == "adult" and rule_mode == "normal":
                    print(f"[Scheduler] 跳过正常种子（设置为仅删除成人种子）: {record.torrent_name}")
                    continue
            
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
                
                # 检查标签是否匹配（根据设置决定是否检查，仅对有规则的种子生效）
                torrent_tags = set(torrent_info.get("tags", []))
                check_tags = auto_delete_config.get("check_tags", True)
                
                if check_tags and rule_tags and not rule_tags.intersection(torrent_tags):
                    # 种子没有规则指定的标签，跳过删除
                    print(f"[Scheduler] 种子标签不匹配规则，跳过删除: {record.torrent_name} (种子标签: {torrent_tags}, 规则标签: {rule_tags})")
                    continue
                
                # 删除种子（原因：促销过期或非免费）
                progress = torrent_info.get("progress", 0)
                mode_info = f"模式: {rule_mode}" if rule_mode else "手动上传"
                print(f"[Scheduler] 删除种子: {record.torrent_name} (原因: {reason}, {mode_info}, 进度: {progress:.1f}%)")
                
                success = await delete_torrent(downloader, record.info_hash, delete_files=True)
                
                if success:
                    record.status = "expired_deleted"
                    print(f"[Scheduler] 已删除种子: {record.torrent_name}")
                else:
                    print(f"[Scheduler] 删除种子失败: {record.torrent_name}")
                    
            except Exception as e:
                print(f"[Scheduler] 处理过期种子失败 {record.torrent_name}: {e}")
        
        db.commit()
        
    except Exception as e:
        print(f"[Scheduler] 检查过期种子任务失败: {e}")
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
                print(f"[DynamicDelete] 解析自动删种设置失败，使用默认配置")
        
        # 如果禁用了动态删种，直接返回
        if not auto_delete_config.get("enable_dynamic_delete", False):
            return
        
        # 动态删种必须指定下载器
        if not auto_delete_config.get("downloader_id"):
            print(f"[DynamicDelete] 动态删种功能已启用，但未指定下载器，跳过")
            return
        
        print(f"[DynamicDelete] 开始检查动态删种，最大容量: {auto_delete_config['max_capacity_gb']} GB，最小容量: {auto_delete_config['min_capacity_gb']} GB")
        
        # 获取指定的下载器
        downloader = db.query(Downloader).filter(
            Downloader.id == auto_delete_config["downloader_id"],
            Downloader.is_active == True
        ).first()
        
        if not downloader:
            print(f"[DynamicDelete] 指定的下载器不存在或未激活: {auto_delete_config['downloader_id']}")
            return
        
        try:
            print(f"[DynamicDelete] 检查下载器: {downloader.name}")
            
            # 获取磁盘空间信息
            disk_info = await get_disk_space_info(downloader)
            if not disk_info or "free_space_gb" not in disk_info:
                print(f"[DynamicDelete] 无法获取下载器 {downloader.name} 的磁盘空间信息")
                return
            
            free_space_gb = disk_info["free_space_gb"]
            max_capacity_gb = auto_delete_config["max_capacity_gb"]
            min_capacity_gb = auto_delete_config["min_capacity_gb"]
            
            print(f"[DynamicDelete] 下载器 {downloader.name} 剩余空间: {free_space_gb:.2f} GB")
            print(f"[DynamicDelete] 容量阈值: 最大 {max_capacity_gb} GB, 最小 {min_capacity_gb} GB")
            
            # 检查是否低于最大容量阈值（剩余空间不足）
            if free_space_gb >= max_capacity_gb:
                print(f"[DynamicDelete] 下载器 {downloader.name} 剩余空间充足，跳过")
                return
            
            print(f"[DynamicDelete] 下载器 {downloader.name} 剩余空间不足，开始删种")
            
            # 计算需要释放的空间
            need_to_free_gb = min_capacity_gb - free_space_gb
            print(f"[DynamicDelete] 需要释放空间: {need_to_free_gb:.2f} GB")
            
            # 获取所有种子详细信息
            all_torrents = await get_all_torrents_with_details(downloader)
            if not all_torrents:
                print(f"[DynamicDelete] 下载器 {downloader.name} 没有种子")
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
                print(f"[DynamicDelete] 下载器 {downloader.name} 没有符合删除条件的种子")
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
                print(f"[DynamicDelete] 下载器 {downloader.name} 动态删种完成，删除了 {len(deleted_hashes)} 个种子")
            
        except Exception as e:
            print(f"[DynamicDelete] 处理下载器 {downloader.name} 失败: {e}")
        
    except Exception as e:
        print(f"[DynamicDelete] 动态删种任务失败: {e}")
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
    
    scheduler.start()
    print(f"[Scheduler] 定时任务已启动")
    print(f"[Scheduler] 账号刷新间隔: {intervals['account_refresh_interval']}秒")
    print(f"[Scheduler] 种子检查间隔: {intervals['torrent_check_interval']}秒")
    print(f"[Scheduler] 过期检查间隔: {intervals['expired_check_interval']}秒")


def stop_scheduler():
    """停止定时任务"""
    scheduler.shutdown()
    print("[Scheduler] 定时任务已停止")


async def restart_scheduler_with_new_intervals(new_intervals: Dict[str, int]):
    """使用新的间隔设置重启调度器"""
    print(f"[Scheduler] 正在应用新的刷新间隔设置: {new_intervals}")
    
    # 更新现有任务的间隔
    if scheduler.running:
        # 更新账号刷新任务
        if "account_refresh_interval" in new_intervals:
            scheduler.modify_job(
                "refresh_accounts",
                trigger=IntervalTrigger(seconds=new_intervals["account_refresh_interval"])
            )
            print(f"[Scheduler] 账号刷新间隔已更新为: {new_intervals['account_refresh_interval']}秒")
        
        # 更新种子检查任务
        if "torrent_check_interval" in new_intervals:
            scheduler.modify_job(
                "auto_download",
                trigger=IntervalTrigger(seconds=new_intervals["torrent_check_interval"])
            )
            print(f"[Scheduler] 种子检查间隔已更新为: {new_intervals['torrent_check_interval']}秒")
        
        # 更新过期检查任务
        if "expired_check_interval" in new_intervals:
            scheduler.modify_job(
                "check_expired",
                trigger=IntervalTrigger(seconds=new_intervals["expired_check_interval"])
            )
            print(f"[Scheduler] 过期检查间隔已更新为: {new_intervals['expired_check_interval']}秒")
    else:
        print("[Scheduler] 调度器未运行，无法更新间隔")


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
