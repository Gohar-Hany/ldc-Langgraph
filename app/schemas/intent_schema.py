from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

from app.schemas.auth_schema import UserRole


class IntentType(str, Enum):
    GREETING = "greeting"
    KNOWLEDGE_SEARCH = "knowledge_search"
    MY_TICKETS_SEARCH = "my_tickets_search"
    TICKET_CREATE_UPDATE = "ticket_create_update"
    EXTERNAL_API_SEARCH = "external_api_search"
    SENSITIVE_OPERATION = "sensitive_operation"
    DATABASE_QUERY_OPERATION = "database_query_operation"
    OUT_OF_SCOPE = "out_of_scope"


# Role-Based Permission Requirements Matrix
INTENT_REQUIRED_ROLES = {
    IntentType.GREETING: [
        UserRole.CUSTOMER,
        UserRole.SUPPORT_AGENT,
        UserRole.SENIOR_AGENT,
        UserRole.ADMIN
    ],
    IntentType.KNOWLEDGE_SEARCH: [
        UserRole.CUSTOMER,
        UserRole.SUPPORT_AGENT,
        UserRole.SENIOR_AGENT,
        UserRole.ADMIN
    ],
    IntentType.MY_TICKETS_SEARCH: [
        UserRole.CUSTOMER,
        UserRole.SUPPORT_AGENT,
        UserRole.SENIOR_AGENT,
        UserRole.ADMIN
    ],
    IntentType.TICKET_CREATE_UPDATE: [
        UserRole.SUPPORT_AGENT,
        UserRole.SENIOR_AGENT,
        UserRole.ADMIN
    ],
    IntentType.EXTERNAL_API_SEARCH: [
        UserRole.SUPPORT_AGENT,
        UserRole.SENIOR_AGENT,
        UserRole.ADMIN
    ],
    IntentType.SENSITIVE_OPERATION: [
        UserRole.SENIOR_AGENT,
        UserRole.ADMIN
    ],
    IntentType.DATABASE_QUERY_OPERATION: [
        UserRole.ADMIN
    ],
    IntentType.OUT_OF_SCOPE: [
        UserRole.CUSTOMER,
        UserRole.SUPPORT_AGENT,
        UserRole.SENIOR_AGENT,
        UserRole.ADMIN
    ],
}


class IntentClassificationOutput(BaseModel):
    intent: IntentType = Field(
        ...,
        description="The classified intent of the user message"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score between 0.0 and 1.0"
    )
    reasoning: str = Field(
        ...,
        description="Brief concise justification for why this intent was selected"
    )
    extracted_entities: Optional[List[str]] = Field(
        default_factory=list,
        description="Optional list of key entities extracted from the query"
    )
