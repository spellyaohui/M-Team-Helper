# M-Team Helper

面向 [M-Team](https://kp.m-team.cc/) 的 PT 站自动化助手：多账号管理、种子浏览与搜索、自动下载规则、qBittorrent / Transmission 联动、下载历史、智能删种与定时调度。支持 **Docker**、**Web 自托管** 与 **Windows 桌面版**。

| 渠道 | 说明 |
|------|------|
| Web / API | `mteam-helper`：React + FastAPI，生产环境前后端一体 |
| Windows 桌面 | `mteam-helper-desktop`：Electron，内置后端，免装 Python/Node |
| Docker | `mteam-helper-docker`：官方镜像，单容器部署 |
| 发布下载 | [GitHub Releases](https://github.com/spellyaohui/M-Team-Helper/releases)（Windows 安装包 / 便携版） |

> 当前公开仓库为 **Monorepo**。Web、桌面、Docker 共用同一套 `mteam-helper` 业务代码；发版版本号应对齐（详见 `AGENTS.md` 与 `.cursor/rules/mteam-release-versioning.mdc`）。

## 功能概览

- **多账号**：API Token 拉取账号信息，支持多账号切换。
- **种子**：分页搜索、分类/促销/体积/做种数等筛选。
- **自动规则**：普通规则与收藏监控；排序、最大同时下载数、保存路径、标签、上传/下载限速。
- **下载器**：qBittorrent、Transmission；连接测试与状态同步。
- **下载历史**：自动/手动推送记录、从下载器导入、暂停/继续/删除、上传本地 `.torrent`。
- **删种**：促销到期、非免费、动态空间、分享率策略、站点已注销种子清理。
- **调度**：刷新间隔、时间段内是否运行自动任务、调度器状态与手动重启。
- **运维**：仪表盘、日志、启动时自动数据库迁移（升级一般无需手改库）。

更细的功能说明见 [`mteam-helper/README.md`](mteam-helper/README.md)。

## 仓库结构

```
M-Team-Helper/
├── mteam-helper/              # 主应用（前端 + 后端）
│   ├── frontend/              # React 19 + Vite + Ant Design
│   ├── backend/               # FastAPI + SQLAlchemy + APScheduler
│   └── deploy.sh              # Linux 一键部署脚本
├── mteam-helper-desktop/      # Windows Electron 桌面版
├── mteam-helper-docker/       # Dockerfile、compose、构建说明
├── AGENTS.md                  # 智能体 / 协作说明
└── README.md                  # 本文件
```

## 环境要求

| 场景 | 要求 |
|------|------|
| Docker 部署 | Docker / Docker Compose |
| 本地 Web | Python 3.10+、Node.js 18+ |
| 桌面版（使用 Release） | Windows 10/11 x64，无需额外运行时 |
| 桌面版（自构建） | Node.js 18+、Python 3.10+、PyInstaller |
| 下载器（可选） | qBittorrent 或 Transmission |

## 快速开始

### 1. Docker 部署（推荐）

Docker Hub：<https://hub.docker.com/r/spellyaohui/mteam-helper>

```bash
git clone https://github.com/spellyaohui/M-Team-Helper.git
cd M-Team-Helper/mteam-helper-docker

# 按需编辑 docker-compose.yml 中的镜像 tag 与端口
docker compose up -d
```

数据持久化目录：`./data` → 容器内 `/app/data`（含 `mteam.db`、`torrents/`）。

容器内访问宿主机下载器时，请使用宿主机 IP 或 `host.docker.internal`，**不要**写 `localhost`。

访问：

- Web：`http://<主机IP>:8001`
- API 文档：`http://<主机IP>:8001/docs`
- 健康检查：`http://<主机IP>:8001/health`

> 若宿主机 **8001** 已被占用（例如部分 NAS），将映射改为 `8010:8001` 等即可。

从源码构建镜像（在 **仓库根目录** 执行）：

```bash
docker build -f mteam-helper-docker/Dockerfile -t spellyaohui/mteam-helper:<版本> .
```

详见 [`mteam-helper-docker/README.md`](mteam-helper-docker/README.md) 与 [`mteam-helper-docker/构建说明.txt`](mteam-helper-docker/构建说明.txt)。

### 2. Windows 桌面版

在 [Releases](https://github.com/spellyaohui/M-Team-Helper/releases) 下载：

- `M-Team.Helper.Setup.<版本>_win_x64.exe` — 安装版
- `MTeam-Helper-Portable-<版本>_win_x64.exe` — 便携版

自构建：

```bash
cd mteam-helper-desktop
build.bat
# 或：npm install && npm run build
```

产物在 `mteam-helper-desktop/dist/`。开发与托盘说明见 [`mteam-helper-desktop/README.md`](mteam-helper-desktop/README.md)。

### 3. 本地 Web（生产模式）

```bash
git clone https://github.com/spellyaohui/M-Team-Helper.git
cd M-Team-Helper/mteam-helper

npm run install:frontend
npm run build

cd backend
python -m venv venv
# Windows: venv\Scripts\activate
# Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # 按需修改
python main.py
```

浏览器打开：`http://localhost:8001`。

### 4. 开发模式（前后端分离）

```bash
# 终端 1：后端
cd mteam-helper/backend
pip install -r requirements.txt
python main.py

# 终端 2：前端热更新
cd mteam-helper/frontend
npm install
npm run dev
```

### 5. Linux 一键脚本

```bash
curl -fsSL https://raw.githubusercontent.com/spellyaohui/M-Team-Helper/main/mteam-helper/deploy.sh -o deploy.sh
chmod +x deploy.sh
sudo bash deploy.sh
```

## 配置与数据

| 项目 | 位置 |
|------|------|
| 后端环境变量 | `mteam-helper/backend/.env`（参考 `.env.example`） |
| SQLite 数据库 | `backend/data/mteam.db`（Docker 为挂载的 `/app/data`） |
| 种子文件 | `backend/data/torrents/` |
| 桌面版用户数据 | `%APPDATA%\mteam-helper-desktop\` |

常用变量：`MTEAM_BASE_URL`（默认 `https://api.m-team.cc`）、`DATABASE_URL`、`DEBUG` 等，完整说明见 [`mteam-helper/README.md`](mteam-helper/README.md#配置说明)。

**请勿将 `.env`、数据库、种子目录提交到 Git**；根目录 `.gitignore` 已做屏蔽。

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 19、TypeScript、Ant Design 5、Vite 7 |
| 后端 | FastAPI、SQLAlchemy 2.x、APScheduler、httpx、SQLite |
| 桌面 | Electron 28、PyInstaller 打包 Python 后端 |
| 容器 | `python:3.11-slim` 多阶段构建（镜像内嵌前端 `dist`） |

## 常见问题

**升级后要不要迁库？**  
不需要。服务启动时会自动检查并迁移表结构。

**改了前端为什么 Docker / 本地生产没变化？**  
需要重新 `npm run build` 前端；Docker 需重新构建镜像；桌面版需重新 `npm run build`。

**下载器连不上？**  
检查下载器 RPC 地址、账号密码与防火墙；Docker 场景注意网络与 `host.docker.internal`。

更多 FAQ 见 [`mteam-helper/README.md`](mteam-helper/README.md)。

## 参与与反馈

- Issue：<https://github.com/spellyaohui/M-Team-Helper/issues>
- 贡献前请阅读 [`AGENTS.md`](AGENTS.md)

## License

MIT（见各子项目声明；作者 [spellyaohui](https://github.com/spellyaohui)）。
