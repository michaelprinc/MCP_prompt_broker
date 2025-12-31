# Hybrid Profile Routing - Implementation Plan

> Generated: 2025-12-31  
> Complexity: **Complex/Critical**  
> Estimated Total Effort: **40-60 hodin (5-8 pracovních dní)**  
> Teams Involved: MCP Prompt Broker Core Team  
> Approval Required: **Yes (před Fází 2 - semantic layer)**  
> Source: [reports/20_profile_routing_analysis_and_recommendations.md](../reports/20_profile_routing_analysis_and_recommendations.md)

---

## 📋 Executive Summary

Tento plán implementuje **hybridní routing systém** pro MCP Prompt Broker, který kombinuje:
- Stávající keyword-based matching
- Nový semantic matching s embeddings
- Softened matching (0-1 score místo boolean)
- Systematický benchmark suite

### Cílové metriky

| Metrika | Současný stav | Cíl po Fázi 1 | Cíl po Fázi 3 |
|---------|---------------|---------------|---------------|
| Accuracy | ~60% | ≥75% | ≥85% |
| Fallback rate | ~25% | ≤15% | ≤10% |
| Critical profile recall | ~70% | ≥90% | ≥95% |
| Avg. confidence | 70% | ≥80% | ≥85% |

---

## 🔍 Pre-Implementation Analysis

### Stakeholders

| Stakeholder | Interest Level | Update Frequency | Channel |
|-------------|----------------|------------------|---------|
| MCP Server Users | High | On milestone | Release notes |
| Companion Agent | High | Daily | Git commits |
| Copilot Integration | Medium | Weekly | Summary |

### Dependencies

| Dependency | Version | Purpose | Status |
|------------|---------|---------|--------|
| sentence-transformers | ≥2.2.0 | Embedding model | 🔴 New |
| numpy | ≥1.24.0 | Vector operations | ✅ Existing |
| scikit-learn | ≥1.3.0 | Cosine similarity, metrics | 🔴 New (optional) |
| pytest | ≥7.0.0 | Testing | ✅ Existing |
| PyYAML | ≥6.0 | Profile parsing | ✅ Existing |

### Breaking Changes Assessment

| Change | Impact | Mitigation |
|--------|--------|------------|
| `is_match()` → `match_score()` | Medium | Keep `is_match()` as wrapper |
| New `utterances` field | Low | Optional field, backward compatible |
| Hybrid scoring | Medium | Feature flag for gradual rollout |
| New dependencies | Low | Optional semantic layer |

### Rollback Strategy

| Phase | Rollback Method | Time to Rollback |
|-------|-----------------|------------------|
| Fáze 1 | `git revert` + keep old `is_match()` | < 5 min |
| Fáze 2 | Feature flag `USE_SEMANTIC_ROUTING=false` | Immediate |
| Fáze 3 | Revert threshold config | < 2 min |

---

## 📊 Dependency Map

```
                    ┌─────────────────────────────────┐
                    │     MCP Server (server.py)      │
                    └───────────────┬─────────────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              ▼                     ▼                     ▼
    ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
    │ Metadata Parser │   │  Profile Router │   │ Profile Loader  │
    │   (parser.py)   │   │(profile_router) │   │(profile_parser) │
    └────────┬────────┘   └────────┬────────┘   └────────┬────────┘
             │                     │                     │
             │    ┌────────────────┴──────────┐          │
             │    ▼                           ▼          │
             │  ┌─────────────────┐ ┌─────────────────┐  │
             │  │ Keyword Scoring │ │ Semantic Scorer │  │
             │  │   (existing)    │ │   (NEW: Fáze 2) │  │
             │  └─────────────────┘ └────────┬────────┘  │
             │                               │           │
             │                    ┌──────────┴───────┐   │
             │                    ▼                  ▼   │
             │         ┌─────────────────┐ ┌─────────────────┐
             │         │ Embedding Model │ │ Utterance Cache │
             │         │(sentence-trans.)│ │   (NEW: Fáze 2) │
             │         └─────────────────┘ └─────────────────┘
             │
             └──────────────────────┐
                                    ▼
                    ┌─────────────────────────────────┐
                    │        InstructionProfile       │
                    │         (profiles.py)           │
                    │  ┌─────────────────────────┐    │
                    │  │ + utterances (NEW)      │    │
                    │  │ + utterance_threshold   │    │
                    │  │ + match_score() (NEW)   │    │
                    │  └─────────────────────────┘    │
                    └─────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
          ┌─────────────────┐             ┌─────────────────┐
          │  copilot-       │             │  Benchmark      │
          │  profiles/*.md  │             │  Suite (NEW)    │
          └─────────────────┘             └─────────────────┘
```

