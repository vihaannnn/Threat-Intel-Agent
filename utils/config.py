import os
import sys
from dotenv import load_dotenv
from typing import Optional

# Load environment variables from .env file
load_dotenv()

# Import secrets manager
try:
    from utils.secrets_manager import SecretsManager
    secrets_manager = SecretsManager()
    SECRETS_AVAILABLE = True
except ImportError:
    SECRETS_AVAILABLE = False
    secrets_manager = None

def get_config_value(key: str, default: Optional[str] = None, required: bool = False) -> Optional[str]:
    """Get configuration value with fallback chain: keyring -> .env -> environment -> default"""
    
    # Try keyring first (if available)
    if SECRETS_AVAILABLE:
        try:
            value = secrets_manager.get_key(key)
            if value:
                return value
        except Exception:
            pass
    
    # Try .env file
    value = os.getenv(key)
    if value:
        return value
    
    # Try environment variable
    value = os.getenv(key)
    if value:
        return value
    
    # Return default or raise error if required
    if required and not value:
        raise EnvironmentError(f"Missing {key}. Set it in keyring, .env file, or environment variable.")
    
    return default

# === Environment Configuration ===
OPENAI_KEY       = get_config_value("OPENAI_API_KEY", required=True)
OPENAI_MODEL     = get_config_value("OPENAI_MODEL", "gpt-4o-mini")
VALID_API_KEY    = get_config_value("MCP_API_KEY", "demo123")
LOG_LEVEL        = get_config_value("LOG_LEVEL", "INFO")
SERPER_API_KEY   = get_config_value("SERPER_API_KEY")  # Optional - for web search

# Local LLM preferences
PREFER_LOCAL_MODELS  = get_config_value("PREFER_LOCAL_MODELS", "false").lower() == "true"
PREFERRED_LOCAL_MODEL = get_config_value("PREFERRED_LOCAL_MODEL", "mistral-7b")

# Web search availability
search_engine = "serper" if SERPER_API_KEY else "duckduckgo"
# IMPORTANT: Do not print to stdout in MCP stdio processes; write to stderr
sys.stderr.write(f"Environment loaded | Model: {OPENAI_MODEL} | Log Level: {LOG_LEVEL} | Search: {search_engine}\n")
