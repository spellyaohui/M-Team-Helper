import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from config import settings
from database import init_db
from routers import accounts, downloaders, torrents, rules, history
from routers.auth import router as auth_router
from services.scheduler import start_scheduler, stop_scheduler

app = FastAPI(
    title=settings.APP_NAME,
    description="M-Team PT 助手 API",
    version="1.0.0"
)

# CORS 配置（开发时可能仍需要）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册 API 路由
app.include_router(auth_router)
app.include_router(accounts.router)
app.include_router(downloaders.router)
app.include_router(torrents.router)
app.include_router(rules.router)
app.include_router(history.router)

# 导入设置路由
from routers import settings
app.include_router(settings.router)

# 导入仪表盘路由
from routers import dashboard
app.include_router(dashboard.router)

# 前端静态文件目录
FRONTEND_DIR = (Path(__file__).resolve().parent.parent / "frontend" / "dist")

@app.on_event("startup")
async def startup():
    """启动时初始化数据库和定时任务"""
    init_db()
    start_scheduler()

@app.on_event("shutdown")
async def shutdown():
    """关闭时停止定时任务"""
    stop_scheduler()

@app.get("/health")
async def health():
    return {"status": "ok"}

# 挂载前端静态文件（如果存在）
if FRONTEND_DIR.exists():
    # 挂载静态资源目录
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")
    
    # 根路径返回 index.html
    @app.get("/")
    async def serve_index():
        """返回前端首页"""
        return FileResponse(FRONTEND_DIR / "index.html")
    
    # 处理前端路由（SPA fallback）
    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        """处理所有非 API 请求，返回前端页面"""
        # 尝试返回静态文件
        file_path = FRONTEND_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        # 否则返回 index.html（SPA 路由）
        return FileResponse(FRONTEND_DIR / "index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
