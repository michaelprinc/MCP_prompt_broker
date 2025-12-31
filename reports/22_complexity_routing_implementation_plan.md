# Complexity-Based Profile Routing - Implementation Plan

> Generated: 2024-12-31  
> Author: GitHub Copilot  
> Related Checklist: [22_complexity_routing_checklist.md](./22_complexity_routing_checklist.md)

---

## 1. Executive Summary

Tento dokument popisuje implementaci funkcionality **automatického preferování `_complex` variant profilů** u dlouhých nebo komplexních promptů v MCP Prompt Broker serveru.

### Cíl

Zlepšit kvalitu odpovědí tím, že dlouhé/komplexní prompty budou automaticky směrovány na podrobnější profily s příponou `_complex`, zatímco krátké/jednoduché prompty využijí stručnější základní profily.

### Scope

| In Scope | Out of Scope |
|----------|--------------|
| Rozšíření `ParsedMetadata` a `EnhancedMetadata` | Nové profily |
| Rozšíření `ProfileRouter` a `HybridProfileRouter` | Změna scoring algoritmu |
| Konfigurační ENV proměnné | UI změny |
| Unit a integration testy | Sémantický model pro komplexitu |

---

## 2. Current State Analysis

### 2.1 Existující komponenty

```
src/mcp_prompt_broker/
├── metadata/
│   └── parser.py           # ParsedMetadata, _estimate_complexity()
├── router/
│   ├── profile_router.py   # ProfileRouter, EnhancedMetadata
│   └── hybrid_router.py    # HybridProfileRouter
├── config/
│   └── profiles.py         # InstructionProfile
└── server.py               # MCP server tools
```

### 2.2 Současná detekce komplexity

```python
# parser.py - současná implementace
def _estimate_complexity(prompt: str) -> str:
    word_count = len(prompt.split())
    if word_count > 80:
        return "high"
    if word_count > 40:
        return "medium"
    if word_count > 15:
        return "low-medium"
    return "low"
```

**Omezení:**
- Pouze počet slov
- Nedetekuje klíčová slova indikující komplexitu
- Nevyužito při routingu

### 2.3 Existující párové profily

| Base Profile | Complex Variant | Status |
|--------------|-----------------|--------|
| `creative_brainstorm` | `creative_brainstorm_complex` | ✅ |
| `general_default` | `general_default_complex` | ✅ |
| `implementation_planner` | `implementation_planner_complex` | ✅ |
| `podman_container_management` | `podman_container_management_complex` | ✅ |
| `privacy_sensitive` | `privacy_sensitive_complex` | ✅ |
| `python_code_generation` | `python_code_generation_complex` | ✅ |
| `python_testing_revision` | `python_testing_revision_complex` | ✅ |
| `technical_support` | `technical_support_complex` | ✅ |

---

## 3. Architecture Design

### 3.1 Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         MCP Server                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌───────────────────┐    ┌───────────────┐ │
│  │    Prompt    │───▶│  MetadataParser   │───▶│ EnhancedMeta  │ │
│  │              │    │                   │    │               │ │
│  │              │    │ + complexity      │    │ + complexity  │ │
│  │              │    │ + prompt_length   │    │ + prompt_len  │ │
│  └──────────────┘    └───────────────────┘    └───────┬───────┘ │
│                                                        │         │
│                                                        ▼         │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    ProfileRouter                          │   │
│  │  ┌────────────────────────────────────────────────────┐  │   │
│  │  │                  route()                            │  │   │
│  │  │  1. Score all profiles                              │  │   │
│  │  │  2. Select best profile                             │  │   │
│  │  │  3. ──▶ _should_prefer_complex(metadata) ◀──        │  │   │
│  │  │  4. ──▶ _find_complex_variant(profile) ◀──          │  │   │
│  │  │  5. Return (adjusted) profile                       │  │   │
│  │  └────────────────────────────────────────────────────┘  │   │
│  │                                                           │   │
│  │  ┌─────────────────┐  ┌─────────────────────────────┐    │   │
│  │  │ _profile_pairs  │  │  ComplexityConfig           │    │   │
│  │  │ Dict[str, str]  │  │  - WORD_COUNT_THRESHOLD     │    │   │
│  │  │                 │  │  - KEYWORD_BONUS_THRESHOLD  │    │   │
│  │  │ base → complex  │  │  - MIN_SCORE_RATIO          │    │   │
│  │  └─────────────────┘  └─────────────────────────────┘    │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Sequence Diagram

