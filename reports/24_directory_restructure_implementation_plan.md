# Directory Restructure - Implementation Plan

> **Generated:** 2026-01-01  
> **Complexity:** Complex  
> **Estimated Effort:** 8-12 hodin  
> **Profile:** implementation_planner  
> **Checklist:** [24_directory_restructure_checklist.md](24_directory_restructure_checklist.md)

---

## 1. Snapshot aktuálního stavu

### 1.1 Současná adresářová struktura

```
MCP_Prompt_Broker/                    # Workspace root
├── .github/                          # GitHub konfigurace
│   ├── agents/                       # 🔴 Nestandard: Custom agents
│   ├── archive/                      # Archivované soubory
│   ├── copilot-instructions.md       # Hlavní instrukce
│   ├── instructions/                 # Další instrukce
│   └── prompts/                      # Prompt templates
├── .vscode/                          # VS Code konfigurace
├── companion-agent.json              # 🔴 Duplicita s .github/agents/
├── companion-instructions.md         # 🔴 Duplicita s .github/agents/
├── docs/                             # Dokumentace
│   ├── api/                          # API dokumentace
│   ├── architecture/                 # Architektura
│   └── modules/                      # Moduly
├── example/                          # 🔴 Nestandard: Mělo by být examples/
│   └── sklearn_toy_model/
├── install.ps1                       # Instalační skript
├── llama-cpp-server/                 # 🟡 Infrastructure modul
│   ├── bin/                          # Binárky
│   ├── config.json
│   └── *.ps1                         # Skripty
├── llama-orchestrator/               # 🟢 Samostatný package (správně)
│   ├── src/llama_orchestrator/
│   ├── tests/
│   └── pyproject.toml
├── mcp-codex-orchestrator/           # 🟢 Samostatný package (správně)
│   ├── src/mcp_codex_orchestrator/
│   ├── docker/
│   ├── tests/
│   └── pyproject.toml
├── pyproject.toml                    # Hlavní package config
├── reports/                          # 🟡 Velké množství reportů
│   └── *.md                          # 24+ reportů
├── runs/                             # 🔴 Orphaned: Mělo by být v delegated-task-runner
├── src/                              # 🔴 PROBLÉM: Smíšená struktura
│   ├── AGENTS.md                     # Nepatří sem
│   ├── config/                       # Duplikát
│   ├── mcp_prompt_broker/            # Hlavní modul
│   │   ├── config/                   # Další konfigurace
│   │   ├── copilot-profiles/         # Markdown profily
│   │   ├── integrations/
│   │   ├── metadata/
│   │   ├── router/
│   │   └── server.py
│   ├── metadata/                     # 🔴 Duplikát
│   └── router/                       # 🔴 Duplikát
├── tests/                            # Testy hlavního modulu
│   └── fixtures/
└── workspace/                        # 🔴 Prázdný adresář
```

### 1.2 Identifikované problémy

