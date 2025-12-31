# Keyword Inheritance for Complex Profiles - Implementation Plan

> Generated: 2026-01-01  
> Complexity: Medium  
> Estimated Effort: 2-3 hours  
> Related Report: [25_complexity_routing_score_ratio_analysis.md](25_complexity_routing_score_ratio_analysis.md)  
> Checklist: [25_keyword_inheritance_checklist.md](25_keyword_inheritance_checklist.md)

---

## 1. Current State Snapshot

### Problem Summary

Při routování promptu:
```
"Vytvoř komplexní implementační plán pro úpravu adresářové struktury workspace..."
```

Router vrací `implementation_planner` místo očekávaného `implementation_planner_complex`.

### Root Cause

| Aspekt | Stav |
|--------|------|
| `extends: implementation_planner` v YAML | ✅ Definováno |
| Keywords dědění | ❌ **Neimplementováno** |
| `implementation_planner` score | 38 |
| `implementation_planner_complex` score | 23 |
| Požadované minimum (80%) | 30.4 |
| Přepnutí na complex | ❌ Blokováno |

### Affected Code Paths

```
profile_parser.py
├── ProfileLoader._load_profiles()     ← zde se parsují profily
├── parse_profile_markdown()           ← zde se čte YAML včetně extends
└── InstructionProfile                 ← finální dataclass bez merge

router/
├── profile_router.py                  ← score() používá weights.keywords
└── hybrid_router.py                   ← complexity adjustment logika
```

---

## 2. Goal and Scope Definition

### Goal

Implementovat dědění `weights.keywords` z rodičovského profilu při použití `extends`, aby komplexní varianty měly dostatečné skóre pro aktivaci complexity routing.

### In Scope

- [x] Keyword inheritance (`weights.keywords`)
- [x] Merge logika (child overrides parent)
- [x] Circular dependency detection
- [x] Unit testy
- [x] Integrace s hot-reload

### Out of Scope

- Dědění jiných polí (`required`, `utterances`, atd.) — budoucí rozšíření
- Změna `COMPLEX_VARIANT_MIN_SCORE_RATIO` — workaround, ne řešení
- Modifikace existujících profilů — pouze systémová změna

---

## 3. Architecture / Flow Diagram

### Before (Current)

```
┌─────────────────────────────────┐
│     parse_profile_markdown()    │
│  ┌───────────────────────────┐  │
│  │ YAML: extends: parent     │  │
│  │ weights.keywords: {...}   │──┼──► InstructionProfile(keywords=child_only)
│  └───────────────────────────┘  │
└─────────────────────────────────┘
         ↓
    Parent keywords IGNORED
```

### After (Proposed)

```
┌─────────────────────────────────────────────────────────┐
│                  ProfileLoader._load_profiles()          │
│  ┌─────────────────┐    ┌─────────────────┐             │
│  │  Parent Profile │    │  Child Profile  │             │
│  │  keywords: {A}  │    │  extends: parent│             │
│  └────────┬────────┘    │  keywords: {B}  │             │
│           │             └────────┬────────┘             │
│           │                      │                      │
│           └──────────┬───────────┘                      │
│                      ▼                                  │
│            ┌─────────────────┐                          │
│            │  _merge_weights │                          │
│            │  {A} + {B} = {C}│                          │
│            └────────┬────────┘                          │
│                     ▼                                   │
│         InstructionProfile(keywords={C})                │
└─────────────────────────────────────────────────────────┘
```

### Merge Strategy

```python
merged_keywords = {
    **parent.weights.get("keywords", {}),  # Base
    **child.weights.get("keywords", {}),   # Override
}
```

---

## 4. Phased Implementation Steps

### Phase 1: Core Merge Logic

**File:** `src/mcp_prompt_broker/profile_parser.py`

```python
def _merge_profile_weights(
    parent_weights: Mapping[str, Mapping[str, int]],
    child_weights: Mapping[str, Mapping[str, int]],
) -> Dict[str, Dict[str, int]]:
    """Merge parent and child weights, with child taking precedence.
    
    Args:
        parent_weights: Weights from parent profile (extends target)
        child_weights: Weights from child profile
        
    Returns:
        Merged weights dictionary
    """
    merged: Dict[str, Dict[str, int]] = {}
    
    # Start with parent
    for key, value_dict in parent_weights.items():
        merged[key] = dict(value_dict)
    
    # Override/extend with child
    for key, value_dict in child_weights.items():
        if key in merged:
            merged[key].update(value_dict)
        else:
            merged[key] = dict(value_dict)
    
    return merged
```

### Phase 2: Integration into ProfileLoader

**File:** `src/mcp_prompt_broker/profile_parser.py`

