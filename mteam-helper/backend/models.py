from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, ForeignKey, Text, JSON, Index
from sqlalchemy.orm import relationship
from datetime import datetime, timezone, timedelta
from database import Base

# 北京时间 (UTC+8)
BEIJING_TZ = timezone(timedelta(hours=8))

def beijing_now():
    """获取当前北京时间"""
    return datetime.now(BEIJING_TZ).replace(tzinfo=None)

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
    
    created_at = Column(DateTime, default=beijing_now)
    updated_at = Column(DateTime, default=beijing_now, onupdate=beijing_now)
    
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
    
    # 规则类型：normal=普通规则, favorite=收藏监控规则
    rule_type = Column(String(20), default="normal")  # normal 或 favorite

    # 规则排序（数字越小越靠前）
    sort_order = Column(Integer, nullable=True, index=True)

    # 筛选条件
    free_only = Column(Boolean, default=False)  # 仅免费
    double_upload = Column(Boolean, default=False)  # 2x上传
    min_size = Column(Float, nullable=True)  # 最小大小 (GB)
    max_size = Column(Float, nullable=True)  # 最大大小 (GB)
    min_seeders = Column(Integer, nullable=True)  # 最小做种数
    max_seeders = Column(Integer, nullable=True)  # 最大做种数
    min_leechers = Column(Integer, nullable=True)  # 最小下载用户数
    max_leechers = Column(Integer, nullable=True)  # 最大下载用户数
    categories = Column(JSON, nullable=True)  # 分类列表
    keywords = Column(String(500), nullable=True)  # 关键词（逗号分隔）
    exclude_keywords = Column(String(500), nullable=True)  # 排除关键词
    max_publish_hours = Column(Integer, nullable=True)  # 最大发布时间（小时），只下载N小时内发布的种子

    # 收藏监控配置（仅当 rule_type=favorite 时有效）
    monitor_favorites = Column(Boolean, default=False)  # 是否监控收藏
    auto_unfavorite_after_seeding = Column(Boolean, default=True)  # 做种后自动取消收藏
    
    # 下载器配置
    downloader_id = Column(Integer, ForeignKey("downloaders.id"), nullable=True)
    save_path = Column(String(500), nullable=True)  # 保存路径
    tags = Column(JSON, nullable=True)  # 下载时添加的标签列表
    max_downloading = Column(Integer, nullable=True)  # 最大同时下载数，超过则暂停添加
    download_limit_kbps = Column(Integer, nullable=True)
    upload_limit_kbps = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, default=beijing_now)
    
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
    
    created_at = Column(DateTime, default=beijing_now)

class SystemSettings(Base):
    """系统设置"""
    __tablename__ = "system_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, index=True)  # 设置键名
    value = Column(Text)  # 设置值（JSON 字符串）
    description = Column(String(500), nullable=True)  # 设置描述
    created_at = Column(DateTime, default=beijing_now)
    updated_at = Column(DateTime, default=beijing_now, onupdate=beijing_now)

class DownloadHistory(Base):
    """下载历史"""
    __tablename__ = "download_history"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), index=True)  # 添加索引
    torrent_id = Column(String(50), index=True)  # 添加索引
    torrent_name = Column(String(500))
    torrent_size = Column(Float)  # bytes
    rule_id = Column(Integer, ForeignKey("filter_rules.id"), nullable=True)
    downloader_id = Column(Integer, ForeignKey("downloaders.id"), nullable=True, index=True)  # 添加索引
    status = Column(String(20), default="pending", index=True)  # 添加索引
    
    # 促销相关
    info_hash = Column(String(64), nullable=True, index=True)  # 添加索引，用于查找特定种子
    discount_type = Column(String(20), nullable=True)  # 促销类型：FREE, _2X_FREE 等
    discount_end_time = Column(DateTime, nullable=True, index=True)  # 添加索引，用于过期检查

    # 收藏相关
    is_favorited = Column(Boolean, default=False)  # 是否已收藏（用于收藏监控规则）
    unfavorited_at = Column(DateTime, nullable=True)  # 取消收藏时间
    
    # 封面图片
    images = Column(JSON, nullable=True)  # 种子封面图片 URL 列表
    
    created_at = Column(DateTime, default=beijing_now, index=True)  # 添加索引，用于排序
    
    account = relationship("Account", back_populates="downloads")
    
    # 添加复合索引，优化常见查询
    __table_args__ = (
        Index('idx_account_created', 'account_id', 'created_at'),  # 按账号和时间查询
        Index('idx_status_created', 'status', 'created_at'),       # 按状态和时间查询
        Index('idx_downloader_status', 'downloader_id', 'status'), # 同步状态时使用
    )
    downloader = relationship("Downloader")
