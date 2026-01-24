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
    """初始化数据库并执行迁移"""
    Base.metadata.create_all(bind=engine)
    
    # 执行数据库迁移
    run_migrations()


def run_migrations():
    """执行数据库迁移，添加缺失的列"""
    migrations = [
        # (表名, 列名, 列定义)
        ("filter_rules", "max_publish_hours", "INTEGER"),
        ("filter_rules", "sort_order", "INTEGER"),
    ]
    
    with engine.connect() as conn:
        for table_name, column_name, column_type in migrations:
            # 检查列是否存在
            result = conn.execute(text(f"PRAGMA table_info({table_name})"))
            columns = [row[1] for row in result.fetchall()]
            
            if column_name not in columns:
                # 添加缺失的列
                try:
                    conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"))
                    conn.commit()
                    print(f"[Migration] 已添加列: {table_name}.{column_name}")
                except Exception as e:
                    print(f"[Migration] 添加列失败 {table_name}.{column_name}: {e}")
