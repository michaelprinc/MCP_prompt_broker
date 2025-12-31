"""Semantic scoring using sentence embeddings for profile matching.

This module provides semantic similarity scoring between user prompts and
profile utterances using sentence-transformers embeddings.

Optional dependency: sentence-transformers
If not installed, semantic scoring is disabled and keyword-only routing is used.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional, Sequence, TYPE_CHECKING

try:
    import numpy as np
    from numpy.typing import NDArray
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    NDArray = Any  # type: ignore

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    SentenceTransformer = None  # type: ignore

if TYPE_CHECKING:
    from ..config.profiles import InstructionProfile


logger = logging.getLogger(__name__)

# Default model - small, fast, good quality
DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"

# Environment variables for configuration
ENV_MODEL_NAME = "SEMANTIC_MODEL_NAME"
ENV_CACHE_ENABLED = "SEMANTIC_CACHE_ENABLED"


def is_semantic_available() -> bool:
    """Check if semantic scoring dependencies are available."""
    return NUMPY_AVAILABLE and SENTENCE_TRANSFORMERS_AVAILABLE


@dataclass
class SemanticMatch:
    """Result of semantic similarity matching."""
    
    profile_name: str
    best_utterance: str
    similarity: float
    utterance_index: int
    
    def as_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return {
            "profile_name": self.profile_name,
            "best_utterance": self.best_utterance,
            "similarity": round(self.similarity, 4),
            "utterance_index": self.utterance_index,
        }


class SemanticScorer:
    """Computes semantic similarity between prompts and profile utterances.
    
    Uses sentence-transformers to embed prompts and profile utterances,
    then computes cosine similarity to find the best matching profile.
    
    Attributes:
        model_name: Name of the sentence-transformers model to use.
        cache_enabled: Whether to cache utterance embeddings at startup.
    """
    
    def __init__(
        self,
        model_name: Optional[str] = None,
        cache_enabled: bool = True,
    ):
        """Initialize the semantic scorer.
        
        Args:
            model_name: Name of sentence-transformers model. 
                       Defaults to all-MiniLM-L6-v2.
            cache_enabled: Whether to pre-compute utterance embeddings.
        """
        self._model_name = model_name or os.getenv(
            ENV_MODEL_NAME, DEFAULT_MODEL_NAME
        )
        self._cache_enabled = cache_enabled or os.getenv(
            ENV_CACHE_ENABLED, "true"
        ).lower() == "true"
        
        self._model: Optional[SentenceTransformer] = None
        self._utterance_cache: Dict[str, NDArray] = {}
        self._profile_utterances: Dict[str, tuple[str, ...]] = {}
        
        if not is_semantic_available():
            logger.warning(
                "Semantic scoring unavailable: sentence-transformers not installed. "
                "Install with: pip install sentence-transformers"
            )
    
    @property
    def is_available(self) -> bool:
        """Check if semantic scoring is available."""
        return is_semantic_available()
    
    @property
    def model_name(self) -> str:
        """Return the model name being used."""
        return self._model_name
    
    @property
    def is_loaded(self) -> bool:
        """Check if the model is loaded."""
        return self._model is not None
    
    @property
    def cache_size(self) -> int:
        """Return number of cached profile embeddings."""
        return len(self._utterance_cache)
    
    def _load_model(self) -> None:
        """Lazy load the sentence transformer model."""
        if self._model is not None:
            return
        
        if not is_semantic_available():
            raise RuntimeError(
                "Cannot load model: sentence-transformers not installed"
            )
        
        logger.info(f"Loading embedding model: {self._model_name}")
        self._model = SentenceTransformer(self._model_name)
        logger.info(f"Model loaded: {self._model_name}")
    
    def encode(self, text: str) -> NDArray:
        """Encode a single text string to an embedding vector.
        
        Args:
            text: Text to encode.
            
        Returns:
            Embedding vector as numpy array.
            
        Raises:
            RuntimeError: If semantic scoring is not available.
        """
        self._load_model()
        return self._model.encode(text, convert_to_numpy=True)
    
    def encode_batch(self, texts: Sequence[str]) -> NDArray:
        """Encode multiple texts to embedding vectors.
        
        Args:
            texts: List of texts to encode.
            
        Returns:
            Matrix of embedding vectors (n_texts x embedding_dim).
        """
        self._load_model()
        return self._model.encode(list(texts), convert_to_numpy=True)
    
    def cosine_similarity(
        self, 
        vec_a: NDArray, 
        vec_b: NDArray
    ) -> float:
        """Compute cosine similarity between two vectors.
        
        Args:
            vec_a: First embedding vector.
            vec_b: Second embedding vector.
            
        Returns:
            Cosine similarity score in range [-1, 1].
        """
        if not NUMPY_AVAILABLE:
            raise RuntimeError("NumPy not available")
        
        dot_product = np.dot(vec_a, vec_b)
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return float(dot_product / (norm_a * norm_b))
    
    def build_utterance_cache(
        self, 
        profiles: Sequence["InstructionProfile"]
    ) -> int:
        """Pre-compute embeddings for all profile utterances.
        
        Args:
            profiles: List of instruction profiles with utterances.
            
        Returns:
            Number of profiles with cached embeddings.
        """
        if not self.is_available:
            logger.warning("Cannot build cache: semantic scoring unavailable")
            return 0
        
        self._load_model()
        cached_count = 0
        
        for profile in profiles:
            if not profile.utterances:
                continue
            
            # Store utterances for reference
            self._profile_utterances[profile.name] = profile.utterances
            
            # Compute embeddings for all utterances
            embeddings = self.encode_batch(profile.utterances)
            self._utterance_cache[profile.name] = embeddings
            cached_count += 1
            
            logger.debug(
                f"Cached {len(profile.utterances)} utterances for {profile.name}"
            )
        
        logger.info(f"Built utterance cache for {cached_count} profiles")
        return cached_count
    
    def clear_cache(self) -> None:
        """Clear the utterance embedding cache."""
        self._utterance_cache.clear()
        self._profile_utterances.clear()
        logger.info("Cleared utterance cache")
    
    def compute_similarity(
        self,
        prompt: str,
        profile: "InstructionProfile",
    ) -> SemanticMatch:
        """Compute semantic similarity between prompt and profile utterances.
        
        Args:
            prompt: User prompt to match.
            profile: Profile with utterances to match against.
            
        Returns:
            SemanticMatch with best matching utterance and similarity score.
        """
        if not profile.utterances:
            return SemanticMatch(
                profile_name=profile.name,
                best_utterance="",
                similarity=0.0,
                utterance_index=-1,
            )
        
        # Encode the prompt
        prompt_embedding = self.encode(prompt)
        
        # Get utterance embeddings (from cache or compute)
        if profile.name in self._utterance_cache:
            utterance_embeddings = self._utterance_cache[profile.name]
        else:
            utterance_embeddings = self.encode_batch(profile.utterances)
        
        # Compute similarities with all utterances
        similarities = []
        for utt_emb in utterance_embeddings:
            sim = self.cosine_similarity(prompt_embedding, utt_emb)
            similarities.append(sim)
        
        # Find best match
        best_idx = int(np.argmax(similarities))
        best_similarity = similarities[best_idx]
        best_utterance = profile.utterances[best_idx]
        
        return SemanticMatch(
            profile_name=profile.name,
            best_utterance=best_utterance,
            similarity=float(best_similarity),
            utterance_index=best_idx,
        )
    
    def rank_profiles(
        self,
        prompt: str,
        profiles: Sequence["InstructionProfile"],
        min_similarity: float = 0.0,
    ) -> list[SemanticMatch]:
        """Rank profiles by semantic similarity to the prompt.
        
        Args:
            prompt: User prompt to match.
            profiles: List of profiles to rank.
            min_similarity: Minimum similarity threshold to include.
            
        Returns:
            List of SemanticMatch objects sorted by similarity (descending).
        """
        if not self.is_available:
            return []
        
        matches = []
        for profile in profiles:
            if not profile.utterances:
                continue
            
            match = self.compute_similarity(prompt, profile)
            if match.similarity >= min_similarity:
                matches.append(match)
        
        # Sort by similarity descending
        matches.sort(key=lambda m: m.similarity, reverse=True)
        return matches
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the semantic scorer."""
        return {
            "available": self.is_available,
            "model_name": self._model_name,
            "model_loaded": self.is_loaded,
            "cache_enabled": self._cache_enabled,
            "cached_profiles": self.cache_size,
            "total_cached_utterances": sum(
                len(utts) for utts in self._profile_utterances.values()
            ),
        }


# Singleton instance for reuse
_scorer_instance: Optional[SemanticScorer] = None


def get_semantic_scorer(
    model_name: Optional[str] = None,
    force_new: bool = False,
) -> SemanticScorer:
    """Get or create a semantic scorer instance.
    
    Args:
        model_name: Optional model name override.
        force_new: If True, create a new instance instead of reusing.
        
    Returns:
        SemanticScorer instance.
    """
    global _scorer_instance
    
    if force_new or _scorer_instance is None:
        _scorer_instance = SemanticScorer(model_name=model_name)
    
    return _scorer_instance