### Modification Impact Matrix

| If you change... | You must also update... |
|------------------|-------------------------|
| `InstructionProfile` dataclass | `profile_parser.py`, tests |
| `ProfileRouter.route()` | `server.py`, integration tests |
| Profile YAML schema | All 45+ profile `.md` files |
| `analyze_prompt()` | Router tests, parser tests |
| Embedding model | Utterance cache, benchmarks |

---

## 🚨 Risk Register

### R-001: Embedding Model Latency

| Attribute | Value |
|-----------|-------|
| **Category** | Technical |
| **Probability** | Medium (30-70%) |
| **Impact** | High |
| **Risk Score** | 6/10 |
| **Owner** | Core Team |
| **Status** | Open |

**Description:**  
Embedding model inference může zvýšit latenci routing rozhodnutí z <10ms na 50-200ms.

**Mitigation Strategy:**
1. Pre-compute utterance embeddings při startu serveru (cache)
2. Použít lightweight model (all-MiniLM-L6-v2 = 80MB, ~10ms inference)
3. Async embedding computation
4. Feature flag pro fallback na keyword-only routing

**Contingency Plan:**  
Pokud latency > 100ms: vypnout semantic layer pomocí `USE_SEMANTIC_ROUTING=false`

---

### R-002: Breaking Changes v Profile Schema

| Attribute | Value |
|-----------|-------|
| **Category** | Operational |
| **Probability** | Low (<30%) |
| **Impact** | Medium |
| **Risk Score** | 3/10 |
| **Owner** | Core Team |
| **Status** | Open |

**Description:**  
Nové `utterances` field může způsobit parsing errory u stávajících profilů.

**Mitigation Strategy:**
1. Pole `utterances` je volitelné s defaultem `tuple()`
2. Backward compatible parser
3. Postupná migrace profilů

---

### R-003: Nedostatečná kvalita utterance samples

| Attribute | Value |
|-----------|-------|
| **Category** | Technical |
| **Probability** | Medium (30-70%) |
| **Impact** | Medium |
| **Risk Score** | 5/10 |
| **Owner** | Core Team |
| **Status** | Open |

**Description:**  
Nekvalitní utterance samples mohou vést k horším výsledkům než keyword matching.

**Mitigation Strategy:**
1. Benchmark porovná keyword-only vs hybrid
2. Minimum 5 utterances per profil pro aktivaci semantic matchingu
3. A/B testing v produkci pomocí feature flag

---

### Risk Response Matrix

| Risk ID | Response Type | Action | Due Date |
|---------|---------------|--------|----------|
| R-001 | Mitigate | Implementovat caching + lightweight model | Fáze 2 |
| R-002 | Avoid | Backward compatible schema | Fáze 1 |
| R-003 | Mitigate | Quality benchmarks + minimum utterances | Fáze 3 |

---

## ✅ Implementation Checklist

### Pre-Implementation
**Owner: Core Team | Estimated: 4 hours | Status: ⬜**

#### Environment Setup
- [ ] Vytvořit feature branch `feature/hybrid-routing`
  - Acceptance: Branch exists, CI passes
- [ ] Připravit development environment
  - Acceptance: All tests pass locally
- [ ] Definovat feature flags
  - `USE_SEMANTIC_ROUTING`: Default OFF
  - `SEMANTIC_ROUTING_ALPHA`: Default 0.5

#### Dependencies Resolution
- [ ] Přidat sentence-transformers do pyproject.toml (optional)
  - Acceptance: `pip install .[semantic]` works
- [ ] Přidat scikit-learn pro metriky (optional)
  - Acceptance: Benchmark suite runs

---

### Phase 1: Foundation (12-16 hours)
**Owner: Core Team | Dependencies: Pre-Implementation | Status: ⬜**

#### 1.1 Rozšíření InstructionProfile
- [ ] Přidat `utterances: tuple[str, ...]` field
  - File: `src/mcp_prompt_broker/config/profiles.py`
  - Tests: `tests/test_profile_parser.py`
  - Acceptance: Field parsuje z YAML, default `tuple()`
  - Rollback: Remove field, revert

