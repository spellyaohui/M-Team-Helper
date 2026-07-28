#!/bin/bash

# M-Team Helper Docker 镜像构建和推送脚本
# 用法: ./build-and-push.sh [版本号]
# 示例: ./build-and-push.sh 1.0.0

set -e

# Docker Hub 用户名
DOCKER_USER="spellyaohui"
IMAGE_NAME="mteam-helper"

# 获取版本号
VERSION=${1:-"latest"}

echo "=========================================="
echo "M-Team Helper Docker 构建脚本"
echo "=========================================="
echo "镜像: ${DOCKER_USER}/${IMAGE_NAME}"
echo "版本: ${VERSION}"
echo "=========================================="

# 切换到项目根目录（mteam-helper-docker 的上级目录）
cd "$(dirname "$0")/.."

# 检查 mteam-helper 目录是否存在
if [ ! -d "mteam-helper" ]; then
    echo "错误: 找不到 mteam-helper 目录"
    echo "请确保目录结构如下:"
    echo "  ├── mteam-helper/"
    echo "  └── mteam-helper-docker/"
    exit 1
fi

# 检查 Docker 是否登录
if ! docker info | grep -q "Username"; then
    echo "请先登录 Docker Hub:"
    echo "  docker login"
    exit 1
fi

# 构建镜像（使用 mteam-helper-docker 目录下的 Dockerfile）
echo ""
echo ">>> 开始构建镜像..."
docker build -t ${DOCKER_USER}/${IMAGE_NAME}:${VERSION} -f mteam-helper-docker/Dockerfile .

# 如果不是 latest，同时打上 latest 标签
if [ "$VERSION" != "latest" ]; then
    echo ""
    echo ">>> 添加 latest 标签..."
    docker tag ${DOCKER_USER}/${IMAGE_NAME}:${VERSION} ${DOCKER_USER}/${IMAGE_NAME}:latest
fi

# 推送镜像
echo ""
echo ">>> 推送镜像到 Docker Hub..."
docker push ${DOCKER_USER}/${IMAGE_NAME}:${VERSION}

if [ "$VERSION" != "latest" ]; then
    docker push ${DOCKER_USER}/${IMAGE_NAME}:latest
fi

echo ""
echo "=========================================="
echo "✅ 构建和推送完成！"
echo ""
echo "拉取镜像:"
echo "  docker pull ${DOCKER_USER}/${IMAGE_NAME}:${VERSION}"
echo "  docker pull ${DOCKER_USER}/${IMAGE_NAME}:latest"
echo "=========================================="
