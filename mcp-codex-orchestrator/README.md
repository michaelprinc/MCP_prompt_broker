# MCP Codex Orchestrator

MCP server pro orchestraci OpenAI Codex CLI běhů v izolovaných Docker kontejnerech.

## 📋 Přehled

MCP Codex Orchestrator je rozšíření [MCP Prompt Broker](../README.md), které umožňuje automatizované spouštění Codex CLI úloh prostřednictvím MCP protokolu. Každý běh probíhá v čistém Docker kontejneru s přimountovaným workspace.

### Klíčové vlastnosti

- 🐳 **Per-run container** – každý běh v čistém izolovaném prostředí
- 🔧 **MCP tool `codex_run`** – standardní MCP interface
- 📝 **Strukturované logování** – všechny běhy jsou logovány
- ⏱️ **Timeout management** – automatické ukončení při překročení limitu
- 🔄 **Marker-based protokol** – spolehlivá detekce dokončení úlohy

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

**Method 2: OpenAI API Key**
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
| `OPENAI_API_KEY` | ✅ | - | OpenAI API klíč |
| `WORKSPACE_PATH` | ❌ | `./workspace` | Cesta k workspace |
| `RUNS_PATH` | ❌ | `./runs` | Cesta k run artefaktům |
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

### Výstup

```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "done",
  "exit_code": 0,
  "duration": 45.2,
  "marker": "::MCP_STATUS::DONE",
  "output": {
    "summary": "Vytvořen soubor src/validators/email.py",
    "files_changed": ["src/validators/email.py"],
    "full_log": "..."
  }
}
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
