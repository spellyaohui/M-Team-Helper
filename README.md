# M-Team Helper

M-Team PT 站自动化助手，支持自动下载免费种子、管理多账号、支持连接 qBittorrent/Transmission 下载器。

## 功能特性

- 多账号管理：通过 API Token 认证管理多个 M-Team 账号
- 自动下载规则：根据条件（免费/2x上传、大小、做种数、关键词等）自动下载种子
- 下载器集成：支持 qBittorrent 和 Transmission
- 促销过期自动删除：免费促销过期后自动删除未完成的种子，保护分享率
- 下载队列限制：可设置最大同时下载数，超过则暂停添加
- 标签管理：下载时自动添加标签，便于分类管理
- 下载历史：记录所有下载历史，支持查看促销状态

## 系统要求

- Python 3.10+
- Node.js 18+
- qBittorrent 或 Transmission（可选）

## 快速部署

### 1. 克隆项目

```bash
git clone <repository-url>
cd mteam-helper
```

### 2. 生产部署（推荐）

前后端合并到一个端口，只需启动后端服务即可：

```bash
# 构建前端
cd mteam-helper/frontend
npm install
npm run build

# 启动后端（同时托管前端）
cd ../backend
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env 文件配置

python main.py
# 或
uvicorn main:app --host 0.0.0.0 --port 8001
```

访问 `http://localhost:8001` 即可使用。

### 3. 开发模式

开发时可以分别启动前后端，前端通过代理访问后端 API：

```bash
# 终端 1：启动后端
cd mteam-helper/backend
python main.py

# 终端 2：启动前端开发服务器
cd mteam-helper/frontend
npm run dev
```

开发时访问 `http://localhost:4000`。

## 配置说明

### 环境变量配置

编辑 `mteam-helper/backend/.env` 文件：

```env
# M-Team 网站地址（根据你的访问地址修改）
# 常用地址：
#   https://kp.m-team.cc
#   https://test2.m-team.cc
#   https://api.m-team.cc
MTEAM_BASE_URL=https://kp.m-team.cc

# 账号刷新间隔（秒），默认 300 秒（5分钟）
REFRESH_INTERVAL=300

# 调试模式
DEBUG=True

# 数据库路径
DATABASE_URL=sqlite:///./data/mteam.db
```

### 更改 M-Team 网站地址

如果需要更改 PT 网站地址，只需修改 `mteam-helper/backend/.env` 文件中的 `MTEAM_BASE_URL` 值：

```env
MTEAM_BASE_URL=https://kp.m-team.cc
```

修改后重启后端服务即可生效。

## 使用指南

### 1. 添加账号

1. 登录 M-Team 网站，获取 API Token
2. 在「账号管理」页面添加账号，填入用户名和 API Token

### 2. 添加下载器

1. 在「下载器」页面添加 qBittorrent 或 Transmission
2. 填写地址、端口、用户名、密码
3. 如果使用 HTTPS，开启「使用 HTTPS」开关
4. 点击「测试连接」验证配置

### 3. 创建下载规则

1. 在「规则」页面添加规则
2. 选择账号、设置筛选条件（免费、大小、做种数等）
3. 选择下载器和保存路径
4. 可设置标签和最大同时下载数
5. 启用规则后，系统会自动检查并下载匹配的种子

### 4. 查看下载历史

在「历史」页面可以查看所有下载记录，包括促销类型、到期时间、下载状态等。

## 目录结构

```
mteam-helper/
├── backend/                 # Python FastAPI 后端
│   ├── main.py             # 应用入口
│   ├── config.py           # 配置管理
│   ├── database.py         # 数据库连接
│   ├── models.py           # 数据模型
│   ├── routers/            # API 路由
│   ├── services/           # 业务逻辑
│   ├── data/               # 数据目录
│   │   ├── mteam.db       # SQLite 数据库
│   │   └── torrents/      # 种子文件
│   ├── .env               # 环境变量配置
│   └── requirements.txt   # Python 依赖
│
└── frontend/               # React 前端
    ├── src/               # 源代码
    ├── package.json       # npm 依赖
    └── vite.config.ts     # Vite 配置
```

## 定时任务

系统自动运行以下定时任务：

- 每 5 分钟刷新账号信息（上传量、下载量、分享率等）
- 每 3 分钟检查自动下载规则
- 每 1 分钟检查促销过期的种子并自动删除

## 注意事项

1. **API Token 安全**：请妥善保管 API Token，不要泄露给他人
2. **分享率保护**：系统会自动删除促销过期但未完成的种子，避免影响分享率
3. **标签关联**：只有带有规则指定标签的种子才会被自动删除，手动添加的种子不受影响
4. **下载队列**：建议设置最大同时下载数，避免同时下载过多种子

## 常见问题

### Q: 如何获取 M-Team API Token？

登录 M-Team 网站 → 控制面板 → 实验室 → 存取令牌 → 生成新令牌

### Q: 连接下载器失败？

1. 检查下载器地址和端口是否正确
2. 检查用户名和密码是否正确
3. 如果使用 HTTPS，确保开启了「使用 HTTPS」开关
4. 检查下载器是否开启了 Web UI

### Q: 种子没有自动下载？

1. 检查规则是否已启用
2. 检查账号 API Token 是否有效
3. 检查下载队列是否已满（如果设置了最大下载数）
4. 查看后端日志了解详细信息

## 技术栈

**后端**
- FastAPI - REST API 框架
- SQLAlchemy - ORM
- APScheduler - 定时任务
- qbittorrent-api / transmission-rpc - 下载器集成

**前端**
- React 19 + TypeScript
- Ant Design 5 - UI 组件库
- Vite - 构建工具

## License

MIT
