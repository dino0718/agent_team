import os
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from datetime import datetime  # 新增的導入

from models import (
    SearchRequest, SearchResponse, 
    SummaryRequest, SummaryResponse,
    SearchAndSummaryRequest, SearchAndSummaryResponse,
    QueryRequest, QueryResponse  # 新增的模型
)
from tools.search import GoogleSearchTool
from tools.summarizer import ContentSummarizer
from tools.agent import LLMAgent  # 導入新的LLM代理
from tools.utils import filter_results

# 載入環境變數
load_dotenv()

# 建立FastAPI應用
app = FastAPI(
    title="搜尋與摘要代理",
    description="一個可以搜尋網路並生成整理筆記的AI代理",
    version="1.0.0"
)

# 設置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化工具
search_tool = GoogleSearchTool()
summarizer = ContentSummarizer()
llm_agent = LLMAgent(search_tool, summarizer)  # 初始化LLM代理

@app.get("/")
async def root():
    return {"message": "歡迎使用搜尋與摘要代理"}

@app.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """執行網路搜尋"""
    try:
        # 修改為預設按日期排序搜尋最新資訊
        results = await search_tool.search(request.query, request.max_results, sort_by_date=True)
        filtered_results = filter_results(results)
        
        return SearchResponse(
            query=request.query,
            results=filtered_results
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜尋過程發生錯誤: {str(e)}")

@app.post("/summarize", response_model=SummaryResponse)
async def summarize(request: SummaryRequest):
    """根據搜尋結果生成摘要"""
    try:
        summary = await summarizer.summarize(request.search_results, request.query)
        
        return SummaryResponse(
            query=request.query,
            summary=summary,
            sources_count=len(request.search_results)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"摘要過程發生錯誤: {str(e)}")

@app.post("/search-and-summarize", response_model=SearchAndSummaryResponse)
async def search_and_summarize(request: SearchAndSummaryRequest):
    """一鍵搜尋並生成摘要"""
    try:
        # 先搜尋，修改為預設按日期排序
        results = await search_tool.search(request.query, request.max_results, sort_by_date=True)
        filtered_results = filter_results(results)
        
        # 再摘要
        summary = await summarizer.summarize(filtered_results, request.query)
        
        return SearchAndSummaryResponse(
            query=request.query,
            summary=summary,
            results=filtered_results
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜尋和摘要過程發生錯誤: {str(e)}")

# 修改自然語言查詢端點
@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """處理自然語言查詢，分析主題並生成報告"""
    try:
        # 如果沒有提供時間戳記，使用當前時間
        if not request.timestamp:
            request.timestamp = datetime.now()
        
        # 將查詢和時間信息一起傳遞給LLM代理
        result = await llm_agent.process_query(
            user_query=request.query,
            timestamp=request.timestamp,
            timezone=request.timezone
        )
        
        return QueryResponse(
            query=request.query,
            answer=result["answer"],
            type=result["type"],
            search_query=result.get("search_query"),
            used_tools=result["used_tools"],
            raw_results=result.get("raw_results"),
            timestamp=request.timestamp,
            timezone=request.timezone
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"處理查詢時發生錯誤: {str(e)}")

# 修改主程序運行部分
if __name__ == "__main__":
    # 從環境變數獲取端口或使用預設值
    port = int(os.getenv("PORT", 8000))
    
    # 啟動服務
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
