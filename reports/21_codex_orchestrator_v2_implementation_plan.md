# Codex Orchestrator v2.0 – Implementační plán

> **Verze:** 2.0  
> **Datum:** 2024-12-31  
> **Autor:** GitHub Copilot (Implementation Planner Profile)  
> **Status:** Draft  
> **Komplexita:** Critical (multi-module, breaking changes, new APIs)

---

## 📋 Executive Summary

Tento dokument definuje implementační plán pro významný upgrade **MCP Codex Orchestrator** na základě doporučení z analýzy reálných možností Codex CLI. Hlavní cíle:

1. **Přechod na `codex exec --json`** – deterministický, strojově zpracovatelný výstup
2. **Výstupní kontrakt přes `--output-schema`** – validace struktury výsledků
3. **Verify Loop** – automatická validace změn (testy, lint, build)
4. **Bezpečnostní režimy** – read-only, workspace-write, full-access
5. **Nové MCP nástroje** – `codex_run_status`, `codex_run_cancel`, `codex_run_artifacts`, `codex_git_diff`
6. **Windows/WSL dokumentace** – ergonomie pro Windows uživatele

---

## 1. Aktuální stav (Current State Snapshot)

### 1.1 Existující architektura

```
mcp-codex-orchestrator/
├── src/mcp_codex_orchestrator/
│   ├── server.py           # MCP server s jedním toolem: codex_run
│   ├── tools/
│   │   └── codex_run.py    # Základní implementace
│   ├── orchestrator/
│   │   ├── run_manager.py      # Lifecycle management
│   │   ├── docker_client.py    # Docker SDK wrapper
│   │   └── result_collector.py # Sběr výsledků (marker-based)
│   ├── models/
│   │   ├── run_request.py  # Request model
│   │   └── run_result.py   # Result model
│   └── utils/
│       ├── markers.py      # MCP status markers (::MCP_STATUS::)
│       └── logging.py      # Logging utilities
└── docker/
    ├── Dockerfile          # Codex CLI container
    └── docker-compose.yml
```

### 1.2 Identifikované problémy

| Problém | Dopad | Priorita |
|---------|-------|----------|
| **Marker-based protokol** jako primární mechanismus | Nespolehlivý, závisí na LLM compliance | 🔴 Critical |
| **Textový výstup** místo strukturovaných dat | Orchestrátor musí "hádat" výsledky | 🔴 Critical |
| **Chybí verify loop** | Částečné/rozbité změny nejsou detekovány | 🟠 High |
| **Jediný bezpečnostní režim** | Riziko blast radius při delegaci | 🟠 High |
| **Chybí status/cancel API** | Nelze monitorovat/zastavit běhy | 🟡 Medium |
| **Windows dokumentace** | Špatná ergonomie pro Windows uživatele | 🟡 Medium |

### 1.3 Co funguje dobře

- ✅ Per-run container architektura
- ✅ Docker SDK integrace
- ✅ Základní timeout management
- ✅ Strukturované logování (structlog)
- ✅ MCP server framework

---

## 2. Cílový stav (Target Architecture)

### 2.1 High-Level architektura v2.0

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             VS Code / MCP Client                            │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                        MCP Codex Orchestrator v2                       │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐        │  │
│  │  │   NEW TOOLS:    │  │   CORE:         │  │   VERIFY:       │        │  │
│  │  │ • codex_run     │  │ • RunManager    │  │ • TestRunner    │        │  │
│  │  │ • codex_status  │  │ • DockerClient  │  │ • LintChecker   │        │  │
│  │  │ • codex_cancel  │  │ • JSONLParser   │  │ • BuildRunner   │        │  │
│  │  │ • codex_artifacts│ │ • SchemaValidator│ │ • VerifyLoop    │        │  │
│  │  │ • codex_git_diff│  │                 │  │                 │        │  │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘        │  │
│  │                              │                      │                  │  │
│  │  ┌───────────────────────────┴──────────────────────┴───────────────┐ │  │
│  │  │                    Security Layer                                │ │  │
│  │  │  • SecurityMode enum (readonly, workspace_write, full_access)    │ │  │
│  │  │  • Patch Workflow (generate → review → apply)                    │ │  │
│  │  │  • Sandbox enforcement                                           │ │  │
│  │  └──────────────────────────────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Docker Container                                   │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │  codex exec --json --output-schema schema.json "<prompt>"               ││
│  │                                                                         ││
│  │  Output: JSONL stream → events.jsonl                                    ││
│  │  • message.delta, tool.call, tool.result, error, completion             ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  Mounted Volumes:                                                       │ │
│  │  • /workspace (readonly | rw depending on SecurityMode)                 │ │
│  │  • /runs/{runId}/ (rw - logs, artifacts, patches)                       │ │
│  │  • /schemas/ (readonly - output schemas)                                │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Nová adresářová struktura

