"""Hybrid router combining keyword-based and semantic similarity scoring.

This module provides a hybrid routing approach that combines:
1. Traditional keyword-based scoring from the base ProfileRouter
2. Semantic similarity scoring using sentence embeddings

The final score is a weighted combination: alpha * semantic + (1 - alpha) * keyword
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional, Sequence

from .profile_router import EnhancedMetadata, ProfileRouter, RoutingResult
from .semantic_scorer import (
    SemanticScorer,
    SemanticMatch,
    get_semantic_scorer,
    is_semantic_available,
)
from ..config.profiles import InstructionProfile, get_instruction_profiles


logger = logging.getLogger(__name__)

# Environment variables for configuration
ENV_SEMANTIC_ALPHA = "SEMANTIC_ROUTING_ALPHA"
ENV_USE_SEMANTIC = "USE_SEMANTIC_ROUTING"

# Default alpha: 50% semantic, 50% keyword
DEFAULT_ALPHA = 0.5


@dataclass(frozen=True)
class HybridRoutingResult(RoutingResult):
    """Extended routing result with semantic scoring details."""
    
    keyword_score: float = 0.0
    semantic_score: float = 0.0
    combined_score: float = 0.0
    alpha: float = DEFAULT_ALPHA
    best_utterance: str = ""
    semantic_enabled: bool = False
    
    def as_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return {
            "profile": self.profile.name,
            "score": self.score,
            "consistency": self.consistency,
            "keyword_score": round(self.keyword_score, 4),
            "semantic_score": round(self.semantic_score, 4),
            "combined_score": round(self.combined_score, 4),
            "alpha": self.alpha,
            "best_utterance": self.best_utterance,
            "semantic_enabled": self.semantic_enabled,
        }


class HybridProfileRouter(ProfileRouter):
    """Route prompts using combined keyword and semantic scoring.
    
    This router extends the base ProfileRouter with semantic similarity
    scoring. When enabled, the final score combines both approaches:
    
    combined_score = alpha * semantic_score + (1 - alpha) * normalized_keyword_score
    
    Attributes:
        alpha: Weight for semantic scoring (0-1). Default 0.5.
        semantic_enabled: Whether semantic scoring is active.
    """
    
    def __init__(
        self,
        profiles: Sequence[InstructionProfile] | None = None,
        alpha: float | None = None,
        semantic_enabled: bool | None = None,
        semantic_scorer: SemanticScorer | None = None,
    ):
        """Initialize the hybrid router.
        
        Args:
            profiles: List of instruction profiles.
            alpha: Semantic weight (0-1). Defaults to SEMANTIC_ROUTING_ALPHA env var.
            semantic_enabled: Enable semantic scoring. Defaults to USE_SEMANTIC_ROUTING.
            semantic_scorer: Optional custom SemanticScorer instance.
        """
        super().__init__(profiles)
        
        # Parse alpha from env or use default
        if alpha is None:
            alpha_str = os.getenv(ENV_SEMANTIC_ALPHA, str(DEFAULT_ALPHA))
            try:
                alpha = float(alpha_str)
            except ValueError:
                alpha = DEFAULT_ALPHA
        
        self._alpha = max(0.0, min(1.0, alpha))  # Clamp to [0, 1]
        
        # Parse semantic_enabled from env or use default
        if semantic_enabled is None:
            env_val = os.getenv(ENV_USE_SEMANTIC, "false").lower()
            semantic_enabled = env_val in ("true", "1", "yes")
        
        self._semantic_enabled = semantic_enabled and is_semantic_available()
        
        # Initialize semantic scorer if enabled
        if self._semantic_enabled:
            self._scorer = semantic_scorer or get_semantic_scorer()
            # Build utterance cache for faster matching
            self._build_cache()
        else:
            self._scorer = None
            if semantic_enabled and not is_semantic_available():
                logger.warning(
                    "Semantic routing requested but dependencies not available. "
                    "Falling back to keyword-only routing."
                )
    
    @property
    def alpha(self) -> float:
        """Return the semantic weight."""
        return self._alpha
    
    @property
    def semantic_enabled(self) -> bool:
        """Check if semantic scoring is active."""
        return self._semantic_enabled
    
    def _build_cache(self) -> None:
        """Build the utterance embedding cache for all profiles."""
        if self._scorer and self._semantic_enabled:
            profiles_with_utterances = [
                p for p in self.profiles if p.utterances
            ]
            if profiles_with_utterances:
                self._scorer.build_utterance_cache(profiles_with_utterances)
                logger.info(
                    f"Built utterance cache for {len(profiles_with_utterances)} profiles"
                )
    
    def _compute_semantic_score(
        self,
        prompt: str,
        profile: InstructionProfile,
    ) -> tuple[float, str]:
        """Compute semantic similarity score for a profile.
        
        Args:
            prompt: User prompt.
            profile: Profile to score.
            
        Returns:
            Tuple of (similarity_score, best_matching_utterance).
        """
        if not self._scorer or not profile.utterances:
            return 0.0, ""
        
        match = self._scorer.compute_similarity(prompt, profile)
        return match.similarity, match.best_utterance
    
    def _normalize_keyword_score(
        self,
        score: int,
        all_scores: Sequence[int],
    ) -> float:
        """Normalize keyword score to 0-1 range.
        
        Args:
            score: Raw keyword score.
            all_scores: All candidate scores for normalization.
            
        Returns:
            Normalized score in [0, 1].
        """
        if not all_scores:
            return 0.0
        
        max_score = max(all_scores)
        if max_score <= 0:
            return 0.0
        
        return score / max_score
    
    def route(self, metadata: EnhancedMetadata) -> HybridRoutingResult:
        """Return the best profile using hybrid scoring.
        
        Combines keyword scoring with semantic similarity when enabled.
        
        Args:
            metadata: Enhanced metadata for routing.
            
        Returns:
            HybridRoutingResult with detailed scoring information.
        """
        metadata_map = metadata.as_mutable()
        prompt = str(metadata_map.get("prompt", ""))
        
        # Collect all candidates with keyword scores
        candidates: list[tuple[InstructionProfile, int, float]] = []
        fallback_profile: InstructionProfile | None = None
        
        for profile in self.profiles:
            if profile.fallback:
                fallback_profile = fallback_profile or profile
            
            # Use match_score for soft matching
            match_score = profile.match_score(metadata_map)
            if match_score < profile.min_match_ratio:
                continue
            
            keyword_score = profile.score(metadata_map)
            candidates.append((profile, keyword_score, match_score))
        
        if not candidates:
            # Use fallback if no candidates match
            if fallback_profile:
                return HybridRoutingResult(
                    profile=fallback_profile,
                    score=fallback_profile.default_score,
                    consistency=100.0,
                    keyword_score=fallback_profile.default_score,
                    semantic_score=0.0,
                    combined_score=float(fallback_profile.default_score),
                    alpha=self._alpha,
                    best_utterance="",
                    semantic_enabled=self._semantic_enabled,
                )
            raise ValueError("No matching profile and no fallback configured")
        
        # Extract keyword scores for normalization
        all_keyword_scores = [score for _, score, _ in candidates]
        max_keyword = max(all_keyword_scores) if all_keyword_scores else 1
        
        # Score all candidates with hybrid approach
        scored_candidates: list[tuple[
            InstructionProfile, int, float, float, float, str
        ]] = []
        
        for profile, keyword_score, match_score in candidates:
            # Normalize keyword score
            norm_keyword = self._normalize_keyword_score(
                keyword_score, all_keyword_scores
            )
            
            # Compute semantic score if enabled
            if self._semantic_enabled and profile.utterances:
                semantic_score, best_utterance = self._compute_semantic_score(
                    prompt, profile
                )
            else:
                semantic_score = 0.0
                best_utterance = ""
            
            # Compute combined score
            if self._semantic_enabled and profile.utterances:
                combined = (
                    self._alpha * semantic_score + 
                    (1 - self._alpha) * norm_keyword
                )
            else:
                combined = norm_keyword
            
            scored_candidates.append((
                profile, keyword_score, norm_keyword,
                semantic_score, combined, best_utterance
            ))
        
        # Sort by combined score
        scored_candidates.sort(key=lambda x: x[4], reverse=True)
        
        # Select best candidate
        best = scored_candidates[0]
        best_profile = best[0]
        best_keyword = best[1]
        best_norm_keyword = best[2]
        best_semantic = best[3]
        best_combined = best[4]
        best_utterance = best[5]
        
        # Calculate consistency using original method
        consistency = self._normalize_consistency(
            best_keyword,
            [score for _, score, _, _, _, _ in scored_candidates]
        )
        
        return HybridRoutingResult(
            profile=best_profile,
            score=best_keyword,
            consistency=consistency,
            keyword_score=best_norm_keyword,
            semantic_score=best_semantic,
            combined_score=best_combined,
            alpha=self._alpha,
            best_utterance=best_utterance,
            semantic_enabled=self._semantic_enabled,
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get router statistics."""
        stats = {
            "type": "HybridProfileRouter",
            "alpha": self._alpha,
            "semantic_enabled": self._semantic_enabled,
            "total_profiles": len(self.profiles),
            "profiles_with_utterances": sum(
                1 for p in self.profiles if p.utterances
            ),
        }
        
        if self._scorer:
            stats["semantic_scorer"] = self._scorer.get_stats()
        
        return stats


def get_router(
    profiles: Sequence[InstructionProfile] | None = None,
    force_hybrid: bool = False,
) -> ProfileRouter:
    """Factory function to get the appropriate router.
    
    Returns HybridProfileRouter if USE_SEMANTIC_ROUTING is enabled,
    otherwise returns the base ProfileRouter.
    
    Args:
        profiles: Optional list of profiles.
        force_hybrid: Force use of HybridProfileRouter even if semantic disabled.
        
    Returns:
        ProfileRouter or HybridProfileRouter instance.
    """
    use_semantic = os.getenv(ENV_USE_SEMANTIC, "false").lower() in ("true", "1", "yes")
    
    if use_semantic or force_hybrid:
        return HybridProfileRouter(profiles=profiles)
    
    return ProfileRouter(profiles=profiles)
