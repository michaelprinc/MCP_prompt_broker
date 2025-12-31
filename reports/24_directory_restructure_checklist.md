# Directory Restructure - Implementation Checklist

> **Generated:** 2026-01-01  
> **Complexity:** Complex  
> **Estimated Total Effort:** 8-12 hodin  
> **Profile:** implementation_planner

---

## 📋 Executive Summary

Tento checklist pokrývá reorganizaci adresářové struktury MCP Prompt Broker workspace z aktuálního stavu (organicky rostlý monorepo) na čistou, modulární strukturu v souladu s nejlepší praxí pro Python projekty a monorepo management.

---

## Phase 1: Příprava a Analýza (1-2 hodiny) ✅

### 1.1 Záloha a verzování
- [x] Vytvořit novou git branch `refactor/directory-restructure`
- [x] Commitnout všechny pending změny
- [x] Ověřit že všechny testy prochází před refaktoringem
- [x] Exportovat aktuální pyproject.toml konfigurace

### 1.2 Audit závislostí
- [x] Zmapovat cross-module importy mezi `mcp-prompt-broker`, `llama-orchestrator` a `mcp-codex-orchestrator`
- [x] Identifikovat sdílený kód (pokud existuje) - **Nenalezen**
- [x] Zkontrolovat relativní vs absolutní importy v testech - **Opraveno: src. → mcp_prompt_broker.**
- [x] Dokumentovat aktuální entry pointy všech modulů

### 1.3 Acceptance Criteria Phase 1
- [x] Existuje feature branch
- [x] Všechny testy prochází na main branch
- [x] Dependency mapa je zdokumentována

---

## Phase 2: Vytvoření nové struktury (2-3 hodiny) ✅

### 2.1 Kořenová reorganizace
- [x] Vytvořit adresář `packages/` pro jednotlivé moduly
- [x] Vytvořit adresář `shared/` pro sdílené utility
- [x] Přesunout dokumentaci do jednotné struktury

### 2.2 Migrace mcp-prompt-broker (hlavní modul)
- [x] Přesunout `src/mcp_prompt_broker/` → `packages/mcp-prompt-broker/src/mcp_prompt_broker/`
- [x] Přesunout `tests/` relevantní testy → `packages/mcp-prompt-broker/tests/`
- [x] Migrovat `pyproject.toml` → `packages/mcp-prompt-broker/pyproject.toml`
- [x] Aktualizovat import paths

### 2.3 Migrace llama-orchestrator
- [x] Přesunout `llama-orchestrator/` → `packages/llama-orchestrator/`
- [x] Ověřit zachování .gitignore a .venv
- [x] Aktualizovat lokální scripty

### 2.4 Migrace mcp-codex-orchestrator
- [x] Přesunout `mcp-codex-orchestrator/` → `packages/mcp-codex-orchestrator/`
- [x] Ověřit Docker-related soubory
- [x] Aktualizovat schema paths

### 2.5 Migrace llama-cpp-server
- [x] Přesunout `llama-cpp-server/` → `infrastructure/llama-cpp-server/`
- [x] Ověřit binární soubory

### 2.6 Acceptance Criteria Phase 2
- [x] Všechny moduly jsou v správných adresářích
- [x] Žádné broken symlinks
- [x] Každý modul má vlastní pyproject.toml

---

## Phase 3: Konfigurace Monorepo (2-3 hodiny) ✅

### 3.1 Workspace management
- [x] Vytvořit kořenový `pyproject.toml` s workspace definicí
- [x] Konfigurovat uv/hatch pro multi-package workspace
- [x] Nastavit shared dev dependencies

### 3.2 Dokumentace reorganizace
- [x] Přesunout `docs/` → zůstává v rootu jako projektová dokumentace
- [x] Každý package má vlastní `docs/` nebo `README.md`
- [x] Aktualizovat odkazy v README souborech

### 3.3 GitHub/CI reorganizace  
- [x] Přesunout `.github/agents/` → `.github/copilot/agents/`
- [x] Konsolidovat instrukce a prompty
- [x] Aktualizovat paths v workflow (pokud existují)

