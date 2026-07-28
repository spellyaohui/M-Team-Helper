# M-Team Helper 桌面版

基于 Electron 的 M-Team Helper 桌面应用，支持 Windows 系统直接运行。

## 功能特点

- 🖥️ 原生桌面应用，无需配置环境
- 🔄 后端服务自动启动和管理
- 📦 支持便携版和安装版
- 🔔 系统托盘支持，后台运行
- 💾 数据存储在用户目录，便于备份

## 系统要求

- Windows 10/11 64位
- 无需安装 Python 或 Node.js（已内置）

## 快速开始

### 方式一：下载预编译版本

从 [Releases](https://github.com/spellyaohui/M-Team-Helper/releases) 下载：

- `MTeam-Helper-Setup-x.x.x.exe` - 安装版
- `MTeam-Helper-Portable-x.x.x.exe` - 便携版（无需安装）

### 方式二：自行构建

#### 前置要求

- Node.js 18+
- Python 3.10+
- pip

#### 构建步骤

```bash
# 1. 进入桌面版目录
cd mteam-helper-desktop

# 2. 运行构建脚本
build.bat
```

构建完成后，输出文件在 `dist/` 目录：
- `MTeam-Helper-Setup-x.x.x.exe` - 安装程序
- `MTeam-Helper-Portable-x.x.x.exe` - 便携版

## 开发模式

```bash
# 进入桌面版目录
cd mteam-helper-desktop

# 运行开发脚本（会同时启动后端和 Electron）
dev.bat
```

## 数据存储

应用数据存储在用户目录：
- Windows: `%APPDATA%\mteam-helper-desktop\`

包含：
- `data/mteam.db` - 数据库
- `data/torrents/` - 种子文件

## 托盘功能

- 双击托盘图标：显示主窗口
- 右键菜单：
  - 显示主窗口
  - 打开数据目录
  - 重启后端服务
  - 退出

## 常见问题

### Q: 启动后白屏？
后端服务可能还在启动中，请等待几秒钟。如果持续白屏，右键托盘图标选择"重启后端服务"。

### Q: 如何备份数据？
打开数据目录（右键托盘图标 → 打开数据目录），复制整个 `data` 文件夹即可。

### Q: 如何迁移数据？
将旧的 `data` 文件夹复制到新电脑的相同位置。

### Q: 端口被占用？
默认使用 8001 端口，如果被占用，请关闭占用该端口的程序。

## 技术架构

```
mteam-helper-desktop/
├── main.js              # Electron 主进程
├── preload.js           # 预加载脚本
├── package.json         # 项目配置
├── build.bat            # 构建脚本
├── dev.bat              # 开发脚本
├── scripts/             # 构建辅助脚本
│   ├── build-backend.js # 后端打包脚本
│   └── build-frontend.js# 前端构建脚本
├── frontend/            # 前端构建产物（构建时生成）
└── backend-dist/        # 后端可执行文件（构建时生成）
```

## License

MIT
