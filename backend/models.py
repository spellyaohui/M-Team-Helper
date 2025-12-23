from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class Account(Base):
    """PT账号"""
    __tablename__ = "accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True)
    password = Column(String(200), nullable=True)  # 可选，加密存储
    api_key = Column(String(100), nullable=True)  # API Token (推荐)
    cookies = Column(Text, nullable=True)  # 登录后的cookies
    uid = Column(String(50), nullable=True)  # M-Team 用户ID
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime, nullable=True)
    
    # 用户数据
    upload = Column(Float, default=0)  # 上传量 (bytes)
    download = Column(Float, default=0)  # 下载量 (bytes)
    ratio = Column(Float, default=0)  # 分享率
    bonus = Column(Float, default=0)  # 魔力值
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联
    rules = relationship("FilterRule", back_populates="account")
    downloads = relationship("DownloadHistory", back_populates="account")

class FilterRule(Base):
    """筛选规则"""
    __tablename__ = "filter_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"))
    name = Column(String(100))
    is_enabled = Column(Boolean, default=True)
    
    # 模式：normal 或 adult
    mode = Column(String(20), default="normal")
    
    # 筛选条件
    free_only = Column(Boolean, default=False)  # 仅免费
    double_upload = Column(Boolean, default=False)  # 2x上传
    min_size = Column(Float, nullable=True)  # 最小大小 (GB)
    max_size = Column(Float, nullable=True)  # 最大大小 (GB)
    min_seeders = Column(Integer, nullable=True)  # 最小做种数
    max_seeders = Column(Integer, nullable=True)  # 最大做种数
    categories = Column(JSON, nullable=True)  # 分类列表
    keywords = Column(String(500), nullable=True)  # 关键词（逗号分隔）
    exclude_keywords = Column(String(500), nullable=True)  # 排除关键词
    
    # 下载器配置
    downloader_id = Column(Integer, ForeignKey("downloaders.id"), nullable=True)
    save_path = Column(String(500), nullable=True)  # 保存路径
    tags = Column(JSON, nullable=True)  # 下载时添加的标签列表
    max_downloading = Column(Integer, nullable=True)  # 最大同时下载数，超过则暂停添加
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    account = relationship("Account", back_populates="rules")
    downloader = relationship("Downloader")

class Downloader(Base):
    """下载器配置"""
    __tablename__ = "downloaders"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    type = Column(String(20))  # qbittorrent / transmission
    host = Column(String(200))
    port = Column(Integer)
    username = Column(String(100), nullable=True)
    password = Column(String(200), nullable=True)
    use_ssl = Column(Boolean, default=False)  # 是否使用 HTTPS
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

class SystemSettings(Base):
    """系统设置"""
    __tablename__ = "system_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, index=True)  # 设置键名
    value = Column(Text)  # 设置值（JSON 字符串）
    description = Column(String(500), nullable=True)  # 设置描述
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class DownloadHistory(Base):
    """下载历史"""
    __tablename__ = "download_history"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"))
    torrent_id = Column(String(50))  # PT站种子ID
    torrent_name = Column(String(500))
    torrent_size = Column(Float)  # bytes
    rule_id = Column(Integer, ForeignKey("filter_rules.id"), nullable=True)
    downloader_id = Column(Integer, ForeignKey("downloaders.id"), nullable=True)
    status = Column(String(20), default="pending")  # pending/downloading/completed/failed/expired_deleted
    
    # 促销相关
    info_hash = Column(String(64), nullable=True)  # 种子哈希，用于在下载器中定位
    discount_type = Column(String(20), nullable=True)  # 促销类型：FREE, _2X_FREE 等
    discount_end_time = Column(DateTime, nullable=True)  # 促销到期时间
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    account = relationship("Account", back_populates="downloads")
    downloader = relationship("Downloader")