```
mcp-codex-orchestrator/
├── src/mcp_codex_orchestrator/
│   ├── __init__.py
│   ├── __main__.py
│   ├── server.py                    # Extended MCP server
│   │
│   ├── tools/                       # MCP Tools (EXPANDED)
│   │   ├── __init__.py
│   │   ├── codex_run.py             # Updated with --json support
│   │   ├── codex_status.py          # NEW: Run status polling
│   │   ├── codex_cancel.py          # NEW: Cancel running jobs
│   │   ├── codex_artifacts.py       # NEW: Get run artifacts
│   │   └── codex_git_diff.py        # NEW: Standardized diff output
│   │
│   ├── orchestrator/
│   │   ├── __init__.py
│   │   ├── run_manager.py           # Updated lifecycle management
│   │   ├── docker_client.py         # Updated command building
│   │   ├── result_collector.py      # DEPRECATED (fallback only)
│   │   ├── jsonl_parser.py          # NEW: JSONL event parser
│   │   └── schema_validator.py      # NEW: Output schema validation
│   │
│   ├── verify/                      # NEW: Verification subsystem
│   │   ├── __init__.py
│   │   ├── verify_loop.py           # Main verify loop orchestrator
│   │   ├── test_runner.py           # pytest integration
│   │   ├── lint_checker.py          # ruff/black integration
│   │   └── build_runner.py          # Build command runner
│   │
│   ├── security/                    # NEW: Security subsystem
│   │   ├── __init__.py
│   │   ├── modes.py                 # SecurityMode enum
│   │   ├── sandbox.py               # Sandbox enforcement
│   │   └── patch_workflow.py        # Patch generation/application
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── run_request.py           # Updated with security_mode
│   │   ├── run_result.py            # Updated with structured data
│   │   ├── jsonl_events.py          # NEW: JSONL event models
│   │   └── verify_result.py         # NEW: Verification result models
│   │
│   └── utils/
│       ├── __init__.py
│       ├── markers.py               # DEPRECATED (fallback only)
│       ├── logging.py
│       └── git_utils.py             # NEW: Git diff utilities
│
├── schemas/                         # NEW: Output schemas
│   ├── default_output.json
│   ├── code_change.json
│   ├── analysis_report.json
│   └── test_results.json
│
├── docker/
│   ├── Dockerfile                   # Updated
│   ├── docker-compose.yml           # Updated
│   └── .env.example
│
├── docs/
│   ├── IMPLEMENTATION_PLAN.md       # Legacy (v1)
│   ├── IMPLEMENTATION_PLAN_V2.md    # NEW: This document
│   ├── WINDOWS_WSL_GUIDE.md         # NEW: Windows/WSL docs
│   ├── SECURITY_MODES.md            # NEW: Security documentation
│   └── VERIFY_LOOP.md               # NEW: Verify loop documentation
│
└── tests/
    ├── test_jsonl_parser.py         # NEW
    ├── test_schema_validator.py     # NEW
    ├── test_verify_loop.py          # NEW
    └── test_security_modes.py       # NEW
```

---

## 3. Implementační fáze

### Fáze 0: Příprava (1 den)

| Úkol | Popis | Výstup |
|------|-------|--------|
| 0.1 | Backup aktuálního stavu | Git tag `v1.0-pre-upgrade` |
| 0.2 | Vytvoření feature branch | `feature/v2-jsonl-verify-security` |
| 0.3 | Aktualizace pyproject.toml | Nové dependencies |
| 0.4 | Vytvoření adresářové struktury | Prázdné moduly |

