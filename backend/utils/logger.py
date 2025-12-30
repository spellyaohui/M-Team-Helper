"""
日志记录模块

提供统一的日志记录功能，支持：
- 控制台输出（带颜色）
- 文件记录（按日期滚动）
- 日志级别控制
- 结构化日志格式
"""

import logging
import os
import sys
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Optional

# 日志目录
LOG_DIR = Path(__file__).parent.parent.parent / "data" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# 日志格式
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 颜色代码（用于控制台输出）
COLORS = {
    "DEBUG": "\033[36m",     # 青色
    "INFO": "\033[32m",      # 绿色
    "WARNING": "\033[33m",   # 黄色
    "ERROR": "\033[31m",     # 红色
    "CRITICAL": "\033[35m",  # 紫色
    "RESET": "\033[0m"       # 重置
}


class ColoredFormatter(logging.Formatter):
    """带颜色的日志格式化器（用于控制台）"""
    
    def format(self, record):
        # 保存原始 levelname
        orig_levelname = record.levelname
        # 添加颜色
        color = COLORS.get(record.levelname, COLORS["RESET"])
        record.levelname = f"{color}{record.levelname}{COLORS['RESET']}"
        # 格式化
        result = super().format(record)
        # 恢复原始 levelname
        record.levelname = orig_levelname
        return result


class LoggerManager:
    """日志管理器"""
    
    _loggers: dict = {}
    _initialized: bool = False
    _log_level: int = logging.INFO
    
    @classmethod
    def init(cls, level: str = "INFO"):
        """初始化日志系统"""
        cls._log_level = getattr(logging, level.upper(), logging.INFO)
        cls._initialized = True
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """获取或创建日志记录器"""
        if name in cls._loggers:
            return cls._loggers[name]
        
        logger = logging.getLogger(name)
        logger.setLevel(cls._log_level)
        logger.propagate = False  # 防止重复输出
        
        # 如果已有处理器，不重复添加
        if logger.handlers:
            cls._loggers[name] = logger
            return logger
        
        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(cls._log_level)
        console_handler.setFormatter(ColoredFormatter(LOG_FORMAT, LOG_DATE_FORMAT))
        logger.addHandler(console_handler)
        
        # 文件处理器（按天滚动，保留30天）
        log_file = LOG_DIR / f"{name}.log"
        file_handler = TimedRotatingFileHandler(
            log_file,
            when="midnight",
            interval=1,
            backupCount=30,
            encoding="utf-8"
        )
        file_handler.setLevel(cls._log_level)
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
        file_handler.suffix = "%Y-%m-%d"
        logger.addHandler(file_handler)
        
        cls._loggers[name] = logger
        return logger


# 预定义的日志记录器
def get_logger(name: str) -> logging.Logger:
    """获取日志记录器的便捷函数"""
    return LoggerManager.get_logger(name)


# 常用日志记录器
scheduler_logger = get_logger("scheduler")
api_logger = get_logger("api")
downloader_logger = get_logger("downloader")
mteam_logger = get_logger("mteam")
auth_logger = get_logger("auth")
app_logger = get_logger("app")