Modify `_load_profiles()` to:

1. First pass: Parse all profiles
2. Build dependency graph from `extends`
3. Topological sort (parents before children)
4. Second pass: Merge weights for profiles with `extends`

```python
def _resolve_extends(self) -> None:
    """Resolve extends relationships and merge inherited weights."""
    for name, parsed in self._parsed_profiles.items():
        extends = parsed.yaml_metadata.get("extends")
        if not extends:
            continue
        
        parent = self._parsed_profiles.get(extends)
        if not parent:
            self._load_errors.append(f"Profile {name} extends unknown profile: {extends}")
            continue
        
        # Merge weights
        merged_weights = _merge_profile_weights(
            parent.profile.weights,
            parsed.profile.weights,
        )
        
        # Create new profile with merged weights
        parsed._profile = InstructionProfile(
            name=parsed.profile.name,
            instructions=parsed.profile.instructions,
            required=parsed.profile.required,
            weights=merged_weights,
            default_score=parsed.profile.default_score,
            fallback=parsed.profile.fallback,
            utterances=parsed.profile.utterances,
            utterance_threshold=parsed.profile.utterance_threshold,
            min_match_ratio=parsed.profile.min_match_ratio,
        )
```

### Phase 3: Circular Dependency Check

```python
def _check_circular_extends(self) -> List[str]:
    """Detect circular extends dependencies.
    
    Returns:
        List of error messages for circular dependencies.
    """
    errors = []
    for name in self._parsed_profiles:
        visited = set()
        current = name
        
        while current:
            if current in visited:
                errors.append(f"Circular extends detected: {name} -> ... -> {current}")
                break
            visited.add(current)
            
            parsed = self._parsed_profiles.get(current)
            if not parsed:
                break
            current = parsed.yaml_metadata.get("extends")
    
    return errors
```

---

## 5. Risk Analysis with Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Circular extends | Low | High | Detect and report error |
| Missing parent profile | Low | Medium | Log warning, skip merge |
| Performance regression | Low | Low | Single-pass merge, O(n) |
| Breaking existing profiles | Medium | High | Unit tests, integration tests |
| Hot-reload inconsistency | Low | Medium | Clear cache before reload |

---

## 6. Testing & Validation Strategy

### Unit Tests

```python
# tests/test_keyword_inheritance.py

def test_keywords_inherited_from_parent():
    """Child profile inherits keywords from parent."""
    # Setup: Create parent and child profiles
    # Assert: Child has merged keywords

def test_child_keywords_override_parent():
    """Child keywords take precedence over parent."""
    # Setup: Both have same keyword with different weights
    # Assert: Child weight is used

def test_circular_extends_detected():
    """Circular extends raises error."""
    # Setup: A extends B, B extends A
    # Assert: Error reported

def test_missing_parent_handled():
    """Missing parent profile logs warning."""
    # Setup: Child extends non-existent parent
    # Assert: Warning logged, child works independently
```

### Integration Test

```python
def test_complex_profile_routing():
    """Complex prompt routes to _complex variant after keyword inheritance."""
    prompt = "Vytvoř komplexní implementační plán pro úpravu..."
    
    loader = get_profile_loader()
    router = get_router(loader.profiles)
    
    parsed = analyze_prompt(prompt)
    enhanced = parsed.to_enhanced_metadata()
    result = router.route(enhanced)
    
    assert result.profile.name == "implementation_planner_complex"
```

---

## 7. Deliverables Summary

| Deliverable | Status | Location |
|-------------|--------|----------|
| `_merge_profile_weights()` function | TODO | `profile_parser.py` |
| `_resolve_extends()` method | TODO | `profile_parser.py` |
| `_check_circular_extends()` method | TODO | `profile_parser.py` |
| Unit tests | TODO | `tests/test_keyword_inheritance.py` |
| Updated documentation | TODO | `docs/DEVELOPER_GUIDE.md` |

---

## 8. Recommended Implementation Prompt

```
Implementuj dědění keywords v MCP Prompt Broker:

1. Přidej funkci `_merge_profile_weights()` do `profile_parser.py`
2. Přidej metodu `_resolve_extends()` do `ProfileLoader`
3. Přidej detekci cyklických závislostí `_check_circular_extends()`
4. Zavolej `_resolve_extends()` na konci `_load_profiles()`
5. Vytvoř unit testy v `tests/test_keyword_inheritance.py`
6. Ověř, že prompt "Vytvoř komplexní implementační plán..." vrací `implementation_planner_complex`

Akceptační kritéria:
- implementation_planner_complex má skóre ≥ 38
- Všechny existující testy procházejí
- Hot-reload funguje správně
```
