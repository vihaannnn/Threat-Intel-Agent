"""
Script to embed OSV vulnerability data into Qdrant vector database
"""

import json
import os
import logging
from pathlib import Path
from typing import List, Dict, Any
import time

import openai
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct

import sys
from pathlib import Path

# Add parent directory to path to import utils
sys.path.append(str(Path(__file__).parent.parent))
from utils.config import OPENAI_KEY as openai_api_key

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536
COLLECTION_NAME = "osv_vulnerabilities"
BATCH_SIZE = 50  # Original batch size


def generate_embedding(text: str, client: openai.OpenAI) -> List[float]:
    """Generate embedding for given text using OpenAI"""
    try:
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        raise


def load_vulnerability_data(data_dir: Path) -> List[Dict]:
    """Load all vulnerability data from JSON files"""
    documents = []
    
    if not data_dir.exists():
        logger.error(f"Data directory not found: {data_dir}")
        return documents
    
    json_files = list(data_dir.glob("*.json"))
    logger.info(f"Found {len(json_files)} JSON files to process")
    
    for json_file in json_files:
        if json_file.name == "collection_summary.json":
            continue  # Skip summary file
            
        logger.info(f"Processing {json_file.name}")
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for entry in data:
                if "content" in entry and "metadata" in entry:
                    documents.append({
                        "id": entry["metadata"].get("id", ""),
                        "content": entry["content"],
                        "metadata": entry["metadata"]
                    })
            
            logger.info(f"Loaded {len(data)} entries from {json_file.name}")
            
        except Exception as e:
            logger.error(f"Error loading {json_file.name}: {e}")
            continue
    
    logger.info(f"Total documents loaded: {len(documents)}")
    return documents


def setup_qdrant_collection(client: QdrantClient):
    """Create Qdrant collection if it doesn't exist"""
    try:
        if not client.collection_exists(COLLECTION_NAME):
            logger.info(f"Creating Qdrant collection: {COLLECTION_NAME}")
            client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=EMBEDDING_DIMENSION,
                    distance=Distance.COSINE
                )
            )
            logger.info("Collection created successfully")
        else:
            logger.info(f"Collection {COLLECTION_NAME} already exists")
    except Exception as e:
        logger.error(f"Error creating collection: {e}")
        raise


def embed_and_store_data(documents: List[Dict], openai_client: openai.OpenAI, qdrant_client: QdrantClient):
    """Generate embeddings and store in Qdrant"""
    logger.info(f"Generating embeddings for {len(documents)} documents")
    
    # Process in batches to avoid rate limits
    for i in range(0, len(documents), BATCH_SIZE):
        batch = documents[i:i + BATCH_SIZE]
        batch_num = i//BATCH_SIZE + 1
        total_batches = (len(documents) + BATCH_SIZE - 1)//BATCH_SIZE
        logger.info(f"Processing batch {batch_num}/{total_batches}")
        
        # Extract texts for batch embedding
        texts = [doc["content"] for doc in batch]
        
        try:
            response = openai_client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=texts
            )
            
            # Create points for Qdrant
            points = []
            for idx, (doc, embedding_data) in enumerate(zip(batch, response.data)):
                # Convert string ID to integer for Qdrant compatibility
                # Use a hash of the string ID to ensure uniqueness
                point_id = hash(doc["id"]) & 0x7FFFFFFFFFFFFFFF  # Convert to positive 64-bit integer
                
                point = PointStruct(
                    id=point_id,
                    vector=embedding_data.embedding,
                    payload={
                        **doc["metadata"],
                        "content": doc["content"]  # Include content in payload
                    }
                )
                points.append(point)
            
            # Store in Qdrant
            qdrant_client.upsert(
                collection_name=COLLECTION_NAME,
                points=points
            )
            
            logger.info(f"Stored batch {batch_num}/{total_batches}")
            
            # Small delay to respect rate limits
            time.sleep(0.1)
            
        except Exception as e:
            logger.error(f"Error processing batch {i//BATCH_SIZE + 1}: {e}")
            continue
    
    logger.info("Finished storing documents in Qdrant")


def main():
    """Main setup function"""
    
    # Check if data directory exists (look in root directory)
    # Script can be run from root or from data directory
    script_dir = Path(__file__).parent
    root_dir = script_dir.parent
    data_dir = root_dir / "osv_data"
    
    # Try both locations
    if not data_dir.exists():
        data_dir = Path("osv_data")  # Try current directory
    
    if not data_dir.exists():
        logger.error(f"Data directory not found: {data_dir}")
        logger.error("\n⚠️  You need to collect vulnerability data first!")
        logger.error("Run the data collector:")
        logger.error("  python data/osv_collector.py")
        logger.error("\nThis will download and process vulnerability data from OSV.dev")
        return False
    
    # Check for JSON files
    json_files = list(data_dir.glob("*.json"))
    if len(json_files) <= 1:  # Only collection_summary.json
        logger.error(f"No vulnerability data files found in {data_dir}")
        logger.error("Expected files like: npm_vulnerabilities.json, PyPI_vulnerabilities.json, etc.")
        logger.error("\nRun the data collector first:")
        logger.error("  python data/osv_collector.py")
        return False
    
    logger.info(f"Using data directory: {data_dir}")
    
    logger.info(f"Found {len(json_files) - 1} vulnerability data files")
    
    try:
        # Initialize clients
        openai_client = openai.OpenAI(api_key=openai_api_key)
        qdrant_client = QdrantClient(host="localhost", port=6333)
        
        # Setup collection
        setup_qdrant_collection(qdrant_client)
        
        # Load data
        documents = load_vulnerability_data(data_dir)
        if not documents:
            logger.error("No documents loaded. Exiting.")
            return False
        
        # Embed and store
        embed_and_store_data(documents, openai_client, qdrant_client)
        
        # Get collection info
        collection_info = qdrant_client.get_collection(COLLECTION_NAME)
        logger.info(f"Collection setup complete!")
        logger.info(f"Total points in collection: {collection_info.points_count}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error during setup: {e}")
        return False


if __name__ == "__main__":
    success = main()
    if success:
        logger.info("Vector database setup completed successfully!")
    else:
        logger.error("Vector database setup failed!")
