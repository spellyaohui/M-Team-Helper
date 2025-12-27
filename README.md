# M-Team Helper

M-Team PT 站自动化助手，支持自动下载免费种子、管理多账号、支持连接 qBittorrent/Transmission 下载器。

## 功能特性

- **多账号管理**：通过 API Token 认证管理多个 M-Team 账号
- **自动下载规则**：根据条件（免费/2x上传、大小、做种数、关键词等）自动下载种子
- **智能跳过**：自动跳过 M-Team 网站上已有下载记录的种子，避免重复下载
- **支持的下载器**：qBittorrent 和 Transmission，支持同时管理多个下载器
- **智能删种**：自动删除促销过期或非免费的下载中种子，保护分享率
- **下载队列限制**：可设置最大同时下载数，精确控制不会超限
- **标签管理**：下载时自动添加标签，便于分类管理
- **种子上传**：手动上传种子文件，自动查询促销信息
- **下载历史管理**：
  - 记录所有下载历史，支持从下载器导入已有种子
  - 同步状态：自动/手动同步下载器中的种子状态
  - 删除联动：删除历史记录时同步删除下载器中的种子文件
  - 清空已删除：一键清理下载器中已删除但数据库仍存在的记录

## 系统要求

- Python 3.10+（本地部署）
- Node.js 18+（本地部署）
- Docker（Docker 部署）
- qBittorrent 或 Transmission

## 快速部署

### 方式一：Docker 部署（推荐）

最简单的部署方式，无需安装 Python 和 Node.js。

**Docker Hub 地址**：https://hub.docker.com/r/spellyaohui/mteam-helper

#### 使用 docker-compose（推荐）

创建 `docker-compose.yml` 文件：

```yaml
version: '3.8'
services:
  mteam-helper:
    image: spellyaohui/mteam-helper:latest
    container_name: mteam-helper
    ports:
      - "8001:8001"
    volumes:
      - ./data:/app/data
    environment:
      - TZ=Asia/Shanghai
    restart: unless-stopped
```

启动服务：

```bash
docker-compose up -d
```

#### 使用 docker run

```bash
docker run -d \
  --name mteam-helper \
  -p 8001:8001 \
  -v $(pwd)/data:/app/data \
  -e TZ=Asia/Shanghai \
  --restart unless-stopped \
  spellyaohui/mteam-helper:latest
```

**部署完成后：**
- 访问地址：`http://服务器IP:8001`
- API 文档：`http://服务器IP:8001/docs`

**常用命令：**
```bash
# 查看日志
docker logs -f mteam-helper

# 重启服务
docker restart mteam-helper

# 更新版本
docker pull spellyaohui/mteam-helper:latest
docker-compose down
docker-compose up -d

# 停止并删除
docker-compose down
```

**数据持久化：**
- 数据库文件：`./data/mteam.db`
- 种子文件：`./data/torrents/`

### 方式二：Linux 一键部署

支持 Ubuntu/Debian、CentOS/RHEL、Fedora 等主流 Linux 发行版。

```bash
# 下载并执行一键部署脚本
curl -fsSL https://raw.githubusercontent.com/spellyaohui/M-Team-Helper/main/deploy.sh -o deploy.sh
chmod +x deploy.sh
sudo bash deploy.sh
```

或者直接执行：

```bash
curl -fsSL https://raw.githubusercontent.com/spellyaohui/M-Team-Helper/main/deploy.sh | sudo bash
```

**脚本功能：**
- ✅ 自动检测系统类型
- ✅ 自动安装 Python 3.10+ 和 Node.js 20+
- ✅ 自动克隆项目代码
- ✅ 自动配置后端和前端
- ✅ 自动创建 systemd 服务
- ✅ 自动配置开机自启
- ✅ 自动配置防火墙

**部署完成后：**
- 访问地址：`http://服务器IP:8001`
- API 文档：`http://服务器IP:8001/docs`

**常用命令：**
```bash
# 查看服务状态
systemctl status mteam-helper

# 查看日志
journalctl -u mteam-helper -f

# 重启服务
systemctl restart mteam-helper

# 更新版本
sudo bash /opt/mteam-helper/deploy.sh update

# 卸载
sudo bash /opt/mteam-helper/deploy.sh uninstall
```

### 方式三：Windows 本地部署

