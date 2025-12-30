import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.middleware.base import BaseHTTPMiddleware

from config import settings
from database import init_db
from routers import accounts, downloaders, torrents, rules, history
from routers.auth import router as auth_router
from services.scheduler import start_scheduler, stop_scheduler
from utils.logger import LoggerManager, app_logger

# 初始化日志系统
LoggerManager.init(level="INFO")

# 前端静态文件目录（提前定义）
_docker_frontend = Path("/app/frontend/dist")
_dev_frontend = Path(__file__).resolve().parent.parent / "frontend" / "dist"
FRONTEND_DIR = _docker_frontend if _docker_frontend.exists() else _dev_frontend

# API 路径前缀列表
API_PREFIXES = ("/accounts", "/auth", "/downloaders", "/torrents", "/rules", "/history", "/settings", "/dashboard", "/health", "/logs")

class SPAMiddleware(BaseHTTPMiddleware):
    """SPA 中间件：处理前端路由，返回 index.html"""
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # 如果是 404 且不是 API 请求，返回 index.html
        if response.status_code == 404:
            path = request.url.path
            # 检查是否是 API 请求
            is_api = any(path.startswith(prefix) for prefix in API_PREFIXES)
            if not is_api and FRONTEND_DIR.exists():
                return FileResponse(FRONTEND_DIR / "index.html")
        
        return response

app = FastAPI(
    title=settings.APP_NAME,
    description="M-Team PT 助手 API",
    version="1.0.0"
)

# 添加 SPA 中间件（必须在其他中间件之前添加）
app.add_middleware(SPAMiddleware)

# 添加 Gzip 压缩中间件（提升 API 响应性能）
app.add_middleware(GZipMiddleware, minimum_size=1000)

# CORS 配置（开发时可能仍需要）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册 API 路由（不带 /api 前缀，前端已配置 baseURL）
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

# 导入日志路由
from routers import logs
app.include_router(logs.router)

@app.on_event("startup")
async def startup():
    """启动时初始化数据库和定时任务"""
    app_logger.info("M-Team Helper 服务启动")
    init_db()
    start_scheduler()

@app.on_event("shutdown")
async def shutdown():
    """关闭时停止定时任务"""
    app_logger.info("M-Team Helper 服务关闭")
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
    
    # 静态文件（vite.svg 等）
    @app.get("/vite.svg")
    async def serve_vite_svg():
        return FileResponse(FRONTEND_DIR / "vite.svg")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
