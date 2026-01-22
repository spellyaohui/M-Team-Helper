"""
数据库自动迁移工具

在应用启动时自动检查数据库结构，如果发现缺失的列则自动添加。
适用于外部部署环境，避免手动执行迁移脚本。
"""

from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError
from database import engine, Base
from utils.logger import scheduler_logger as logger


def get_table_columns(table_name: str) -> set:
    """获取数据库表的所有列名"""
    inspector = inspect(engine)
    try:
        columns = inspector.get_columns(table_name)
        return {col['name'] for col in columns}
    except Exception as e:
        logger.warning(f"获取表 {table_name} 列信息失败: {e}")
        return set()


def get_model_columns(model_class) -> dict:
    """获取模型类定义的所有列及其属性

    返回格式: {列名: 列对象}
    """
    columns = {}
    for column in model_class.__table__.columns:
        columns[column.name] = column
    return columns


def column_to_sql_type(column) -> str:
    """将SQLAlchemy列类型转换为SQL类型字符串"""
    from sqlalchemy import String, Integer, Float, Boolean, DateTime, Text, JSON

    col_type = column.type

    # 处理各种类型
    if isinstance(col_type, String):
        length = col_type.length if col_type.length else 255
        return f"VARCHAR({length})"
    elif isinstance(col_type, Integer):
        return "INTEGER"
    elif isinstance(col_type, Float):
        return "REAL"
    elif isinstance(col_type, Boolean):
        return "BOOLEAN"
    elif isinstance(col_type, DateTime):
        return "DATETIME"
    elif isinstance(col_type, Text):
        return "TEXT"
    elif isinstance(col_type, JSON):
        return "JSON"
    else:
        # 默认返回类型的字符串表示
        return str(col_type)


def get_column_definition(column) -> str:
    """生成列的完整SQL定义"""
    sql_type = column_to_sql_type(column)

    # 构建列定义
    parts = [sql_type]

    # 添加约束
    if not column.nullable:
        parts.append("NOT NULL")

    # 添加默认值
    if column.default is not None:
        default_value = column.default.arg
        if isinstance(default_value, bool):
            parts.append(f"DEFAULT {1 if default_value else 0}")
        elif isinstance(default_value, (int, float)):
            parts.append(f"DEFAULT {default_value}")
        elif isinstance(default_value, str):
            parts.append(f"DEFAULT '{default_value}'")
        elif callable(default_value):
            # 对于函数默认值（如 beijing_now），跳过
            pass

    return " ".join(parts)


def add_missing_column(table_name: str, column_name: str, column):
    """添加缺失的列"""
    try:
        column_def = get_column_definition(column)
        sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}"

        logger.info(f"执行SQL: {sql}")

        with engine.connect() as conn:
            conn.execute(text(sql))
            conn.commit()

        logger.info(f"[OK] 成功添加列: {table_name}.{column_name}")
        return True

    except SQLAlchemyError as e:
        logger.error(f"[ERROR] 添加列失败 {table_name}.{column_name}: {e}")
        return False


def check_and_migrate_table(model_class, table_name: str = None) -> dict:
    """检查并迁移单个表

    Returns:
        dict: 迁移结果统计
    """
    if table_name is None:
        table_name = model_class.__tablename__

    logger.info(f"检查表: {table_name}")

    # 获取数据库现有列
    db_columns = get_table_columns(table_name)

    if not db_columns:
        logger.warning(f"表 {table_name} 不存在或无法访问，将通过 Base.metadata.create_all() 创建")
        try:
            model_class.__table__.create(engine, checkfirst=True)
            logger.info(f"[OK] 创建表: {table_name}")
            return {"created": 1, "added": 0, "skipped": 0, "failed": 0}
        except Exception as e:
            logger.error(f"[ERROR] 创建表失败 {table_name}: {e}")
            return {"created": 0, "added": 0, "skipped": 0, "failed": 1}

    # 获取模型定义的列
    model_columns = get_model_columns(model_class)

    # 找出缺失的列
    missing_columns = set(model_columns.keys()) - db_columns

    stats = {"created": 0, "added": 0, "skipped": 0, "failed": 0}

    if not missing_columns:
        logger.info(f"[OK] 表 {table_name} 结构完整，无需迁移")
        stats["skipped"] = len(model_columns)
        return stats

    logger.info(f"发现 {len(missing_columns)} 个缺失的列: {missing_columns}")

    # 添加缺失的列
    for col_name in missing_columns:
        column = model_columns[col_name]
        if add_missing_column(table_name, col_name, column):
            stats["added"] += 1
        else:
            stats["failed"] += 1

    return stats


def auto_migrate_database():
    """自动迁移数据库

    检查所有模型表，添加缺失的列。
    这个函数应该在应用启动时调用。
    """
    logger.info("=" * 60)
    logger.info("开始数据库自动迁移检查")
    logger.info("=" * 60)

    from models import Account, FilterRule, Downloader, SystemSettings, DownloadHistory

    # 定义需要检查的模型（按依赖顺序）
    models = [
        Account,
        Downloader,
        FilterRule,
        SystemSettings,
        DownloadHistory
    ]

    total_stats = {"created": 0, "added": 0, "skipped": 0, "failed": 0}

    try:
        for model in models:
            stats = check_and_migrate_table(model)
            for key in total_stats:
                total_stats[key] += stats[key]

        logger.info("=" * 60)
        logger.info("数据库迁移检查完成")
        logger.info(f"统计: 创建表={total_stats['created']}, "
                   f"添加列={total_stats['added']}, "
                   f"跳过列={total_stats['skipped']}, "
                   f"失败={total_stats['failed']}")
        logger.info("=" * 60)

        if total_stats['failed'] > 0:
            logger.warning(f"[WARNING] 有 {total_stats['failed']} 个操作失败，请检查日志")
        elif total_stats['added'] > 0 or total_stats['created'] > 0:
            logger.info(f"[OK] 成功完成数据库结构更新")
        else:
            logger.info(f"[OK] 数据库结构已是最新")

        return total_stats['failed'] == 0

    except Exception as e:
        logger.error(f"数据库迁移过程发生异常: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def create_all_tables():
    """创建所有表（如果不存在）"""
    logger.info("创建所有数据库表...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("[OK] 数据库表创建完成")
        return True
    except Exception as e:
        logger.error(f"[ERROR] 创建数据库表失败: {e}")
        return False


if __name__ == "__main__":
    # 测试迁移
    auto_migrate_database()
