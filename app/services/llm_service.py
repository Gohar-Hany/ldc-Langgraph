import re
from typing import Optional
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.core.logging import logger
from app.schemas.intent_schema import IntentClassificationOutput, IntentType


class LLMService:
    def __init__(self):
        self._llm: Optional[ChatOpenAI] = None
        self._structured_classifier = None
        self._initialize_llm()

    def _initialize_llm(self) -> None:
        provider = settings.LLM_PROVIDER.lower()
        logger.info(f"Initializing LLM Service with primary provider: '{provider}'")

        if provider == "aurai":
            key = settings.AURAI_API_KEY.strip() if settings.AURAI_API_KEY else ""
            if key and not key.startswith("api_gAAAAAB_your_aurai"):
                try:
                    self._llm = ChatOpenAI(
                        model=settings.AURAI_MODEL,
                        api_key=key,
                        base_url=settings.AURAI_BASE_URL,
                        temperature=settings.AURAI_TEMPERATURE,
                        max_tokens=settings.AURAI_MAX_TOKENS,
                        model_kwargs={"top_p": settings.AURAI_TOP_P},
                        timeout=settings.LLM_REQUEST_TIMEOUT
                    )
                    self._structured_classifier = self._llm.with_structured_output(
                        IntentClassificationOutput
                    )
                    logger.info(
                        f"Aurai ChatOpenAI client initialized (Model: {settings.AURAI_MODEL}, "
                        f"Endpoint: {settings.AURAI_BASE_URL}, temp: {settings.AURAI_TEMPERATURE}, "
                        f"top_p: {settings.AURAI_TOP_P})"
                    )
                    return
                except Exception as e:
                    logger.warning(f"Failed to initialize Aurai client: {e}")
            else:
                logger.info("Aurai API key is empty or placeholder.")

        # Fallback / Secondary provider: OpenRouter
        openrouter_key = settings.OPENROUTER_API_KEY.strip() if settings.OPENROUTER_API_KEY else ""
        if openrouter_key and openrouter_key.startswith("sk-or-v1-") and not ("your-openrouter" in openrouter_key):
            try:
                self._llm = ChatOpenAI(
                    model=settings.OPENROUTER_MODEL,
                    api_key=openrouter_key,
                    base_url=settings.OPENROUTER_BASE_URL,
                    temperature=0.0,
                    timeout=settings.LLM_REQUEST_TIMEOUT
                )
                self._structured_classifier = self._llm.with_structured_output(
                    IntentClassificationOutput
                )
                logger.info(f"OpenRouter client initialized (Model: {settings.OPENROUTER_MODEL})")
                return
            except Exception as e:
                logger.warning(f"Failed to initialize OpenRouter client: {e}")

        logger.info("No active remote LLM client initialized. Using deterministic rule-based classifier.")

    @property
    def client(self) -> Optional[ChatOpenAI]:
        """Returns the active ChatOpenAI client instance."""
        return self._llm

    def get_chat_model(self) -> Optional[ChatOpenAI]:
        """Returns the active ChatOpenAI model instance."""
        return self._llm

    def get_structured_classifier(self):
        return self._structured_classifier

    def call_structured(self, schema_cls, prompt: str, system_message: str = ""):
        """Invokes the active LLM with structured output using schema_cls."""
        if not self._llm:
            raise RuntimeError("No active LLM initialized for structured call.")
        
        from langchain_core.messages import SystemMessage, HumanMessage
        structured_llm = self._llm.with_structured_output(schema_cls)
        messages = []
        if system_message:
            messages.append(SystemMessage(content=system_message))
        messages.append(HumanMessage(content=prompt))
        return structured_llm.invoke(messages)


    def classify_intent_fallback(self, text: str) -> IntentClassificationOutput:
        """
        Deterministic intent classifier with bilingual (English/Arabic) keyword recognition.
        """
        text_lower = text.lower().strip()

        # 1. Database Operations (Admin only)
        if any(w in text_lower for w in ["database", "sql", "drop table", "select *", "db query", "schema", "postgres", "mysql", "قاعدة البيانات"]):
            return IntentClassificationOutput(
                intent=IntentType.DATABASE_QUERY_OPERATION,
                confidence=0.95,
                reasoning="Message requests direct database queries, SQL operations, or schema inspection."
            )

        # 2. Sensitive Operations (Senior Agent / Admin)
        if any(w in text_lower for w in [
            "refund", "double-billed", "billing", "invoice", "charge", "wipe vps", 
            "wipe", "delete server", "terminate server", "deprovision", "reset password", 
            "elevate permission", "superuser", "reboot server", "grant admin", "unlock account", 
            "صلاحيات", "اعادة تعيين", "استرداد", "استرجاع", "فاتورة", "حذف سيرفر"
        ]):
            return IntentClassificationOutput(
                intent=IntentType.SENSITIVE_OPERATION,
                confidence=0.96,
                reasoning="Message involves sensitive operational actions requiring elevated privileges."
            )

        # 3. External API Search (Support Agent+)
        if any(w in text_lower for w in ["external api", "vendor api", "stripe", "github api", "third party", "vendor", "api documentation", "api status", "اي بي اي"]):
            return IntentClassificationOutput(
                intent=IntentType.EXTERNAL_API_SEARCH,
                confidence=0.90,
                reasoning="Message asks to search or query external vendor APIs and status endpoints."
            )

        # 4. Ticket Create / Update (Support Agent+)
        if ("ticket" in text_lower or "تذكرة" in text_lower) and any(w in text_lower for w in ["create", "new", "update", "priority", "close", "assign", "انشاء", "تعديل", "فتح"]):
            return IntentClassificationOutput(
                intent=IntentType.TICKET_CREATE_UPDATE,
                confidence=0.94,
                reasoning="Message requests creating, updating, or re-prioritizing a support ticket."
            )

        # 5. My Tickets Search (Customer+)
        if ("ticket" in text_lower or "tickets" in text_lower or "تذاكر" in text_lower or "تذكرتي" in text_lower or "تذاكري" in text_lower) and any(w in text_lower for w in ["my", "status", "open", "check", "show", "list", "حالة", "استعراض", "مفتوحة"]):
            return IntentClassificationOutput(
                intent=IntentType.MY_TICKETS_SEARCH,
                confidence=0.94,
                reasoning="Message asks to view or check status of user's own tickets."
            )

        # 6. Knowledge Search / RAG (Customer+)
        if any(w in text_lower for w in [
            "how to", "vpn", "wifi", "wi-fi", "wireless", "policy", "documentation", 
            "guide", "setup", "configure", "requirements", "password", "mfa", 
            "hardware", "license", "licensing", "procurement", "cairo", "datacenter", 
            "colocation", "sla", "uptime", "tier-iii", "tier 3", "power", "cooling", 
            "generator", "peering", "bgp", "bandwidth", "redundancy", "specs", "specification",
            "كيفية", "وثائق", "دليل", "واي فاي", "سياسة", "مركز البيانات", "كوليكيشن"
        ]):
            return IntentClassificationOutput(
                intent=IntentType.KNOWLEDGE_SEARCH,
                confidence=0.92,
                reasoning="Message requests technical support guidelines or knowledge base documentation."
            )


        # 7. Greetings (Exact word boundary matching with Arabic support)
        greeting_patterns = [r"\bhello\b", r"\bhi\b", r"\bhey\b", r"\bgood morning\b", r"\bgood evening\b", r"\bgreetings\b", r"مرحبا", r"اهلا", r"السلام عليكم"]
        if any(re.search(pat, text_lower) for pat in greeting_patterns):
            return IntentClassificationOutput(
                intent=IntentType.GREETING,
                confidence=0.96,
                reasoning="Message contains standard greeting phrases."
            )

        # 8. Out of Scope
        return IntentClassificationOutput(
            intent=IntentType.OUT_OF_SCOPE,
            confidence=0.70,
            reasoning="Query does not match any recognized IT support workflows."
        )


llm_service = LLMService()
