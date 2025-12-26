# MCP Codex Orchestrator – Implementační plán

> **Verze:** 1.0  
> **Datum:** 2025-12-25  
> **Autor:** GitHub Copilot  
> **Status:** Draft

---

## 1. Přehled projektu

### 1.1 Cíl
Vytvořit **MCP server (Prompt Broker rozšíření)**, který orchestruje běhy OpenAI Codex CLI v izolovaných Docker kontejnerech. Server vystavuje MCP tool `codex.run()` a zajišťuje plánování, logování, error handling a komunikaci výsledků.

### 1.2 Klíčové vlastnosti
- **Per-run container** architektura (čistý start pro každý běh)
- **Docker Compose** konfigurace pro snadné nasazení ve VS Code
- **Sdílený mount** pro workspace a run artefakty
- **Marker-based protokol** pro detekci dokončení úlohy
- **Timeout management** a graceful shutdown

---

## 2. Architektura

### 2.1 Komponenty

```
┌─────────────────────────────────────────────────────────────────┐
│                        VS Code                                   │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                   MCP Client (Copilot)                      ││
│  └─────────────────────────────────────────────────────────────┘│
│                              │                                   │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │              MCP Codex Orchestrator Server                  ││
│  │  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   ││
│  │  │ Tool:       │  │ Run Manager  │  │ Result Collector │   ││
│  │  │ codex.run() │  │              │  │                  │   ││
│  │  └─────────────┘  └──────────────┘  └──────────────────┘   ││
│  └─────────────────────────────────────────────────────────────┘│
│                              │                                   │
└──────────────────────────────┼───────────────────────────────────┘
                               │ Docker API / docker-compose
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Docker Runtime                              │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │              Per-Run Container (ephemeral)                  ││
│  │  ┌─────────────────────────────────────────────────────────┐││
│  │  │                    Codex CLI                            │││
│  │  │   codex --full-auto "<prompt with MCP instructions>"    │││
│  │  └─────────────────────────────────────────────────────────┘││
│  │                              │                              ││
│  │  ┌───────────────────────────┴───────────────────────────┐ ││
│  │  │                  Mounted Volumes                       │ ││
│  │  │  /workspace (repo)     /runs/{runId}/ (logs, results) │ ││
│  │  └───────────────────────────────────────────────────────┘ ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Adresářová struktura projektu

```
mcp-codex-orchestrator/
├── docs/
│   ├── IMPLEMENTATION_PLAN.md      # Tento soubor
│   └── IMPLEMENTATION_CHECKLIST.md # Podrobný checklist
├── src/
│   └── mcp_codex_orchestrator/
│       ├── __init__.py
│       ├── __main__.py             # Entry point
│       ├── server.py               # MCP server implementace
│       ├── tools/
│       │   ├── __init__.py
│       │   └── codex_run.py        # codex.run() tool
│       ├── orchestrator/
│       │   ├── __init__.py
│       │   ├── run_manager.py      # Správa běhů
│       │   ├── docker_client.py    # Docker API wrapper
│       │   └── result_collector.py # Sběr výsledků
│       ├── models/
│       │   ├── __init__.py
│       │   ├── run_request.py      # Request model
│       │   └── run_result.py       # Result model
│       └── utils/
│           ├── __init__.py
│           ├── markers.py          # MCP status markers
│           └── logging.py          # Logging utilities
├── docker/
│   ├── Dockerfile                  # Codex CLI container image
│   ├── docker-compose.yml          # Compose konfigurace
│   └── .env.example                # Environment variables template
├── runs/                           # Run artefakty (gitignored)
│   └── .gitkeep
├── workspace/                      # Mountovaný workspace (gitignored)
│   └── .gitkeep
├── tests/
│   ├── __init__.py
│   ├── test_run_manager.py
│   ├── test_docker_client.py
│   └── test_result_collector.py
├── pyproject.toml
├── README.md
└── .gitignore
```

---

## 3. Detailní návrh komponent

### 3.1 MCP Server (`server.py`)

**Odpovědnosti:**
- Registrace MCP toolů
- Zpracování příchozích požadavků
- Delegace na orchestrátor

**MCP Tool definice:**

```python
@mcp_tool(name="codex.run")
async def codex_run(
    prompt: str,
    mode: str = "full-auto",           # full-auto | suggest | ask
    repo: str | None = None,            # Cesta k repo (default: aktuální workspace)
    timeout: int = 300,                 # Timeout v sekundách
    working_dir: str | None = None,     # Working directory uvnitř repo
    env_vars: dict[str, str] | None = None,  # Extra environment variables
) -> CodexRunResult:
    """
    Spustí Codex CLI v izolovaném Docker kontejneru.
    """
