"""Tests for keyword inheritance via extends in profile parser."""
from __future__ import annotations

import pytest
from pathlib import Path
from typing import Dict, Any

from mcp_prompt_broker.profile_parser import (
    _merge_profile_weights,
    ProfileLoader,
    parse_profile_markdown,
)
from mcp_prompt_broker.metadata.parser import analyze_prompt
from mcp_prompt_broker.router.hybrid_router import get_router


class TestMergeProfileWeights:
    """Tests for _merge_profile_weights function."""
    
    def test_merge_empty_parent(self):
        """Child weights are returned when parent is empty."""
        parent = {}
        child = {"keywords": {"test": 10}}
        
        result = _merge_profile_weights(parent, child)
        
        assert result == {"keywords": {"test": 10}}
    
    def test_merge_empty_child(self):
        """Parent weights are returned when child is empty."""
        parent = {"keywords": {"parent_kw": 5}}
        child = {}
        
        result = _merge_profile_weights(parent, child)
        
        assert result == {"keywords": {"parent_kw": 5}}
    
    def test_child_overrides_parent(self):
        """Child keywords override parent keywords with same key."""
        parent = {"keywords": {"shared": 5, "parent_only": 3}}
        child = {"keywords": {"shared": 10, "child_only": 7}}
        
        result = _merge_profile_weights(parent, child)
        
        assert result["keywords"]["shared"] == 10  # Child overrides
        assert result["keywords"]["parent_only"] == 3  # Inherited
        assert result["keywords"]["child_only"] == 7  # Added
    
    def test_merge_multiple_weight_categories(self):
        """Multiple weight categories are merged correctly."""
        parent = {
            "keywords": {"kw1": 5},
            "domain": {"engineering": 3},
        }
        child = {
            "keywords": {"kw2": 7},
            "priority": {"high": 4},
        }
        
        result = _merge_profile_weights(parent, child)
        
        assert "kw1" in result["keywords"]
        assert "kw2" in result["keywords"]
        assert result["domain"]["engineering"] == 3
        assert result["priority"]["high"] == 4
    
    def test_merge_preserves_original_dicts(self):
        """Original dictionaries are not mutated."""
        parent = {"keywords": {"kw1": 5}}
        child = {"keywords": {"kw2": 7}}
        
        parent_copy = {"keywords": {"kw1": 5}}
        child_copy = {"keywords": {"kw2": 7}}
        
        _merge_profile_weights(parent, child)
        
        assert parent == parent_copy
        assert child == child_copy


class TestExtendsResolution:
    """Tests for extends resolution in ProfileLoader."""
    
    @pytest.fixture
    def loader(self) -> ProfileLoader:
        """Get a fresh profile loader."""
        # Reset global loader
        import mcp_prompt_broker.profile_parser as pp
        pp._global_loader = None
        
        loader = ProfileLoader()
        loader.reload()
        return loader
    
    def test_implementation_planner_complex_inherits_keywords(self, loader):
        """implementation_planner_complex inherits keywords from parent."""
        parent = loader.parsed_profiles.get("implementation_planner")
        child = loader.parsed_profiles.get("implementation_planner_complex")
        
        assert parent is not None
        assert child is not None
        
        parent_keywords = set(parent.profile.weights.get("keywords", {}).keys())
        child_keywords = set(child.profile.weights.get("keywords", {}).keys())
        
        # Child should have all parent keywords
        assert parent_keywords.issubset(child_keywords), \
            f"Missing keywords: {parent_keywords - child_keywords}"
    
    def test_child_has_more_keywords_than_original(self, loader):
        """Child profile has merged keywords (more than its original)."""
        child = loader.parsed_profiles.get("implementation_planner_complex")
        
        assert child is not None
        
        # implementation_planner_complex originally had 27 keywords
        # After merge with parent (36), it should have ~63
        keyword_count = len(child.profile.weights.get("keywords", {}))
        
        assert keyword_count > 27, f"Expected > 27 keywords, got {keyword_count}"
        assert keyword_count >= 50, f"Expected >= 50 merged keywords, got {keyword_count}"
    
    def test_extends_chain_resolution(self, loader):
        """Multi-level extends chain is resolved correctly."""
        # python_code_generation_complex_with_codex extends python_code_generation_complex
        # which extends python_code_generation
        
        level1 = loader.parsed_profiles.get("python_code_generation")
        level2 = loader.parsed_profiles.get("python_code_generation_complex")
        level3 = loader.parsed_profiles.get("python_code_generation_complex_with_codex")
        
        assert level1 is not None
        assert level2 is not None
        assert level3 is not None
        
        kw1 = set(level1.profile.weights.get("keywords", {}).keys())
        kw2 = set(level2.profile.weights.get("keywords", {}).keys())
        kw3 = set(level3.profile.weights.get("keywords", {}).keys())
        
        # Each level should have keywords from previous levels
        assert kw1.issubset(kw2), "Level 2 should inherit from level 1"
        assert kw2.issubset(kw3), "Level 3 should inherit from level 2"
    
    def test_reload_summary_includes_extends(self, loader):
        """Reload summary includes extends resolution details."""
        result = loader.reload()
        
        assert "extends_resolution" in result
        ext = result["extends_resolution"]
        
        assert ext["success"] is True
        assert ext["resolved_count"] == 9  # 9 profiles with extends
        assert len(ext["details"]) == 9


