"""Test routing of Codex CLI prompts to the appropriate profile."""
import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from mcp_prompt_broker.metadata.parser import analyze_prompt
from mcp_prompt_broker.profile_parser import get_profile_loader
from mcp_prompt_broker.router.profile_router import ProfileRouter


def test_codex_cli_prompt():
    """Test that Codex CLI prompt is correctly identified."""
    
    # Test prompt from user
    prompt = """Dobrý den, GitHub Copilot. Prosím, použij Codex CLI pro vytvoření ukázky modelovací úlohy. Modelovací úloha by měla analyzovat jednu z klasifikačních úloh v "Sci-Kit Learn dataset". Výsledek by měl být v novém adresáři."""
    
    print("=" * 80)
    print("TEST: Codex CLI Prompt Routing")
    print("=" * 80)
    print(f"\nPrompt:\n{prompt}\n")
    
    # Step 1: Analyze the prompt
    print("-" * 80)
    print("STEP 1: Prompt Analysis")
    print("-" * 80)
    parsed = analyze_prompt(prompt)
    print(f"Intent: {parsed.intent}")
    print(f"Domain: {parsed.domain}")
    print(f"Topics: {sorted(parsed.topics)}")
    print(f"Sensitivity: {parsed.sensitivity}")
    print(f"Complexity: {parsed.complexity}")
    
    # Step 2: Convert to enhanced metadata
    print("\n" + "-" * 80)
    print("STEP 2: Enhanced Metadata")
    print("-" * 80)
    enhanced = parsed.to_enhanced_metadata()
    print(f"Domain: {enhanced.domain}")
    print(f"Intent: {enhanced.intent}")
    print(f"Context Tags: {sorted(enhanced.context_tags)}")
    
    # Step 3: Load profiles and route
    print("\n" + "-" * 80)
    print("STEP 3: Profile Loading")
    print("-" * 80)
    loader = get_profile_loader()
    print(f"Loaded {len(loader.profiles)} profiles:")
    for profile in loader.profiles:
        print(f"  - {profile.name} (score: {profile.default_score}, fallback: {profile.fallback})")
    
    # Step 4: Test routing
    print("\n" + "-" * 80)
    print("STEP 4: Profile Routing")
    print("-" * 80)
    router = ProfileRouter(loader.profiles)
    result = router.route(enhanced)
    
    print(f"Selected Profile: {result.profile.name}")
    print(f"Score: {result.score}")
    print(f"Consistency: {result.consistency}%")
    
    # Step 5: Check if Codex CLI profile exists and why it wasn't selected
    print("\n" + "-" * 80)
    print("STEP 5: Codex CLI Profile Analysis")
    print("-" * 80)
    
    codex_profile = None
    for profile in loader.profiles:
        if "codex" in profile.name.lower():
            codex_profile = profile
            print(f"Found profile: {profile.name}")
            print(f"  Required capabilities: {profile.required.get('capabilities', [])}")
            print(f"  Weights: {dict(profile.weights)}")
            print(f"  Default score: {profile.default_score}")
            
            # Check if it matches
            metadata_map = enhanced.as_mutable()
            matches = profile.is_match(metadata_map)
            score = profile.score(metadata_map) if matches else 0
            
            print(f"  Matches requirements: {matches}")
            print(f"  Score: {score}")
            
            # Detailed matching analysis
            print(f"\n  Detailed Analysis:")
            for key, allowed_values in profile.required.items():
                value = metadata_map.get(key)
                print(f"    {key}: required={list(allowed_values)}, actual={value}")
                if key == "capabilities":
                    if value:
                        overlap = set(allowed_values).intersection(set(value) if isinstance(value, (list, set)) else {value})
                        print(f"      Overlap: {overlap}")
    
    if not codex_profile:
        print("WARNING: No Codex CLI profile found!")
    
    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    
    return result


if __name__ == "__main__":
    result = test_codex_cli_prompt()
