# M-Team Helper Docker 镜像
# 多阶段构建：前端构建 + 后端运行
# 构建时需要在 mteam-helper 目录的上级目录执行，或指定 context

# ============ 阶段1：构建前端 ============
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# 复制前端依赖文件
COPY mteam-helper/frontend/package*.json ./

# 安装依赖
RUN npm ci --registry=https://registry.npmmirror.com

# 复制前端源码
COPY mteam-helper/frontend/ ./

# 构建前端
RUN npm run build

# ============ 阶段2：运行环境 ============
FROM python:3.11-slim

LABEL maintainer="spellyaohui"
LABEL description="M-Team Helper - PT站自动化助手"

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=Asia/Shanghai

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata \
    && rm -rf /var/lib/apt/lists/* \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone

# 升级 pip/setuptools 并固定无漏洞的 wheel 版本
RUN pip install --no-cache-dir --upgrade \
    pip \
    setuptools \
    wheel==0.46.2 \
    -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制后端依赖文件
COPY mteam-helper/backend/requirements.txt ./

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 强制升级 python-multipart 至修复版本
RUN pip install --no-cache-dir --upgrade \
    python-multipart==0.0.22 \
    -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制后端代码
COPY mteam-helper/backend/ ./

# 创建前端目录结构（与 main.py 中的路径一致）
RUN mkdir -p /app/frontend/dist

# 从前端构建阶段复制构建产物
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# 创建数据目录
RUN mkdir -p /app/data/torrents

# 暴露端口
EXPOSE 8001

# 数据卷
VOLUME ["/app/data"]

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/health')" || exit 1

# 启动命令
CMD ["python", "main.py"]
