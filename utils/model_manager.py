"""
Local Model Manager for downloading and managing LLM models
Supports Llama, Qwen, Mistral with automatic downloading and caching
"""

import os
import logging
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import requests
from tqdm import tqdm

logger = logging.getLogger("ModelManager")

class LocalModelManager:
    """Manages local LLM model downloads and caching"""
    
    # Model configurations optimized for 32GB RAM
    MODELS = {
        "llama-3.1-8b": {
            "repo": "meta-llama/Llama-3.1-8B-Instruct",
            "size_gb": 8,
            "ram_required": 12,
            "description": "Fast, efficient 8B model"
        },
        "llama-3.1-14b": {
            "repo": "meta-llama/Llama-3.1-14B-Instruct", 
            "size_gb": 14,
            "ram_required": 20,
            "description": "Balanced 14B model"
        },
        "llama-3.1-70b": {
            "repo": "meta-llama/Llama-3.1-70B-Instruct",
            "size_gb": 70,
            "ram_required": 32,
            "description": "Powerful 70B model (recommended for 32GB)"
        },
        "qwen2.5-7b": {
            "repo": "Qwen/Qwen2.5-7B-Instruct",
            "size_gb": 7,
            "ram_required": 12,
            "description": "Fast Qwen 7B model"
        },
        "qwen2.5-14b": {
            "repo": "Qwen/Qwen2.5-14B-Instruct",
            "size_gb": 14,
            "ram_required": 20,
            "description": "Balanced Qwen 14B model"
        },
        "qwen2.5-32b": {
            "repo": "Qwen/Qwen2.5-32B-Instruct",
            "size_gb": 32,
            "ram_required": 32,
            "description": "Large Qwen 32B model"
        },
        "mistral-7b": {
            "repo": "mistralai/Mistral-7B-Instruct-v0.3",
            "size_gb": 7,
            "ram_required": 12,
            "description": "Mistral 7B model"
        },
        "mixtral-8x7b": {
            "repo": "mistralai/Mixtral-8x7B-Instruct-v0.1",
            "size_gb": 45,
            "ram_required": 32,
            "description": "Mixtral 8x7B model"
        }
    }
    
    def __init__(self, models_dir: str = "models"):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(exist_ok=True)
        
        # Check if transformers is available
        try:
            import transformers
            self.transformers_available = True
        except ImportError:
            self.transformers_available = False
            logger.warning("transformers not available, install with: pip install transformers")
    
    def get_recommended_model(self, ram_gb: int = 32) -> str:
        """Get recommended model based on available RAM"""
        suitable_models = []
        
        for model_name, config in self.MODELS.items():
            if config["ram_required"] <= ram_gb:
                suitable_models.append((model_name, config))
        
        if not suitable_models:
            return "llama-3.1-8b"  # Fallback to smallest
        
        # Sort by size (largest first for better quality)
        suitable_models.sort(key=lambda x: x[1]["size_gb"], reverse=True)
        return suitable_models[0][0]
    
    def list_models(self) -> Dict[str, Dict]:
        """List all available models with status"""
        models_info = {}
        
        for model_name, config in self.MODELS.items():
            model_path = self.models_dir / model_name
            is_downloaded = model_path.exists() and any(model_path.iterdir())
            
            models_info[model_name] = {
                **config,
                "downloaded": is_downloaded,
                "path": str(model_path)
            }
        
        return models_info
    
    def download_model(self, model_name: str, force: bool = False) -> bool:
        """Download a model using git-lfs"""
        if model_name not in self.MODELS:
            logger.error(f"Unknown model: {model_name}")
            return False
        
        model_path = self.models_dir / model_name
        config = self.MODELS[model_name]
        
        # Check if already downloaded
        if model_path.exists() and any(model_path.iterdir()) and not force:
            logger.info(f"Model {model_name} already downloaded")
            return True
        
        logger.info(f"Downloading {model_name} ({config['size_gb']}GB)...")
        logger.info(f"Description: {config['description']}")
        
        # Check git-lfs availability
        try:
            subprocess.run(["git", "lfs", "version"], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.error("git-lfs not found. Install with:")
            logger.error("  Windows: winget install Git.Git")
            logger.error("  Mac: brew install git-lfs")
            logger.error("  Linux: apt install git-lfs")
            return False
        
        # Download model
        try:
            repo_url = f"https://huggingface.co/{config['repo']}"
            logger.info(f"Cloning from {repo_url}")
            
            if model_path.exists():
                import shutil
                shutil.rmtree(model_path)
            
            # Clone with git-lfs
            result = subprocess.run([
                "git", "clone", repo_url, str(model_path)
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"Git clone failed: {result.stderr}")
                return False
            
            logger.info(f"{model_name} downloaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Download failed: {e}")
            return False
    
    def download_recommended(self, ram_gb: int = 32) -> str:
        """Download the recommended model for available RAM"""
        recommended = self.get_recommended_model(ram_gb)
        logger.info(f"Recommended model for {ram_gb}GB RAM: {recommended}")
        
        if self.download_model(recommended):
            return recommended
        else:
            logger.error("Failed to download recommended model")
            return ""
    
    def setup_model_for_use(self, model_name: str) -> bool:
        """Setup model for use with transformers"""
        if not self.transformers_available:
            logger.error("transformers not available")
            return False
        
        model_path = self.models_dir / model_name
        if not model_path.exists():
            logger.error(f"Model {model_name} not found. Download it first.")
            return False
        
        try:
            from transformers import AutoTokenizer, AutoModelForCausalLM
            
            logger.info(f"Loading {model_name} for testing...")
            
            # Test loading
            tokenizer = AutoTokenizer.from_pretrained(str(model_path))
            model = AutoModelForCausalLM.from_pretrained(
                str(model_path),
                torch_dtype="auto",
                device_map="auto"
            )
            
            logger.info(f"{model_name} ready for use")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup {model_name}: {e}")
            return False
    
    def interactive_setup(self):
        """Interactive model setup"""
        print("Local Model Manager")
        print("=" * 40)
        
        # Show available RAM
        try:
            import psutil
            ram_gb = psutil.virtual_memory().total // (1024**3)
            print(f"Detected RAM: {ram_gb}GB")
        except ImportError:
            ram_gb = 32  # Default assumption
            print(f"Assuming RAM: {ram_gb}GB")
        
        # Show recommended model
        recommended = self.get_recommended_model(ram_gb)
        print(f"Recommended: {recommended}")
        
        # List all models
        print("\nAvailable Models:")
        models_info = self.list_models()
        
        for model_name, info in models_info.items():
            status = "[DOWNLOADED]" if info["downloaded"] else "[NOT DOWNLOADED]"
            ram_req = f"{info['ram_required']}GB RAM"
            size = f"{info['size_gb']}GB"
            
            print(f"  {model_name}: {status} | {ram_req} | {size}")
            print(f"    {info['description']}")
        
        # Ask user choice
        print(f"\nOptions:")
        print(f"  1. Download recommended ({recommended})")
        print(f"  2. Choose specific model")
        print(f"  3. Download all suitable models")
        print(f"  4. Exit")
        
        choice = input("\nEnter choice (1-4): ").strip()
        
        if choice == "1":
            self.download_model(recommended)
        elif choice == "2":
            model_name = input("Enter model name: ").strip()
            if model_name in self.MODELS:
                self.download_model(model_name)
            else:
                print("Invalid model name")
        elif choice == "3":
            suitable_models = [
                name for name, info in models_info.items()
                if info["ram_required"] <= ram_gb and not info["downloaded"]
            ]
            for model_name in suitable_models:
                self.download_model(model_name)
        elif choice == "4":
            print("Exiting...")
        else:
            print("Invalid choice")

def main():
    """CLI interface for model manager"""
    manager = LocalModelManager()
    
    if len(sys.argv) < 2:
        print("Usage: python -m utils.model_manager <command>")
        print("Commands:")
        print("  setup     - Interactive model setup")
        print("  list      - List all models")
        print("  download <model> - Download specific model")
        print("  recommended - Download recommended model")
        return
    
    command = sys.argv[1].lower()
    
    if command == "setup":
        manager.interactive_setup()
    
    elif command == "list":
        models_info = manager.list_models()
        print("Available Models:")
        for model_name, info in models_info.items():
            status = "[DOWNLOADED]" if info["downloaded"] else "[NOT DOWNLOADED]"
            print(f"{status} {model_name}: {info['description']} ({info['size_gb']}GB)")
    
    elif command == "download" and len(sys.argv) >= 3:
        model_name = sys.argv[2]
        manager.download_model(model_name)
    
    elif command == "recommended":
        recommended = manager.get_recommended_model()
        print(f"Recommended model: {recommended}")
        manager.download_model(recommended)
    
    else:
        print("Invalid command")

if __name__ == "__main__":
    main()





