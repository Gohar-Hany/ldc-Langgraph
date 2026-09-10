import pytest
from app.services.qdrant_cloud_service import QdrantCloudService
from app.schemas.rag_schema import KnowledgeChunk, ChunkMetadata


@pytest.fixture
def local_qdrant():
    """Provides an in-memory Qdrant instance for fast isolated unit tests."""
    from qdrant_client import QdrantClient
    service = QdrantCloudService(url="", api_key="")
    service.client = QdrantClient(":memory:")
    service.collection_name = "test_isolated_collection"
    service.dimension = 4
    service.ensure_collection()
    return service



def test_qdrant_ensure_collection(local_qdrant):
    assert local_qdrant.count_points() == 0


def test_qdrant_upsert_and_search(local_qdrant):
    chunks = [
        KnowledgeChunk(
            id="test_vpn_0",
            content="VPN setup requires GlobalProtect client and MFA.",
            metadata=ChunkMetadata(
                document_name="vpn.md",
                section_title="Setup",
                category="network",
                chunk_index=0
            )
        ),
        KnowledgeChunk(
            id="test_wifi_0",
            content="Connect to Corp-Secure using corporate certificate.",
            metadata=ChunkMetadata(
                document_name="wifi.md",
                section_title="Access",
                category="network",
                chunk_index=0
            )
        )
    ]
    # Synthetic 4-dimensional vectors
    embeddings = [
        [0.9, 0.1, 0.0, 0.0],
        [0.0, 0.0, 0.8, 0.2]
    ]

    upserted = local_qdrant.upsert_chunks(chunks, embeddings)
    assert upserted == 2
    assert local_qdrant.count_points() == 2

    # Query closest to chunk 0
    query_vec = [1.0, 0.0, 0.0, 0.0]
    results = local_qdrant.similarity_search(query_vec, top_k=1)
    assert len(results) == 1
    assert results[0].document_name == "vpn.md"
    assert "GlobalProtect" in results[0].content
    assert results[0].score > 0.8
