"""
Multi-model embedding support for the threat intelligence agent
Supports OpenAI, BGE, and E5 models with automatic fallback
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Union
import numpy as np

# OpenAI
import openai

# BGE and E5 models
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

# HuggingFace Transformers for BGE
try:
    from transformers import AutoTokenizer, AutoModel
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

from utils.config import OPENAI_KEY

logger = logging.getLogger("Embeddings")

class EmbeddingProvider:
    """Unified embedding interface supporting multiple models"""
    
    def __init__(self, model_name: str = "auto", device: str = "cpu"):
        self.model_name = model_name
        self.device = device
        self.openai_client = None
        self.local_model = None
        self.tokenizer = None
        
        # Initialize based on model preference
        if model_name == "auto":
            self._auto_select_model()
        else:
            self._initialize_model(model_name)
    
    def _auto_select_model(self):
        """Auto-select best available model"""
        if OPENAI_KEY and self._test_openai():
            self.model_name = "openai"
            self.openai_client = openai.OpenAI(api_key=OPENAI_KEY)
            logger.info("Using OpenAI embeddings")
        elif SENTENCE_TRANSFORMERS_AVAILABLE:
            self.model_name = "bge-large-en-v1.5"
            self._initialize_sentence_transformer()
            logger.info("Using BGE embeddings via sentence-transformers")
        elif TRANSFORMERS_AVAILABLE:
            self.model_name = "BAAI/bge-large-en-v1.5"
            self._initialize_transformers()
            logger.info("Using BGE embeddings via transformers")
        else:
            raise RuntimeError("No embedding models available. Install sentence-transformers or transformers")
    
    def _test_openai(self) -> bool:
        """Test OpenAI API availability"""
        try:
            client = openai.OpenAI(api_key=OPENAI_KEY)
            client.embeddings.create(
                model="text-embedding-3-small",
                input="test"
            )
            return True
        except Exception:
            return False
    
    def _initialize_sentence_transformer(self):
        """Initialize sentence-transformers model"""
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError("sentence-transformers not available")
        
        model_map = {
            "bge-large-en-v1.5": "BAAI/bge-large-en-v1.5",
            "bge-m3": "BAAI/bge-m3",
            "e5-large-v2": "intfloat/e5-large-v2"
        }
        
        model_path = model_map.get(self.model_name, "BAAI/bge-large-en-v1.5")
        self.local_model = SentenceTransformer(model_path, device=self.device)
    
    def _initialize_transformers(self):
        """Initialize transformers model"""
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError("transformers not available")
        
        model_path = self.model_name
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.local_model = AutoModel.from_pretrained(model_path)
        
        if torch.cuda.is_available() and self.device == "auto":
            self.device = "cuda"
            self.local_model = self.local_model.to(self.device)
    
    def _initialize_model(self, model_name: str):
        """Initialize specific model"""
        if model_name == "openai":
            if not OPENAI_KEY:
                raise ValueError("OPENAI_KEY required for OpenAI embeddings")
            self.openai_client = openai.OpenAI(api_key=OPENAI_KEY)
        elif model_name in ["bge-large-en-v1.5", "bge-m3", "e5-large-v2"]:
            self._initialize_sentence_transformer()
        elif model_name.startswith("BAAI/") or model_name.startswith("intfloat/"):
            self._initialize_transformers()
        else:
            raise ValueError(f"Unknown model: {model_name}")
    
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        if self.model_name == "openai":
            return await self._embed_openai(texts)
        else:
            return await self._embed_local(texts)
    
    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for single text"""
        embeddings = await self.embed_texts([text])
        return embeddings[0]
    
    async def _embed_openai(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using OpenAI API"""
        try:
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=texts
            )
            return [data.embedding for data in response.data]
        except Exception as e:
            logger.error(f"OpenAI embedding error: {e}")
            raise
    
    async def _embed_local(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using local models"""
        try:
            if SENTENCE_TRANSFORMERS_AVAILABLE and hasattr(self, 'local_model') and hasattr(self.local_model, 'encode'):
                # Use sentence-transformers
                embeddings = self.local_model.encode(texts, convert_to_tensor=False)
                return embeddings.tolist() if hasattr(embeddings, 'tolist') else embeddings
            
            elif TRANSFORMERS_AVAILABLE and self.tokenizer and self.local_model:
                # Use transformers directly
                return await self._embed_transformers(texts)
            
            else:
                raise RuntimeError("No local embedding model available")
                
        except Exception as e:
            logger.error(f"Local embedding error: {e}")
            raise
    
    async def _embed_transformers(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using transformers library"""
        def _encode_batch():
            # Tokenize
            inputs = self.tokenizer(texts, padding=True, truncation=True, return_tensors="pt")
            if self.device != "cpu":
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Generate embeddings
            with torch.no_grad():
                outputs = self.local_model(**inputs)
                # Use mean pooling
                embeddings = outputs.last_hidden_state.mean(dim=1)
                return embeddings.cpu().numpy()
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(None, _encode_batch)
        return embeddings.tolist()
    
    def get_embedding_dimension(self) -> int:
        """Get embedding dimension for current model"""
        if self.model_name == "openai":
            return 1536  # text-embedding-3-small
        elif self.model_name in ["bge-large-en-v1.5", "BAAI/bge-large-en-v1.5"]:
            return 1024
        elif self.model_name in ["bge-m3", "BAAI/bge-m3"]:
            return 1024
        elif self.model_name in ["e5-large-v2", "intfloat/e5-large-v2"]:
            return 1024
        else:
            return 1024  # Default fallback

# Global embedding provider instance
_embedding_provider = None

def get_embedding_provider(model_name: str = "auto", device: str = "cpu") -> EmbeddingProvider:
    """Get global embedding provider instance"""
    global _embedding_provider
    if _embedding_provider is None:
        _embedding_provider = EmbeddingProvider(model_name, device)
    return _embedding_provider

async def generate_embedding(text: str, model_name: str = "auto") -> List[float]:
    """Convenience function for single text embedding"""
    provider = get_embedding_provider(model_name)
    return await provider.embed_text(text)

async def generate_embeddings(texts: List[str], model_name: str = "auto") -> List[List[float]]:
    """Convenience function for multiple text embeddings"""
    provider = get_embedding_provider(model_name)
    return await provider.embed_texts(texts)

