"""
BGE Reranking support for improved retrieval quality
Integrates with the existing RAG system for better search results
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

try:
    from sentence_transformers import CrossEncoder
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

try:
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

logger = logging.getLogger("Reranker")

class Reranker:
    """Reranking model for improving search result quality"""
    
    def __init__(self, model_name: str = "auto", device: str = "cpu"):
        self.model_name = model_name
        self.device = device
        self.model = None
        self.tokenizer = None
        
        if model_name == "auto":
            self._auto_select_model()
        else:
            self._initialize_model(model_name)
    
    def _auto_select_model(self):
        """Auto-select best available reranking model"""
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            self.model_name = "bge-reranker-large"
            self._initialize_sentence_transformer()
            logger.info("Using BGE reranker via sentence-transformers")
        elif TRANSFORMERS_AVAILABLE:
            self.model_name = "cross-encoder/ms-marco-MiniLM-L-6-v2"
            self._initialize_transformers()
            logger.info("Using cross-encoder reranker via transformers")
        else:
            logger.warning("No reranking models available")
            self.model = None
    
    def _initialize_sentence_transformer(self):
        """Initialize sentence-transformers reranker"""
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError("sentence-transformers not available")
        
        model_map = {
            "bge-reranker-large": "BAAI/bge-reranker-large",
            "bge-reranker-base": "BAAI/bge-reranker-base",
            "ms-marco": "cross-encoder/ms-marco-MiniLM-L-6-v2"
        }
        
        model_path = model_map.get(self.model_name, "BAAI/bge-reranker-large")
        
        try:
            self.model = CrossEncoder(model_path, device=self.device)
            logger.info(f"Loaded reranker: {model_path}")
        except Exception as e:
            logger.error(f"Failed to load reranker {model_path}: {e}")
            self.model = None
    
    def _initialize_transformers(self):
        """Initialize transformers reranker"""
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError("transformers not available")
        
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
            
            if torch.cuda.is_available() and self.device == "auto":
                self.device = "cuda"
                self.model = self.model.to(self.device)
            
            logger.info(f"Loaded reranker: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to load reranker {self.model_name}: {e}")
            self.model = None
    
    def _initialize_model(self, model_name: str):
        """Initialize specific reranker model"""
        if model_name in ["bge-reranker-large", "bge-reranker-base", "ms-marco"]:
            self._initialize_sentence_transformer()
        elif model_name.startswith("cross-encoder/"):
            self._initialize_transformers()
        else:
            raise ValueError(f"Unknown reranker model: {model_name}")
    
    async def rerank(
        self, 
        query: str, 
        documents: List[Dict[str, Any]], 
        top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Rerank documents based on query relevance
        
        Args:
            query: Search query
            documents: List of documents to rerank
            top_k: Number of top results to return
            
        Returns:
            Reranked documents with relevance scores
        """
        if not self.model or not documents:
            return documents
        
        if top_k is None:
            top_k = len(documents)
        
        try:
            if SENTENCE_TRANSFORMERS_AVAILABLE and hasattr(self.model, 'predict'):
                # Use sentence-transformers CrossEncoder
                return await self._rerank_sentence_transformers(query, documents, top_k)
            elif TRANSFORMERS_AVAILABLE and self.tokenizer:
                # Use transformers directly
                return await self._rerank_transformers(query, documents, top_k)
            else:
                logger.warning("No reranking model available")
                return documents[:top_k]
                
        except Exception as e:
            logger.error(f"Reranking error: {e}")
            return documents[:top_k]
    
    async def _rerank_sentence_transformers(
        self, 
        query: str, 
        documents: List[Dict[str, Any]], 
        top_k: int
    ) -> List[Dict[str, Any]]:
        """Rerank using sentence-transformers CrossEncoder"""
        def _compute_scores():
            # Prepare query-document pairs
            pairs = []
            for doc in documents:
                # Use content field for reranking
                content = doc.get('content', '')
                if not content:
                    # Fallback to other fields
                    content = doc.get('summary', '') or doc.get('details', '') or str(doc)
                pairs.append([query, content])
            
            # Compute relevance scores
            scores = self.model.predict(pairs)
            return scores
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        scores = await loop.run_in_executor(None, _compute_scores)
        
        # Add scores to documents and sort
        for i, doc in enumerate(documents):
            doc['rerank_score'] = float(scores[i])
        
        # Sort by rerank score (descending)
        reranked_docs = sorted(documents, key=lambda x: x['rerank_score'], reverse=True)
        
        return reranked_docs[:top_k]
    
    async def _rerank_transformers(
        self, 
        query: str, 
        documents: List[Dict[str, Any]], 
        top_k: int
    ) -> List[Dict[str, Any]]:
        """Rerank using transformers directly"""
        def _compute_scores():
            scores = []
            
            for doc in documents:
                # Use content field for reranking
                content = doc.get('content', '')
                if not content:
                    content = doc.get('summary', '') or doc.get('details', '') or str(doc)
                
                # Tokenize query and document
                inputs = self.tokenizer(
                    query, 
                    content, 
                    truncation=True, 
                    padding=True, 
                    return_tensors="pt",
                    max_length=512
                )
                
                if self.device == "cuda":
                    inputs = {k: v.to(self.device) for k, v in inputs.items()}
                
                # Compute score
                with torch.no_grad():
                    outputs = self.model(**inputs)
                    score = torch.sigmoid(outputs.logits).item()
                    scores.append(score)
            
            return scores
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        scores = await loop.run_in_executor(None, _compute_scores)
        
        # Add scores to documents and sort
        for i, doc in enumerate(documents):
            doc['rerank_score'] = scores[i]
        
        # Sort by rerank score (descending)
        reranked_docs = sorted(documents, key=lambda x: x['rerank_score'], reverse=True)
        
        return reranked_docs[:top_k]
    
    def is_available(self) -> bool:
        """Check if reranking is available"""
        return self.model is not None

# Global reranker instance
_reranker = None

def get_reranker(model_name: str = "auto", device: str = "cpu") -> Reranker:
    """Get global reranker instance"""
    global _reranker
    if _reranker is None:
        _reranker = Reranker(model_name, device)
    return _reranker

async def rerank_documents(
    query: str, 
    documents: List[Dict[str, Any]], 
    top_k: Optional[int] = None,
    model_name: str = "auto"
) -> List[Dict[str, Any]]:
    """Convenience function for document reranking"""
    reranker = get_reranker(model_name)
    return await reranker.rerank(query, documents, top_k)





