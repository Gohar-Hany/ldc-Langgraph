from typing import List, Union
import httpx
from app.core.config import settings
from app.core.logging import logger


class OpenRouterEmbeddingService:
    """Service to generate cloud embeddings using OpenRouter's embeddings API."""

    def __init__(self):
        self.api_key = settings.OPENROUTER_API_KEY
        self.base_url = settings.OPENROUTER_BASE_URL.rstrip("/")
        self.model = settings.EMBEDDING_MODEL
        self.dimension = settings.EMBEDDING_DIMENSION

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of text strings."""
        if not texts:
            return []

        endpoint = f"{self.base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "input": texts
        }

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(endpoint, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                
                # Sort by index to maintain original order
                embeddings_data = sorted(data.get("data", []), key=lambda x: x.get("index", 0))
                embeddings = [item["embedding"] for item in embeddings_data]
                
                logger.info(f"[OpenRouterEmbedding] Generated {len(embeddings)} embeddings using {self.model}.")
                return embeddings
        except Exception as exc:
            logger.error(f"[OpenRouterEmbedding: Error] Failed to generate embeddings: {exc}")
            raise RuntimeError(f"Embedding generation failed: {exc}") from exc

    def embed_query(self, query: str) -> List[float]:
        """Generate embedding for a single search query string."""
        results = self.embed_texts([query])
        if not results:
            raise ValueError("No embedding returned for query.")
        return results[0]


embedding_service = OpenRouterEmbeddingService()
