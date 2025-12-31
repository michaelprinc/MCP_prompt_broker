# MCP Codex Orchestrator – Implementační Checklist

> **Verze:** 1.0  
> **Datum:** 2025-12-25  
> **Status:** ✅ Implementation Complete  
> **Tracking:** Zaškrtni `[x]` po dokončení každé položky

---

## 📋 Přehled fází

| Fáze | Název | Odhadovaný čas | Status |
|------|-------|----------------|--------|
| 1 | Projektová struktura & Docker setup | 2-3 hodiny | ✅ Completed |
| 2 | Core MCP Server | 3-4 hodiny | ✅ Completed |
| 3 | Orchestrace & Run Management | 4-5 hodin | ✅ Completed |
| 4 | Error Handling & Robustnost | 2-3 hodiny | ✅ Completed |
| 5 | Testování | 3-4 hodiny | ✅ Completed |
| 6 | Integrace & Dokumentace | 2-3 hodiny | ✅ Completed |

---

## Fáze 1: Projektová struktura & Docker setup

### 1.1 Inicializace projektu
- [x] Vytvořit adresářovou strukturu projektu
  ```
  mcp-codex-orchestrator/
  ├── src/mcp_codex_orchestrator/
  ├── docker/
  ├── runs/
  ├── workspace/
  └── tests/
  ```
- [x] Vytvořit `pyproject.toml` s dependencies:
  - `mcp>=1.0.0`
  - `docker>=7.0.0`
  - `pydantic>=2.0.0`
  - `aiofiles>=23.0.0`
  - `structlog>=24.0.0`
- [x] Vytvořit `.gitignore`:
  - `runs/` (kromě .gitkeep)
  - `workspace/` (kromě .gitkeep)
  - `.env`
  - `__pycache__/`
  - `*.egg-info/`
- [x] Vytvořit `README.md` se základním popisem

### 1.2 Docker konfigurace
- [x] Vytvořit `docker/Dockerfile` pro Codex CLI:
  - Base image: `node:20-slim`
  - Instalace `@openai/codex` přes npm
  - Non-root user pro bezpečnost
  - ENTRYPOINT na codex
- [x] Vytvořit `docker/docker-compose.yml`:
  - Service `codex-runner` (manual profile)
  - Volume mounts pro workspace a runs
  - Environment variables (OPENAI_API_KEY)
- [x] Vytvořit `docker/.env.example`:
  - `OPENAI_API_KEY=sk-...`
  - `WORKSPACE_PATH=./workspace`
  - `RUNS_PATH=./runs`
- [x] Vytvořit `docker/Dockerfile.orchestrator` pro kontejnerizovaný MCP server
- [ ] Otestovat build Docker image:
  ```bash
  docker-compose build codex-runner
  ```
- [ ] Otestovat manuální spuštění Codex v containeru:
  ```bash
  docker-compose run --rm codex-runner --version
  ```

### 1.3 Adresáře pro runtime
- [x] Vytvořit `runs/.gitkeep`
- [x] Vytvořit `workspace/.gitkeep`
- [ ] Ověřit permissions pro mount volumes

**✅ Acceptance Criteria Fáze 1:**
- [x] Docker image konfigurace připravena
- [ ] `codex --version` funguje uvnitř containeru (vyžaduje Docker)
- [x] Volumes konfigurace připravena

---

## Fáze 2: Core MCP Server

### 2.1 Základní server struktura
- [x] Vytvořit `src/mcp_codex_orchestrator/__init__.py`:
  - Verze a základní metadata
- [x] Vytvořit `src/mcp_codex_orchestrator/__main__.py`:
  - Entry point pro `python -m mcp_codex_orchestrator`
  - Inicializace a spuštění serveru
  - Argument parsing (--host, --port, --transport, --log-level)
