import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# === Environment Configuration ===
OPENAI_KEY      = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL    = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
VALID_API_KEY   = os.getenv("MCP_API_KEY", "demo123")
LOG_LEVEL       = os.getenv("LOG_LEVEL", "INFO")
SERPER_API_KEY  = os.getenv("SERPER_API_KEY")  # Optional - for web search

# Validate critical envs
if not OPENAI_KEY:
    raise EnvironmentError("Missing OPENAI_API_KEY in .env file")

# Web search availability
search_engine = "serper" if SERPER_API_KEY else "duckduckgo"
print(f"Environment loaded | Model: {OPENAI_MODEL} | Log Level: {LOG_LEVEL} | Search: {search_engine}")