```

### 3.2 Run Manager (`run_manager.py`)

**Odpovědnosti:**
- Generování unikátních `runId`
- Příprava run adresáře a request.json
- Koordinace Docker kontejneru
- Monitoring běhu (timeout, markery)
- Ukládání výsledků

**Životní cyklus běhu:**

```
1. create_run(request) → runId
   ├── Vytvoř runs/{runId}/
   ├── Zapiš runs/{runId}/request.json
   └── Vrať runId

2. execute_run(runId)
   ├── Spusť Docker container
   ├── Streamuj stdout/stderr → runs/{runId}/log.txt
   ├── Monitoruj:
   │   ├── Exit code procesu
   │   ├── Markery (::MCP_STATUS::DONE, ::MCP_STATUS::NEED_USER)
   │   └── Hard timeout
   └── Ukonči při splnění podmínky

3. collect_result(runId) → RunResult
   ├── Načti log.txt
   ├── Parsuj markery a status
   ├── Zapiš runs/{runId}/result.json
   └── Vrať strukturovaný výsledek
```

### 3.3 Docker Client (`docker_client.py`)

**Odpovědnosti:**
- Abstrakce nad Docker SDK
- Správa kontejnerů (create, start, logs, stop, remove)
- Volume mounting
- Environment variables injection

**Klíčové metody:**

```python
class DockerCodexClient:
    async def run_codex(
        self,
        run_id: str,
        prompt: str,
        mode: str,
        workspace_path: Path,
        runs_path: Path,
        timeout: int,
        env_vars: dict[str, str] | None = None,
    ) -> AsyncGenerator[str, None]:
        """Spustí Codex container a streamuje výstup."""
        
    async def stop_container(self, container_id: str) -> None:
        """Zastaví běžící container."""
        
    async def cleanup(self, container_id: str) -> None:
        """Odstraní container a související resources."""
```

### 3.4 Result Collector (`result_collector.py`)

**Odpovědnosti:**
- Parsování log souboru
- Detekce MCP markerů
- Extrakce změněných souborů
- Sestavení strukturovaného výsledku

**Status markery:**

| Marker | Význam |
|--------|--------|
| `::MCP_STATUS::DONE` | Úloha dokončena úspěšně |
| `::MCP_STATUS::NEED_USER` | Vyžadován zásah uživatele |
| `::MCP_STATUS::ERROR` | Interní chyba (přidáno orchestrátorem) |
| `::MCP_STATUS::TIMEOUT` | Timeout (přidáno orchestrátorem) |

---

## 4. Docker konfigurace

### 4.1 Dockerfile

```dockerfile
# Codex CLI container
FROM node:20-slim

# Install Codex CLI
RUN npm install -g @openai/codex

# Create non-root user
RUN useradd -m -s /bin/bash codex
USER codex

WORKDIR /workspace

ENTRYPOINT ["codex"]
```

### 4.2 docker-compose.yml

```yaml
version: "3.8"

services:
  codex-runner:
    build:
      context: .
      dockerfile: Dockerfile
    volumes:
      - ${WORKSPACE_PATH:-./workspace}:/workspace:rw
      - ${RUNS_PATH:-./runs}:/runs:rw
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - CODEX_QUIET_MODE=1
    working_dir: /workspace
    # Container je spouštěn per-run, ne jako service
    profiles:
      - manual
    
  # MCP Orchestrator server (volitelně jako service)
  mcp-orchestrator:
    build:
      context: ../
      dockerfile: docker/Dockerfile.orchestrator
    volumes:
      - ${WORKSPACE_PATH:-./workspace}:/workspace:rw
      - ${RUNS_PATH:-./runs}:/runs:rw
      - /var/run/docker.sock:/var/run/docker.sock:ro
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    ports:
      - "3000:3000"
    profiles:
      - with-orchestrator
