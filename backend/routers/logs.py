"""
日志查看 API

提供日志文件的查看和管理功能
"""

from fastapi import APIRouter, Query, HTTPException
from pathlib import Path
from typing import List, Optional
from datetime import datetime
import os

router = APIRouter(prefix="/logs", tags=["logs"])

# 日志目录
LOG_DIR = Path(__file__).parent.parent.parent / "data" / "logs"


@router.get("")
async def list_log_files():
    """获取所有日志文件列表"""
    if not LOG_DIR.exists():
        return {"files": []}
    
    files = []
    for f in LOG_DIR.iterdir():
        if f.is_file() and f.suffix == ".log":
            stat = f.stat()
            files.append({
                "name": f.name,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
    
    # 按修改时间倒序
    files.sort(key=lambda x: x["modified"], reverse=True)
    return {"files": files}


@router.get("/{filename}")
async def get_log_content(
    filename: str,
    lines: int = Query(default=200, ge=1, le=5000, description="返回的行数"),
    level: Optional[str] = Query(default=None, description="过滤日志级别"),
    search: Optional[str] = Query(default=None, description="搜索关键词")
):
    """获取日志文件内容
    
    Args:
        filename: 日志文件名
        lines: 返回最后 N 行
        level: 过滤日志级别 (DEBUG/INFO/WARNING/ERROR)
        search: 搜索关键词
    """
    # 安全检查：防止路径遍历
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="无效的文件名")
    
    log_file = LOG_DIR / filename
    if not log_file.exists():
        raise HTTPException(status_code=404, detail="日志文件不存在")
    
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取日志失败: {str(e)}")
    
    # 过滤日志级别
    if level:
        level_upper = level.upper()
        all_lines = [line for line in all_lines if f"[{level_upper}]" in line]
    
    # 搜索关键词
    if search:
        all_lines = [line for line in all_lines if search.lower() in line.lower()]
    
    # 取最后 N 行
    result_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
    
    return {
        "filename": filename,
        "total_lines": len(all_lines),
        "returned_lines": len(result_lines),
        "content": "".join(result_lines)
    }


@router.delete("/{filename}")
async def delete_log_file(filename: str):
    """删除日志文件"""
    # 安全检查
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="无效的文件名")
    
    log_file = LOG_DIR / filename
    if not log_file.exists():
        raise HTTPException(status_code=404, detail="日志文件不存在")
    
    try:
        os.remove(log_file)
        return {"message": f"已删除 {filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@router.delete("")
async def clear_old_logs(days: int = Query(default=7, ge=1, le=365)):
    """清理指定天数前的日志文件"""
    if not LOG_DIR.exists():
        return {"deleted": 0}
    
    deleted = 0
    now = datetime.now()
    
    for f in LOG_DIR.iterdir():
        if f.is_file():
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            if (now - mtime).days > days:
                try:
                    os.remove(f)
                    deleted += 1
                except:
                    pass
    
    return {"deleted": deleted, "message": f"已清理 {days} 天前的日志"}
