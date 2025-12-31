"""Configuration for instruction profiles used by the profile router.

Supports hot-reload from markdown files in copilot-profiles/ directory.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Mapping, MutableMapping, Optional, Sequence, TYPE_CHECKING

if TYPE_CHECKING:
    from ..profile_parser import ProfileLoader


@dataclass(frozen=True)
class InstructionProfile:
    """Instruction set metadata used by the router.

    Attributes:
        name: Human-friendly profile identifier.
        instructions: Instruction content or identifier for downstream use.
        required: Metadata keys and acceptable values that must be present for the
            profile to be considered.
        weights: Optional weighting rules where matches add to the profile score.
        default_score: Base score applied before weighting.
        fallback: Whether the profile should be used when no other profile matches.
        utterances: Sample prompts that should route to this profile (for semantic matching).
        utterance_threshold: Minimum semantic similarity to consider an utterance match.
        min_match_ratio: Minimum match_score() ratio for soft matching (0-1).
    """

    name: str
    instructions: str
    required: Mapping[str, Iterable[str]] = field(default_factory=dict)
    weights: Mapping[str, Mapping[str, int]] = field(default_factory=dict)
    default_score: int = 0
    fallback: bool = False
    utterances: tuple[str, ...] = field(default_factory=tuple)
    utterance_threshold: float = 0.7
    min_match_ratio: float = 0.5

    def match_score(self, metadata: MutableMapping[str, object]) -> float:
        """Calculate a soft match score (0.0-1.0) for how well metadata matches requirements.
        
        This replaces the binary is_match() with a gradient score that enables
        better profile ranking when multiple profiles partially match.
        
        Returns:
            0.0 if no required fields are defined or no matches.
            1.0 if all required fields match perfectly.
            Intermediate values for partial matches.
        """
        if not self.required:
            # No requirements = neutral score (will be ranked by weights)
            return 1.0
        
        total_requirements = 0
        matched_requirements = 0
        
        for key, allowed_values in self.required.items():
            # Skip capabilities check - we match on keywords instead
            if key == "capabilities":
                continue
            
            total_requirements += 1
            value = metadata.get(key)
            
            if value is None:
                continue
            
            # context_tags: check intersection ratio
            if key == "context_tags":
                if isinstance(value, Iterable):
                    value_set = set(value)
                    allowed_set = set(allowed_values)
                    if allowed_set:
                        intersection = value_set.intersection(allowed_set)
                        # Partial credit for partial overlap
                        matched_requirements += len(intersection) / len(allowed_set)
            elif value in allowed_values:
                matched_requirements += 1.0
        
        if total_requirements == 0:
            return 1.0
        
        return matched_requirements / total_requirements

    def is_match(self, metadata: MutableMapping[str, object]) -> bool:
        """Return True if the metadata satisfies the minimum match threshold.
        
        This is now a wrapper around match_score() for backward compatibility.
        A profile matches if match_score() >= min_match_ratio.
        
        Note: Profiles without required fields always match (scored by weights).
        """
        return self.match_score(metadata) >= self.min_match_ratio

    def score(self, metadata: MutableMapping[str, object]) -> int:
        """Calculate a score for the profile based on metadata weights and prompt keywords."""

        score = self.default_score
        prompt = str(metadata.get("prompt", "")).lower()

        for key, value_weights in self.weights.items():
            # Special handling for keywords - match against prompt text
            if key == "keywords":
                if isinstance(value_weights, dict):
                    # Dict format: {"keyword": weight, ...}
                    for keyword, weight in value_weights.items():
                        if keyword.lower() in prompt:
                            score += weight
                elif isinstance(value_weights, (list, tuple)):
                    # List format: ["keyword1", "keyword2", ...] - each match = 1 point
                    for keyword in value_weights:
                        if str(keyword).lower() in prompt:
                            score += 1
                continue
            
            value = metadata.get(key)
            if value is None:
                continue

            if key == "context_tags" and isinstance(value, Iterable):
                score += sum(value_weights.get(tag, 0) for tag in set(value))
            elif isinstance(value_weights, dict):
                score += value_weights.get(value, 0)

        return score


# Fallback profiles for when markdown loading fails
_FALLBACK_PROFILES: tuple[InstructionProfile, ...] = (
    InstructionProfile(
        name="general_default",
        instructions="Use balanced, general-purpose instructions",
        required={},
        weights={"priority": {"high": 1}},
        default_score=1,
        fallback=True,
    ),
)


def get_instruction_profiles(use_markdown: bool = True) -> Sequence[InstructionProfile]:
    """Return instruction profiles, loading from markdown if available.
    
    Args:
        use_markdown: If True, attempt to load from markdown files first.
                     Falls back to hardcoded defaults on failure.
    
    Returns:
        Sequence of InstructionProfile instances.
    """
    if use_markdown:
        try:
            from ..profile_parser import get_profile_loader
            loader = get_profile_loader()
            profiles = loader.profiles
            if profiles:
                return profiles
        except Exception:
            pass  # Fall back to defaults
    
    return _FALLBACK_PROFILES


def reload_instruction_profiles() -> Dict[str, Any]:
    """Reload instruction profiles from markdown files.
    
    Returns:
        Summary of the reload operation.
    """
    from ..profile_parser import reload_profiles
    return reload_profiles()
