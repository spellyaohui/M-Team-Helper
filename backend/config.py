import os
from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    # 应用配置
    APP_NAME: str = "M-Team Helper"
    DEBUG: bool = True
    
    # 数据目录（支持 Electron 传入的路径）
    MTEAM_DATA_DIR: str = "./data"
    
    # 数据库（如果未设置，将基于 MTEAM_DATA_DIR 动态生成）
    DATABASE_URL: str = ""
    
    # Firecrawl 配置
    FIRECRAWL_URL: str = "http://localhost:4001"
    
    # M-Team 配置
    MTEAM_BASE_URL: str = "https://test2.m-team.cc"
    
    # 定时任务间隔（秒）
    REFRESH_INTERVAL: int = 300
    
    class Config:
        env_file = ".env"

settings = Settings()

# 使用环境变量或默认路径
DATA_DIR = Path(settings.MTEAM_DATA_DIR).resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)
TORRENT_DIR = DATA_DIR / "torrents"
TORRENT_DIR.mkdir(parents=True, exist_ok=True)

# 动态生成数据库 URL（如果未显式设置）
if not settings.DATABASE_URL:
    db_path = DATA_DIR / "mteam.db"
    # Windows 路径需要使用正斜杠，并且绝对路径需要 4 个斜杠
    settings.DATABASE_URL = f"sqlite:///{db_path.as_posix()}"

print(f"[Config] 数据目录: {DATA_DIR}")
print(f"[Config] 数据库 URL: {settings.DATABASE_URL}")
