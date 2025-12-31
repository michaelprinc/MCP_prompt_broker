# Hybrid Profile Routing - Dependency Map

> Generated: 2025-12-31  
> Project: MCP Prompt Broker - Hybrid Routing Implementation

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           MCP Prompt Broker Server                          │
│                              (server.py)                                    │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
            ┌──────────────────────────────────────────────┐
            │              Router Factory                   │
            │         get_router() function                 │
            │                                               │
            │  ┌─────────────┐    ┌─────────────────────┐  │
            │  │ Feature Flag│───▶│ USE_SEMANTIC_ROUTING│  │
            │  └──────┬──────┘    └─────────────────────┘  │
            │         │                                     │
            │    ┌────┴────┐                               │
            │    ▼         ▼                               │
            │ ┌─────┐   ┌──────┐                           │
            │ │ OFF │   │  ON  │                           │
            │ └──┬──┘   └──┬───┘                           │
            └────┼─────────┼───────────────────────────────┘
                 │         │
                 ▼         ▼
    ┌────────────────┐   ┌─────────────────────────────────┐
    │ ProfileRouter  │   │      HybridProfileRouter        │
    │  (existing)    │   │          (NEW)                  │
    │                │   │                                 │
    │ - Keyword only │   │ - Keyword + Semantic            │
    │ - is_match()   │   │ - match_score()                 │
    │ - score()      │   │ - _compute_semantic_score()     │
    └───────┬────────┘   └──────────────┬──────────────────┘
            │                           │
            │                  ┌────────┴────────┐
            │                  ▼                 ▼
            │      ┌─────────────────┐  ┌─────────────────┐
            │      │  Keyword Scorer │  │ Semantic Scorer │
            │      │   (existing)    │  │     (NEW)       │
            │      └────────┬────────┘  └────────┬────────┘
            │               │                    │
            └───────────────┴────────────────────┘
                            │
                            ▼
            ┌───────────────────────────────────────┐
            │          InstructionProfile           │
            │            (profiles.py)              │
            │                                       │
            │  Existing Fields:                     │
            │  - name: str                          │
            │  - instructions: str                  │
            │  - required: Mapping                  │
            │  - weights: Mapping                   │
            │  - default_score: int                 │
            │  - fallback: bool                     │
            │                                       │
            │  NEW Fields (Phase 1):                │
            │  + utterances: tuple[str, ...]        │
            │  + utterance_threshold: float = 0.7   │
            │  + min_match_ratio: float = 0.5       │
            │                                       │
            │  NEW Methods:                         │
            │  + match_score() -> float             │
            │  ~ is_match() -> bool (wrapper)       │
            └───────────────────────────────────────┘
                            │
                            ▼
            ┌───────────────────────────────────────┐
            │          Profile Parser               │
            │       (profile_parser.py)             │
            │                                       │
            │  - parse_profile_markdown()           │
            │  + parse utterances field             │
            │  + parse threshold fields             │
            └───────────────────────────────────────┘
                            │
                            ▼
            ┌───────────────────────────────────────┐
            │       copilot-profiles/*.md           │
            │          (45+ profiles)               │
            │                                       │
            │  YAML Frontmatter:                    │
            │  ---                                  │
            │  name: profile_name                   │
            │  + utterances:                        │
            │  +   - "Example prompt 1"             │
            │  +   - "Example prompt 2"             │
            │  + utterance_threshold: 0.7           │
            │  + min_match_ratio: 0.5               │
            │  ---                                  │
            └───────────────────────────────────────┘
```

---

## Semantic Layer Architecture (Phase 2)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         HybridProfileRouter                                 │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              ▼                    ▼                    ▼
    ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
    │ Keyword Scoring │  │ Semantic Scoring│  │ Combined Score  │
    │                 │  │                 │  │                 │
    │ profile.score() │  │ cosine_sim()    │  │ α×semantic +    │
    │ match_score()   │  │ embedding match │  │ (1-α)×keyword   │
    └────────┬────────┘  └────────┬────────┘  └────────┬────────┘
             │                    │                    │
             │                    ▼                    │
             │      ┌─────────────────────────┐        │
             │      │    SemanticScorer       │        │
             │      │  (semantic_scorer.py)   │        │
             │      │                         │        │
             │      │ - model: SentenceTransf │        │
             │      │ - utterance_cache: dict │        │
             │      │                         │        │
             │      │ + encode(prompt)        │        │
             │      │ + similarity(p, profile)│        │
             │      └────────────┬────────────┘        │
             │                   │                     │
             │      ┌────────────┴────────────┐        │
             │      ▼                         ▼        │
             │ ┌──────────────┐    ┌──────────────────┐│
             │ │ Embedding    │    │ Utterance Cache  ││
             │ │ Model        │    │                  ││
             │ │              │    │ {profile_name:   ││
             │ │ all-MiniLM-  │    │  [emb1, emb2,..]}││
             │ │ L6-v2 (80MB) │    │                  ││
             │ └──────────────┘    └──────────────────┘│
             │                                         │
             └─────────────────────────────────────────┘
```

---

## Internal Dependencies

| Component | Depends On | Depended By | Coupling |
|-----------|------------|-------------|----------|
| `server.py` | ProfileRouter, ProfileLoader | MCP Protocol | High |
| `ProfileRouter` | InstructionProfile, EnhancedMetadata | server.py | High |
| `HybridProfileRouter` (NEW) | ProfileRouter, SemanticScorer | server.py | Medium |
| `SemanticScorer` (NEW) | sentence-transformers | HybridProfileRouter | Low |
| `InstructionProfile` | - | ProfileRouter, Parser | High |
| `profile_parser.py` | InstructionProfile, YAML | ProfileLoader | High |
| `metadata/parser.py` | - | server.py | Medium |

---

## External Dependencies

| Dependency | Version | Purpose | Required | Fallback |
|------------|---------|---------|----------|----------|
| `mcp` | ^1.0.0 | MCP Protocol | ✅ Yes | None |
| `PyYAML` | ≥6.0 | Profile parsing | ✅ Yes | None |
| `numpy` | ≥1.24.0 | Vector operations | ✅ Yes | None |
| `sentence-transformers` | ≥2.2.0 | Embeddings | ❌ Optional | Keyword-only mode |
| `scikit-learn` | ≥1.3.0 | Metrics, similarity | ❌ Optional | Basic numpy impl |
| `pytest` | ≥7.0.0 | Testing | ✅ Yes (dev) | None |

---

## Modification Impact Matrix

| If you change... | You must also update... | Risk Level |
|------------------|-------------------------|------------|
| `InstructionProfile` dataclass | `profile_parser.py`, all tests | 🔴 High |
| `ProfileRouter.route()` | `server.py`, integration tests | 🔴 High |
| Profile YAML schema | All 45+ `.md` profiles | 🟡 Medium |
| `analyze_prompt()` | Router tests, parser tests | 🟡 Medium |
| `SemanticScorer` | `HybridProfileRouter` | 🟢 Low |
| Embedding model name | Cache rebuild needed | 🟢 Low |
| Feature flags | Environment config, docs | 🟢 Low |

---

## Build/Test Order

```
1. src/mcp_prompt_broker/config/profiles.py
   └── No dependencies, foundation layer
   
2. src/mcp_prompt_broker/profile_parser.py
   └── Depends on: profiles.py
   
3. src/mcp_prompt_broker/metadata/parser.py
   └── No router dependencies
   
4. src/mcp_prompt_broker/router/profile_router.py
   └── Depends on: profiles.py, metadata/parser.py
   
5. src/mcp_prompt_broker/router/semantic_scorer.py (NEW)
   └── Depends on: sentence-transformers (optional)
   
6. src/mcp_prompt_broker/router/hybrid_router.py (NEW)
   └── Depends on: profile_router.py, semantic_scorer.py
   
7. src/mcp_prompt_broker/router/evaluation.py (NEW)
   └── Depends on: profile_router.py or hybrid_router.py
   
8. src/mcp_prompt_broker/server.py
   └── Depends on: all router modules

Test order:
1. tests/test_profiles.py
2. tests/test_profile_parser.py
3. tests/test_metadata_parser.py
4. tests/test_profile_router.py
5. tests/test_semantic_scorer.py (NEW)
6. tests/test_hybrid_router.py (NEW)
7. tests/test_evaluation.py (NEW)
8. tests/test_routing_benchmark.py (NEW)
9. tests/test_mcp_server_validation.py
```

---

## Risk Dependencies

| Risk | Affected Components | Detection | Mitigation |
|------|---------------------|-----------|------------|
| Embedding model not installed | HybridProfileRouter | ImportError | Fallback to ProfileRouter |
| Embedding latency > 100ms | server.py response time | Monitoring | Pre-compute cache |
| Profile parse error | ProfileLoader | Exception logging | Skip invalid, log error |
| Utterance quality poor | Semantic scores | Benchmark accuracy | Minimum 5 utterances rule |
| YAML schema change | All profiles | Parser tests | Backward compat fields |

---

## Environment Configuration

```bash
# Feature Flags
USE_SEMANTIC_ROUTING=false      # Enable hybrid routing
SEMANTIC_ROUTING_ALPHA=0.5      # Weight: 0=keyword, 1=semantic
SEMANTIC_MODEL_NAME=all-MiniLM-L6-v2  # Embedding model

# Performance
SEMANTIC_CACHE_ENABLED=true     # Cache utterance embeddings
SEMANTIC_BATCH_SIZE=32          # Batch size for encoding

# Debugging
ROUTING_DEBUG=false             # Log routing decisions
BENCHMARK_MODE=false            # Run in benchmark mode
```

---

## File Structure After Implementation

```
src/mcp_prompt_broker/
├── __init__.py
├── server.py                    # Modified: feature flag handling
├── config/
│   └── profiles.py              # Modified: new fields + match_score()
├── metadata/
│   └── parser.py                # Unchanged
├── router/
│   ├── __init__.py              # Modified: export new classes
│   ├── profile_router.py        # Unchanged (base)
│   ├── hybrid_router.py         # NEW: HybridProfileRouter
│   ├── semantic_scorer.py       # NEW: SemanticScorer
│   ├── evaluation.py            # NEW: Benchmark evaluation
│   └── optimization.py          # NEW: Threshold optimization
├── profile_parser.py            # Modified: parse new fields
└── copilot-profiles/
    └── *.md                     # Modified: add utterances

tests/
├── fixtures/
│   └── routing_benchmark.yaml   # NEW: 50+ test cases
├── test_hybrid_router.py        # NEW
├── test_semantic_scorer.py      # NEW
├── test_evaluation.py           # NEW
├── test_routing_benchmark.py    # NEW
├── test_match_score.py          # NEW
└── conftest.py                  # Modified: benchmark fixtures

docs/
├── HYBRID_ROUTING_IMPLEMENTATION_PLAN.md  # NEW
├── HYBRID_ROUTING_CHECKLIST.md            # NEW
├── HYBRID_ROUTING_DEPENDENCY_MAP.md       # NEW (this file)
├── USER_GUIDE.md                          # Updated
└── DEVELOPER_GUIDE.md                     # Updated

scripts/
└── optimize_thresholds.py       # NEW
```

---

*Generated by Implementation Planner Complex Profile*