**Nové dependencies:**
```toml
[project.dependencies]
# Existing
mcp = ">=1.9.0"
docker = ">=7.0.0"
structlog = ">=24.0.0"
pydantic = ">=2.0.0"
aiofiles = ">=24.0.0"

# NEW for v2
jsonlines = ">=4.0.0"        # JSONL parsing
jsonschema = ">=4.21.0"      # Schema validation
gitpython = ">=3.1.40"       # Git operations
```

---

### Fáze 1: JSONL Infrastructure (2 dny)

#### 1.1 JSONL Event Models (`models/jsonl_events.py`)

```python
from enum import Enum
from pydantic import BaseModel
from typing import Any, Optional
from datetime import datetime

class EventType(str, Enum):
    MESSAGE_DELTA = "message.delta"
    TOOL_CALL = "tool.call"
    TOOL_RESULT = "tool.result"
    FILE_CHANGE = "file.change"
    COMMAND_RUN = "command.run"
    ERROR = "error"
    COMPLETION = "completion"

class CodexEvent(BaseModel):
    """Single JSONL event from Codex CLI."""
    type: EventType
    timestamp: datetime
    data: dict[str, Any]
    
class FileChange(BaseModel):
    """File change event data."""
    path: str
    action: str  # created, modified, deleted
    diff: Optional[str] = None

class CommandRun(BaseModel):
    """Command execution event data."""
    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int

class CompletionData(BaseModel):
    """Completion event with validated output."""
    summary: str
    changed_files: list[str]
    commands_run: list[str]
    tests_run: Optional[dict[str, Any]] = None
    next_steps: Optional[list[str]] = None
    token_usage: dict[str, int]
```

#### 1.2 JSONL Parser (`orchestrator/jsonl_parser.py`)

```python
import json
from pathlib import Path
from typing import AsyncIterator
import aiofiles
from .models.jsonl_events import CodexEvent, EventType

class JSONLParser:
    """Parser pro JSONL stream z Codex CLI --json výstupu."""
    
    async def parse_stream(
        self, 
        stream: AsyncIterator[str]
    ) -> AsyncIterator[CodexEvent]:
        """Parse JSONL stream in real-time."""
        buffer = ""
        async for chunk in stream:
            buffer += chunk
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                if line.strip():
                    yield self._parse_line(line)
    
    async def parse_file(self, path: Path) -> list[CodexEvent]:
        """Parse completed JSONL file."""
        events = []
        async with aiofiles.open(path, "r") as f:
            async for line in f:
                if line.strip():
                    events.append(self._parse_line(line))
        return events
    
    def extract_summary(self, events: list[CodexEvent]) -> dict:
        """Extract structured summary from events."""
        return {
            "changed_files": self._extract_file_changes(events),
            "commands_run": self._extract_commands(events),
            "errors": self._extract_errors(events),
            "token_usage": self._extract_token_usage(events),
        }
```

#### 1.3 Schema Validator (`orchestrator/schema_validator.py`)

```python
import json
from pathlib import Path
from jsonschema import validate, ValidationError

class SchemaValidator:
    """Validator pro Codex --output-schema výstupy."""
    
    SCHEMAS_DIR = Path(__file__).parent.parent.parent / "schemas"
    
    DEFAULT_SCHEMA = {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "changed_files": {
                "type": "array",
                "items": {"type": "string"}
            },
            "commands_run": {
                "type": "array", 
                "items": {"type": "string"}
            },
            "tests_run": {
                "type": "object",
                "properties": {
                    "passed": {"type": "integer"},
                    "failed": {"type": "integer"},
                    "skipped": {"type": "integer"}
                }
            },
            "next_steps": {
                "type": "array",
                "items": {"type": "string"}
            }
        },
        "required": ["summary", "changed_files"]
    }
    
    def get_schema_path(self, schema_name: str = "default") -> Path:
        """Get path to schema file."""
        return self.SCHEMAS_DIR / f"{schema_name}_output.json"
    
    def validate_output(self, output: dict, schema_name: str = "default") -> bool:
        """Validate output against schema."""
        schema = self._load_schema(schema_name)
        try:
            validate(instance=output, schema=schema)
            return True
        except ValidationError as e:
            raise OutputValidationError(str(e))
```

---

### Fáze 2: Docker Client Update (1 den)

#### 2.1 Aktualizace `_build_command()` v `docker_client.py`

