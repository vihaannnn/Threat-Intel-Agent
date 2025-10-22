import asyncio, logging
from datetime import datetime
from typing import Dict, Any
from mcp.server.fastmcp import FastMCP
from mcp.types import ServerMetadata
from utils.config import VALID_API_KEY, LOG_LEVEL

# Logging configuration
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger("MCPServer")

# Initialize MCP server
mcp = FastMCP("AI_Toolbox")

# Metadata
mcp.set_metadata(ServerMetadata(
    name="AI_Toolbox",
    version="2.0.0",
    contact="dev@aitoolbox.com",
    description="Provides math, weather, and motivation capabilities."
))

# Simple authentication
def check_auth(api_key: str):
    if api_key != VALID_API_KEY:
        raise PermissionError("Invalid API key")

# TOOL: Add two numbers
@mcp.tool()
async def add_numbers(a: int, b: int, api_key: str) -> Dict[str, Any]:
    """Add two numbers asynchronously."""
    check_auth(api_key)
    await asyncio.sleep(0.2)
    result = a + b
    logger.info(f"add_numbers -> {result}")
    return {"result": result, "time": datetime.utcnow().isoformat()}

# RESOURCE: Fake weather
@mcp.resource("weather://{city}")
def get_weather(city: str) -> Dict[str, Any]:
    """Fake weather resource."""
    forecast = {"Durham":"Sunny 27°C","NY":"Rainy 18°C","London":"Foggy 15°C"}
    return {"city": city, "forecast": forecast.get(city, "Unknown")}

# PROMPT: Motivation
@mcp.prompt("prompt://motivate")
def motivate(args: Dict[str, Any]) -> str:
    """Motivational phrase generator."""
    who = args.get("name", "friend")
    return f"Keep going {who}! Every step matters."

# Error handler
@mcp.error_handler()
def handle_error(e: Exception):
    logger.error(f"Server error: {e}")
    return {"error": str(e)}

if __name__ == "__main__":
    logger.info("Running MCP server on stdio...")
    mcp.run()
