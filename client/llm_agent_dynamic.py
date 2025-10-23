import asyncio, json
from datetime import datetime
from openai import AsyncOpenAI
from mcp.client import MCPClient
from utils.config import OPENAI_KEY, OPENAI_MODEL, VALID_API_KEY

# Initialize LLM client
llm = AsyncOpenAI(api_key=OPENAI_KEY)

async def mcp_agent(user_query: str):
    async with MCPClient.create_stdio_process(["python", "server/mcp_server.py"]) as client:
        # 1️⃣ Dynamic Discovery
        server_info = await client.get_server_info()
        tools = await client.list_tools()
        resources = await client.list_resources()

        tool_descriptions = [
            {"name": t.name, "description": t.description, "params": t.parameters}
            for t in tools
        ]
        resource_descriptions = [
            {"uri": r.uri_template, "description": r.description}
            for r in resources
        ]

        # 2️⃣ Scratchpad memory
        scratchpad = []
        max_steps = 4

        print(f"\n🤖 Connected to MCP server: {server_info.name}")
        print(f"🧠 User query: {user_query}")

        for step in range(max_steps):
            reasoning_prompt = f"""
You are an autonomous AI agent connected to the MCP server "{server_info.name}".
Your GOAL: answer this question — "{user_query}"

Available TOOLS:
{json.dumps(tool_descriptions, indent=2)}

Available RESOURCES:
{json.dumps(resource_descriptions, indent=2)}

Scratchpad (your notes so far):
{json.dumps(scratchpad, indent=2)}

Return your next action as JSON:
{{
  "thought": "<your reasoning>",
  "action": "use_tool" | "use_resource" | "finish",
  "target": "<tool_name_or_uri>",
  "arguments": {{...}},
  "expected_result": "<what you hope to get>"
}}
"""
            resp = await llm.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[{"role": "system", "content": reasoning_prompt}],
                temperature=0.3
            )

            plan_text = resp.choices[0].message.content
            print(f"\n🔍 Step {step+1} plan:\n{plan_text}")

            try:
                plan = json.loads(plan_text)
            except json.JSONDecodeError:
                print("❌ Non-JSON output; aborting.")
                break

            scratchpad.append({"step": step+1, "thought": plan.get("thought")})

            # 3️⃣ Execution & Validation
            if plan["action"] == "use_tool":
                try:
                    if plan["target"] not in [t["name"] for t in tool_descriptions]:
                        raise ValueError("Tool not found.")
                    result = await client.invoke_tool(plan["target"], plan["arguments"])
                except Exception as e:
                    result = f"Error: {str(e)}"
                scratchpad.append({"action": plan["target"], "result": result})
                print(f"⚙️ Executed tool '{plan['target']}' → {result}")

            elif plan["action"] == "use_resource":
                try:
                    if plan["target"] not in [r["uri"] for r in resource_descriptions]:
                        raise ValueError("Resource not found.")
                    result = await client.read_resource(plan["target"])
                except Exception as e:
                    result = f"Error: {str(e)}"
                scratchpad.append({"action": plan["target"], "result": result})
                print(f"📚 Retrieved resource '{plan['target']}' → {result}")

            elif plan["action"] == "finish":
                print("🏁 Agent decided to finish.")
                break

        # 4️⃣ Final Answer Generation
        final_prompt = f"""
You have finished analyzing "{user_query}".
Here is your scratchpad of thoughts and results:
{json.dumps(scratchpad, indent=2)}
Now summarize your reasoning into a clear, concise final answer.
"""
        summary = await llm.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "system", "content": final_prompt}]
        )
        print("\n✅ Final Agent Answer:")
        print(summary.choices[0].message.content)

if __name__ == "__main__":
    asyncio.run(mcp_agent("Add 5 and 10, then tell me the weather in Durham and motivate me"))
