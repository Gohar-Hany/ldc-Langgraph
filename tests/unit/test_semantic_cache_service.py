import time
import pytest
from qdrant_client import QdrantClient

from app.services.semantic_cache_service import SemanticCacheService
from app.schemas.cache_schema import CachedQueryEntry


class MockEmbeddingService:
    """Deterministic mock embedding service for isolated unit testing."""
    def __init__(self):
        self.dimension = 4

    def embed_query(self, query: str):
        q = query.lower()
        if "vpn" in q or "globalprotect" in q or "connect" in q:
            return [0.95, 0.05, 0.0, 0.0]
        elif "wifi" in q or "network" in q:
            return [0.0, 0.95, 0.05, 0.0]
        elif "hello" in q or "hi" in q:
            return [0.0, 0.0, 0.95, 0.05]
        else:
            return [0.1, 0.1, 0.1, 0.9]


@pytest.fixture
def isolated_cache_service():
    """Provides an in-memory SemanticCacheService for unit tests."""
    client = QdrantClient(":memory:")
    mock_emb = MockEmbeddingService()
    svc = SemanticCacheService(
        client=client,
        embedding_svc=mock_emb,
        collection_name="test_semantic_cache",
        threshold=0.90,
        dimension=4
    )
    return svc


def test_semantic_cache_store_and_lookup_hit(isolated_cache_service):
    # Store initial response
    stored = isolated_cache_service.store(
        query="How to set up VPN?",
        response="Install GlobalProtect and authenticate with corporate MFA.",
        intent="knowledge_search",
        user_role="customer",
        sources=["vpn_setup.md"]
    )
    assert stored is True
    assert isolated_cache_service.count() == 1

    # Look up semantically similar query (same embedding cluster in mock)
    hit = isolated_cache_service.lookup(
        query="Guide to configure corporate VPN",
        user_role="customer"
    )
    assert hit is not None
    assert isinstance(hit, CachedQueryEntry)
    assert "GlobalProtect" in hit.response
    assert hit.similarity_score >= 0.90
    assert "vpn_setup.md" in hit.sources


def test_semantic_cache_miss_on_dissimilar_query(isolated_cache_service):
    isolated_cache_service.store(
        query="How to set up VPN?",
        response="Install GlobalProtect client.",
        intent="knowledge_search",
        user_role="customer"
    )

    # Completely different domain (wifi)
    hit = isolated_cache_service.lookup(
        query="What is the office WiFi password?",
        user_role="customer"
    )
    assert hit is None


def test_semantic_cache_ttl_expiration(isolated_cache_service):
    # Store with 1-second TTL
    isolated_cache_service.store(
        query="Hello assistant",
        response="Hello! How can I help you today?",
        intent="greeting",
        user_role="customer",
        ttl_seconds=1
    )

    # Immediate lookup succeeds
    hit1 = isolated_cache_service.lookup("Hello there", user_role="customer")
    assert hit1 is not None

    # Wait for TTL to expire
    time.sleep(1.2)

    hit2 = isolated_cache_service.lookup("Hello there", user_role="customer")
    assert hit2 is None


def test_semantic_cache_role_isolation(isolated_cache_service):
    # Admin stores a privileged entry
    isolated_cache_service.store(
        query="Internal cluster architecture topology",
        response="Production cluster runs on AWS us-east-1 with 8 worker nodes.",
        intent="knowledge_search",
        user_role="admin"
    )

    # Customer attempts to read admin cached entry -> MUST BE DENIED
    customer_hit = isolated_cache_service.lookup(
        query="Internal cluster architecture topology",
        user_role="customer"
    )
    assert customer_hit is None

    # Admin reading same entry -> PERMITTED
    admin_hit = isolated_cache_service.lookup(
        query="Internal cluster architecture topology",
        user_role="admin"
    )
    assert admin_hit is not None
    assert "AWS us-east-1" in admin_hit.response


def test_semantic_cache_disallows_private_and_mutating_intents(isolated_cache_service):
    # Private customer tickets should NEVER be stored
    ticket_stored = isolated_cache_service.store(
        query="Check status of ticket #1042",
        response="Ticket #1042 is resolved.",
        intent="my_tickets_search",
        user_role="customer"
    )
    assert ticket_stored is False

    # High-privilege mutations should NEVER be stored
    sensitive_stored = isolated_cache_service.store(
        query="Reset password for user John",
        response="Password reset completed.",
        intent="sensitive_operation",
        user_role="senior_agent"
    )
    assert sensitive_stored is False

    # Direct DB queries should NEVER be stored
    db_stored = isolated_cache_service.store(
        query="SELECT * FROM users",
        response="Returned 15 rows.",
        intent="database_query_operation",
        user_role="admin"
    )
    assert db_stored is False

    assert isolated_cache_service.count() == 0


def test_semantic_cache_clear(isolated_cache_service):
    isolated_cache_service.store(
        query="Hello",
        response="Hi there!",
        intent="greeting",
        user_role="customer"
    )
    assert isolated_cache_service.count() >= 1

    isolated_cache_service.clear()
    assert isolated_cache_service.count() == 0
