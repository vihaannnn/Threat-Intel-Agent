import asyncio, json
from datetime import datetime
from openai import AsyncOpenAI

# Try different MCP client imports based on version
try:
    from mcp.client.stdio import stdio_client, StdioServerParameters
    from mcp.client.session import ClientSession
    MCP_VERSION = "new"
except ImportError:
    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        MCP_VERSION = "medium"
    except ImportError:
        from mcp.client import MCPClient
        MCP_VERSION = "old"

from utils.config import OPENAI_KEY, OPENAI_MODEL, VALID_API_KEY

# Initialize LLM client
llm = AsyncOpenAI(api_key=OPENAI_KEY)

print(f"Using MCP version: {MCP_VERSION}")

async def mcp_agent(user_query: str):
    # Connect to MCP server based on version
    if MCP_VERSION == "new":
        # Newer MCP SDK (1.0+)
        import sys
        import os
        
        # Get the project root directory
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        server_params = StdioServerParameters(
            command="python",
            args=["-m", "server.mcp_server"],  # Run as module to fix imports
            env={**os.environ, "PYTHONPATH": project_root}  # Add project root to PYTHONPATH
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # Get server info
                result = await session.list_tools()
                tools = result.tools
                
                result = await session.list_resources()
                resources = result.resources
                
                # Try to get server info (may not be available in all versions)
                try:
                    server_info = await session.get_server_info()
                except:
                    # Create a dummy server info
                    class DummyInfo:
                        name = "AI_Toolbox"
                    server_info = DummyInfo()
                
                await run_agent_loop(session, server_info, tools, resources, user_query)


async def run_agent_loop(client, server_info, tools, resources, user_query: str):
    """Main agent loop that works with any MCP version."""
    # 1️⃣ Dynamic Discovery
    tool_descriptions = [
        {"name": t.name, "description": t.description, "params": getattr(t, 'parameters', getattr(t, 'inputSchema', {}))}
        for t in tools
    ]
    resource_descriptions = [
        {"uri": getattr(r, 'uri_template', getattr(r, 'uri', r.name)), "description": getattr(r, 'description', '')}
        for r in resources
    ]

    # 2️⃣ Scratchpad memory
    scratchpad = []
    max_steps = 6  # Increased for web search

    print(f"\n🤖 Connected to MCP server: {server_info.name if hasattr(server_info, 'name') else 'AI_Toolbox'}")
    print(f"📋 Available tools: {[t['name'] for t in tool_descriptions]}")
    print(f"📚 Available resources: {[r['uri'] for r in resource_descriptions]}")
    print(f"🧠 User query: {user_query}\n")

    for step in range(max_steps):
        reasoning_prompt = f"""
You are an autonomous AI agent connected to the MCP server.
Your GOAL: answer this question — "{user_query}"

Available TOOLS (you can use these):
{json.dumps(tool_descriptions, indent=2)}

Available RESOURCES (you can read these):
{json.dumps(resource_descriptions, indent=2)}

IMPORTANT NOTES:
- For ALL tools, you MUST include "api_key": "{VALID_API_KEY}" in the arguments
- For web_search tool, arguments should be: {{"query": "your search", "api_key": "{VALID_API_KEY}", "count": 5, "engine": "auto"}}
- For add_numbers tool, arguments should be: {{"a": 5, "b": 10, "api_key": "{VALID_API_KEY}"}}

Scratchpad (your notes so far):
{json.dumps(scratchpad, indent=2)}

Return your next action as JSON:
{{
  "thought": "<your reasoning about what to do next>",
  "action": "use_tool" | "use_resource" | "finish",
  "target": "<tool_name_or_resource_uri>",
  "arguments": {{"key": "value", "api_key": "{VALID_API_KEY}"}},
  "expected_result": "<what you hope to get>"
}}

If you have completed all necessary steps to answer the question, use "action": "finish".
"""
        resp = await llm.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "system", "content": reasoning_prompt}],
            temperature=0.3
        )

        plan_text = resp.choices[0].message.content
        print(f"\n🔍 Step {step+1} Plan:")
        print(f"   {plan_text[:200]}...")  # Show first 200 chars

        try:
            # Try to extract JSON from the response
            if "```json" in plan_text:
                plan_text = plan_text.split("```json")[1].split("```")[0].strip()
            elif "```" in plan_text:
                plan_text = plan_text.split("```")[1].split("```")[0].strip()
            
            plan = json.loads(plan_text)
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse JSON: {e}")
            print(f"Raw response: {plan_text}")
            break

        scratchpad.append({
            "step": step+1, 
            "thought": plan.get("thought"),
            "action": plan.get("action"),
            "target": plan.get("target")
        })

        # 3️⃣ Execution & Validation
        if plan["action"] == "use_tool":
            tool_name = plan["target"]
            arguments = plan.get("arguments", {})
            
            print(f"⚙️  Executing tool: {tool_name}")
            print(f"   Arguments: {json.dumps(arguments, indent=2)}")
            
            try:
                if tool_name not in [t["name"] for t in tool_descriptions]:
                    raise ValueError(f"Tool '{tool_name}' not found. Available: {[t['name'] for t in tool_descriptions]}")
                
                # Call tool based on MCP version
                if hasattr(client, 'call_tool'):
                    result = await client.call_tool(tool_name, arguments)
                    # Extract content if it's a response object
                    if hasattr(result, 'content'):
                        result = result.content
                elif hasattr(client, 'invoke_tool'):
                    result = await client.invoke_tool(tool_name, arguments)
                else:
                    # Newest version with typed requests
                    from mcp.types import CallToolRequest
                    response = await client.call_tool(CallToolRequest(name=tool_name, arguments=arguments))
                    result = response.content
                
                # Convert TextContent objects to strings for JSON serialization
                if isinstance(result, list):
                    result_text = []
                    for item in result:
                        if hasattr(item, 'text'):
                            result_text.append(item.text)
                        else:
                            result_text.append(str(item))
                    result = "\n".join(result_text)
                elif hasattr(result, 'text'):
                    result = result.text
                
                print(f"✅ Tool result: {result}")
                
            except Exception as e:
                result = {"error": str(e)}
                print(f"❌ Tool error: {e}")
            
            scratchpad.append({"tool": tool_name, "result": result})

        elif plan["action"] == "use_resource":
            resource_uri = plan["target"]
            print(f"📚 Reading resource: {resource_uri}")
            
            try:
                if not any(resource_uri.startswith(r["uri"].split("{")[0]) for r in resource_descriptions):
                    raise ValueError(f"Resource '{resource_uri}' not found.")
                
                # Call resource based on MCP version
                if hasattr(client, 'read_resource'):
                    result = await client.read_resource(resource_uri)
                    # Extract contents if it's a response object
                    if hasattr(result, 'contents'):
                        result = result.contents
                else:
                    from mcp.types import ReadResourceRequest
                    response = await client.read_resource(ReadResourceRequest(uri=resource_uri))
                    result = response.contents
                
                print(f"✅ Resource data: {result}")
                
            except Exception as e:
                result = {"error": str(e)}
                print(f"❌ Resource error: {e}")
            
            scratchpad.append({"resource": resource_uri, "result": result})

        elif plan["action"] == "finish":
            print("🏁 Agent decided to finish.")
            break

    # 4️⃣ Final Answer Generation
    final_prompt = f"""
You have finished analyzing the user's question: "{user_query}"

Here is your scratchpad of thoughts and results:
{json.dumps(scratchpad, indent=2)}

Now provide a clear, concise final answer to the user's question.
Include all relevant information you gathered from tools and resources.
Format your answer in a user-friendly way.
"""
    summary = await llm.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "system", "content": final_prompt}],
        temperature=0.5
    )
    
    print("\n" + "="*60)
    print("✅ FINAL ANSWER:")
    print("="*60)
    print(summary.choices[0].message.content)
    print("="*60)


if __name__ == "__main__":
    # Test different queries
    test_queries = [
        # Simple test
        "Add 5 and 10",
        
        # Web search test
        "Search the web for 'Python MCP framework' and tell me what you find",
        
        # Combined test
        "Add 5 and 10, tell me the weather in Durham, and search for recent AI news",
        
        # Your original complex query
        "Add 5 and 10, then tell me the weather in Durham and motivate me, also search for who won the recent Pakistan vs India Cricket match",

        "Tell me the current temperature in Bali, also tell me who won the recent Pakistan vs India Cricket match"
    ]
    
    # Run the first query (change index to test others)
    query_to_test = test_queries[4]  # Change this number (0-3) to test different queries
    
    print("="*60)
    print(f"TESTING QUERY: {query_to_test}")
    print("="*60)
    
    asyncio.run(mcp_agent(query_to_test))