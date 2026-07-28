# M-Team Helper

M-Team PT 站自动化助手，提供账号管理、种子浏览与搜索、自动下载规则、下载器联动、下载历史管理、自动删种与系统调度等能力，支持 qBittorrent 和 Transmission。

本仓库 Monorepo 总览见根目录 [README.md](../README.md)。下文为 **mteam-helper** 主应用（Web + 后端）说明。

## 项目说明

本目录包含：

- React + TypeScript 前端。
- FastAPI + SQLAlchemy 后端。
- 生产环境前后端一体化部署能力。

生产模式与 Docker 镜像下，前端会先构建为静态文件，再由后端统一托管；因此**部署时不需要像开发模式那样分别启动前端和后端**。

## 核心功能

- **多账号管理**：支持添加多个 M-Team 账号，通过 API Token 拉取账号信息。
- **种子浏览与搜索**：支持分页搜索、关键词、分类、促销、大小、做种数等过滤。
- **自动下载规则**：支持普通规则与收藏监控规则，按条件自动推送种子到下载器。
- **规则排序与精细控制**：支持规则拖拽排序、最大同时下载数、保存路径、标签、上传限速、下载限速。
- **下载器集成**：支持 qBittorrent、Transmission，多下载器管理、连接测试与状态同步。
- **下载历史管理**：支持导入已有种子、同步状态、手动上传种子、暂停、继续、删除、清空已删除记录。
- **智能删种**：支持过期删种、非免费删种、动态删种、自动删除站点已注销种子。
- **系统调度**：支持刷新间隔配置、时间段运行控制、调度器状态查看与手动重启。
- **仪表盘与日志**：支持系统统计、下载器状态概览、最近活动、日志查看与清理。
- **自动数据库迁移**：服务启动时会自动检查并补齐缺失字段，升级版本无需手工改库。

## 当前已落地的关键能力

### 自动下载规则

- 支持普通区与成人区两种模式。
- 支持普通规则与收藏监控规则。
- 支持免费、2x、体积范围、做种数、下载数、分类、关键词、排除关键词、发布时间等条件。
- 支持收藏监控后自动下载免费收藏种子。
- 支持做种后自动取消收藏。
- 支持规则排序，排序结果会持久化保存。
- 支持限制最大同时下载数，避免下载队列超限。
- 支持为单条规则配置上传限速、下载限速，推送到下载器时自动应用。

### 下载历史与状态控制

- 支持记录自动下载与手动推送的种子。
- 支持从下载器导入已有种子。
- 支持手动同步状态，导入新种子并刷新历史状态。
- 支持等待中、队列中、下载中、已暂停、已完成、做种中、已删除等状态展示。
- 支持暂停、继续、删除种子，并同步更新历史记录。
- 支持上传本地 `.torrent` 文件到下载器，并可关联 M-Team 账号补充促销信息。

### 自动删种与调度

- 支持按促销到期时间进行精准删种。
- 支持删除下载中且促销过期或非免费种子，保护分享率。
- 支持按剩余空间启用动态删种。
- 支持最旧优先、最大优先、最低分享率优先等删种策略。
- 支持自动删除站点已注销（unregistered）的种子。
- 支持时间段控制自动下载和过期检查任务是否运行。

## 系统架构

### 开发模式

- 前端通过 Vite 单独启动。
- 后端通过 FastAPI 单独启动。
- 适合本地开发和热更新调试。

### 生产模式

- 前端先构建为 `frontend/dist`。
- 后端统一托管前端静态资源和 SPA 路由。
- 服务启动时自动初始化数据库并执行迁移。
- Docker 只需要启动一个服务即可完成整套 Web 应用部署。

## 环境要求

- Docker（推荐部署方式）。
- Python 3.10+（本地部署）。
- Node.js 18+（本地部署或开发模式）。
- qBittorrent 或 Transmission（如需推送下载器）。

## 快速部署

### 方式一：Docker 部署（推荐）

Docker Hub：<https://hub.docker.com/r/spellyaohui/mteam-helper>

> ⚠️ 飞牛 NAS 等环境如果 8001 端口被占用，请自行改为其他宿主机端口，例如 `8010:8001`。

