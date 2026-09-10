import uuid
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient, models
from qdrant_client.models import VectorParams, Distance, PointStruct, Filter, FieldCondition, MatchValue

from app.core.config import settings
from app.core.logging import logger
from app.schemas.rag_schema import RetrievedDocument, KnowledgeChunk


class QdrantCloudService:
    """Service to interact with Qdrant Cloud cluster for vector and payload storage."""

    def __init__(self, url: Optional[str] = None, api_key: Optional[str] = None):
        self.url = url or settings.QDRANT_URL
        self.api_key = api_key or settings.QDRANT_API_KEY
        self.collection_name = settings.QDRANT_COLLECTION_NAME
        self.dimension = settings.EMBEDDING_DIMENSION
        
        # Initialize client
        if self.url and self.api_key:
            logger.info(f"[QdrantCloudService] Connecting to Qdrant Cloud at {self.url[:35]}...")
            self.client = QdrantClient(
                url=self.url,
                api_key=self.api_key,
                check_compatibility=False,
                timeout=30.0
            )
        else:
            logger.warning("[QdrantCloudService] Credentials not found; falling back to in-memory Qdrant instance.")
            self.client = QdrantClient(":memory:")

    def ensure_collection(self) -> None:
        """Create the collection if it does not already exist."""
        try:
            collections = self.client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)
            
            if not exists:
                logger.info(f"[QdrantCloudService] Creating collection '{self.collection_name}' (dim={self.dimension})...")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.dimension,
                        distance=Distance.COSINE
                    )
                )
                
                # Create payload indexes for faster filtering
                for field in ["document_name", "category", "section_title"]:
                    try:
                        self.client.create_payload_index(
                            collection_name=self.collection_name,
                            field_name=field,
                            field_schema=models.PayloadSchemaType.KEYWORD
                        )
                    except Exception as e:
                        logger.debug(f"[QdrantCloudService] Index for {field} creation note: {e}")
                        
                logger.info(f"[QdrantCloudService] Collection '{self.collection_name}' ready with payload indices.")
            else:
                logger.info(f"[QdrantCloudService] Collection '{self.collection_name}' already exists.")
        except Exception as exc:
            logger.error(f"[QdrantCloudService: Error] Failed to ensure collection: {exc}")
            raise

    def count_points(self) -> int:
        """Return number of points currently in the collection."""
        try:
            info = self.client.get_collection(collection_name=self.collection_name)
            return info.points_count or 0
        except Exception:
            return 0

    def upsert_chunks(self, chunks: List[KnowledgeChunk], embeddings: List[List[float]]) -> int:
        """Upsert document chunks and their embeddings into Qdrant."""
        if len(chunks) != len(embeddings):
            raise ValueError(f"Mismatched counts: {len(chunks)} chunks vs {len(embeddings)} embeddings")

        points = []
        for chunk, emb in zip(chunks, embeddings):
            # Generate deterministic UUID from chunk ID or random UUID
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk.id))
            payload = {
                "chunk_id": chunk.id,
                "content": chunk.content,
                "document_name": chunk.metadata.document_name,
                "section_title": chunk.metadata.section_title,
                "category": chunk.metadata.category,
                "chunk_index": chunk.metadata.chunk_index
            }
            points.append(PointStruct(id=point_id, vector=emb, payload=payload))

        self.client.upsert(collection_name=self.collection_name, points=points)
        logger.info(f"[QdrantCloudService] Successfully upserted {len(points)} points into '{self.collection_name}'.")
        return len(points)

    def similarity_search(
        self,
        query_vector: List[float],
        top_k: int = 4,
        category: Optional[str] = None
    ) -> List[RetrievedDocument]:
        """Search the collection for chunks most similar to query vector."""
        query_filter = None
        if category:
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="category",
                        match=MatchValue(value=category)
                    )
                ]
            )

        # qdrant-client 1.16+ uses query_points
        response = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            query_filter=query_filter,
            limit=top_k,
            with_payload=True
        )

        documents: List[RetrievedDocument] = []
        for res in response.points:
            payload = res.payload or {}
            doc = RetrievedDocument(
                content=payload.get("content", ""),
                document_name=payload.get("document_name", "unknown"),
                section_title=payload.get("section_title", "General"),
                category=payload.get("category", "general"),
                score=float(res.score)
            )
            documents.append(doc)

        logger.info(f"[QdrantCloudService] Retrieved {len(documents)} matching chunks (top score: {documents[0].score if documents else 0.0:.3f}).")
        return documents



qdrant_service = QdrantCloudService()