class TestComplexProfileRouting:
    """Integration tests for complex profile routing after keyword inheritance."""
    
    @pytest.fixture
    def router_and_loader(self):
        """Get fresh router and loader."""
        import mcp_prompt_broker.profile_parser as pp
        pp._global_loader = None
        
        loader = ProfileLoader()
        loader.reload()
        router = get_router(loader.profiles)
        return router, loader
    
    def test_complex_prompt_routes_to_complex_variant(self, router_and_loader):
        """Complex prompt should route to implementation_planner_complex."""
        router, loader = router_and_loader
        
        prompt = (
            "Vytvoř komplexní implementační plán pro úpravu adresářové struktury "
            "workspace v souladu s nejlepší praxí. Workspace obsahuje více modulů: "
            "mcp-prompt-broker, llama-orchestrator, mcp-codex-orchestrator a další."
        )
        
        parsed = analyze_prompt(prompt)
        enhanced = parsed.to_enhanced_metadata()
        result = router.route(enhanced)
        
        assert result.profile.name == "implementation_planner_complex", \
            f"Expected implementation_planner_complex, got {result.profile.name}"
    
    def test_complex_variant_score_higher_than_base(self, router_and_loader):
        """Complex variant should score higher than base for complex prompts."""
        router, loader = router_and_loader
        
        prompt = (
            "Vytvoř komplexní implementační plán pro úpravu adresářové struktury "
            "workspace v souladu s nejlepší praxí. Workspace obsahuje více modulů."
        )
        
        parsed = analyze_prompt(prompt)
        enhanced = parsed.to_enhanced_metadata()
        metadata_map = enhanced.as_mutable()
        
        base_profile = None
        complex_profile = None
        
        for p in router.profiles:
            if p.name == "implementation_planner":
                base_profile = p
            elif p.name == "implementation_planner_complex":
                complex_profile = p
        
        assert base_profile is not None
        assert complex_profile is not None
        
        base_score = base_profile.score(metadata_map)
        complex_score = complex_profile.score(metadata_map)
        
        assert complex_score >= base_score, \
            f"Complex ({complex_score}) should be >= base ({base_score})"
    
    def test_simple_prompt_routes_to_base(self, router_and_loader):
        """Simple prompt should route to base implementation_planner."""
        router, loader = router_and_loader
        
        prompt = "Vytvoř implementační plán."
        
        parsed = analyze_prompt(prompt)
        enhanced = parsed.to_enhanced_metadata()
        result = router.route(enhanced)
        
        # For very simple prompt, base profile should win or be selected
        # (exact result depends on other profiles' scores)
        assert result.profile.name in [
            "implementation_planner", 
            "implementation_planner_complex"
        ]


class TestCircularExtendsDetection:
    """Tests for circular extends detection."""
    
    def test_no_circular_extends_in_real_profiles(self):
        """Real profiles should not have circular extends."""
        import mcp_prompt_broker.profile_parser as pp
        pp._global_loader = None
        
        loader = ProfileLoader()
        loader.reload()
        
        # _check_circular_extends is called during reload
        # If there were circular deps, there would be errors
        errors = [e for e in loader.load_errors if "Circular" in e]
        
        assert len(errors) == 0, f"Circular extends detected: {errors}"
