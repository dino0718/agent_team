from typing import List, Dict, Any
import re

def clean_snippet(snippet: str) -> str:
    """清理搜尋結果片段中的多餘空格和特殊字元
    
    Args:
        snippet: 搜尋結果片段
        
    Returns:
        清理後的片段
    """
    # 移除HTML標籤
    clean_text = re.sub(r'<[^>]+>', '', snippet)
    # 替換連續空白
    clean_text = re.sub(r'\s+', ' ', clean_text)
    # 修剪前後空白
    return clean_text.strip()

def filter_results(results: List[Dict[str, Any]], min_length: int = 50) -> List[Dict[str, Any]]:
    """篩選有意義的搜尋結果
    
    Args:
        results: 搜尋結果列表
        min_length: 最小內容長度
        
    Returns:
        篩選後的結果
    """
    filtered = []
    for result in results:
        if len(result.get("snippet", "")) >= min_length:
            result["snippet"] = clean_snippet(result["snippet"])
            filtered.append(result)
    return filtered

def extract_keywords(query: str) -> List[str]:
    """從查詢中提取關鍵字
    
    Args:
        query: 搜尋查詢
        
    Returns:
        關鍵字列表
    """
    # 移除常見停用詞
    stopwords = ["的", "是", "在", "有", "和", "與", "了", "我", "你", "他", "她", "它", "們", "什麼", "如何", "為什麼"]
    words = query.split()
    keywords = [word for word in words if word.lower() not in stopwords]
    return keywords
