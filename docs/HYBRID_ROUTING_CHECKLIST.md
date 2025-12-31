# Hybrid Profile Routing - Implementation Checklist

> Generated: 2025-12-31  
> Complexity: Complex/Critical  
> Estimated Total Effort: 40-60 hours (5-8 pracovních dní)  
> Teams Involved: MCP Prompt Broker Core Team  
> Approval Required: Yes

---

## Pre-Implementation
**Owner: Core Team | Estimated: 4 hours | Status: ⬜**

### Environment Setup
- [ ] Vytvořit feature branch `feature/hybrid-routing`
  - Acceptance: Branch exists, CI passes
  - Command: `git checkout -b feature/hybrid-routing`
  - Dependencies: None

- [ ] Připravit development environment
  - Acceptance: All tests pass locally
  - Command: `pytest tests/ -v`
  - Dependencies: None

- [ ] Definovat feature flags v konfiguraci
  - Acceptance: Env vars documented
  - Flags:
    - `USE_SEMANTIC_ROUTING=false`
    - `SEMANTIC_ROUTING_ALPHA=0.5`
    - `SEMANTIC_MODEL_NAME=all-MiniLM-L6-v2`

### Dependencies Resolution
- [ ] Přidat sentence-transformers jako optional dependency
  - File: `pyproject.toml`
  - Acceptance: `pip install .[semantic]` works
  - Rollback: Remove from pyproject.toml

- [ ] Přidat scikit-learn pro metriky (optional)
  - File: `pyproject.toml`
  - Acceptance: Benchmark suite runs

---

## Phase 1: Foundation (12-16 hours)
**Owner: Core Team | Dependencies: Pre-Implementation | Status: ⬜**

### 1.1 Rozšíření InstructionProfile
- [ ] Přidat `utterances: tuple[str, ...]` field
  - File: `src/mcp_prompt_broker/config/profiles.py`
  - Tests: `tests/test_profile_parser.py`
  - Acceptance: Field parsuje z YAML, default `tuple()`
  - Rollback: Remove field, revert commit

- [ ] Přidat `utterance_threshold: float = 0.7` field
  - File: `src/mcp_prompt_broker/config/profiles.py`
  - Acceptance: Konfigurovatelné per-profil
  - Rollback: Remove field

- [ ] Přidat `min_match_ratio: float = 0.5` field
  - File: `src/mcp_prompt_broker/config/profiles.py`
  - Acceptance: Soft matching support
  - Rollback: Remove field

### 1.2 Implementace match_score()
- [ ] Vytvořit `match_score(metadata) -> float` metodu
  - File: `src/mcp_prompt_broker/config/profiles.py`
  - Tests: `tests/test_match_score.py`
  - Acceptance: Returns 0-1, handles edge cases
  - Rollback: Remove method

- [ ] Upravit `is_match()` jako wrapper nad `match_score()`
  - File: `src/mcp_prompt_broker/config/profiles.py`
  - Acceptance: `is_match() == (match_score() >= min_match_ratio)`
  - Rollback: Revert to original implementation

### 1.3 Rozšíření Profile Parser
- [ ] Parsovat `utterances` z YAML frontmatter
  - File: `src/mcp_prompt_broker/profile_parser.py`
  - Function: `parse_profile_markdown()`
  - Tests: `tests/test_profile_parser.py`
  - Acceptance: List → tuple conversion

- [ ] Parsovat `utterance_threshold` a `min_match_ratio`
  - File: `src/mcp_prompt_broker/profile_parser.py`
  - Acceptance: Float values with defaults

### 1.4 Přidat utterances do klíčových profilů

