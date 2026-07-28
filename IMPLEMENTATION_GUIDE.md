# M-Team 收藏种子自动下载功能实现指南

## 功能概述

监控收藏的种子（普通/成人分类），当收藏种子变为免费时自动下载到指定下载器。免费过期前自动删除种子但保留收藏，种子完成做种后自动取消收藏。

## 已完成的修改

### 1. 数据模型修改 (models.py)

#### FilterRule 模型新增字段：
```python
# 规则类型：normal=普通规则, favorite=收藏监控规则
rule_type = Column(String(20), default="normal")  # normal 或 favorite

# 收藏监控配置（仅当 rule_type=favorite 时有效）
monitor_favorites = Column(Boolean, default=False)  # 是否监控收藏
auto_unfavorite_after_seeding = Column(Boolean, default=True)  # 做种后自动取消收藏
```

#### DownloadHistory 模型新增字段：
```python
# 收藏相关
is_favorited = Column(Boolean, default=False)  # 是否已收藏（用于收藏监控规则）
unfavorited_at = Column(DateTime, nullable=True)  # 取消收藏时间
```

### 2. 规则API修改 (routers/rules.py)

更新了 `RuleCreate` 和 `RuleResponse` 模型，添加了收藏监控相关字段。

## 需要继续实现的部分

### 3. M-Team API 收藏管理方法 (services/scraper.py)

需要在 `MTeamAPI` 类中添加以下方法：

```python
async def get_favorites(
    self,
    mode: str = "normal",  # normal 或 adult
    page: int = 1,
    page_size: int = 100
) -> Dict[str, Any]:
    """获取收藏列表"""
    data = {
        "mode": mode,
        "onlyFav": 1,
        "visible": 1,
        "pageNumber": page,
        "pageSize": page_size
    }
    return await self._request("torrent/search", data)

async def add_favorite(self, torrent_id: str) -> Dict[str, Any]:
    """添加收藏"""
    data = {
        "id": str(torrent_id),
        "make": "true"
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(
            f"{self.base_url}/torrent/collection",
            headers={"x-api-key": self.api_key},
            data=data  # 使用 form-data 格式
        )
        result = response.json()
        return {
            "success": result.get("code") == "0",
            "message": result.get("message")
        }

async def remove_favorite(self, torrent_id: str) -> Dict[str, Any]:
    """取消收藏"""
    data = {
        "id": str(torrent_id),
        "make": "false"
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(
            f"{self.base_url}/torrent/collection",
            headers={"x-api-key": self.api_key},
            data=data  # 使用 form-data 格式
        )
        result = response.json()
        return {
            "success": result.get("code") == "0",
            "message": result.get("message")
        }
```

### 4. 收藏监控调度任务 (services/scheduler.py)

需要添加新的调度任务：

