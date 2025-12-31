# MCP Codex Orchestrator - Technická dokumentace modulu

> **Verze dokumentace:** 1.0.0  
> **Verze modulu:** 0.1.0  
> **Datum:** 31. prosince 2025  
> **Úroveň:** 3/4 - Module Technical Documentation

---

## 📋 Obsah

1. [Přehled modulu](#přehled-modulu)
2. [Struktura adresářů](#struktura-adresářů)
3. [Klíčové komponenty](#klíčové-komponenty)
4. [Docker architektura](#docker-architektura)
5. [MCP Tool: codex_run](#mcp-tool-codex_run)
6. [Autentizace](#autentizace)
7. [Konfigurace](#konfigurace)
8. [Testování](#testování)

---

## Přehled modulu

**MCP Codex Orchestrator** je MCP server pro orchestraci OpenAI Codex CLI běhů v izolovaných Docker kontejnerech.

### Technické charakteristiky

| Vlastnost | Hodnota |
|-----------|---------|
| **Jazyk** | Python 3.11+ |
| **Protokol** | MCP (Model Context Protocol) |
| **Transport** | stdio |
| **Container Runtime** | Docker Engine 24.0+ |
| **Package** | `mcp-codex-orchestrator` |
| **Entry point** | `mcp_codex_orchestrator.__main__:main` |

### Klíčové vlastnosti

- 🐳 **Per-run container** – každý běh v čistém izolovaném prostředí
- 🔧 **MCP tool `codex_run`** – standardní MCP interface
- 📝 **Strukturované logování** – všechny běhy jsou logovány
- ⏱️ **Timeout management** – automatické ukončení při překročení limitu
- 🔄 **Marker-based protokol** – spolehlivá detekce dokončení úlohy

### Závislosti

```toml
[dependencies]
mcp = ">=1.0.0"
docker = ">=7.0.0"
pydantic = ">=2.0.0"
aiofiles = ">=23.0.0"
structlog = ">=24.0.0"
```

---

## Struktura adresářů

```
mcp-codex-orchestrator/
├── pyproject.toml              # Package configuration
├── README.md                   # Module documentation
├── src/
│   └── mcp_codex_orchestrator/
│       ├── __init__.py         # Package init
│       ├── __main__.py         # Entry point
│       ├── server.py           # MCP server implementation
│       ├── models/
│       │   ├── __init__.py
│       │   └── schemas.py      # Pydantic models
│       ├── orchestrator/
│       │   ├── __init__.py
│       │   └── runner.py       # Docker container orchestration
│       ├── tools/
│       │   ├── __init__.py
│       │   └── codex_run.py    # codex_run tool implementation
│       └── utils/
│           ├── __init__.py
│           ├── logging.py      # Structured logging
│           └── markers.py      # Completion markers
├── docker/
│   ├── Dockerfile              # Codex runner image
│   ├── docker-compose.yml      # Compose configuration
│   └── .env.example            # Environment template
├── workspace/                  # Mounted workspace for Codex
├── runs/                       # Run logs and artifacts
├── scripts/
│   ├── setup-auth.ps1          # Authentication setup
│   └── build-image.ps1         # Docker image build
└── tests/
    └── test_*.py
```

---

## Klíčové komponenty

### 1. server.py - MCP Server

```python
import mcp.server.stdio
import mcp.types as types
from mcp.server.lowlevel import Server

from .tools.codex_run import handle_codex_run
from .orchestrator.runner import CodexRunner

def create_server() -> Server:
    """Create and configure MCP server."""
    server = Server("mcp-codex-orchestrator")
    runner = CodexRunner()
    
    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name="codex_run",
                description=(
                    "Spustí OpenAI Codex CLI v izolovaném Docker kontejneru. "
                    "Codex provede zadanou úlohu nad workspace a vrátí výsledek."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": "Zadání pro Codex CLI - co má udělat"
                        },
                        "mode": {
                            "type": "string",
                            "enum": ["full-auto", "suggest", "ask"],
                            "default": "full-auto",
                            "description": "Režim běhu Codex CLI"
                        },
                        "timeout": {
                            "type": "integer",
                            "default": 300,
                            "description": "Timeout v sekundách"
                        },
                        "repo": {
                            "type": "string",
                            "description": "Cesta k repository (default: aktuální workspace)"
                        },
                        "working_dir": {
                            "type": "string",
                            "description": "Working directory uvnitř repository"
                        }
                    },
                    "required": ["prompt"]
                }
            )
        ]
    
    @server.call_tool()
    async def call_tool(
        name: str, 
        arguments: dict
    ) -> list[types.TextContent]:
        if name == "codex_run":
            result = await handle_codex_run(runner, arguments)
            return [types.TextContent(type="text", text=result)]
        raise ValueError(f"Unknown tool: {name}")
    
    return server
```

### 2. orchestrator/runner.py - Docker Orchestration

```python
import docker
import asyncio
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from ..models.schemas import CodexRunRequest, CodexRunResult
from ..utils.markers import COMPLETION_MARKER, parse_output

@dataclass
class ContainerConfig:
    image: str = "codex-runner:latest"
    workspace_mount: str = "/app"
    auth_mount: str = "/root/.codex"
    network_mode: str = "bridge"

class CodexRunner:
    """Orchestrates Codex CLI runs in Docker containers."""
    
    def __init__(self, config: Optional[ContainerConfig] = None):
        self.config = config or ContainerConfig()
        self.client = docker.from_env()
        self._ensure_image_exists()
    
    def _ensure_image_exists(self):
        """Check if codex-runner image exists."""
        try:
            self.client.images.get(self.config.image)
        except docker.errors.ImageNotFound:
            raise RuntimeError(
                f"Docker image '{self.config.image}' not found. "
                "Run: docker-compose build codex-runner"
            )
    
    async def run(self, request: CodexRunRequest) -> CodexRunResult:
        """
        Execute Codex CLI in a Docker container.
        
        Args:
            request: CodexRunRequest with prompt, mode, timeout, etc.
            
        Returns:
            CodexRunResult with success status, output, and file changes.
        """
        container = None
        try:
            # Create container
            container = self.client.containers.create(
                image=self.config.image,
                command=self._build_command(request),
                volumes=self._build_volumes(request),
                environment=self._build_env(request),
                network_mode=self.config.network_mode,
                detach=True
            )
            
            # Start container
            container.start()
            
            # Wait for completion with timeout
            exit_code = await self._wait_for_completion(
                container, 
                timeout=request.timeout
            )
            
            # Collect output
            logs = container.logs().decode("utf-8")
            
            # Parse output for file changes
            files_changed = self._parse_file_changes(logs)
            
            return CodexRunResult(
                success=exit_code == 0,
                exit_code=exit_code,
                output=logs,
                files_changed=files_changed,
                container_id=container.id[:12]
            )
            
        except asyncio.TimeoutError:
            if container:
                container.kill()
            return CodexRunResult(
                success=False,
                exit_code=-1,
                output="Timeout exceeded",
                files_changed=[],
                error="Execution timeout"
            )
            
        finally:
            if container:
                container.remove(force=True)
    
    def _build_command(self, request: CodexRunRequest) -> list[str]:
        """Build Codex CLI command."""
        cmd = [
            "codex",
            "--approval-mode", request.mode,
            "--quiet",
            request.prompt
        ]
        
        if request.working_dir:
            cmd.extend(["--cwd", request.working_dir])
        
        return cmd
    
    def _build_volumes(self, request: CodexRunRequest) -> dict:
        """Build volume mounts."""
        workspace = request.repo or "/workspace"
        auth_path = Path.home() / ".codex"
        
        return {
            str(workspace): {
                "bind": self.config.workspace_mount,
                "mode": "rw"
            },
            str(auth_path): {
                "bind": self.config.auth_mount,
                "mode": "ro"
            }
        }
    
    async def _wait_for_completion(
        self, 
        container, 
        timeout: int
    ) -> int:
        """Wait for container to complete with timeout."""
        loop = asyncio.get_event_loop()
        
        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(
                    None, 
                    lambda: container.wait()
                ),
                timeout=timeout
            )
            return result["StatusCode"]
        except asyncio.TimeoutError:
            raise
```

### 3. models/schemas.py - Pydantic Models

```python
from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class CodexRunRequest(BaseModel):
    """Request model for codex_run tool."""
    
    prompt: str = Field(
        ...,
        description="Task description for Codex CLI"
    )
    mode: Literal["full-auto", "suggest", "ask"] = Field(
        default="full-auto",
        description="Codex approval mode"
    )
    timeout: int = Field(
        default=300,
        ge=10,
        le=3600,
        description="Execution timeout in seconds"
    )
    repo: Optional[str] = Field(
        default=None,
        description="Path to repository"
    )
    working_dir: Optional[str] = Field(
        default=None,
        description="Working directory inside repo"
    )
    env_vars: Optional[dict[str, str]] = Field(
        default=None,
        description="Extra environment variables"
    )

class CodexRunResult(BaseModel):
    """Result model from codex_run execution."""
    
    success: bool = Field(
        ...,
        description="Whether execution was successful"
    )
    exit_code: int = Field(
        ...,
        description="Container exit code"
    )
    output: str = Field(
        ...,
        description="Stdout + stderr from execution"
    )
    files_changed: List[str] = Field(
        default_factory=list,
        description="List of files modified by Codex"
    )
    container_id: Optional[str] = Field(
        default=None,
        description="Docker container ID"
    )
    execution_time_ms: Optional[int] = Field(
        default=None,
        description="Execution time in milliseconds"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if failed"
    )
```

### 4. utils/logging.py - Structured Logging

```python
import structlog
from pathlib import Path
from datetime import datetime

def configure_logging(runs_dir: Path) -> structlog.BoundLogger:
    """Configure structured logging for Codex runs."""
    
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    return structlog.get_logger()

def log_run(
    logger: structlog.BoundLogger,
    request: "CodexRunRequest",
    result: "CodexRunResult",
    run_id: str
):
    """Log a Codex run with structured data."""
    logger.info(
        "codex_run_completed",
        run_id=run_id,
        prompt=request.prompt[:100],
        mode=request.mode,
        success=result.success,
        exit_code=result.exit_code,
        files_changed=len(result.files_changed),
        execution_time_ms=result.execution_time_ms
    )
```

---

## Docker architektura

### Dockerfile

```dockerfile
# mcp-codex-orchestrator/docker/Dockerfile
FROM node:18-slim

# System dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Codex CLI
RUN npm install -g @openai/codex

# Configure git (required by Codex)
RUN git config --global user.email "codex@localhost" \
    && git config --global user.name "Codex Runner"

# Setup workspace
WORKDIR /app
VOLUME /app

# Codex auth directory
VOLUME /root/.codex

# Default entrypoint
ENTRYPOINT ["codex"]
CMD ["--help"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  codex-runner:
    build:
      context: .
      dockerfile: Dockerfile
    image: codex-runner:latest
    volumes:
      - ../workspace:/app
      - ${USERPROFILE}/.codex:/root/.codex:ro
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY:-}
      - CODEX_QUIET_MODE=true
    network_mode: bridge
    # Container is created per-run, not kept running
    profiles:
      - tools

  # Development helper
  codex-shell:
    image: codex-runner:latest
    volumes:
      - ../workspace:/app
      - ${USERPROFILE}/.codex:/root/.codex:ro
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY:-}
    entrypoint: /bin/bash
    stdin_open: true
    tty: true
    profiles:
      - dev
```

### Container Lifecycle

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        CONTAINER LIFECYCLE                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. CREATE                                                                  │
│     docker.containers.create(                                               │
│         image="codex-runner:latest",                                        │
│         command=["codex", "--approval-mode", "full-auto", prompt],          │
│         volumes={workspace: "/app", auth: "/root/.codex"}                   │
│     )                                                                       │
│           │                                                                 │
│           ▼                                                                 │
│  2. START                                                                   │
│     container.start()                                                       │
│           │                                                                 │
│           ▼                                                                 │
│  3. EXECUTE                                                                 │
│     ┌───────────────────────────────────────────────────────────────────┐  │
│     │  Container                                                         │  │
│     │  ├── codex CLI running                                             │  │
│     │  ├── Reading files from /app                                       │  │
│     │  ├── Generating code changes                                       │  │
│     │  ├── Writing files to /app                                         │  │
│     │  └── git commit (if successful)                                    │  │
│     └───────────────────────────────────────────────────────────────────┘  │
│           │                                                                 │
│           ▼                                                                 │
│  4. WAIT                                                                    │
│     container.wait(timeout=300)                                             │
│           │                                                                 │
│           ▼                                                                 │
│  5. COLLECT                                                                 │
│     logs = container.logs()                                                 │
│     files_changed = parse_git_diff()                                        │
│           │                                                                 │
│           ▼                                                                 │
│  6. CLEANUP                                                                 │
│     container.remove(force=True)                                            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## MCP Tool: codex_run

### Vstupní parametry

| Parametr | Typ | Povinný | Default | Popis |
|----------|-----|---------|---------|-------|
| `prompt` | string | ✅ | - | Zadání úlohy pro Codex |
| `mode` | enum | ❌ | full-auto | Režim schvalování |
| `timeout` | int | ❌ | 300 | Timeout v sekundách |
| `repo` | string | ❌ | workspace/ | Cesta k repository |
| `working_dir` | string | ❌ | - | Working directory |
| `env_vars` | object | ❌ | - | Extra env variables |

### Approval modes

| Mode | Popis | Použití |
|------|-------|---------|
| `full-auto` | Automatické schválení všech změn | Důvěryhodné úlohy |
| `suggest` | Pouze navrhuje změny | Review mode |
| `ask` | Ptá se na každou změnu | Interaktivní mode |

### Příklad volání

```json
{
  "tool": "codex_run",
  "arguments": {
    "prompt": "Refactor the authentication module to use async/await patterns",
    "mode": "full-auto",
    "timeout": 600,
    "working_dir": "src/auth"
  }
}
```

### Příklad odpovědi

```json
{
  "success": true,
  "exit_code": 0,
  "output": "Successfully refactored authentication module.\n\nChanges made:\n- Converted login() to async\n- Added await for database calls\n- Updated session management\n\nFiles modified: 3",
  "files_changed": [
    "src/auth/login.py",
    "src/auth/session.py",
    "src/auth/middleware.py"
  ],
  "container_id": "abc123def456",
  "execution_time_ms": 45230
}
```

---

## Autentizace

### Metody autentizace

#### Metoda 1: ChatGPT Plus (Doporučeno)

```powershell
# Instalace Codex CLI
npm install -g @openai/codex

# Login pomocí ChatGPT účtu
codex login

# Ověření
Test-Path "$env:USERPROFILE\.codex\auth.json"
```

#### Metoda 2: OpenAI API Key

```powershell
# Nastavení v docker/.env
cp docker/.env.example docker/.env

# Editovat .env
OPENAI_API_KEY=sk-...
```

### Auth flow v kontejneru

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          AUTHENTICATION FLOW                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Host Machine                          Container                            │
│  ┌─────────────────────┐              ┌─────────────────────┐              │
│  │ ~/.codex/           │              │ /root/.codex/       │              │
│  │ └── auth.json       │──────────────│ └── auth.json (RO)  │              │
│  │                     │   Mount      │                     │              │
│  └─────────────────────┘   (ro)       └─────────────────────┘              │
│                                              │                              │
│                                              ▼                              │
│                                       ┌─────────────────────┐              │
│                                       │ Codex CLI           │              │
│                                       │ ├── Read auth.json  │              │
│                                       │ ├── Validate token  │              │
│                                       │ └── Execute prompt  │              │
│                                       └─────────────────────┘              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Konfigurace

### Environment variables

| Proměnná | Povinná | Default | Popis |
|----------|---------|---------|-------|
| `CODEX_IMAGE` | ❌ | codex-runner:latest | Docker image |
| `CODEX_WORKSPACE` | ❌ | ./workspace | Workspace path |
| `CODEX_TIMEOUT` | ❌ | 300 | Default timeout |
| `OPENAI_API_KEY` | ❌ | - | API key (if not using login) |
| `PYTHONPATH` | ✅ | - | Path to src/ |

### MCP konfigurace

```json
{
  "mcpServers": {
    "mcp-codex-orchestrator": {
      "command": "python",
      "args": ["-m", "mcp_codex_orchestrator"],
      "env": {
        "PYTHONPATH": "K:/Data_science_projects/MCP_Prompt_Broker/mcp-codex-orchestrator/src",
        "CODEX_WORKSPACE": "K:/Data_science_projects/MCP_Prompt_Broker/mcp-codex-orchestrator/workspace"
      }
    }
  }
}
```

---

## Testování

### Struktura testů

```
tests/
├── test_server.py          # MCP server tests
├── test_runner.py          # Docker runner tests
├── test_models.py          # Schema validation tests
└── conftest.py             # Fixtures
```

### Spuštění testů

```bash
# Všechny testy
pytest tests/ -v

# S coverage
pytest tests/ --cov=mcp_codex_orchestrator --cov-report=term-missing

# Bez Docker (mock)
pytest tests/ -v -m "not docker"
```

### Příklad testu

```python
# tests/test_runner.py
import pytest
from mcp_codex_orchestrator.orchestrator.runner import CodexRunner
from mcp_codex_orchestrator.models.schemas import CodexRunRequest

@pytest.fixture
def runner():
    return CodexRunner()

@pytest.mark.docker
@pytest.mark.asyncio
async def test_codex_run_simple(runner):
    request = CodexRunRequest(
        prompt="Create a hello.py file that prints 'Hello, World!'",
        mode="full-auto",
        timeout=60
    )
    
    result = await runner.run(request)
    
    assert result.success is True
    assert result.exit_code == 0
    assert "hello.py" in result.files_changed
```

---

## Známé limitace

| Limitace | Popis | Workaround |
|----------|-------|------------|
| Docker required | Vyžaduje Docker Engine | WSL2 na Windows |
| Container overhead | Startup time ~2-5s | Reuse kontejneru plánován |
| Network isolation | Omezený přístup k síti | network_mode: host |
| Windows paths | Problémy s cestami | Absolutní cesty |

---

## Troubleshooting

### Časté problémy

| Problém | Příčina | Řešení |
|---------|---------|--------|
| Image not found | Image nebyl buildnut | `docker-compose build codex-runner` |
| Auth failed | Chybí auth.json | `codex login` na hostu |
| Timeout | Dlouhá úloha | Zvýšit timeout parameter |
| Permission denied | Volume mount | Ověřit cesty a oprávnění |

### Diagnostické příkazy

```powershell
# Ověření Docker
docker images | Select-String codex

# Test image
docker run --rm codex-runner:latest codex --version

# Test auth
docker run --rm -v ${env:USERPROFILE}/.codex:/root/.codex:ro codex-runner:latest codex auth status

# Interaktivní shell
docker-compose --profile dev run codex-shell
```

---

## Související dokumenty

- **Architektura:** [../architecture/ARCHITECTURE.md](../architecture/ARCHITECTURE.md)
- **Data Flow:** [../architecture/DATA_FLOW.md](../architecture/DATA_FLOW.md)
- **API Reference:** [../api/MCP_TOOLS.md](../api/MCP_TOOLS.md)

---

*Tato dokumentace je součástí 4-úrovňové dokumentační struktury projektu MCP Prompt Broker.*
