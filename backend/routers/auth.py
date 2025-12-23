from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
import hashlib
import secrets

from database import get_db, Base, engine
from sqlalchemy import Column, Integer, String, DateTime, Boolean

# 北京时间 (UTC+8)
BEIJING_TZ = timezone(timedelta(hours=8))

def beijing_now():
    """获取当前北京时间"""
    return datetime.now(BEIJING_TZ).replace(tzinfo=None)

# 用户模型
class User(Base):
    """系统用户"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    password_hash = Column(String(128))
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=beijing_now)
    last_login = Column(DateTime, nullable=True)

# 创建表
Base.metadata.create_all(bind=engine)

router = APIRouter(prefix="/auth", tags=["认证"])

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    success: bool
    message: str
    token: str = ""
    username: str = ""

class RegisterRequest(BaseModel):
    username: str
    password: str

def hash_password(password: str) -> str:
    """密码哈希"""
    return hashlib.sha256(password.encode()).hexdigest()

def generate_token() -> str:
    """生成简单 token"""
    return secrets.token_hex(32)

# 简单的 token 存储（生产环境应使用 Redis）
active_tokens: dict = {}

@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest, db: Session = Depends(get_db)):
    """用户登录"""
    user = db.query(User).filter(User.username == req.username).first()
    
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    
    if user.password_hash != hash_password(req.password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    
    # 生成 token
    token = generate_token()
    active_tokens[token] = {
        "user_id": user.id,
        "username": user.username,
        "expires": beijing_now() + timedelta(days=7)
    }
    
    # 更新最后登录时间
    user.last_login = beijing_now()
    db.commit()
    
    return LoginResponse(
        success=True,
        message="登录成功",
        token=token,
        username=user.username
    )

@router.post("/register", response_model=LoginResponse)
async def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """用户注册（仅首次使用时可注册）"""
    # 检查是否已有用户
    user_count = db.query(User).count()
    if user_count > 0:
        # 已有用户，需要管理员权限才能注册新用户
        raise HTTPException(status_code=403, detail="注册已关闭，请联系管理员")
    
    # 检查用户名是否存在
    existing = db.query(User).filter(User.username == req.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")
    
    # 创建用户
    user = User(
        username=req.username,
        password_hash=hash_password(req.password),
        is_admin=True  # 首个用户为管理员
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # 自动登录
    token = generate_token()
    active_tokens[token] = {
        "user_id": user.id,
        "username": user.username,
        "expires": beijing_now() + timedelta(days=7)
    }
    
    return LoginResponse(
        success=True,
        message="注册成功",
        token=token,
        username=user.username
    )

@router.post("/logout")
async def logout(token: str = ""):
    """用户登出"""
    if token in active_tokens:
        del active_tokens[token]
    return {"success": True, "message": "已登出"}

@router.get("/verify")
async def verify_token(token: str = ""):
    """验证 token"""
    if token not in active_tokens:
        raise HTTPException(status_code=401, detail="未登录或登录已过期")
    
    token_data = active_tokens[token]
    if beijing_now() > token_data["expires"]:
        del active_tokens[token]
        raise HTTPException(status_code=401, detail="登录已过期")
    
    return {"success": True, "username": token_data["username"]}

@router.get("/check-init")
async def check_init(db: Session = Depends(get_db)):
    """检查是否需要初始化（注册首个用户）"""
    user_count = db.query(User).count()
    return {"need_init": user_count == 0}
