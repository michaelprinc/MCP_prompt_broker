"""Lightweight prompt analysis for routing and auditing metadata."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping, MutableMapping

from ..router.profile_router import EnhancedMetadata

INTENT_KEYWORDS: Mapping[str, tuple[str, ...]] = {
    "bug_report": ("bug", "stack trace", "exception", "error", "crash"),
    "brainstorm": ("brainstorm", "ideas", "ideation", "imagine", "creative"),
    "diagnosis": ("investigate", "diagnose", "root cause", "analysis"),
    "review": ("review", "feedback", "critique", "audit"),
    "question": ("how", "what", "why", "can you"),
}

DOMAIN_KEYWORDS: Mapping[str, tuple[str, ...]] = {
    "healthcare": ("patient", "medical", "clinic", "hospital"),
    "finance": ("payment", "invoice", "credit", "bank", "ssn", "tax"),
    "engineering": ("stack trace", "exception", "api", "deploy", "server", "debug"),
    "security": ("exploit", "payload", "vulnerability", "attack", "breach"),
    "legal": ("contract", "law", "regulation", "compliance"),
    "marketing": ("campaign", "launch", "ad copy", "audience"),
}

TOPIC_KEYWORDS: Mapping[str, tuple[str, ...]] = {
    "pii": ("ssn", "social security", "credit card", "personal data", "patient"),
    "compliance": ("hipaa", "gdpr", "pci", "regulation", "policy"),
    "storytelling": ("story", "narrative", "creative", "brainstorm"),
    "incident": ("outage", "downtime", "breach", "incident", "crash", "failure"),
    "security": ("exploit", "payload", "attack", "ransomware"),
}

SENSITIVE_PHRASES: Mapping[str, int] = {
    "ssn": 5,
    "social security": 5,
    "credit card": 4,
    "patient": 3,
    "password": 3,
    "secret": 3,
    "exploit": 3,
    "payload": 3,
    "breach": 3,
    "private": 2,
    "confidential": 2,
}

TONE_KEYWORDS: Mapping[str, str] = {
    "urgent": "urgent",
    "asap": "urgent",
    "immediately": "urgent",
    "please": "polite",
    "thanks": "polite",
    "thank you": "polite",
    "frustrated": "frustrated",
    "annoyed": "frustrated",
}


@dataclass(frozen=True)
class ParsedMetadata:
    """Represents enriched metadata derived from the raw prompt."""

    prompt: str
    intent: str
    domain: str | None
    topics: frozenset[str] = field(default_factory=frozenset)
    sensitivity: str = "low"
    safety_score: int = 0
    tone: str = "neutral"
    complexity: str = "low"

    def to_enhanced_metadata(self, overrides: Mapping[str, object] | None = None) -> EnhancedMetadata:
        """Convert the parsed metadata to :class:`EnhancedMetadata` with overrides."""

        metadata: MutableMapping[str, object] = {
            "prompt": self.prompt,
            "domain": self.domain,
            "sensitivity": self.sensitivity,
            "intent": self.intent,
            "context_tags": set(self.topics),
        }

        if overrides:
            for key, value in overrides.items():
                if value is None:
                    continue
                if key == "context_tags":
                    existing = metadata.setdefault("context_tags", set())
                    if isinstance(existing, Iterable):
                        if isinstance(value, str):
                            value = [value]
                        existing = set(existing)
                        existing.update(value if isinstance(value, Iterable) and not isinstance(value, str) else [value])
                        metadata["context_tags"] = existing
                else:
                    metadata[key] = value

        return EnhancedMetadata.from_dict(metadata)

    def as_dict(self) -> Mapping[str, object]:
        """Return a JSON-safe representation of the parsed metadata."""

        return {
            "prompt": self.prompt,
            "intent": self.intent,
            "domain": self.domain,
            "topics": sorted(self.topics),
            "sensitivity": self.sensitivity,
            "safety_score": self.safety_score,
            "tone": self.tone,
            "complexity": self.complexity,
        }


def _classify_intent(normalized: str) -> str:
    for intent, keywords in INTENT_KEYWORDS.items():
        if any(keyword in normalized for keyword in keywords):
            return intent

    if "?" in normalized:
        return "question"

    return "statement"


def _detect_domain(normalized: str) -> str | None:
    best_domain: str | None = None
    best_score = 0
    for domain, keywords in DOMAIN_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in normalized)
        if score > best_score:
            best_domain = domain
            best_score = score
    return best_domain


def _collect_topics(normalized: str) -> set[str]:
    topics: set[str] = set()
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(keyword in normalized for keyword in keywords):
            topics.add(topic)
    return topics


def _score_safety(normalized: str) -> tuple[int, str]:
    score = 0
    for phrase, weight in SENSITIVE_PHRASES.items():
        if phrase in normalized:
            score += weight

    # cap for stability
    score = min(score, 10)

    if score >= 8:
        sensitivity = "critical"
    elif score >= 6:
        sensitivity = "high"
    elif score >= 3:
        sensitivity = "medium"
    else:
        sensitivity = "low"

    return score, sensitivity


def _detect_tone(normalized: str) -> str:
    for keyword, tone in TONE_KEYWORDS.items():
        if keyword in normalized:
            return tone
    if "!" in normalized:
        return "urgent"
    return "neutral"


def _estimate_complexity(prompt: str) -> str:
    word_count = len(prompt.split())
    if word_count > 80:
        return "high"
    if word_count > 40:
        return "medium"
    if word_count > 15:
        return "low-medium"
    return "low"


def analyze_prompt(prompt: str) -> ParsedMetadata:
    """Analyze prompt text and derive routing metadata."""

    if not prompt or not prompt.strip():
        raise ValueError("Prompt must not be empty")

    normalized = prompt.lower()
    intent = _classify_intent(normalized)
    domain = _detect_domain(normalized)
    topics = _collect_topics(normalized)
    safety_score, sensitivity = _score_safety(normalized)
    tone = _detect_tone(normalized)
    complexity = _estimate_complexity(prompt)

    return ParsedMetadata(
        prompt=prompt.strip(),
        intent=intent,
        domain=domain,
        topics=frozenset(topics),
        sensitivity=sensitivity,
        safety_score=safety_score,
        tone=tone,
        complexity=complexity,
    )
