# Integrace v MCP Prompt Broker Ekosystému

> **Verze dokumentace:** 1.0.0  
> **Datum:** 31. prosince 2025  
> **Úroveň:** 2/4 - Architecture Detail

---

## 📋 Obsah

1. [Přehled integrací](#přehled-integrací)
2. [VS Code integrace](#vs-code-integrace)
3. [MCP Protocol integrace](#mcp-protocol-integrace)
4. [Docker integrace](#docker-integrace)
5. [llama.cpp integrace](#llamacpp-integrace)
6. [Konfigurace integrací](#konfigurace-integrací)

---

## Přehled integrací

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          INTEGRATION LANDSCAPE                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│                              ┌─────────────────┐                            │
│                              │    VS Code      │                            │
│                              │  + Extensions   │                            │
│                              └────────┬────────┘                            │
│                                       │                                     │
│                    ┌──────────────────┼──────────────────┐                  │
│                    │                  │                  │                  │
│                    ▼                  ▼                  ▼                  │
│           ┌─────────────┐    ┌─────────────┐    ┌─────────────┐            │
│           │   GitHub    │    │     MCP     │    │   Python    │            │
│           │   Copilot   │    │  Extension  │    │  Extension  │            │
│           └──────┬──────┘    └──────┬──────┘    └─────────────┘            │
│                  │                  │                                       │
│                  │                  │                                       │
│                  ▼                  ▼                                       │
│           ┌─────────────────────────────────────────────────────┐          │
│           │              MCP Protocol (stdio)                    │          │
│           └─────────────────────────┬───────────────────────────┘          │
│                                     │                                       │
│                    ┌────────────────┼────────────────┐                      │
│                    ▼                                 ▼                      │
│           ┌─────────────┐                    ┌─────────────┐               │
│           │   Prompt    │                    │   Codex     │               │
│           │   Broker    │                    │ Orchestrator│               │
│           └─────────────┘                    └──────┬──────┘               │
│                                                     │                       │
│                                                     ▼                       │
│                                              ┌─────────────┐               │
│                                              │   Docker    │               │
│                                              │   Engine    │               │
│                                              └─────────────┘               │
│                                                                             │
│           ┌─────────────┐                    ┌─────────────┐               │
│           │   Llama     │─────────────────▶│  llama.cpp  │               │
│           │ Orchestrator│                    │   Server    │               │
│           └─────────────┘                    └─────────────┘               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## VS Code integrace

### Požadované rozšíření

| Rozšíření | ID | Účel |
|-----------|----|----|
| GitHub Copilot | `github.copilot` | AI asistent |
| GitHub Copilot Chat | `github.copilot-chat` | Chat interface |
| MCP Extension | `automata-studios.copilot-mcp` | MCP client |
| Python | `ms-python.python` | Python development |

### Companion Agent Setup

Companion agent je custom agent pro GitHub Copilot Chat, který automaticky používá MCP Prompt Broker.

#### Struktura konfigurace

```
.github/
├── companion-agent.json      # Agent definice
├── companion-instructions.md # Agent instrukce
└── copilot-instructions.md   # Workspace instrukce
```

#### companion-agent.json

```json
{
  "name": "companion-instructions",
  "description": "Intelligent AI assistant with context-aware instruction routing via MCP Prompt Broker",
  "instructions": ".github/agents/companion-instructions.md",
  "tools": ["mcp"],
  "model": "claude-sonnet-4-20250514"
}
```

### Instalační skript (install.ps1)

Automaticky konfiguruje:

1. ✅ Python virtual environment
2. ✅ MCP Prompt Broker package
3. ✅ MCP server konfigurace (global)
4. ✅ MCP server konfigurace (workspace)
5. ✅ Companion agent soubory

---

## MCP Protocol integrace

### Transport: stdio

MCP servery komunikují přes standardní vstup/výstup (stdio), což zajišťuje:

- Bezpečnost (žádná síťová expozice)
- Jednoduchost (žádný port management)
- Spolehlivost (přímá komunikace)

### MCP konfigurace

#### Globální (~/.vscode/mcp.json)

```json
{
  "mcpServers": {
    "mcp-prompt-broker": {
      "command": "python",
      "args": ["-m", "mcp_prompt_broker"],
      "env": {
        "PYTHONPATH": "K:/Data_science_projects/MCP_Prompt_Broker/src"
      }
    },
    "mcp-codex-orchestrator": {
      "command": "python",
      "args": ["-m", "mcp_codex_orchestrator"],
      "env": {
        "PYTHONPATH": "K:/Data_science_projects/MCP_Prompt_Broker/mcp-codex-orchestrator/src"
      }
    }
  }
}
```

#### Workspace (.vscode/mcp.json)

```json
{
  "mcpServers": {
    "mcp-prompt-broker": {
      "command": "python",
      "args": ["-m", "mcp_prompt_broker", "--profiles-dir", "./src/mcp_prompt_broker/copilot-profiles"]
    }
  }
}
```

### MCP Tools registrace

```python
# server.py
@server.list_tools()
async def list_tools() -> List[types.Tool]:
    return [
        types.Tool(
            name="resolve_prompt",
            description="PRIMARY TOOL: Always call this FIRST...",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {"type": "string"},
                    "metadata": {"type": "object"}
                },
                "required": ["prompt"]
            }
        ),
        # ... další tools
    ]
```

---

## Docker integrace

### Architektura

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DOCKER INTEGRATION                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  MCP Codex Orchestrator                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────┤
│  │  Python Process                                                          │
│  │  └── docker-py client                                                    │
│  │       │                                                                  │
│  │       ▼                                                                  │
│  │  Docker Engine API (unix socket / named pipe)                           │
│  │       │                                                                  │
│  │       ├── containers.create()                                            │
│  │       ├── containers.start()                                             │
│  │       ├── containers.logs()                                              │
│  │       └── containers.remove()                                            │
│  └─────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Docker Desktop                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┤
│  │  Images:                                                                 │
│  │  └── codex-runner:latest                                                 │
│  │       ├── Node.js 18+                                                    │
│  │       ├── @openai/codex CLI                                              │
│  │       ├── Python 3.11                                                    │
│  │       └── Git                                                            │
│  ├─────────────────────────────────────────────────────────────────────────┤
│  │  Containers (per-run):                                                   │
│  │  ├── codex-run-abc123 (running)                                          │
│  │  │    └── Volumes: /app ← workspace                                      │
│  │  └── codex-run-def456 (exited)                                           │
│  └─────────────────────────────────────────────────────────────────────────┤
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Dockerfile

```dockerfile
# mcp-codex-orchestrator/docker/Dockerfile
FROM node:18-slim

# Install dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Codex CLI
RUN npm install -g @openai/codex

# Setup workspace
WORKDIR /app
VOLUME /app

# Entry point
ENTRYPOINT ["codex"]
```

### Docker Compose

```yaml
# mcp-codex-orchestrator/docker/docker-compose.yml
version: '3.8'

services:
  codex-runner:
    build:
      context: .
      dockerfile: Dockerfile
    volumes:
      - ../workspace:/app
      - ~/.codex:/root/.codex  # Auth
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY:-}
    network_mode: bridge
```

---

## llama.cpp integrace

### Architektura

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        LLAMA.CPP INTEGRATION                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Llama Orchestrator                                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┤
│  │  CLI (Typer)                                                             │
│  │  └── Engine                                                              │
│  │       └── ProcessManager                                                 │
│  │            │                                                             │
│  │            ▼                                                             │
│  │  ┌─────────────────────────────────────────────────────────────────────┤│
│  │  │  subprocess.Popen()                                                  ││
│  │  │  └── llama-server.exe                                                ││
│  │  │       --model path/to/model.gguf                                     ││
│  │  │       --host 127.0.0.1                                               ││
│  │  │       --port 8001                                                    ││
│  │  │       --ctx-size 4096                                                ││
│  │  │       --n-gpu-layers 0                                               ││
│  │  │       --threads 16                                                   ││
│  │  └─────────────────────────────────────────────────────────────────────┤│
│  └─────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  llama-cpp-server                                                           │
│  ┌─────────────────────────────────────────────────────────────────────────┤
│  │  Process: llama-server.exe                                               │
│  │  ├── Endpoint: http://127.0.0.1:8001                                     │
│  │  ├── API: OpenAI-compatible                                              │
│  │  │    ├── POST /v1/chat/completions                                      │
│  │  │    ├── POST /v1/completions                                           │
│  │  │    └── GET  /health                                                   │
│  │  └── Backend: Vulkan (AMD GPU)                                           │
│  └─────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Model: gpt-oss-20b-Q4_K_S.gguf (10.81 GB)                                 │
│  Performance: ~12 tokens/s generation                                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Health Check API

```python
# llama_orchestrator/health/checker.py
import httpx

async def check_instance_health(host: str, port: int) -> bool:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"http://{host}:{port}/health")
            return response.status_code == 200
    except Exception:
        return False
```

### OpenAI-Compatible API

```python
# Použití llama.cpp serveru jako OpenAI API
import httpx

async def generate_completion(prompt: str) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://127.0.0.1:8001/v1/chat/completions",
            json={
                "model": "gpt-oss-20b",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 500
            }
        )
        return response.json()["choices"][0]["message"]["content"]
```

---

## Konfigurace integrací

### Environment Variables

| Proměnná | Modul | Popis |
|----------|-------|-------|
| `PYTHONPATH` | all | Cesta k src/ |
| `MCP_SERVER` | prompt-broker | local/staging/prod |
| `OPENAI_API_KEY` | codex-orchestrator | API klíč (volitelné) |
| `DOCKER_HOST` | codex-orchestrator | Docker daemon |
| `LLAMA_CPP_PATH` | llama-orchestrator | Cesta k binárce |

### Konfigurační soubory

| Soubor | Umístění | Účel |
|--------|----------|------|
| `mcp.json` | `~/.vscode/` | Globální MCP konfig |
| `mcp.json` | `.vscode/` | Workspace MCP konfig |
| `companion-agent.json` | `.github/` | Agent definice |
| `config.json` | `llama-cpp-server/` | Server konfig |
| `pyproject.toml` | root, moduly | Package konfig |

### Integrace checklist

```markdown
## Checklist pro novou instalaci

### VS Code
- [ ] Nainstalovat GitHub Copilot extension
- [ ] Nainstalovat GitHub Copilot Chat extension
- [ ] Nainstalovat MCP extension
- [ ] Nainstalovat Python extension

### MCP Prompt Broker
- [ ] Spustit install.ps1
- [ ] Ověřit mcp.json konfigurace
- [ ] Ověřit companion agent
- [ ] Otestovat resolve_prompt tool

### Codex Orchestrator (volitelné)
- [ ] Nainstalovat Docker Desktop
- [ ] Buildnout codex-runner image
- [ ] Nastavit Codex autentizaci
- [ ] Otestovat codex_run tool

### Llama Server (volitelné)
- [ ] Stáhnout model (GGUF)
- [ ] Spustit start-server.ps1
- [ ] Ověřit /health endpoint
- [ ] Nastavit llama-orchestrator
```

---

## Troubleshooting

### Časté problémy

| Problém | Příčina | Řešení |
|---------|---------|--------|
| MCP server nedostupný | PYTHONPATH | Zkontrolovat env v mcp.json |
| Companion nefunguje | Agent JSON | Ověřit .github/ strukturu |
| Docker timeout | Image missing | `docker-compose build` |
| llama.cpp crash | Model path | Ověřit absolutní cestu |

### Diagnostické příkazy

```powershell
# MCP Prompt Broker
python -m mcp_prompt_broker --help

# Docker
docker images | Select-String codex
docker ps -a

# llama.cpp
curl http://localhost:8001/health

# Python environment
pip list | Select-String mcp
```

---

## Související dokumenty

- **Architektura:** [ARCHITECTURE.md](ARCHITECTURE.md)
- **Data Flow:** [DATA_FLOW.md](DATA_FLOW.md)
- **User Guide:** [../USER_GUIDE.md](../USER_GUIDE.md)

---

*Tato dokumentace je součástí 4-úrovňové dokumentační struktury projektu MCP Prompt Broker.*
