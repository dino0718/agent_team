import os
import re
import httpx
import asyncio
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional # Removed Tuple as it's unused
from openai import AsyncOpenAI

class ContentSummarizer:
    """使用GPT-4o-mini生成搜尋結果摘要的工具，支援深度爬蟲"""
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        
        if not self.api_key:
            raise ValueError("OpenAI API Key未設置，請檢查.env檔案")
            
        self.client = AsyncOpenAI(api_key=self.api_key)
        self.model = "gpt-4o-mini"
        # 添加HTTP客戶端
        self.max_content_length = 10000  # 每個網頁最大抓取字元數
        self.max_urls_to_crawl = 10  # 最多爬取幾個URL
        self.max_retries = 3 # Define max_retries here
    
    async def summarize(self, search_results: List[Dict[str, Any]], query: str, deep_search: bool = True) -> str:
        """使用GPT-4o-mini摘要搜尋結果，可選擇是否深度爬蟲獲取更多內容
        
        Args:
            search_results: 搜尋結果列表
            query: 原始查詢
            deep_search: 是否執行深度爬蟲獲取完整內容
            
        Returns:
            摘要內容
        """
        # 準備給GPT的上下文
        context = ""
        
        # 如果啟用深度搜尋，先爬取URL內容
        enriched_results = search_results
        if (deep_search):
            enriched_results = await self._enrich_search_results(search_results)
        
        # 構建上下文
        for i, result in enumerate(enriched_results):
            context += f"來源 {i+1}:\n"
            context += f"標題: {result['title']}\n"
            context += f"URL: {result['link']}\n"
            
            # 如果有爬取到的內容，就使用爬取內容
            if 'full_content' in result and result['full_content']:
                context += f"內容: {result['full_content']}\n\n"
            else:
                # 否則使用Google API返回的摘要
                context += f"摘要: {result['snippet']}\n\n"
        
        prompt = f"""
        我需要你根據以下搜尋結果來生成有關「{query}」的詳細整理筆記。
        
        搜尋結果:
        {context}
        
        請按照以下格式生成筆記：
        1. 主題概述 (簡要解釋主題)
        2. 重要發現與趨勢 (列出3-5個重點)
        3. 相關細節與事實 (整理重要細節與事實)
        4. 結論
        5. 引用來源 (列出資訊來源)
        
        請確保筆記是以事實為基礎的，並且資訊是整合自所有提供的來源。
        如果有不同的來源提供相互矛盾的信息，請指出這些差異。
        """
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一位專業的研究助理，擅長整理與摘要網路上的最新資訊。你的分析應該詳盡而全面，包含深度研究的觀點。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000  # 增加token上限以容納更詳細的回應
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"摘要生成時發生錯誤: {str(e)}")
            return f"摘要生成失敗: {str(e)}"
    
    async def _enrich_search_results(self, search_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """爬取搜尋結果URL的完整內容，豐富搜尋結果
        
        Args:
            search_results: 原始搜尋結果列表
            
        Returns:
            豐富後的搜尋結果列表
        """
        enriched_results = []
        
        # 只處理前幾個結果以節省資源
        tasks = []
        for result in search_results[:self.max_urls_to_crawl]:
            tasks.append(self._extract_content_from_url(result['link']))
            
        contents = await asyncio.gather(*tasks)

        for i, result in enumerate(search_results[:self.max_urls_to_crawl]):
            # 複製原始結果並添加爬取的完整內容
            enriched_result = result.copy()
            if contents[i]:
                enriched_result['full_content'] = contents[i]
            enriched_results.append(enriched_result)
        
        # 添加剩餘的結果(不爬取)
        if len(search_results) > self.max_urls_to_crawl:
            enriched_results.extend(search_results[self.max_urls_to_crawl:])
        
        return enriched_results
    
    async def _extract_content_from_url(self, url: str) -> Optional[str]:
        """從URL爬取並提取有價值的內容
        
        Args:
            url: 要爬取的網頁URL
            
        Returns:
            提取並清理後的內容，或者None(如果爬取失敗)
        """
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36', # Added comma
            'Accept': 'text/html,application/xhtml+xml,application/xml',
            'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7', # Moved to new line
        }
        
        html_content = None # Initialize html_content
        retry_count = 0
        
        async with httpx.AsyncClient(headers=headers, timeout=15.0, follow_redirects=True) as client:
            while retry_count < self.max_retries:
                try:
                    response = await client.get(url)
                    response.raise_for_status() # Check for HTTP errors (4xx or 5xx)

                    # httpx 不支援 apparent_encoding，使用 charset 偵測或預設編碼
                    # 嘗試從 content-type 標頭獲取編碼
                    content_type = response.headers.get('content-type', '')
                    charset = None
                    if 'charset=' in content_type:
                        charset_part = content_type.split('charset=')[-1].split(';')[0].strip()
                        try:
                            # Test if charset is valid
                            ''.encode(charset_part)
                            charset = charset_part
                        except LookupError:
                            print(f"從 {url} 獲取到無效的charset: {charset_part}，將嘗試UTF-8")
                            charset = None # Fallback to default

                    try:
                        if charset:
                            html_content = response.content.decode(charset)
                        else:
                             # 預設使用 utf-8，並在錯誤時使用替換字符
                            html_content = response.content.decode('utf-8', errors='replace')
                    except UnicodeDecodeError:
                         # 如果指定編碼失敗或預設UTF-8失敗，再次嘗試UTF-8替換
                        print(f"從 {url} 解碼內容時發生錯誤 (Charset: {charset})，強制使用UTF-8替換")
                        html_content = response.content.decode('utf-8', errors='replace')

                    # If successful, break the retry loop
                    break

                except httpx.HTTPStatusError as http_err:
                    # Handle HTTP errors (e.g., 404, 500, 520)
                    retry_count += 1
                    print(f"從 {url} 爬取內容時遇到HTTP錯誤 {http_err.response.status_code}，正在進行第 {retry_count} 次重試...")
                    if retry_count >= self.max_retries:
                        print(f"從 {url} 爬取內容失敗：達到最大重試次數，最後錯誤: {http_err}")
                        return f"無法訪問此網站，伺服器返回錯誤: {http_err.response.status_code}"
                    await asyncio.sleep(1) # Wait before retrying

                except httpx.RequestError as req_err:
                    # Handle other request errors (e.g., connection error, timeout)
                    retry_count += 1
                    print(f"從 {url} 爬取內容時遇到請求錯誤: {str(req_err)}，正在進行第 {retry_count} 次重試...")
                    if retry_count >= self.max_retries:
                         print(f"從 {url} 爬取內容失敗：達到最大重試次數，最後錯誤: {req_err}")
                         return f"無法從該網站獲取內容：{str(req_err)}"
                    await asyncio.sleep(1) # Wait before retrying
                
                except Exception as e:
                    # Catch any other unexpected errors during request/decoding
                    print(f"從 {url} 爬取或解碼內容時發生未預期錯誤: {str(e)}")
                    return None # Return None for unexpected errors

        if html_content is None:
             # This case should ideally be handled by the retry logic, but as a fallback
             print(f"從 {url} 爬取內容失敗：所有重試嘗試都失敗了")
             return None

        # 清理和提取內容
        try:
            clean_text = self._clean_html(html_content)
            return clean_text
        except Exception as e:
            print(f"從 {url} 清理HTML內容時發生錯誤: {str(e)}")
            return "內容處理錯誤"


    def _clean_html(self, html_content: str) -> str: # Corrected method signature and indentation
        """清理HTML內容，提取有用的文本
        
        Args:
            html_content: 原始HTML內容
            
        Returns:
            清理後的文本內容
        """            
        try: # Corrected indentation
            # 使用BeautifulSoup解析HTML
            soup = BeautifulSoup(html_content, 'html.parser') # Corrected indentation
            
            # 移除不需要的標籤
            for tag in soup(['script', 'style', 'meta', 'noscript', 'header', 'footer', 'nav', 'aside']): # Corrected indentation
                tag.decompose() # Corrected indentation
                
            # 提取主要內容
            main_content = "" # Corrected indentation
            
            # 嘗試找出主要內容區塊
            potential_content_elements = [] # Corrected indentation
            
            # 可能的內容容器標籤
            for tag_name in ['article', 'main', 'div.content', 'div.article', 'div.post', 'body']: # Added 'body' as fallback, Corrected indentation
                elements = soup.select(tag_name) # Corrected indentation
                if elements: # Corrected indentation
                    potential_content_elements.extend(elements) # Corrected indentation
                    
            # 如果找到潛在的內容容器
            if potential_content_elements: # Corrected indentation
                # 找出最長的內容
                # Filter out elements with very short text to avoid selecting headers/footers if body is the only match
                filtered_elements = [el for el in potential_content_elements if len(el.get_text(strip=True)) > 100] # Heuristic length filter
                if filtered_elements:
                     longest_element = max(filtered_elements, key=lambda x: len(x.get_text(strip=True)))
                elif potential_content_elements: # If filtering removed everything, fall back to the longest of the original list
                     longest_element = max(potential_content_elements, key=lambda x: len(x.get_text(strip=True)))
                else: # Should not happen if body is included, but as safeguard
                    longest_element = soup # Fallback to whole soup if no elements found

                main_content = longest_element.get_text(separator=' ', strip=True) # Corrected indentation
            else:
                # 如果找不到明確的內容容器，使用頁面的段落 (Should be less likely now with 'body' tag)
                paragraphs = soup.find_all('p') # Corrected indentation
                if paragraphs: # Corrected indentation
                    main_content = ' '.join(p.get_text(strip=True) for p in paragraphs) # Corrected indentation
                else:
                    # 最後的選擇：取整個頁面的文本
                    main_content = soup.get_text(separator=' ', strip=True) # Corrected indentation
            
            # 限制內容長度
            if main_content: # Corrected indentation
                main_content = re.sub(r'\s+', ' ', main_content).strip() # Corrected indentation
                original_length = len(main_content) # Store original length before potential truncation
                main_content = main_content[:self.max_content_length] # Corrected indentation
                
                # 如果內容被截斷，添加指示
                if len(main_content) < original_length: # Check if truncation actually happened
                    main_content += "...(內容過長，已截斷)" # Corrected indentation
                
                return main_content # Corrected indentation
            
            return "無法從此頁面提取有意義的內容" # Corrected indentation
            
        except Exception as e: # Corrected indentation
            print(f"清理HTML內容時發生錯誤: {str(e)}") # Corrected indentation
            return "內容處理錯誤" # Corrected indentation
