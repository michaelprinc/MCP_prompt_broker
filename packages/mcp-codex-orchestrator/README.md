# MCP Codex Orchestrator

MCP server pro orchestraci OpenAI Codex CLI běhů v izolovaných Docker kontejnerech.

## 📋 Přehled

MCP Codex Orchestrator je rozšíření [MCP Prompt Broker](../README.md), které umožňuje automatizované spouštění Codex CLI úloh prostřednictvím MCP protokolu. Každý běh probíhá v čistém Docker kontejneru s přimountovaným workspace.

### Klíčové vlastnosti

- 🐳 **Per-run container** – každý běh v čistém izolovaném prostředí
- 🔧 **MCP tools** – `codex_run`, `codex_status`, `codex_cancel`, `codex_artifacts`, `codex_git_diff`
- 📝 **JSONL output** – strojově čitelný výstup z Codex CLI (`--json`)
- 🔒 **Security modes** – `readonly`, `workspace_write`, `full_access`
- ✅ **Verify loop** – automatické spouštění testů a lintu po změnách
- 📊 **Schema validation** – validace výstupu pomocí JSON schémat
- ⏱️ **Timeout management** – automatické ukončení při překročení limitu

### v2.0 New Features

| Feature | Popis |
|---------|-------|
| **JSONL Output** | `codex exec --json` pro strukturovaný výstup |
| **Schema Validation** | `--output-schema` pro validaci výstupu |
| **Security Modes** | Tři úrovně izolace: readonly, workspace_write, full_access |
| **Verify Loop** | Automatické testy + lint po každém běhu |
| **New MCP Tools** | Status polling, cancel, artifacts, git diff |
| **Windows/WSL Guide** | Kompletní dokumentace pro Windows |

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker Engine 24.0+
- Docker Compose v2
- **ChatGPT Plus/Pro/Team** subscription (recommended) OR OpenAI API key
- Node.js 18+ (for Codex CLI)

### Instalace

**Important:** Install into the correct Python environment (the same one used by VS Code MCP extension).

```powershell
# Windows PowerShell - aktivace virtuálního prostředí
& K:/Data_science_projects/MCP_Prompt_Broker/.venv/Scripts/Activate.ps1

# Přejít do adresáře projektu
cd mcp-codex-orchestrator

# Instalace dependencies do .venv
pip install -e ".[dev]"

# Ověření instalace
python -m mcp_codex_orchestrator --version
```

**Authentication Setup:**

Choose ONE authentication method:

**Method 1: ChatGPT Plus (Recommended)**
```powershell
# Install Codex CLI
npm install -g @openai/codex

# Login with your ChatGPT account
codex login

# Verify auth.json was created
Test-Path "$env:USERPROFILE\.codex\auth.json"

# Or use the setup script
.\scripts\setup-auth.ps1
```

**Method 2: OpenAI API Key (Fallback - not used in the project)**
```powershell
# Konfigurace
cp docker/.env.example docker/.env
# Editujte docker/.env a nastavte OPENAI_API_KEY
```

### Build Docker image

```powershell
cd docker
docker-compose build codex-runner
```

### Inicializace workspace

```powershell
# Codex vyžaduje git repository pro bezpečnost
cd workspace
git init
git config user.email "your@email.com"
git config user.name "Your Name"
git add .
git commit -m "Initial commit"
```

### Spuštění MCP serveru

```bash
python -m mcp_codex_orchestrator
```

## 🔧 Konfigurace

### Environment variables

| Variable | Required | Default | Popis |
|----------|----------|---------|-------|
| `OPENAI_API_KEY` | ❌ | - | OpenAI API klíč (volitelně při integraci přes API)|
| `WORKSPACE_PATH` | ❌ | `./workspace` | Cesta k workspace |
| `RUNS_PATH` | ❌ | `./runs` | Cesta k run artefaktům |
| `SCHEMAS_PATH` | ❌ | `./schemas` | Cesta k JSON schématům (v2.0) |
| `CODEX_IMAGE` | ❌ | `codex-runner:latest` | Docker image name |
| `DEFAULT_TIMEOUT` | ❌ | `300` | Default timeout (s) |
| `LOG_LEVEL` | ❌ | `INFO` | Log level |

### VS Code integrace

Přidejte do `.vscode/mcp.json`:

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

## 📖 Použití

### MCP Tool: `codex_run`

```python
# Příklad volání přes MCP
result = await mcp_client.call_tool("codex_run", {
    "prompt": "Implementuj funkci pro validaci emailu",
    "mode": "full-auto",
    "timeout": 300
})
```

### Parametry

| Parametr | Typ | Default | Popis |
|----------|-----|---------|-------|
| `prompt` | string | (required) | Zadání pro Codex |
| `mode` | string | `"full-auto"` | Režim: full-auto, suggest, ask |
| `repo` | string | workspace | Cesta k repository |
| `working_dir` | string | repo root | Working directory |
| `timeout` | int | 300 | Timeout v sekundách |
| `env_vars` | dict | null | Extra environment variables |
| `security_mode` | string | `"workspace_write"` | Security mode (v2.0) |
| `verify` | bool | false | Spustit verify loop (v2.0) |
| `output_schema` | string | null | JSON schema pro validaci (v2.0) |
| `json_output` | bool | true | Použít JSONL výstup (v2.0) |

