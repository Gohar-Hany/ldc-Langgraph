"""
Shared utility helpers for LangGraph agent nodes.

Centralises helpers that were previously duplicated across node modules (Fix H-01).
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def append_trace(
    trace: Optional[List[Dict[str, Any]]],
    node_name: str,
    status: str = "success",
    details: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Appends a structured trace entry to the execution trace list and returns it.

    Args:
        trace:     Existing trace list (may be None — will be treated as empty).
        node_name: Name of the graph node being recorded.
        status:    Outcome status string (e.g. 'success', 'failed', 'forbidden').
        details:   Optional dict of additional context (kept only when provided).

    Returns:
        The updated trace list (same object, mutated in-place and returned for chaining).
    """
    trace = trace or []
    entry: Dict[str, Any] = {
        "step_name": node_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": status,
    }
    if details is not None:
        entry["details"] = details
    trace.append(entry)
    return trace
