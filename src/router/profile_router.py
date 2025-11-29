"""Router for mapping enhanced prompt metadata to instruction profiles."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping, MutableMapping, Sequence

from config.profiles import InstructionProfile, get_instruction_profiles


@dataclass(frozen=True)
class EnhancedMetadata:
    """Normalized metadata used to select instruction profiles."""

    prompt: str
    domain: str | None = None
    sensitivity: str | None = None
    language: str | None = None
    priority: str | None = None
    audience: str | None = None
    intent: str | None = None
    context_tags: frozenset[str] = field(default_factory=frozenset)

    @classmethod
    def from_dict(cls, metadata: Mapping[str, object]) -> "EnhancedMetadata":
        """Create :class:`EnhancedMetadata` from a raw mapping."""

        context_tags = metadata.get("context_tags") or []
        if not isinstance(context_tags, Iterable) or isinstance(context_tags, str):
            context_tags = [context_tags]

        return cls(
            prompt=str(metadata.get("prompt", "")),
            domain=metadata.get("domain"),
            sensitivity=metadata.get("sensitivity"),
            language=metadata.get("language"),
            priority=metadata.get("priority"),
            audience=metadata.get("audience"),
            intent=metadata.get("intent"),
            context_tags=frozenset(tag for tag in context_tags if tag),
        )

    def as_mutable(self) -> MutableMapping[str, object]:
        """Return the metadata as a mutable mapping for scoring."""

        return {
            "prompt": self.prompt,
            "domain": self.domain,
            "sensitivity": self.sensitivity,
            "language": self.language,
            "priority": self.priority,
            "audience": self.audience,
            "intent": self.intent,
            "context_tags": set(self.context_tags),
        }


class ProfileRouter:
    """Route prompts to instruction profiles using rule-based scoring."""

    def __init__(self, profiles: Sequence[InstructionProfile] | None = None):
        self.profiles = list(profiles or get_instruction_profiles())

    def route(self, metadata: EnhancedMetadata) -> InstructionProfile:
        """Return the best instruction profile for the given metadata."""

        metadata_map = metadata.as_mutable()
        best_profile: InstructionProfile | None = None
        best_score: int | None = None
        fallback_profile: InstructionProfile | None = None

        for profile in self.profiles:
            if profile.fallback:
                fallback_profile = fallback_profile or profile

            if not profile.is_match(metadata_map):
                continue

            score = profile.score(metadata_map)
            if best_score is None or score > best_score:
                best_score = score
                best_profile = profile

        if best_profile:
            return best_profile

        if fallback_profile:
            return fallback_profile

        raise ValueError("No matching profile and no fallback configured")
