#!/bin/bash
# 停止Docker容器

cd "$(dirname "$0")/.."
docker-compose down
echo "Docker容器已停止"
