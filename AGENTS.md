# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## 交互规则

- **语言要求**：全程使用**中文**与用户交流（代码变量名除外）。

## 项目概述

M-Team Helper 是一个 PT 站自动化助手的单体仓库（Monorepo），包含多个子项目：

- **mteam-helper**：主要的 Web 应用（核心开发项目）
- **mteam-helper-desktop**：基于 Electron 的桌面应用
- **mteam-helper-Mobile**：基于 uni-app 的移动端应用
- **mteam-helper-docker**：Docker 部署配置

## 常用开发命令

### mteam-helper（主 Web 项目）

#### 前端 (React + Vite)
```bash
cd mteam-helper/frontend
npm install
npm run dev          # 开发模式（热重载）
npm run build        # 生产构建
```

#### 后端 (FastAPI)
```bash
cd mteam-helper/backend
python -m venv venv
# 激活环境: source venv/bin/activate (Linux/Mac) 或 venv\Scripts\activate (Windows)
pip install -r requirements.txt
python main.py       # 启动服务 (默认端口 8001)
```

#### 完整构建部署
```bash
cd mteam-helper/frontend && npm run build
cd ../backend && python main.py
```

### mteam-helper-desktop（桌面端）

```bash
cd mteam-helper-desktop
npm install
npm start            # 启动 Electron 开发环境
npm run build        # 构建所有内容 (Backend + Frontend + Electron)
npm run dist         # 打包发布版本
```

### mteam-helper-Mobile（移动端）

```bash
cd mteam-helper-Mobile
npm install
npm run dev:h5       # H5 开发模式
npm run dev:app      # App 开发模式
npm run build:h5     # 构建 H5
npm run build:app    # 构建 App
npm run test         # 运行测试 (Vitest)
```

### Docker 部署

```bash
docker-compose up -d             # 启动服务
docker logs -f mteam-helper      # 查看日志
docker-compose down              # 停止服务
```

## 核心架构

### 1. 后端架构 (mteam-helper/backend)

**技术栈**：FastAPI + SQLAlchemy 2.x + APScheduler + httpx + SQLite

**主要模块**：
- `main.py`: 应用入口，集成静态文件服务
- `services/scheduler.py`: 核心定时任务（账号刷新、种子检查、过期清理）
- `services/`: 业务逻辑层 (Account, Downloader, Torrent)
- `routers/`: API 接口层
- `models.py`: 数据库模型

**关键逻辑**：
- **单体服务**：后端通过 `StaticFiles` 托管前端构建产物。
- **定时任务**：自动刷新账号数据，扫描新种子并推送到下载器。
- **下载器集成**：支持 qBittorrent 和 Transmission，统一接口管理。

### 2. 前端架构 (mteam-helper/frontend)

**技术栈**：React 19 + TypeScript + Ant Design 5 + Vite 7

**特点**：
- 生产环境集成到后端。
- API 调用无 `/api` 前缀，直接映射。

### 3. 桌面端架构 (mteam-helper-desktop)

**技术栈**：Electron + Node.js
- 封装了 Web 端功能。
- 打包时包含 Python 后端环境 (`backend-dist`)。

### 4. 移动端架构 (mteam-helper-Mobile)

**技术栈**：uni-app + Vue 3 + TypeScript + Pinia + Vitest
- 支持 H5 和 App 跨平台构建。

## 开发指南

1. **环境配置**：后端配置在 `backend/.env` (参考 `MTEAM_BASE_URL`, `DATABASE_URL`)。
2. **前端构建**：修改前端后必须 `npm run build` 才能在后端静态服务中生效。
3. **数据库**：使用 SQLite (`backend/data/mteam.db`)，修改 `models.py` 后需重置数据库。
4. **下载器连接**：Docker 容器内连接宿主机下载器需使用 `host.docker.internal`。
5. **种子存储**：种子文件保存在 `backend/data/torrents/`。

## 版本与同步发布（智能体必遵）

详细规则见 `.cursor/rules/mteam-release-versioning.mdc`。摘要：

- **统一版本**：桌面端、网页端（`mteam-helper` 前后端一体）、Docker 共用 **2.0.x**；当前基线 **2.0.8**，下次发版从 **2.0.9** 起跳。
- **同步打包**：凡需用户重新部署/重装的功能改动，默认**同版本**内完成：前端 `npm run build`、桌面 `mteam-helper-desktop` 全量构建、Docker 镜像构建并更新 `docker-compose.yml` 中的 tag。
- **不含 App**：`mteam-helper-Mobile` 可独立版本，不纳入上述三端齐发要求；**该目录为私有源码，已 gitignore，不得上传 GitHub。**
