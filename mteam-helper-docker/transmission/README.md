# Transmission Docker 部署

用于测试 M-Team Helper 的 Transmission 下载器集成。

## 快速启动

```bash
cd mteam-helper-docker/transmission
docker-compose up -d
```

## 访问地址

- Web UI: http://localhost:9091
- 用户名: `admin`
- 密码: `admin123`（请在 docker-compose.yml 中修改）

## 目录说明

- `config/` - Transmission 配置文件
- `downloads/` - 下载文件存放目录
- `watch/` - 监控目录，放入 .torrent 文件自动开始下载

## 在 M-Team Helper 中配置

添加下载器时使用以下配置：

- 类型: Transmission
- 地址: `localhost`（或 Docker 宿主机 IP）
- 端口: `9091`
- 用户名: `admin`
- 密码: `admin123`

## 常用命令

```bash
# 启动
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止
docker-compose down

# 重启
docker-compose restart
```
