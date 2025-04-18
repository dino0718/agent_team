from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class SearchRequest(BaseModel):
    """搜尋請求模型"""
    query: str = Field(..., description="搜尋主題或問題")
    max_results: int = Field(default=5, ge=1, le=10, description="要返回的最大結果數量")

class SearchResult(BaseModel):
    """單一搜尋結果模型"""
    title: str
    link: str
    short_link: Optional[str] = None  # 添加短網址欄位
    snippet: str
    source: str = "google"
    full_content: Optional[str] = None  # 可選的完整內容欄位

class SearchResponse(BaseModel):
    """搜尋回應模型"""
    query: str
    results: List[SearchResult]

class SummaryRequest(BaseModel):
    """摘要請求模型"""
    query: str = Field(..., description="摘要主題")
    search_results: List[Dict[str, Any]] = Field(..., description="搜尋結果列表")

class SummaryResponse(BaseModel):
    """摘要回應模型"""
    query: str
    summary: str
    sources_count: int

class SearchAndSummaryRequest(BaseModel):
    """一鍵搜尋和摘要請求模型"""
    query: str = Field(..., description="搜尋和摘要的主題")
    max_results: int = Field(default=5, ge=1, le=10, description="要返回的最大結果數量")

class SearchAndSummaryResponse(BaseModel):
    """一鍵搜尋和摘要回應模型"""
    query: str
    summary: str
    results: List[SearchResult]

# 新增的模型定義
class QueryRequest(BaseModel):
    """自然語言查詢請求模型"""
    query: str = Field(..., description="使用者的自然語言問題或指令")
    timestamp: Optional[datetime] = Field(default_factory=datetime.now, description="查詢時間")
    timezone: Optional[str] = Field(default="Asia/Taipei", description="使用者時區")

class QueryResponse(BaseModel):
    """查詢回應模型"""
    query: str = Field(..., description="原始查詢")
    answer: str = Field(..., description="報告內容")
    type: str = Field(..., description="回應類型：search_and_report, no_results, error")
    search_query: Optional[str] = Field(None, description="系統生成的搜尋關鍵字")
    used_tools: List[str] = Field(default=[], description="使用的工具清單")
    raw_results: Optional[List[Dict[str, Any]]] = Field(None, description="原始搜尋結果(如果有)")
    timestamp: Optional[datetime] = Field(None, description="查詢處理時間")
    timezone: Optional[str] = Field(None, description="使用者時區")
