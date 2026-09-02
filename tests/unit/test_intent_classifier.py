import pytest
from app.services.llm_service import llm_service
from app.schemas.intent_schema import IntentType


@pytest.mark.parametrize(
    "query,expected_intent",
    [
        ("Hello, good morning!", IntentType.GREETING),
        ("Hi there, how are you?", IntentType.GREETING),
        ("Greetings team", IntentType.GREETING),
        ("مرحبا، السلام عليكم", IntentType.GREETING),
        ("How to configure corporate VPN on MacOS?", IntentType.KNOWLEDGE_SEARCH),
        ("What is the company WiFi password policy?", IntentType.KNOWLEDGE_SEARCH),
        ("Check my ticket status #1042", IntentType.MY_TICKETS_SEARCH),
        ("Show me my open support tickets", IntentType.MY_TICKETS_SEARCH),
        ("Create a new support ticket for email outage", IntentType.TICKET_CREATE_UPDATE),
        ("Update ticket #44 priority to high", IntentType.TICKET_CREATE_UPDATE),
        ("Query external API for Stripe payment status", IntentType.EXTERNAL_API_SEARCH),
        ("Check third party vendor API documentation", IntentType.EXTERNAL_API_SEARCH),
        ("Reset password for user John", IntentType.SENSITIVE_OPERATION),
        ("Elevate permissions for my account to superuser", IntentType.SENSITIVE_OPERATION),
        ("Reboot server staging-01", IntentType.SENSITIVE_OPERATION),
        ("Run SQL database query on users table", IntentType.DATABASE_QUERY_OPERATION),
        ("Drop table logs in production database", IntentType.DATABASE_QUERY_OPERATION),
        ("What is the weather in Tokyo?", IntentType.OUT_OF_SCOPE),
    ]
)
def test_all_7_plus_intents_classification(query: str, expected_intent: IntentType):
    result = llm_service.classify_intent_fallback(query)
    assert result.intent == expected_intent
    assert result.confidence >= 0.70
    assert result.reasoning is not None
