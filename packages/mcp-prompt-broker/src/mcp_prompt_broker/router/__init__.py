"""Routing module for instruction profile selection."""

from .profile_router import EnhancedMetadata, ProfileRouter, RoutingResult
from .semantic_scorer import (
    SemanticScorer,
    SemanticMatch,
    get_semantic_scorer,
    is_semantic_available,
)
from .hybrid_router import (
    HybridProfileRouter,
    HybridRoutingResult,
    get_router,
)
from .complexity_config import (
    COMPLEXITY_ROUTING_ENABLED,
    COMPLEX_SUFFIX,
    get_complexity_config,
)

__all__ = [
    # Base router
    "EnhancedMetadata",
    "ProfileRouter", 
    "RoutingResult",
    # Hybrid router
    "HybridProfileRouter",
    "HybridRoutingResult",
    "get_router",
    # Semantic scoring
    "SemanticScorer",
    "SemanticMatch",
    "get_semantic_scorer",
    "is_semantic_available",
    # Complexity routing
    "COMPLEXITY_ROUTING_ENABLED",
    "COMPLEX_SUFFIX",
    "get_complexity_config",
]