```python
def _build_command(
    self, 
    prompt: str, 
    mode: str,
    output_schema: Path | None = None,
    json_output: bool = True,  # NEW: default True
) -> list[str]:
    """Build Docker command for Codex CLI with JSONL support."""
    
    # Use 'exec' subcommand for non-interactive mode
    cmd = ["exec"]
    
    # Add mode flag
    if mode == "full-auto":
        cmd.append("--full-auto")
    elif mode == "suggest":
        cmd.append("--suggest")
    
    # NEW: Enable JSON output (JSONL streaming)
    if json_output:
        cmd.append("--json")
    
    # NEW: Add output schema validation
    if output_schema:
        cmd.extend(["--output-schema", str(output_schema)])
    
    # Add prompt as the task
    cmd.append(prompt)
    
    return cmd
```

#### 2.2 Aktualizace volume mounts pro schemas

```python
def _build_volumes(
    self,
    workspace_path: Path,
    runs_path: Path,
    run_id: str,
    security_mode: str = "workspace_write",  # NEW
) -> dict[str, dict[str, str]]:
    """Build volume mounts with security mode support."""
    
    run_dir = runs_path / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    
    # Determine workspace mount mode
    ws_mode = "ro" if security_mode == "readonly" else "rw"
    
    volumes = {
        str(workspace_path): {
            "bind": "/workspace", 
            "mode": ws_mode  # NEW: respects security mode
        },
        str(run_dir): {
            "bind": f"/runs/{run_id}", 
            "mode": "rw"
        },
        # NEW: Mount schemas directory
        str(self.schemas_path): {
            "bind": "/schemas",
            "mode": "ro"
        },
    }
    
    # Mount Codex auth
    if self.codex_auth_path.exists():
        volumes[str(self.codex_auth_path)] = {
            "bind": "/root/.codex",
            "mode": "ro"
        }
    
    return volumes
```

---

### Fáze 3: Security Subsystem (2 dny)

#### 3.1 Security Modes (`security/modes.py`)

```python
from enum import Enum

class SecurityMode(str, Enum):
    """Bezpečnostní režimy pro Codex běhy."""
    
    READONLY = "readonly"
    """Read-only sandbox. Pro analýzy, návrhy, reporty.
    
    - Workspace mounted jako read-only
    - Výstup pouze jako diff/patch artefakt
    - Bezpečné pro delegaci bez kontroly
    """
    
    WORKSPACE_WRITE = "workspace_write"
    """Workspace write access s verify loop.
    
    - Workspace mounted jako read-write
    - Automatický verify loop po změnách
    - Doporučeno pro implementační úlohy
    """
    
    FULL_ACCESS = "full_access"
    """Plný přístup (DANGER).
    
    - Workspace mounted jako read-write
    - Síťový přístup povolen
    - POUZE v izolovaném runneru
    - Vyžaduje explicitní potvrzení
    - Logovat veškeré akce
    """

# Mapování na Codex CLI flags
SECURITY_MODE_FLAGS = {
    SecurityMode.READONLY: ["--sandbox", "read-only"],
    SecurityMode.WORKSPACE_WRITE: ["--sandbox", "write-user"],
    SecurityMode.FULL_ACCESS: ["--full-auto"],  # YOLO equivalent
}
```

#### 3.2 Patch Workflow (`security/patch_workflow.py`)

```python
from pathlib import Path
import subprocess
from typing import Optional

class PatchWorkflow:
    """Workflow pro bezpečnou aplikaci změn přes patch."""
    
    async def generate_patch(
        self,
        workspace_path: Path,
        run_id: str,
    ) -> Path:
        """Generate patch from uncommitted changes."""
        patch_path = self.runs_path / run_id / "changes.patch"
        
        result = subprocess.run(
            ["git", "diff", "--no-color"],
            cwd=workspace_path,
            capture_output=True,
            text=True,
        )
        
        patch_path.write_text(result.stdout)
        return patch_path
    
    async def preview_patch(self, patch_path: Path) -> dict:
        """Preview what the patch would change."""
        result = subprocess.run(
            ["git", "apply", "--stat", str(patch_path)],
            capture_output=True,
            text=True,
        )
        return {
            "summary": result.stdout,
            "files_affected": self._parse_stat(result.stdout),
        }
    
    async def apply_patch(
        self,
        patch_path: Path,
        workspace_path: Path,
        user_approved: bool = False,
    ) -> bool:
        """Apply patch to workspace (requires approval)."""
        if not user_approved:
            raise SecurityError("Patch application requires user approval")
        
        result = subprocess.run(
            ["git", "apply", str(patch_path)],
            cwd=workspace_path,
            capture_output=True,
        )
        return result.returncode == 0
```

