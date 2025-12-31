"""Configuration for complexity-based profile routing.

This module provides configuration constants and environment variable overrides
for the automatic preference of _complex profile variants based on prompt complexity.
"""
from __future__ import annotations

import os
from typing import FrozenSet

# Feature toggle - can be disabled via environment variable
COMPLEXITY_ROUTING_ENABLED: bool = os.getenv(
    "MCP_COMPLEXITY_ROUTING", "true"
).lower() in ("true", "1", "yes")

# Profile naming convention for complex variants
COMPLEX_SUFFIX: str = "_complex"

# Word count thresholds for complexity detection
WORD_COUNT_HIGH_THRESHOLD: int = int(os.getenv("MCP_COMPLEXITY_WORD_HIGH", "80"))
WORD_COUNT_MEDIUM_THRESHOLD: int = int(os.getenv("MCP_COMPLEXITY_WORD_MEDIUM", "40"))
WORD_COUNT_PREFER_COMPLEX_THRESHOLD: int = int(os.getenv("MCP_COMPLEXITY_PREFER_THRESHOLD", "60"))

# Keyword bonus thresholds
KEYWORD_BONUS_HIGH_THRESHOLD: int = 4
KEYWORD_BONUS_MEDIUM_THRESHOLD: int = 2

# Minimum score ratio for variant switching
# Complex variant must have at least this ratio of the base profile's score
COMPLEX_VARIANT_MIN_SCORE_RATIO: float = 0.8
# Simple variant must have at least this ratio when downgrading from complex
SIMPLE_VARIANT_MIN_SCORE_RATIO: float = 0.9

# Complexity levels that trigger _complex preference
COMPLEX_PREFERENCE_LEVELS: FrozenSet[str] = frozenset({"high", "medium"})

# Complexity levels that trigger preference for base (non-complex) profiles
SIMPLE_PREFERENCE_LEVELS: FrozenSet[str] = frozenset({"low"})

# Maximum word count for preferring simple profiles
SIMPLE_PREFERENCE_MAX_WORDS: int = 30


def get_complexity_config() -> dict[str, object]:
    """Return current complexity routing configuration as a dictionary."""
    return {
        "enabled": COMPLEXITY_ROUTING_ENABLED,
        "complex_suffix": COMPLEX_SUFFIX,
        "word_count_thresholds": {
            "high": WORD_COUNT_HIGH_THRESHOLD,
            "medium": WORD_COUNT_MEDIUM_THRESHOLD,
            "prefer_complex": WORD_COUNT_PREFER_COMPLEX_THRESHOLD,
        },
        "keyword_bonus_thresholds": {
            "high": KEYWORD_BONUS_HIGH_THRESHOLD,
            "medium": KEYWORD_BONUS_MEDIUM_THRESHOLD,
        },
        "score_ratios": {
            "complex_min": COMPLEX_VARIANT_MIN_SCORE_RATIO,
            "simple_min": SIMPLE_VARIANT_MIN_SCORE_RATIO,
        },
        "preference_levels": {
            "complex": sorted(COMPLEX_PREFERENCE_LEVELS),
            "simple": sorted(SIMPLE_PREFERENCE_LEVELS),
        },
        "simple_max_words": SIMPLE_PREFERENCE_MAX_WORDS,
    }
