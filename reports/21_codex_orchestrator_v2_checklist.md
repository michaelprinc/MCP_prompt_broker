# Codex Orchestrator v2.0 – Implementační Checklist

> **Generated:** 2024-12-31  
> **Complexity:** Critical  
> **Estimated Total Effort:** 13 pracovních dnů (~2.5 týdne)  
> **Related Plan:** [21_codex_orchestrator_v2_implementation_plan.md](21_codex_orchestrator_v2_implementation_plan.md)

---

## Fáze 0: Příprava (~1 den)

### Setup
- [ ] Vytvořit git tag `v1.0-pre-upgrade` pro backup
- [ ] Vytvořit feature branch `feature/v2-jsonl-verify-security`
- [ ] Aktualizovat `pyproject.toml` s novými dependencies
  - [ ] `jsonlines>=4.0.0`
  - [ ] `jsonschema>=4.21.0`
  - [ ] `gitpython>=3.1.40`
- [ ] Vytvořit prázdné moduly pro novou strukturu
  - [ ] `src/mcp_codex_orchestrator/verify/`
  - [ ] `src/mcp_codex_orchestrator/security/`
  - [ ] `schemas/`

**Acceptance Criteria:**
- Git tag existuje
- Feature branch vytvořen
- `pip install -e ".[dev]"` proběhne bez chyb
- Prázdné moduly importovatelné

---

## Fáze 1: JSONL Infrastructure (~2 dny)

### 1.1 JSONL Event Models
- [ ] Vytvořit `models/jsonl_events.py`
  - [ ] `EventType` enum (message.delta, tool.call, tool.result, file.change, command.run, error, completion)
  - [ ] `CodexEvent` base model
  - [ ] `FileChange` model
  - [ ] `CommandRun` model
  - [ ] `CompletionData` model
- [ ] Přidat unit testy pro modely

### 1.2 JSONL Parser
- [ ] Vytvořit `orchestrator/jsonl_parser.py`
  - [ ] `parse_stream()` – real-time async parsing
  - [ ] `parse_file()` – completed JSONL file parsing
  - [ ] `extract_summary()` – structured summary extraction
  - [ ] `_extract_file_changes()` helper
  - [ ] `_extract_commands()` helper
  - [ ] `_extract_errors()` helper
  - [ ] `_extract_token_usage()` helper
- [ ] Vytvořit `tests/test_jsonl_parser.py`
  - [ ] Test parse_stream s mock daty
  - [ ] Test parse_file
  - [ ] Test extract_summary

### 1.3 Schema Validator
- [ ] Vytvořit `orchestrator/schema_validator.py`
  - [ ] `DEFAULT_SCHEMA` konstanta
  - [ ] `get_schema_path()` method
  - [ ] `validate_output()` method
  - [ ] `_load_schema()` helper
  - [ ] `OutputValidationError` exception
- [ ] Vytvořit `schemas/default_output.json`
- [ ] Vytvořit `schemas/code_change.json`
- [ ] Vytvořit `schemas/analysis_report.json`
- [ ] Vytvořit `tests/test_schema_validator.py`

**Acceptance Criteria:**
- JSONL parser korektně parsuje stream i soubor
- Schema validator validuje výstupy
- Všechny unit testy procházejí
- `ruff check` bez chyb

---

## Fáze 2: Docker Client Update (~1 den)

### 2.1 Command Building
- [ ] Aktualizovat `_build_command()` v `docker_client.py`
  - [ ] Přidat `--json` flag (default True)
  - [ ] Přidat `--output-schema` podpora
  - [ ] Zachovat zpětnou kompatibilitu
- [ ] Aktualizovat `run_codex()` signaturu
  - [ ] Přidat `json_output: bool = True`
  - [ ] Přidat `output_schema: Path | None = None`

### 2.2 Volume Mounts
- [ ] Aktualizovat `_build_volumes()`
  - [ ] Přidat `security_mode` parametr
  - [ ] Implementovat `ro` vs `rw` logiku
  - [ ] Přidat mount pro `/schemas/`
- [ ] Přidat `self.schemas_path` property

### 2.3 JSONL Logging
- [ ] Ukládat JSONL stream do `runs/{run_id}/events.jsonl`
- [ ] Aktualizovat `result_collector.py` jako fallback

**Acceptance Criteria:**
- `codex exec --json` se korektně volá
- JSONL output se ukládá do events.jsonl
- Security mode respektuje mount permissions
- Existující testy stále procházejí

