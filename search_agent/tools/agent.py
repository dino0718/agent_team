import os
import json
from typing import Dict, Any, List
from openai import AsyncOpenAI
from .search import GoogleSearchTool
from .summarizer import ContentSummarizer
from .url_shortener import UrlShortener  # 導入URL縮短工具
from datetime import datetime
import re

class LLMAgent:
    """基於GPT-4o-mini的主要代理，能理解使用者意圖並分析查詢主題"""
    
    def __init__(self, search_tool: GoogleSearchTool, summarizer: ContentSummarizer):
        self.api_key = os.getenv("OPENAI_API_KEY")
        
        if not self.api_key:
            raise ValueError("OpenAI API Key未設置，請檢查.env檔案")
            
        self.client = AsyncOpenAI(api_key=self.api_key)
        self.model = "gpt-4o-mini"
        self.search_tool = search_tool
        self.summarizer = summarizer
        self.url_shortener = UrlShortener(use_external_api=True)  # 初始化URL縮短工具
        
    async def process_query(self, user_query: str, timestamp: datetime = None, timezone: str = "Asia/Taipei") -> Dict[str, Any]:
        """處理使用者的自然語言查詢，分析主題並生成報告
        
        Args:
            user_query: 使用者提問或指令
            timestamp: 查詢時間
            timezone: 使用者時區
            
        Returns:
            處理結果，包含主題分析和報告內容
        """
        # 如果未提供時間，使用當前時間
        if timestamp is None:
            timestamp = datetime.now()
            
        # 格式化時間為易讀格式
        formatted_time = timestamp.strftime("%Y-%m-%d %H:%M:%S")
        
        # 步驟1: 分析使用者查詢，提取主題和關鍵詞
        query_analysis = await self._analyze_query(user_query, formatted_time, timezone)
        search_query = query_analysis["search_query"]
        max_results = query_analysis.get("max_results", 5)
        
        # 步驟2: 執行搜尋（已整合網頁爬取功能）
        print(f"使用查詢關鍵字: '{search_query}'")
        search_results = await self.search_tool.search(search_query, max_results, deep_search=True)
        
        if not search_results:
            # 搜尋無結果
            return {
                "type": "no_results",
                "query": user_query,
                "search_query": search_query,
                "answer": f"很抱歉，我找不到關於「{search_query}」的相關資訊。請嘗試使用其他關鍵字或更明確的描述。",
                "used_tools": ["search"],
            }
        
        # 步驟3: 生成解析報告
        report = await self._generate_comprehensive_report(user_query, search_query, search_results, formatted_time)
        
        return {
            "type": "search_and_report",
            "query": user_query,
            "search_query": search_query,
            "answer": report,
            "raw_results": search_results,
            "used_tools": ["search", "analyze"],
        }
    
    async def _analyze_query(self, user_query: str, formatted_time: str, timezone: str) -> Dict[str, Any]:
        """分析使用者查詢，提取主要主題和關鍵詞
        
        Args:
            user_query: 使用者提問
            formatted_time: 格式化的查詢時間
            timezone: 使用者時區
            
        Returns:
            包含搜尋關鍵字的分析結果
        """
        prompt = f"""
        你是一個專業的搜尋關鍵字分析師，需要從使用者的自然語言問題中提取最佳搜尋關鍵字。

        使用者查詢: {user_query}
        查詢時間: {formatted_time} ({timezone})
        
        請分析這個查詢，提取關鍵主題和重要詞彙，組成一個最佳的搜尋關鍵字組合。
        這些關鍵字將用於網路搜尋，以尋找最新、最相關的資訊。
        
        請特別注意查詢中可能包含的時間相關訊息，並參考現在的時間來理解使用者可能想查詢的時間範圍。
        例如，如果使用者問「昨天的新聞」，你應該考慮到查詢時間並計算出相應的日期。
        
        考慮以下因素:
        1. 識別查詢的核心主題和概念
        2. 移除無助於搜尋的詞語（如"請問"、"幫我查"等）
        3. 添加可能有助於找到更多相關資訊的同義詞或相關概念
        4. 如果查詢中有明確的時間範圍，確保在搜尋關鍵字中保留
        5. 保留時間、地點、人物等重要元素
        
        請以下列JSON格式回答:
        ```json
        {{
            "search_query": "最佳搜尋關鍵字",
            "topics": ["核心主題1", "核心主題2"],
            "time_relevant": true/false,  // 查詢是否與時間有關
            "time_reference": "查詢中提及的時間參考",  // 如果查詢有提及時間
            "max_results": 搜尋結果數量建議(1-10之間)
        }}
        ```
        
        只返回JSON格式，不要有其他文字。
        """
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一個專業的搜尋關鍵字分析師，專門從自然語言查詢中提取最佳搜尋關鍵字。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result_text = response.choices[0].message.content
            result = json.loads(result_text)
            return result
            
        except Exception as e:
            print(f"分析查詢時發生錯誤: {str(e)}")
            # 預設直接使用原始查詢
            return {
                "search_query": user_query,
                "topics": [user_query],
                "max_results": 5
            }
    
    async def _generate_comprehensive_report(self, original_query: str, search_query: str, search_results: List[Dict[str, Any]], formatted_time: str = None) -> str:
        """根據搜尋結果生成綜合報告
        
        Args:
            original_query: 原始使用者查詢
            search_query: 搜尋關鍵字
            search_results: 搜尋結果（已包含網頁內容）
            formatted_time: 格式化的查詢時間
            
        Returns:
            綜合報告
        """
        # 構建上下文
        context = ""
        
        # 建立一個URL映射表，用於后續替換報告中的URL
        url_map = {}
        
        for i, result in enumerate(search_results):
            # 確保每個結果都有縮短URL
            original_url = result['link']
            short_url = result.get('short_link')
            
            if not short_url:
                # 如果結果中沒有縮短URL，則現在生成一個
                short_url = await self.url_shortener.shorten(original_url)
                result['short_link'] = short_url
                
            # 添加到映射表
            url_map[original_url] = short_url
            
            context += f"來源 {i+1}:\n"
            context += f"標題: {result['title']}\n"
            context += f"網址: {short_url}\n"  # 在上下文中只提供縮短URL
            context += f"原始網址: {original_url}\n"
            
            # 優先使用爬取的完整內容
            if 'full_content' in result and result['full_content']:
                content_excerpt = result['full_content'][:1000] + "..." if len(result['full_content']) > 1000 else result['full_content']
                context += f"內容: {content_excerpt}\n\n"
            else:
                context += f"摘要: {result['snippet']}\n\n"
        
        time_context = f"查詢時間: {formatted_time}" if formatted_time else ""
        
        prompt = f"""
        使用者查詢: {original_query}
        {time_context}
        搜尋關鍵字: {search_query}
        
        以下是搜尋結果的相關資訊:
        
        {context}
        
        請根據以上資料，撰寫一份全面且詳細的研究報告。報告應包含:
        
        1. 主題概述：簡要介紹主題背景和重要性
        2. 關鍵發現：列出3-5個重點發現或事實
        3. 詳細分析：深入討論主題的各個方面，引用不同來源的資訊
        4. 趨勢與影響：分析主題的發展趨勢和潛在影響
        5. 結論：總結主要觀點和研究發現
        6. 資料來源：列出引用的來源
        
        重要注意事項:
        - 在報告中引用資料來源時，請統一使用縮短版本的URL（例如：{list(url_map.values())[:1]} 而不是 {list(url_map.keys())[:1]}）
        - 在「資料來源」部分必須列出所有資訊來源，並使用縮短的網址
        - 避免在報告中使用原始的冗長URL
        
        如果使用者問題涉及時間性資訊，請特別注意報告中的時間參考是否準確反映了使用者查詢時間({formatted_time})的情境。
        
        報告應該:
        - 保持客觀，以事實為基礎
        - 整合來自不同來源的資訊，提供全面視角
        - 識別資料中的模式和趨勢
        - 清晰標示信息來源
        - 如果來源間有矛盾資訊，請指出並分析可能原因
        
        請使用專業且易於理解的語言撰寫，避免過度技術性術語。
        """
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一位專業的研究分析師，擅長整合多源資訊並生成全面詳細的研究報告。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4,
                max_tokens=2500  # 增加token上限以容納詳細報告
            )
            
            report = response.choices[0].message.content
            
            # 額外檢查：查找報告中可能遺漏的原始URL並替換為縮短版本
            # 使用正則表達式查找類似URL的模式
            urls_in_report = re.findall(r'https?://[^\s)\]"\']+', report)
            for url in urls_in_report:
                # 檢查這是否是原始URL（需要被替換）
                if url in url_map:
                    report = report.replace(url, url_map[url])
                # 如果是一個新的URL（報告中生成的），也將其縮短
                elif not any(short_url == url for short_url in url_map.values()):
                    try:
                        short_url = await self.url_shortener.shorten(url)
                        report = report.replace(url, short_url)
                    except:
                        # 如果縮短失敗，保持原樣
                        pass
            
            return report
            
        except Exception as e:
            print(f"生成報告時發生錯誤: {str(e)}")
            # 即使在錯誤情況下，也嘗試使用縮短的URL
            basic_info = []
            for r in search_results[:3]:
                url = r.get('short_link', r['link'])
                basic_info.append(f"- {r['title']}: {url}")
            
            return f"在生成報告過程中遇到技術問題。以下是搜尋到的基本資訊:\n\n" + "\n\n".join(basic_info)