```bash
# 克隆项目
git clone https://github.com/spellyaohui/M-Team-Helper.git
cd M-Team-Helper

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

### 方式四：Ubuntu/宝塔面板部署

#### 1. 安装依赖

```bash
# 安装 Python 3.10+ 和 Node.js 18+
apt update
apt install python3 python3-pip python3-venv nodejs npm -y

# 验证版本
python3 --version  # 需要 3.10+
node --version     # 需要 18+
```

#### 2. 克隆项目

```bash
cd /www/wwwroot  # 宝塔默认网站目录，可自定义
git clone https://github.com/spellyaohui/M-Team-Helper.git
cd M-Team-Helper
```

#### 3. 构建前端

```bash
cd mteam-helper/frontend
npm install
npm run build
```

#### 4. 配置后端

```bash
cd ../backend

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
nano .env  # 编辑配置
```

#### 5. 启动服务

**方式 A：简单后台运行（推荐新手）**

```bash
cd /www/wwwroot/M-Team-Helper/mteam-helper/backend
source venv/bin/activate
nohup python main.py > output.log 2>&1 &

# 查看日志
tail -f output.log

# 停止服务
pkill -f "python main.py"
```

**方式 B：Systemd 服务（推荐生产环境）**

Systemd 可以实现开机自启、崩溃自动重启。

创建服务文件：

```bash
sudo nano /etc/systemd/system/mteam-helper.service
```

写入以下内容（根据实际路径修改）：

```ini
[Unit]
Description=M-Team Helper Service
After=network.target

[Service]
Type=simple
User=www
Group=www
WorkingDirectory=/www/wwwroot/M-Team-Helper/mteam-helper/backend
Environment="PATH=/www/wwwroot/M-Team-Helper/mteam-helper/backend/venv/bin"
ExecStart=/www/wwwroot/M-Team-Helper/mteam-helper/backend/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable mteam-helper
sudo systemctl start mteam-helper

# 查看状态
sudo systemctl status mteam-helper

# 查看日志
sudo journalctl -u mteam-helper -f
```

#### 6. 宝塔面板反向代理（可选）

如果需要通过域名访问，在宝塔面板中：

1. 添加网站，绑定域名
2. 设置 → 反向代理 → 添加反向代理
3. 目标 URL：`http://127.0.0.1:8001`
4. 发送域名：`$host`

#### 7. 防火墙设置

```bash
# 如果直接通过 IP:8001 访问
sudo ufw allow 8001

# 如果使用反向代理
sudo ufw allow 80
sudo ufw allow 443
```

### 方式五：开发模式

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

### 4. 下载历史管理

在「历史」页面可以：

- **同步状态**：手动点击会先从所有下载器导入新种子，再同步所有记录的状态（页面每30秒自动同步状态，不导入新种子）
- **上传种子**：选择种子文件和下载器，关联M-Team账号可自动查询促销信息
- **清空已删除**：清理状态为「已删除」的记录（下载器中已手动删除的种子）
- **删除记录**：删除单条记录时会同步删除下载器中的种子文件
- **清空历史**：删除所有历史记录及对应的下载器种子

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
5. Docker 部署时，下载器地址不能用 `localhost`，需要用宿主机 IP 或 `host.docker.internal`

### Q: 种子没有自动下载？
1. 检查规则是否已启用
2. 检查账号 API Token 是否有效
3. 检查下载队列是否已满
4. 查看后端日志了解详情

### Q: 上传种子没有促销信息？
确保上传时选择了关联的 M-Team 账号，系统会自动通过 API 查询促销信息。

### Q: 为什么种子被自动删除了？
系统会删除下载中且非免费的种子。如果种子是50%促销或无优惠，会被自动删除以保护分享率。

### Q: 如何更新 Docker 版本？
```bash
docker pull spellyaohui/mteam-helper:latest
docker-compose down
docker-compose up -d
```

### Q: 如何更新本地部署版本？
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

## 💡 专业定制开发服务

**🚀 让 PT 自动化更进一步！**

如果您对本项目感兴趣，或希望获得更强大的功能和更贴合业务需求的解决方案，作者提供专业的定制开发服务。凭借丰富的 PT 站点开发经验和深度的技术积累，为您量身打造最适合的自动化系统。

**为什么选择我们的定制服务？**
- 🎯 **深度理解 PT 生态**：多年 PT 站点和自动化工具开发经验
- 🛠️ **全栈技术能力**：从前端 UI 到后端架构，从数据库优化到系统部署
- 📈 **性能优化专家**：解决大数据量下的性能瓶颈和系统稳定性问题
- 🔒 **安全可靠**：企业级安全标准，保护您的数据和隐私
- 💬 **持续支持**：不仅是开发，更提供长期的技术支持和系统维护