---

## Fáze 3: Security Subsystem (~2 dny)

### 3.1 Security Modes
- [ ] Vytvořit `security/__init__.py`
- [ ] Vytvořit `security/modes.py`
  - [ ] `SecurityMode` enum (READONLY, WORKSPACE_WRITE, FULL_ACCESS)
  - [ ] `SECURITY_MODE_FLAGS` mapování
  - [ ] Docstringy s popisem režimů
- [ ] Vytvořit `security/sandbox.py`
  - [ ] `SandboxEnforcer` class
  - [ ] `validate_mode()` method
  - [ ] `get_docker_flags()` method

### 3.2 Patch Workflow
- [ ] Vytvořit `security/patch_workflow.py`
  - [ ] `PatchWorkflow` class
  - [ ] `generate_patch()` – vytvoření patch souboru
  - [ ] `preview_patch()` – náhled změn
  - [ ] `apply_patch()` – aplikace s vyžadovaným approval
  - [ ] `_parse_stat()` helper
  - [ ] `SecurityError` exception

### 3.3 Integration
- [ ] Aktualizovat `run_request.py` – přidat `security_mode` field
- [ ] Aktualizovat `run_manager.py` – respektovat security mode
- [ ] Vytvořit `tests/test_security_modes.py`

**Acceptance Criteria:**
- Tři security režimy funkční
- Patch workflow generuje/aplikuje patche
- READONLY mode zamezuje zápisům
- FULL_ACCESS vyžaduje explicitní potvrzení
- Audit logging funkční

---

## Fáze 4: Verify Loop (~2 dny)

### 4.1 Core Components
- [ ] Vytvořit `verify/__init__.py`
- [ ] Vytvořit `verify/verify_loop.py`
  - [ ] `VerifyConfig` dataclass
  - [ ] `VerifyResult` dataclass
  - [ ] `VerifyLoop` class
  - [ ] `run()` – single pass verification
  - [ ] `run_with_auto_fix()` – verification s auto-fix
  - [ ] `_generate_fix_prompt()` helper

### 4.2 Runners
- [ ] Vytvořit `verify/test_runner.py`
  - [ ] `TestRunner` class
  - [ ] `run()` method (pytest integration)
  - [ ] `parse_output()` method
- [ ] Vytvořit `verify/lint_checker.py`
  - [ ] `LintChecker` class
  - [ ] `check()` method (ruff/black)
- [ ] Vytvořit `verify/build_runner.py`
  - [ ] `BuildRunner` class
  - [ ] `run()` method (generic command)

### 4.3 Integration
- [ ] Aktualizovat `run_result.py` – přidat `verify_result` field
- [ ] Aktualizovat `run_manager.py` – volat verify loop po běhu
- [ ] Vytvořit `tests/test_verify_loop.py`
- [ ] Vytvořit `models/verify_result.py`

**Acceptance Criteria:**
- Verify loop detekuje failing testy
- Verify loop detekuje lint chyby
- Auto-fix funguje (max 2 pokusy)
- Konfigurovatelné přes VerifyConfig
- Všechny verify testy procházejí

---

## Fáze 5: Nové MCP Tools (~2 dny)

### 5.1 codex_run_status
- [ ] Vytvořit `tools/codex_status.py`
  - [ ] `handle_codex_status()` function
  - [ ] Status file reading
  - [ ] Container running check
  - [ ] Progress parsing z partial JSONL
- [ ] Přidat do `server.py` tool registrace

### 5.2 codex_run_cancel
- [ ] Vytvořit `tools/codex_cancel.py`
  - [ ] `handle_codex_cancel()` function
  - [ ] Container stop logic
  - [ ] Status update to "cancelled"
- [ ] Přidat do `server.py` tool registrace

### 5.3 codex_run_artifacts
- [ ] Vytvořit `tools/codex_artifacts.py`
  - [ ] `handle_codex_artifacts()` function
  - [ ] Artifact path collection
  - [ ] Optional content inclusion
- [ ] Přidat do `server.py` tool registrace

### 5.4 codex_git_diff
- [ ] Vytvořit `tools/codex_git_diff.py`
  - [ ] `handle_codex_git_diff()` function
  - [ ] `parse_unified_diff()` helper
  - [ ] Multiple format support (unified, stat, name-only)