---

### Fáze 4: Verify Loop (2 dny)

#### 4.1 Verify Loop Orchestrator (`verify/verify_loop.py`)

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import structlog

from .test_runner import TestRunner
from .lint_checker import LintChecker
from .build_runner import BuildRunner

logger = structlog.get_logger(__name__)

@dataclass
class VerifyConfig:
    """Konfigurace verify loop."""
    run_tests: bool = True
    run_lint: bool = True
    run_build: bool = False
    max_fix_attempts: int = 2
    test_command: str = "pytest"
    lint_command: str = "ruff check ."
    build_command: Optional[str] = None

@dataclass  
class VerifyResult:
    """Výsledek verify loop."""
    passed: bool
    tests_passed: Optional[bool] = None
    tests_output: Optional[str] = None
    lint_passed: Optional[bool] = None
    lint_output: Optional[str] = None
    build_passed: Optional[bool] = None
    build_output: Optional[str] = None
    fix_attempts: int = 0

class VerifyLoop:
    """Automatický verify loop po Codex změnách."""
    
    def __init__(
        self,
        workspace_path: Path,
        config: VerifyConfig,
    ):
        self.workspace_path = workspace_path
        self.config = config
        self.test_runner = TestRunner(workspace_path)
        self.lint_checker = LintChecker(workspace_path)
        self.build_runner = BuildRunner(workspace_path)
    
    async def run(self, run_id: str) -> VerifyResult:
        """Run full verify loop."""
        result = VerifyResult(passed=True)
        
        # Step 1: Run lint
        if self.config.run_lint:
            lint_result = await self.lint_checker.check(
                self.config.lint_command
            )
            result.lint_passed = lint_result.passed
            result.lint_output = lint_result.output
            if not lint_result.passed:
                result.passed = False
        
        # Step 2: Run tests
        if self.config.run_tests:
            test_result = await self.test_runner.run(
                self.config.test_command
            )
            result.tests_passed = test_result.passed
            result.tests_output = test_result.output
            if not test_result.passed:
                result.passed = False
        
        # Step 3: Run build (optional)
        if self.config.run_build and self.config.build_command:
            build_result = await self.build_runner.run(
                self.config.build_command
            )
            result.build_passed = build_result.passed
            result.build_output = build_result.output
            if not build_result.passed:
                result.passed = False
        
        return result
    
    async def run_with_auto_fix(
        self,
        run_id: str,
        codex_runner: "CodexRunner",
    ) -> VerifyResult:
        """Run verify loop with automatic fix attempts."""
        attempt = 0
        
        while attempt <= self.config.max_fix_attempts:
            result = await self.run(run_id)
            result.fix_attempts = attempt
            
            if result.passed:
                logger.info("Verify loop passed", attempt=attempt)
                return result
            
            if attempt >= self.config.max_fix_attempts:
                logger.warning(
                    "Max fix attempts reached",
                    attempts=attempt,
                )
                return result
            
            # Generate fix prompt
            fix_prompt = self._generate_fix_prompt(result)
            
            # Run Codex to fix
            logger.info("Running auto-fix", attempt=attempt + 1)
            await codex_runner.run(
                prompt=fix_prompt,
                mode="full-auto",
            )
            
            attempt += 1
        
        return result
    
    def _generate_fix_prompt(self, result: VerifyResult) -> str:
        """Generate fix prompt from failed verification."""
        parts = ["Fix the following issues:\n"]
        
        if result.lint_passed is False:
            parts.append(f"## Lint errors:\n```\n{result.lint_output}\n```\n")
        
        if result.tests_passed is False:
            parts.append(f"## Test failures:\n```\n{result.tests_output}\n```\n")
        
        if result.build_passed is False:
            parts.append(f"## Build errors:\n```\n{result.build_output}\n```\n")
        
        return "\n".join(parts)
```

---

### Fáze 5: Nové MCP Tools (2 dny)

#### 5.1 `codex_status` Tool

```python
# tools/codex_status.py