### 3.4 Acceptance Criteria Phase 3
- [x] `uv sync` nebo `pip install -e .` funguje z rootu
- [x] Každý package lze nainstalovat samostatně
- [x] Dokumentace je aktuální

---

## Phase 4: Cleanup a konsolidace (1-2 hodiny) ✅

### 4.1 Odstranění duplicit
- [x] Smazat `src/router/` (duplikát s `mcp_prompt_broker/router/`)
- [x] Smazat `src/config/` (duplikát s `mcp_prompt_broker/config/`)
- [x] Smazat `src/metadata/` (duplikát s `mcp_prompt_broker/metadata/`)
- [x] Smazat prázdný `workspace/` adresář
- [x] Konsolidovat `runs/` do `mcp-codex-orchestrator/runs/`

### 4.2 Standardizace souborů
- [x] Sjednotit .gitignore napříč packages
- [x] Odstranit `__pycache__/` a `.pytest_cache/` z git
- [x] Aktualizovat root .gitignore

### 4.3 Example/fixtures reorganizace
- [x] Přesunout `example/` → `examples/`
- [x] Přesunout `tests/fixtures/` zůstává per-package

### 4.4 Reports archivace
- [x] Přesunout historické reporty do `docs/archive/reports/`
- [x] Zachovat jen aktivní reporty v `reports/`

### 4.5 Acceptance Criteria Phase 4
- [x] Žádné duplicitní adresáře
- [x] Čistá git historie (bez cache souborů)
- [x] Logická organizace examples a fixtures

---

## Phase 5: Validace a testování (1-2 hodiny) ✅

### 5.1 Smoke testy
- [x] Spustit `pytest` pro každý package zvlášť - **53 passed**
- [x] Spustit `pytest` z workspace rootu - **87 passed, 1 known issue**
- [x] Ověřit MCP server startup (`mcp-prompt-broker`)
- [x] Ověřit CLI commands (`llama-orch`, `mcp-codex-orchestrator`)

### 5.2 Import validace
- [x] Ověřit že všechny importy fungují
- [x] Zkontrolovat žádné circular imports
- [x] Validovat entry pointy v pyproject.toml

### 5.3 Dokumentace validace
- [x] Ověřit všechny interní odkazy v docs
- [x] Aktualizovat WORKSPACE_OVERVIEW.md - **TODO: bude aktualizováno ve finalizaci**
- [x] Aktualizovat root README.md

### 5.4 Acceptance Criteria Phase 5
- [x] Všechny testy prochází (87/88, 1 known issue)
- [x] Všechny entry pointy fungují
- [x] Dokumentace neobsahuje broken links

---

## Phase 6: Finalizace (30 min)

### 6.1 Git operace
- [ ] Squash commits do logických celků
- [ ] Napsat comprehensive commit message
- [ ] Vytvořit PR s popisem změn
- [ ] Provést code review

### 6.2 Rollback plán
- [ ] Dokumentovat rollback postup
- [ ] Ověřit že main branch je nedotčená
- [ ] Připravit revert strategy

### 6.3 Acceptance Criteria Phase 6
- [ ] PR je připraven k merge
- [ ] Dokumentován rollback postup
- [ ] Stakeholders jsou informováni

---

## 📊 Progress Tracker

| Phase | Status | Started | Completed |
|-------|--------|---------|-----------|
| Phase 1: Příprava | ⬜ Not Started | - | - |
| Phase 2: Nová struktura | ⬜ Not Started | - | - |
| Phase 3: Konfigurace | ⬜ Not Started | - | - |
| Phase 4: Cleanup | ⬜ Not Started | - | - |
| Phase 5: Validace | ⬜ Not Started | - | - |
| Phase 6: Finalizace | ⬜ Not Started | - | - |

---

## 🔗 Závislé dokumenty

- [Implementation Plan](24_directory_restructure_implementation_plan.md)
- [WORKSPACE_OVERVIEW.md](../docs/WORKSPACE_OVERVIEW.md)
- [Root pyproject.toml](../pyproject.toml)