| Profile | File | Min Utterances | Status |
|---------|------|----------------|--------|
| codex_cli | `codex_cli.md` | 5 | ⬜ |
| python_code_generation | `python_code_generation.md` | 5 | ⬜ |
| creative_brainstorm | `creative_brainstorm.md` | 5 | ⬜ |
| technical_support | `technical_support.md` | 5 | ⬜ |
| privacy_sensitive | `privacy_sensitive.md` | 5 | ⬜ |
| general_default | `general_default.md` | 5 | ⬜ |
| mcp_server_testing | `mcp_server_testing_and_validation.md` | 5 | ⬜ |
| implementation_planner | `implementation_planner.md` | 5 | ⬜ |
| security_compliance | `security_compliance_reviewer.md` | 5 | ⬜ |
| documentation_diataxis | `documentation_diataxis.md` | 5 | ⬜ |

### 1.5 Vytvořit Benchmark Dataset
- [ ] Vytvořit `tests/fixtures/routing_benchmark.yaml`
  - Content: 50+ prompt-profile pairs
  - Acceptance: Covers all major profiles
  - Format:
    ```yaml
    test_cases:
      - id: "test_001"
        prompt: "..."
        expected_profile: "profile_name"
        min_score: 5
        tags: ["category"]
    ```

- [ ] Implementovat benchmark loader
  - File: `tests/conftest.py`
  - Acceptance: `@pytest.fixture` for benchmark cases

---

## Phase 2: Semantic Layer (16-20 hours)
**Owner: Core Team | Dependencies: Phase 1 | Status: ⬜**

### 2.1 Embedding Infrastructure
- [ ] Vytvořit `SemanticScorer` class
  - File: `src/mcp_prompt_broker/router/semantic_scorer.py`
  - Tests: `tests/test_semantic_scorer.py`
  - Acceptance: Loads model, computes embeddings
  - Rollback: Delete file

- [ ] Implementovat utterance embedding cache
  - Method: `_build_utterance_index()`
  - Acceptance: < 5s for 45 profiles × 5 utterances
  - Rollback: Disable caching

- [ ] Lazy loading embedding modelu
  - Acceptance: Model loaded only when needed
  - Rollback: Always load (acceptable)

### 2.2 Hybrid Router Implementation
- [ ] Vytvořit `HybridProfileRouter` class
  - File: `src/mcp_prompt_broker/router/hybrid_router.py`
  - Tests: `tests/test_hybrid_router.py`
  - Acceptance: Extends ProfileRouter
  - Rollback: Delete file, use ProfileRouter

- [ ] Implementovat `_compute_semantic_score()` metodu
  - Acceptance: Cosine similarity, returns 0-1
  - Performance: < 20ms per query

- [ ] Implementovat konfigurovatelné `alpha`
  - Default: 0.5
  - Env var: `SEMANTIC_ROUTING_ALPHA`
  - Range: 0.0 (keyword only) - 1.0 (semantic only)

### 2.3 Integrace do MCP Serveru
- [ ] Přidat feature flag handling
  - File: `src/mcp_prompt_broker/server.py`
  - Env var: `USE_SEMANTIC_ROUTING`
  - Default: `false`

- [ ] Upravit `get_router()` factory function
  - Returns: HybridRouter when enabled
  - Fallback: ProfileRouter when disabled

- [ ] Přidat semantic metadata do response
  - Fields: `semantic_score`, `keyword_score`, `combined_score`
  - Acceptance: Visible in JSON response

### 2.4 Per-Profile Thresholds
- [ ] Přidat `threshold` konfigurace do YAML schema
  - Fields: `min_score`, `min_semantic_similarity`
  - Acceptance: Parseable from profiles

- [ ] Implementovat threshold checking v routeru
  - Acceptance: Profile filtered if below threshold

---

## Phase 3: Evaluation & Optimization (10-14 hours)
**Owner: Core Team | Dependencies: Phase 2 | Status: ⬜**

### 3.1 Evaluation Framework
- [ ] Vytvořit `RoutingEvaluationResult` dataclass
  - File: `src/mcp_prompt_broker/router/evaluation.py`
  - Fields: accuracy, precision, recall, f1, confusion_matrix

- [ ] Implementovat `evaluate_routing()` funkci
  - Input: router, test_cases
  - Output: RoutingEvaluationResult