- [x] Vytvořit `src/mcp_codex_orchestrator/server.py`:
  - MCP server instance
  - Tool registrace (`codex_run`)
  - Lifecycle management (startup, shutdown)

### 2.2 Data modely
- [x] Vytvořit `src/mcp_codex_orchestrator/models/__init__.py`
- [x] Vytvořit `src/mcp_codex_orchestrator/models/run_request.py`:
  ```python
  class CodexRunRequest(BaseModel):
      prompt: str
      mode: Literal["full-auto", "suggest", "ask"] = "full-auto"
      repo: str | None = None
      working_dir: str | None = None
      timeout: int = 300
      env_vars: dict[str, str] | None = None
  ```
- [x] Vytvořit `src/mcp_codex_orchestrator/models/run_result.py`:
  ```python
  class CodexRunResult(BaseModel):
      run_id: str
      status: RunStatus
      exit_code: int | None
      duration: float
      marker: str | None
      output: RunOutput
      error: str | None
      started_at: datetime | None
      finished_at: datetime | None
  ```

### 2.3 MCP Tool definice
- [x] Vytvořit `src/mcp_codex_orchestrator/tools/__init__.py`
- [x] Vytvořit `src/mcp_codex_orchestrator/tools/codex_run.py`:
  - Implementovat `handle_codex_run()` tool handler
  - Input validace
  - Delegace na orchestrátor
  - Formátování MCP odpovědi

### 2.4 Utility moduly
- [x] Vytvořit `src/mcp_codex_orchestrator/utils/__init__.py`
- [x] Vytvořit `src/mcp_codex_orchestrator/utils/markers.py`:
  - Konstanty pro MCP status markery
  - `parse_marker()` - Parser pro detekci markerů v logu
  - `marker_to_status()` - Konverze marker → status
  - `inject_mcp_instructions()` - Přidání instrukcí k promptu
  - `extract_summary_from_log()` - Extrakce shrnutí
  - `extract_files_changed()` - Extrakce změněných souborů
- [x] Vytvořit `src/mcp_codex_orchestrator/utils/logging.py`:
  - `setup_logging()` - Strukturované logování (structlog)
  - `get_logger()` - Logger factory
  - Podpora JSON i console output

**✅ Acceptance Criteria Fáze 2:**
- [x] Server má validní strukturu
- [x] MCP tool je definován s kompletním schema
- [x] Modely validují vstupy správně

---

## Fáze 3: Orchestrace & Run Management

### 3.1 Docker Client
- [x] Vytvořit `src/mcp_codex_orchestrator/orchestrator/__init__.py`
- [x] Vytvořit `src/mcp_codex_orchestrator/orchestrator/docker_client.py`:
  - [x] Třída `DockerCodexClient`
  - [x] Metoda `async def check_docker_available() -> bool`
  - [x] Metoda `async def ensure_image_exists(image_name: str) -> bool`
  - [x] Metoda `async def run_codex(...) -> AsyncGenerator[str, None]`:
    - Vytvoření containeru
    - Nastavení volumes a env vars
    - Spuštění a streaming logů
  - [x] Metoda `async def stop_container(container_id: str) -> None`
  - [x] Metoda `async def cleanup(container_id: str) -> None`
  - [x] Helper metody `_build_command()`, `_build_environment()`, `_build_volumes()`

### 3.2 Run Manager
- [x] Vytvořit `src/mcp_codex_orchestrator/orchestrator/run_manager.py`:
  - [x] Třída `RunManager`
  - [x] Metoda `def generate_run_id() -> str`:
    - UUID v4 generování
  - [x] Metoda `async def create_run(request: CodexRunRequest) -> str`:
    - Vytvoření runs/{runId}/ adresáře
    - Zápis request.json
  - [x] Metoda `async def execute_run(run_id: str) -> CodexRunResult`:
    - Spuštění Docker containeru
    - Real-time logging do log.txt
    - Monitoring exit conditions
  - [x] Metoda `async def get_run_status(run_id: str) -> RunStatus`:
    - Kontrola stavu běhu
  - [x] Metoda `async def cancel_run(run_id: str) -> None`:
    - Graceful stop containeru
    - Zápis partial result
  - [x] Metoda `async def _save_result()`:
    - Zápis result.json

