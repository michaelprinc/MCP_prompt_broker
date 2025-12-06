import pytest

from mcp_prompt_broker.router.profile_router import EnhancedMetadata, ProfileRouter
from mcp_prompt_broker.config.profiles import get_instruction_profiles


def test_privacy_profile_selected_for_sensitive_healthcare():
    router = ProfileRouter()
    metadata = EnhancedMetadata(
        prompt="Handle patient info",
        domain="healthcare",
        sensitivity="high",
        language="es",
        context_tags=frozenset({"pii"}),
    )

    routing = router.route(metadata)

    # Accept both standard and complex privacy profiles
    assert routing.profile.name.startswith("privacy_sensitive")
    # With complex profiles, consistency may be lower due to more matching profiles
    assert routing.consistency >= 90.0


def test_creative_profile_selected_for_brainstorming():
    router = ProfileRouter()
    metadata = EnhancedMetadata(
        prompt="Generate product ideas",
        intent="brainstorm",
        audience="marketing",
        language="en",
        context_tags=frozenset({"storytelling"}),
    )

    routing = router.route(metadata)

    # Accept both standard and complex creative profiles
    assert routing.profile.name.startswith("creative_brainstorm")
    # With complex profiles, consistency may be lower due to more matching profiles
    assert routing.consistency >= 90.0


def test_technical_support_profile_for_bug_reports():
    router = ProfileRouter()
    metadata = EnhancedMetadata(
        prompt="Investigate stack trace",
        domain="engineering",
        intent="bug_report",
        context_tags=frozenset({"incident"}),
    )

    routing = router.route(metadata)

    # Accept both standard and complex technical support profiles
    assert routing.profile.name.startswith("technical_support")
    # With complex profiles, consistency may be lower due to more matching profiles
    assert routing.consistency >= 90.0


def test_fallback_used_when_no_profiles_match():
    router = ProfileRouter()
    metadata = EnhancedMetadata(prompt="Hello world")

    routing = router.route(metadata)

    # Accept both standard and complex general default profiles
    assert routing.profile.name.startswith("general_default")
    # Fallback consistency can be lower when multiple fallbacks exist
    assert routing.consistency >= 50.0


def test_privacy_outscores_technical_when_requirements_met():
    router = ProfileRouter()
    metadata = EnhancedMetadata(
        prompt="Server crash with user SSN",
        domain="finance",
        intent="bug_report",
        sensitivity="critical",
        context_tags=frozenset({"pii", "incident"}),
    )

    routing = router.route(metadata)

    # Accept both standard and complex privacy profiles
    assert routing.profile.name.startswith("privacy_sensitive")
    # With complex profiles, consistency may be lower due to more matching profiles
    assert routing.consistency >= 90.0


def test_metadata_from_dict_normalizes_tags():
    router = ProfileRouter(get_instruction_profiles())
    metadata = EnhancedMetadata.from_dict(
        {
            "prompt": "Need help with login",
            "domain": "it",
            "intent": "diagnosis",
            "context_tags": "outage",
        }
    )

    routing = router.route(metadata)

    assert metadata.context_tags == frozenset({"outage"})
    # Accept both standard and complex technical support profiles
    assert routing.profile.name.startswith("technical_support")
    assert routing.score >= routing.profile.default_score