```
User                MCP Server           Parser              Router
  │                     │                   │                   │
  │  get_profile(prompt)│                   │                   │
  │────────────────────▶│                   │                   │
  │                     │                   │                   │
  │                     │ analyze_prompt()  │                   │
  │                     │──────────────────▶│                   │
  │                     │                   │                   │
  │                     │ ParsedMetadata    │                   │
  │                     │◀──────────────────│                   │
  │                     │ (complexity,      │                   │
  │                     │  prompt_length)   │                   │
  │                     │                   │                   │
  │                     │ to_enhanced_meta()│                   │
  │                     │──────────────────▶│                   │
  │                     │                   │                   │
  │                     │              route(enhanced)          │
  │                     │──────────────────────────────────────▶│
  │                     │                   │                   │
  │                     │                   │    Score profiles │
  │                     │                   │    ───────────────│
  │                     │                   │                   │
  │                     │                   │  _should_prefer   │
  │                     │                   │  _complex()       │
  │                     │                   │    ───────────────│
  │                     │                   │                   │
  │                     │                   │  _find_complex    │
  │                     │                   │  _variant()       │
  │                     │                   │    ───────────────│
  │                     │                   │                   │
  │                     │              RoutingResult            │
  │                     │◀──────────────────────────────────────│
  │                     │              (adjusted profile)       │
  │                     │                   │                   │
  │  Profile + metadata │                   │                   │
  │◀────────────────────│                   │                   │
  │                     │                   │                   │
```

---

## 4. Detailed Implementation

### 4.1 Phase 1: Metadata Extension

#### 4.1.1 Complexity Keywords (`parser.py`)

```python
# Nová konstanta - přidat za TONE_KEYWORDS
COMPLEXITY_KEYWORDS: Mapping[str, int] = {
    # Explicitní indikátory vysoké komplexity
    "complex": 3,
    "enterprise": 3,
    "migration": 2,
    "refactor": 2,
    "refactoring": 2,
    "multi-module": 3,
    "microservices": 2,
    "architecture": 2,
    "scalable": 2,
    "distributed": 2,
    "infrastructure": 2,
    "cross-team": 2,
    "large-scale": 3,
    # České ekvivalenty
    "komplexní": 3,
    "migrace": 2,
    "architektura": 2,
    "velký projekt": 3,
}
```

#### 4.1.2 Enhanced Complexity Estimation (`parser.py`)

```python
def _estimate_complexity(prompt: str) -> tuple[str, int, int]:
    """Estimate complexity based on word count and keywords.
    
    Returns:
        Tuple of (complexity_level, word_count, keyword_bonus)
    """
    word_count = len(prompt.split())
    normalized = prompt.lower()
    
    # Keyword-based bonus
    keyword_bonus = sum(
        weight for keyword, weight in COMPLEXITY_KEYWORDS.items()
        if keyword in normalized
    )
    
    # Combined decision
    if word_count > 80 or keyword_bonus >= 4:
        return "high", word_count, keyword_bonus
    if word_count > 40 or keyword_bonus >= 2:
        return "medium", word_count, keyword_bonus
    if word_count > 15:
        return "low-medium", word_count, keyword_bonus
    return "low", word_count, keyword_bonus
```

#### 4.1.3 Extended ParsedMetadata (`parser.py`)

```python
@dataclass(frozen=True)
class ParsedMetadata:
    """Represents enriched metadata derived from the raw prompt."""

    prompt: str
    intent: str
    domain: str | None
    topics: frozenset[str] = field(default_factory=frozenset)
    sensitivity: str = "low"
    safety_score: int = 0
    tone: str = "neutral"
    complexity: str = "low"
    prompt_length: int = 0          # NOVÝ atribut
    complexity_keyword_bonus: int = 0  # NOVÝ atribut
```