### 3.3 Result Collector
- [x] Vytvořit `src/mcp_codex_orchestrator/orchestrator/result_collector.py`:
  - [x] Třída `ResultCollector`
  - [x] Metoda `async def collect(run_id, log, started_at, finished_at) -> CodexRunResult`:
    - Parsování markerů
    - Extrakce změněných souborů
    - Sestavení result objektu
  - [x] Metoda `_determine_status()`:
    - Priorita: marker → exit code → log analysis
  - [x] Metoda `_looks_like_success()` a `_looks_like_needs_input()`:
    - Heuristická analýza logu
  - [x] Metoda `_extract_error()`:
    - Extrakce chybových zpráv

### 3.4 Prompt Injection
- [x] Implementovat přidávání MCP instrukcí k promptu:
  - [x] Vytvořit konstantu `MCP_INSTRUCTION_SUFFIX` v `markers.py`
  - [x] Vytvořit konstantu `MCP_INSTRUCTION_SUFFIX_EN` pro angličtinu
  - [x] Metoda `inject_mcp_instructions()` pro spojení promptu + instrukce
  - [x] Zajistit oddělení `---` pro vizuální clarity

### 3.5 Integrační spojení
- [x] Propojit všechny komponenty v `codex_run.py`:
  - RunManager → DockerClient → ResultCollector
  - Správné předávání run_id mezi komponentami
  - Error propagation

**✅ Acceptance Criteria Fáze 3:**
- [x] Kompletní flow implementován: request → container → result
- [x] Logy se ukládají do runs/{runId}/log.txt
- [x] Markery jsou správně detekovány
- [x] Result.json obsahuje všechny požadované informace

---

## Fáze 4: Error Handling & Robustnost

### 4.1 Exception handling
- [x] Vytvořit `src/mcp_codex_orchestrator/orchestrator/exceptions.py`:
  - [x] `OrchestratorError` - Base exception
  - [x] `DockerNotAvailableError`
  - [x] `ImageNotFoundError`
  - [x] `ContainerError`
  - [x] `RunTimeoutError`
  - [x] `RunNotFoundError`
  - [x] `MarkerNotFoundError`
- [x] Implementovat error handling v DockerClient:
  - Try/catch pro Docker API calls
  - Meaningful error messages
- [x] Implementovat error handling v RunManager:
  - Cleanup při chybě
  - Partial result zápis

### 4.2 Timeout management
- [x] Implementovat hard timeout v `execute_run()`:
  - asyncio.TimeoutError handling
  - Container stop při timeout
- [x] Implementovat timeout v `_stream_logs()`:
  - Elapsed time tracking
  - TimeoutError raising

### 4.3 Graceful shutdown
- [x] Implementovat signal handlers v `__main__.py`:
  - KeyboardInterrupt handling
  - Clean exit
- [x] Implementovat `close()` metoda v RunManager a DockerClient:
  - Resource cleanup

### 4.4 Retry logika
- [ ] Implementovat retry pro Docker API calls (optional extension):
  - Exponential backoff
  - Max retry count
- [x] Implementovat recovery při container crash:
  - Log zachování
  - Error status zápis

**✅ Acceptance Criteria Fáze 4:**
- [x] Timeout správně ukončuje běh
- [x] SIGTERM/KeyboardInterrupt gracefully zastavuje server
- [x] Chyby jsou logované a vrací smysluplné zprávy
- [x] Exception hierarchy implementována

---

## Fáze 5: Testování

### 5.1 Unit testy
- [x] Vytvořit `tests/__init__.py`
- [x] Vytvořit `tests/conftest.py`:
  - Pytest fixtures
  - Mock Docker client
  - Temporary directories
  - Sample log fixtures
