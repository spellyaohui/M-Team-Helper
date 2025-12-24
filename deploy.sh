#!/bin/bash

# ============================================================
# M-Team Helper 一键部署脚本
# 支持系统: Ubuntu/Debian, CentOS/RHEL, Fedora
# 功能: 自动安装依赖、部署应用、配置服务、设置开机自启
# ============================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置变量
REPO_URL="https://github.com/spellyaohui/M-Team-Helper.git"
INSTALL_DIR="/opt/mteam-helper"
SERVICE_NAME="mteam-helper"
APP_PORT=8001
PYTHON_VERSION="3.10"
NODE_VERSION="20"

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# 检查是否为 root 用户
check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "请使用 root 用户运行此脚本"
        log_info "使用: sudo bash deploy.sh"
        exit 1
    fi
}

# 检测系统类型
detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
        VERSION=$VERSION_ID
    elif [ -f /etc/redhat-release ]; then
        OS="centos"
    else
        log_error "不支持的操作系统"
        exit 1
    fi
    log_info "检测到系统: $OS $VERSION"
}

# 安装基础依赖
install_base_deps() {
    log_step "安装基础依赖..."
    
    case $OS in
        ubuntu|debian)
            apt-get update
            apt-get install -y curl wget git build-essential software-properties-common
            ;;
        centos|rhel|rocky|almalinux)
            yum install -y curl wget git gcc gcc-c++ make
            ;;
        fedora)
            dnf install -y curl wget git gcc gcc-c++ make
            ;;
        *)
            log_error "不支持的系统: $OS"
            exit 1
            ;;
    esac
}

# 安装 Python
install_python() {
    log_step "安装 Python ${PYTHON_VERSION}..."
    
    # 检查是否已安装
    if command -v python3 &> /dev/null; then
        CURRENT_VERSION=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
        log_info "当前 Python 版本: $CURRENT_VERSION"
        if [[ "$CURRENT_VERSION" == "3.10" || "$CURRENT_VERSION" == "3.11" || "$CURRENT_VERSION" == "3.12" ]]; then
            log_info "Python 版本满足要求，跳过安装"
            return
        fi
    fi
    
    case $OS in
        ubuntu|debian)
            add-apt-repository -y ppa:deadsnakes/ppa 2>/dev/null || true
            apt-get update
            apt-get install -y python3.10 python3.10-venv python3.10-dev python3-pip
            update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1 2>/dev/null || true
            ;;
        centos|rhel|rocky|almalinux)
            yum install -y python3 python3-pip python3-devel
            ;;
        fedora)
            dnf install -y python3 python3-pip python3-devel
            ;;
    esac
    
    # 安装 pip
    python3 -m pip install --upgrade pip 2>/dev/null || curl -sS https://bootstrap.pypa.io/get-pip.py | python3
}

# 安装 Node.js
install_nodejs() {
    log_step "安装 Node.js ${NODE_VERSION}..."
    
    # 检查是否已安装
    if command -v node &> /dev/null; then
        CURRENT_VERSION=$(node --version | cut -d. -f1 | tr -d 'v')
        log_info "当前 Node.js 版本: v$CURRENT_VERSION"
        if [ "$CURRENT_VERSION" -ge 18 ]; then
            log_info "Node.js 版本满足要求，跳过安装"
            return
        fi
    fi
    
    # 使用 NodeSource 安装
    curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | bash - 2>/dev/null || \
    curl -fsSL https://rpm.nodesource.com/setup_${NODE_VERSION}.x | bash - 2>/dev/null || true
    
    case $OS in
        ubuntu|debian)
            apt-get install -y nodejs
            ;;
        centos|rhel|rocky|almalinux|fedora)
            yum install -y nodejs || dnf install -y nodejs
            ;;
    esac
    
    # 安装 npm（如果没有）
    if ! command -v npm &> /dev/null; then
        log_warn "npm 未安装，尝试单独安装..."
        case $OS in
            ubuntu|debian)
                apt-get install -y npm
                ;;
            *)
                yum install -y npm || dnf install -y npm
                ;;
        esac
    fi
}

# 克隆或更新仓库
clone_repo() {
    log_step "获取项目代码..."
    
    if [ -d "$INSTALL_DIR" ]; then
        log_info "项目目录已存在，更新代码..."
        cd "$INSTALL_DIR"
        git fetch origin
        git reset --hard origin/main
    else
        log_info "克隆项目仓库..."
        git clone "$REPO_URL" "$INSTALL_DIR"
    fi
    
    cd "$INSTALL_DIR"
    log_info "当前版本: $(git log --oneline -1)"
}

# 配置前端（构建）
setup_frontend() {
    log_step "构建前端..."
    
    cd "$INSTALL_DIR/frontend"
    
    # 安装依赖
    log_info "安装前端依赖..."
    npm install
    
    # 构建生产版本
    log_info "构建前端生产版本..."
    npm run build
}

# 配置后端
setup_backend() {
    log_step "配置后端服务..."
    
    cd "$INSTALL_DIR/backend"
    
    # 创建虚拟环境
    log_info "创建 Python 虚拟环境..."
    python3 -m venv venv
    source venv/bin/activate
    
    # 安装依赖
    log_info "安装 Python 依赖..."
    pip install --upgrade pip
    pip install -r requirements.txt
    
    # 创建数据目录
    mkdir -p data/torrents
    
    # 创建 .env 文件（如果不存在）
    if [ ! -f .env ]; then
        log_info "创建配置文件..."
        cat > .env << EOF
# M-Team 网站地址
MTEAM_BASE_URL=https://api.m-team.cc

# 数据库配置
DATABASE_URL=sqlite:///./data/mteam.db

# 定时任务间隔（秒）
REFRESH_INTERVAL=300

# 调试模式
DEBUG=false
EOF
    fi
    
    deactivate
}

