import logging
from typing import List, Dict, Any, Optional
import uuid
from araya.core.config import settings

logger = logging.getLogger(__name__)

class VectorStoreManager:
    """
    Manages connections and operations for the Vector Database.
    Defaults to Qdrant based on current configuration.
    """
    
    def __init__(self):
        self.client = None
        self.collection_name = settings.QDRANT_COLLECTION
        self._initialized = False

    def _initialize(self):
        """Lazy initialization of the vector store client."""
        if self._initialized:
            return
            
        try:
            from qdrant_client import QdrantClient
            # Try to connect to a real Qdrant instance
            self.client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
            
            # Check connection by listing collections
            self.client.get_collections()
            self._initialized = True
            logger.info(f"Connected to Qdrant at {settings.QDRANT_HOST}:{settings.QDRANT_PORT}")
        except ImportError:
            logger.warning("qdrant-client not installed. Vector store will operate in mock mode.")
            self.client = None
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}. Vector store will operate in mock mode.")
            self.client = None
        finally:
            self._initialized = True

    async def add_text(self, text: str, metadata: Optional[Dict[str, Any]] = None):
        """Add a text chunk with metadata to the vector store."""
        self._initialize()
        if not self.client:
            logger.debug(f"Mock: Adding text: {text[:50]}...")
            return True
            
        try:
            # Qdrant high-level 'add' handles embeddings if fastembed is installed
            self.client.add(
                collection_name=self.collection_name,
                documents=[text],
                metadata=[metadata] if metadata else None,
                ids=[str(uuid.uuid4())]
            )
            return True
        except Exception as e:
            logger.error(f"Error adding to Qdrant: {e}")
            return False

    async def similarity_search(self, query: str, k: int = 4, filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Perform a similarity search in the vector store."""
        self._initialize()
        if not self.client:
            logger.debug(f"Mock: Searching for: {query}")
            return []
            
        try:
            # high-level query method
            results = self.client.query(
                collection_name=self.collection_name,
                query_text=query,
                limit=k
            )
            
            return [
                {
                    "content": res.document,
                    "metadata": res.metadata,
                    "score": res.score
                }
                for res in results
            ]
        except Exception as e:
            logger.error(f"Error searching Qdrant: {e}")
            return []

# Singleton instance
vector_store = VectorStoreManager()
