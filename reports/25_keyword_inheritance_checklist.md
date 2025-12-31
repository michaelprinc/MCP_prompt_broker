# Keyword Inheritance for Complex Profiles - Implementation Checklist

> Generated: 2026-01-01  
> Complexity: Medium  
> Estimated Total Effort: 2-3 hours  
> Related Report: [25_complexity_routing_score_ratio_analysis.md](25_complexity_routing_score_ratio_analysis.md)

---

## Phase 1: Analysis & Preparation (30 min)

- [x] **1.1** Review current `extends` handling in `profile_parser.py`
  - Acceptance: Understand how `extends` field is parsed but not applied to keywords
  - ✅ `extends` is stored in `yaml_metadata` but never processed for inheritance
  
- [x] **1.2** Identify all profiles using `extends`
  - Acceptance: List of all parent-child profile pairs documented
  - ✅ Found 9 profiles with extends:
    - `creative_brainstorm_complex` → `creative_brainstorm`
    - `general_default_complex` → `general_default`
    - `implementation_planner_complex` → `implementation_planner`
    - `podman_container_management_complex` → `podman_container_management`
    - `privacy_sensitive_complex` → `privacy_sensitive`
    - `python_code_generation_complex` → `python_code_generation`
    - `python_code_generation_complex_with_codex` → `python_code_generation_complex`
    - `python_testing_revision_complex` → `python_testing_revision`
    - `technical_support_complex` → `technical_support`
  
- [x] **1.3** Document current keyword inheritance gap
  - Acceptance: Clear understanding of which fields should be inherited
  - ✅ Need to inherit: `weights.keywords` (primary), optionally other weights

---

## Phase 2: Core Implementation (60 min)

- [x] **2.1** Implement keyword merging in `ProfileLoader._load_profiles()`
  - File: `src/mcp_prompt_broker/profile_parser.py`
  - Acceptance: Child profiles inherit `weights.keywords` from parent
  - Child keywords override parent keywords with same key
  - ✅ Implemented `_merge_profile_weights()` function
  
- [x] **2.2** Add `_merge_profile_weights()` helper function
  - File: `src/mcp_prompt_broker/profile_parser.py`
  - Acceptance: Clean merge logic for weights dictionaries
  - ✅ Function merges parent + child weights, child overrides parent
  
- [x] **2.3** Handle circular extends detection
  - Acceptance: Prevent infinite loops when A extends B extends A
  - ✅ Implemented `_check_circular_extends()` method
  
- [x] **2.4** Ensure proper load order (parents before children)
  - Acceptance: Topological sort of profiles by extends dependency
  - ✅ Implemented `_get_extends_order()` with topological sort

---

## Phase 3: Testing (45 min)

- [x] **3.1** Create unit test for keyword inheritance
  - File: `tests/test_keyword_inheritance.py`
  - Acceptance: Test parent→child keyword merge works correctly
  - ✅ Created 13 tests in `tests/test_keyword_inheritance.py`
  
- [x] **3.2** Test with original failing prompt
  ```
  "Vytvoř komplexní implementační plán pro úpravu adresářové struktury workspace..."
  ```
  - Acceptance: Returns `implementation_planner_complex` instead of `implementation_planner`
  - ✅ Test `test_complex_prompt_routes_to_complex_variant` passes
  
- [x] **3.3** Test score calculation after merge
  - Acceptance: `implementation_planner_complex` score ≥ 38 (same as parent)
  - ✅ Score is now 51 (was 23), parent score is 38
  
- [x] **3.4** Run existing test suite
  - Command: `pytest tests/ -v`
  - Acceptance: All existing tests pass
  - ✅ 87/88 tests pass (1 pre-existing failure unrelated to this change)

---

## Phase 4: Validation & Integration (30 min)

- [x] **4.1** Hot-reload profiles and verify via MCP
  - Tool: `reload_profiles`
  - Acceptance: Profiles reload without errors
  - ✅ Reload successful, 47 profiles loaded, no errors
  - ⚠️ Note: MCP server requires restart to load new Python code
  
- [x] **4.2** Test via `resolve_prompt` MCP tool
  - Acceptance: Complex prompts route to `_complex` variants
  - ✅ Verified via Python simulation - returns `implementation_planner_complex` with score 51
  - ⚠️ MCP server in VS Code needs restart to reflect code changes
  
- [x] **4.3** Verify no regression in other profile pairs
  - Profiles to check: `technical_support_complex`, `creative_brainstorm_complex`, etc.
  - ✅ All 9 extends relationships resolved correctly

---

## Phase 5: Documentation (15 min)

- [x] **5.1** Update `extends` documentation in profile templates
  - Acceptance: Document that keywords are inherited
  - ✅ Added "Keyword Inheritance via extends" section to DEVELOPER_GUIDE.md
  
- [x] **5.2** Add example in developer guide
  - File: `docs/DEVELOPER_GUIDE.md`
  - Acceptance: Clear example of keyword inheritance
  - ✅ Added merge example and multi-level inheritance explanation

---

## Rollback Plan

If issues arise:
1. Revert changes in `profile_parser.py`
2. Run `reload_profiles` to restore original behavior
3. All changes are backward-compatible (no data migration needed)

---

## Success Criteria

| Metric | Before | After |
|--------|--------|-------|
| `implementation_planner_complex` score | 23 | ✅ **51** |
| Prompt routes to complex variant | ❌ | ✅ |
| `extends` inherits keywords | ❌ | ✅ |
| Existing tests pass | ✅ | ✅ (87/88) |

---

## Implementation Summary

**Completed:** 2026-01-01

**Files modified:**
- `src/mcp_prompt_broker/profile_parser.py` - Added `_merge_profile_weights()`, `_resolve_extends()`, `_check_circular_extends()`, `_get_extends_order()`
- `tests/test_keyword_inheritance.py` - 13 new tests
- `docs/DEVELOPER_GUIDE.md` - Added keyword inheritance documentation

**Key changes:**
1. Profiles with `extends` now inherit `weights.keywords` from parent
2. Multi-level extends chains are supported (A → B → C)
3. Circular extends are detected and reported as errors
4. Reload summary includes `extends_resolution` details
