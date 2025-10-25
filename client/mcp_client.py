import asyncio
from mcp import ClientSession, stdio_client, StdioServerParameters

async def test_connection():
    server_params = StdioServerParameters(
        command="python",
        args=["server/mcp_server.py"]
    )
    
    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            # Initialize the session and get server info
            init_result = await session.initialize()
            print("Connected to:", init_result.serverInfo.name, init_result.serverInfo.version)

            # List tools
            tools = await session.list_tools()
            print("\nTools:")
            for t in tools.tools:
                print(f"- {t.name}: {t.description}")

            # Call a tool
            res = await session.call_tool("web_search", {"query": "Python MCP framework", "api_key": "demo123", "count": 3})
            print("\nweb_search result:", res)
if __name__ == "__main__":
    asyncio.run(test_connection())