| Problém | Závažnost | Popis |
|---------|-----------|-------|
| **Duplikované moduly v src/** | 🔴 Vysoká | `src/config/`, `src/metadata/`, `src/router/` jsou duplikáty modulů v `mcp_prompt_broker/` |
| **Nekonzistentní package layout** | 🟡 Střední | Hlavní modul používá flat src/, ostatní mají nested packages/ strukturu |
| **Smíšený monorepo pattern** | 🟡 Střední | Některé packages jsou v rootu, některé v sub-adresářích |
| **Orphaned soubory** | 🟠 Nízká | `runs/`, `workspace/`, root-level companion files |
| **Přetížený reports/** | 🟠 Nízká | 24+ reportů bez archivace |
| **Nestandardní naming** | 🟠 Nízká | `example/` místo `examples/`, nekonzistentní case |

---

## 2. Cílová architektura

### 2.1 Navrhovaná struktura (Best Practice)

```
MCP_Prompt_Broker/                    # Workspace root (monorepo)
├── .github/                          # GitHub konfigurace
│   ├── copilot/                      # GitHub Copilot specifické
│   │   ├── agents/                   # Custom agents
│   │   └── instructions.md           # Hlavní instrukce
│   ├── workflows/                    # CI/CD (budoucí)
│   └── CODEOWNERS                    # (budoucí)
├── .vscode/                          # VS Code konfigurace
├── docs/                             # Globální dokumentace
│   ├── api/                          # API reference
│   ├── architecture/                 # Architektonické diagramy
│   ├── guides/                       # User & Developer guides
│   ├── archive/                      # Archivované dokumenty
│   │   └── reports/                  # Historické reporty
│   └── README.md
├── examples/                         # Příklady použití
│   └── sklearn_toy_model/
├── infrastructure/                   # Infrastrukturní nástroje
│   └── llama-cpp-server/
│       ├── bin/
│       ├── config.json
│       └── scripts/
├── packages/                         # 🆕 Python packages (monorepo)
│   ├── mcp-prompt-broker/            # Hlavní MCP server
│   │   ├── src/
│   │   │   └── mcp_prompt_broker/
│   │   │       ├── config/
│   │   │       ├── copilot-profiles/
│   │   │       ├── integrations/
│   │   │       ├── metadata/
│   │   │       ├── router/
│   │   │       ├── server.py
│   │   │       └── __init__.py
│   │   ├── tests/
│   │   ├── pyproject.toml
│   │   └── README.md
│   ├── llama-orchestrator/           # LLM orchestrace
│   │   ├── src/
│   │   │   └── llama_orchestrator/
│   │   ├── tests/
│   │   ├── pyproject.toml
│   │   └── README.md
│   └── mcp-codex-orchestrator/       # Codex Docker orchestrace
│       ├── src/
│       │   └── mcp_codex_orchestrator/
│       ├── docker/
│       ├── runs/                     # Přesunuto z root
│       ├── schemas/
│       ├── tests/
│       ├── pyproject.toml
│       └── README.md
├── reports/                          # Aktivní reporty (max 5-10)
├── scripts/                          # Globální skripty
│   └── install.ps1
├── shared/                           # 🆕 Sdílené utility (budoucí)
│   └── README.md
├── pyproject.toml                    # Workspace/monorepo config
├── pytest.ini                        # Globální pytest config
└── README.md                         # Root README
```

### 2.2 Klíčové principy návrhu

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        DIRECTORY STRUCTURE PRINCIPLES                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. SEPARATION OF CONCERNS                                                  │
│     • packages/ - Python packages (installable)                             │
│     • infrastructure/ - Non-Python tools, binaries                          │
│     • docs/ - All documentation                                             │
│     • examples/ - Usage examples                                            │
│                                                                             │
│  2. MONOREPO PATTERN                                                        │
│     • Single root pyproject.toml s workspace definicí                       │
│     • Každý package má vlastní pyproject.toml                               │
│     • Sdílené dev dependencies v rootu                                      │
│                                                                             │
│  3. CONSISTENT NAMING                                                       │
│     • Adresáře: lowercase-with-dashes                                       │
│     • Python packages: lowercase_with_underscores                           │
│     • Dokumenty: UPPERCASE pro top-level, lowercase pro ostatní             │
│                                                                             │
│  4. FLAT OVER NESTED (where possible)                                       │
│     • Max 4 úrovně vnořen                                                   │
│     • Explicitní nad implicitním                                            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Architektura a Flow

### 3.1 Modulární závislosti

```
                              ┌─────────────────────┐
                              │   VS Code / Copilot │
                              └──────────┬──────────┘
                                         │ MCP Protocol
                    ┌────────────────────┼────────────────────┐
                    │                    │                    │
                    ▼                    ▼                    ▼
        ┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐
        │ mcp-prompt-broker │ │mcp-codex-orchestr.│ │ (future MCP srv)  │
        │                   │ │                   │ │                   │
        │ Profile Routing   │ │ Docker Execution  │ │                   │
        │ Metadata Parsing  │ │ Artifact Mgmt     │ │                   │
        └───────────────────┘ └─────────┬─────────┘ └───────────────────┘
                                        │
                    ┌───────────────────┴───────────────────┐
                    │                                       │
                    ▼                                       ▼
        ┌───────────────────┐               ┌───────────────────────────┐
        │ llama-orchestrator│               │ Docker Runtime            │
        │                   │               │ (Codex CLI containers)    │
        │ CLI for llama.cpp │               └───────────────────────────┘
        │ Instance Mgmt     │
        └─────────┬─────────┘
                  │
                  ▼
        ┌───────────────────┐
        │ llama-cpp-server  │
        │ (Binary + Config) │
        └───────────────────┘
```

### 3.2 Package dependency mapa

| Package | Internal Deps | External Deps | Type |
|---------|---------------|---------------|------|
| mcp-prompt-broker | - | mcp, pyyaml | MCP Server |
| llama-orchestrator | - | pydantic, typer, httpx | CLI Tool |
| mcp-codex-orchestrator | - | mcp, docker, pydantic | MCP Server |
| shared (future) | - | - | Library |

---

## 4. Implementační fáze

### Phase 1: Příprava (Est. 1-2 hod)

```bash
# 1. Vytvořit feature branch
git checkout -b refactor/directory-restructure

# 2. Ověřit testy
pytest tests/ -v

# 3. Exportovat závislosti
pip freeze > requirements.backup.txt
```

**Deliverables:**
- Feature branch vytvořena
- Testy prochází
- Backup závislostí

### Phase 2: Vytvoření nové struktury (Est. 2-3 hod)

**Krok 2.1: Vytvořit kostru**
```bash
mkdir -p packages/mcp-prompt-broker/src
mkdir -p packages/mcp-prompt-broker/tests
mkdir -p infrastructure
mkdir -p examples
mkdir -p scripts
mkdir -p shared
mkdir -p docs/archive/reports
mkdir -p docs/guides
```

**Krok 2.2: Migrace mcp-prompt-broker**
```bash
# Přesunout source code
mv src/mcp_prompt_broker packages/mcp-prompt-broker/src/

# Přesunout relevantní testy
mv tests/test_profile_*.py packages/mcp-prompt-broker/tests/
mv tests/test_metadata_*.py packages/mcp-prompt-broker/tests/
mv tests/test_mcp_*.py packages/mcp-prompt-broker/tests/
mv tests/fixtures packages/mcp-prompt-broker/tests/
```

**Krok 2.3: Migrace ostatních packages**
```bash
mv llama-orchestrator packages/
mv mcp-codex-orchestrator packages/
mv llama-cpp-server infrastructure/
```

**Krok 2.4: Cleanup root**
```bash
mv runs packages/mcp-codex-orchestrator/
mv example examples
mv install.ps1 scripts/
rmdir workspace  # prázdný
rm -rf src/config src/metadata src/router  # duplikáty
rm -rf src/__pycache__
```

### Phase 3: Konfigurace Monorepo (Est. 2-3 hod)

**Nový kořenový pyproject.toml:**
```toml
[project]
name = "mcp-prompt-broker-workspace"
version = "0.1.0"
description = "MCP Prompt Broker Monorepo Workspace"
readme = "README.md"
requires-python = ">=3.11"
license = {text = "MIT"}

# Workspace nemá vlastní dependencies - jen dev tools
[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "ruff>=0.1",
    "mypy>=1.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

# UV workspace configuration
[tool.uv.workspace]
members = [
    "packages/mcp-prompt-broker",
    "packages/llama-orchestrator", 
    "packages/mcp-codex-orchestrator",
]

[tool.pytest.ini_options]
testpaths = ["packages/*/tests"]
pythonpath = ["packages/mcp-prompt-broker/src", "packages/llama-orchestrator/src", "packages/mcp-codex-orchestrator/src"]
asyncio_mode = "auto"

