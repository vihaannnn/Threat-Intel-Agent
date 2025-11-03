import asyncio
import logging
import json
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

import openai
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue, Range, MatchAny

from utils.config import OPENAI_KEY

logger = logging.getLogger("RAGTool")

@dataclass
class ExtractedEntities:
    """Enhanced entities extracted from user queries by LLM"""
    ecosystems: List[str] = None
    query_text: str = ""

class OSVRAGTool:
    """Enhanced RAG tool with better filtering and organizational query support"""
    
    def __init__(self, openai_api_key: str, qdrant_host: str = "localhost", qdrant_port: int = 6333):
        self.openai_client = openai.OpenAI(api_key=openai_api_key)
        self.qdrant_client = QdrantClient(host=qdrant_host, port=qdrant_port)
        self.collection_name = "osv_vulnerabilities"

    
    def _build_ecosystem_filter(self, entities: ExtractedEntities) -> Optional[Filter]:
        """Build simple Qdrant filter for ecosystem only"""
        if entities.ecosystems:
            return Filter(
                must=[
                    FieldCondition(
                        key="ecosystem",
                        match=MatchAny(any=entities.ecosystems)
                    )
                ]
            )
        return None

    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using OpenAI"""
        try:
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            embedding = response.data[0].embedding
            
            # Validate embedding dimension
            if len(embedding) != 1536:
                logger.error(f"Embedding dimension mismatch: expected 1536, got {len(embedding)}")
                raise ValueError(f"Embedding dimension mismatch: expected 1536, got {len(embedding)}")
            
            # Validate embedding values (check for NaN, infinity, etc.)
            import math
            for i, val in enumerate(embedding):
                if not isinstance(val, (int, float)) or math.isnan(val) or math.isinf(val):
                    logger.error(f"Invalid embedding value at index {i}: {val}")
                    # Replace invalid values with 0
                    embedding[i] = 0.0
            
            return embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise
    
    async def search_vulnerabilities(
        self, 
        query: str, 
        entities: ExtractedEntities,
        limit: int = 10,
        use_hybrid: bool = False,
        use_reranking: bool = False
    ) -> Dict[str, Any]:
        """
        Vulnerability search with ecosystem filtering
        
        Args:
            query: User's search query
            entities: Entities extracted by LLM
            limit: Maximum number of results to return
            use_hybrid: Whether to use hybrid search (BM25 + vector) - currently not implemented, ignored
            use_reranking: Whether to use reranking - currently not implemented, ignored
            
        Returns:
            Dictionary containing search results and metadata
        """
        try:
            logger.info(f"Search with entities: {entities}")
            
            # Generate embedding for semantic search
            query_embedding = await self.generate_embedding(query)
            
            # Validate embedding dimension before search
            if len(query_embedding) != 1536:
                logger.error(f"Query embedding dimension mismatch: expected 1536, got {len(query_embedding)}")
                raise ValueError(f"Query embedding dimension mismatch: expected 1536, got {len(query_embedding)}")
            
            # Build ecosystem filter
            ecosystem_filter = self._build_ecosystem_filter(entities)
            
            # Validate query vector before search
            import math
            valid_vector = []
            for val in query_embedding:
                if not isinstance(val, (int, float)) or math.isnan(val) or math.isinf(val):
                    valid_vector.append(0.0)
                else:
                    valid_vector.append(float(val))
            query_embedding = valid_vector
            
            # Perform vector search with ecosystem filtering
            try:
                search_results = self.qdrant_client.search(
                    collection_name=self.collection_name,
                    query_vector=query_embedding,
                    query_filter=ecosystem_filter,
                    limit=limit,
                    with_payload=True
                )
            except Exception as search_error:
                error_str = str(search_error).lower()
                # If search fails with OutputTooSmall or similar, try without filter
                if "outputtoosmall" in error_str or "dimension" in error_str or "500" in error_str:
                    logger.warning(f"Search failed with error, retrying without filter: {search_error}")
                    try:
                        search_results = self.qdrant_client.search(
                            collection_name=self.collection_name,
                            query_vector=query_embedding,
                            limit=limit,
                            with_payload=True
                        )
                    except Exception as retry_error:
                        error_str_retry = str(retry_error).lower()
                        if "outputtoosmall" in error_str_retry or "500" in error_str_retry or "channel closed" in error_str_retry:
                            logger.error(f"Search failed even without filter: {retry_error}")
                            logger.warning("This indicates the Qdrant collection may be corrupted.")
                            logger.warning("Attempting alternative search method...")
                            
                            # Try using scroll as fallback - keyword-based search
                            try:
                                logger.info("Attempting scroll-based fallback search...")
                                # Get larger sample to search through
                                scroll_results, _ = self.qdrant_client.scroll(
                                    collection_name=self.collection_name,
                                    limit=min(limit * 10, 500),  # Get more to filter from
                                    with_payload=True,
                                    with_vectors=False
                                )
                                
                                if not scroll_results:
                                    logger.warning("No data found in collection via scroll")
                                    search_results = []
                                else:
                                    # Convert scroll results to search-like results with keyword-based scoring
                                    search_results = []
                                    query_words = set(query.lower().split())
                                    
                                    for point in scroll_results:
                                        payload = point.payload
                                        content = payload.get("content", "").lower()
                                        package_names = []
                                        
                                        # Extract package names from affected packages
                                        affected = payload.get("affected", [])
                                        for aff in affected:
                                            if isinstance(aff, dict) and "package" in aff:
                                                pkg = aff["package"]
                                                if isinstance(pkg, dict):
                                                    package_names.append(pkg.get("name", "").lower())
                                        
                                        # Calculate relevance score
                                        score = 0.0
                                        
                                        # Match query words in content
                                        content_words = set(content.split())
                                        matching_words = query_words & content_words
                                        score += len(matching_words) / max(len(query_words), 1) * 0.5
                                        
                                        # Match query words in package names
                                        for pkg_name in package_names:
                                            if any(word in pkg_name for word in query_words):
                                                score += 0.3
                                                break
                                        
                                        # Match ecosystem if mentioned
                                        ecosystem = payload.get("ecosystem", "").lower()
                                        if any(word in ecosystem for word in query_words):
                                            score += 0.2
                                        
                                        # Only include if some relevance
                                        if score > 0 or len(search_results) < limit:
                                            search_results.append(
                                                type('ScoredPoint', (), {
                                                    'payload': payload,
                                                    'score': score,
                                                    'id': point.id
                                                })()
                                            )
                                    
                                    # Sort by score and limit
                                    search_results = sorted(search_results, key=lambda x: x.score, reverse=True)[:limit]
                                    logger.info(f"Scroll fallback found {len(search_results)} relevant results")
                            except Exception as scroll_fallback_error:
                                error_str_scroll = str(scroll_fallback_error).lower()
                                if "outputtoosmall" in error_str_scroll or "500" in error_str_scroll or "channel closed" in error_str_scroll:
                                    logger.error(f"Scroll fallback also failed: {scroll_fallback_error}")
                                    logger.warning("Qdrant collection appears corrupted or incompatible.")
                                    logger.warning("Possible solutions:")
                                    logger.warning("1. Restart Qdrant Docker container")
                                    logger.warning("2. Run: python recreate_qdrant_collection.py")
                                    logger.warning("3. Then: python data/setup_local_qdrant.py")
                                    search_results = []
                                else:
                                    logger.error(f"Unexpected scroll error: {scroll_fallback_error}")
                                    search_results = []
                        else:
                            logger.error(f"Search error: {retry_error}")
                            search_results = []
                else:
                    error_str_search = str(search_error).lower()
                    if "outputtoosmall" in error_str_search or "500" in error_str_search:
                        logger.warning("Qdrant collection may be corrupted. Run: python recreate_qdrant_collection.py")
                    logger.error(f"Search error: {search_error}")
                    # Return empty results instead of raising
                    search_results = []
            
            # Process results
            results = []
            for result in search_results:
                vulnerability_data = {
                    "id": result.payload.get("id"),
                    "aliases": result.payload.get("aliases", []),
                    "content": result.payload.get("content", ""),
                    "ecosystem": result.payload.get("ecosystem"),
                    "published": result.payload.get("published"),
                    "modified": result.payload.get("modified"),
                    "severity": result.payload.get("severity", []),
                    "affected_packages": result.payload.get("affected", []),
                    "references": result.payload.get("references", []),
                    "similarity_score": result.score
                }
                results.append(vulnerability_data)
            
            return {
                "query": query,
                "extracted_entities": entities.__dict__,
                "results": results,
                "total_found": len(results),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in vulnerability search: {e}")
            raise
    
    
    
    async def get_vulnerability_by_id(self, vuln_id: str) -> Dict[str, Any]:
        """
        Get specific vulnerability by ID (CVE or GHSA)
        
        Args:
            vuln_id: Vulnerability ID (CVE-XXXX-XXXX or GHSA-XXXX-XXXX-XXXX)
            
        Returns:
            Vulnerability data or None if not found
        """
        try:
            # Try using scroll for filtering by ID
            try:
                scroll_results, _ = self.qdrant_client.scroll(
                    collection_name=self.collection_name,
                    scroll_filter=Filter(
                        must=[
                            FieldCondition(
                                key="aliases",
                                match=MatchValue(value=vuln_id)
                            )
                        ]
                    ),
                    limit=1,
                    with_payload=True,
                    with_vectors=False
                )
                
                if scroll_results:
                    result = scroll_results[0]
                    return {
                        "id": result.payload.get("id"),
                        "aliases": result.payload.get("aliases", []),
                        "summary": result.payload.get("summary", ""),
                        "content": result.payload.get("content", ""),
                        "ecosystem": result.payload.get("ecosystem"),
                        "published": result.payload.get("published"),
                        "modified": result.payload.get("modified"),
                        "severity": result.payload.get("severity", []),
                        "affected_packages": result.payload.get("affected", []),
                        "references": result.payload.get("references", [])
                    }
            except Exception as scroll_error:
                error_str = str(scroll_error).lower()
                if "outputtoosmall" in error_str or "500" in error_str:
                    logger.warning(f"Scroll operation failed with OutputTooSmall error. This may indicate a corrupted collection.")
                    logger.warning(f"Try running: python recreate_qdrant_collection.py")
                    # Fall through to try id field
                else:
                    raise
            
            # Also try searching in the "id" field directly
            try:
                scroll_results, _ = self.qdrant_client.scroll(
                    collection_name=self.collection_name,
                    scroll_filter=Filter(
                        must=[
                            FieldCondition(
                                key="id",
                                match=MatchValue(value=vuln_id.upper())
                            )
                        ]
                    ),
                    limit=1,
                    with_payload=True,
                    with_vectors=False
                )
                
                if scroll_results:
                    result = scroll_results[0]
                    return {
                        "id": result.payload.get("id"),
                        "aliases": result.payload.get("aliases", []),
                        "summary": result.payload.get("summary", ""),
                        "content": result.payload.get("content", ""),
                        "ecosystem": result.payload.get("ecosystem"),
                        "published": result.payload.get("published"),
                        "modified": result.payload.get("modified"),
                        "severity": result.payload.get("severity", []),
                        "affected_packages": result.payload.get("affected", []),
                        "references": result.payload.get("references", [])
                    }
            except Exception as scroll_error2:
                error_str = str(scroll_error2).lower()
                if "outputtoosmall" in error_str or "500" in error_str:
                    logger.warning(f"Scroll by ID also failed. Collection may need to be recreated.")
                    logger.warning(f"Run: python recreate_qdrant_collection.py")
                    return None
                else:
                    raise
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting vulnerability by ID: {e}")
            # Return None instead of raising to allow app to continue
            return None
