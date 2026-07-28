# M-Team Helper

M-Team PT 站自动化助手，支持自动下载免费种子、管理多账号、连接 qBittorrent/Transmission 下载器。

## 功能特性

- 多账号管理（API Token 认证）
- 自动下载规则（免费/2x上传、大小、做种数、关键词筛选）
- 支持 qBittorrent 和 Transmission
- 智能删种（自动删除促销过期的下载中种子）
- 下载历史管理（同步状态、批量删除）
- 标签管理

## 快速开始

### 方式一：Docker Compose（推荐）

```bash
mkdir mteam-helper && cd mteam-helper

# 下载 docker-compose.yml
curl -O https://raw.githubusercontent.com/spellyaohui/M-Team-Helper/main/docker/docker-compose.yml

# 启动
docker-compose up -d
```

### 方式二：Docker 命令

```bash
docker run -d \
  --name mteam-helper \
  --restart unless-stopped \
  -p 8001:8001 \
  -v $(pwd)/data:/app/data \
  -e TZ=Asia/Shanghai \
  spellyaohui/mteam-helper:latest
```

## 端口映射

| 容器端口 | 说明 |
|---------|------|
| 8001 | Web 界面和 API |

默认映射到主机 8001 端口，可自定义：

```bash
# 映射到主机 9000 端口
docker run -d -p 9000:8001 ...
```

> ⚠️ **飞牛 NAS 用户注意**：飞牛系统会占用 8001 端口，建议改用其他端口（如 `8010:8001`）。

## 数据持久化

**重要**：必须挂载 `/app/data` 目录以持久化数据，否则容器删除后数据丢失。

```bash
-v /your/path/data:/app/data
```

数据目录结构：
```
data/
├── mteam.db      # SQLite 数据库（账号、规则、历史等）
└── torrents/     # 下载的种子文件
```

### 备份与恢复

```bash
# 备份
cp -r ./data ./data-backup-$(date +%Y%m%d)

# 恢复
docker stop mteam-helper
cp -r ./data-backup-xxx/* ./data/
docker start mteam-helper
```

## 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| TZ | Asia/Shanghai | 时区 |
| DEBUG | False | 调试模式 |
| MTEAM_BASE_URL | https://api.m-team.cc | M-Team API 地址 |

## 访问地址

- Web 界面：`http://IP:8001`
- API 文档：`http://IP:8001/docs`

## 常用命令

```bash
# 查看日志
docker logs -f mteam-helper

# 重启
docker restart mteam-helper

# 更新
docker pull spellyaohui/mteam-helper:latest
docker stop mteam-helper && docker rm mteam-helper
docker run -d --name mteam-helper ...
```

## 相关链接

- GitHub：https://github.com/spellyaohui/M-Team-Helper
- 问题反馈：https://github.com/spellyaohui/M-Team-Helper/issues