#### docker-compose

创建 `docker-compose.yml`：

```yaml
version: '3.8'

services:
  mteam-helper:
    image: spellyaohui/mteam-helper:latest
    container_name: mteam-helper
    restart: unless-stopped
    ports:
      - "8001:8001"
    volumes:
      - ./data:/app/data
    environment:
      - TZ=Asia/Shanghai
      - DEBUG=False
      - MTEAM_BASE_URL=https://api.m-team.cc
```

启动：

```bash
docker-compose up -d
```

#### docker run

```bash
docker run -d \
  --name mteam-helper \
  --restart unless-stopped \
  -p 8001:8001 \
  -v $(pwd)/data:/app/data \
  -e TZ=Asia/Shanghai \
  -e DEBUG=False \
  -e MTEAM_BASE_URL=https://api.m-team.cc \
  spellyaohui/mteam-helper:latest
```

部署完成后访问：

- Web 界面：`http://服务器IP:8001`
- API 文档：`http://服务器IP:8001/docs`
- 健康检查：`http://服务器IP:8001/health`

### 方式二：Linux 一键部署

适用于 Ubuntu、Debian、CentOS、RHEL、Fedora 等主流发行版。

```bash
curl -fsSL https://raw.githubusercontent.com/spellyaohui/M-Team-Helper/main/mteam-helper/deploy.sh -o deploy.sh
chmod +x deploy.sh
sudo bash deploy.sh
```

更新：

```bash
sudo bash /opt/mteam-helper/deploy.sh update
```

卸载：

```bash
sudo bash /opt/mteam-helper/deploy.sh uninstall
```

### 方式三：本地部署

```bash
git clone https://github.com/spellyaohui/M-Team-Helper.git
cd M-Team-Helper/mteam-helper

# 安装并构建前端
npm run install:frontend
npm run build

# 安装后端依赖
cd backend
python -m venv venv
```

Windows：

```bash
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Linux / macOS：

```bash
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

启动后访问：`http://localhost:8001`

### 方式四：开发模式

后端：

```bash
cd mteam-helper/backend
python main.py
```

前端：

```bash
cd mteam-helper/frontend
npm install
npm run dev
```

## 配置说明

后端配置文件位于 `backend/.env`，常用配置如下：

```env
MTEAM_BASE_URL=https://api.m-team.cc
DATABASE_URL=sqlite:///./data/mteam.db
DEBUG=False
```

说明：

- `MTEAM_BASE_URL`：M-Team API 地址。
- `DATABASE_URL`：数据库地址，默认使用 SQLite。
- `DEBUG`：是否启用调试模式。

## 首次使用流程

### 1. 初始化管理员账号

系统首次启动时，`/auth/check-init` 会返回是否需要初始化；首个注册用户会成为管理员。

### 2. 添加 M-Team 账号

进入 M-Team：控制面板 → 实验室 → 存取令牌，生成 API Token 后在系统中添加账号。

### 3. 添加下载器

在下载器页面添加 qBittorrent 或 Transmission，填写：

- 地址。
- 端口。
- 用户名、密码。
- 是否使用 HTTPS。

### 4. 浏览种子或手动推送

可在种子页面使用搜索、分类、促销和大小等条件筛选种子，并手动推送到下载器。

### 5. 创建自动下载规则

在规则页面配置筛选条件、下载器、保存路径、标签、最大同时下载数、上传限速和下载限速。

### 6. 配置系统设置

在系统设置页面配置：

- 刷新间隔。
- 自动删种。
- 动态删种。
- 站点已注销种子自动删除。
- 定时运行控制。
- 调度器状态查看与重启。

## 下载历史与状态说明

历史页面支持以下操作：

- **同步状态**：手动触发时会先导入下载器中的新种子，再同步所有历史记录状态。
- **上传种子**：上传本地 `.torrent` 文件到指定下载器。
- **清空已删除**：清理数据库中状态为已删除的历史记录。
- **删除记录**：删除单条记录时同步删除下载器中的种子。
- **清空历史**：删除所有历史记录及对应下载器种子。

当前常见状态：

