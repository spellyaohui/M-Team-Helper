# M-Team Helper

M-Team PT 站自动化助手，支持自动下载免费种子、管理多账号、支持连接 qBittorrent/Transmission 下载器。

## 功能特性

- **多账号管理**：通过 API Token 认证管理多个 M-Team 账号
- **自动下载规则**：根据条件（免费/2x上传、大小、做种数、关键词等）自动下载种子
- **支持的下载器**：qBittorrent 和 Transmission
- **智能删种**：自动删除促销过期或非免费的下载中种子，保护分享率
- **下载队列限制**：可设置最大同时下载数，超过则暂停添加
- **标签管理**：下载时自动添加标签，便于分类管理
- **种子上传**：手动上传种子文件，自动查询促销信息
- **下载历史**：记录所有下载历史，支持状态同步

## 系统要求

- Python 3.10+
- Node.js 18+
- qBittorrent 或 Transmission

## 快速部署

### 1. 克隆项目

```bash
git clone https://github.com/spellyaohui/M-Team-Helper.git
cd M-Team-Helper
```

### 2. 生产部署（推荐）

```bash
# 构建前端
cd mteam-helper/frontend
npm install
npm run build

# 配置并启动后端
cd ../backend
python -m pip install -r requirements.txt
cp .env.example .env
# 编辑 .env 文件

# 启动服务
python main.py
```

访问 `http://localhost:8001` 即可使用。

### 3. 开发模式

```bash
# 终端 1：后端
cd mteam-helper/backend
python main.py

# 终端 2：前端（可选，用于热重载开发）
cd mteam-helper/frontend
npm run dev
```

## 配置说明

编辑 `mteam-helper/backend/.env` 文件：

```env
# M-Team 网站地址
MTEAM_BASE_URL=https://api.m-team.cc

# 调试模式
DEBUG=True

# 数据库路径
DATABASE_URL=sqlite:///./data/mteam.db
```

## 使用指南

### 1. 添加账号

登录 M-Team → 控制面板 → 实验室 → 存取令牌 → 生成新令牌

在「账号管理」页面添加账号，填入用户名和 API Token。

### 2. 添加下载器

在「下载器」页面添加 qBittorrent 或 Transmission，填写地址、端口、用户名、密码，点击「测试连接」验证。

### 3. 创建下载规则

在「规则」页面添加规则，设置筛选条件（免费、大小、做种数等），选择下载器和保存路径，可设置标签和最大同时下载数。

### 4. 上传种子

在「历史」页面点击「上传种子」，选择种子文件和下载器。如果关联了M-Team账号，系统会自动查询促销信息。

### 5. 系统设置

在「系统设置」页面可以配置：
- **刷新间隔**：账号刷新、种子检查、过期检查的频率
- **自动删种**：启用/禁用、删种范围、标签检查

## 定时任务

- **账号刷新**：定期获取账号信息（默认5分钟）
- **种子检查**：检查自动下载规则（默认3分钟）
- **过期检查**：检查并删除非免费/过期的下载中种子（默认1分钟）

## 智能删种规则

系统会自动删除以下情况的**下载中**种子：
1. 促销已过期（有到期时间且已过期）
2. 非免费促销（如50%、无优惠等）

**不会删除**的种子：
- 已完成/做种中的种子
- 免费或2x免费促销的种子
- 没有促销信息的种子

> ⚠️ **注意**：促销信息是在添加种子时获取并保存的，之后不会实时更新。如果网站促销状态发生变化（如临时取消免费），系统不会感知到。建议上传种子时务必关联M-Team账号以获取准确的促销信息。

## 目录结构

```
mteam-helper/
├── backend/                 # Python FastAPI 后端
│   ├── main.py             # 应用入口
│   ├── config.py           # 配置管理
│   ├── routers/            # API 路由
│   ├── services/           # 业务逻辑
│   └── data/               # 数据目录
│       ├── mteam.db        # SQLite 数据库
│       └── torrents/       # 种子文件
└── frontend/               # React 前端
    ├── src/                # 源代码
    └── dist/               # 构建输出
```

## 常见问题

### Q: 如何获取 M-Team API Token？
登录 M-Team → 控制面板 → 实验室 → 存取令牌 → 生成新令牌

### Q: 连接下载器失败？
1. 检查地址和端口是否正确
2. 检查用户名和密码
3. 如果使用 HTTPS，开启「使用 HTTPS」开关
4. 确保下载器已开启 Web UI

### Q: 种子没有自动下载？
1. 检查规则是否已启用
2. 检查账号 API Token 是否有效
3. 检查下载队列是否已满
4. 查看后端日志了解详情

### Q: 上传种子没有促销信息？
确保上传时选择了关联的 M-Team 账号，系统会自动通过 API 查询促销信息。

### Q: 为什么种子被自动删除了？
系统会删除下载中且非免费的种子。如果种子是50%促销或无优惠，会被自动删除以保护分享率。

### Q: 如何更新前端代码？
```bash
cd mteam-helper/frontend
npm run build
# 重启后端服务
```

## 技术栈

### 后端
- FastAPI、SQLAlchemy 2.x、Pydantic、APScheduler
- httpx、qbittorrent-api、transmission-rpc

### 前端
- React 19、TypeScript 5、Ant Design 5、Vite 7

## License

MIT