# 创建 systemd 服务
create_systemd_service() {
    log_step "创建系统服务..."
    
    cat > /etc/systemd/system/${SERVICE_NAME}.service << EOF
[Unit]
Description=M-Team Helper Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=${INSTALL_DIR}/backend
Environment="PATH=${INSTALL_DIR}/backend/venv/bin"
ExecStart=${INSTALL_DIR}/backend/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    # 重新加载 systemd
    systemctl daemon-reload
}

# 启动服务
start_services() {
    log_step "启动服务..."
    
    # 启用并启动服务
    systemctl enable ${SERVICE_NAME}
    systemctl start ${SERVICE_NAME}
    
    # 等待服务启动
    sleep 3
    
    # 检查服务状态
    log_info "检查服务状态..."
    systemctl status ${SERVICE_NAME} --no-pager || true
}

# 配置防火墙
configure_firewall() {
    log_step "配置防火墙..."
    
    # 检测防火墙类型
    if command -v ufw &> /dev/null; then
        ufw allow ${APP_PORT}/tcp 2>/dev/null || true
        log_info "已配置 UFW 防火墙，开放端口 ${APP_PORT}"
    elif command -v firewall-cmd &> /dev/null; then
        firewall-cmd --permanent --add-port=${APP_PORT}/tcp 2>/dev/null || true
        firewall-cmd --reload 2>/dev/null || true
        log_info "已配置 firewalld 防火墙，开放端口 ${APP_PORT}"
    else
        log_warn "未检测到防火墙，跳过配置"
    fi
}

# 显示安装信息
show_info() {
    # 获取服务器 IP
    SERVER_IP=$(hostname -I | awk '{print $1}')
    
    echo ""
    echo "============================================================"
    echo -e "${GREEN}M-Team Helper 部署完成！${NC}"
    echo "============================================================"
    echo ""
    echo -e "访问地址: ${BLUE}http://${SERVER_IP}:${APP_PORT}${NC}"
    echo -e "API 文档: ${BLUE}http://${SERVER_IP}:${APP_PORT}/docs${NC}"
    echo ""
    echo "常用命令:"
    echo "  查看状态: systemctl status ${SERVICE_NAME}"
    echo "  查看日志: journalctl -u ${SERVICE_NAME} -f"
    echo "  重启服务: systemctl restart ${SERVICE_NAME}"
    echo "  停止服务: systemctl stop ${SERVICE_NAME}"
    echo "  启动服务: systemctl start ${SERVICE_NAME}"
    echo ""
    echo "安装目录: ${INSTALL_DIR}"
    echo "配置文件: ${INSTALL_DIR}/backend/.env"
    echo "数据目录: ${INSTALL_DIR}/backend/data/"
    echo ""
    echo "卸载命令: sudo bash ${INSTALL_DIR}/deploy.sh uninstall"
    echo ""
    echo "============================================================"
}

# 卸载函数
uninstall() {
    log_step "卸载 M-Team Helper..."
    
    # 停止并禁用服务
    systemctl stop ${SERVICE_NAME} 2>/dev/null || true
    systemctl disable ${SERVICE_NAME} 2>/dev/null || true
    
    # 删除服务文件
    rm -f /etc/systemd/system/${SERVICE_NAME}.service
    systemctl daemon-reload
    
    # 询问是否删除数据
    read -p "是否删除数据目录？(y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$INSTALL_DIR"
        log_info "已删除安装目录和数据"
    else
        # 只删除代码，保留数据
        rm -rf "$INSTALL_DIR/frontend"
        rm -rf "$INSTALL_DIR/backend/venv"
        rm -rf "$INSTALL_DIR/.git"
        log_info "已删除程序文件，保留数据目录"
    fi
    
    log_info "卸载完成！"
}

# 更新函数
update() {
    log_step "更新 M-Team Helper..."
    
    # 停止服务
    systemctl stop ${SERVICE_NAME} 2>/dev/null || true
    
    # 更新代码
    cd "$INSTALL_DIR"
    git fetch origin
    git reset --hard origin/main
    log_info "代码已更新到: $(git log --oneline -1)"
    
    # 重新构建前端
    setup_frontend
    
    # 更新后端依赖
    cd "$INSTALL_DIR/backend"
    source venv/bin/activate
    pip install -r requirements.txt
    deactivate
    
    # 重启服务
    systemctl start ${SERVICE_NAME}
    
    log_info "更新完成！"
    systemctl status ${SERVICE_NAME} --no-pager || true
}

# 主函数
main() {
    echo ""
    echo "============================================================"
    echo "       M-Team Helper 一键部署脚本"
    echo "============================================================"
    echo ""
    
    # 检查参数
    case "$1" in
        uninstall)
            check_root
            uninstall
            exit 0
            ;;
        update)
            check_root
            update
            exit 0
            ;;
    esac
    
    check_root
    detect_os
    
    log_info "开始部署..."
    echo ""
    
    install_base_deps
    install_python
    install_nodejs
    clone_repo
    setup_frontend
    setup_backend
    create_systemd_service
    configure_firewall
    start_services
    show_info
}

# 运行主函数
main "$@"
