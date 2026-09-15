"""Pydantic schemas for Schema-Aware Dynamic Database Queries."""
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class FilterCondition(BaseModel):
    column: str = Field(description="Column name to filter on, e.g. 'status', 'priority', 'role', 'category'")
    operator: Literal["eq", "neq", "like", "ilike", "gt", "lt", "gte", "lte"] = Field(
        default="eq",
        description="Filter operator: eq for exact match, ilike for case-insensitive substring, etc."
    )
    value: Any = Field(description="Value to compare against, e.g. 'open', 'high', 'admin', 'customer'")


class DatabaseQuerySpec(BaseModel):
    target_table: Literal["users", "tickets", "audit_logs"] = Field(
        description="Target Supabase table to query based on user request."
    )
    columns: Optional[List[str]] = Field(
        default=None,
        description="Specific columns to retrieve. If None or empty, selects standard informative columns."
    )
    filters: List[FilterCondition] = Field(
        default_factory=list,
        description="Filter conditions to apply to the query."
    )
    order_by: Optional[str] = Field(
        default="created_at",
        description="Column to sort results by. Defaults to 'created_at'."
    )
    order_direction: Literal["asc", "desc"] = Field(
        default="desc",
        description="Sort direction: 'desc' for newest first, 'asc' for oldest first."
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of rows to return (default: 10, max: 50)."
    )
    query_explanation_ar: str = Field(
        description="Brief 1-sentence explanation in natural Arabic describing what this query searches for."
    )
    query_explanation_en: str = Field(
        description="Brief 1-sentence explanation in natural English describing what this query searches for."
    )