### 🎯 定制服务范围

#### PT 站点扩展
- **多站点支持**：对接其他 PT 站点（HDChina、TTG、CHDBits 等）
- **站点适配**：针对特定站点的规则引擎和数据解析
- **跨站点管理**：统一管理多个 PT 站点的种子和账号
- **站点监控**：实时监控站点状态和种子更新

#### 下载器集成
- **更多下载器支持**：Deluge、Aria2、uTorrent 等
- **云盘集成**：阿里云盘、百度网盘、OneDrive 等
- **NAS 优化**：群晖、威联通等 NAS 系统深度集成
- **远程下载**：多服务器分布式下载管理

#### 高级自动化功能
- **智能分类**：基于 AI 的种子内容识别和自动分类
- **资源去重**：跨站点资源去重和质量评估
- **做种优化**：智能做种策略和分享率管理
- **通知系统**：微信、钉钉、Telegram 等多渠道通知

#### 企业级功能
- **多用户系统**：用户权限管理和资源隔离
- **API 接口**：RESTful API 和 WebHook 支持
- **数据分析**：下载统计、趋势分析、报表生成
- **集群部署**：高可用、负载均衡、容器化部署

#### 移动端应用
- **iOS/Android 原生应用**：完整的移动端体验
- **微信小程序**：轻量级移动端管理
- **PWA 应用**：渐进式 Web 应用支持

### 🛠️ 技术服务

#### 部署与运维
- **一键部署脚本**：针对特定环境的自动化部署
- **Docker 镜像定制**：企业级 Docker 镜像和编排
- **云服务器配置**：阿里云、腾讯云、AWS 等云平台部署
- **监控告警**：系统监控、性能优化、故障告警

#### 数据迁移
- **现有数据导入**：从其他工具迁移数据
- **数据库优化**：性能调优和结构优化
- **备份恢复**：自动备份和灾难恢复方案

#### 培训与支持
- **使用培训**：系统使用和最佳实践培训
- **技术支持**：长期技术支持和维护服务
- **文档定制**：针对性的使用文档和操作手册

### 💼 合作模式

#### 功能定制
- **按需开发**：根据具体需求评估工期和费用
- **模块化开发**：可选择性集成所需功能模块
- **源码交付**：提供完整源码和技术文档

#### 技术咨询
- **架构设计**：系统架构设计和技术选型建议
- **性能优化**：现有系统性能分析和优化方案
- **安全加固**：系统安全评估和加固建议

#### 长期合作
- **技术顾问**：长期技术顾问服务
- **版本维护**：定制版本的持续更新和维护
- **功能迭代**：根据业务发展持续功能迭代

### 🎨 成功案例

- **某影视工作室**：定制多站点资源聚合系统，日处理种子数千个
- **个人 NAS 用户**：深度集成群晖系统，实现全自动化下载流程
- **PT 站点管理员**：开发站点管理后台，提升运营效率
- **企业用户**：构建内部资源管理系统，支持多部门协作

### 📞 联系方式

**项目咨询**：
- 📧 邮箱：通过 [GitHub Issues](https://github.com/spellyaohui/M-Team-Helper/issues) 联系
- 💬 即时沟通：GitHub Discussions 或 Issues 留言
- 📋 需求描述：请详细描述您的使用场景和功能需求

**响应时间**：
- 一般咨询：24小时内回复
- 紧急需求：12小时内回复
- 技术支持：工作日当天回复

**服务承诺**：
- ✅ 需求分析和方案设计免费
- ✅ 提供详细的开发计划和时间表
- ✅ 代码质量保证和测试覆盖
- ✅ 完整的部署文档和使用说明
- ✅ 后续技术支持和问题解答

---

*让技术为您的 PT 生活带来更多便利，期待与您的合作！*

## 🌟 Star History

如果这个项目对你有帮助，请给一个 ⭐ Star 支持一下！

[![Star History Chart](https://api.star-history.com/svg?repos=spellyaohui/M-Team-Helper&type=Date)](https://star-history.com/#spellyaohui/M-Team-Helper&Date)

---

**Made with ❤️ by [spellyaohui](https://github.com/spellyaohui)**

## License

MIT
