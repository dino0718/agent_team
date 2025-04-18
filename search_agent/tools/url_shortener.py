import hashlib
import httpx
from typing import Optional, Dict
import os

class UrlShortener:
    """URL縮短工具，支援多種縮短服務"""
    
    def __init__(self, use_external_api: bool = False):
        """初始化URL縮短工具
        
        Args:
            use_external_api: 是否使用外部API縮短網址
        """
        self.use_external_api = use_external_api
        self.short_urls_cache: Dict[str, str] = {}  # 用於緩存已經縮短過的URL
        
    async def shorten(self, url: str) -> str:
        """縮短URL
        
        Args:
            url: 原始URL
            
        Returns:
            縮短後的URL
        """
        # 檢查緩存
        if url in self.short_urls_cache:
            return self.short_urls_cache[url]
            
        # 如果設置為使用外部API
        if self.use_external_api:
            shortened = await self._shorten_with_external_api(url)
            if shortened:
                self.short_urls_cache[url] = shortened
                return shortened
        
        # 預設使用本地方法
        shortened = self._shorten_locally(url)
        self.short_urls_cache[url] = shortened
        return shortened
        
    async def _shorten_with_external_api(self, url: str) -> Optional[str]:
        """使用TinyURL API縮短URL
        
        Args:
            url: 原始URL
            
        Returns:
            縮短後的URL或None（如果失敗）
        """
        try:
            # 使用TinyURL服務，不需要API key
            tinyurl_api = f"https://tinyurl.com/api-create.php?url={url}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(tinyurl_api, timeout=5.0)
                if response.status_code == 200:
                    return response.text
                return None
        except Exception as e:
            print(f"使用外部API縮短URL時發生錯誤: {str(e)}")
            return None
    
    def _shorten_locally(self, url: str) -> str:
        """使用本地哈希算法產生短URL
        
        Args:
            url: 原始URL
            
        Returns:
            本地格式的短URL
        """
        # 生成URL的MD5雜湊值並取前8位作為短碼
        hash_object = hashlib.md5(url.encode())
        short_code = hash_object.hexdigest()[:8]
        
        # 組合成短URL格式 (使用一個假設的域名)
        return f"https://short.url/{short_code}"
