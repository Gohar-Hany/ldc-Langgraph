from pathlib import Path
from unittest.mock import MagicMock
import pytest
from app.services.docling_ingestion import DoclingIngestionService


def test_infer_category():
    """Unit test for category inference heuristics (isolated from heavy ML models)."""
    service = object.__new__(DoclingIngestionService)
    assert service._infer_category("vpn_access_policy.md") == "network"
    assert service._infer_category("wifi_network_access.md") == "network"
    assert service._infer_category("password_mfa_policy.md") == "security"
    assert service._infer_category("hardware_procurement.md") == "hardware"
    assert service._infer_category("software_license_guidelines.md") == "software"
    assert service._infer_category("random_doc.md") == "general"


@pytest.mark.slow
def test_docling_parse_single_file():
    file_path = Path("data/knowledge_base/vpn_access_policy.md")
    assert file_path.exists(), "VPN policy file must exist for ingestion test"
    
    ingestion_service = DoclingIngestionService(kb_dir="data/knowledge_base")
    chunks = ingestion_service.parse_file(file_path)
    assert len(chunks) > 0
    
    # Check first chunk properties
    first_chunk = chunks[0]
    assert first_chunk.id.startswith("vpn_access_policy_chunk_")
    assert len(first_chunk.content) > 10
    assert first_chunk.metadata.document_name == "vpn_access_policy.md"
    assert first_chunk.metadata.category == "network"
    assert first_chunk.metadata.section_title is not None


@pytest.mark.slow
def test_docling_parse_directory():
    ingestion_service = DoclingIngestionService(kb_dir="data/knowledge_base")
    all_chunks = ingestion_service.parse_directory()
    assert len(all_chunks) >= 20, "Should have parsed multiple documents across knowledge base"
    
    doc_names = {c.metadata.document_name for c in all_chunks}
    assert "vpn_access_policy.md" in doc_names
    assert "wifi_network_access.md" in doc_names
    assert "password_mfa_policy.md" in doc_names