- [ ] Přidat `utterance_threshold: float = 0.7` field
  - File: `src/mcp_prompt_broker/config/profiles.py`
  - Acceptance: Konfigurovatelné per-profil

- [ ] Přidat `min_match_ratio: float = 0.5` field
  - File: `src/mcp_prompt_broker/config/profiles.py`
  - Acceptance: Soft matching support

#### 1.2 Implementace match_score()
- [ ] Vytvořit `match_score(metadata) -> float` metodu
  - File: `src/mcp_prompt_broker/config/profiles.py`
  - Tests: `tests/test_match_score.py`
  - Acceptance: Returns 0-1, handles all edge cases
  - Rollback: Remove method

- [ ] Upravit `is_match()` jako wrapper nad `match_score()`
  - Acceptance: `is_match() == (match_score() >= min_match_ratio)`
  - Rollback: Revert to original implementation

#### 1.3 Rozšíření Profile Parser
- [ ] Parsovat `utterances` z YAML frontmatter
  - File: `src/mcp_prompt_broker/profile_parser.py`
  - Tests: `tests/test_profile_parser.py`
  - Acceptance: List of strings → tuple

- [ ] Parsovat `utterance_threshold` a `min_match_ratio`
  - Acceptance: Float values with defaults

#### 1.4 Přidat utterances do klíčových profilů (10 profilů)
- [ ] `codex_cli.md` - 5+ utterances
- [ ] `python_code_generation.md` - 5+ utterances
- [ ] `creative_brainstorm.md` - 5+ utterances
- [ ] `technical_support.md` - 5+ utterances
- [ ] `privacy_sensitive.md` - 5+ utterances
- [ ] `general_default.md` - 5+ utterances
- [ ] `mcp_server_testing_and_validation.md` - 5+ utterances
- [ ] `implementation_planner.md` - 5+ utterances
- [ ] `security_compliance_reviewer.md` - 5+ utterances
- [ ] `documentation_diataxis.md` - 5+ utterances
  - Acceptance: Each profile has min 5 quality utterances
  - Directory: `src/mcp_prompt_broker/copilot-profiles/`

#### 1.5 Vytvořit Benchmark Dataset
- [ ] Vytvořit `tests/fixtures/routing_benchmark.yaml`
  - Content: 50+ prompt-profile pairs
  - Acceptance: Covers all major profiles
  - Format: YAML with id, prompt, expected_profile, tags

- [ ] Implementovat benchmark loader
  - File: `tests/conftest.py`
  - Acceptance: `pytest.fixture` for benchmark cases

---

### Phase 2: Semantic Layer (16-20 hours)
**Owner: Core Team | Dependencies: Phase 1 complete | Status: ⬜**

#### 2.1 Embedding Infrastructure
- [ ] Vytvořit `SemanticScorer` class
  - File: `src/mcp_prompt_broker/router/semantic_scorer.py`
  - Tests: `tests/test_semantic_scorer.py`
  - Acceptance: Loads model, computes embeddings

- [ ] Implementovat utterance embedding cache
  - Acceptance: Embeddings computed once at startup
  - Performance: < 5 seconds for 45 profiles × 5 utterances

- [ ] Lazy loading embedding modelu
  - Acceptance: Model loaded only when semantic routing enabled

#### 2.2 Hybrid Router Implementation
- [ ] Vytvořit `HybridProfileRouter` class
  - File: `src/mcp_prompt_broker/router/hybrid_router.py`
  - Tests: `tests/test_hybrid_router.py`
  - Acceptance: Combines keyword + semantic scores

- [ ] Implementovat `_compute_semantic_score()` metodu
  - Acceptance: Cosine similarity, returns 0-1

- [ ] Implementovat konfigurovatelné `alpha` (semantic weight)
  - Default: 0.5 (50% semantic, 50% keyword)
  - Acceptance: Env var `SEMANTIC_ROUTING_ALPHA`

#### 2.3 Integrace do MCP Serveru
- [ ] Přidat feature flag `USE_SEMANTIC_ROUTING`
  - File: `src/mcp_prompt_broker/server.py`
  - Default: `false`
  - Acceptance: Falls back to keyword-only when disabled

- [ ] Upravit `get_router()` pro hybrid router
  - Acceptance: Returns HybridRouter when enabled

- [ ] Přidat semantic metadata do response
  - Acceptance: Response includes `semantic_score`, `keyword_score`

