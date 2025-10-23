import asyncio
from mcp.client import MCPClient

async def test_connection():
    async with MCPClient.create_stdio_process(["python", "server/mcp_server.py"]) as client:
        info = await client.get_server_info()
        print("Connected to:", info.name, info.version)

        tools = await client.list_tools()
        print("\n🧰 Tools:")
        for t in tools:
            print(f"- {t.name}: {t.description}")

        res = await client.invoke_tool("add_numbers", {"a": 5, "b": 10, "api_key": "demo123"})
        print("\nadd_numbers result:", res)

if __name__ == "__main__":
    asyncio.run(test_connection())
