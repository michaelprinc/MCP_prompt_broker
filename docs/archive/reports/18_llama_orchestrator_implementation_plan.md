# Report: llama-orchestrator Implementation Plan

> **Datum:** 2024-12-27  
> **Typ:** Implementační plán  
> **Složitost:** Critical  
> **Odhadovaný čas:** 40-60 hodin

---

## Shrnutí

Vytvořen komplexní implementační plán pro **llama-orchestrator** — Python-based control plane pro správu více llama.cpp server instancí. Projekt poskytuje Docker-like UX bez Dockeru na Windows.

## Vytvořené soubory

### Dokumentace
| Soubor | Popis |
|--------|-------|
| [llama-orchestrator/docs/IMPLEMENTATION_PLAN.md](../llama-orchestrator/docs/IMPLEMENTATION_PLAN.md) | Detailní implementační plán (6 fází) |
| [llama-orchestrator/docs/CHECKLIST.md](../llama-orchestrator/docs/CHECKLIST.md) | Podrobný checklist s akceptačními kritérii |
| [llama-orchestrator/README.md](../llama-orchestrator/README.md) | Projektová dokumentace |

### Zdrojový kód (Phase 0 scaffolding)
| Soubor | Popis |
|--------|-------|
| [pyproject.toml](../llama-orchestrator/pyproject.toml) | Projekt konfigurace (uv/pip compatible) |
| [src/llama_orchestrator/__init__.py](../llama-orchestrator/src/llama_orchestrator/__init__.py) | Package init |
| [src/llama_orchestrator/__main__.py](../llama-orchestrator/src/llama_orchestrator/__main__.py) | CLI entry point |
| [src/llama_orchestrator/cli.py](../llama-orchestrator/src/llama_orchestrator/cli.py) | Typer CLI (všechny příkazy) |
| [src/llama_orchestrator/config/schema.py](../llama-orchestrator/src/llama_orchestrator/config/schema.py) | Pydantic schemas |

### Konfigurace a skripty
| Soubor | Popis |
|--------|-------|
| [instances/gpt-oss/config.json](../llama-orchestrator/instances/gpt-oss/config.json) | Příklad instance konfigurace |
| [scripts/llama.ps1](../llama-orchestrator/scripts/llama.ps1) | PowerShell wrapper |
| [scripts/install-service.ps1](../llama-orchestrator/scripts/install-service.ps1) | Windows service instalátor |
| [tests/test_config.py](../llama-orchestrator/tests/test_config.py) | Unit testy pro config schemas |
| [.gitignore](../llama-orchestrator/.gitignore) | Git ignore pravidla |

## Architektura

```
┌─────────────────────────────────────────────────────────────┐
│                    CONTROL PLANE (Python)                   │
│  llama-orch CLI → Daemon → TUI Dashboard                   │
│                      ↓                                      │
│              State Manager (SQLite)                         │
└─────────────────────────────────────────────────────────────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
┌─────────────────────────────────────────────────────────────┐
│                    DATA PLANE (llama.cpp)                   │
│  llama-server:8001  llama-server:8002  llama-server:8003   │
└─────────────────────────────────────────────────────────────┘
```

## Implementační fáze

| Fáze | Název | Effort | Status |
|------|-------|--------|--------|
| 0 | Foundations | 4-6h | ✅ Hotovo (scaffolding) |
| 1 | Config Model + Validation | 6-8h | ⬜ TODO |
| 2 | Process Engine | 8-10h | ⬜ TODO |
| 3 | Health Monitoring | 6-8h | ⬜ TODO |
| 4 | CLI + Dashboard | 8-10h | ⬜ TODO |
| 5 | Daemon + Autostart | 6-8h | ⬜ TODO |
| 6 | Extensions | 10+h | ⬜ Future |

## Klíčové funkce

1. **Multi-instance** — Více llama-server procesů na různých portech
2. **Health monitoring** — GET /health polling s auto-restart
3. **CLI + Daemon** — Interaktivní příkazy + background monitoring
4. **TUI Dashboard** — Live tabulka stavu instancí (rich)
5. **Windows Autostart** — Task Scheduler / NSSM integrace
6. **GPU Backend** — CPU, Vulkan (AMD), CUDA (future)

## Použité technologie

- **Python 3.11+** — Core language
- **Pydantic v2** — Config validation
- **Typer** — CLI framework
- **Rich** — TUI/terminal formatting
- **httpx** — HTTP client for health checks
- **psutil** — Process management
- **aiosqlite** — Async state storage

## Další kroky

1. **Nainstalovat závislosti:**
   ```powershell
   cd llama-orchestrator
   uv sync
   ```

2. **Ověřit CLI:**
   ```powershell
   python -m llama_orchestrator --help
   ```

3. **Spustit testy:**
   ```powershell
   pytest tests/
   ```

4. **Pokračovat Phase 1:** Implementovat config validator

---

**Autor:** GitHub Copilot (Implementation Planner Profile)
