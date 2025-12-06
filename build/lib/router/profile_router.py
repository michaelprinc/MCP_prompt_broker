"""Router for mapping enhanced prompt metadata to instruction profiles."""
from __future__ import annotations

import math
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


@dataclass(frozen=True)
class RoutingResult:
    """Result of routing including the matched profile and confidence."""

    profile: InstructionProfile
    score: int
    consistency: float


class ProfileRouter:
    """Route prompts to instruction profiles using rule-based scoring."""

    def __init__(self, profiles: Sequence[InstructionProfile] | None = None):
        self.profiles = list(profiles or get_instruction_profiles())

    def _normalize_consistency(self, best_score: int, candidate_scores: Sequence[int]) -> float:
        """Normalize consistency to a 0-100 scale using a softmax-style weighting."""

        if not candidate_scores:
            return 100.0

        max_score = max(candidate_scores)
        exp_scores = [math.exp(score - max_score) for score in candidate_scores]
        best_weight = math.exp(best_score - max_score)
        probability = best_weight / sum(exp_scores)
        return round(probability * 100, 2)

    def route(self, metadata: EnhancedMetadata) -> RoutingResult:
        """Return the best instruction profile for the given metadata."""

        metadata_map = metadata.as_mutable()
        scored_matches: list[tuple[InstructionProfile, int]] = []
        fallback_profile: InstructionProfile | None = None

        for profile in self.profiles:
            if profile.fallback:
                fallback_profile = fallback_profile or profile

            if not profile.is_match(metadata_map):
                continue

            scored_matches.append((profile, profile.score(metadata_map)))

        if scored_matches:
            best_profile, best_score = max(scored_matches, key=lambda item: item[1])
            consistency = self._normalize_consistency(
                best_score, [score for _, score in scored_matches]
            )
            return RoutingResult(best_profile, best_score, consistency)

        if fallback_profile:
            return RoutingResult(fallback_profile, fallback_profile.default_score, 100.0)

        raise ValueError("No matching profile and no fallback configured")