#### 2.4 Per-Profile Thresholds
- [ ] Přidat `threshold` konfigurace do profilů
  - File: Profile YAML schema
  - Acceptance: `threshold.min_score`, `threshold.min_semantic_similarity`

- [ ] Implementovat threshold checking v routeru
  - Acceptance: Profile ignored if below threshold

---

### Phase 3: Evaluation & Optimization (10-14 hours)
**Owner: Core Team | Dependencies: Phase 2 complete | Status: ⬜**

#### 3.1 Evaluation Framework
- [ ] Implementovat `evaluate_routing()` funkci
  - File: `src/mcp_prompt_broker/router/evaluation.py`
  - Tests: `tests/test_evaluation.py`
  - Returns: `RoutingEvaluationResult` dataclass

- [ ] Implementovat confusion matrix generování
  - Acceptance: Matrix visualizable, exportable

- [ ] Implementovat per-profile metrics
  - Acceptance: Precision, recall, F1 per profile

#### 3.2 Benchmark Suite
- [ ] Vytvořit `tests/test_routing_benchmark.py`
  - Tests: Accuracy, fallback rate, critical recall
  - Acceptance: Automated CI test

- [ ] Přidat benchmark do CI pipeline
  - Acceptance: Fails if accuracy < 75%

- [ ] Vytvořit benchmark report generator
  - Output: Markdown report with metrics

#### 3.3 Threshold Optimization
- [ ] Implementovat `fit()` metodu pro threshold tuning
  - File: `src/mcp_prompt_broker/router/optimization.py`
  - Acceptance: Random search optimization

- [ ] Vytvořit optimization script
  - File: `scripts/optimize_thresholds.py`
  - Acceptance: Outputs optimal thresholds

#### 3.4 Documentation & Metrics
- [ ] Dokumentovat nové features v USER_GUIDE.md
- [ ] Přidat routing metrics do MCP tool response
- [ ] Vytvořit benchmark baseline dokumentaci
- [ ] Aktualizovat DEVELOPER_GUIDE.md

---

### Phase 4: Testing & QA (8-10 hours)
**Owner: Core Team | Dependencies: Phase 3 complete | Status: ⬜**

#### 4.1 Automated Testing
- [ ] Unit tests (≥80% coverage pro nový kód)
  - Files: `tests/test_*.py`
- [ ] Integration tests pro hybrid router
- [ ] Performance tests
  - Acceptance: Routing latency < 100ms (with semantic)
  - Acceptance: Routing latency < 10ms (keyword-only)

#### 4.2 Quality Assurance
- [ ] Manual testing s různými prompty
- [ ] Regression testing stávajících funkcí
- [ ] Edge case testing (prázdný prompt, unknown domain)

#### 4.3 Benchmark Validation
- [ ] Verify accuracy ≥ 75% (Phase 1 target)
- [ ] Verify accuracy ≥ 85% (Phase 3 target)
- [ ] Verify fallback rate < 15%
- [ ] Verify critical profile recall ≥ 90%

---

### Phase 5: Deployment (4-6 hours)
**Owner: Core Team | Dependencies: Phase 4 complete, QA sign-off | Status: ⬜**

#### 5.1 Staging Deployment
- [ ] Deploy to staging environment
- [ ] Run full benchmark suite
- [ ] Stakeholder review of results

#### 5.2 Production Rollout
- [ ] Feature flag enabled (OFF by default)
- [ ] Documentation published
- [ ] Release notes prepared

#### 5.3 Gradual Rollout
- [ ] Enable `USE_SEMANTIC_ROUTING=true` pro testing
- [ ] Monitor routing metrics
- [ ] Full rollout after 1 week stability

---

### Post-Deployment
**Owner: Core Team | Estimated: Ongoing | Status: ⬜**

- [ ] Monitor routing accuracy for 2 weeks
- [ ] Collect feedback from users
- [ ] Document lessons learned
- [ ] Plan utterance expansion for remaining profiles
- [ ] Consider advanced optimizations (fine-tuned embeddings)

---

## 📊 Sign-off Matrix

| Phase | Owner | Reviewer | Date | Status |
|-------|-------|----------|------|--------|
| Pre-Implementation | Core Team | - | | ⬜ |
| Phase 1: Foundation | Core Team | - | | ⬜ |
| Phase 2: Semantic Layer | Core Team | Senior Review | | ⬜ |
| Phase 3: Evaluation | Core Team | - | | ⬜ |
| Phase 4: Testing | Core Team | QA | | ⬜ |
| Phase 5: Deployment | Core Team | - | | ⬜ |
| Post-Deployment | Core Team | - | | ⬜ |

