import asyncio
import logging
from datetime import datetime
from typing import Dict, Any
import sys
import os

# Add project root to path for imports
if __name__ == "__main__":
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

# MCP imports
from mcp.server.fastmcp import FastMCP

# Your project imports
from utils.config import VALID_API_KEY, LOG_LEVEL, SERPER_API_KEY
from tools.web_search import WebSearchTool

# Logging configuration
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger("MCPServer")

# Initialize MCP server
mcp = FastMCP("AI_Toolbox")

# Initialize web search tool
search_tool = WebSearchTool(serper_api_key=SERPER_API_KEY)

# Simple authentication
def check_auth(api_key: str):
    """Verify API key for authentication."""
    if api_key != VALID_API_KEY:
        raise PermissionError("Invalid API key")

# ========== TOOLS ==========

@mcp.tool()
async def add_numbers(a: int, b: int, api_key: str) -> Dict[str, Any]:
    """
    Add two numbers asynchronously.
    
    Args:
        a: First number
        b: Second number
        api_key: Authentication key
    
    Returns:
        Dictionary with result and timestamp
    """
    check_auth(api_key)
    await asyncio.sleep(0.2)
    result = a + b
    logger.info(f"add_numbers: {a} + {b} = {result}")
    return {
        "result": result,
        "operation": f"{a} + {b}",
        "time": datetime.now(datetime.UTC if hasattr(datetime, 'UTC') else datetime.timezone.utc).isoformat()
    }

@mcp.tool()
async def web_search(
    query: str, 
    api_key: str,
    engine: str = "auto", 
    count: int = 5
) -> Dict[str, Any]:
    """
    Perform a web search and return results.
    
    Args:
        query: The search query string
        api_key: Authentication key (required)
        engine: Search engine to use - "serper" (Google results), "duckduckgo" (free), or "auto" (default)
        count: Number of results to return (1-10, default: 5)
    
    Returns:
        Dictionary containing:
        - query: The search query
        - engine: Engine used ("serper" or "duckduckgo")
        - results: List of search results with title, url, description
        - timestamp: When the search was performed
    
    Example:
        results = await web_search("Python asyncio tutorial", api_key="demo123", count=3)
    """
    check_auth(api_key)
    
    if not query or not query.strip():
        raise ValueError("Query cannot be empty")
    
    if count < 1 or count > 10:
        raise ValueError("Count must be between 1 and 10")
    
    try:
        results = await search_tool.search(query, engine, count)
        logger.info(f"web_search: '{query}' -> {len(results.get('results', []))} results using {results['engine']}")
        return results
    except Exception as e:
        logger.error(f"web_search error: {e}")
        raise

# ========== RESOURCES ==========

@mcp.resource("weather://{city}")
def get_weather(city: str) -> Dict[str, Any]:
    """
    Get fake weather data for a city.
    
    Args:
        city: City name
    
    Returns:
        Dictionary with city and forecast
    """
    forecast = {
        "Durham": "Sunny 27°C",
        "NY": "Rainy 18°C",
        "London": "Foggy 15°C",
        "Tokyo": "Cloudy 22°C",
        "Paris": "Clear 20°C",
        "Sydney": "Windy 25°C"
    }
    logger.info(f"get_weather: {city}")
    return {
        "city": city, 
        "forecast": forecast.get(city, "Unknown location"),
        "time": datetime.utcnow().isoformat()
    }

# ========== PROMPTS ==========

@mcp.prompt("prompt://motivate")
def motivate(args: Dict[str, Any]) -> str:
    """
    Generate a motivational message.
    
    Args:
        args: Dictionary with optional 'name' field
    
    Returns:
        Motivational message string
    """
    who = args.get("name", "friend")
    logger.info(f"motivate: for {who}")
    return f"Keep going {who}! Every step matters. 💪"

# ========== MAIN ==========

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Starting MCP Server: AI_Toolbox v2.1.0")
    logger.info("=" * 60)
    logger.info(f"Log Level: {LOG_LEVEL}")
    logger.info(f"Web Search Engine: {'serper' if search_tool.serper_api_key else 'duckduckgo'}")
    logger.info("Available Tools:")
    logger.info("  - add_numbers: Add two numbers")
    logger.info("  - web_search: Search the web")
    logger.info("Available Resources:")
    logger.info("  - weather://{city}: Get weather data")
    logger.info("Available Prompts:")
    logger.info("  - prompt://motivate: Get motivation")
    logger.info("=" * 60)
    logger.info("Running MCP server on stdio...")
    
    try:
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server crashed: {e}", exc_info=True)
        raise