- [ ] Vytvořit `utils/git_utils.py`
  - [ ] Diff parsing utilities
- [ ] Přidat do `server.py` tool registrace

### 5.5 Updated codex_run
- [ ] Aktualizovat `tools/codex_run.py`
  - [ ] Přidat `security_mode` parametr
  - [ ] Přidat `verify` parametr
  - [ ] Přidat `output_schema` parametr
- [ ] Aktualizovat tool schema v `server.py`

### 5.6 Testing
- [ ] Vytvořit `tests/test_new_tools.py`
  - [ ] Test codex_run_status
  - [ ] Test codex_run_cancel
  - [ ] Test codex_run_artifacts
  - [ ] Test codex_git_diff

**Acceptance Criteria:**
- Všechny 4 nové tooly registrovány
- Status polling funguje bez čtení logů
- Cancel zastaví běžící kontejner
- Artifacts vrací správné cesty a obsah
- Git diff parsuje korektně
- Updated codex_run respektuje nové parametry

---

## Fáze 6: Windows/WSL Dokumentace (~1 den)

### 6.1 Windows Guide
- [ ] Vytvořit `docs/WINDOWS_WSL_GUIDE.md`
  - [ ] Path mapping tabulka (Windows ↔ WSL)
  - [ ] Docker Desktop integration
  - [ ] File permissions sekce
  - [ ] Git repository requirement
  - [ ] Authentication in container
  - [ ] Common issues & solutions

### 6.2 README Updates
- [ ] Aktualizovat hlavní `README.md`
  - [ ] Odkaz na Windows guide
  - [ ] WSL doporučení

**Acceptance Criteria:**
- Windows guide je kompletní
- Path mapping jasně vysvětlen
- Common issues pokrývají reálné problémy
- README obsahuje odkaz

---

## Fáze 7: Testy & Dokumentace (~2 dny)

### 7.1 Integration Tests
- [ ] End-to-end test s reálným Codex CLI
- [ ] Test JSONL flow
- [ ] Test verify loop integration
- [ ] Test security modes v Docker

### 7.2 Documentation
- [ ] Vytvořit `docs/SECURITY_MODES.md`
  - [ ] Popis všech režimů
  - [ ] Use cases
  - [ ] Příklady konfigurace
- [ ] Vytvořit `docs/VERIFY_LOOP.md`
  - [ ] Jak funguje verify loop
  - [ ] Konfigurace
  - [ ] Auto-fix workflow
- [ ] Vytvořit `docs/JSONL_OUTPUT.md`
  - [ ] Event typy
  - [ ] Příklady JSONL
  - [ ] Parsing dokumentace

### 7.3 Final Updates
- [ ] Aktualizovat `README.md`
  - [ ] v2 features
  - [ ] Nové tooly
  - [ ] Migration guide z v1
- [ ] Aktualizovat `CHANGELOG.md`
- [ ] Code review všech změn
- [ ] `ruff check .` passes
- [ ] `pytest` passes (>80% coverage)
- [ ] `mypy` passes

**Acceptance Criteria:**
- Všechny testy procházejí
- Dokumentace kompletní
- Lint/type checks bez chyb
- Code review schválen

---

## Release Checklist

### Pre-Release
- [ ] Všechny fáze dokončeny ✓
- [ ] Feature branch merged do main
- [ ] Vytvořit git tag `v2.0.0`
- [ ] Aktualizovat `__version__` v `__init__.py`

### Post-Release
- [ ] Oznámení v projektu
- [ ] Dokumentace na správném místě
- [ ] Smazat feature branch

---

## Progress Tracking

| Fáze | Status | Started | Completed | Notes |
|------|--------|---------|-----------|-------|
| Fáze 0 | ⬜ Not Started | - | - | |
| Fáze 1 | ⬜ Not Started | - | - | |
| Fáze 2 | ⬜ Not Started | - | - | |
| Fáze 3 | ⬜ Not Started | - | - | |
| Fáze 4 | ⬜ Not Started | - | - | |
| Fáze 5 | ⬜ Not Started | - | - | |
| Fáze 6 | ⬜ Not Started | - | - | |
| Fáze 7 | ⬜ Not Started | - | - | |
| Release | ⬜ Not Started | - | - | |

**Legend:** ⬜ Not Started | 🔄 In Progress | ✅ Completed | ❌ Blocked

---

*Checklist vygenerován: 2024-12-31*  
*Profil: implementation_planner*