#### 4.1.4 Extended EnhancedMetadata (`profile_router.py`)

```python
@dataclass(frozen=True)
class EnhancedMetadata:
    """Normalized metadata used to select instruction profiles."""

    prompt: str
    domain: str | None = None
    sensitivity: str | None = None
    language: str | None = None
    priority: str | None = None
    audience: str | None = None
    intent: str | None = None
    context_tags: frozenset[str] = field(default_factory=frozenset)
    complexity: str | None = None      # NOVÝ atribut
    prompt_length: int = 0             # NOVÝ atribut
```

### 4.2 Phase 2: Router Extension

#### 4.2.1 Configuration Module (`router/complexity_config.py`)

```python
"""Configuration for complexity-based profile routing."""
from __future__ import annotations

import os

# Feature toggle
COMPLEXITY_ROUTING_ENABLED = os.getenv(
    "MCP_COMPLEXITY_ROUTING", "true"
).lower() in ("true", "1", "yes")

# Profile naming convention
COMPLEX_SUFFIX = "_complex"

# Word count thresholds
WORD_COUNT_HIGH_THRESHOLD = int(os.getenv("MCP_COMPLEXITY_WORD_HIGH", "80"))
WORD_COUNT_MEDIUM_THRESHOLD = int(os.getenv("MCP_COMPLEXITY_WORD_MEDIUM", "40"))

# Keyword bonus thresholds
KEYWORD_BONUS_HIGH_THRESHOLD = 4
KEYWORD_BONUS_MEDIUM_THRESHOLD = 2

# Minimum score ratio for variant switching
COMPLEX_VARIANT_MIN_SCORE_RATIO = 0.8
SIMPLE_VARIANT_MIN_SCORE_RATIO = 0.9

# Complexity levels that trigger _complex preference
COMPLEX_PREFERENCE_LEVELS = frozenset({"high", "medium"})
SIMPLE_PREFERENCE_LEVELS = frozenset({"low"})
```

#### 4.2.2 Profile Pair Discovery (`profile_router.py`)

```python
class ProfileRouter:
    """Route prompts to instruction profiles using rule-based scoring."""

    def __init__(self, profiles: Sequence[InstructionProfile] | None = None):
        self.profiles = list(profiles or get_instruction_profiles())
        self._profile_pairs = self._build_profile_pairs()
    
    def _build_profile_pairs(self) -> dict[str, str]:
        """Build mapping of base profiles to their _complex variants."""
        pairs: dict[str, str] = {}
        profile_names = {p.name for p in self.profiles}
        
        for name in profile_names:
            if name.endswith(COMPLEX_SUFFIX):
                continue
            complex_name = f"{name}{COMPLEX_SUFFIX}"
            if complex_name in profile_names:
                pairs[name] = complex_name
        
        return pairs
    
    def _find_complex_variant(self, profile_name: str) -> InstructionProfile | None:
        """Find the _complex variant of a profile if it exists."""
        if profile_name.endswith(COMPLEX_SUFFIX):
            return None
        
        complex_name = self._profile_pairs.get(profile_name)
        if not complex_name:
            return None
        
        for profile in self.profiles:
            if profile.name == complex_name:
                return profile
        return None
    
    def _find_simple_variant(self, profile_name: str) -> InstructionProfile | None:
        """Find the base variant of a _complex profile."""
        if not profile_name.endswith(COMPLEX_SUFFIX):
            return None
        
        base_name = profile_name[:-len(COMPLEX_SUFFIX)]
        for profile in self.profiles:
            if profile.name == base_name:
                return profile
        return None
```

#### 4.2.3 Complexity Preference Logic (`profile_router.py`)