```

---

## 5. Komunikační protokol

### 5.1 Request format (`request.json`)

```json
{
  "runId": "uuid-v4",
  "timestamp": "2025-12-25T10:30:00Z",
  "prompt": "Implementuj funkci pro validaci emailu",
  "mode": "full-auto",
  "repo": "/workspace/my-project",
  "workingDir": "src/validators",
  "timeout": 300,
  "envVars": {
    "DEBUG": "1"
  }
}
```

### 5.2 Result format (`result.json`)

```json
{
  "runId": "uuid-v4",
  "status": "done",
  "exitCode": 0,
  "duration": 45.2,
  "marker": "::MCP_STATUS::DONE",
  "output": {
    "summary": "Vytvořen soubor src/validators/email.py",
    "filesChanged": [
      "src/validators/email.py",
      "tests/test_email.py"
    ],
    "fullLog": "..."
  },
  "error": null
}
```

### 5.3 Prompt injection (MCP instrukce)

Orchestrátor automaticky přidává na konec každého promptu:

```
---
Na konci své odpovědi vypiš na samostatný poslední řádek přesně jeden z následujících markerů:
::MCP_STATUS::DONE pokud je úloha dokončena.
::MCP_STATUS::NEED_USER pokud je nutný zásah uživatele nebo chybí informace.
Nevypisuj žádný jiný text za markerem.
```

---

## 6. Error handling

### 6.1 Typy chyb

| Chyba | Příčina | Řešení |
|-------|---------|--------|
| `DockerNotAvailable` | Docker daemon neběží | Vrať chybovou MCP odpověď |
| `ImageNotFound` | Codex image neexistuje | Auto-build nebo chybová zpráva |
| `Timeout` | Běh překročil limit | Forceful stop + status TIMEOUT |
| `ContainerCrash` | Codex CLI havaroval | Zachyť exit code, loguj |
| `MarkerNotFound` | Codex nevypsal marker | Fallback na exit code analýzu |

### 6.2 Graceful shutdown

1. Při SIGTERM/SIGINT:
   - Zapiš do control souboru `runs/{runId}/STOP`
   - Pošli SIGTERM do containeru
   - Počkej max 10s na graceful exit
   - Pokud neukončí, SIGKILL
   - Zapiš partial result

---

## 7. Integrace s VS Code

### 7.1 MCP konfigurace

Přidání do `.vscode/mcp.json`:

```json
{
  "servers": {
    "codex-orchestrator": {
      "type": "stdio",
      "command": "python",
      "args": ["-m", "mcp_codex_orchestrator"],
      "cwd": "${workspaceFolder}/mcp-codex-orchestrator"
    }
  }
}
```

### 7.2 Alternativa: HTTP transport

Pro komplexnější scénáře lze použít HTTP transport s docker-compose:

```json
{
  "servers": {
    "codex-orchestrator": {
      "type": "http",
      "url": "http://localhost:3000/mcp"
    }
  }
}
```

---

## 8. Fáze implementace

### Fáze 1: Základní infrastruktura (MVP)
- [ ] Projektová struktura a konfigurace
- [ ] Dockerfile pro Codex CLI
- [ ] docker-compose.yml
- [ ] Základní MCP server s jedním toolem

### Fáze 2: Core orchestrace
- [ ] Run Manager implementace
- [ ] Docker client wrapper
- [ ] Log streaming a ukládání
- [ ] Marker detekce

### Fáze 3: Error handling & robustnost
- [ ] Timeout management
- [ ] Graceful shutdown
- [ ] Error recovery
- [ ] Retry logika

### Fáze 4: Integrace & testování
- [ ] VS Code integrace
- [ ] Unit testy
- [ ] Integration testy
- [ ] E2E test scénáře

### Fáze 5: Polish & dokumentace
- [ ] README a uživatelská dokumentace
- [ ] Příklady použití
- [ ] Troubleshooting guide

---

## 9. Rizika a mitigace

| Riziko | Pravděpodobnost | Dopad | Mitigace |
|--------|-----------------|-------|----------|
| Docker socket permission issues | Střední | Vysoký | Dokumentace, helper skripty |
| Codex CLI API změny | Nízká | Střední | Abstrakce, pinned verze |
| Race conditions v run manageru | Střední | Střední | Async locks, idempotentní operace |
| Memory leaks při dlouhých bězích | Nízká | Střední | Per-run containers, monitoring |
| OpenAI API rate limits | Střední | Střední | Retry s backoff, queue management |

---

## 10. Metriky úspěchu

- [ ] Úspěšný E2E běh: prompt → Docker container → výsledek
- [ ] Průměrná latence start containeru < 5s
- [ ] Správná detekce markerů v 100% případů
- [ ] Graceful handling timeoutů
- [ ] Integrace s VS Code funguje bez manuální konfigurace

---

## Přílohy

### A. Referenční zdroje
- [OpenAI Codex CLI dokumentace](https://github.com/openai/codex)
- [MCP Protocol specifikace](https://modelcontextprotocol.io)
- [Docker SDK for Python](https://docker-py.readthedocs.io)

### B. Související soubory
- [IMPLEMENTATION_CHECKLIST.md](./IMPLEMENTATION_CHECKLIST.md) – Podrobný checklist úkolů
