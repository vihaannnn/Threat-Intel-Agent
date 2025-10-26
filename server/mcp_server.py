import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List
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
from utils.config import VALID_API_KEY, LOG_LEVEL, SERPER_API_KEY, OPENAI_KEY
from tools.web_search import WebSearchTool
from tools.rag_tool import OSVRAGTool

# Logging configuration
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger("MCPServer")

# Initialize MCP server
mcp = FastMCP("AI_Toolbox")

# Initialize tools
search_tool = WebSearchTool(serper_api_key=SERPER_API_KEY)
rag_tool = OSVRAGTool(openai_api_key=OPENAI_KEY)

# Simple authentication
def check_auth(api_key: str):
    """Verify API key for authentication."""
    if api_key != VALID_API_KEY:
        raise PermissionError("Invalid API key")

# ========== TOOLS ==========


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

@mcp.tool()
async def search_vulnerabilities(
    query: str,
    api_key: str,
    ecosystems: List[str] = None,
) -> Dict[str, Any]:
    """
    Search for security vulnerabilities using semantic search with metadata filtering.
    
    Args:
        query: Natural language query about vulnerabilities
        api_key: Authentication key (required)
        ecosystems: List of ecosystems to filter by (npm, PyPI, Maven, Go, Debian)
    
    Returns:
        Dictionary containing search results and metadata
    """
    check_auth(api_key)
    
    if not query or not query.strip():
        raise ValueError("Query cannot be empty")
    
    try:
        # Create ExtractedEntities object from provided parameters
        from tools.rag_tool import ExtractedEntities
        entities = ExtractedEntities(
            ecosystems=ecosystems,
            query_text=query
        )
        
        results = await rag_tool.search_vulnerabilities(
            query=query,
            entities=entities,
            limit=10
        )
        logger.info(f"search_vulnerabilities: '{query}' -> {results['total_found']} results")
        return results
    except Exception as e:
        logger.error(f"search_vulnerabilities error: {e}")
        raise

@mcp.tool()
async def get_vulnerability_by_id(
    vuln_id: str,
    api_key: str
) -> Dict[str, Any]:
    """
    Get specific vulnerability details by CVE or GHSA ID.
    
    Args:
        vuln_id: Vulnerability ID (CVE-XXXX-XXXX or GHSA-XXXX-XXXX-XXXX)
        api_key: Authentication key (required)
    
    Returns:
        Dictionary containing vulnerability details or None if not found
    
    Example:
        vuln_data = await get_vulnerability_by_id("CVE-2024-48913", api_key="demo123")
    """
    check_auth(api_key)
    
    if not vuln_id or not vuln_id.strip():
        raise ValueError("Vulnerability ID cannot be empty")
    
    # Validate ID format
    import re
    if not re.match(r'^(CVE-\d{4}-\d{4,7}|GHSA-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4})$', vuln_id, re.IGNORECASE):
        raise ValueError("Invalid vulnerability ID format. Use CVE-XXXX-XXXX or GHSA-XXXX-XXXX-XXXX")
    
    try:
        result = await rag_tool.get_vulnerability_by_id(vuln_id)
        logger.info(f"get_vulnerability_by_id: {vuln_id} -> {'found' if result else 'not found'}")
        return result
    except Exception as e:
        logger.error(f"get_vulnerability_by_id error: {e}")
        raise

# ========== RESOURCES ==========

# ========== PROMPTS ==========

# ========== MAIN ==========

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Starting MCP Server: AI_Toolbox v2.1.0")
    logger.info("=" * 60)
    logger.info(f"Log Level: {LOG_LEVEL}")
    logger.info(f"Web Search Engine: {'serper' if search_tool.serper_api_key else 'duckduckgo'}")
    logger.info("Available Tools:")
    logger.info("  - web_search: Search the web")
    logger.info("  - search_vulnerabilities: Search security vulnerabilities")
    logger.info("  - get_vulnerability_by_id: Get vulnerability by CVE/GHSA ID")
    logger.info("=" * 60)
    logger.info("Running MCP server on stdio...")
    
    try:
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server crashed: {e}", exc_info=True)
        raise