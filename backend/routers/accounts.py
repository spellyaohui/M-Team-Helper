from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from database import get_db
from models import Account
from services.scraper import MTeamAPI, parse_user_profile

router = APIRouter(prefix="/accounts", tags=["账号管理"])

class AccountCreate(BaseModel):
    username: str
    api_key: str  # API Token

class AccountResponse(BaseModel):
    id: int
    username: str
    uid: Optional[str]
    is_active: bool
    last_login: Optional[datetime]
    upload: float
    download: float
    ratio: float
    bonus: float
    created_at: datetime
    
    class Config:
        from_attributes = True

class ProfileResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None

@router.get("/", response_model=List[AccountResponse])
async def list_accounts(db: Session = Depends(get_db)):
    """获取所有账号"""
    accounts = db.query(Account).all()
    return accounts

@router.post("/", response_model=AccountResponse)
async def create_account(account: AccountCreate, db: Session = Depends(get_db)):
    """添加新账号（使用 API Token）"""
    # 检查是否已存在
    existing = db.query(Account).filter(Account.username == account.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="账号已存在")
    
    # 验证 API Token
    api = MTeamAPI(account.api_key)
    result = await api.get_profile()
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=f"API Token 无效: {result.get('error')}")
    
    profile = parse_user_profile(result["data"])
    
    db_account = Account(
        username=account.username,
        api_key=account.api_key,
        uid=profile["uid"],
        upload=profile["uploaded"],
        download=profile["downloaded"],
        ratio=profile["ratio"],
        bonus=profile["bonus"],
        last_login=datetime.utcnow()
    )
    db.add(db_account)
    db.commit()
    db.refresh(db_account)
    return db_account

@router.get("/{account_id}", response_model=AccountResponse)
async def get_account(account_id: int, db: Session = Depends(get_db)):
    """获取单个账号"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")
    return account

@router.post("/{account_id}/refresh", response_model=ProfileResponse)
async def refresh_account_info(account_id: int, db: Session = Depends(get_db)):
    """刷新账号信息"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")
    
    if not account.api_key:
        raise HTTPException(status_code=400, detail="账号未配置 API Token")
    
    api = MTeamAPI(account.api_key)
    result = await api.get_profile()
    
    if result["success"]:
        profile = parse_user_profile(result["data"])
        account.uid = profile["uid"]
        account.upload = profile["uploaded"]
        account.download = profile["downloaded"]
        account.ratio = profile["ratio"]
        account.bonus = profile["bonus"]
        account.last_login = datetime.utcnow()
        db.commit()
        return ProfileResponse(success=True, message="刷新成功", data=profile)
    
    return ProfileResponse(success=False, message=result.get("error", "刷新失败"))

@router.delete("/{account_id}")
async def delete_account(account_id: int, db: Session = Depends(get_db)):
    """删除账号"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")
    
    db.delete(account)
    db.commit()
    return {"success": True, "message": "删除成功"}
