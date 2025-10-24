import asyncio
import logging
from datetime import datetime
from typing import Dict, Any
import aiohttp
import ssl

# WARNING: Only use this if you cannot fix SSL certificates properly
# This disables SSL verification and is insecure for production use
DISABLE_SSL_VERIFY = True  # Set to True only for testing

logger = logging.getLogger("WebSearchTool")

class WebSearchTool:
    """Web search tool supporting multiple search engines."""
    
    def __init__(self, serper_api_key: str = None):
        """
        Initialize web search tool.
        
        Args:
            serper_api_key: Serper API key (optional, falls back to DuckDuckGo)
        """
        self.serper_api_key = serper_api_key
    
    async def search_serper(self, query: str, count: int = 5) -> Dict[str, Any]:
        """
        Search using Serper API (Google Search wrapper).
        Get API key at: https://serper.dev/
        """
        if not self.serper_api_key:
            raise ValueError("SERPER_API_KEY not configured")
        
        url = "https://google.serper.dev/search"
        headers = {
            "X-API-KEY": self.serper_api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "q": query,
            "num": count
        }
        
        # Configure SSL - use proper certificates or disable for testing
        if DISABLE_SSL_VERIFY:
            logger.warning("⚠️  SSL verification is DISABLED - not secure for production!")
            connector = aiohttp.TCPConnector(ssl=False)
        else:
            # Use proper SSL context
            ssl_context = ssl.create_default_context()
            connector = aiohttp.TCPConnector(ssl=ssl_context)
        
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Serper API error {response.status}: {error_text}")
                
                data = await response.json()
                
                results = []
                for item in data.get("organic", [])[:count]:
                    results.append({
                        "title": item.get("title"),
                        "url": item.get("link"),
                        "description": item.get("snippet"),
                        "position": item.get("position")
                    })
                
                return {
                    "query": query,
                    "engine": "serper",
                    "results": results,
                    "timestamp": datetime.utcnow().isoformat()
                }
    
    async def search_duckduckgo(self, query: str, count: int = 5) -> Dict[str, Any]:
        """
        Search using DuckDuckGo (no API key required).
        Uses the duckduckgo-search library.
        Install: pip install duckduckgo-search
        """
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            raise ImportError("Install duckduckgo-search: pip install duckduckgo-search")
        
        # DuckDuckGo library is synchronous, so run in executor
        def _search():
            with DDGS() as ddgs:
                return list(ddgs.text(query, max_results=count))
        
        loop = asyncio.get_event_loop()
        raw_results = await loop.run_in_executor(None, _search)
        
        results = []
        for item in raw_results:
            results.append({
                "title": item.get("title"),
                "url": item.get("href"),
                "description": item.get("body")
            })
        
        return {
            "query": query,
            "engine": "duckduckgo",
            "results": results,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def search(
        self, 
        query: str, 
        engine: str = "auto", 
        count: int = 5
    ) -> Dict[str, Any]:
        """
        Perform web search using specified or available engine.
        
        Args:
            query: Search query string
            engine: Search engine to use ("serper", "duckduckgo", or "auto")
            count: Number of results to return (default: 5)
        
        Returns:
            Dictionary containing search results and metadata
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        
        if engine == "auto":
            # Try engines in order of preference
            if self.serper_api_key:
                engine = "serper"
            else:
                engine = "duckduckgo"
        
        logger.info(f"Searching with {engine}: '{query}'")
        
        if engine == "serper":
            return await self.search_serper(query, count)
        elif engine == "duckduckgo":
            return await self.search_duckduckgo(query, count)
        else:
            raise ValueError(f"Unknown search engine: {engine}")


# ===== STANDALONE USAGE =====
async def main():
    """Standalone test function."""
    from utils.config import SERPER_API_KEY
    
    search = WebSearchTool(serper_api_key=SERPER_API_KEY)
    
    # Test search
    query = "Python asyncio tutorial"
    print(f"\nSearching for: {query}\n")
    
    results = await search.search(query, engine="auto", count=3)
    
    print(f"Engine: {results['engine']}")
    print(f"Query: {results['query']}")
    print(f"Results: {len(results['results'])}\n")
    
    for i, result in enumerate(results['results'], 1):
        print(f"{i}. {result['title']}")
        print(f"   URL: {result['url']}")
        print(f"   {result['description'][:100]}...")
        print()


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run test
    asyncio.run(main())