---

## 🔧 Feature Flag Strategy

| Flag Name | Default | Rollout Plan | Rollback Trigger |
|-----------|---------|--------------|------------------|
| `USE_SEMANTIC_ROUTING` | OFF | After Phase 2 testing | Accuracy < 70% |
| `SEMANTIC_ROUTING_ALPHA` | 0.5 | Tunable 0.3-0.7 | Based on benchmarks |
| `SEMANTIC_MODEL_NAME` | all-MiniLM-L6-v2 | Fixed initially | Performance issues |

---

## 📈 Monitoring & Success Criteria

### Key Metrics to Track

| Metric | Warning | Critical | Target |
|--------|---------|----------|--------|
| Routing accuracy | < 80% | < 70% | ≥ 85% |
| Fallback rate | > 15% | > 25% | ≤ 10% |
| Avg. latency (semantic) | > 80ms | > 150ms | < 50ms |
| Avg. latency (keyword) | > 15ms | > 30ms | < 10ms |
| Critical profile recall | < 90% | < 80% | ≥ 95% |

### Success Criteria for Each Phase

| Phase | Criterion | Metric |
|-------|-----------|--------|
| 1 | match_score() implemented | All tests pass |
| 1 | 10 profiles with utterances | Min 5 each |
| 1 | Benchmark dataset | 50+ test cases |
| 2 | Semantic scoring works | Embeddings computed |
| 2 | Hybrid router works | Accuracy ≥ 75% |
| 3 | Optimization works | Accuracy ≥ 85% |
| 4 | All tests pass | Coverage ≥ 80% |
| 5 | Production ready | Feature flag toggleable |

---

## 🚀 Recommended Implementation Prompts

### Prompt pro Fázi 1 - Foundation

```
This is a **complex, multi-phase implementation** based on:
- Implementation Plan: `docs/HYBRID_ROUTING_IMPLEMENTATION_PLAN.md`

**Phase to Execute:** Phase 1 - Foundation

**Pre-Conditions:**
- [ ] Feature branch `feature/hybrid-routing` created
- [ ] All current tests pass

**Tasks for This Phase:**
1. Extend InstructionProfile with utterances, utterance_threshold, min_match_ratio
2. Implement match_score() method
3. Update profile parser for new fields
4. Add utterances to 10 key profiles
5. Create benchmark dataset (50+ cases)

**Acceptance Criteria:**
- All new fields parse correctly from YAML
- match_score() returns 0-1 for all edge cases
- is_match() wraps match_score() correctly
- 10 profiles have 5+ quality utterances each
- Benchmark YAML has 50+ test cases

**Constraints:**
- Backward compatible - existing profiles must work
- No new required dependencies in this phase
- All tests must pass

Please proceed with Phase 1 implementation.
```

### Prompt pro Fázi 2 - Semantic Layer

```
This is a **complex, multi-phase implementation** based on:
- Implementation Plan: `docs/HYBRID_ROUTING_IMPLEMENTATION_PLAN.md`

**Phase to Execute:** Phase 2 - Semantic Layer

**Pre-Conditions:**
- [ ] Phase 1 completed and tested
- [ ] match_score() working correctly
- [ ] 10 profiles have utterances

**Tasks for This Phase:**
1. Create SemanticScorer class with embedding model
2. Implement utterance embedding cache
3. Create HybridProfileRouter class
4. Integrate feature flags
5. Add semantic metadata to response

**Risk Awareness:**
- Primary risk: Embedding latency
- Mitigation: Use lightweight model, pre-compute cache
- Rollback: USE_SEMANTIC_ROUTING=false

**Constraints:**
- sentence-transformers is optional dependency
- Must work without semantic layer when disabled
- Latency < 100ms with semantic, < 10ms without

Please proceed with Phase 2 implementation.
```

---

## 📝 Notes

- Tento plán je pro **planning only** - implementace používá samostatné prompts
- Feature flags umožňují bezpečný rollout a rychlý rollback
- Preferujeme malé, inkrementální změny před big-bang deploymentem
- Benchmark dataset je kritický pro měření úspěchu
- Semantic layer je volitelná - systém musí fungovat i bez ní

---

*Generated by Implementation Planner Complex Profile*  
*Based on: [20_profile_routing_analysis_and_recommendations.md](../reports/20_profile_routing_analysis_and_recommendations.md)*
