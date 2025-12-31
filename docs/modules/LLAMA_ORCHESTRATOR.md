# Llama Orchestrator - Technická dokumentace modulu

> **Verze dokumentace:** 1.0.0  
> **Verze modulu:** 0.1.0  
> **Datum:** 31. prosince 2025  
> **Úroveň:** 3/4 - Module Technical Documentation

---

## 📋 Obsah

1. [Přehled modulu](#přehled-modulu)
2. [Struktura adresářů](#struktura-adresářů)
3. [Klíčové komponenty](#klíčové-komponenty)
4. [CLI příkazy](#cli-příkazy)
5. [Daemon a health monitoring](#daemon-a-health-monitoring)
6. [Konfigurace instancí](#konfigurace-instancí)
7. [TUI Dashboard](#tui-dashboard)
8. [Testování](#testování)

---

## Přehled modulu

**Llama Orchestrator** je Docker-like CLI nástroj pro orchestraci llama.cpp server instancí na Windows.

### Technické charakteristiky

| Vlastnost | Hodnota |
|-----------|---------|
| **Jazyk** | Python 3.11+ |
| **CLI Framework** | Typer |
| **TUI Framework** | Rich |
| **HTTP Client** | httpx |
| **State Storage** | SQLite (aiosqlite) |
| **Package** | `llama-orchestrator` |
| **Entry point** | `llama_orchestrator.cli:app` |

### Závislosti

```toml
[dependencies]
pydantic = ">=2.5"
typer = { version = ">=0.9", extras = ["all"] }
rich = ">=13.7"
httpx = ">=0.25"
psutil = ">=5.9"
aiosqlite = ">=0.19"
```

---

## Struktura adresářů

```
llama-orchestrator/
├── pyproject.toml              # Package configuration
├── README.md                   # Module documentation
├── src/
│   └── llama_orchestrator/
│       ├── __init__.py         # Package init
│       ├── __main__.py         # Entry point
│       ├── cli.py              # Typer CLI commands
│       ├── binaries/
│       │   ├── __init__.py
│       │   └── manager.py      # llama.cpp binary management
│       ├── config/
│       │   ├── __init__.py
│       │   └── models.py       # Pydantic config models
│       ├── daemon/
│       │   ├── __init__.py
│       │   └── service.py      # Background daemon
│       ├── engine/
│       │   ├── __init__.py
│       │   └── instance.py     # Instance lifecycle
│       └── health/
│           ├── __init__.py
│           └── checker.py      # Health monitoring
├── instances/                  # Instance configurations
│   └── <instance-name>/
│       └── config.json
├── logs/                       # Instance logs
├── state/                      # SQLite state DB
├── bins/                       # llama.cpp binaries
│   └── registry.json
├── tests/
│   └── test_*.py
└── docs/
    └── *.md
```

---

## Klíčové komponenty

### 1. cli.py - Typer CLI

```python
import typer
from rich.console import Console

app = typer.Typer(
    name="llama-orch",
    help="Docker-like orchestration for llama.cpp servers"
)
console = Console()

@app.command()
def up(
    name: str = typer.Argument(..., help="Instance name"),
    detach: bool = typer.Option(False, "-d", "--detach", help="Run in background")
):
    """Start an instance."""
    engine = get_engine()
    engine.start_instance(name, detach=detach)
    console.print(f"[green]Instance {name} started[/green]")

@app.command()
def down(name: str):
    """Stop an instance."""
    
@app.command()
def ps():
    """List all instances."""
    
@app.command()
def logs(name: str, follow: bool = False):
    """View instance logs."""
    
@app.command()
def dashboard():
    """Launch TUI dashboard."""
```

### 2. engine/instance.py - Instance Manager

```python
from dataclasses import dataclass
from typing import Optional
import subprocess
import psutil

@dataclass
class InstanceState:
    name: str
    status: str  # "running", "stopped", "starting", "unhealthy"
    pid: Optional[int]
    port: int
    model_path: str
    started_at: Optional[datetime]
    last_health_check: Optional[datetime]

class InstanceEngine:
    """Manages llama.cpp instance lifecycle."""
    
    def __init__(self, instances_dir: Path, bins_dir: Path):
        self.instances_dir = instances_dir
        self.bins_dir = bins_dir
        self._processes: Dict[str, subprocess.Popen] = {}
    
    def start_instance(self, name: str, detach: bool = False) -> InstanceState:
        """Start a llama.cpp server instance."""
        config = self._load_config(name)
        
        cmd = [
            str(self.bins_dir / "llama-server.exe"),
            "--model", config.model.path,
            "--host", config.server.host,
            "--port", str(config.server.port),
            "--ctx-size", str(config.model.context_size),
            "--threads", str(config.model.threads),
            "--n-gpu-layers", str(config.gpu.layers),
        ]
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if detach else 0
        )
        
        self._processes[name] = process
        return self._get_state(name)
    
    def stop_instance(self, name: str) -> None:
        """Stop a running instance."""
        if name in self._processes:
            self._processes[name].terminate()
            self._processes[name].wait(timeout=10)
            del self._processes[name]
    
    def get_all_instances(self) -> List[InstanceState]:
        """Get state of all configured instances."""
```

### 3. health/checker.py - Health Monitor

```python
import httpx
import asyncio
from dataclasses import dataclass

@dataclass
class HealthResult:
    healthy: bool
    response_time_ms: Optional[float]
    error: Optional[str]

class HealthChecker:
    """Monitors llama.cpp server health."""
    
    def __init__(self, config: HealthConfig):
        self.interval = config.interval_seconds
        self.timeout = config.timeout_seconds
        self.max_failures = config.max_failures
        self._failure_counts: Dict[str, int] = {}
    
    async def check_instance(self, host: str, port: int) -> HealthResult:
        """Check health of a single instance."""
        url = f"http://{host}:{port}/health"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                start = time.perf_counter()
                response = await client.get(url)
                elapsed = (time.perf_counter() - start) * 1000
                
                return HealthResult(
                    healthy=response.status_code == 200,
                    response_time_ms=elapsed,
                    error=None
                )
        except Exception as e:
            return HealthResult(
                healthy=False,
                response_time_ms=None,
                error=str(e)
            )
    
    async def run_monitoring_loop(
        self, 
        instances: List[InstanceState],
        on_unhealthy: Callable[[str], Awaitable[None]]
    ):
        """Continuous health monitoring loop."""
        while True:
            for instance in instances:
                result = await self.check_instance(
                    instance.host, 
                    instance.port
                )
                
                if not result.healthy:
                    self._failure_counts[instance.name] = \
                        self._failure_counts.get(instance.name, 0) + 1
                    
                    if self._failure_counts[instance.name] >= self.max_failures:
                        await on_unhealthy(instance.name)
                        self._failure_counts[instance.name] = 0
                else:
                    self._failure_counts[instance.name] = 0
            
            await asyncio.sleep(self.interval)
```

### 4. daemon/service.py - Background Daemon

```python
import asyncio
from pathlib import Path

class OrchestratorDaemon:
    """Background daemon for instance management."""
    
    def __init__(self, engine: InstanceEngine, health_checker: HealthChecker):
        self.engine = engine
        self.health_checker = health_checker
        self._running = False
    
    async def start(self):
        """Start the daemon."""
        self._running = True
        
        # Start health monitoring
        instances = self.engine.get_all_instances()
        await self.health_checker.run_monitoring_loop(
            instances,
            on_unhealthy=self._handle_unhealthy
        )
    
    async def _handle_unhealthy(self, instance_name: str):
        """Handle unhealthy instance - attempt restart."""
        config = self.engine.get_config(instance_name)
        
        if config.restart.policy == "on-failure":
            logger.warning(f"Instance {instance_name} unhealthy, restarting...")
            self.engine.stop_instance(instance_name)
            await asyncio.sleep(config.restart.backoff_seconds)
            self.engine.start_instance(instance_name, detach=True)
    
    def stop(self):
        """Stop the daemon."""
        self._running = False
```

### 5. config/models.py - Pydantic Models

```python
from pydantic import BaseModel, Field
from typing import Literal

class ModelConfig(BaseModel):
    path: str
    context_size: int = Field(default=4096, ge=512, le=131072)
    batch_size: int = Field(default=512, ge=1)
    threads: int = Field(default=8, ge=1)

class ServerConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = Field(default=8001, ge=1024, le=65535)
    parallel: int = Field(default=4, ge=1)

class GpuConfig(BaseModel):
    layers: int = Field(default=0, ge=0)
    backend: Literal["vulkan", "cuda", "cpu"] = "vulkan"

class HealthConfig(BaseModel):
    interval_seconds: int = Field(default=30, ge=5)
    timeout_seconds: int = Field(default=5, ge=1)
    max_failures: int = Field(default=3, ge=1)

class RestartConfig(BaseModel):
    policy: Literal["always", "on-failure", "never"] = "on-failure"
    max_retries: int = Field(default=5, ge=0)
    backoff_seconds: int = Field(default=10, ge=1)

class InstanceConfig(BaseModel):
    name: str
    model: ModelConfig
    server: ServerConfig
    gpu: GpuConfig = GpuConfig()
    health: HealthConfig = HealthConfig()
    restart: RestartConfig = RestartConfig()
```

---

## CLI příkazy

### Přehled příkazů

| Příkaz | Popis | Příklad |
|--------|-------|---------|
| `init` | Vytvoří novou instanci | `llama-orch init gpt-oss --model ./model.gguf --port 8001` |
| `up` | Spustí instanci | `llama-orch up gpt-oss` |
| `down` | Zastaví instanci | `llama-orch down gpt-oss` |
| `restart` | Restartuje instanci | `llama-orch restart gpt-oss` |
| `ps` | Seznam instancí | `llama-orch ps` |
| `logs` | Zobrazí logy | `llama-orch logs gpt-oss -f` |
| `health` | Zkontroluje zdraví | `llama-orch health gpt-oss` |
| `describe` | Detailní info | `llama-orch describe gpt-oss` |
| `dashboard` | TUI dashboard | `llama-orch dashboard` |
| `daemon start` | Spustí daemon | `llama-orch daemon start` |
| `config validate` | Validuje config | `llama-orch config validate` |

### Příklady použití

```powershell
# Inicializace nové instance
llama-orch init gpt-oss \
  --model "../models/gpt-oss-20b-Q4_K_S.gguf" \
  --port 8001 \
  --context-size 4096 \
  --gpu-layers 0

# Spuštění na pozadí
llama-orch up gpt-oss -d

# Sledování logů
llama-orch logs gpt-oss -f

# Zobrazení všech instancí
llama-orch ps
# Output:
# NAME      STATUS    PORT   MODEL                   UPTIME
# gpt-oss   running   8001   gpt-oss-20b-Q4_K_S     2h 15m

# Health check
llama-orch health gpt-oss
# Output:
# Instance: gpt-oss
# Status: healthy
# Response time: 45ms
# Last check: 2025-12-31 10:30:00
```

---

## Daemon a health monitoring

### Architektura daemonu

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             DAEMON ARCHITECTURE                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  CLI Command: llama-orch daemon start                                       │
│                    │                                                        │
│                    ▼                                                        │
│  ┌─────────────────────────────────────────────────────────────────────────┤
│  │  OrchestratorDaemon                                                      │
│  │  ├── Event Loop (asyncio)                                                │
│  │  ├── Health Checker (30s interval)                                       │
│  │  ├── Auto-restart Handler                                                │
│  │  └── State Persistence (SQLite)                                          │
│  └─────────────────────────────────────────────────────────────────────────┤
│                    │                                                        │
│                    ▼                                                        │
│  ┌─────────────────────────────────────────────────────────────────────────┤
│  │  Instance Monitoring                                                     │
│  │                                                                          │
│  │  gpt-oss ─────────────▶ HTTP GET /health ─────────────▶ 200 OK ✓        │
│  │  model-b ─────────────▶ HTTP GET /health ─────────────▶ Timeout ✗       │
│  │                                      │                                   │
│  │                                      ▼                                   │
│  │                              fail_count++                                │
│  │                                      │                                   │
│  │                         fail_count >= 3 ?                                │
│  │                                      │                                   │
│  │                              ┌───────┴───────┐                           │
│  │                              ▼               ▼                           │
│  │                         RESTART          CONTINUE                        │
│  │                                                                          │
│  └─────────────────────────────────────────────────────────────────────────┤
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Restart politiky

| Policy | Popis | Použití |
|--------|-------|---------|
| `always` | Vždy restartovat | Kritické produkční služby |
| `on-failure` | Restartovat při selhání | Výchozí nastavení |
| `never` | Nikdy nerestartovat | Development/testing |

### Backoff strategie

```
Attempt 1: Wait 10s
Attempt 2: Wait 20s (10 * 2)
Attempt 3: Wait 40s (20 * 2)
Attempt 4: Wait 80s (40 * 2)
Attempt 5: Wait 160s (80 * 2) - max reached
Attempt 6+: Give up, mark as failed
```

---

## Konfigurace instancí

### Příklad konfigurace

```json
{
  "name": "gpt-oss",
  "model": {
    "path": "../../models/gpt-oss-20b-Q4_K_S.gguf",
    "context_size": 4096,
    "batch_size": 512,
    "threads": 16
  },
  "server": {
    "host": "127.0.0.1",
    "port": 8001,
    "parallel": 4
  },
  "gpu": {
    "layers": 0,
    "backend": "vulkan"
  },
  "health": {
    "interval_seconds": 30,
    "timeout_seconds": 5,
    "max_failures": 3
  },
  "restart": {
    "policy": "on-failure",
    "max_retries": 5,
    "backoff_seconds": 10
  }
}
```

### Konfigurační parametry

| Parametr | Typ | Default | Popis |
|----------|-----|---------|-------|
| `model.path` | string | - | Cesta k GGUF modelu |
| `model.context_size` | int | 4096 | Max context window |
| `model.batch_size` | int | 512 | Batch size |
| `model.threads` | int | 8 | CPU threads |
| `server.host` | string | 127.0.0.1 | Listen address |
| `server.port` | int | 8001 | Listen port |
| `server.parallel` | int | 4 | Parallel requests |
| `gpu.layers` | int | 0 | GPU layers (0 = CPU) |
| `gpu.backend` | string | vulkan | GPU backend |

---

## TUI Dashboard

### Vzhled dashboardu

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        LLAMA ORCHESTRATOR DASHBOARD                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Instances                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┤
│  │ NAME       │ STATUS   │ PORT │ CPU  │ MEM   │ UPTIME   │ HEALTH        ││
│  ├────────────┼──────────┼──────┼──────┼───────┼──────────┼───────────────┤│
│  │ gpt-oss    │ ●running │ 8001 │ 45%  │ 12GB  │ 2h 15m   │ ✓ healthy     ││
│  │ model-b    │ ○stopped │ 8002 │ -    │ -     │ -        │ -             ││
│  │ test-inst  │ ●running │ 8003 │ 12%  │ 4GB   │ 30m      │ ⚠ degraded    ││
│  └─────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Recent Events                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┤
│  │ 10:30:00  gpt-oss     Health check passed (45ms)                        ││
│  │ 10:29:30  test-inst   Health check slow (2100ms)                        ││
│  │ 10:25:00  gpt-oss     Started successfully                              ││
│  │ 10:20:00  model-b     Stopped by user                                   ││
│  └─────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  [Q] Quit  [R] Refresh  [S] Start  [D] Stop  [L] Logs                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Keyboard shortcuts

| Klávesa | Akce |
|---------|------|
| `Q` | Ukončit dashboard |
| `R` | Refresh dat |
| `S` | Spustit vybranou instanci |
| `D` | Zastavit vybranou instanci |
| `L` | Zobrazit logy instance |
| `↑/↓` | Navigace mezi instancemi |
| `Enter` | Zobrazit detail instance |

---

## Testování

### Struktura testů

```
tests/
├── test_cli.py           # CLI command tests
├── test_engine.py        # Instance engine tests
├── test_health.py        # Health checker tests
├── test_config.py        # Config validation tests
└── conftest.py           # Pytest fixtures
```

### Spuštění testů

```bash
# Všechny testy
pytest tests/ -v

# S coverage
pytest tests/ --cov=llama_orchestrator --cov-report=term-missing

# Konkrétní test
pytest tests/test_health.py -v
```

### Příklad testu

```python
# tests/test_health.py
import pytest
from llama_orchestrator.health.checker import HealthChecker, HealthResult

@pytest.fixture
def health_checker():
    config = HealthConfig(interval_seconds=5, timeout_seconds=2)
    return HealthChecker(config)

@pytest.mark.asyncio
async def test_health_check_success(health_checker, httpx_mock):
    httpx_mock.add_response(url="http://127.0.0.1:8001/health", status_code=200)
    
    result = await health_checker.check_instance("127.0.0.1", 8001)
    
    assert result.healthy is True
    assert result.response_time_ms is not None
    assert result.error is None

@pytest.mark.asyncio
async def test_health_check_timeout(health_checker):
    # Non-existent server
    result = await health_checker.check_instance("127.0.0.1", 9999)
    
    assert result.healthy is False
    assert result.error is not None
```

---

## Známé limitace

| Limitace | Popis | Workaround |
|----------|-------|------------|
| Windows only | Aktuálně pouze Windows | Linux podpora plánována |
| Single machine | Bez distribuovaného režimu | Použít více instancí |
| No GPU sharing | Jedna instance = jeden GPU | Správná alokace |
| Manual binary | Vyžaduje stažení llama.cpp | Automatické stažení plánováno |

---

## Související dokumenty

- **Architektura:** [../architecture/ARCHITECTURE.md](../architecture/ARCHITECTURE.md)
- **llama-cpp-server:** [LLAMA_CPP_SERVER.md](LLAMA_CPP_SERVER.md)
- **CLI Reference:** [../api/CLI_REFERENCE.md](../api/CLI_REFERENCE.md)

---

*Tato dokumentace je součástí 4-úrovňové dokumentační struktury projektu MCP Prompt Broker.*
