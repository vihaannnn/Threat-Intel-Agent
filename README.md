# Threat-Intel-Agent

Note: Using uv package manager. Use `uv sync` to install required packages from lock file.


# Threat-Intel-Agent

Setup - 
1. Create venv
2. Install requirments via requirements.txt



How to run - 
1. Navigate to the root directory
2. python -m client.llm_agent_dynamic
3. the server runs as the subprocess from the client


To test the connection with the server JUST FOR TESTING
1. Navigate to the root directory
2. python -m client.mcp_client



Add tools in the server. 
For large tools create new file and reference/import them in the mcp_server

Add Env Variables into your custom .env file in the root directory
they are loaded via the utils/config.py - so reference this in your tools, do not directly reference your env file

