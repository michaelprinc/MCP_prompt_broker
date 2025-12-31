# Directory Restructure - Implementation Checklist

> **Generated:** 2026-01-01  
> **Complexity:** Complex  
> **Estimated Total Effort:** 8-12 hodin  
> **Profile:** implementation_planner

---

## 📋 Executive Summary

Tento checklist pokrývá reorganizaci adresářové struktury MCP Prompt Broker workspace z aktuálního stavu (organicky rostlý monorepo) na čistou, modulární strukturu v souladu s nejlepší praxí pro Python projekty a monorepo management.

---

## Phase 1: Příprava a Analýza (1-2 hodiny)

### 1.1 Záloha a verzování
- [ ] Vytvořit novou git branch `refactor/directory-restructure`
- [ ] Commitnout všechny pending změny
- [ ] Ověřit že všechny testy prochází před refaktoringem
- [ ] Exportovat aktuální pyproject.toml konfigurace

### 1.2 Audit závislostí
- [ ] Zmapovat cross-module importy mezi `mcp-prompt-broker`, `llama-orchestrator` a `mcp-codex-orchestrator`
- [ ] Identifikovat sdílený kód (pokud existuje)
- [ ] Zkontrolovat relativní vs absolutní importy v testech
- [ ] Dokumentovat aktuální entry pointy všech modulů

### 1.3 Acceptance Criteria Phase 1
- [ ] Existuje feature branch
- [ ] Všechny testy prochází na main branch
- [ ] Dependency mapa je zdokumentována

---

## Phase 2: Vytvoření nové struktury (2-3 hodiny)

### 2.1 Kořenová reorganizace
- [ ] Vytvořit adresář `packages/` pro jednotlivé moduly
- [ ] Vytvořit adresář `shared/` pro sdílené utility
- [ ] Přesunout dokumentaci do jednotné struktury

### 2.2 Migrace mcp-prompt-broker (hlavní modul)
- [ ] Přesunout `src/mcp_prompt_broker/` → `packages/mcp-prompt-broker/src/mcp_prompt_broker/`
- [ ] Přesunout `tests/` relevantní testy → `packages/mcp-prompt-broker/tests/`
- [ ] Migrovat `pyproject.toml` → `packages/mcp-prompt-broker/pyproject.toml`
- [ ] Aktualizovat import paths

### 2.3 Migrace llama-orchestrator
- [ ] Přesunout `llama-orchestrator/` → `packages/llama-orchestrator/`
- [ ] Ověřit zachování .gitignore a .venv
- [ ] Aktualizovat lokální scripty

### 2.4 Migrace mcp-codex-orchestrator
- [ ] Přesunout `mcp-codex-orchestrator/` → `packages/mcp-codex-orchestrator/`
- [ ] Ověřit Docker-related soubory
- [ ] Aktualizovat schema paths

### 2.5 Migrace llama-cpp-server
- [ ] Přesunout `llama-cpp-server/` → `infrastructure/llama-cpp-server/`
- [ ] Ověřit binární soubory

### 2.6 Acceptance Criteria Phase 2
- [ ] Všechny moduly jsou v správných adresářích
- [ ] Žádné broken symlinks
- [ ] Každý modul má vlastní pyproject.toml

---

## Phase 3: Konfigurace Monorepo (2-3 hodiny)

### 3.1 Workspace management
- [ ] Vytvořit kořenový `pyproject.toml` s workspace definicí
- [ ] Konfigurovat uv/hatch pro multi-package workspace
- [ ] Nastavit shared dev dependencies

### 3.2 Dokumentace reorganizace
- [ ] Přesunout `docs/` → zůstává v rootu jako projektová dokumentace
- [ ] Každý package má vlastní `docs/` nebo `README.md`
- [ ] Aktualizovat odkazy v README souborech

### 3.3 GitHub/CI reorganizace  
- [ ] Přesunout `.github/agents/` → `.github/copilot/agents/`
- [ ] Konsolidovat instrukce a prompty
- [ ] Aktualizovat paths v workflow (pokud existují)

### 3.4 Acceptance Criteria Phase 3
- [ ] `uv sync` nebo `pip install -e .` funguje z rootu
- [ ] Každý package lze nainstalovat samostatně
- [ ] Dokumentace je aktuální

---

## Phase 4: Cleanup a konsolidace (1-2 hodiny)

### 4.1 Odstranění duplicit
- [ ] Smazat `src/router/` (duplikát s `mcp_prompt_broker/router/`)
- [ ] Smazat `src/config/` (duplikát s `mcp_prompt_broker/config/`)
- [ ] Smazat `src/metadata/` (duplikát s `mcp_prompt_broker/metadata/`)
- [ ] Smazat prázdný `workspace/` adresář
- [ ] Konsolidovat `runs/` do `mcp-codex-orchestrator/runs/`

### 4.2 Standardizace souborů
- [ ] Sjednotit .gitignore napříč packages
- [ ] Odstranit `__pycache__/` a `.pytest_cache/` z git
- [ ] Aktualizovat root .gitignore

### 4.3 Example/fixtures reorganizace
- [ ] Přesunout `example/` → `examples/`
- [ ] Přesunout `tests/fixtures/` zůstává per-package

### 4.4 Reports archivace
- [ ] Přesunout historické reporty do `docs/archive/reports/`
- [ ] Zachovat jen aktivní reporty v `reports/`

### 4.5 Acceptance Criteria Phase 4
- [ ] Žádné duplicitní adresáře
- [ ] Čistá git historie (bez cache souborů)
- [ ] Logická organizace examples a fixtures

---

## Phase 5: Validace a testování (1-2 hodiny)

### 5.1 Smoke testy
- [ ] Spustit `pytest` pro každý package zvlášť
- [ ] Spustit `pytest` z workspace rootu
- [ ] Ověřit MCP server startup (`mcp-prompt-broker`)
- [ ] Ověřit CLI commands (`llama-orch`, `mcp-codex-orchestrator`)

### 5.2 Import validace
- [ ] Ověřit že všechny importy fungují
- [ ] Zkontrolovat žádné circular imports
- [ ] Validovat entry pointy v pyproject.toml

### 5.3 Dokumentace validace
- [ ] Ověřit všechny interní odkazy v docs
- [ ] Aktualizovat WORKSPACE_OVERVIEW.md
- [ ] Aktualizovat root README.md

### 5.4 Acceptance Criteria Phase 5
- [ ] Všechny testy prochází
- [ ] Všechny entry pointy fungují
- [ ] Dokumentace neobsahuje broken links

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