async def handle_codex_status(
    run_id: str,
    run_manager: RunManager,
) -> dict:
    """Get status of a Codex run without reading full logs."""
    
    run_dir = run_manager.runs_path / run_id
    
    if not run_dir.exists():
        return {"status": "not_found", "run_id": run_id}
    
    # Check status file
    status_file = run_dir / "status.json"
    if status_file.exists():
        return json.loads(status_file.read_text())
    
    # Check if container is still running
    container_running = await run_manager.is_container_running(run_id)
    
    if container_running:
        # Parse partial JSONL for progress
        progress = await run_manager.get_run_progress(run_id)
        return {
            "status": "running",
            "run_id": run_id,
            "progress": progress,
        }
    
    return {"status": "unknown", "run_id": run_id}
```

#### 5.2 `codex_cancel` Tool

```python
# tools/codex_cancel.py

async def handle_codex_cancel(
    run_id: str,
    run_manager: RunManager,
) -> dict:
    """Cancel a running Codex job."""
    
    container = await run_manager.get_container(run_id)
    
    if container is None:
        return {
            "success": False,
            "error": f"No running container for run {run_id}",
        }
    
    await run_manager.docker_client.stop_container(container)
    
    # Mark as cancelled in status
    await run_manager.update_status(run_id, "cancelled")
    
    return {
        "success": True,
        "run_id": run_id,
        "status": "cancelled",
    }
```

#### 5.3 `codex_artifacts` Tool

```python
# tools/codex_artifacts.py

async def handle_codex_artifacts(
    run_id: str,
    run_manager: RunManager,
    include_diff: bool = True,
    include_jsonl: bool = True,
) -> dict:
    """Get artifacts from a completed Codex run."""
    
    run_dir = run_manager.runs_path / run_id
    
    artifacts = {
        "run_id": run_id,
        "paths": {},
    }
    
    # Collect artifact paths
    for artifact_type, filename in [
        ("request", "request.json"),
        ("result", "result.json"),
        ("events", "events.jsonl"),
        ("log", "log.txt"),
        ("diff", "changes.patch"),
    ]:
        path = run_dir / filename
        if path.exists():
            artifacts["paths"][artifact_type] = str(path)
            
            # Include content if requested
            if artifact_type == "diff" and include_diff:
                artifacts["diff_content"] = path.read_text()
            if artifact_type == "events" and include_jsonl:
                artifacts["events"] = await run_manager.parse_events(path)
    
    return artifacts
```

#### 5.4 `codex_git_diff` Tool

```python
# tools/codex_git_diff.py

async def handle_codex_git_diff(
    run_id: str,
    run_manager: RunManager,
    format: str = "unified",  # unified, stat, name-only
) -> dict:
    """Get standardized git diff output for a run."""
    
    run_dir = run_manager.runs_path / run_id
    diff_file = run_dir / "changes.patch"
    
    if not diff_file.exists():
        # Generate from workspace
        diff_content = await run_manager.generate_diff(run_id, format)
    else:
        diff_content = diff_file.read_text()
    
    # Parse diff into structured format
    parsed = parse_unified_diff(diff_content)
    
    return {
        "run_id": run_id,
        "format": format,
        "raw_diff": diff_content,
        "files_changed": parsed.files,
        "insertions": parsed.insertions,
        "deletions": parsed.deletions,
        "hunks": parsed.hunks,
    }
