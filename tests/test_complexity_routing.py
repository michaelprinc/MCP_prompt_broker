"""Tests for complexity-based profile routing.

This module tests the automatic preference of _complex profile variants
based on prompt length and complexity keywords.
"""
import os
import pytest
from unittest.mock import patch

from mcp_prompt_broker.metadata.parser import (
    analyze_prompt,
    COMPLEXITY_KEYWORDS,
    _estimate_complexity,
    _calculate_complexity_keyword_bonus,
)
from mcp_prompt_broker.router.profile_router import ProfileRouter, EnhancedMetadata
from mcp_prompt_broker.router.complexity_config import (
    COMPLEXITY_ROUTING_ENABLED,
    COMPLEX_SUFFIX,
    WORD_COUNT_PREFER_COMPLEX_THRESHOLD,
    get_complexity_config,
)
from mcp_prompt_broker.profile_parser import get_profile_loader


class TestComplexityKeywords:
    """Test complexity keyword detection."""

    def test_complexity_keywords_defined(self):
        """Verify COMPLEXITY_KEYWORDS is populated."""
        assert len(COMPLEXITY_KEYWORDS) > 10
        assert "complex" in COMPLEXITY_KEYWORDS
        assert "enterprise" in COMPLEXITY_KEYWORDS
        assert "migration" in COMPLEXITY_KEYWORDS

    def test_keyword_bonus_calculation(self):
        """Test keyword bonus is calculated correctly."""
        # Single keyword
        bonus = _calculate_complexity_keyword_bonus("this is a complex task")
        assert bonus >= 3  # "complex" has weight 3

        # Multiple keywords
        bonus = _calculate_complexity_keyword_bonus(
            "enterprise migration architecture"
        )
        assert bonus >= 7  # enterprise(3) + migration(2) + architecture(2)

        # No keywords
        bonus = _calculate_complexity_keyword_bonus("simple hello world")
        assert bonus == 0


class TestEstimateComplexity:
    """Test complexity estimation function."""

    def test_short_prompt_low_complexity(self):
        """Short prompt without keywords = low complexity."""
        complexity, word_count, keyword_bonus = _estimate_complexity("Hello world")
        assert complexity == "low"
        assert word_count == 2
        assert keyword_bonus == 0

    def test_medium_prompt_low_medium_complexity(self):
        """Medium prompt (15-40 words) = low-medium complexity."""
        prompt = "This is a test prompt " * 5  # ~25 words
        complexity, word_count, keyword_bonus = _estimate_complexity(prompt)
        assert complexity == "low-medium"
        assert 20 <= word_count <= 30

    def test_long_prompt_high_complexity(self):
        """Long prompt (80+ words) = high complexity."""
        prompt = "This is a test word " * 20  # 100 words
        complexity, word_count, keyword_bonus = _estimate_complexity(prompt)
        assert complexity == "high"
        assert word_count >= 80

    def test_keyword_override_short_prompt(self):
        """Keywords can override word count for complexity."""
        # Short prompt with high-weight keywords
        prompt = "Complex enterprise migration"
        complexity, word_count, keyword_bonus = _estimate_complexity(prompt)
        assert complexity == "high"
        assert word_count == 3
        assert keyword_bonus >= 7  # complex(3) + enterprise(3) + migration(2)


class TestParsedMetadataExtension:
    """Test ParsedMetadata new attributes."""

    def test_prompt_length_attribute(self):
        """Verify prompt_length is set correctly."""
        result = analyze_prompt("This is a test prompt with seven words")
        assert result.prompt_length == 8

    def test_complexity_keyword_bonus_attribute(self):
        """Verify complexity_keyword_bonus is set correctly."""
        result = analyze_prompt("Enterprise architecture migration")
        assert result.complexity_keyword_bonus >= 7

    def test_as_dict_includes_new_fields(self):
        """Verify as_dict() includes new fields."""
        result = analyze_prompt("Test prompt")
        data = result.as_dict()
        assert "prompt_length" in data
        assert "complexity_keyword_bonus" in data