### Výstup

```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "success",
  "exit_code": 0,
  "duration": 45.2,
  "marker": "::MCP_STATUS::DONE",
  "output": {
    "summary": "Vytvořen soubor src/validators/email.py",
    "files_changed": ["src/validators/email.py"],
    "full_log": "...",
    "verify_result": {
      "status": "passed",
      "tests": {"passed": 5, "failed": 0},
      "lint": {"errors": 0, "warnings": 2}
    }
  }
}
```

## 🔒 Security Modes (v2.0)

| Mode | Čtení | Zápis workspace | Síť | Use Case |
|------|-------|-----------------|-----|----------|
| `readonly` | ✅ | ❌ | ❌ | Code review, analýza |
| `workspace_write` | ✅ | ✅ | ✅ | Běžný vývoj (default) |
| `full_access` | ✅ | ✅ | ✅ | Instalace závislostí |

Více informací: [docs/SECURITY.md](docs/SECURITY.md)

## ✅ Verify Loop (v2.0)

---

### Note about local workspace imports

If you run the MCP server from the workspace root without installing this package,
a small compatibility shim `mcp_codex_orchestrator` is provided in the repository root
to ensure the package can be imported. Prefer installing in editable mode for development:

```powershell
cd packages/mcp-codex-orchestrator
pip install -e .
```

Automatická validace po změnách:

```json
{
  "prompt": "Implementuj validaci emailu",
  "verify": true
}
```

Spouští:
1. **pytest** – kontrola testů
2. **ruff/flake8** – kontrola kvality kódu
3. **build** (volitelně) – kontrola sestavení

Více informací: [docs/VERIFY_LOOP.md](docs/VERIFY_LOOP.md)

## 🛠️ Additional MCP Tools (v2.0)

### `codex_run_status`

Polling stavu běžícího runu:

```python
result = await mcp_client.call_tool("codex_run_status", {
    "run_id": "550e8400-e29b-41d4-a716-446655440000",
    "include_events": true
})
```

### `codex_run_cancel`

Zrušení běžícího runu:

```python
result = await mcp_client.call_tool("codex_run_cancel", {
    "run_id": "550e8400-e29b-41d4-a716-446655440000",
    "force": false
})
```

### `codex_run_artifacts`

Získání artefaktů z dokončeného runu:

```python
result = await mcp_client.call_tool("codex_run_artifacts", {
    "run_id": "550e8400-e29b-41d4-a716-446655440000",
    "artifact_type": "all"  # all, files, diffs, logs, events
})
```

### `codex_git_diff`

Standardizovaný git diff výstup:

```python
result = await mcp_client.call_tool("codex_git_diff", {
    "run_id": "550e8400-e29b-41d4-a716-446655440000",
    "file_filter": "*.py",
    "context_lines": 3
})
```

## 🏗️ Architektura

```
┌─────────────────────────────────────────────────────┐
│                    MCP Client                        │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│              MCP Codex Orchestrator                  │
│  ┌─────────────┐  ┌──────────┐  ┌────────────────┐ │
│  │ codex.run() │→ │ Run Mgr  │→ │ Docker Client  │ │
│  └─────────────┘  └──────────┘  └────────────────┘ │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│              Docker Container (per-run)              │
│  ┌─────────────────────────────────────────────────┐│
│  │              Codex CLI                          ││
│  │   /workspace (mounted)  /runs/{id}/ (mounted)   ││
│  └─────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────┘
```

## 📁 Struktura projektu

```
mcp-codex-orchestrator/
├── src/mcp_codex_orchestrator/
│   ├── __init__.py
│   ├── __main__.py
│   ├── server.py
│   ├── tools/
│   ├── orchestrator/
│   ├── models/
│   └── utils/
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── .env.example
├── runs/               # Run artefakty
├── workspace/          # Mountovaný workspace
├── tests/
├── docs/
└── pyproject.toml
```

## 🧪 Testování

```bash
# Spuštění testů
pytest
- [Troubleshooting Guide](docs/TROUBLESHOOTING.md) ⭐

## ⚠️ Common Issues

See [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for solutions to:
- `No module named mcp_codex_orchestrator` error
- Docker build errors
- Authentication problems
- Git repository requirements

# S coverage
pytest --cov=mcp_codex_orchestrator

# Pouze unit testy
pytest tests/test_*.py -k "not integration"
```

## 📚 Dokumentace

- [Implementační plán](docs/IMPLEMENTATION_PLAN.md)
- [Implementační checklist](docs/IMPLEMENTATION_CHECKLIST.md)

## 🤝 Contributing

Viz [DEVELOPER_GUIDE.md](../docs/DEVELOPER_GUIDE.md) v hlavním repozitáři.

## 📄 Licence

MIT License - viz [LICENSE](../LICENSE)