- `pending`：等待中。
- `queued`：队列中。
- `downloading`：下载中。
- `paused`：已暂停。
- `completed`：已完成。
- `seeding`：做种中。
- `deleted`：已删除。
- `expired_deleted`：过期已删。

## 自动删种说明

系统默认针对**下载中**种子进行判断，常见删除场景包括：

- 促销已过期。
- 当前不是免费种子。
- 动态删种触发空间回收。
- Tracker 返回站点已注销。

默认不会删除：

- 已完成或正在做种的种子。
- 免费或 2x 免费种子。
- 未命中规则范围的种子。

> 提示：促销信息通常在添加种子时写入历史记录，建议手动上传种子时选择关联账号，以便自动补充促销信息。

## 数据存储与升级

默认数据目录：

```text
data/
├── mteam.db
├── torrents/
└── logs/
```

说明：

- `mteam.db`：SQLite 数据库，保存账号、规则、系统设置、下载历史等。
- `torrents/`：缓存的种子文件。
- `logs/`：系统日志文件。

升级时：

- Docker 用户通常只需要拉取新镜像并重启容器。
- 本地部署用户需要重新构建前端并重启后端。
- 新版本启动时会自动执行数据库迁移，补齐缺失字段。

## 常用运维命令

### Docker

```bash
docker logs -f mteam-helper
docker restart mteam-helper
docker pull spellyaohui/mteam-helper:latest
docker-compose down
docker-compose up -d
```

### Linux 一键部署

```bash
systemctl status mteam-helper
journalctl -u mteam-helper -f
systemctl restart mteam-helper
sudo bash /opt/mteam-helper/deploy.sh update
```

### 本地部署更新

```bash
cd mteam-helper
npm run build
cd backend
python main.py
```

## 项目结构

```text
mteam-helper/
├── backend/
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── routers/
│   ├── services/
│   ├── utils/
│   └── docs/
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── pages/
│   │   └── utils/
│   └── dist/
├── deploy.sh
├── package.json
└── README.md
```

## 更新记录

更新说明统一放在 `backend/docs/`：

- 索引入口：[backend/docs/README.md](backend/docs/README.md)
- 自动规则分类匹配与分页搜索说明：[backend/docs/auto_rule_category_pagination_update.md](backend/docs/auto_rule_category_pagination_update.md)
- 下载用户数限制说明：[backend/docs/leechers_limit_feature.md](backend/docs/leechers_limit_feature.md)

## 常见问题

### Q：Docker 部署为什么不需要分别启动前后端？

因为生产模式下前端会先构建成静态文件，再由后端统一托管；容器里只需要启动后端服务即可。

### Q：如何获取 M-Team API Token？

登录 M-Team → 控制面板 → 实验室 → 存取令牌 → 生成新令牌。

### Q：连接下载器失败怎么办？

排查顺序：

1. 检查地址和端口是否正确。
2. 检查用户名和密码。
3. 如果使用 HTTPS，确认已开启 HTTPS 开关。
4. 确保下载器已启用 Web UI / RPC。
5. Docker 部署时不要把下载器地址写成 `localhost`，应使用宿主机 IP 或 `host.docker.internal`。

### Q：种子没有自动下载？

排查顺序：

1. 检查规则是否已启用。
2. 检查账号 API Token 是否有效。
3. 检查下载器是否可连接。
4. 检查最大同时下载数是否已满。
5. 查看系统日志和调度器状态。

### Q：上传种子后为什么没有促销信息？

请在上传时选择关联的 M-Team 账号，系统会通过 API 查询并补充促销信息；未关联账号时只能保留本地上传记录。

### Q：为什么种子会被自动删除？

通常是命中了过期删种、非免费删种、动态删种或站点已注销种子自动删除策略，请先检查系统设置中的自动删种配置。

### Q：升级版本需要手工迁移数据库吗？

不需要。当前版本会在服务启动时自动执行数据库初始化与迁移检查。

## 技术栈

### 后端

- FastAPI
- SQLAlchemy 2.x
- Pydantic
- APScheduler
- httpx
- qbittorrent-api
- transmission-rpc

### 前端

- React 19
- TypeScript 5
- Ant Design
- Vite 7
- React Router 7

## 许可证

MIT
