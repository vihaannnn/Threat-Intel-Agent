import asyncio, json
from datetime import datetime
from openai import AsyncOpenAI

from mcp import ClientSession, stdio_client, StdioServerParameters

from utils.config import OPENAI_KEY, OPENAI_MODEL, VALID_API_KEY

# Initialize LLM client
llm = AsyncOpenAI(api_key=OPENAI_KEY)

async def mcp_agent(user_query: str):
    # Connect to MCP server
    import sys
    import os
    
    # Get the project root directory
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    server_params = StdioServerParameters(
        command="python",
        args=["server/mcp_server.py"],
        env={**os.environ, "PYTHONPATH": project_root}  # Add project root to PYTHONPATH
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the session and get server info
            init_result = await session.initialize()
            server_info = init_result.serverInfo
            
            # Get tools and resources
            tools_result = await session.list_tools()
            tools = tools_result.tools
            
            resources_result = await session.list_resources()
            resources = resources_result.resources
            
            final_answer = await run_agent_loop(session, server_info, tools, resources, user_query)
            return final_answer

async def run_agent_loop(client, server_info, tools, resources, user_query: str):
    """Main agent loop that works with any MCP version."""

    final_answer = None

    # Dynamic Discovery
    tool_descriptions = [
        {"name": t.name, "description": t.description, "params": getattr(t, 'parameters', getattr(t, 'inputSchema', {}))}
        for t in tools
    ]
    resource_descriptions = [
        {"uri": getattr(r, 'uri_template', getattr(r, 'uri', r.name)), "description": getattr(r, 'description', '')}
        for r in resources
    ]

    # Scratchpad memory
    scratchpad = []
    max_steps = 6  # Increased for web search

    print(f"\nConnected to MCP server: {server_info.name if hasattr(server_info, 'name') else 'AI_Toolbox'}")
    print(f"Available tools: {[t['name'] for t in tool_descriptions]}")
    print(f"Available resources: {[r['uri'] for r in resource_descriptions]}")
    print(f"User query: {user_query}\n")

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
        - For search_vulnerabilities tool, you should extract ecosystem from the query (if available) and pass it:
        {{"query": "semantic query that would be run against the vulnerability database", "api_key": "{VALID_API_KEY}", "ecosystems": ["npm", "PyPI", "Maven", "Go", "Debian"]}}
        - For get_vulnerability_by_id tool, arguments should be: {{"vuln_id": "CVE-XXXX-XXXX", "api_key": "{VALID_API_KEY}"}}

        ECOSYSTEM EXTRACTION RULES for search_vulnerabilities:
        - ecosystems: Extract from "Node.js"→["npm"], "Python"→["PyPI"], "Java"→["Maven"], "Go"→["Go"], "Debian/Ubuntu"→["Debian"]
        - If no ecosystem is mentioned, leave ecosystems as empty array []

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
            temperature=0.0
        )

        plan_text = resp.choices[0].message.content
        print(f"\nStep {step+1} Plan:")
        print(f"   {plan_text[:200]}...")  # Show first 200 chars

        try:
            # Try to extract JSON from the response
            if "```json" in plan_text:
                plan_text = plan_text.split("```json")[1].split("```")[0].strip()
            elif "```" in plan_text:
                plan_text = plan_text.split("```")[1].split("```")[0].strip()
            
            plan = json.loads(plan_text)
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON: {e}")
            print(f"Raw response: {plan_text}")
            break

        scratchpad.append({
            "step": step+1, 
            "thought": plan.get("thought"),
            "action": plan.get("action"),
            "target": plan.get("target")
        })

        # Execution & Validation
        if plan["action"] == "use_tool":
            tool_name = plan["target"]
            arguments = plan.get("arguments", {})
            
            print(f"Executing tool: {tool_name}")
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
                
                print(f"Tool result: {result}")
                
            except Exception as e:
                result = {"error": str(e)}
                print(f"Tool error: {e}")
            
            scratchpad.append({"tool": tool_name, "result": result})

        elif plan["action"] == "use_resource":
            resource_uri = plan["target"]
            print(f"Reading resource: {resource_uri}")
            
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
                
                print(f"Resource data: {result}")
                
            except Exception as e:
                result = {"error": str(e)}
                print(f"Resource error: {e}")
            
            scratchpad.append({"resource": resource_uri, "result": result})

        elif plan["action"] == "finish":
            print("Agent decided to finish.")
            break

    # Final Answer Generation
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
        temperature=0.0
    )
    
    print("\n" + "="*60)
    print("FINAL ANSWER:")
    print("="*60)
    print(summary.choices[0].message.content)
    print("="*60)

    final_answer = summary.choices[0].message.content

    return final_answer


if __name__ == "__main__":
    test_queries = [
        "How do I remediate CVE-2025-59823?",
        "List recent npm vulnerabilities that allow bypassing authentication or CSRF protection",
        "What Python package vulnerabilities enable remote code execution in web applications?",
        "Show me recent Java vulnerabilities related to deserialization or denial of service",
        "Find Debian vulnerabilities that impact OpenSSL or the Linux kernel",
        "Are there any Go module vulnerabilities exposing insecure HTTP endpoints or missing input validation?"
        ]

    for query in test_queries:
        try:
            print("="*60)
            print(f"TESTING QUERY: {query}")
            print("="*60)
            asyncio.run(mcp_agent(query))
            
        except Exception as e:
            print(f"Query {query} failed: {e}")
            print("="*60)
