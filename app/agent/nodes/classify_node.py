from typing import Any, Dict
from datetime import datetime, timezone
from langchain_core.messages import SystemMessage, HumanMessage

from app.agent.state import AgentState
from app.agent.prompts.classifier_prompt import CLASSIFIER_SYSTEM_PROMPT
from app.core.logging import logger
from app.services.llm_service import llm_service
from app.schemas.intent_schema import IntentClassificationOutput, IntentType


def classify_intent_node(state: AgentState) -> Dict[str, Any]:
    """
    Executes structured intent classification using OpenRouter ChatOpenAI or fallback rules.
    """
    message = state.get("raw_message", "")
    trace = state.get("execution_trace", []) or []
    
    structured_classifier = llm_service.get_structured_classifier()
    classification_result: IntentClassificationOutput
    
    if structured_classifier:
        try:
            logger.info("[ClassifyNode] Executing LLM-based structured output classification...")
            messages = [
                SystemMessage(content=CLASSIFIER_SYSTEM_PROMPT),
                HumanMessage(content=message)
            ]
            classification_result = structured_classifier.invoke(messages)
            logger.info(f"[ClassifyNode] LLM classification success: {classification_result.intent} (conf: {classification_result.confidence})")
        except Exception as e:
            logger.warning(f"[ClassifyNode] LLM invocation failed ({e}), falling back to deterministic classifier.")
            classification_result = llm_service.classify_intent_fallback(message)
    else:
        logger.info("[ClassifyNode] Using deterministic fallback classifier.")
        classification_result = llm_service.classify_intent_fallback(message)

    trace.append({
        "step_name": "intent_classification",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "success",
        "details": {
            "intent": classification_result.intent.value,
            "confidence": classification_result.confidence,
            "reasoning": classification_result.reasoning,
            "entities": classification_result.extracted_entities
        }
    })

    return {
        "intent": classification_result.intent,
        "confidence": classification_result.confidence,
        "reasoning": classification_result.reasoning,
        "extracted_entities": classification_result.extracted_entities,
        "execution_trace": trace
    }
