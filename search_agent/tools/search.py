import os
import httpx
import asyncio
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
import re
from .url_shortener import UrlShortener  # 導入URL縮短工具

class GoogleSearchTool:
    """使用Google Custom Search API進行網路搜尋的工具"""
    
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        self.cse_id = os.getenv("GOOGLE_CSE_ID")
        
        if not self.api_key or not self.cse_id:
            raise ValueError("Google API Key或CSE ID未設置，請檢查.env檔案")
            
        self.base_url = "https://www.googleapis.com/customsearch/v1"
        self.max_content_length = 10000  # 每個頁面最大爬取字元數
        self.max_urls_to_crawl = 5  # 最多爬取幾個URL (避免過多請求)
        
        # 初始化URL縮短工具
        self.url_shortener = UrlShortener(use_external_api=True)
    
    async def search(self, query: str, num_results: int = 10, sort_by_date: bool = True, deep_search: bool = True) -> List[Dict[str, Any]]:
        """執行Google搜尋並返回結果，可選擇是否同時爬取網頁內容
        
        Args:
            query: 搜尋關鍵字
            num_results: 要返回的結果數量 (最大10)
            sort_by_date: 是否按日期排序（最新的優先）
            deep_search: 是否爬取搜尋結果的網頁內容
            
        Returns:
            包含搜尋結果的列表
        """
        params = {
            "key": self.api_key,
            "cx": self.cse_id,
            "q": query,
            "num": min(num_results, 10)  # Google API限制最多10筆結果
        }
        
        # 如果需要按日期排序，添加sort參數
        if sort_by_date:
            params["sort"] = "date"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                
                search_results = response.json()
                
                if "items" not in search_results:
                    return []
                    
                formatted_results = []
                print("\n獲取搜尋結果:")
                
                # 處理每個搜尋結果，並縮短URL
                for i, item in enumerate(search_results["items"]):
                    original_url = item.get("link", "")
                    
                    # 縮短URL
                    short_url = await self.url_shortener.shorten(original_url)
                    
                    # 輸出原始URL和縮短URL
                    print(f"{i+1}. 標題: {item.get('title', '')}")
                    print(f"   原始連結: {original_url}")
                    print(f"   縮短連結: {short_url}")
                    print(f"   摘要: {item.get('snippet', '')[:150]}...\n")
                    
                    result = {
                        "title": item.get("title", ""),
                        "link": original_url,
                        "short_link": short_url,  # 保存縮短的URL
                        "snippet": item.get("snippet", ""),
                        "source": "google",
                        "published_date": item.get("pagemap", {}).get("metatags", [{}])[0].get("article:published_time", "")
                    }
                    formatted_results.append(result)
                
                # 如果啟用深度搜尋，爬取內容
                if deep_search:
                    print(f"\n進行深度搜尋，爬取網頁內容...")
                    return await self._enrich_search_results(formatted_results)
                    
                return formatted_results
                
        except httpx.HTTPError as e:
            print(f"搜尋時發生錯誤: {str(e)}")
            return []
    
    async def _enrich_search_results(self, search_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """爬取搜尋結果URL的完整內容，豐富搜尋結果
        
        Args:
            search_results: 原始搜尋結果列表
            
        Returns:
            豐富後的搜尋結果列表
        """
        enriched_results = []
        
        # 只處理前幾個結果以節省資源
        for i, result in enumerate(search_results[:self.max_urls_to_crawl]):
            url = result['link']
            print(f"正在爬取 ({i+1}/{min(len(search_results), self.max_urls_to_crawl)}):")
            print(f"標題: {result['title']}")
            print(f"縮短連結: {result['short_link']}")
            print(f"原始連結: {url}")
            
            full_content = await self.get_page_content(url)
            
            # 複製原始結果並添加爬取的完整內容
            enriched_result = result.copy()
            if full_content:
                # 清理獲取的內容
                clean_content = self._clean_html_content(full_content)
                enriched_result['full_content'] = clean_content
                print(f"成功爬取內容，長度: {len(clean_content)} 字元")
            else:
                print(f"無法爬取內容")
            
            enriched_results.append(enriched_result)
            print("-----------------------------------")
        
        # 添加剩餘的結果(不爬取)
        if len(search_results) > self.max_urls_to_crawl:
            enriched_results.extend(search_results[self.max_urls_to_crawl:])
        
        return enriched_results
            
    async def get_page_content(self, url: str) -> Optional[str]:
        """獲取網頁內容
        
        Args:
            url: 網頁URL
            
        Returns:
            網頁內容或None (如果獲取失敗)
        """
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml',
            'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': 'https://www.google.com/'
        }
        
        # 實現重試機制
        max_retries = 2
        retry_count = 0
        
        while retry_count <= max_retries:
            try:
                async with httpx.AsyncClient(headers=headers, timeout=15.0, follow_redirects=True) as client:
                    response = await client.get(url)
                    
                    # 檢查狀態碼
                    if 400 <= response.status_code < 600:
                        # 伺服器或客戶端錯誤
                        if retry_count < max_retries:
                            retry_count += 1
                            await asyncio.sleep(1)  # 重試前等待1秒
                            continue
                        else:
                            print(f"無法訪問網站 {url}，狀態碼: {response.status_code}")
                            return None
                    
                    response.raise_for_status()
                    
                    # 處理編碼
                    content_type = response.headers.get('content-type', '')
                    if 'charset=' in content_type:
                        charset = content_type.split('charset=')[-1].split(';')[0].strip()
                        try:
                            html_content = response.content.decode(charset)
                        except (UnicodeDecodeError, LookupError):
                            html_content = response.content.decode('utf-8', errors='replace')
                    else:
                        html_content = response.content.decode('utf-8', errors='replace')
                    
                    return html_content
                    
            except httpx.HTTPError as http_err:
                if retry_count < max_retries:
                    retry_count += 1
                    await asyncio.sleep(1)
                else:
                    print(f"HTTP錯誤 {url}: {str(http_err)}")
                    return None
            except Exception as e:
                print(f"無法獲取頁面內容 {url}: {str(e)}")
                return None
                
        return None  # 如果所有重試都失敗
    
    def _clean_html_content(self, html_content: str) -> str:
        """清理HTML內容，提取主要文本
        
        Args:
            html_content: HTML內容
            
        Returns:
            清理後的文本
        """
        try:
            # 使用BeautifulSoup解析HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 移除不需要的標籤
            for tag in soup(['script', 'style', 'meta', 'noscript', 'header', 'footer', 'nav', 'aside']):
                tag.decompose()
            
            # 提取主要內容
            main_content = ""
            
            # 嘗試找出主要內容區塊
            potential_content_elements = []
            
            # 可能的內容容器標籤
            for tag_name in ['article', 'main', 'div.content', 'div.article', 'div.post']:
                elements = soup.select(tag_name)
                if elements:
                    potential_content_elements.extend(elements)
            
            # 如果找到潛在的內容容器
            if potential_content_elements:
                # 找出最長的內容
                longest_element = max(potential_content_elements, key=lambda x: len(x.get_text(strip=True)))
                main_content = longest_element.get_text(separator=' ', strip=True)
            else:
                # 如果找不到明確的內容容器，使用頁面的段落
                paragraphs = soup.find_all('p')
                if paragraphs:
                    main_content = ' '.join(p.get_text(strip=True) for p in paragraphs)
                else:
                    # 最後的選擇：取整個頁面的文本
                    main_content = soup.get_text(separator=' ', strip=True)
            
            # 限制內容長度
            if main_content:
                main_content = re.sub(r'\s+', ' ', main_content).strip()
                main_content = main_content[:self.max_content_length]
                
                # 如果內容被截斷，添加指示
                if len(main_content) == self.max_content_length:
                    main_content += "...(內容過長，已截斷)"
                
                return main_content
            
            return "無法從此頁面提取有意義的內容"
            
        except Exception as e:
            print(f"清理HTML內容時發生錯誤: {str(e)}")
            return "內容處理錯誤"
