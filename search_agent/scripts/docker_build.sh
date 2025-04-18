#!/bin/bash
# 建立Docker映像

cd "$(dirname "$0")/.."
docker-compose build
echo "Docker映像建立完成"
