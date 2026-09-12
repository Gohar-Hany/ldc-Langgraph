from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CachedQueryEntry(BaseModel):
    """Represents a cached query-response item in the semantic vector store."""
    query: str = Field(..., description="The original sanitized query text that was cached")
    response: str = Field(..., description="The synthesized response that was cached")
    intent: str = Field(..., description="The intent classification of the cached entry")
    user_role: str = Field(..., description="The minimal user role permitted to read this entry")
    sources: List[str] = Field(default_factory=list, description="Knowledge base sources/citations")
    similarity_score: float = Field(default=1.0, description="Cosine similarity score against lookup query")
    created_at: float = Field(..., description="Unix timestamp of creation")
    ttl_seconds: int = Field(default=604800, description="Time-To-Live in seconds")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional context metadata")
