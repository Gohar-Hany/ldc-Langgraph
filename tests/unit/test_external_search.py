import pytest
from unittest.mock import MagicMock, patch

from app.services.external_search_service import ExternalSearchService


@pytest.fixture
def search_service():
    return ExternalSearchService()


def test_empty_query_returns_error(search_service):
    res = search_service.search("")
    assert res["success"] is False
    assert res["results"] == []
    assert "cannot be empty" in res["error"]


def test_resilient_fallback_aws():
    service = ExternalSearchService()
    service.client = None  # Force fallback path
    res = service.search("Is AWS us-east-1 down right now?")
    assert res["success"] is True
    assert res["is_fallback"] is True
    assert len(res["results"]) > 0
    assert any("aws" in r["title"].lower() for r in res["results"])


def test_resilient_fallback_github():
    service = ExternalSearchService()
    service.client = None  # Force fallback path
    res = service.search("Check GitHub Actions and Webhooks status")
    assert res["success"] is True
    assert res["is_fallback"] is True
    assert any("github" in r["title"].lower() for r in res["results"])


def test_live_or_mock_tavily_search():
    service = ExternalSearchService()
    res = service.search("Status of AWS cloud services")
    assert res["success"] is True
    assert len(res["results"]) > 0
    if service.client:
        assert res["provider"] == "tavily"
        assert res["is_fallback"] is False
    else:
        assert res["is_fallback"] is True


def test_tavily_client_mock_success():
    service = ExternalSearchService()
    mock_tavily_client = MagicMock()
    mock_tavily_client.search.return_value = {
        "answer": "All systems nominal for test vendor.",
        "results": [
            {
                "title": "Vendor Live Status",
                "url": "https://status.vendor.example.com",
                "content": "Status 100% operational.",
                "score": 0.99
            }
        ]
    }
    service.client = mock_tavily_client

    res = service.search("Query vendor live status")
    assert res["success"] is True
    assert res["provider"] == "tavily"
    assert res["is_fallback"] is False
    assert "All systems nominal" in res["answer"]
    assert res["results"][0]["url"] == "https://status.vendor.example.com"


def test_tavily_client_exception_triggers_fallback():
    service = ExternalSearchService()
    mock_tavily_client = MagicMock()
    mock_tavily_client.search.side_effect = TimeoutError("External API request timed out")
    service.client = mock_tavily_client

    res = service.search("AWS cloud computing health")
    assert res["success"] is True
    assert res["is_fallback"] is True
    assert res["provider"] == "tavily_fallback"
