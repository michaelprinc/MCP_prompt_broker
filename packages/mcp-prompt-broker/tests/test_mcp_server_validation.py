"""Comprehensive validation suite for MCP Prompt Broker server.

This script implements the testing methodology from the 
mcp_server_testing_and_validation profile.
"""
import json
import sys
from pathlib import Path
from typing import Dict, List, Any

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from mcp_prompt_broker.profile_parser import (
    get_profile_loader,
    parse_profile_markdown,
    ProfileParseError,
)
from mcp_prompt_broker.metadata.parser import analyze_prompt
from mcp_prompt_broker.router.profile_router import ProfileRouter


class MCPServerValidator:
    """Comprehensive validator for MCP Prompt Broker server."""
    
    def __init__(self, profiles_dir: Path = None):
        self.profiles_dir = profiles_dir or (src_path / "mcp_prompt_broker" / "copilot-profiles")
        self.loader = None
        self.results = {
            "profile_validation": {},
            "parser_tests": {},
            "routing_tests": {},
            "hot_reload_tests": {},
            "overall_status": "not_run"
        }
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run complete test suite."""
        print("=" * 80)
        print("MCP PROMPT BROKER - COMPREHENSIVE VALIDATION SUITE")
        print("=" * 80)
        
        # Phase 1: Profile Structure Validation
        print("\n" + "=" * 80)
        print("PHASE 1: Profile Structure Validation")
        print("=" * 80)
        self._validate_profile_structures()
        
        # Phase 2: Profile Loading Test
        print("\n" + "=" * 80)
        print("PHASE 2: Profile Loading Test")
        print("=" * 80)
        self._test_profile_loading()
        
        # Phase 3: Metadata Parser Test
        print("\n" + "=" * 80)
        print("PHASE 3: Metadata Parser Test")
        print("=" * 80)
        self._test_metadata_parser()
        
        # Phase 4: Routing Logic Test
        print("\n" + "=" * 80)
        print("PHASE 4: Routing Logic Test")
        print("=" * 80)
        self._test_routing_logic()
        
        # Phase 5: Hot Reload Test
        print("\n" + "=" * 80)
        print("PHASE 5: Hot Reload Test")
        print("=" * 80)
        self._test_hot_reload()
        
        # Generate summary
        self._generate_summary()
        
        return self.results
    
    def _validate_profile_structures(self):
        """Validate all profile markdown files for structural correctness."""
        print("\n📋 Scanning profile files...")
        
        md_files = sorted(self.profiles_dir.glob("*.md"))
        print(f"Found {len(md_files)} markdown files")
        
        results = {
            "total_files": len(md_files),
            "valid": [],
            "errors": [],
            "warnings": []
        }
        
        for md_file in md_files:
            print(f"\n🔍 Validating: {md_file.name}")
            
            try:
                parsed = parse_profile_markdown(md_file)
                
                # Check for structural issues
                issues = []
                
                if not parsed.profile.required:
                    issues.append("Empty 'required' field")
                
                if not parsed.profile.weights:
                    issues.append("Empty 'weights' field")
                
                if not parsed.checklist.items:
                    issues.append("No checklist items found")
                
                if not parsed.yaml_metadata.get("short_description"):
                    issues.append("Missing 'short_description'")
                
                # Check for common keywords
                keywords = parsed.yaml_metadata.get("weights", {}).get("keywords", [])
                if isinstance(keywords, dict):
                    keywords = list(keywords.keys())
                
                if not keywords:
                    issues.append("No keywords defined")
                
                if issues:
                    results["warnings"].append({
                        "file": md_file.name,
                        "profile_name": parsed.profile.name,
                        "issues": issues
                    })
                    print(f"  ⚠️  Warnings: {', '.join(issues)}")
                else:
                    results["valid"].append(md_file.name)
                    print(f"  ✅ Valid structure")
                
            except ProfileParseError as e:
                error_msg = str(e)
                results["errors"].append({
                    "file": md_file.name,
                    "error": error_msg,
                    "type": "ProfileParseError"
                })
                print(f"  ❌ Parse Error: {error_msg}")
            
            except Exception as e:
                results["errors"].append({
                    "file": md_file.name,
                    "error": str(e),
                    "type": type(e).__name__
                })
                print(f"  ❌ Unexpected Error: {e}")
        
        self.results["profile_validation"] = results
        
        print(f"\n📊 Summary:")
        print(f"  Total files: {results['total_files']}")
        print(f"  Valid: {len(results['valid'])}")
        print(f"  Warnings: {len(results['warnings'])}")
        print(f"  Errors: {len(results['errors'])}")
    
    def _test_profile_loading(self):
        """Test profile loading and compare with expected count."""
        print("\n🔄 Loading profiles...")
        
        self.loader = get_profile_loader()
        
        # Expected count (md files minus metadata json)
        md_files = list(self.profiles_dir.glob("*.md"))
        expected_count = len(md_files)
        actual_count = len(self.loader.profiles)
        
        print(f"\n📊 Profile Loading Results:")
        print(f"  Expected profiles: {expected_count}")
        print(f"  Loaded profiles: {actual_count}")
        print(f"  Success rate: {actual_count/expected_count*100:.1f}%")
        
        # List loaded profiles
        print(f"\n📝 Loaded profiles:")
        for profile in sorted(self.loader.profiles, key=lambda p: p.name):
            print(f"  - {profile.name} (score: {profile.default_score})")
        
        # Check for missing profiles
        loaded_names = {p.name for p in self.loader.profiles}
        expected_names = {f.stem for f in md_files}
        missing = expected_names - loaded_names
        
        if missing:
            print(f"\n⚠️  Missing profiles (files exist but not loaded):")
            for name in sorted(missing):
                print(f"  - {name}")
        
        # Check for errors
        if self.loader.load_errors:
            print(f"\n❌ Parse Errors ({len(self.loader.load_errors)}):")
            for error in self.loader.load_errors:
                print(f"  - {error}")
        
        self.results["profile_loading"] = {
            "expected_count": expected_count,
            "actual_count": actual_count,
            "success_rate": actual_count / expected_count * 100,
            "loaded_profiles": [p.name for p in self.loader.profiles],
            "missing_profiles": list(missing),
            "parse_errors": self.loader.load_errors
        }
    
    def _test_metadata_parser(self):
        """Test metadata parser with various prompts."""
        print("\n🧪 Testing metadata parser...")
        
        test_cases = [
            {
                "name": "Codex CLI prompt (Czech)",
                "prompt": "Prosím, použij Codex CLI pro vytvoření modelovací úlohy",
                "expected": {
                    "intent": "code_generation",
                    "topics_should_contain": ["codex_cli"],
                }
            },
            {
                "name": "Codex CLI prompt (English)",
                "prompt": "Use Codex CLI to create a classification model",
                "expected": {
                    "intent": "code_generation",
                    "topics_should_contain": ["codex_cli"],
                }
            },
            {
                "name": "Debug prompt",
                "prompt": "Debug the authentication error in the API",
                "expected": {
                    "intent": "bug_report",
                    "domain": "engineering"
                }
            },
            {
                "name": "Brainstorm prompt",
                "prompt": "Brainstorm creative ideas for the campaign",
                "expected": {
                    "intent": "brainstorm",
                    "topics_should_contain": ["storytelling"]
                }
            },
            {
                "name": "Privacy prompt",
                "prompt": "Review patient data with SSN for HIPAA compliance",
                "expected": {
                    "sensitivity": "critical",
                    "topics_should_contain": ["pii", "compliance"]
                }
            }
        ]
        
        results = []
        
        for test_case in test_cases:
            print(f"\n🔬 Test: {test_case['name']}")
            print(f"  Prompt: {test_case['prompt'][:60]}...")
            
            parsed = analyze_prompt(test_case['prompt'])
            
            print(f"  Intent: {parsed.intent}")
            print(f"  Domain: {parsed.domain}")
            print(f"  Topics: {sorted(parsed.topics) if parsed.topics else '[]'}")
            print(f"  Sensitivity: {parsed.sensitivity}")
            
            # Check expectations
            passed = True
            failures = []
            
            expected = test_case.get("expected", {})
            
            if "intent" in expected and parsed.intent != expected["intent"]:
                passed = False
                failures.append(f"Intent mismatch: expected {expected['intent']}, got {parsed.intent}")
            
            if "domain" in expected and parsed.domain != expected["domain"]:
                passed = False
                failures.append(f"Domain mismatch: expected {expected['domain']}, got {parsed.domain}")
            
            if "topics_should_contain" in expected:
                for topic in expected["topics_should_contain"]:
                    if topic not in parsed.topics:
                        passed = False
                        failures.append(f"Missing topic: {topic}")
            
            if "sensitivity" in expected and parsed.sensitivity != expected["sensitivity"]:
                passed = False
                failures.append(f"Sensitivity mismatch: expected {expected['sensitivity']}, got {parsed.sensitivity}")
            
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  {status}")
            
            if failures:
                print(f"  Issues:")
                for failure in failures:
                    print(f"    - {failure}")
            
            results.append({
                "test_name": test_case["name"],
                "prompt": test_case["prompt"],
                "parsed": parsed.as_dict(),
                "expected": expected,
                "passed": passed,
                "failures": failures
            })
        
        self.results["parser_tests"] = {
            "total_tests": len(test_cases),
            "passed": sum(1 for r in results if r["passed"]),
            "failed": sum(1 for r in results if not r["passed"]),
            "results": results
        }
    
    def _test_routing_logic(self):
        """Test routing logic with specific prompts."""
        print("\n🎯 Testing routing logic...")
        
        if not self.loader:
            print("  ⚠️  Skipping: loader not initialized")
            return
        
        router = ProfileRouter(self.loader.profiles)
        
        test_cases = [
            {
                "prompt": "Use Codex CLI to create a classification model",
                "expected_profile": "python_code_generation_complex_with_codex",
                "description": "Codex CLI ML task"
            },
            {
                "prompt": "Brainstorm creative marketing ideas",
                "expected_profile": "creative_brainstorm_complex",
                "description": "Creative brainstorming"
            },
            {
                "prompt": "Manage podman containers and images",
                "expected_profile": "podman_container_management_complex",
                "description": "Container management"
            },
            {
                "prompt": "Review sensitive patient medical records",
                "expected_profile": "privacy_sensitive_complex",
                "description": "Privacy-sensitive task"
            },
            {
                "prompt": "Just a general question",
                "expected_profile": "general_default_complex",
                "description": "Generic fallback"
            }
        ]
        
        results = []
        
        for test_case in test_cases:
            print(f"\n🧭 Test: {test_case['description']}")
            print(f"  Prompt: {test_case['prompt'][:60]}...")
            
            parsed = analyze_prompt(test_case['prompt'])
            enhanced = parsed.to_enhanced_metadata()
            routing = router.route(enhanced)
            
            print(f"  Selected Profile: {routing.profile.name}")
            print(f"  Score: {routing.score}")
            print(f"  Consistency: {routing.consistency}%")
            
            # Check if matches expected
            expected = test_case.get("expected_profile")
            passed = routing.profile.name == expected if expected else True
            
            status = "✅ MATCH" if passed else "⚠️  MISMATCH"
            print(f"  {status}")
            
            if not passed:
                print(f"  Expected: {expected}")
            
            results.append({
                "description": test_case["description"],
                "prompt": test_case["prompt"],
                "expected_profile": expected,
                "actual_profile": routing.profile.name,
                "score": routing.score,
                "consistency": routing.consistency,
                "passed": passed
            })
        
        self.results["routing_tests"] = {
            "total_tests": len(test_cases),
            "passed": sum(1 for r in results if r["passed"]),
            "results": results
        }
    
    def _test_hot_reload(self):
        """Test hot reload functionality."""
        print("\n🔄 Testing hot reload...")
        
        if not self.loader:
            print("  ⚠️  Skipping: loader not initialized")
            return
        
        initial_count = len(self.loader.profiles)
        print(f"  Initial profile count: {initial_count}")
        
        # Test reload
        print("  Triggering reload...")
        reload_result = self.loader.reload()
        
        new_count = len(self.loader.profiles)
        print(f"  Profile count after reload: {new_count}")
        
        print(f"\n  Reload result:")
        print(f"    Success: {reload_result.get('success', False)}")
        print(f"    Profiles loaded: {reload_result.get('profiles_loaded', 0)}")
        
        if reload_result.get('errors'):
            print(f"    Errors: {len(reload_result['errors'])}")
            for error in reload_result['errors']:
                print(f"      - {error}")
        else:
            print(f"    Errors: None")
        
        # Check consistency
        consistent = initial_count == new_count
        status = "✅ CONSISTENT" if consistent else "⚠️  INCONSISTENT"
        print(f"\n  {status}")
        
        self.results["hot_reload_tests"] = {
            "initial_count": initial_count,
            "reload_count": new_count,
            "consistent": consistent,
            "reload_result": reload_result
        }
    
    def _generate_summary(self):
        """Generate overall test summary."""
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        
        # Profile validation
        pv = self.results.get("profile_validation", {})
        print(f"\n📋 Profile Validation:")
        print(f"  Valid: {len(pv.get('valid', []))}/{pv.get('total_files', 0)}")
        print(f"  Warnings: {len(pv.get('warnings', []))}")
        print(f"  Errors: {len(pv.get('errors', []))}")
        
        # Profile loading
        pl = self.results.get("profile_loading", {})
        print(f"\n🔄 Profile Loading:")
        print(f"  Success rate: {pl.get('success_rate', 0):.1f}%")
        print(f"  Missing profiles: {len(pl.get('missing_profiles', []))}")
        
        # Parser tests
        pt = self.results.get("parser_tests", {})
        print(f"\n🧪 Metadata Parser:")
        print(f"  Passed: {pt.get('passed', 0)}/{pt.get('total_tests', 0)}")
        
        # Routing tests
        rt = self.results.get("routing_tests", {})
        print(f"\n🎯 Routing Logic:")
        print(f"  Passed: {rt.get('passed', 0)}/{rt.get('total_tests', 0)}")
        
        # Hot reload
        hr = self.results.get("hot_reload_tests", {})
        print(f"\n🔄 Hot Reload:")
        print(f"  Consistent: {'Yes' if hr.get('consistent') else 'No'}")
        
        # Overall status
        all_passed = (
            len(pv.get('errors', [])) == 0 and
            pl.get('success_rate', 0) == 100 and
            pt.get('passed', 0) == pt.get('total_tests', 1) and
            rt.get('passed', 0) == rt.get('total_tests', 1) and
            hr.get('consistent', False)
        )
        
        status = "✅ ALL TESTS PASSED" if all_passed else "⚠️  SOME TESTS FAILED"
        print(f"\n{status}")
        
        self.results["overall_status"] = "passed" if all_passed else "failed"
    
    def save_report(self, output_path: Path):
        """Save detailed test report to JSON."""
        output_path.write_text(json.dumps(self.results, indent=2))
        print(f"\n💾 Report saved to: {output_path}")


def main():
    """Run the validation suite."""
    validator = MCPServerValidator()
    results = validator.run_all_tests()
    
    # Save report
    report_path = Path(__file__).parent / "mcp_server_validation_report.json"
    validator.save_report(report_path)
    
    # Exit with appropriate code
    exit_code = 0 if results["overall_status"] == "passed" else 1
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
