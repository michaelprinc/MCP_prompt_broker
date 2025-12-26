"""Lightweight prompt analysis for routing and auditing metadata."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, Mapping, MutableMapping, Tuple

from ..router.profile_router import EnhancedMetadata

# Base static keywords (always present)
_BASE_INTENT_KEYWORDS: Mapping[str, tuple[str, ...]] = {
    "bug_report": ("bug", "stack trace", "exception", "error", "crash"),
    "brainstorm": ("brainstorm", "ideas", "ideation", "imagine", "creative"),
    "diagnosis": ("investigate", "diagnose", "root cause", "analysis"),
    "review": ("review", "feedback", "critique", "audit"),
    "question": ("how", "what", "why", "can you"),
    # Code generation intents
    "code_generation": (
        "create", "generate", "implement", "build", "develop", "write code",
        "codex cli", "codex", "použij codex", "vytvoř", "generuj", "implementuj",
        "make a script", "make a function", "make a class",
    ),
    # Testing and validation intents
    "testing": (
        "test", "testing", "validate", "validation", "verify", "verification",
        "check", "kontrola", "ověř", "zkontroluj", "funkčnost",
    ),
    # Debugging intents
    "debugging": (
        "debug", "troubleshoot", "fix", "resolve", "oprav", "problém",
    ),
}

_BASE_DOMAIN_KEYWORDS: Mapping[str, tuple[str, ...]] = {
    "healthcare": ("patient", "medical", "clinic", "hospital"),
    "finance": ("payment", "invoice", "credit", "bank", "ssn", "tax"),
    "engineering": ("stack trace", "exception", "api", "deploy", "server", "debug"),
    "security": ("exploit", "payload", "vulnerability", "attack", "breach"),
    "legal": ("contract", "law", "regulation", "compliance"),
    "marketing": ("campaign", "launch", "ad copy", "audience"),
    # Data science and ML domains
    "data_science": (
        "model", "dataset", "classification", "regression", "clustering",
        "machine learning", "ml", "sklearn", "sci-kit learn", "scikit",
        "pandas", "numpy", "tensorflow", "pytorch", "keras",
        "klasifikac", "modelovací", "trénování", "predikce",
    ),
    # Python development domain
    "python": (
        "python", ".py", "pip", "venv", "pytest", "django", "flask", "fastapi",
    ),
    # Container and DevOps domain
    "containers": (
        "docker", "podman", "container", "kubernetes", "k8s", "helm",
    ),
    # Testing and QA domain
    "testing": (
        "mcp server", "prompt broker", "profile", "routing", "hot reload",
        "qa", "quality assurance", "unit test", "integration test",
    ),
}

_BASE_TOPIC_KEYWORDS: Mapping[str, tuple[str, ...]] = {
    "pii": ("ssn", "social security", "credit card", "personal data", "patient"),
    "compliance": ("hipaa", "gdpr", "pci", "regulation", "policy"),
    "storytelling": ("story", "narrative", "creative", "brainstorm"),
    "incident": ("outage", "downtime", "breach", "incident", "crash", "failure"),
    "security": ("exploit", "payload", "attack", "ransomware"),
    # Codex CLI and tool orchestration topics
    "codex_cli": (
        "codex cli", "codex", "použij codex", "tool orchestration",
        "cli tool", "external tool",
    ),
    # Machine learning topics
    "ml_modeling": (
        "modelovací úloha", "klasifikační", "classification", "regression",
        "dataset", "training", "prediction", "sklearn", "sci-kit learn",
        "iris", "mnist", "titanic", "feature engineering",
    ),
    # MCP server testing topics
    "mcp_testing": (
        "mcp server", "prompt broker", "hot reload", "metadata parser",
        "profile routing", "profile loading",
    ),
    # Container management topics
    "container_management": (
        "podman", "docker", "container", "image", "volume", "network",
    ),
}

# Dynamic keywords storage (populated from profiles during hot reload)
_dynamic_intent_keywords: Dict[str, Tuple[str, ...]] = {}
_dynamic_domain_keywords: Dict[str, Tuple[str, ...]] = {}
_dynamic_topic_keywords: Dict[str, Tuple[str, ...]] = {}


def _merge_keyword_dicts(
    base: Mapping[str, tuple[str, ...]],
    dynamic: Dict[str, Tuple[str, ...]],
) -> Dict[str, tuple[str, ...]]:
    """Merge base and dynamic keyword dictionaries, combining tuples for same keys."""
    result: Dict[str, tuple[str, ...]] = dict(base)
    for key, values in dynamic.items():
        if key in result:
            # Merge with existing, avoiding duplicates
            existing = set(result[key])
            existing.update(values)
            result[key] = tuple(sorted(existing))
        else:
            result[key] = values
    return result


def get_intent_keywords() -> Mapping[str, tuple[str, ...]]:
    """Get combined base and dynamic intent keywords."""
    return _merge_keyword_dicts(_BASE_INTENT_KEYWORDS, _dynamic_intent_keywords)


def get_domain_keywords() -> Mapping[str, tuple[str, ...]]:
    """Get combined base and dynamic domain keywords."""
    return _merge_keyword_dicts(_BASE_DOMAIN_KEYWORDS, _dynamic_domain_keywords)


def get_topic_keywords() -> Mapping[str, tuple[str, ...]]:
    """Get combined base and dynamic topic keywords."""
    return _merge_keyword_dicts(_BASE_TOPIC_KEYWORDS, _dynamic_topic_keywords)


def update_parser_keywords(
    intent_keywords: Dict[str, Tuple[str, ...]] | None = None,
    domain_keywords: Dict[str, Tuple[str, ...]] | None = None,
    topic_keywords: Dict[str, Tuple[str, ...]] | None = None,
) -> Dict[str, int]:
    """Update dynamic keywords from external source (e.g., profiles).
    
    Args:
        intent_keywords: New intent keywords to add/update
        domain_keywords: New domain keywords to add/update
        topic_keywords: New topic keywords to add/update
        
    Returns:
        Summary of updates made.
    """
    global _dynamic_intent_keywords, _dynamic_domain_keywords, _dynamic_topic_keywords
    
    counts = {"intent": 0, "domain": 0, "topic": 0}
    
    if intent_keywords:
        _dynamic_intent_keywords.update(intent_keywords)
        counts["intent"] = len(intent_keywords)
    
    if domain_keywords:
        _dynamic_domain_keywords.update(domain_keywords)
        counts["domain"] = len(domain_keywords)
    
    if topic_keywords:
        _dynamic_topic_keywords.update(topic_keywords)
        counts["topic"] = len(topic_keywords)
    
    return counts


def clear_dynamic_keywords() -> None:
    """Clear all dynamic keywords (for testing or reset)."""
    global _dynamic_intent_keywords, _dynamic_domain_keywords, _dynamic_topic_keywords
    _dynamic_intent_keywords.clear()
    _dynamic_domain_keywords.clear()
    _dynamic_topic_keywords.clear()


def get_parser_stats() -> Dict[str, int]:
    """Get statistics about current parser keywords."""
    return {
        "base_intent_count": len(_BASE_INTENT_KEYWORDS),
        "base_domain_count": len(_BASE_DOMAIN_KEYWORDS),
        "base_topic_count": len(_BASE_TOPIC_KEYWORDS),
        "dynamic_intent_count": len(_dynamic_intent_keywords),
        "dynamic_domain_count": len(_dynamic_domain_keywords),
        "dynamic_topic_count": len(_dynamic_topic_keywords),
        "total_intent_count": len(get_intent_keywords()),
        "total_domain_count": len(get_domain_keywords()),
        "total_topic_count": len(get_topic_keywords()),
    }


# Legacy aliases for backward compatibility
INTENT_KEYWORDS = _BASE_INTENT_KEYWORDS
DOMAIN_KEYWORDS = _BASE_DOMAIN_KEYWORDS
TOPIC_KEYWORDS = _BASE_TOPIC_KEYWORDS

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
    for intent, keywords in get_intent_keywords().items():
        if any(keyword in normalized for keyword in keywords):
            return intent

    if "?" in normalized:
        return "question"

    return "statement"


def _detect_domain(normalized: str) -> str | None:
    best_domain: str | None = None
    best_score = 0
    for domain, keywords in get_domain_keywords().items():
        score = sum(1 for keyword in keywords if keyword in normalized)
        if score > best_score:
            best_domain = domain
            best_score = score
    return best_domain


def _collect_topics(normalized: str) -> set[str]:
    topics: set[str] = set()
    for topic, keywords in get_topic_keywords().items():
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
