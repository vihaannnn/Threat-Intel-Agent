"""
Secrets Manager for API Keys
Uses keyring for secure storage with CLI interface
"""

import keyring
import getpass
import sys
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger("SecretsManager")

class SecretsManager:
    """Secure API key management using keyring"""
    
    SERVICE_NAME = "threat-intel-agent"
    
    # Supported API keys
    SUPPORTED_KEYS = {
        "OPENAI_API_KEY": {
            "description": "OpenAI API key for GPT models",
            "required": True,
            "example": "sk-proj-..."
        },
        "SERPER_API_KEY": {
            "description": "Serper API key for Google search (optional)",
            "required": False,
            "example": "your-serper-key"
        },
        "MCP_API_KEY": {
            "description": "MCP server authentication key",
            "required": False,
            "example": "demo123"
        }
    }
    
    def __init__(self):
        self.service = self.SERVICE_NAME
    
    def set_key(self, key_name: str, value: str) -> bool:
        """Set an API key securely"""
        if key_name not in self.SUPPORTED_KEYS:
            logger.error(f"Unsupported key: {key_name}")
            return False
        
        try:
            keyring.set_password(self.service, key_name, value)
            logger.info(f"{key_name} stored securely")
            return True
        except Exception as e:
            logger.error(f"Failed to store {key_name}: {e}")
            return False
    
    def get_key(self, key_name: str) -> Optional[str]:
        """Get an API key securely"""
        try:
            return keyring.get_password(self.service, key_name)
        except Exception as e:
            logger.error(f"Failed to retrieve {key_name}: {e}")
            return None
    
    def delete_key(self, key_name: str) -> bool:
        """Delete an API key"""
        try:
            keyring.delete_password(self.service, key_name)
            logger.info(f"{key_name} deleted")
            return True
        except Exception as e:
            logger.error(f"Failed to delete {key_name}: {e}")
            return False
    
    def list_keys(self) -> Dict[str, bool]:
        """List all stored keys and their status"""
        status = {}
        for key_name in self.SUPPORTED_KEYS:
            status[key_name] = self.get_key(key_name) is not None
        return status
    
    def interactive_setup(self):
        """Interactive setup for all API keys"""
        print("Threat Intelligence Agent - API Key Setup")
        print("=" * 50)
        
        for key_name, info in self.SUPPORTED_KEYS.items():
            print(f"\n{key_name}:")
            print(f"  Description: {info['description']}")
            print(f"  Required: {'Yes' if info['required'] else 'No'}")
            print(f"  Example: {info['example']}")
            
            current_value = self.get_key(key_name)
            if current_value:
                print(f"  Current: {'*' * 20} (already set)")
                update = input("  Update? (y/N): ").lower().strip()
                if update != 'y':
                    continue
            
            if info['required']:
                value = getpass.getpass(f"  Enter {key_name}: ")
            else:
                value = input(f"  Enter {key_name} (or press Enter to skip): ")
            
            if value.strip():
                self.set_key(key_name, value.strip())
            elif info['required']:
                print(f"  {key_name} is required!")
        
        print("\n" + "=" * 50)
        print("Setup complete!")
        self.show_status()
    
    def show_status(self):
        """Show current key status"""
        print("\nCurrent API Key Status:")
        print("-" * 30)
        
        status = self.list_keys()
        for key_name, is_set in status.items():
            info = self.SUPPORTED_KEYS[key_name]
            status_text = "[SET]" if is_set else "[NOT SET]"
            required_text = "[REQUIRED]" if info['required'] else "[OPTIONAL]"
            print(f"{status_text} {required_text} {key_name}")
        
        print("\nLegend: [SET] / [NOT SET] | [REQUIRED] / [OPTIONAL]")
    
    def validate_setup(self) -> bool:
        """Validate that all required keys are set"""
        status = self.list_keys()
        missing_required = [
            key for key, info in self.SUPPORTED_KEYS.items()
            if info['required'] and not status[key]
        ]
        
        if missing_required:
            print("Missing required API keys:")
            for key in missing_required:
                print(f"  - {key}")
            return False
        
        print("All required API keys are set")
        return True

def main():
    """CLI interface for secrets manager"""
    manager = SecretsManager()
    
    if len(sys.argv) < 2:
        print("Usage: python -m core.secrets_manager <command>")
        print("Commands:")
        print("  setup     - Interactive API key setup")
        print("  status    - Show current key status")
        print("  set <key> - Set a specific key")
        print("  get <key> - Get a specific key")
        print("  delete <key> - Delete a specific key")
        print("  validate - Validate required keys are set")
        return
    
    command = sys.argv[1].lower()
    
    if command == "setup":
        manager.interactive_setup()
    
    elif command == "status":
        manager.show_status()
    
    elif command == "set" and len(sys.argv) >= 3:
        key_name = sys.argv[2]
        value = getpass.getpass(f"Enter {key_name}: ")
        manager.set_key(key_name, value)
    
    elif command == "get" and len(sys.argv) >= 3:
        key_name = sys.argv[2]
        value = manager.get_key(key_name)
        if value:
            print(f"{key_name}: {value}")
        else:
            print(f"{key_name}: Not set")
    
    elif command == "delete" and len(sys.argv) >= 3:
        key_name = sys.argv[2]
        manager.delete_key(key_name)
    
    elif command == "validate":
        manager.validate_setup()
    
    else:
        print("Invalid command. Use 'python -m core.secrets_manager' for help.")

if __name__ == "__main__":
    main()





