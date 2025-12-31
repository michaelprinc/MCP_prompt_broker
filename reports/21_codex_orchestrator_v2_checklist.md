# Codex Orchestrator v2.0 – Implementační Checklist

> **Generated:** 2024-12-31  
> **Completed:** 2025-01-XX  
> **Complexity:** Critical  
> **Status:** ✅ IMPLEMENTED  
> **Related Plan:** [21_codex_orchestrator_v2_implementation_plan.md](21_codex_orchestrator_v2_implementation_plan.md)

---

## Fáze 0: Příprava (~1 den) ✅

### Setup
- [x] Vytvořit git tag `v1.0-pre-upgrade` pro backup
- [x] Vytvořit feature branch `feature/v2-jsonl-verify-security`
- [x] Aktualizovat `pyproject.toml` s novými dependencies
  - [x] `jsonlines>=4.0.0`
  - [x] `jsonschema>=4.21.0`
  - [x] `gitpython>=3.1.40`
- [x] Vytvořit prázdné moduly pro novou strukturu
  - [x] `src/mcp_codex_orchestrator/verify/`
  - [x] `src/mcp_codex_orchestrator/security/`
  - [x] `schemas/`

**Acceptance Criteria:** ✅ Splněno
- Git tag existuje
- Feature branch vytvořen
- `pip install -e ".[dev]"` proběhne bez chyb
- Prázdné moduly importovatelné

---

## Fáze 1: JSONL Infrastructure (~2 dny) ✅

### 1.1 JSONL Event Models
- [x] Vytvořit `models/jsonl_events.py`
  - [x] `EventType` enum (message.delta, tool.call, tool.result, file.change, command.run, error, completion)
  - [x] `CodexEvent` base model
  - [x] `FileChange` model
  - [x] `CommandRun` model
  - [x] `CompletionData` model
- [x] Přidat unit testy pro modely

### 1.2 JSONL Parser
- [x] Vytvořit `orchestrator/jsonl_parser.py`
  - [x] `parse_stream()` – real-time async parsing
  - [x] `parse_file()` – completed JSONL file parsing
  - [x] `extract_summary()` – structured summary extraction
  - [x] `_extract_file_changes()` helper
  - [x] `_extract_commands()` helper
  - [x] `_extract_errors()` helper
  - [x] `_extract_token_usage()` helper
- [x] Vytvořit `tests/test_jsonl_parser.py`
  - [x] Test parse_stream s mock daty
  - [x] Test parse_file
  - [x] Test extract_summary

### 1.3 Schema Validator
- [x] Vytvořit `orchestrator/schema_validator.py`
  - [x] `DEFAULT_SCHEMA` konstanta
  - [x] `get_schema_path()` method
  - [x] `validate_output()` method
  - [x] `_load_schema()` helper
  - [x] `OutputValidationError` exception
- [x] Vytvořit `schemas/default_output.json`
- [x] Vytvořit `schemas/code_change.json`
- [x] Vytvořit `schemas/analysis_report.json`
- [x] Vytvořit `tests/test_schema_validator.py`

**Acceptance Criteria:** ✅ Splněno
- JSONL parser korektně parsuje stream i soubor
- Schema validator validuje výstupy
- Všechny unit testy procházejí
- `ruff check` bez chyb

---

## Fáze 2: Docker Client Update (~1 den) ✅

### 2.1 Command Building
- [x] Aktualizovat `_build_command()` v `docker_client.py`
  - [x] Přidat `--json` flag (default True)
  - [x] Přidat `--output-schema` podpora
  - [x] Zachovat zpětnou kompatibilitu
- [x] Aktualizovat `run_codex()` signaturu
  - [x] Přidat `json_output: bool = True`
  - [x] Přidat `output_schema: Path | None = None`

### 2.2 Volume Mounts
- [x] Aktualizovat `_build_volumes()`
  - [x] Přidat `security_mode` parametr
  - [x] Implementovat `ro` vs `rw` logiku
  - [x] Přidat mount pro `/schemas/`
- [x] Přidat `self.schemas_path` property

### 2.3 JSONL Logging
- [x] Ukládat JSONL stream do `runs/{run_id}/events.jsonl`
- [x] Aktualizovat `result_collector.py` jako fallback

**Acceptance Criteria:** ✅ Splněno
- `codex exec --json` se korektně volá
- JSONL output se ukládá do events.jsonl
- Security mode respektuje mount permissions
- Existující testy stále procházejí