- [ ] Implementovat confusion matrix
  - Format: numpy array or dict
  - Visualization: ASCII or export to file

### 3.2 Benchmark Suite
- [ ] Vytvořit `tests/test_routing_benchmark.py`
  - Tests:
    - `test_minimum_accuracy()` - ≥80%
    - `test_no_critical_misroutes()`
    - `test_fallback_rate_threshold()` - <15%
    - `test_key_profile_recall()` - ≥75%

- [ ] Přidat benchmark do CI
  - File: `.github/workflows/test.yml` (if exists)
  - Acceptance: Fails if accuracy < 75%

- [ ] Vytvořit benchmark report generator
  - Output: `reports/benchmark_results.md`

### 3.3 Threshold Optimization
- [ ] Implementovat `fit()` metodu
  - File: `src/mcp_prompt_broker/router/optimization.py`
  - Algorithm: Random search
  - Acceptance: Improves accuracy

- [ ] Vytvořit optimization script
  - File: `scripts/optimize_thresholds.py`
  - Usage: `python scripts/optimize_thresholds.py`

### 3.4 Documentation
- [ ] Aktualizovat USER_GUIDE.md
  - Sections: Semantic routing, configuration
- [ ] Aktualizovat DEVELOPER_GUIDE.md
  - Sections: HybridRouter, SemanticScorer
- [ ] Vytvořit benchmark baseline dokumentaci

---

## Phase 4: Testing & QA (8-10 hours)
**Owner: Core Team | Dependencies: Phase 3 | Status: ⬜**

### 4.1 Automated Testing
- [ ] Unit tests pro nový kód
  - Coverage target: ≥80%
  - Files: All new modules

- [ ] Integration tests
  - File: `tests/test_integration.py`
  - Scenarios: Full routing flow

- [ ] Performance tests
  - Latency targets:
    - Semantic: < 100ms
    - Keyword: < 10ms

### 4.2 Manual Testing
- [ ] Testovat různé typy promptů
  - Czech prompts
  - English prompts
  - Mixed language
  - Edge cases (empty, very long)

- [ ] Regression testing
  - Stávající profily fungují
  - Backward compatibility

### 4.3 Benchmark Validation
- [ ] Accuracy ≥ 75% (Fáze 1 cíl)
- [ ] Accuracy ≥ 85% (Fáze 3 cíl)
- [ ] Fallback rate < 15%
- [ ] Critical profile recall ≥ 90%

---

## Phase 5: Deployment (4-6 hours)
**Owner: Core Team | Dependencies: Phase 4, QA sign-off | Status: ⬜**

### 5.1 Staging Deployment
- [ ] Deploy to staging
- [ ] Run full benchmark suite
- [ ] Stakeholder review

### 5.2 Production Deployment
- [ ] Merge feature branch to main
- [ ] Feature flag OFF by default
- [ ] Documentation published
- [ ] Release notes prepared

### 5.3 Gradual Rollout
- [ ] Enable `USE_SEMANTIC_ROUTING=true` pro testing
- [ ] Monitor routing metrics
- [ ] Full rollout after 1 week stability

---

## Post-Deployment
**Owner: Core Team | Estimated: Ongoing | Status: ⬜**

- [ ] Monitor routing accuracy for 2 weeks
- [ ] Collect user feedback
- [ ] Document lessons learned
- [ ] Plan utterance expansion for remaining 35+ profiles
- [ ] Consider advanced optimizations

---

## Sign-off Matrix

| Phase | Owner | Reviewer | Date | Status |
|-------|-------|----------|------|--------|
| Pre-Implementation | Core Team | - | | ⬜ |
| Phase 1 | Core Team | - | | ⬜ |
| Phase 2 | Core Team | Senior | | ⬜ |
| Phase 3 | Core Team | - | | ⬜ |
| Phase 4 | Core Team | QA | | ⬜ |
| Phase 5 | Core Team | - | | ⬜ |
| Post-Deployment | Core Team | - | | ⬜ |

---

*Generated by Implementation Planner Complex Profile*
