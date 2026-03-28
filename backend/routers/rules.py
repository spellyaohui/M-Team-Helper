from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import json

from database import get_db
from models import FilterRule, Account, Downloader

router = APIRouter(prefix="/rules", tags=["筛选规则"])

class RuleCreate(BaseModel):
    account_id: int
    name: str
    is_enabled: bool = True
    mode: str = "normal"  # normal 或 adult
    rule_type: str = "normal"  # normal=普通规则, favorite=收藏监控规则
    free_only: bool = False
    double_upload: bool = False
    min_size: Optional[float] = None  # GB
    max_size: Optional[float] = None  # GB
    min_seeders: Optional[int] = None
    max_seeders: Optional[int] = None
    min_leechers: Optional[int] = None
    max_leechers: Optional[int] = None
    categories: Optional[List[str]] = None
    keywords: Optional[str] = None
    exclude_keywords: Optional[str] = None
    max_publish_hours: Optional[int] = None  # 最大发布时间（小时）
    monitor_favorites: bool = False  # 是否监控收藏
    auto_unfavorite_after_seeding: bool = True  # 做种后自动取消收藏
    downloader_id: Optional[int] = None
    save_path: Optional[str] = None
    tags: Optional[List[str]] = None  # 下载时添加的标签
    max_downloading: Optional[int] = None  # 最大同时下载数
    download_limit_kbps: Optional[int] = None
    upload_limit_kbps: Optional[int] = None
    sort_order: Optional[int] = None  # 规则排序（数字越小越靠前）

class RuleResponse(BaseModel):
    id: int
    account_id: int
    name: str
    is_enabled: bool
    mode: str
    rule_type: str
    free_only: bool
    double_upload: bool
    min_size: Optional[float]
    max_size: Optional[float]
    min_seeders: Optional[int]
    max_seeders: Optional[int]
    min_leechers: Optional[int]
    max_leechers: Optional[int]
    categories: Optional[List[str]]
    keywords: Optional[str]
    exclude_keywords: Optional[str]
    max_publish_hours: Optional[int]
    monitor_favorites: bool
    auto_unfavorite_after_seeding: bool
    downloader_id: Optional[int]
    save_path: Optional[str]
    tags: Optional[List[str]]
    max_downloading: Optional[int]
    download_limit_kbps: Optional[int]
    upload_limit_kbps: Optional[int]
    sort_order: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True

