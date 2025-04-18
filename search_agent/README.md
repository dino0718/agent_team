# 智能搜尋代理 (Search Agent)

一個基於大語言模型的智能搜尋代理，專門根據使用者的自然語言查詢搜索最新網路資訊，並生成整理後的研究報告。

## 📋 功能特點

- 🔍 **智能搜尋**：解析自然語言查詢，提取最佳搜尋關鍵詞
- 🌐 **深度爬蟲**：獲取搜尋結果的完整網頁內容，而非僅依賴簡短摘要
- 📝 **自動生成報告**：整合多來源資訊，生成全面詳細的研究報告
- 🔗 **URL縮短**：自動縮短所有URL，使報告更易閱讀
- 🕰️ **時間感知**：理解查詢中的時間元素（如：昨天、上週）
- 🚀 **容器化部署**：支援Docker容器部署，方便在各種環境中運行

## 🧠 技術架構

- **後端框架**：FastAPI
- **大語言模型**：GPT-4o-mini (OpenAI API)
- **搜尋引擎**：Google Custom Search API
- **容器化技術**：Docker 和 Docker Compose

## 🛠️ 快速開始

### 前置需求

- Python 3.9+
- Docker 和 Docker Compose (可選，用於容器化部署)
- 一個有效的 OpenAI API 金鑰
- Google Custom Search API 金鑰和搜尋引擎 ID

### 環境設置

1. 複製專案
   ```bash
   git clone https://github.com/dino0718/agent_team.git
   cd search_agent
   ```

2. 安裝依賴
   ```bash
   pip install -r requirements.txt
   ```

3. 設置環境變數
   複製.env.example為.env，並填入你的API金鑰：
   ```bash
   cp .env.example .env
   # 編輯.env文件，填入API金鑰
   ```

### 運行服務

#### 本地運行
```bash
python main.py
```

#### 使用Docker
```bash
# 建立映像
./scripts/docker_build.sh

# 啟動容器
./scripts/docker_run.sh

# 停止容器
./scripts/docker_stop.sh
```

### 訪問API
服務啟動後，API將在以下位置運行：
- 本地服務：http://localhost:8000
- API文檔：http://localhost:8000/docs

## 🔄 API端點

### 主要端點
- `POST /query`: 處理自然語言查詢，返回完整研究報告
- `POST /search`: 僅執行網頁搜尋
- `POST /search-and-summarize`: 搜尋並摘要結果
- `POST /summarize`: 對已有搜尋結果生成摘要

### 查詢範例
```json
POST /query
{
  "query": "最近的人工智能發展趨勢",
  "timestamp": "2023-06-15T14:30:00"
}
```

## ⚙️ 環境變數

必要的環境變數：
- `OPENAI_API_KEY`: OpenAI API金鑰，用於大語言模型
- `GOOGLE_API_KEY`: Google API金鑰
- `GOOGLE_CSE_ID`: Google Custom Search Engine ID

可選環境變數：
- `PORT`: API服務端口（預設：8000）

## 📂 專案結構

```
search_agent/
├── main.py                 # FastAPI主程序入口
├── models.py               # Pydantic模型定義
├── requirements.txt        # Python依賴
├── .env                    # 環境變數（需自行創建）
├── Dockerfile              # Docker配置
├── docker-compose.yml      # Docker Compose配置
├── tools/                  # 功能模組
│   ├── __init__.py
│   ├── agent.py            # LLM代理核心邏輯
│   ├── search.py           # Google搜尋工具
│   ├── summarizer.py       # 內容摘要工具
│   └── url_shortener.py    # URL縮短工具
└── scripts/                # 工具腳本
    ├── docker_build.sh
    ├── docker_run.sh
    └── docker_stop.sh
```

## 🐳 Docker部署說明

### 本地部署
使用專案根目錄的Docker Compose文件進行部署：
```bash
docker-compose up -d
```

### 雲端部署
支援部署到以下平台：
- AWS Elastic Container Service (ECS)
- Google Cloud Run
- Azure Container Instances
- Heroku

詳細的部署步驟請參考各平台的文檔。

## 🔧 進階配置

### 調整搜索深度
修改`tools/search.py`中的`max_urls_to_crawl`參數可以控制深度爬蟲的URL數量。

### 更換語言模型
如需更換使用的模型，修改`tools/agent.py`和`tools/summarizer.py`中的`self.model`變數。