```

#### 5.5 Aktualizace `server.py` – registrace nových tools

```python
@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools."""
    return [
        # Existing (updated)
        Tool(
            name="codex_run",
            description="Spustí Codex CLI v Docker kontejneru s JSONL výstupem a volitelným verify loop.",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {"type": "string"},
                    "mode": {"type": "string", "enum": ["full-auto", "suggest", "ask"]},
                    "security_mode": {
                        "type": "string",
                        "enum": ["readonly", "workspace_write", "full_access"],
                        "default": "workspace_write",
                    },
                    "verify": {
                        "type": "boolean",
                        "default": True,
                        "description": "Run verify loop after completion",
                    },
                    "output_schema": {
                        "type": "string",
                        "description": "Name of output schema to validate against",
                    },
                    "timeout": {"type": "integer", "default": 300},
                },
                "required": ["prompt"],
            },
        ),
        
        # NEW Tools
        Tool(
            name="codex_run_status",
            description="Získá status běžícího Codex jobu bez čtení logů.",
            inputSchema={
                "type": "object",
                "properties": {
                    "run_id": {"type": "string"},
                },
                "required": ["run_id"],
            },
        ),
        Tool(
            name="codex_run_cancel",
            description="Zruší běžící Codex job.",
            inputSchema={
                "type": "object", 
                "properties": {
                    "run_id": {"type": "string"},
                },
                "required": ["run_id"],
            },
        ),
        Tool(
            name="codex_run_artifacts",
            description="Získá artefakty z dokončeného Codex běhu.",
            inputSchema={
                "type": "object",
                "properties": {
                    "run_id": {"type": "string"},
                    "include_diff": {"type": "boolean", "default": True},
                    "include_jsonl": {"type": "boolean", "default": True},
                },
                "required": ["run_id"],
            },
        ),
        Tool(
            name="codex_git_diff",
            description="Získá standardizovaný git diff výstup pro Codex běh.",
            inputSchema={
                "type": "object",
                "properties": {
                    "run_id": {"type": "string"},
                    "format": {
                        "type": "string",
                        "enum": ["unified", "stat", "name-only"],
                        "default": "unified",
                    },
                },
                "required": ["run_id"],
            },
        ),
    ]
```

---

### Fáze 6: Windows/WSL Dokumentace (1 den)

#### 6.1 Nový dokument `docs/WINDOWS_WSL_GUIDE.md`

```markdown
# Windows & WSL Guide for MCP Codex Orchestrator

## Overview

Codex CLI má Windows podporu jako "experimentální". Pro nejlepší zkušenost
doporučujeme WSL 2 workflow.

## Path Mapping

### Windows → WSL Path Conversion

| Windows Path | WSL Path |
|--------------|----------|
| `C:\Users\name\project` | `/mnt/c/Users/name/project` |
| `D:\repos\myapp` | `/mnt/d/repos/myapp` |

### Docker Desktop Integration

Docker Desktop automaticky zpřístupňuje Windows cesty přes WSL.
V `docker-compose.yml` použijte WSL cesty:

```yaml
volumes:
  - /mnt/c/Users/name/workspace:/workspace
```

## File Permissions

### Problém

Windows filesystém nemá Unix permission bits. Git může hlásit změny
v permission mode.

### Řešení

```bash
# V WSL
git config core.fileMode false

# Nebo globálně
git config --global core.fileMode false
```

## Git Repository Requirement

Codex CLI vyžaduje git repository pro bezpečnost.

### Inicializace

```powershell
# PowerShell
cd C:\Users\name\workspace
git init
git config user.email "your@email.com"
git config user.name "Your Name"
git add .
git commit -m "Initial commit"
```

## Authentication in Container

### OAuth Token Sharing

Codex auth.json musí být dostupný v kontejneru:

```yaml
# docker-compose.yml
volumes:
  - ${USERPROFILE}/.codex:/root/.codex:ro
```

### WSL Path for Auth

```yaml
volumes:
  - /mnt/c/Users/${USER}/.codex:/root/.codex:ro
```

## Common Issues

### Issue: Docker volumes not syncing

**Symptom:** Changes made in container not visible on host.

**Solution:**
1. Use Docker Desktop with WSL 2 backend
2. Enable "Use WSL 2 based engine" in Docker settings
3. Store workspace in WSL filesystem for better performance

### Issue: Line endings (CRLF vs LF)

**Solution:**
```bash
git config --global core.autocrlf input
```

### Issue: Slow filesystem in /mnt/c

**Solution:** Use WSL native filesystem:
```bash
# Store projects in ~/projects instead of /mnt/c/...
mkdir ~/projects
cd ~/projects
git clone ...
```
```

---

### Fáze 7: Testy & Dokumentace (2 dny)

#### 7.1 Testy

| Test soubor | Coverage |
|-------------|----------|
| `test_jsonl_parser.py` | JSONLParser, event parsing |
| `test_schema_validator.py` | Schema loading, validation |
| `test_verify_loop.py` | VerifyLoop, auto-fix |
| `test_security_modes.py` | SecurityMode, sandbox |
| `test_new_tools.py` | status, cancel, artifacts, diff tools |

#### 7.2 Dokumentace

| Dokument | Obsah |
|----------|-------|
| `docs/SECURITY_MODES.md` | Popis bezpečnostních režimů |
| `docs/VERIFY_LOOP.md` | Konfigurace verify loop |
| `docs/JSONL_OUTPUT.md` | JSONL event formát |
| `README.md` | Aktualizace s v2 features |

---

## 4. Risk Analysis

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Breaking changes v Codex CLI | Medium | High | Fallback na marker protokol |
| Windows path issues | High | Medium | Důkladná WSL dokumentace |
| Verify loop false positives | Medium | Medium | Konfigurovatelné pravidla |
| Security mode bypass | Low | Critical | Audit logging, review |
| Schema validation failures | Medium | Low | Graceful fallback |

---

## 5. Rollback Procedures

### Quick Rollback

```bash
# Vrátit na v1
git checkout v1.0-pre-upgrade

# Reinstall
pip install -e ".[dev]"
```

### Partial Rollback (disable v2 features)

```python
# V server.py - environment variables
ENABLE_JSONL = os.getenv("CODEX_ENABLE_JSONL", "true") == "true"
ENABLE_VERIFY = os.getenv("CODEX_ENABLE_VERIFY", "true") == "true"
ENABLE_SECURITY = os.getenv("CODEX_ENABLE_SECURITY", "true") == "true"
```

---

## 6. Timeline Summary

| Fáze | Trvání | Kumulativně |
|------|--------|-------------|
| Fáze 0: Příprava | 1 den | 1 den |
| Fáze 1: JSONL Infrastructure | 2 dny | 3 dny |
| Fáze 2: Docker Client Update | 1 den | 4 dny |
| Fáze 3: Security Subsystem | 2 dny | 6 dnů |
| Fáze 4: Verify Loop | 2 dny | 8 dnů |
| Fáze 5: Nové MCP Tools | 2 dny | 10 dnů |
| Fáze 6: Windows/WSL Docs | 1 den | 11 dnů |
| Fáze 7: Testy & Dokumentace | 2 dny | **13 dnů** |

**Celkový odhad: 13 pracovních dnů (~2.5 týdne)**

---

## 7. Deliverables Summary

### Kód

- [ ] `orchestrator/jsonl_parser.py` – JSONL event parsing
- [ ] `orchestrator/schema_validator.py` – Output schema validation
- [ ] `security/modes.py` – SecurityMode enum
- [ ] `security/sandbox.py` – Sandbox enforcement
- [ ] `security/patch_workflow.py` – Patch generation/application
- [ ] `verify/verify_loop.py` – Verify loop orchestrator
- [ ] `verify/test_runner.py` – pytest integration
- [ ] `verify/lint_checker.py` – Linter integration
- [ ] `tools/codex_status.py` – Status polling
- [ ] `tools/codex_cancel.py` – Job cancellation
- [ ] `tools/codex_artifacts.py` – Artifact retrieval
- [ ] `tools/codex_git_diff.py` – Git diff output
- [ ] Updated `docker_client.py` – --json, --output-schema support
- [ ] Updated `server.py` – New tool registrations

### Schemas

- [ ] `schemas/default_output.json`
- [ ] `schemas/code_change.json`
- [ ] `schemas/analysis_report.json`

### Dokumentace

- [ ] `docs/WINDOWS_WSL_GUIDE.md`
- [ ] `docs/SECURITY_MODES.md`
- [ ] `docs/VERIFY_LOOP.md`
- [ ] `docs/JSONL_OUTPUT.md`
- [ ] Updated `README.md`

### Testy

- [ ] `tests/test_jsonl_parser.py`
- [ ] `tests/test_schema_validator.py`
- [ ] `tests/test_verify_loop.py`
- [ ] `tests/test_security_modes.py`
- [ ] `tests/test_new_tools.py`

---

## 8. Next Steps

Po schválení tohoto plánu:

1. **Vytvoření feature branch** – `feature/v2-jsonl-verify-security`
2. **Implementace Fáze 0** – Příprava prostředí
3. **Iterativní implementace** – Fáze 1-7 s průběžným review
4. **Integration testing** – End-to-end testy s reálným Codex CLI
5. **Release v2.0** – Merge do main, tagging, changelog

---

*Dokument vygenerován: 2024-12-31*  
*Profil: implementation_planner*  
*Verze profilu: 1.0.0*