```python
async def monitor_favorite_torrents():
    """监控收藏种子，检测免费促销并自动下载"""
    last_execution_times["monitor_favorites"] = beijing_now()

    # 检查是否允许执行
    if not is_task_allowed("auto_download"):
        logger.info("收藏监控任务在当前时间段被禁用，跳过")
        return

    db = SessionLocal()
    try:
        # 获取所有启用的收藏监控规则
        rules = db.query(FilterRule).filter(
            FilterRule.is_enabled == True,
            FilterRule.rule_type == "favorite",
            FilterRule.monitor_favorites == True
        ).all()

        for rule in rules:
            account = db.query(Account).filter(Account.id == rule.account_id).first()
            if not account or not account.api_key:
                continue

            # 检查下载队列限制
            if rule.downloader_id and rule.max_downloading:
                downloader = db.query(Downloader).filter(
                    Downloader.id == rule.downloader_id
                ).first()

                if downloader:
                    try:
                        current_downloading = await get_downloading_count(downloader)
                        if current_downloading >= rule.max_downloading:
                            logger.info(f"收藏监控规则 '{rule.name}' 下载队列已满 ({current_downloading}/{rule.max_downloading})，跳过")
                            continue
                    except Exception as e:
                        logger.error(f"检查下载器队列失败: {e}")
                        continue

            try:
                api = MTeamAPI(account.api_key)

                # 获取收藏列表
                logger.info(f"收藏监控规则 '{rule.name}' 开始检查收藏，模式={rule.mode}")
                result = await api.get_favorites(mode=rule.mode, page=1, page_size=100)

                if not result["success"]:
                    logger.warning(f"获取收藏列表失败: {result.get('error')}")
                    continue

                favorites = [parse_torrent(t) for t in result["data"].get("data", [])]
                logger.info(f"收藏监控规则 '{rule.name}' 获取到 {len(favorites)} 个收藏种子")

                for torrent in favorites:
                    # 检查是否已在本地下载历史中
                    existing = db.query(DownloadHistory).filter(
                        DownloadHistory.account_id == account.id,
                        DownloadHistory.torrent_id == torrent["id"]
                    ).first()

                    if existing:
                        continue

                    # 检查是否为免费种子
                    if not torrent.get("is_free"):
                        continue

                    # 检查是否匹配其他筛选条件
                    if not match_torrent(torrent, rule):
                        continue

                    # 检查促销到期时间
                    if torrent.get("discount_end_time"):
                        try:
                            ts = torrent["discount_end_time"]
                            if isinstance(ts, (int, float)):
                                expire_time = datetime.fromtimestamp(ts / 1000 if ts > 1e10 else ts)
                            else:
                                expire_time = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))

                            if expire_time:
                                now = beijing_now()
                                remaining_seconds = (expire_time - now).total_seconds()
                                if remaining_seconds < 600:  # 少于10分钟
                                    logger.info(f"跳过收藏种子 {torrent['name']}: 促销仅剩 {remaining_seconds:.0f} 秒")
                                    continue
                        except Exception as e:
                            logger.debug(f"检查促销到期时间失败: {e}")

                    # 检查下载队列
                    if rule.downloader_id and rule.max_downloading:
                        downloader = db.query(Downloader).filter(
                            Downloader.id == rule.downloader_id
                        ).first()
                        if downloader:
                            current_downloading = await get_downloading_count(downloader)
                            if current_downloading >= rule.max_downloading:
                                logger.info(f"下载队列已满，停止处理更多收藏种子")
                                break

                    logger.info(f"收藏监控匹配: {torrent['name']} (免费)")

                    # 下载种子文件
                    torrent_content = await api.download_torrent(torrent["id"])
                    if not torrent_content:
                        logger.warning(f"下载种子文件失败: {torrent['name']}")
                        continue

                    # 保存种子文件
                    from config import TORRENT_DIR
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
                            from services.downloader import add_torrent
                            info_hash = await add_torrent(
                                downloader,
                                str(torrent_path),
                                rule.save_path,
                                rule.tags
                            )
                            status = "pushing" if info_hash else "push_failed"
                            logger.info(f"推送到下载器: {bool(info_hash)}, hash: {info_hash}")

                    # 解析促销到期时间
                    discount_end_time = None
                    if torrent.get("discount_end_time"):
                        try:
                            ts = torrent["discount_end_time"]
                            if isinstance(ts, (int, float)):
                                discount_end_time = datetime.fromtimestamp(ts / 1000 if ts > 1e10 else ts)
                            elif isinstance(ts, str):
                                discount_end_time = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                        except Exception as e:
                            logger.warning(f"解析促销到期时间失败: {e}")

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
                        discount_end_time=discount_end_time,
                        images=torrent.get("images"),
                        is_favorited=True  # 标记为收藏种子
                    )
                    db.add(history)
                    db.commit()

                    # 调度精准删种任务
                    if discount_end_time and info_hash:
                        schedule_precise_delete(
                            history_id=history.id,
                            torrent_name=torrent["name"],
                            discount_end_time=discount_end_time,
                            info_hash=info_hash
                        )

            except Exception as e:
                logger.error(f"处理收藏监控规则 '{rule.name}' 失败: {e}")

    finally:
        db.close()
```

### 5. 做种后自动取消收藏 (services/scheduler.py)

在 `sync_download_status()` 函数中添加逻辑：

```python
async def sync_download_status():
    """定时同步下载历史状态（包含自动取消收藏逻辑）"""
    last_execution_times["sync_status"] = beijing_now()

    db = SessionLocal()
    try:
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
                    if record.status != "deleted":
                        record.status = "deleted"
                        updated_count += 1
                        cancel_precise_delete(record.id)
                else:
                    progress = torrent_info.get("progress", 0)
                    qb_state = torrent_info.get("state", "")

                    new_status = None

                    if progress >= 100 or torrent_info.get("is_completed", False):
                        # 已完成
                        if qb_state in ["uploading", "stalledUP", "queuedUP", "forcedUP"]:
                            new_status = "seeding"  # 做种中

                            # ⭐ 新增：如果是收藏种子且规则设置了自动取消收藏
                            if record.is_favorited and record.rule_id and not record.unfavorited_at:
                                rule = db.query(FilterRule).filter(FilterRule.id == record.rule_id).first()
                                if rule and rule.rule_type == "favorite" and rule.auto_unfavorite_after_seeding:
                                    # 获取账号API密钥
                                    account = db.query(Account).filter(Account.id == record.account_id).first()
                                    if account and account.api_key:
                                        try:
                                            from services.scraper import MTeamAPI
                                            api = MTeamAPI(account.api_key)
                                            result = await api.remove_favorite(record.torrent_id)
                                            if result["success"]:
                                                record.unfavorited_at = beijing_now()
                                                logger.info(f"自动取消收藏: {record.torrent_name} (已完成做种)")
                                            else:
                                                logger.warning(f"取消收藏失败: {record.torrent_name}, {result.get('message')}")
                                        except Exception as e:
                                            logger.error(f"取消收藏异常: {record.torrent_name}, {e}")
                        else:
                            new_status = "completed"
                        cancel_precise_delete(record.id)
                    elif progress > 0:
                        if qb_state in ["downloading", "stalledDL", "queuedDL", "metaDL", "forcedDL"]:
                            new_status = "downloading"
                        elif qb_state == "pausedDL":
                            new_status = "paused"
                        else:
                            new_status = "downloading"
                    else:
                        if qb_state == "pausedDL":
                            new_status = "paused"
                        elif qb_state in ["queuedDL", "allocating"]:
                            new_status = "queued"
                        else:
                            new_status = "downloading"

                    if new_status and record.status != new_status:
                        record.status = new_status
                        updated_count += 1

            except Exception as e:
                continue

        if updated_count > 0:
            db.commit()
            logger.info(f"状态同步完成，更新了 {updated_count} 条记录")

    except Exception as e:
        logger.error(f"状态同步任务失败: {e}")
    finally:
        db.close()
```

