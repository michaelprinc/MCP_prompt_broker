from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class PromptMetadata:
    intent: str
    domain_tags: List[str] = field(default_factory=list)
    safety_score: float = 0.0
    sensitivity_score: float = 0.0
    tone: str = "neutral"
    complexity: str = "medium"


class PromptMetadataParser:
    """Heuristic parser to derive structured metadata from a prompt string."""

    INTENT_KEYWORDS = {
        "question": ["?", "who", "what", "when", "where", "why", "how do", "how does", "impact"],
        "instruction": ["please", "guide", "steps", "need", "create", "build", "write", "explain how"],
        "code": ["python", "code", "script", "function", "program"],
        "story": ["story", "narrative", "novel", "plot"],
        "analysis": ["analyze", "analysis", "summarize", "impact"],
    }

    DOMAIN_KEYWORDS = {
        "programming": ["python", "code", "script", "function", "api", "debug", "algorithm"],
        "finance": ["stock", "investment", "mortgage", "loan", "interest", "payments", "budget"],
        "health": ["medical", "doctor", "diagnosed", "hypertension", "diet", "health"],
        "legal": ["law", "legal", "contract", "compliance", "regulation"],
        "customer_support": ["customer", "support", "refund", "ticket", "outage"],
        "security": ["password", "credential", "encryption", "breach"],
    }

    SAFETY_RISK = {
        "explosive": 0.95,
        "weapon": 0.8,
        "kill": 0.9,
        "harm": 0.75,
        "suicide": 0.95,
        "self-harm": 0.95,
        "bomb": 0.95,
    }

    SENSITIVITY_RISK = {
        "doctor": 0.6,
        "diagnosed": 0.7,
        "medical": 0.7,
        "hypertension": 0.8,
        "social security": 0.9,
        "ssn": 0.9,
        "password": 0.8,
        "credit card": 0.8,
    }

    @classmethod
    def analyze(cls, prompt: str) -> PromptMetadata:
        normalized = prompt.lower()
        intent = cls._detect_intent(normalized)
        domain_tags = cls._detect_domains(normalized)
        safety_score = cls._score_safety(normalized)
        sensitivity_score = cls._score_sensitivity(normalized)
        tone = cls._detect_tone(normalized)
        complexity = cls._estimate_complexity(prompt)

        return PromptMetadata(
            intent=intent,
            domain_tags=domain_tags,
            safety_score=round(safety_score, 2),
            sensitivity_score=round(sensitivity_score, 2),
            tone=tone,
            complexity=complexity,
        )

    @classmethod
    def _detect_intent(cls, normalized: str) -> str:
        for intent, keywords in cls.INTENT_KEYWORDS.items():
            if any(keyword in normalized for keyword in keywords):
                return intent
        if normalized.strip().endswith("?"):
            return "question"
        return "chat"

    @classmethod
    def _detect_domains(cls, normalized: str) -> List[str]:
        tags = []
        for tag, keywords in cls.DOMAIN_KEYWORDS.items():
            if any(keyword in normalized for keyword in keywords):
                tags.append(tag)
        return sorted(set(tags))

    @classmethod
    def _score_safety(cls, normalized: str) -> float:
        score = 0.2
        for keyword, risk in cls.SAFETY_RISK.items():
            if keyword in normalized:
                score = max(score, risk)
        return min(score, 1.0)

    @classmethod
    def _score_sensitivity(cls, normalized: str) -> float:
        score = 0.1
        for keyword, risk in cls.SENSITIVITY_RISK.items():
            if keyword in normalized:
                score = max(score, risk)
        return min(score, 1.0)

    @classmethod
    def _detect_tone(cls, normalized: str) -> str:
        if any(marker in normalized for marker in ["urgent", "immediately", "asap", "emergency"]):
            return "urgent"
        if any(marker in normalized for marker in ["please", "could you", "would you", "thank you"]):
            return "friendly"
        if any(marker in normalized for marker in ["dear", "sincerely", "regards"]):
            return "formal"
        return "neutral"

    @classmethod
    def _estimate_complexity(cls, prompt: str) -> str:
        word_count = len(prompt.split())
        if word_count < 8:
            return "low"
        if word_count <= 30:
            return "medium"
        return "high"


def analyze_prompt(prompt: str) -> PromptMetadata:
    """Convenience wrapper around ``PromptMetadataParser.analyze``."""

    return PromptMetadataParser.analyze(prompt)