```python
    def _should_prefer_complex(self, metadata: EnhancedMetadata) -> bool:
        """Determine if _complex variant should be preferred."""
        if not COMPLEXITY_ROUTING_ENABLED:
            return False
        
        complexity = metadata.complexity
        prompt_length = metadata.prompt_length
        
        # Explicitní vysoká komplexita
        if complexity in COMPLEX_PREFERENCE_LEVELS:
            return True
        
        # Dlouhý prompt bez explicitní komplexity
        if prompt_length > WORD_COUNT_MEDIUM_THRESHOLD:
            return True
        
        return False
    
    def _should_prefer_simple(self, metadata: EnhancedMetadata) -> bool:
        """Determine if base (non-complex) variant should be preferred."""
        if not COMPLEXITY_ROUTING_ENABLED:
            return False
        
        complexity = metadata.complexity
        prompt_length = metadata.prompt_length
        
        # Krátký prompt s nízkou komplexitou
        if complexity in SIMPLE_PREFERENCE_LEVELS and prompt_length <= 30:
            return True
        
        return False
```

#### 4.2.4 Extended RoutingResult (`profile_router.py`)

```python
@dataclass(frozen=True)
class RoutingResult:
    """Result of routing including the matched profile and confidence."""

    profile: InstructionProfile
    score: int
    consistency: float
    complexity_adjusted: bool = False      # NOVÝ atribut
    original_profile_name: str | None = None  # NOVÝ atribut
```

#### 4.2.5 Modified route() Method (`profile_router.py`)

```python
    def route(self, metadata: EnhancedMetadata) -> RoutingResult:
        """Return the best instruction profile for the given metadata."""

        metadata_map = metadata.as_mutable()
        scored_matches: list[tuple[InstructionProfile, int]] = []
        fallback_profile: InstructionProfile | None = None

        for profile in self.profiles:
            if profile.fallback:
                fallback_profile = fallback_profile or profile

            if not profile.is_match(metadata_map):
                continue

            scored_matches.append((profile, profile.score(metadata_map)))

        if scored_matches:
            best_profile, best_score = max(scored_matches, key=lambda item: item[1])
            original_name: str | None = None
            complexity_adjusted = False
            
            # === NOVÁ LOGIKA: Komplexitní preference ===
            if COMPLEXITY_ROUTING_ENABLED:
                if self._should_prefer_complex(metadata):
                    # Preferovat _complex variantu
                    if not best_profile.name.endswith(COMPLEX_SUFFIX):
                        complex_variant = self._find_complex_variant(best_profile.name)
                        if complex_variant:
                            complex_score = complex_variant.score(metadata_map)
                            if complex_score >= best_score * COMPLEX_VARIANT_MIN_SCORE_RATIO:
                                original_name = best_profile.name
                                best_profile = complex_variant
                                best_score = complex_score
                                complexity_adjusted = True
                
                elif self._should_prefer_simple(metadata):
                    # Preferovat základní variantu
                    if best_profile.name.endswith(COMPLEX_SUFFIX):
                        simple_variant = self._find_simple_variant(best_profile.name)
                        if simple_variant:
                            simple_score = simple_variant.score(metadata_map)
                            if simple_score >= best_score * SIMPLE_VARIANT_MIN_SCORE_RATIO:
                                original_name = best_profile.name
                                best_profile = simple_variant
                                best_score = simple_score
                                complexity_adjusted = True
            # === KONEC NOVÉ LOGIKY ===
            
            consistency = self._normalize_consistency(
                best_score, [score for _, score in scored_matches]
            )
            return RoutingResult(
                best_profile, 
                best_score, 
                consistency,
                complexity_adjusted=complexity_adjusted,
                original_profile_name=original_name,
            )

        if fallback_profile:
            return RoutingResult(fallback_profile, fallback_profile.default_score, 100.0)

        raise ValueError("No matching profile and no fallback configured")
```

### 4.3 Phase 3: Server Integration

#### 4.3.1 Extended Response (`server.py`)

```python
# V call_tool() funkci, sekce get_profile/resolve_prompt
routing_info: Dict[str, Any] = {
    "score": routing.score,
    "consistency": routing.consistency,
    # NOVÉ: Komplexitní routing info
    "complexity_routing": {
        "enabled": COMPLEXITY_ROUTING_ENABLED,
        "adjusted": routing.complexity_adjusted,
        "original_profile": routing.original_profile_name,
    },
}
```

---

## 5. Testing Strategy

### 5.1 Unit Test Cases

