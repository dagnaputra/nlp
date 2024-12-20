from typing import List, Dict, Any
from abc import ABC, abstractmethod
from pydantic import BaseModel
from api.core.config import settings
from pymilvus import connections, Collection


class CollectionConfig(BaseModel):
    name: str
    dimension: int
    distance: str = "cosine"  # or "euclidean", "dot"
    metadata_schema: Dict[str, str] = {
        "content": "text",
        "title": "text",
        "file_path": "text",
        "file_type": "keyword",
        "chunk_index": "integer",
        "token_count": "integer",
        "file_size": "integer",
        "created_at": "float",
        "modified_at": "float"
    }
    on_disk_payload: bool = False
    replication_factor: int = 1

class VectorDBException(Exception):
    """Base exception for vector database operations"""
    pass

class VectorDBBase(ABC):
    @abstractmethod
    def create_collection(self, config: CollectionConfig) -> bool:
        pass

    @abstractmethod
    def delete_collection(self, collection_name: str) -> bool:
        pass

    @abstractmethod
    def list_collections(self) -> List[str]:
        pass

    @abstractmethod
    def collection_exists(self, collection_name: str) -> bool:
        pass

    @abstractmethod
    def search(self, collection_name: str, query_vector: List[float], limit: int = 5):
        pass

    @abstractmethod
    def add_documents(self, collection_name: str, documents: List[Dict[str, Any]], embeddings: List[List[float]]):
        pass

class QdrantDB(VectorDBBase):
    def __init__(self):
        from qdrant_client import QdrantClient
        from qdrant_client.http import models
        self.client = QdrantClient(url=settings.VECTOR_DB_URL, api_key=settings.VECTOR_DB_API_KEY)
        self.models = models
        from uuid import uuid4
        self.uuid4 = uuid4

    def create_collection(self, config: CollectionConfig) -> bool:
        try:
            distance_map = {
                "cosine": self.models.Distance.COSINE,
                "euclidean": self.models.Distance.EUCLID,
                "dot": self.models.Distance.DOT,
            }
            
            vectors_config = self.models.VectorParams(
                size=config.dimension,
                distance=distance_map.get(config.distance, self.models.Distance.COSINE)
            )
            
            self.client.create_collection(
                collection_name=config.name,
                vectors_config=vectors_config,
                on_disk_payload=config.on_disk_payload
            )
            return True
        except Exception as e:
            raise VectorDBException(f"Failed to create collection: {str(e)}")

    def delete_collection(self, collection_name: str) -> bool:
        try:
            self.client.delete_collection(collection_name=collection_name)
            return True
        except Exception as e:
            raise VectorDBException(f"Failed to delete collection: {str(e)}")

    def list_collections(self) -> List[str]:
        try:
            # Get collections and extract names
            collections = self.client.get_collections()
            return [collection.name for collection in collections.collections]
        except Exception as e:
            raise VectorDBException(f"Failed to list collections: {str(e)}")

    def collection_exists(self, collection_name: str) -> bool:
        try:
            collections = self.list_collections()
            return collection_name in collections
        except Exception as e:
            raise VectorDBException(f"Failed to check collection existence: {str(e)}")

    def search(self, collection_name: str, query_vector: List[float], limit: int = 5):
        try:
            return self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit
            )
        except Exception as e:
            raise VectorDBException(f"Search failed: {str(e)}")

    def add_documents(self, collection_name: str, documents: List[Dict[str, Any]], embeddings: List[List[float]]):
        try:
            points = []
            for i, (document, embedding) in enumerate(zip(documents, embeddings)):
                # Generate a UUID for each point
                point_id = str(self.uuid4())
                
                point = self.models.PointStruct(
                    id=point_id,  # Using UUID as ID
                    vector=embedding,
                    payload={
                        "content": document.get("content", ""),
                        "title": document.get("title", ""),
                        "file_path": document.get("file_path", ""),
                        "file_type": document.get("file_type", ""),
                        "chunk_index": document.get("chunk_index", 0),
                        "token_count": document.get("token_count", 0),
                        "file_size": document.get("file_size", 0),
                        "created_at": document.get("created_at", 0.0),
                        "modified_at": document.get("modified_at", 0.0)
                    }
                )
                points.append(point)
            
            # Add points in batches to avoid potential memory issues
            batch_size = 100
            for i in range(0, len(points), batch_size):
                batch = points[i:i + batch_size]
                self.client.upsert(
                    collection_name=collection_name,
                    points=batch
                )
                print(f"Uploaded batch {i//batch_size + 1} of {(len(points) + batch_size - 1)//batch_size}")
                
        except Exception as e:
            import traceback
            print(f"Detailed error: {traceback.format_exc()}")
            raise VectorDBException(f"Failed to add documents: {str(e)}")

def get_vector_db() -> VectorDBBase:
    if settings.VECTOR_DB_TYPE == "qdrant":
        return QdrantDB()
    else:
        raise ValueError(f"Unsupported vector database type: {settings.VECTOR_DB_TYPE}")