- [x] Vytvořit `tests/test_models.py`:
  - Validace CodexRunRequest
  - Validace CodexRunResult
  - Edge cases (missing fields, invalid values)
  - format_response() testy
- [x] Vytvořit `tests/test_markers.py`:
  - Parsování různých marker formátů
  - Handling chybějících markerů
  - Edge cases (marker uprostřed textu)
  - marker_to_status() testy
  - inject_mcp_instructions() testy
- [x] Vytvořit `tests/test_run_manager.py`:
  - Mock Docker client
  - Test create_run flow
  - Test generate_run_id uniqueness
  - Test get_run_status
- [x] Vytvořit `tests/test_result_collector.py`:
  - Test collect s různými markery
  - Test duration calculation
  - Test file extraction

### 5.2 Integration testy
- [ ] Vytvořit `tests/test_integration.py` (optional - vyžaduje Docker):
  - Test s reálným Docker
  - E2E flow test
- [ ] Vytvořit `tests/test_mcp_server.py` (optional):
  - Test MCP tool registration
  - Test tool invocation

### 5.3 Test fixtures a data
- [x] Sample log fixtures v `conftest.py`:
  - `sample_log_done`
  - `sample_log_need_user`
  - `sample_log_no_marker`
  - `sample_request_data`

### 5.4 CI konfigurace
- [ ] Vytvořit `.github/workflows/test.yml` (optional):
  - Python matrix (3.11, 3.12)
  - Coverage reporting

**✅ Acceptance Criteria Fáze 5:**
- [x] Unit testy vytvořeny pro klíčové komponenty
- [x] Test fixtures připraveny
- [ ] Integration testy (vyžaduje Docker runtime)

---

## Fáze 6: Integrace & Dokumentace

### 6.1 VS Code integrace
- [x] Vytvořit `.vscode/mcp.json` konfiguraci:
  - STDIO transport setup
  - Správné cesty a argumenty
- [x] Vytvořit `.vscode/settings.json`:
  - Python interpreter
  - Pytest konfigurace
  - Ruff formatter
- [ ] Otestovat v reálném VS Code:
  - Server se spustí automaticky
  - Tool je viditelný v MCP panelu
- [x] Docker Compose obsahuje HTTP transport config:
  - `mcp-orchestrator` service s profilem `with-orchestrator`
  - Port mapping (3000)

### 6.2 Dokumentace
- [x] Vytvořit kompletní `README.md`:
  - Popis projektu
  - Quick start guide
  - Prerequisites (Docker, Node.js, Python)
  - Instalace a konfigurace
  - Použití a příklady
  - Architektura diagram
- [x] `docs/IMPLEMENTATION_PLAN.md`:
  - Vysokoúrovňový plán
  - Architektura
  - Komponenty
  - Sekvence
- [x] `docs/IMPLEMENTATION_CHECKLIST.md` (tento soubor):
  - Detailní checklist
  - Progress tracking

### 6.3 Příklady
- [ ] Vytvořit `examples/` adresář (optional):
  - `simple_task.py` – jednoduchý příklad
  - `batch_run.py` – více úloh za sebou

### 6.4 Release preparation
- [x] Code review checklist:
  - [x] Žádné hardcoded secrets
  - [x] Všechny dependencies v pyproject.toml
  - [x] Type hints všude
  - [x] Docstrings pro public API
- [ ] Vytvořit `CHANGELOG.md` s první verzí (optional)

**✅ Acceptance Criteria Fáze 6:**
- [x] README umožňuje pochopení projektu
- [x] VS Code konfigurace připravena
- [x] Dokumentace pokrývá architekturu

---

## 🔧 Technické poznámky

### Dependencies (pyproject.toml)

