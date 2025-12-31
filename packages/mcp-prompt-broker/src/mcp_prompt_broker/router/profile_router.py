"""Router for mapping enhanced prompt metadata to instruction profiles."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Iterable, Mapping, MutableMapping, Sequence

from ..config.profiles import InstructionProfile, get_instruction_profiles


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
    complexity: str | None = None  # Complexity level: low, low-medium, medium, high
    prompt_length: int = 0  # Word count of the prompt

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
            complexity=metadata.get("complexity"),
            prompt_length=int(metadata.get("prompt_length", 0)),
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
            "complexity": self.complexity,
            "prompt_length": self.prompt_length,
        }


@dataclass(frozen=True)
class RoutingResult:
    """Result of routing including the matched profile and confidence."""

    profile: InstructionProfile
    score: int
    consistency: float
    complexity_adjusted: bool = False  # Whether profile was switched due to complexity
    original_profile_name: str | None = None  # Original profile before complexity adjustment


# Import complexity configuration
from .complexity_config import (
    COMPLEXITY_ROUTING_ENABLED,
    COMPLEX_SUFFIX,
    WORD_COUNT_PREFER_COMPLEX_THRESHOLD,
    COMPLEX_VARIANT_MIN_SCORE_RATIO,
    SIMPLE_VARIANT_MIN_SCORE_RATIO,
    COMPLEX_PREFERENCE_LEVELS,
    SIMPLE_PREFERENCE_LEVELS,
    SIMPLE_PREFERENCE_MAX_WORDS,
)


class ProfileRouter:
    """Route prompts to instruction profiles using rule-based scoring."""

    def __init__(self, profiles: Sequence[InstructionProfile] | None = None):
        self.profiles = list(profiles or get_instruction_profiles())
        self._profile_pairs = self._build_profile_pairs()

    def _build_profile_pairs(self) -> dict[str, str]:
        """Build mapping of base profiles to their _complex variants.
        
        Returns:
            Dict mapping base profile names to their _complex variant names.
        """
        pairs: dict[str, str] = {}
        profile_names = {p.name for p in self.profiles}
        
        for name in profile_names:
            if name.endswith(COMPLEX_SUFFIX):
                continue
            complex_name = f"{name}{COMPLEX_SUFFIX}"
            if complex_name in profile_names:
                pairs[name] = complex_name
        
        return pairs

    def _find_complex_variant(self, profile_name: str) -> InstructionProfile | None:
        """Find the _complex variant of a profile if it exists.
        
        Args:
            profile_name: Name of the base profile.
            
        Returns:
            The _complex variant profile, or None if not found.
        """
        if profile_name.endswith(COMPLEX_SUFFIX):
            return None
        
        complex_name = self._profile_pairs.get(profile_name)
        if not complex_name:
            return None
        
        for profile in self.profiles:
            if profile.name == complex_name:
                return profile
        return None

    def _find_simple_variant(self, profile_name: str) -> InstructionProfile | None:
        """Find the base variant of a _complex profile.
        
        Args:
            profile_name: Name of a _complex profile.
            
        Returns:
            The base profile, or None if not found.
        """
        if not profile_name.endswith(COMPLEX_SUFFIX):
            return None
        
        base_name = profile_name[:-len(COMPLEX_SUFFIX)]
        for profile in self.profiles:
            if profile.name == base_name:
                return profile
        return None

    def _should_prefer_complex(self, metadata: EnhancedMetadata) -> bool:
        """Determine if _complex variant should be preferred based on prompt complexity.
        
        Args:
            metadata: Enhanced metadata from prompt analysis.
            
        Returns:
            True if _complex variant should be preferred.
        """
        if not COMPLEXITY_ROUTING_ENABLED:
            return False
        
        complexity = metadata.complexity
        prompt_length = metadata.prompt_length
        
        # Explicit high/medium complexity detected
        if complexity in COMPLEX_PREFERENCE_LEVELS:
            return True
        
        # Long prompt without explicit complexity classification
        if prompt_length > WORD_COUNT_PREFER_COMPLEX_THRESHOLD:
            return True
        
        return False

    def _should_prefer_simple(self, metadata: EnhancedMetadata) -> bool:
        """Determine if base (non-complex) variant should be preferred.
        
        Args:
            metadata: Enhanced metadata from prompt analysis.
            
        Returns:
            True if base profile should be preferred over _complex.
        """
        if not COMPLEXITY_ROUTING_ENABLED:
            return False
        
        complexity = metadata.complexity
        prompt_length = metadata.prompt_length
        
        # Short prompt with low complexity
        if complexity in SIMPLE_PREFERENCE_LEVELS and prompt_length <= SIMPLE_PREFERENCE_MAX_WORDS:
            return True
        
        return False

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
        """Return the best instruction profile for the given metadata.
        
        This method scores all matching profiles and selects the best one.
        If complexity routing is enabled, it may switch to a _complex or base
        variant based on the prompt's complexity analysis.
        """

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
            original_name: str | None = None
            complexity_adjusted = False
            
            # === COMPLEXITY-BASED PROFILE ADJUSTMENT ===
            if COMPLEXITY_ROUTING_ENABLED:
                if self._should_prefer_complex(metadata):
                    # Prefer _complex variant for complex/long prompts
                    if not best_profile.name.endswith(COMPLEX_SUFFIX):
                        complex_variant = self._find_complex_variant(best_profile.name)
                        if complex_variant:
                            complex_score = complex_variant.score(metadata_map)
                            # Only switch if complex variant has reasonable score
                            if complex_score >= best_score * COMPLEX_VARIANT_MIN_SCORE_RATIO:
                                original_name = best_profile.name
                                best_profile = complex_variant
                                best_score = complex_score
                                complexity_adjusted = True
                
                elif self._should_prefer_simple(metadata):
                    # Prefer base variant for simple/short prompts
                    if best_profile.name.endswith(COMPLEX_SUFFIX):
                        simple_variant = self._find_simple_variant(best_profile.name)
                        if simple_variant:
                            simple_score = simple_variant.score(metadata_map)
                            # Only switch if simple variant has reasonable score
                            if simple_score >= best_score * SIMPLE_VARIANT_MIN_SCORE_RATIO:
                                original_name = best_profile.name
                                best_profile = simple_variant
                                best_score = simple_score
                                complexity_adjusted = True
            # === END COMPLEXITY ADJUSTMENT ===
            
            consistency = self._normalize_consistency(
                best_score, [score for _, score in scored_matches]
            )
            return RoutingResult(
                profile=best_profile,
                score=best_score,
                consistency=consistency,
                complexity_adjusted=complexity_adjusted,
                original_profile_name=original_name,
            )

        if fallback_profile:
            return RoutingResult(
                profile=fallback_profile,
                score=fallback_profile.default_score,
                consistency=100.0,
            )

        raise ValueError("No matching profile and no fallback configured")