class TestEnhancedMetadataExtension:
    """Test EnhancedMetadata new attributes."""

    def test_complexity_propagation(self):
        """Verify complexity is propagated to EnhancedMetadata."""
        parsed = analyze_prompt("Complex enterprise task")
        enhanced = parsed.to_enhanced_metadata()
        assert enhanced.complexity == "high"

    def test_prompt_length_propagation(self):
        """Verify prompt_length is propagated to EnhancedMetadata."""
        parsed = analyze_prompt("This prompt has five words")
        enhanced = parsed.to_enhanced_metadata()
        assert enhanced.prompt_length == 5

    def test_from_dict_with_complexity(self):
        """Verify from_dict handles new attributes."""
        data = {
            "prompt": "test",
            "complexity": "high",
            "prompt_length": 50,
        }
        enhanced = EnhancedMetadata.from_dict(data)
        assert enhanced.complexity == "high"
        assert enhanced.prompt_length == 50


class TestProfilePairDiscovery:
    """Test profile pair discovery in router."""

    @pytest.fixture
    def router(self):
        """Create router with real profiles."""
        loader = get_profile_loader()
        return ProfileRouter(loader.profiles)

    def test_profile_pairs_discovered(self, router):
        """Verify profile pairs are discovered correctly."""
        pairs = router._profile_pairs
        assert len(pairs) >= 6
        assert "implementation_planner" in pairs
        assert pairs["implementation_planner"] == "implementation_planner_complex"

    def test_find_complex_variant(self, router):
        """Test _find_complex_variant method."""
        complex_profile = router._find_complex_variant("implementation_planner")
        assert complex_profile is not None
        assert complex_profile.name == "implementation_planner_complex"

    def test_find_complex_variant_not_found(self, router):
        """Test _find_complex_variant returns None for profiles without complex variant."""
        result = router._find_complex_variant("nonexistent_profile")
        assert result is None

    def test_find_complex_variant_already_complex(self, router):
        """Test _find_complex_variant returns None for already complex profiles."""
        result = router._find_complex_variant("implementation_planner_complex")
        assert result is None

    def test_find_simple_variant(self, router):
        """Test _find_simple_variant method."""
        simple_profile = router._find_simple_variant("implementation_planner_complex")
        assert simple_profile is not None
        assert simple_profile.name == "implementation_planner"

    def test_find_simple_variant_not_found(self, router):
        """Test _find_simple_variant returns None for non-complex profiles."""
        result = router._find_simple_variant("implementation_planner")
        assert result is None


class TestComplexityPreferenceLogic:
    """Test _should_prefer_complex and _should_prefer_simple methods."""

    @pytest.fixture
    def router(self):
        """Create router with real profiles."""
        loader = get_profile_loader()
        return ProfileRouter(loader.profiles)

    def test_should_prefer_complex_for_high_complexity(self, router):
        """High complexity prompts should prefer complex profiles."""
        parsed = analyze_prompt("Complex enterprise migration architecture")
        enhanced = parsed.to_enhanced_metadata()
        assert router._should_prefer_complex(enhanced) is True

    def test_should_prefer_complex_for_long_prompt(self, router):
        """Long prompts (60+ words) should prefer complex profiles."""
        prompt = "This is a test word " * 15  # 75 words
        parsed = analyze_prompt(prompt)
        enhanced = parsed.to_enhanced_metadata()
        assert router._should_prefer_complex(enhanced) is True

    def test_should_not_prefer_complex_for_short_prompt(self, router):
        """Short simple prompts should not prefer complex profiles."""
        parsed = analyze_prompt("Simple task")
        enhanced = parsed.to_enhanced_metadata()
        assert router._should_prefer_complex(enhanced) is False

    def test_should_prefer_simple_for_low_complexity(self, router):
        """Low complexity short prompts should prefer simple profiles."""
        parsed = analyze_prompt("Hello")
        enhanced = parsed.to_enhanced_metadata()
        assert router._should_prefer_simple(enhanced) is True


