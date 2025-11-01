"""
OpenSearch integration for hybrid BM25+vector search
Extends the existing RAG system with keyword search capabilities
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Union
import json
from datetime import datetime

try:
    from opensearchpy import OpenSearch, RequestsHttpConnection
    from opensearchpy.helpers import bulk, scan
    OPENSEARCH_AVAILABLE = True
except ImportError:
    OPENSEARCH_AVAILABLE = False

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue, Range, MatchAny

from utils.config import OPENAI_KEY
from utils.embeddings import get_embedding_provider

logger = logging.getLogger("HybridSearch")

class HybridSearchEngine:
    """Hybrid search combining BM25 (OpenSearch) and vector search (Qdrant)"""
    
    def __init__(
        self, 
        opensearch_host: str = "localhost",
        opensearch_port: int = 9200,
        opensearch_use_ssl: bool = False,
        qdrant_host: str = "localhost",
        qdrant_port: int = 6333,
        embedding_model: str = "auto"
    ):
        self.opensearch_client = None
        self.qdrant_client = None
        self.embedding_provider = None
        self.collection_name = "osv_vulnerabilities"
        self.index_name = "osv_vulnerabilities"
        
        # Initialize OpenSearch
        if OPENSEARCH_AVAILABLE:
            self._initialize_opensearch(opensearch_host, opensearch_port, opensearch_use_ssl)
        else:
            logger.warning("OpenSearch not available, falling back to vector-only search")
        
        # Initialize Qdrant
        self._initialize_qdrant(qdrant_host, qdrant_port)
        
        # Initialize embeddings
        self.embedding_provider = get_embedding_provider(embedding_model)
    
    def _initialize_opensearch(self, host: str, port: int, use_ssl: bool):
        """Initialize OpenSearch client"""
        try:
            self.opensearch_client = OpenSearch(
                hosts=[{'host': host, 'port': port}],
                http_compress=True,
                use_ssl=use_ssl,
                verify_certs=False if not use_ssl else True,
                connection_class=RequestsHttpConnection,
                timeout=60
            )
            
            # Test connection
            if self.opensearch_client.ping():
                logger.info(f"Connected to OpenSearch at {host}:{port}")
            else:
                logger.warning("OpenSearch ping failed")
                self.opensearch_client = None
                
        except Exception as e:
            logger.error(f"Failed to initialize OpenSearch: {e}")
            self.opensearch_client = None
    
    def _initialize_qdrant(self, host: str, port: int):
        """Initialize Qdrant client"""
        try:
            self.qdrant_client = QdrantClient(host=host, port=port)
            logger.info(f"Connected to Qdrant at {host}:{port}")
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant: {e}")
            raise
    
    async def create_opensearch_index(self):
        """Create OpenSearch index with proper mapping"""
        if not self.opensearch_client:
            return False
        
        mapping = {
            "mappings": {
                "properties": {
                    "id": {"type": "keyword"},
                    "aliases": {"type": "keyword"},
                    "content": {
                        "type": "text",
                        "analyzer": "standard",
                        "search_analyzer": "standard"
                    },
                    "summary": {
                        "type": "text",
                        "analyzer": "standard"
                    },
                    "details": {
                        "type": "text",
                        "analyzer": "standard"
                    },
                    "ecosystem": {"type": "keyword"},
                    "published": {"type": "date"},
                    "modified": {"type": "date"},
                    "severity": {
                        "type": "nested",
                        "properties": {
                            "type": {"type": "keyword"},
                            "score": {"type": "float"}
                        }
                    },
                    "affected_packages": {
                        "type": "nested",
                        "properties": {
                            "name": {"type": "keyword"},
                            "ecosystem": {"type": "keyword"}
                        }
                    },
                    "references": {
                        "type": "nested",
                        "properties": {
                            "type": {"type": "keyword"},
                            "url": {"type": "keyword"}
                        }
                    }
                }
            },
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "analysis": {
                    "analyzer": {
                        "standard": {
                            "type": "standard",
                            "stopwords": "_english_"
                        }
                    }
                }
            }
        }
        
        try:
            if not self.opensearch_client.indices.exists(index=self.index_name):
                self.opensearch_client.indices.create(
                    index=self.index_name,
                    body=mapping
                )
                logger.info(f"Created OpenSearch index: {self.index_name}")
            else:
                logger.info(f"OpenSearch index already exists: {self.index_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to create OpenSearch index: {e}")
            return False
    
    async def index_documents(self, documents: List[Dict[str, Any]]):
        """Index documents in both OpenSearch and Qdrant"""
        if not documents:
            return
        
        # Index in OpenSearch
        if self.opensearch_client:
            await self._index_opensearch(documents)
        
        # Index in Qdrant (if not already done)
        await self._index_qdrant(documents)
    
    async def _index_opensearch(self, documents: List[Dict[str, Any]]):
        """Index documents in OpenSearch"""
        if not self.opensearch_client:
            return
        
        try:
            # Prepare documents for bulk indexing
            actions = []
            for doc in documents:
                action = {
                    "_index": self.index_name,
                    "_id": doc.get("id", ""),
                    "_source": doc
                }
                actions.append(action)
            
            # Bulk index
            success, failed = bulk(self.opensearch_client, actions)
            logger.info(f"Indexed {success} documents in OpenSearch, {len(failed)} failed")
            
        except Exception as e:
            logger.error(f"Failed to index documents in OpenSearch: {e}")
    
    async def _index_qdrant(self, documents: List[Dict[str, Any]]):
        """Index documents in Qdrant (if not already done)"""
        try:
            # Check if collection exists and has documents
            collection_info = self.qdrant_client.get_collection(self.collection_name)
            if collection_info.points_count > 0:
                logger.info("Qdrant collection already has documents, skipping indexing")
                return
            
            # Generate embeddings and index
            texts = [doc.get("content", "") for doc in documents]
            embeddings = await self.embedding_provider.embed_texts(texts)
            
            points = []
            for i, (doc, embedding) in enumerate(zip(documents, embeddings)):
                point_id = hash(doc.get("id", str(i))) & 0x7FFFFFFFFFFFFFFF
                point = {
                    "id": point_id,
                    "vector": embedding,
                    "payload": doc
                }
                points.append(point)
            
            # Upsert to Qdrant
            self.qdrant_client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            logger.info(f"Indexed {len(points)} documents in Qdrant")
            
        except Exception as e:
            logger.error(f"Failed to index documents in Qdrant: {e}")
    
    async def hybrid_search(
        self,
        query: str,
        ecosystems: Optional[List[str]] = None,
        limit: int = 10,
        vector_weight: float = 0.7,
        bm25_weight: float = 0.3
    ) -> Dict[str, Any]:
        """
        Perform hybrid search combining BM25 and vector search
        
        Args:
            query: Search query
            ecosystems: Filter by ecosystems
            limit: Maximum results to return
            vector_weight: Weight for vector search results
            bm25_weight: Weight for BM25 search results
        """
        results = {
            "query": query,
            "ecosystems": ecosystems,
            "results": [],
            "total_found": 0,
            "search_method": "hybrid",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Perform BM25 search
        bm25_results = []
        if self.opensearch_client:
            bm25_results = await self._bm25_search(query, ecosystems, limit * 2)
        
        # Perform vector search
        vector_results = await self._vector_search(query, ecosystems, limit * 2)
        
        # Combine and rerank results
        combined_results = self._combine_results(
            bm25_results, 
            vector_results, 
            vector_weight, 
            bm25_weight
        )
        
        # Apply ecosystem filter if specified
        if ecosystems:
            filtered_results = []
            for result in combined_results:
                if result.get("ecosystem") in ecosystems:
                    filtered_results.append(result)
            combined_results = filtered_results
        
        # Limit results
        results["results"] = combined_results[:limit]
        results["total_found"] = len(results["results"])
        
        return results
    
    async def _bm25_search(
        self, 
        query: str, 
        ecosystems: Optional[List[str]] = None, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Perform BM25 search using OpenSearch"""
        if not self.opensearch_client:
            return []
        
        # Build query
        search_query = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "multi_match": {
                                "query": query,
                                "fields": ["content^2", "summary^1.5", "details"],
                                "type": "best_fields",
                                "fuzziness": "AUTO"
                            }
                        }
                    ]
                }
            },
            "size": limit,
            "_source": True
        }
        
        # Add ecosystem filter
        if ecosystems:
            search_query["query"]["bool"]["filter"] = [
                {"terms": {"ecosystem": ecosystems}}
            ]
        
        try:
            response = self.opensearch_client.search(
                index=self.index_name,
                body=search_query
            )
            
            results = []
            for hit in response["hits"]["hits"]:
                doc = hit["_source"]
                doc["bm25_score"] = hit["_score"]
                results.append(doc)
            
            return results
            
        except Exception as e:
            logger.error(f"BM25 search error: {e}")
            return []
    
    async def _vector_search(
        self, 
        query: str, 
        ecosystems: Optional[List[str]] = None, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Perform vector search using Qdrant"""
        try:
            # Generate query embedding
            query_embedding = await self.embedding_provider.embed_text(query)
            
            # Build ecosystem filter
            ecosystem_filter = None
            if ecosystems:
                ecosystem_filter = Filter(
                    must=[
                        FieldCondition(
                            key="ecosystem",
                            match=MatchAny(any=ecosystems)
                        )
                    ]
                )
            
            # Search Qdrant
            search_results = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                query_filter=ecosystem_filter,
                limit=limit,
                with_payload=True
            )
            
            results = []
            for result in search_results:
                doc = result.payload.copy()
                doc["vector_score"] = result.score
                results.append(doc)
            
            return results
            
        except Exception as e:
            logger.error(f"Vector search error: {e}")
            return []
    
    def _combine_results(
        self, 
        bm25_results: List[Dict[str, Any]], 
        vector_results: List[Dict[str, Any]], 
        vector_weight: float, 
        bm25_weight: float
    ) -> List[Dict[str, Any]]:
        """Combine and rerank BM25 and vector search results"""
        # Create a map of document IDs to combined scores
        doc_scores = {}
        
        # Process BM25 results
        for doc in bm25_results:
            doc_id = doc.get("id", "")
            if doc_id:
                doc_scores[doc_id] = {
                    "doc": doc,
                    "bm25_score": doc.get("bm25_score", 0),
                    "vector_score": 0
                }
        
        # Process vector results
        for doc in vector_results:
            doc_id = doc.get("id", "")
            if doc_id in doc_scores:
                doc_scores[doc_id]["vector_score"] = doc.get("vector_score", 0)
            else:
                doc_scores[doc_id] = {
                    "doc": doc,
                    "bm25_score": 0,
                    "vector_score": doc.get("vector_score", 0)
                }
        
        # Calculate combined scores and sort
        combined_results = []
        for doc_id, scores in doc_scores.items():
            doc = scores["doc"]
            
            # Normalize scores (simple min-max normalization)
            bm25_norm = scores["bm25_score"] / 10.0 if scores["bm25_score"] > 0 else 0
            vector_norm = scores["vector_score"]
            
            # Combined score
            combined_score = (vector_weight * vector_norm) + (bm25_weight * bm25_norm)
            
            doc["combined_score"] = combined_score
            doc["bm25_score"] = scores["bm25_score"]
            doc["vector_score"] = scores["vector_score"]
            
            combined_results.append(doc)
        
        # Sort by combined score
        combined_results.sort(key=lambda x: x["combined_score"], reverse=True)
        
        return combined_results
    
    async def get_document_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get document by ID from either OpenSearch or Qdrant"""
        # Try OpenSearch first
        if self.opensearch_client:
            try:
                response = self.opensearch_client.get(
                    index=self.index_name,
                    id=doc_id
                )
                return response["_source"]
            except Exception:
                pass
        
        # Fallback to Qdrant
        try:
            search_results = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=[0] * self.embedding_provider.get_embedding_dimension(),
                query_filter=Filter(
                    must=[
                        FieldCondition(
                            key="id",
                            match=MatchValue(value=doc_id)
                        )
                    ]
                ),
                limit=1,
                with_payload=True
            )
            
            if search_results:
                return search_results[0].payload
                
        except Exception as e:
            logger.error(f"Error getting document by ID: {e}")
        
        return None

# Global hybrid search engine instance
_hybrid_search_engine = None

def get_hybrid_search_engine() -> HybridSearchEngine:
    """Get global hybrid search engine instance"""
    global _hybrid_search_engine
    if _hybrid_search_engine is None:
        _hybrid_search_engine = HybridSearchEngine()
    return _hybrid_search_engine

