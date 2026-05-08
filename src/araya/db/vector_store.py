import logging
from typing import List, Dict, Any, Optional
import uuid
from araya.core.config import settings

logger = logging.getLogger(__name__)

class VectorStoreManager:
    """
    Manages connections and operations for the Vector Database.
    Defaults to Qdrant based on current configuration.
    Implements connection reuse and pooling for better performance.
    """
    
    def __init__(self):
        self.client = None
        self.collection_name = settings.QDRANT_COLLECTION
        self._initialized = False
        self._connection_attempts = 0
        self._max_connection_attempts = 3

    def _initialize(self):
        """Lazy initialization of the vector store client with retry logic."""
        if self._initialized:
            return
            
        if self._connection_attempts >= self._max_connection_attempts:
            logger.error(f"Max connection attempts ({self._max_connection_attempts}) reached. Vector store will operate in mock mode.")
            self.client = None
            self._initialized = True
            return

        try:
            from qdrant_client import QdrantClient
            from qdrant_client.http.models import Distance, VectorParams
            
            # Try to connect to a real Qdrant instance
            # QdrantClient is designed to be reused and handles connection pooling internally
            self.client = QdrantClient(
                host=settings.QDRANT_HOST, 
                port=settings.QDRANT_PORT,
                timeout=30.0,  # Request timeout
                prefer_grpc=False  # Use HTTP/REST for better compatibility
            )
            
            # Check connection by listing collections
            collections = self.client.get_collections()
            logger.info(f"Connected to Qdrant at {settings.QDRANT_HOST}:{settings.QDRANT_PORT}. Found {len(collections.collections)} collections.")
            
            # Ensure our collection exists
            collection_names = [col.name for col in collections.collections]
            if self.collection_name not in collection_names:
                logger.info(f"Creating collection '{self.collection_name}'")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=768, distance=Distance.COSINE),  # Adjust size based on your embedding model
                )
                logger.info(f"Collection '{self.collection_name}' created successfully")
            
            self._initialized = True
            self._connection_attempts = 0  # Reset on success
        except ImportError:
            logger.warning("qdrant-client not installed. Vector store will operate in mock mode.")
            self.client = None
            self._initialized = True
        except Exception as e:
            self._connection_attempts += 1
            logger.warning(f"Failed to connect to Qdrant (attempt {self._connection_attempts}/{self._max_connection_attempts}): {e}")
            if self._connection_attempts >= self._max_connection_attempts:
                logger.error(f"Max connection attempts reached. Vector store will operate in mock mode.")
                self.client = None
                self._initialized = True
            else:
                # Retry after a brief delay
                import time
                time.sleep(1)
                self._initialize()  # Recursive retry

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
            # Try to reconnect on failure
            self._initialized = False
            self._connection_attempts = 0
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
            # Try to reconnect on failure
            self._initialized = False
            self._connection_attempts = 0
            return []

    def close(self):
        """Close the vector store connection."""
        if self.client:
            try:
                # QdrantClient doesn't have an explicit close method in older versions
                # In newer versions, you might need to close the transport
                if hasattr(self.client, 'close'):
                    self.client.close()
                logger.info("Qdrant client connection closed")
            except Exception as e:
                logger.warning(f"Error closing Qdrant client: {e}")
            finally:
                self.client = None
                self._initialized = False

# Singleton instance
vector_store = VectorStoreManager()
