FROM python:3.9-slim

WORKDIR /app

# 安裝依賴
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程式檔案
COPY . .

# 設定環境變數（預設值，可在容器啟動時覆蓋）
ENV PORT=8000

# 暴露API端口
EXPOSE ${PORT}

# 啟動應用程式
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT}
