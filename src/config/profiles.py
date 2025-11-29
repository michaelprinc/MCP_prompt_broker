"""Configuration for instruction profiles used by the profile router."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, Mapping, MutableMapping, Sequence


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
        """Return True if the metadata satisfies the profile requirements."""

        for key, allowed_values in self.required.items():
            value = metadata.get(key)
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
        """Calculate a score for the profile based on metadata weights."""

        score = self.default_score

        for key, value_weights in self.weights.items():
            value = metadata.get(key)
            if value is None:
                continue

            if key == "context_tags" and isinstance(value, Iterable):
                score += sum(value_weights.get(tag, 0) for tag in set(value))
            else:
                score += value_weights.get(value, 0)

        return score


def get_instruction_profiles() -> Sequence[InstructionProfile]:
    """Return the default instruction profiles used by the router."""

    return (
        InstructionProfile(
            name="privacy_sensitive",
            instructions="Use privacy-first responses with redaction",
            required={"sensitivity": {"high", "critical"}},
            weights={
                "domain": {"healthcare": 3, "finance": 2},
                "language": {"es": 1},
                "context_tags": {"pii": 2, "compliance": 1},
            },
            default_score=5,
        ),
        InstructionProfile(
            name="creative_brainstorm",
            instructions="Encourage creative exploration and divergent thinking",
            required={"intent": {"brainstorm", "ideation"}},
            weights={
                "audience": {"marketing": 2, "product": 1},
                "language": {"en": 1, "fr": 1},
                "context_tags": {"storytelling": 2},
            },
            default_score=3,
        ),
        InstructionProfile(
            name="technical_support",
            instructions="Provide concise technical troubleshooting steps",
            required={"domain": {"engineering", "it"}},
            weights={
                "domain": {"engineering": 3, "it": 2},
                "intent": {"bug_report": 3, "diagnosis": 2},
                "context_tags": {"outage": 2, "incident": 1},
            },
            default_score=2,
        ),
        InstructionProfile(
            name="general_default",
            instructions="Use balanced, general-purpose instructions",
            required={},
            weights={"priority": {"high": 1}},
            default_score=1,
            fallback=True,
        ),
    )
