import re
from typing import Tuple, Dict, Any
from app.core.logging import logger


class GuardrailsService:
    """
    Enterprise AI Security & Compliance Guardrails (Phase 8):
    - PII Redaction: Credit cards (with Luhn validation), emails, phones, API secrets, National IDs.
    - Prompt Injection Defense: Interception of jailbreak attempts and system prompt override attacks.
    """

    # 1. PII Patterns
    EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b")
    PHONE_REGEX = re.compile(
        r"(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{2,4}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{3,4}\b"
    )
    SECRET_TOKEN_REGEX = re.compile(
        r"\b(?:sk-[a-zA-Z0-9_\-]{20,}|tvly-[a-zA-Z0-9_\-]{20,}|Bearer\s+[a-zA-Z0-9_\.\-]{20,})\b"
    )
    PASSWORD_KV_REGEX = re.compile(
        r"(?i)\b(password|passwd|secret|api_key|token)\s*[:=]\s*([^\s,;]+)"
    )
    SSN_ID_REGEX = re.compile(
        r"\b(?:\d{3}-\d{2}-\d{4}|[23]\d{13})\b"
    )
    CREDIT_CARD_CANDIDATE_REGEX = re.compile(r"\b(?:\d[ -]*?){13,19}\b")

    # 2. Prompt Injection & Jailbreak Signatures
    INJECTION_PATTERNS = [
        # English Signatures
        re.compile(r"(?i)\bignore\s+(?:all\s+)?(?:previous|prior|above)\s+(?:instructions|rules|directions|prompts)\b"),
        re.compile(r"(?i)\b(?:system\s+override|override\s+system|developer\s+mode\s+enabled)\b"),
        re.compile(r"(?i)\b(?:do\s+anything\s+now|dan\s+mode|jailbreak)\b"),
        re.compile(r"(?i)\b(?:reveal|print|dump|show|output|leak)\s+(?:your\s+)?(?:system\s+prompt|initial\s+prompt|instructions)\b"),
        re.compile(r"(?i)\byou\s+are\s+now\s+(?:unrestricted|free|without\s+rules|an\s+unfiltered\s+ai)\b"),
        re.compile(r"(?i)\bdisregard\s+(?:all\s+)?safety\s+(?:guidelines|rules|filters)\b"),
        
        # Arabic Signatures
        re.compile(r"تجاهل\s+(?:كل\s+)?التعليمات\s+السابقة"),
        re.compile(r"اكشف\s+(?:عن\s+)?البرومبت\s+(?:الأساسي|الأصلي|الخاص\s+بك)"),
        re.compile(r"أنت\s+الآن\s+(?:حر|بدون\s+قيود|تتصرف\s+بلا\s+قواعد)"),
        re.compile(r"تخطي\s+(?:كل\s+)?قواعد\s+الأمان")
    ]

    @staticmethod
    def _is_luhn_valid(card_number_str: str) -> bool:
        """Validates potential credit card numbers using Luhn checksum algorithm."""
        digits = [int(c) for c in card_number_str if c.isdigit()]
        if len(digits) < 13 or len(digits) > 19:
            return False
        
        checksum = 0
        reverse_digits = digits[::-1]
        for i, digit in enumerate(reverse_digits):
            if i % 2 == 1:
                doubled = digit * 2
                checksum += (doubled - 9) if doubled > 9 else doubled
            else:
                checksum += digit
        return checksum % 10 == 0

    def mask_pii(self, text: str) -> Tuple[str, Dict[str, int]]:
        """
        Scans and redacts sensitive PII from text before it reaches LLMs or external search APIs.
        Returns:
            sanitized_text: String with PII replaced by [REDACTED_...]
            redaction_counts: Breakdown of redacted entities
        """
        counts = {
            "credit_cards": 0,
            "emails": 0,
            "phones": 0,
            "secrets": 0,
            "national_ids": 0
        }
        sanitized = text

        # 1. Redact Secrets & API Keys
        def _replace_secret(match):
            counts["secrets"] += 1
            return "[REDACTED_SECRET]"
        sanitized = self.SECRET_TOKEN_REGEX.sub(_replace_secret, sanitized)

        def _replace_kv(match):
            counts["secrets"] += 1
            return f"{match.group(1)}=[REDACTED_SECRET]"
        sanitized = self.PASSWORD_KV_REGEX.sub(_replace_kv, sanitized)

        # 2. Redact Emails
        def _replace_email(match):
            counts["emails"] += 1
            return "[REDACTED_EMAIL]"
        sanitized = self.EMAIL_REGEX.sub(_replace_email, sanitized)

        # 3. Redact Credit Cards (strictly Luhn-validated)
        for match in self.CREDIT_CARD_CANDIDATE_REGEX.finditer(sanitized):
            candidate = match.group(0)
            digits_only = re.sub(r"\D", "", candidate)
            if self._is_luhn_valid(digits_only):
                sanitized = sanitized.replace(candidate, "[REDACTED_CREDIT_CARD]")
                counts["credit_cards"] += 1

        # 4. Redact SSN / National IDs
        def _replace_id(match):
            counts["national_ids"] += 1
            return "[REDACTED_ID]"
        sanitized = self.SSN_ID_REGEX.sub(_replace_id, sanitized)

        # 5. Redact Phone Numbers (min 7 digits to avoid matching short IDs)
        for match in self.PHONE_REGEX.finditer(sanitized):
            candidate = match.group(0)
            digits_only = re.sub(r"\D", "", candidate)
            if 7 <= len(digits_only) <= 15 and not candidate.startswith("[REDACTED"):
                sanitized = sanitized.replace(candidate, "[REDACTED_PHONE]")
                counts["phones"] += 1

        total_redacted = sum(counts.values())
        if total_redacted > 0:
            logger.info(f"[Guardrails: PII] Redacted {total_redacted} sensitive items: {counts}")

        return sanitized, counts

    def detect_prompt_injection(self, text: str) -> Tuple[bool, str]:
        """
        Inspects text for prompt injection, jailbreaks, or system override attempts.
        Returns:
            is_injection: True if violation detected
            reason: Description of the detected signature
        """
        for pattern in self.INJECTION_PATTERNS:
            match = pattern.search(text)
            if match:
                signature = match.group(0)
                reason = f"Prohibited prompt override pattern detected: '{signature}'"
                logger.warning(f"[Guardrails: Security] Blocked injection attempt: {reason}")
                return True, reason

        return False, ""


# Singleton instance
guardrails_service = GuardrailsService()
