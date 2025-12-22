from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    # 应用配置
    APP_NAME: str = "M-Team Helper"
    DEBUG: bool = True
    
    # 数据库
    DATABASE_URL: str = "sqlite:///./data/mteam.db"
    
    # Firecrawl 配置
    FIRECRAWL_URL: str = "http://localhost:4001"
    
    # M-Team 配置
    MTEAM_BASE_URL: str = "https://test2.m-team.cc"
    
    # 定时任务间隔（秒）
    REFRESH_INTERVAL: int = 300
    
    class Config:
        env_file = ".env"

settings = Settings()

# 确保数据目录存在
DATA_DIR = Path("./data")
DATA_DIR.mkdir(exist_ok=True)
TORRENT_DIR = DATA_DIR / "torrents"
TORRENT_DIR.mkdir(exist_ok=True)