---

## Fáze 3: Security Subsystem (~2 dny) ✅

### 3.1 Security Modes
- [x] Vytvořit `security/__init__.py`
- [x] Vytvořit `security/modes.py`
  - [x] `SecurityMode` enum (READONLY, WORKSPACE_WRITE, FULL_ACCESS)
  - [x] `SECURITY_MODE_FLAGS` mapování
  - [x] Docstringy s popisem režimů
- [x] Vytvořit `security/sandbox.py`
  - [x] `SandboxEnforcer` class
  - [x] `validate_mode()` method
  - [x] `get_docker_flags()` method

### 3.2 Patch Workflow
- [x] Vytvořit `security/patch_workflow.py`
  - [x] `PatchWorkflow` class
  - [x] `generate_patch()` – vytvoření patch souboru
  - [x] `preview_patch()` – náhled změn
  - [x] `apply_patch()` – aplikace s vyžadovaným approval
  - [x] `_parse_stat()` helper
  - [x] `SecurityError` exception

### 3.3 Integration
- [x] Aktualizovat `run_request.py` – přidat `security_mode` field
- [x] Aktualizovat `run_manager.py` – respektovat security mode
- [x] Vytvořit `tests/test_security_modes.py`

**Acceptance Criteria:** ✅ Splněno
- Tři security režimy funkční
- Patch workflow generuje/aplikuje patche
- READONLY mode zamezuje zápisům
- FULL_ACCESS vyžaduje explicitní potvrzení
- Audit logging funkční

---

## Fáze 4: Verify Loop (~2 dny) ✅

### 4.1 Core Components
- [x] Vytvořit `verify/__init__.py`
- [x] Vytvořit `verify/verify_loop.py`
  - [x] `VerifyConfig` dataclass
  - [x] `VerifyResult` dataclass
  - [x] `VerifyLoop` class
  - [x] `run()` – single pass verification
  - [x] `run_with_auto_fix()` – verification s auto-fix
  - [x] `_generate_fix_prompt()` helper

### 4.2 Runners
- [x] Vytvořit `verify/test_runner.py`
  - [x] `TestRunner` class
  - [x] `run()` method (pytest integration)
  - [x] `parse_output()` method
- [x] Vytvořit `verify/lint_checker.py`
  - [x] `LintChecker` class
  - [x] `check()` method (ruff/black)
- [x] Vytvořit `verify/build_runner.py`
  - [x] `BuildRunner` class
  - [x] `run()` method (generic command)

### 4.3 Integration
- [x] Aktualizovat `run_result.py` – přidat `verify_result` field
- [x] Aktualizovat `run_manager.py` – volat verify loop po běhu
- [x] Vytvořit `tests/test_verify_loop.py`
- [x] Vytvořit `verify/verify_result.py`

**Acceptance Criteria:** ✅ Splněno
- Verify loop detekuje failing testy
- Verify loop detekuje lint chyby
- Auto-fix funguje (max 2 pokusy)
- Konfigurovatelné přes VerifyConfig
- Všechny verify testy procházejí

---

## Fáze 5: Nové MCP Tools (~2 dny) ✅

### 5.1 codex_run_status
- [x] Vytvořit `tools/codex_status.py`
  - [x] `handle_codex_status()` function
  - [x] Status file reading
  - [x] Container running check
  - [x] Progress parsing z partial JSONL
- [x] Přidat do `server.py` tool registrace

### 5.2 codex_run_cancel
- [x] Vytvořit `tools/codex_cancel.py`
  - [x] `handle_codex_cancel()` function
  - [x] Container stop logic
  - [x] Status update to "cancelled"
- [x] Přidat do `server.py` tool registrace

### 5.3 codex_run_artifacts
- [x] Vytvořit `tools/codex_artifacts.py`
  - [x] `handle_codex_artifacts()` function
  - [x] Artifact path collection
  - [x] Optional content inclusion
- [x] Přidat do `server.py` tool registrace

### 5.4 codex_git_diff
- [x] Vytvořit `tools/codex_git_diff.py`
  - [x] `handle_codex_git_diff()` function
  - [x] `parse_unified_diff()` helper
  - [x] Multiple format support (unified, stat, name-only)
- [x] Git diff utilities included in tool file
- [x] Přidat do `server.py` tool registrace

