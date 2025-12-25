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
    """

    name: str
    instructions: str
    required: Mapping[str, Iterable[str]] = field(default_factory=dict)
    weights: Mapping[str, Mapping[str, int]] = field(default_factory=dict)
    default_score: int = 0
    fallback: bool = False

    def is_match(self, metadata: MutableMapping[str, object]) -> bool:
        """Return True if the metadata satisfies the profile requirements.
        
        Note: Profiles without required fields always match (scored by weights).
        """
        if not self.required:
            # No requirements = always matches (will be scored by weights)
            return True

        for key, allowed_values in self.required.items():
            value = metadata.get(key)
            
            # Skip capabilities check - we match on keywords instead
            if key == "capabilities":
                continue
            
            if value is None:
                return False

            # context_tags are represented as iterables that may contain multiple
            # tags, so we need to verify intersection.
            if key == "context_tags":
                if not isinstance(value, Iterable):
                    return False
                if not set(allowed_values).intersection(set(value)):
                    return False
            elif value not in allowed_values:
                return False

        return True

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
