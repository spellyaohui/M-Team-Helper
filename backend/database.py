from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, declarative_base
from config import settings

# 启用 SQLite WAL 模式和性能优化
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={
        "check_same_thread": False,
        "timeout": 20,  # 20秒超时
    },
    echo=False,
    pool_pre_ping=True,  # 连接前检查
    pool_recycle=3600,   # 1小时回收连接
)

# 启用 WAL 模式和其他性能优化
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """设置 SQLite 性能优化参数"""
    cursor = dbapi_connection.cursor()
    
    # 启用 WAL 模式（Write-Ahead Logging）
    cursor.execute("PRAGMA journal_mode=WAL")
    
    # 设置同步模式为 NORMAL（平衡性能和安全性）
    cursor.execute("PRAGMA synchronous=NORMAL")
    
    # 增加缓存大小（默认 2MB，这里设置为 64MB）
    cursor.execute("PRAGMA cache_size=16384")  # 16384 * 4KB = 64MB
    
    # 设置临时存储在内存中
    cursor.execute("PRAGMA temp_store=MEMORY")
    
    # 启用内存映射 I/O（64MB）
    cursor.execute("PRAGMA mmap_size=67108864")
    
    # 优化查询规划器
    cursor.execute("PRAGMA optimize")
    
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """初始化数据库"""
    Base.metadata.create_all(bind=engine)
    
    # 数据库迁移：添加 images 列（如果不存在）
    with engine.connect() as conn:
        # 检查 download_history 表是否有 images 列
        result = conn.execute(text("PRAGMA table_info(download_history)"))
        columns = [row[1] for row in result.fetchall()]
        
        if "images" not in columns:
            print("[Database] 正在添加 images 列到 download_history 表...")
            conn.execute(text("ALTER TABLE download_history ADD COLUMN images TEXT"))
            conn.commit()
            print("[Database] images 列添加成功")
        
        # 分析表以优化查询计划
        conn.execute(text("PRAGMA optimize"))
        conn.commit()
