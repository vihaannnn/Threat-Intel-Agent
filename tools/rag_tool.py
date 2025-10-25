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
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise
    
    async def search_vulnerabilities(
        self, 
        query: str, 
        entities: ExtractedEntities,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Vulnerability search with ecosystem filtering
        
        Args:
            query: User's search query
            entities: Entities extracted by LLM
            limit: Maximum number of results to return
            
        Returns:
            Dictionary containing search results and metadata
        """
        try:
            logger.info(f"Search with entities: {entities}")
            
            # Generate embedding for semantic search
            query_embedding = await self.generate_embedding(query)
            
            # Build ecosystem filter
            ecosystem_filter = self._build_ecosystem_filter(entities)
            
            # Perform vector search with ecosystem filtering
            search_results = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                query_filter=ecosystem_filter,
                limit=limit,
                with_payload=True
            )
            
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
            # Search for the specific vulnerability ID
            search_results = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=[0] * 1536,  # Dummy vector since we're filtering by ID
                query_filter=Filter(
                    must=[
                        FieldCondition(
                            key="aliases",
                            match=MatchValue(value=vuln_id)
                        )
                    ]
                ),
                limit=1,
                with_payload=True
            )
            
            if search_results:
                result = search_results[0]
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
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting vulnerability by ID: {e}")
            raise
