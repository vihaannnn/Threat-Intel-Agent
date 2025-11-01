"""
Helper script to create .env file with API key
Run this once to set up your environment
"""

import os
from pathlib import Path

def create_env_file():
    """Create .env file with the OpenAI API key"""
    env_path = Path(".env")
    
    if env_path.exists():
        print(".env file already exists")
        overwrite = input("Do you want to overwrite it? (y/N): ").lower().strip()
        if overwrite != 'y':
            print("Aborted. Keeping existing .env file.")
            return
    
    # Prompt user for API key
    api_key = input("Enter your OpenAI API key (or press Enter to skip): ").strip()
    if not api_key:
        print("No API key provided. You'll need to set OPENAI_API_KEY in the .env file manually.")
        return
    
    env_content = f"""# Threat Intelligence Agent - Environment Configuration
# Generated automatically

# === Required API Keys ===
OPENAI_API_KEY={api_key}

# === Optional API Keys ===
# Get Serper API key from: https://serper.dev/ (for Google search)
SERPER_API_KEY=your-serper-key-here

# === Model Configuration ===
OPENAI_MODEL=gpt-4o-mini

# === Server Configuration ===
MCP_API_KEY=demo123

# Logging level (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO

# === Local Model Configuration ===
PREFER_LOCAL_MODELS=false
PREFERRED_LOCAL_MODEL=llama-3.1-70b
"""
    
    with open(env_path, 'w') as f:
        f.write(env_content)
    
    print(".env file created successfully")
    print(f"Location: {env_path.absolute()}")
    print(f"OpenAI API Key configured: {api_key[:20]}...")

if __name__ == "__main__":
    create_env_file()