[tool.ruff]
line-length = 100
target-version = "py311"
```

### Phase 4: Cleanup (Est. 1-2 hod)

**Reorganizace .github:**
```bash
mkdir -p .github/copilot/agents
mv .github/agents/*.md .github/copilot/agents/
mv .github/copilot-instructions.md .github/copilot/
rm companion-agent.json companion-instructions.md  # duplikáty
```

**Archivace reportů:**
```bash
# Ponechat jen posledních 5 aktivních
mv reports/01_*.md docs/archive/reports/
mv reports/02_*.md docs/archive/reports/
# ... archivovat staré
```

### Phase 5: Validace (Est. 1-2 hod)

```bash
# Test každého package
cd packages/mcp-prompt-broker && pytest -v
cd ../llama-orchestrator && pytest -v
cd ../mcp-codex-orchestrator && pytest -v

# Test z rootu
cd ../../..
pytest packages/*/tests -v

# Ověřit entry pointy
python -m mcp_prompt_broker.server --help
llama-orch --help
```

---

## 5. Risk Analysis

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Broken imports po migraci | Střední | Vysoký | Důkladná validace + git revert ready |
| CI/CD failure | Nízká | Střední | Není CI → není riziko zatím |
| Lost files | Nízká | Vysoký | Git tracking + backup branch |
| VS Code config invalid | Střední | Nízký | Aktualizovat .vscode/settings.json |

### Rollback plán

```bash
# Pokud něco selže:
git checkout main
git branch -D refactor/directory-restructure
# Nebo:
git revert --no-commit HEAD~N..HEAD
```

---

## 6. Doporučený implementační prompt

Po schválení tohoto plánu použijte následující prompt pro spuštění implementace:

```
Proveď reorganizaci adresářové struktury podle schváleného plánu v 
reports/24_directory_restructure_implementation_plan.md.

Postupuj po fázích:
1. Vytvoř feature branch
2. Proveď migrace souborů
3. Aktualizuj pyproject.toml
4. Spusť validační testy
5. Připrav commit s popisem změn

Používej checklist v reports/24_directory_restructure_checklist.md 
pro sledování progressu.
```

---

## 7. Deliverables Summary

| Deliverable | Popis | Status |
|-------------|-------|--------|
| Feature branch | `refactor/directory-restructure` | ⬜ TODO |
| Nová struktura | `packages/`, `infrastructure/`, `examples/` | ⬜ TODO |
| Root pyproject.toml | Workspace konfigurace | ⬜ TODO |
| Aktualizovaná dokumentace | README, WORKSPACE_OVERVIEW | ⬜ TODO |
| Validované testy | Všechny packages | ⬜ TODO |
| PR ready | Pro merge do main | ⬜ TODO |

---

## 8. Následující kroky

1. **Review** tohoto implementačního plánu
2. **Schválení** změn stakeholdery
3. **Vytvoření feature branch** a zahájení Phase 1
4. **Inkrementální implementace** s průběžnou validací
5. **Code review** a merge

---

## 📎 Přílohy

- [Implementation Checklist](24_directory_restructure_checklist.md)
- [Current WORKSPACE_OVERVIEW](../docs/WORKSPACE_OVERVIEW.md)
- [Root pyproject.toml](../pyproject.toml)