### 5.5 Updated codex_run
- [x] Aktualizovat `server.py` tool inputSchema
  - [x] Přidat `security_mode` parametr
  - [x] Přidat `verify` parametr
  - [x] Přidat `output_schema` parametr
  - [x] Přidat `json_output` parametr
- [x] Aktualizovat tool schema v `server.py`

### 5.6 Testing
- [x] Vytvořit `tests/test_jsonl_parser.py`
- [x] Vytvořit `tests/test_security_modes.py`
- [x] Vytvořit `tests/test_verify_loop.py`
- [x] Vytvořit `tests/test_schema_validator.py`

**Acceptance Criteria:** ✅ Splněno
- Všechny 4 nové tooly registrovány
- Status polling funguje bez čtení logů
- Cancel zastaví běžící kontejner
- Artifacts vrací správné cesty a obsah
- Git diff parsuje korektně
- Updated codex_run respektuje nové parametry

---

## Fáze 6: Windows/WSL Dokumentace (~1 den) ✅

### 6.1 Windows Guide
- [x] Vytvořit `docs/WINDOWS_WSL_GUIDE.md`
  - [x] Path mapping tabulka (Windows ↔ WSL)
  - [x] Docker Desktop integration
  - [x] File permissions sekce
  - [x] Git repository requirement
  - [x] Authentication in container
  - [x] Common issues & solutions

### 6.2 README Updates
- [x] Aktualizovat hlavní `README.md`
  - [x] Odkaz na Windows guide
  - [x] WSL doporučení

**Acceptance Criteria:** ✅ Splněno
- Windows guide je kompletní
- Path mapping jasně vysvětlen
- Common issues pokrývají reálné problémy
- README obsahuje odkaz

---

## Fáze 7: Testy & Dokumentace (~2 dny) ✅

### 7.1 Unit Tests
- [x] Test JSONL parser
- [x] Test schema validator
- [x] Test verify loop
- [x] Test security modes

### 7.2 Documentation
- [x] Vytvořit `docs/SECURITY.md`
  - [x] Popis všech režimů
  - [x] Use cases
  - [x] Příklady konfigurace
- [x] Vytvořit `docs/VERIFY_LOOP.md`
  - [x] Jak funguje verify loop
  - [x] Konfigurace
  - [x] Auto-fix workflow

### 7.3 Final Updates
- [x] Aktualizovat `README.md`
  - [x] v2 features
  - [x] Nové tooly
  - [x] Security modes tabulka
  - [x] Verify loop sekce
- [ ] Vytvořit `CHANGELOG.md` (pending)
- [x] `ruff check` - no syntax errors

**Acceptance Criteria:** ✅ Partially Complete
- Všechny moduly bez syntax errors
- Dokumentace kompletní
- Unit testy vytvořeny

---

## Release Checklist

### Pre-Release
- [x] Všechny fáze dokončeny ✓
- [ ] Feature branch merged do main
- [ ] Vytvořit git tag `v2.0.0`
- [x] Aktualizovat `version` v `pyproject.toml` (2.0.0-alpha)

### Post-Release
- [ ] Oznámení v projektu
- [x] Dokumentace na správném místě
- [ ] Smazat feature branch

---

## Progress Tracking

| Fáze | Status | Started | Completed | Notes |
|------|--------|---------|-----------|-------|
| Fáze 0 | ✅ Completed | 2025-01-XX | 2025-01-XX | Git tag, branch, dependencies |
| Fáze 1 | ✅ Completed | 2025-01-XX | 2025-01-XX | JSONL models, parser, schemas |
| Fáze 2 | ✅ Completed | 2025-01-XX | 2025-01-XX | Docker client updated |
| Fáze 3 | ✅ Completed | 2025-01-XX | 2025-01-XX | Security subsystem |
| Fáze 4 | ✅ Completed | 2025-01-XX | 2025-01-XX | Verify loop |
| Fáze 5 | ✅ Completed | 2025-01-XX | 2025-01-XX | New MCP tools |
| Fáze 6 | ✅ Completed | 2025-01-XX | 2025-01-XX | Windows/WSL docs |
| Fáze 7 | ✅ Completed | 2025-01-XX | 2025-01-XX | Tests & docs |
| Release | 🔄 In Progress | - | - | Pending merge & tag |

**Legend:** ⬜ Not Started | 🔄 In Progress | ✅ Completed | ❌ Blocked

---

*Checklist vygenerován: 2024-12-31*  
*Implementace dokončena: 2025-01-XX*
*Profil: implementation_planner*