@router.get("/", response_model=List[RuleResponse])
async def list_rules(
    account_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """获取所有规则"""
    query = db.query(FilterRule)
    if account_id:
        query = query.filter(FilterRule.account_id == account_id)
    query = query.order_by(
        func.coalesce(FilterRule.sort_order, 1000000),
        FilterRule.id.asc()
    )
    return query.all()

@router.post("/", response_model=RuleResponse)
async def create_rule(rule: RuleCreate, db: Session = Depends(get_db)):
    """创建筛选规则"""
    # 验证账号存在
    account = db.query(Account).filter(Account.id == rule.account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")
    
    # 验证下载器存在
    if rule.downloader_id:
        downloader = db.query(Downloader).filter(Downloader.id == rule.downloader_id).first()
        if not downloader:
            raise HTTPException(status_code=404, detail="下载器不存在")
    
    sort_order = rule.sort_order
    if sort_order is None:
        max_order = db.query(func.max(FilterRule.sort_order)).scalar()
        sort_order = (max_order or 0) + 1

    db_rule = FilterRule(
        account_id=rule.account_id,
        name=rule.name,
        is_enabled=rule.is_enabled,
        mode=rule.mode,
        rule_type=rule.rule_type,
        free_only=rule.free_only,
        double_upload=rule.double_upload,
        min_size=rule.min_size,
        max_size=rule.max_size,
        min_seeders=rule.min_seeders,
        max_seeders=rule.max_seeders,
        min_leechers=rule.min_leechers,
        max_leechers=rule.max_leechers,
        categories=rule.categories,
        keywords=rule.keywords,
        exclude_keywords=rule.exclude_keywords,
        max_publish_hours=rule.max_publish_hours,
        monitor_favorites=rule.monitor_favorites,
        auto_unfavorite_after_seeding=rule.auto_unfavorite_after_seeding,
        downloader_id=rule.downloader_id,
        save_path=rule.save_path,
        tags=rule.tags,
        max_downloading=rule.max_downloading,
        download_limit_kbps=rule.download_limit_kbps,
        upload_limit_kbps=rule.upload_limit_kbps,
        sort_order=sort_order
    )
    db.add(db_rule)
    db.commit()
    db.refresh(db_rule)
    return db_rule

@router.get("/{rule_id}", response_model=RuleResponse)
async def get_rule(rule_id: int, db: Session = Depends(get_db)):
    """获取单个规则"""
    rule = db.query(FilterRule).filter(FilterRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    return rule

@router.put("/{rule_id}", response_model=RuleResponse)
async def update_rule(rule_id: int, rule: RuleCreate, db: Session = Depends(get_db)):
    """更新规则"""
    db_rule = db.query(FilterRule).filter(FilterRule.id == rule_id).first()
    if not db_rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    
    for key, value in rule.model_dump().items():
        if key == "sort_order" and value is None:
            continue
        setattr(db_rule, key, value)
    
    db.commit()
    db.refresh(db_rule)
    return db_rule

@router.delete("/{rule_id}")
async def delete_rule(rule_id: int, db: Session = Depends(get_db)):
    """删除规则"""
    rule = db.query(FilterRule).filter(FilterRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    
    db.delete(rule)
    db.commit()
    return {"success": True, "message": "删除成功"}

@router.post("/{rule_id}/toggle")
async def toggle_rule(rule_id: int, db: Session = Depends(get_db)):
    """启用/禁用规则"""
    rule = db.query(FilterRule).filter(FilterRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    
    rule.is_enabled = not rule.is_enabled
    db.commit()
    return {"success": True, "is_enabled": rule.is_enabled}


def match_torrent(torrent: dict, rule: FilterRule, debug: bool = False) -> bool:
    """检查种子是否匹配规则
    
    Args:
        torrent: 种子信息字典
        rule: 筛选规则
        debug: 是否输出调试信息
    """
    from datetime import datetime, timezone, timedelta
    from models import beijing_now
    
    # 免费检查
    if rule.free_only and not torrent.get("is_free"):
        if debug:
            print(f"  不匹配: 非免费 (is_free={torrent.get('is_free')})")
        return False
    
    # 2x上传检查
    if rule.double_upload and not torrent.get("is_2x"):
        if debug:
            print(f"  不匹配: 非2x上传 (is_2x={torrent.get('is_2x')})")
        return False
    
    # 大小检查 (GB)
    size_gb = torrent.get("size_gb", 0)
    if rule.min_size and size_gb < rule.min_size:
        if debug:
            print(f"  不匹配: 大小太小 ({size_gb} < {rule.min_size})")
        return False
    if rule.max_size and size_gb > rule.max_size:
        if debug:
            print(f"  不匹配: 大小太大 ({size_gb} > {rule.max_size})")
        return False
    
    # 做种数检查
    seeders = torrent.get("seeders", 0)
    if rule.min_seeders and seeders < rule.min_seeders:
        if debug:
            print(f"  不匹配: 做种数太少 ({seeders} < {rule.min_seeders})")
        return False
    if rule.max_seeders and seeders > rule.max_seeders:
        if debug:
            print(f"  不匹配: 做种数太多 ({seeders} > {rule.max_seeders})")
        return False
    
    # 下载用户数检查
    leechers = torrent.get("leechers", 0)
    if rule.min_leechers and leechers < rule.min_leechers:
        if debug:
            print(f"  不匹配: 下载用户数太少 ({leechers} < {rule.min_leechers})")
        return False
    if rule.max_leechers and leechers > rule.max_leechers:
        if debug:
            print(f"  不匹配: 下载用户数太多 ({leechers} > {rule.max_leechers})")
        return False
    
    # 发布时间检查
    if rule.max_publish_hours:
        created_date = torrent.get("created_date")
        if created_date:
            try:
                # 解析发布时间
                if isinstance(created_date, str):
                    # ISO 格式字符串
                    publish_time = datetime.fromisoformat(created_date.replace("Z", "+00:00"))
                    # 转换为北京时间（无时区）
                    if publish_time.tzinfo:
                        publish_time = publish_time.astimezone(timezone(timedelta(hours=8))).replace(tzinfo=None)
                elif isinstance(created_date, (int, float)):
                    # 时间戳（毫秒或秒）
                    ts = created_date / 1000 if created_date > 1e10 else created_date
                    publish_time = datetime.fromtimestamp(ts)
                else:
                    publish_time = None
                
                if publish_time:
                    now = beijing_now()
                    hours_ago = (now - publish_time).total_seconds() / 3600
                    if hours_ago > rule.max_publish_hours:
                        if debug:
                            print(f"  不匹配: 发布时间超过限制 ({hours_ago:.1f}h > {rule.max_publish_hours}h)")
                        return False
            except Exception as e:
                if debug:
                    print(f"  警告: 解析发布时间失败: {e}")
    
    # 分类检查（处理 'null' 字符串和空列表的情况）
    normalized_rule_categories = []
    if rule.categories and rule.categories != 'null' and rule.categories != ['null']:
        raw_categories = rule.categories
        if isinstance(raw_categories, str):
            try:
                parsed_categories = json.loads(raw_categories)
                if isinstance(parsed_categories, list):
                    raw_categories = parsed_categories
                else:
                    raw_categories = [raw_categories]
            except Exception:
                raw_categories = [raw_categories]

        if isinstance(raw_categories, list):
            normalized_rule_categories = [str(category_id) for category_id in raw_categories if category_id is not None and str(category_id) != 'null']

    if normalized_rule_categories:
        torrent_category = torrent.get("category")
        if str(torrent_category) not in normalized_rule_categories:
            if debug:
                print(f"  不匹配: 分类不符 ({torrent_category} not in {normalized_rule_categories})")
            return False
    
    # 关键词检查
    name = torrent.get("name", "").lower()
    descr = torrent.get("small_descr", "").lower() if torrent.get("small_descr") else ""
    
    if rule.keywords:
        keywords = [k.strip().lower() for k in rule.keywords.split(",")]
        if not any(kw in name or kw in descr for kw in keywords):
            if debug:
                print(f"  不匹配: 关键词不符 (keywords={keywords})")
            return False
    
    # 排除关键词检查
    if rule.exclude_keywords:
        exclude = [k.strip().lower() for k in rule.exclude_keywords.split(",")]
        if any(kw in name or kw in descr for kw in exclude):
            if debug:
                print(f"  不匹配: 包含排除关键词 (exclude={exclude})")
            return False
    
    return True