### 6. 注册调度任务 (services/scheduler.py)

在 `start_scheduler()` 函数中添加：

```python
def start_scheduler():
    """启动定时任务"""
    intervals = get_refresh_intervals()

    # ... 现有任务 ...

    # 收藏监控任务（每5分钟执行一次）
    scheduler.add_job(
        monitor_favorite_torrents,
        IntervalTrigger(seconds=300),  # 5分钟
        id="monitor_favorites",
        replace_existing=True
    )

    scheduler.start()
    logger.info("定时任务已启动")
    logger.info(f"收藏监控间隔: 300秒")
```

## 数据库迁移

需要创建数据库迁移脚本来添加新字段：

```bash
# 使用 Alembic 创建迁移
alembic revision --autogenerate -m "add_favorite_monitoring_fields"
alembic upgrade head
```

## 使用示例

### 创建收藏监控规则

```python
POST /api/rules/

{
  "account_id": 1,
  "name": "普通收藏监控",
  "is_enabled": true,
  "mode": "normal",
  "rule_type": "favorite",  // 关键：设置为收藏监控类型
  "monitor_favorites": true,  // 启用收藏监控
  "auto_unfavorite_after_seeding": true,  // 做种后自动取消收藏
  "free_only": true,  // 只监控免费种子
  "min_size": 1.0,  // 可选：最小1GB
  "max_size": 50.0,  // 可选：最大50GB
  "downloader_id": 1,
  "save_path": "/downloads/favorites",
  "tags": ["favorite", "auto"],
  "max_downloading": 5
}
```

### 成人分类收藏监控

```python
POST /api/rules/

{
  "account_id": 1,
  "name": "成人收藏监控",
  "is_enabled": true,
  "mode": "adult",  // 成人分类
  "rule_type": "favorite",
  "monitor_favorites": true,
  "auto_unfavorite_after_seeding": true,
  "free_only": true,
  "downloader_id": 1,
  "save_path": "/downloads/adult-favorites",
  "tags": ["adult", "favorite"],
  "max_downloading": 3
}
```

## 工作流程

1. **监控阶段**：每5分钟执行一次收藏监控任务
   - 获取启用的收藏监控规则
   - 调用M-Team API获取收藏列表
   - 检查收藏种子是否变为免费
   - 匹配其他筛选条件（大小、做种数等）

2. **下载阶段**：发现免费收藏种子时
   - 检查下载队列是否已满
   - 检查促销到期时间（少于10分钟则跳过）
   - 下载种子文件并推送到下载器
   - 记录下载历史并标记 `is_favorited=True`
   - 调度精准删种任务

3. **删种阶段**：促销到期前5分钟
   - 精准删种任务自动触发
   - 删除未完成的种子（保留收藏）
   - 更新状态为 `expired_deleted`

4. **取消收藏阶段**：种子完成做种后
   - 状态同步任务检测到 `status=seeding`
   - 如果规则设置了 `auto_unfavorite_after_seeding=true`
   - 调用M-Team API取消收藏
   - 记录取消收藏时间 `unfavorited_at`

## 注意事项

1. **API速率限制**：收藏监控每5分钟执行一次，注意M-Team API的速率限制
2. **下载队列管理**：设置合理的 `max_downloading` 避免队列过载
3. **促销到期判断**：少于10分钟的促销种子会被跳过
4. **取消收藏时机**：只有在种子状态变为 `seeding`（做种中）时才会取消收藏
5. **数据库索引**：确保 `is_favorited` 和 `unfavorited_at` 字段有适当的索引

## 测试建议

1. 测试收藏监控规则的创建和更新
2. 手动添加一些免费收藏种子，验证自动下载
3. 测试促销到期前的自动删种
4. 测试做种完成后的自动取消收藏
5. 测试下载队列限制是否生效
6. 测试普通和成人分类的独立监控

## 后续优化

1. 添加收藏监控统计（成功/失败/跳过数量）
2. 添加取消收藏失败重试机制
3. 支持分页获取大量收藏（100+）
4. 添加收藏变化通知（新增免费收藏时发送通知）
5. 优化API调用频率，减少网络请求
