from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from database import get_db
from models import FilterRule, Account, Downloader

router = APIRouter(prefix="/rules", tags=["筛选规则"])

class RuleCreate(BaseModel):
    account_id: int
    name: str
    is_enabled: bool = True
    mode: str = "normal"  # normal 或 adult
    free_only: bool = False
    double_upload: bool = False
    min_size: Optional[float] = None  # GB
    max_size: Optional[float] = None  # GB
    min_seeders: Optional[int] = None
    max_seeders: Optional[int] = None
    categories: Optional[List[str]] = None
    keywords: Optional[str] = None
    exclude_keywords: Optional[str] = None
    downloader_id: Optional[int] = None
    save_path: Optional[str] = None
    tags: Optional[List[str]] = None  # 下载时添加的标签
    max_downloading: Optional[int] = None  # 最大同时下载数

class RuleResponse(BaseModel):
    id: int
    account_id: int
    name: str
    is_enabled: bool
    mode: str
    free_only: bool
    double_upload: bool
    min_size: Optional[float]
    max_size: Optional[float]
    min_seeders: Optional[int]
    max_seeders: Optional[int]
    categories: Optional[List[str]]
    keywords: Optional[str]
    exclude_keywords: Optional[str]
    downloader_id: Optional[int]
    save_path: Optional[str]
    tags: Optional[List[str]]
    max_downloading: Optional[int]
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
    
    db_rule = FilterRule(
        account_id=rule.account_id,
        name=rule.name,
        is_enabled=rule.is_enabled,
        mode=rule.mode,
        free_only=rule.free_only,
        double_upload=rule.double_upload,
        min_size=rule.min_size,
        max_size=rule.max_size,
        min_seeders=rule.min_seeders,
        max_seeders=rule.max_seeders,
        categories=rule.categories,
        keywords=rule.keywords,
        exclude_keywords=rule.exclude_keywords,
        downloader_id=rule.downloader_id,
        save_path=rule.save_path,
        tags=rule.tags,
        max_downloading=rule.max_downloading
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


def match_torrent(torrent: dict, rule: FilterRule) -> bool:
    """检查种子是否匹配规则"""
    # 免费检查
    if rule.free_only and not torrent.get("is_free"):
        return False
    
    # 2x上传检查
    if rule.double_upload and not torrent.get("is_2x"):
        return False
    
    # 大小检查 (GB)
    size_gb = torrent.get("size_gb", 0)
    if rule.min_size and size_gb < rule.min_size:
        return False
    if rule.max_size and size_gb > rule.max_size:
        return False
    
    # 做种数检查
    seeders = torrent.get("seeders", 0)
    if rule.min_seeders and seeders < rule.min_seeders:
        return False
    if rule.max_seeders and seeders > rule.max_seeders:
        return False
    
    # 分类检查
    if rule.categories:
        if torrent.get("category") not in rule.categories:
            return False
    
    # 关键词检查
    name = torrent.get("name", "").lower()
    descr = torrent.get("small_descr", "").lower() if torrent.get("small_descr") else ""
    
    if rule.keywords:
        keywords = [k.strip().lower() for k in rule.keywords.split(",")]
        if not any(kw in name or kw in descr for kw in keywords):
            return False
    
    # 排除关键词检查
    if rule.exclude_keywords:
        exclude = [k.strip().lower() for k in rule.exclude_keywords.split(",")]
        if any(kw in name or kw in descr for kw in exclude):
            return False
    
    return True
