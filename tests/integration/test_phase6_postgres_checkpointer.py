import pytest
from unittest.mock import patch, MagicMock
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.base import CheckpointTuple

from app.core.config import settings
from app.agent.graph import (
    init_checkpointer,
    set_checkpointer,
    build_enterprise_support_graph,
    enterprise_agent_graph
)
from app.schemas.auth_schema import UserRole
from app.schemas.intent_schema import IntentType
from langgraph.types import Command


@pytest.fixture
def clean_memory_checkpointer():
    """Provides a fresh isolated MemorySaver checkpointer for testing."""
    saver = MemorySaver()
    set_checkpointer(saver)
    yield saver
    # Reset back to default
    set_checkpointer(MemorySaver())


def test_checkpointer_factory_memory_backend():
    """Verifies that memory backend returns MemorySaver."""
    original_backend = settings.CHECKPOINTER_BACKEND
    try:
        settings.CHECKPOINTER_BACKEND = "memory"
        saver = init_checkpointer()
        assert isinstance(saver, MemorySaver)
    finally:
        settings.CHECKPOINTER_BACKEND = original_backend


def test_checkpointer_factory_resilient_fallback_on_invalid_db_url():
    """
    Critical Enterprise Resilience:
    If DATABASE_URL is configured but database is unreachable or invalid,
    the factory must NOT crash the app; it must gracefully fall back to MemorySaver.
    """
    original_backend = settings.CHECKPOINTER_BACKEND
    original_url = settings.DATABASE_URL
    try:
        settings.CHECKPOINTER_BACKEND = "postgres"
        settings.DATABASE_URL = "postgresql://bad_user:bad_pass@127.0.0.1:59999/non_existent_db"
        saver = init_checkpointer()
        assert isinstance(saver, MemorySaver)
    finally:
        settings.CHECKPOINTER_BACKEND = original_backend
        settings.DATABASE_URL = original_url


def test_checkpointer_mocked_postgres_saver_setup():
    """
    Verifies that when Postgres is configured and accessible,
    PostgresSaver is instantiated and .setup() is executed to run schema migrations.
    """
    original_backend = settings.CHECKPOINTER_BACKEND
    original_url = settings.DATABASE_URL
    try:
        settings.CHECKPOINTER_BACKEND = "postgres"
        settings.DATABASE_URL = "postgresql://postgres:secret@localhost:5432/enterprise_db"

        mock_pool = MagicMock()
        mock_saver = MagicMock()

        with patch("psycopg_pool.ConnectionPool", return_value=mock_pool), \
             patch("langgraph.checkpoint.postgres.PostgresSaver", return_value=mock_saver):
            saver = init_checkpointer()
            assert saver == mock_saver
            mock_saver.setup.assert_called_once()
    finally:
        settings.CHECKPOINTER_BACKEND = original_backend
        settings.DATABASE_URL = original_url


def test_checkpointer_state_persistence_across_invocations(clean_memory_checkpointer):
    """
    Verifies that multi-step graph state is persisted in checkpointer storage
    and can be retrieved by thread_id.
    """
    graph = build_enterprise_support_graph(use_checkpointer=True, custom_checkpointer=clean_memory_checkpointer)
    thread_id = "test_persistence_thread_001"
    config = {"configurable": {"thread_id": thread_id}}

    # Initial invoke
    state_input = {
        "user_id": "test_user_p6",
        "user_role": UserRole.CUSTOMER,
        "raw_message": "Hello enterprise support!",
        "conversation_id": thread_id,
        "thread_id": thread_id,
        "execution_trace": []
    }
    result = graph.invoke(state_input, config=config)

    assert result["intent"] == IntentType.GREETING
    assert "Hello" in result["final_response"] or "مرحبا" in result["final_response"]

    # Verify checkpointer recorded checkpoints for this thread
    checkpoint_tuple = clean_memory_checkpointer.get_tuple(config)
    assert checkpoint_tuple is not None
    assert isinstance(checkpoint_tuple, CheckpointTuple)
    assert checkpoint_tuple.checkpoint["channel_values"]["thread_id"] == thread_id
    assert checkpoint_tuple.checkpoint["channel_values"]["user_id"] == "test_user_p6"


def test_checkpointer_thread_isolation(clean_memory_checkpointer):
    """
    Verifies that different thread IDs maintain isolated conversation states in storage.
    """
    graph = build_enterprise_support_graph(use_checkpointer=True, custom_checkpointer=clean_memory_checkpointer)

    thread_a = "thread_user_alpha"
    thread_b = "thread_user_beta"

    # User A: Greeting
    graph.invoke(
        {
            "user_id": "alpha",
            "user_role": UserRole.CUSTOMER,
            "raw_message": "Hello from Alpha",
            "conversation_id": thread_a,
            "thread_id": thread_a,
            "execution_trace": []
        },
        config={"configurable": {"thread_id": thread_a}}
    )

    # User B: Ticket Search
    graph.invoke(
        {
            "user_id": "beta",
            "user_role": UserRole.CUSTOMER,
            "raw_message": "Check my ticket status #1042",
            "conversation_id": thread_b,
            "thread_id": thread_b,
            "execution_trace": []
        },
        config={"configurable": {"thread_id": thread_b}}
    )

    tuple_a = clean_memory_checkpointer.get_tuple({"configurable": {"thread_id": thread_a}})
    tuple_b = clean_memory_checkpointer.get_tuple({"configurable": {"thread_id": thread_b}})

    assert tuple_a is not None
    assert tuple_b is not None

    # Assert thread isolation
    assert tuple_a.checkpoint["channel_values"]["user_id"] == "alpha"
    assert tuple_a.checkpoint["channel_values"]["raw_message"] == "Hello from Alpha"

    assert tuple_b.checkpoint["channel_values"]["user_id"] == "beta"
    assert tuple_b.checkpoint["channel_values"]["raw_message"] == "Check my ticket status #1042"


def test_checkpointer_interrupt_persistence_and_resumption(clean_memory_checkpointer):
    """
    Validates that when a sensitive operation triggers a LangGraph interrupt(),
    the pending execution state is persisted and can be resumed via Command(resume=...).
    """
    graph = build_enterprise_support_graph(use_checkpointer=True, custom_checkpointer=clean_memory_checkpointer)
    thread_id = "thread_hitl_p6_test"
    config = {"configurable": {"thread_id": thread_id}}

    # 1. Invoke sensitive operation -> Interrupt triggered
    interrupted_state = graph.invoke(
        {
            "user_id": "admin_requester",
            "user_role": UserRole.ADMIN,
            "raw_message": "Reset user password for john.doe",
            "conversation_id": thread_id,
            "thread_id": thread_id,
            "execution_trace": []
        },
        config=config
    )

    # Check interrupt is recorded in checkpoint
    assert "__interrupt__" in interrupted_state
    tuple_interrupt = clean_memory_checkpointer.get_tuple(config)
    assert tuple_interrupt is not None

    # 2. Resume execution using supervisor approval
    resumed_state = graph.invoke(
        Command(resume={"approved": True, "reviewer_id": "senior_supervisor_01", "notes": "Approved by senior supervisor"}),
        config=config
    )

    assert resumed_state["approval_status"] == "APPROVED"
    assert "SUCCESS" in resumed_state["final_response"] or "Approved" in resumed_state["final_response"]
