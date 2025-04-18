#!/bin/bash
# 運行Docker容器

cd "$(dirname "$0")/.."

# 確保.env檔案存在
if [ ! -f .env ]; then
    echo "錯誤: .env檔案不存在"
    exit 1
fi

# 啟動容器
docker-compose up -d
echo "Docker容器已啟動"
echo "API運行於: http://localhost:8000"
echo "查看日誌: docker-compose logs -f search-agent"