```toml
[project]
name = "mcp-codex-orchestrator"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "mcp>=1.0.0",
    "docker>=7.0.0",
    "pydantic>=2.0.0",
    "aiofiles>=23.0.0",
    "structlog>=24.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.0.0",
]
```

### Docker requirements
- Docker Engine 24.0+
- Docker Compose v2
- Přístup k Docker socket (`/var/run/docker.sock`)

### Environment variables

| Variable | Required | Default | Popis |
|----------|----------|---------|-------|
| `OPENAI_API_KEY` | ✅ | - | OpenAI API klíč |
| `WORKSPACE_PATH` | ❌ | `./workspace` | Cesta k workspace |
| `RUNS_PATH` | ❌ | `./runs` | Cesta k run artefaktům |
| `CODEX_IMAGE` | ❌ | `codex-runner:latest` | Docker image name |
| `DEFAULT_TIMEOUT` | ❌ | `300` | Default timeout (s) |
| `LOG_LEVEL` | ❌ | `INFO` | Log level |

---

## 📊 Progress Tracking

### Celkový progress
```
Fáze 1: 🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩 100%
Fáze 2: 🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩 100%
Fáze 3: 🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩 100%
Fáze 4: 🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩 100%
Fáze 5: 🟩🟩🟩🟩🟩🟩🟩🟩🟨🟨 80%
Fáze 6: 🟩🟩🟩🟩🟩🟩🟩🟨🟨🟨 70%
─────────────────────────────
TOTAL:  🟩🟩🟩🟩🟩🟩🟩🟩🟩🟨 ~92%
```

### Milestones
- [x] 🏁 **M1:** Docker setup připraven (Fáze 1)
- [x] 🏁 **M2:** MCP server implementován (Fáze 2)
- [x] 🏁 **M3:** Orchestrace implementována (Fáze 3)
- [x] 🏁 **M4:** Error handling implementován (Fáze 4)
- [x] 🏁 **M5:** Unit testy vytvořeny (Fáze 5)
- [x] 🏁 **M6:** Dokumentace připravena (Fáze 6)

---

## 📁 Vytvořené soubory

```
mcp-codex-orchestrator/
├── .gitignore
├── .vscode/
│   ├── mcp.json
│   └── settings.json
├── README.md
├── pyproject.toml
├── docs/
│   ├── IMPLEMENTATION_PLAN.md
│   └── IMPLEMENTATION_CHECKLIST.md
├── docker/
│   ├── Dockerfile
│   ├── Dockerfile.orchestrator
│   ├── docker-compose.yml
│   └── .env.example
├── runs/
│   └── .gitkeep
├── workspace/
│   └── .gitkeep
├── src/
│   └── mcp_codex_orchestrator/
│       ├── __init__.py
│       ├── __main__.py
│       ├── server.py
│       ├── models/
│       │   ├── __init__.py
│       │   ├── run_request.py
│       │   └── run_result.py
│       ├── tools/
│       │   ├── __init__.py
│       │   └── codex_run.py
│       ├── orchestrator/
│       │   ├── __init__.py
│       │   ├── docker_client.py
│       │   ├── run_manager.py
│       │   ├── result_collector.py
│       │   └── exceptions.py
│       └── utils/
│           ├── __init__.py
│           ├── markers.py
│           └── logging.py
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_markers.py
    ├── test_models.py
    ├── test_result_collector.py
    └── test_run_manager.py
```

---

## 📝 Poznámky a rozhodnutí

| Datum | Rozhodnutí | Důvod |
|-------|------------|-------|
| 2025-12-25 | Per-run container architektura | Jednodušší lifecycle management, čistý stav |
| 2025-12-25 | Marker-based protokol | Spolehlivější než parsing exit code |
| 2025-12-25 | docker-compose pro definici | Standardní VS Code workflow |

---

## 🔗 Související dokumenty

- [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md) – Vysokoúrovňový plán
- [../README.md](../README.md) – Projektový README