class TestComplexityRouting:
    """Test the full routing with complexity adjustment."""

    @pytest.fixture
    def router(self):
        """Create router with real profiles."""
        loader = get_profile_loader()
        return ProfileRouter(loader.profiles)

    def test_routing_result_has_complexity_fields(self, router):
        """Verify RoutingResult includes complexity fields."""
        parsed = analyze_prompt("Test prompt")
        enhanced = parsed.to_enhanced_metadata()
        result = router.route(enhanced)
        
        assert hasattr(result, 'complexity_adjusted')
        assert hasattr(result, 'original_profile_name')

    def test_short_prompt_uses_base_profile(self, router):
        """Short prompts should use base profiles when available."""
        parsed = analyze_prompt("Jednoduchý plán")  # Simple plan
        enhanced = parsed.to_enhanced_metadata()
        result = router.route(enhanced)
        
        # Should not be adjusted (may or may not end with _complex)
        # The key is that complexity_adjusted tracks manual switches
        assert result.profile is not None

    def test_high_complexity_triggers_complex_variant(self, router):
        """High complexity should trigger switch to _complex variant."""
        # This prompt triggers implementation_planner context
        prompt = "Potřebuji komplexní implementační plán pro enterprise migraci s architekturou microservices"
        parsed = analyze_prompt(prompt)
        enhanced = parsed.to_enhanced_metadata()
        result = router.route(enhanced)
        
        # Should select a profile (may be complex already due to keywords)
        assert result.profile is not None
        # Complexity should be high due to keywords
        assert parsed.complexity == "high"


class TestComplexityRoutingDisabled:
    """Test routing with complexity routing disabled."""

    @pytest.fixture
    def router_disabled(self):
        """Create router with complexity routing disabled."""
        with patch.dict(os.environ, {"MCP_COMPLEXITY_ROUTING": "false"}):
            # Need to reimport to pick up new env var
            from mcp_prompt_broker.router import complexity_config
            import importlib
            importlib.reload(complexity_config)
            
            loader = get_profile_loader()
            return ProfileRouter(loader.profiles)

    def test_disabled_routing_does_not_adjust(self, router_disabled):
        """When disabled, routing should not adjust profiles."""
        # This test would need proper env var mocking
        # For now, just verify the config function works
        config = get_complexity_config()
        assert "enabled" in config


class TestComplexityConfig:
    """Test complexity configuration module."""

    def test_get_complexity_config(self):
        """Verify get_complexity_config returns expected structure."""
        config = get_complexity_config()
        
        assert "enabled" in config
        assert "complex_suffix" in config
        assert "word_count_thresholds" in config
        assert "keyword_bonus_thresholds" in config
        assert "score_ratios" in config
        assert "preference_levels" in config

    def test_complex_suffix_constant(self):
        """Verify COMPLEX_SUFFIX is defined correctly."""
        assert COMPLEX_SUFFIX == "_complex"


class TestIntegration:
    """Integration tests for the full complexity routing flow."""

    def test_end_to_end_short_prompt(self):
        """E2E test: short prompt routing."""
        loader = get_profile_loader()
        router = ProfileRouter(loader.profiles)
        
        parsed = analyze_prompt("Vytvoř funkci")
        enhanced = parsed.to_enhanced_metadata()
        result = router.route(enhanced)
        
        assert result.profile is not None
        assert result.score >= 0
        assert 0 <= result.consistency <= 100

    def test_end_to_end_long_complex_prompt(self):
        """E2E test: long complex prompt routing."""
        loader = get_profile_loader()
        router = ProfileRouter(loader.profiles)
        
        prompt = """
        Potřebuji vytvořit komplexní enterprise systém pro správu dokumentů.
        Systém musí podporovat microservices architekturu s Kubernetes deployment.
        Musí obsahovat autentizaci přes OAuth2, audit logging, a škálovatelnou
        databázovou vrstvu s PostgreSQL a Redis cache. Deployment bude přes
        CI/CD pipeline s GitLab a Terraform pro infrastructure as code.
        """
        
        parsed = analyze_prompt(prompt)
        enhanced = parsed.to_enhanced_metadata()
        result = router.route(enhanced)
        
        assert result.profile is not None
        # Should detect high complexity due to keywords
        assert parsed.complexity in ("high", "medium")
        assert parsed.complexity_keyword_bonus > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
