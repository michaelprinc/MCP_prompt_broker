"""Test that the MCP server testing profile is correctly identified."""
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from mcp_prompt_broker.metadata.parser import analyze_prompt
from mcp_prompt_broker.profile_parser import get_profile_loader
from mcp_prompt_broker.router.profile_router import ProfileRouter


def test_testing_profile_detection():
    """Test that testing and validation prompts route to correct profile."""
    
    test_prompts = [
        "Zkontroluj funkčnost MCP serveru prompt broker",
        "Validate all profiles in the MCP server",
        "Test the routing logic for prompt broker",
        "Debug the MCP server profile loading",
        "Verify hot reload functionality of prompt broker"
    ]
    
    print("=" * 80)
    print("TEST: MCP Server Testing Profile Detection")
    print("=" * 80)
    
    loader = get_profile_loader()
    router = ProfileRouter(loader.profiles)
    
    # Check if testing profile was loaded
    testing_profile = None
    for profile in loader.profiles:
        if "testing" in profile.name.lower() and "validation" in profile.name.lower():
            testing_profile = profile
            break
    
    if testing_profile:
        print(f"\n✅ Testing profile loaded: {testing_profile.name}")
        print(f"   Default score: {testing_profile.default_score}")
        print(f"   Required capabilities: {list(testing_profile.required.get('capabilities', []))}")
    else:
        print("\n❌ Testing profile NOT found!")
        return
    
    print("\n" + "-" * 80)
    print("Testing various validation prompts:")
    print("-" * 80)
    
    for prompt in test_prompts:
        print(f"\n📝 Prompt: {prompt}")
        
        parsed = analyze_prompt(prompt)
        enhanced = parsed.to_enhanced_metadata()
        result = router.route(enhanced)
        
        print(f"   Intent: {parsed.intent}")
        print(f"   Domain: {parsed.domain}")
        print(f"   Topics: {sorted(parsed.topics) if parsed.topics else '[]'}")
        print(f"   Selected Profile: {result.profile.name}")
        print(f"   Score: {result.score}")
        
        # Check if it matched the testing profile
        if result.profile.name == testing_profile.name:
            print(f"   ✅ Correctly routed to testing profile")
        else:
            print(f"   ⚠️  Routed to different profile (not testing)")


if __name__ == "__main__":
    test_testing_profile_detection()