| Test ID | Description | Input | Expected Output |
|---------|-------------|-------|-----------------|
| TC01 | Krátký simple prompt | "Sečti 2+2" | Base profile, no adjustment |
| TC02 | Dlouhý prompt (80+ slov) | Lorem ipsum 100 slov | `_complex` variant |
| TC03 | Krátký s keywords | "Enterprise architecture migration" | `_complex` variant |
| TC04 | Medium prompt bez keywords | 50 slov bez keywords | Base profile |
| TC05 | Profil bez _complex varianty | Prompt → `codex_cli` | `codex_cli` (unchanged) |
| TC06 | ENV disabled | `MCP_COMPLEXITY_ROUTING=false` | No adjustment |
| TC07 | Explicitní _complex má nižší skóre | Complex < 80% base | Base profile |

### 5.2 Integration Test Flow

```python
def test_complexity_routing_e2e():
    """E2E test through MCP server."""
    
    # Short prompt → base profile
    result = await call_tool("get_profile", {"prompt": "Vytvoř funkci"})
    assert not result["routing"]["complexity_routing"]["adjusted"]
    
    # Long prompt → complex profile
    long_prompt = "Potřebuji komplexní enterprise řešení..." * 20
    result = await call_tool("get_profile", {"prompt": long_prompt})
    assert result["routing"]["complexity_routing"]["adjusted"]
    assert "_complex" in result["profile"]["name"]
```

---

## 6. Rollback Procedure

### Immediate Rollback

```bash
# 1. Disable feature via environment
export MCP_COMPLEXITY_ROUTING=false

# 2. Restart MCP server
# (automatic in VS Code extension reload)
```

### Full Rollback

```bash
# Git revert if needed
git revert <commit-hash>
```

---

## 7. Deliverables

| Deliverable | File Path | Status |
|-------------|-----------|--------|
| Complexity keywords | `src/mcp_prompt_broker/metadata/parser.py` | 🔲 |
| Extended ParsedMetadata | `src/mcp_prompt_broker/metadata/parser.py` | 🔲 |
| Extended EnhancedMetadata | `src/mcp_prompt_broker/router/profile_router.py` | 🔲 |
| Complexity config | `src/mcp_prompt_broker/router/complexity_config.py` | 🔲 |
| Router extension | `src/mcp_prompt_broker/router/profile_router.py` | 🔲 |
| HybridRouter extension | `src/mcp_prompt_broker/router/hybrid_router.py` | 🔲 |
| Server integration | `src/mcp_prompt_broker/server.py` | 🔲 |
| Unit tests | `tests/test_complexity_routing.py` | 🔲 |
| Documentation | `docs/USER_GUIDE.md`, `docs/DEVELOPER_GUIDE.md` | 🔲 |

---

## 8. Recommended Implementation Prompt

Pro zahájení implementace použijte následující prompt:

```
Implementuj Fázi 1 z implementačního plánu "Complexity-Based Profile Routing":

1. Přidej COMPLEXITY_KEYWORDS konstantu do parser.py
2. Rozšiř _estimate_complexity() o detekci klíčových slov  
3. Přidej prompt_length a complexity_keyword_bonus do ParsedMetadata
4. Aktualizuj analyze_prompt() pro nové atributy
5. Rozšiř EnhancedMetadata o complexity a prompt_length
6. Aktualizuj to_enhanced_metadata() pro propagaci

Reference: reports/22_complexity_routing_implementation_plan.md
Checklist: reports/22_complexity_routing_checklist.md
```

---

## 9. Next Steps

Po schválení tohoto plánu:

1. ✅ Review implementačního plánu
2. ⏳ Implementace Fáze 1 (Metadata Extension)
3. ⏳ Implementace Fáze 2 (Router Extension)
4. ⏳ Implementace Fáze 3 (HybridRouter)
5. ⏳ Implementace Fáze 4 (Configuration)
6. ⏳ Implementace Fáze 5 (Testing)
7. ⏳ Implementace Fáze 6 (Documentation)
8. ⏳ Code review a merge

---

*Vytvořeno pomocí MCP Prompt Broker - Implementation Planner Profile*
