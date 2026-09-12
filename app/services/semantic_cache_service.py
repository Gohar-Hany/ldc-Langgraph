import time
import uuid
from typing import Any, Dict, List, Optional
from qdrant_client import QdrantClient, models
from qdrant_client.models import VectorParams, Distance, PointStruct, Filter, FieldCondition, MatchValue

from app.core.config import settings
from app.core.logging import logger
from app.schemas.cache_schema import CachedQueryEntry
from app.services.openrouter_embedding import OpenRouterEmbeddingService, embedding_service


# Role hierarchy for access isolation in semantic cache
ROLE_HIERARCHY = {
    "customer": 1,
    "support_agent": 2,
    "senior_agent": 3,
    "admin": 4
}

# Intents permitted to be stored in semantic cache (stateful/private intents are strictly excluded)
CACHEABLE_INTENTS = {
    "knowledge_search",
    "greeting",
    "out_of_scope"
}


class SemanticCacheService:
    """
    Enterprise Vector Semantic Caching Service (Phase 9 - FinOps & Latency Optimization):
    - Embeds queries and searches Qdrant for semantic matches (Cosine Similarity >= 0.92).
    - Returns cached responses in < 25ms, saving 100% of LLM tokens on recurring inquiries.
    - Strictly isolates role permissions (Customers cannot read Agent-cached responses).
    - Enforces TTL (Time-To-Live) expiration.
    - Prevents caching of user-private data (Tickets) and privileged mutations (Sensitive ops, DB queries).
    """

    def __init__(
        self,
        client: Optional[QdrantClient] = None,
        embedding_svc: Optional[OpenRouterEmbeddingService] = None,
        collection_name: Optional[str] = None,
        threshold: Optional[float] = None,
        dimension: Optional[int] = None
    ):
        self.collection_name = collection_name or settings.SEMANTIC_CACHE_COLLECTION_NAME
        self.embedding_service = embedding_svc or embedding_service
        self.dimension = dimension or (getattr(self.embedding_service, "dimension", None) or settings.EMBEDDING_DIMENSION)
        self.threshold = threshold if threshold is not None else settings.SEMANTIC_CACHE_THRESHOLD
        self.ttl_seconds = settings.SEMANTIC_CACHE_TTL_SECONDS

        if client:
            self.client = client
        elif settings.QDRANT_URL and settings.QDRANT_API_KEY:
            self.client = QdrantClient(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY,
                check_compatibility=False,
                timeout=15.0
            )
        else:
            logger.warning("[SemanticCache] Credentials not found; using in-memory Qdrant client.")
            self.client = QdrantClient(":memory:")

        self._ensure_collection()

    def _ensure_collection(self) -> None:
        """Ensures the semantic cache collection exists in Qdrant with cosine metric."""
        try:
            collections = self.client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)
            if not exists:
                logger.info(f"[SemanticCache] Creating collection '{self.collection_name}' (dim={self.dimension})...")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.dimension,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"[SemanticCache] Collection '{self.collection_name}' created.")
        except Exception as exc:
            logger.error(f"[SemanticCache: Error] Failed to ensure collection: {exc}")

    def lookup(
        self,
        query: str,
        user_role: str,
        threshold: Optional[float] = None
    ) -> Optional[CachedQueryEntry]:
        """
        Searches semantic cache for a query with cosine similarity >= threshold.
        Returns CachedQueryEntry if a fresh, authorized match is found, else None.
        """
        if not settings.SEMANTIC_CACHE_ENABLED:
            return None

        clean_query = query.strip()
        if len(clean_query) < 3:
            return None

        sim_threshold = threshold if threshold is not None else self.threshold

        try:
            query_vector = self.embedding_service.embed_query(clean_query)
        except Exception as exc:
            logger.warning(f"[SemanticCache] Embedding generation skipped or failed ({exc}). Treating as cache miss.")
            return None

        try:
            response = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                limit=1,
                with_payload=True
            )

            if not response.points:
                return None

            top_point = response.points[0]
            similarity_score = float(top_point.score)

            if similarity_score < sim_threshold:
                logger.debug(f"[SemanticCache] Top match score {similarity_score:.3f} below threshold {sim_threshold:.3f}.")
                return None

            payload = top_point.payload or {}
            created_at = float(payload.get("created_at", 0.0))
            entry_ttl = int(payload.get("ttl_seconds", self.ttl_seconds))

            # 1. TTL Check
            if (time.time() - created_at) > entry_ttl:
                logger.info(f"[SemanticCache] Expired entry ignored for query '{clean_query[:40]}' (age: {time.time()-created_at:.0f}s).")
                return None

            # 2. RBAC Role Isolation Check
            entry_role = str(payload.get("user_role", "customer")).lower()
            current_role_lvl = ROLE_HIERARCHY.get(str(user_role).lower(), 1)
            entry_role_lvl = ROLE_HIERARCHY.get(entry_role, 1)

            if current_role_lvl < entry_role_lvl:
                logger.warning(
                    f"[SemanticCache] Role violation: user with role '{user_role}' "
                    f"cannot access entry cached for higher role '{entry_role}'."
                )
                return None

            logger.info(
                f"[SemanticCache: HIT] Query '{clean_query[:40]}...' matched cached query "
                f"'{payload.get('query', '')[:40]}...' (similarity: {similarity_score:.4f})."
            )

            return CachedQueryEntry(
                query=payload.get("query", clean_query),
                response=payload.get("response", ""),
                intent=payload.get("intent", "knowledge_search"),
                user_role=entry_role,
                sources=payload.get("sources", []),
                similarity_score=round(similarity_score, 4),
                created_at=created_at,
                ttl_seconds=entry_ttl
            )

        except Exception as exc:
            logger.error(f"[SemanticCache: Lookup Error] {exc}")
            return None

    def store(
        self,
        query: str,
        response: str,
        intent: str,
        user_role: str,
        sources: Optional[List[str]] = None,
        ttl_seconds: Optional[int] = None
    ) -> bool:
        """
        Stores a query-response pair in the semantic cache if the intent is cacheable.
        """
        if not settings.SEMANTIC_CACHE_ENABLED:
            return False

        clean_intent = intent.lower()
        if hasattr(intent, "value"):
            clean_intent = intent.value.lower()

        # Strict Security & FinOps Guard: Never cache private or mutating operations
        if clean_intent not in CACHEABLE_INTENTS:
            logger.debug(f"[SemanticCache] Skipping store for non-cacheable intent: '{clean_intent}'")
            return False

        clean_query = query.strip()
        clean_response = response.strip()

        if len(clean_query) < 3 or len(clean_response) < 5:
            return False

        try:
            vector = self.embedding_service.embed_query(clean_query)
        except Exception as exc:
            logger.warning(f"[SemanticCache] Embedding failed on store ({exc}). Skipping cache insert.")
            return False

        try:
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{clean_query.lower()}_{user_role.lower()}"))
            payload = {
                "query": clean_query,
                "response": clean_response,
                "intent": clean_intent,
                "user_role": str(user_role).lower(),
                "sources": sources or [],
                "created_at": time.time(),
                "ttl_seconds": ttl_seconds or self.ttl_seconds
            }

            self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    PointStruct(
                        id=point_id,
                        vector=vector,
                        payload=payload
                    )
                ]
            )
            logger.info(f"[SemanticCache: STORE] Stored response for query '{clean_query[:40]}...' (intent: {clean_intent}).")
            return True

        except Exception as exc:
            logger.error(f"[SemanticCache: Store Error] {exc}")
            return False

    def count(self) -> int:
        """Returns total entries currently stored in the cache collection."""
        try:
            info = self.client.get_collection(collection_name=self.collection_name)
            return info.points_count or 0
        except Exception:
            return 0

    def clear(self) -> None:
        """Clears all entries in the cache collection."""
        try:
            self.client.delete_collection(collection_name=self.collection_name)
            self._ensure_collection()
            logger.info("[SemanticCache] Cleared and recreated cache collection.")
        except Exception as exc:
            logger.debug(f"[SemanticCache] Clear note: {exc}")


# Singleton instance
semantic_cache_service = SemanticCacheService()
