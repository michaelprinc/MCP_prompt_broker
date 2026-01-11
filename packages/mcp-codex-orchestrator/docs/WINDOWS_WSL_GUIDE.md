# Windows a WSL Instalační Průvodce

Tento průvodce popisuje instalaci a konfiguraci MCP Codex Orchestratoru na Windows s Docker Desktop a WSL2.

## Obsah

1. [Požadavky](#požadavky)
2. [Instalace Docker Desktop](#instalace-docker-desktop)
3. [Konfigurace WSL2](#konfigurace-wsl2)
4. [Instalace MCP Codex Orchestratoru](#instalace-mcp-codex-orchestratoru)
5. [Konfigurace VS Code](#konfigurace-vs-code)
6. [Řešení problémů](#řešení-problémů)

---

## Požadavky

### Systémové požadavky

- **Windows 10** verze 2004 nebo novější, nebo **Windows 11**
- **WSL2** (Windows Subsystem for Linux 2)
- **Docker Desktop** 4.x nebo novější
- **Python** 3.11+ (v WSL nebo Windows)
- **Git**

### Hardwarové požadavky

- Minimálně 8 GB RAM (doporučeno 16 GB+)
- SSD disk pro rychlejší I/O operace
- Virtualizace povolena v BIOS/UEFI (VT-x, AMD-V)

---

## Instalace Docker Desktop

### Krok 1: Stažení Docker Desktop

1. Stáhněte Docker Desktop z [docker.com](https://www.docker.com/products/docker-desktop/)
2. Spusťte instalátor a postupujte podle pokynů

### Krok 2: Konfigurace Docker Desktop

1. Otevřete Docker Desktop → Settings
2. Přejděte do **General**:
   - ✅ Use the WSL 2 based engine
   - ✅ Start Docker Desktop when you log in
3. Přejděte do **Resources → WSL Integration**:
   - ✅ Enable integration with my default WSL distro
   - Povolte integraci pro vaši WSL distribuci (např. Ubuntu)
4. Přejděte do **Resources → Advanced**:
   - Nastavte přiměřené limity CPU a RAM
   - Doporučeno: 4+ CPU, 8+ GB RAM

### Krok 3: Ověření instalace

```powershell
# V PowerShell
docker version
docker run hello-world
```

```bash
# V WSL
docker version
docker run hello-world
```

---

## Konfigurace WSL2

### Krok 1: Instalace WSL2

```powershell
# Jako administrátor
wsl --install

# Nebo specifická distribuce
wsl --install -d Ubuntu-22.04
```

### Krok 2: Konfigurace WSL

Vytvořte nebo upravte `%USERPROFILE%\.wslconfig`:

```ini
[wsl2]
memory=8GB
processors=4
swap=4GB
localhostForwarding=true

[experimental]
# Pro lepší výkon souborového systému
sparseVhd=true
```

### Krok 3: Restartujte WSL

```powershell
wsl --shutdown
wsl
```

---

## Instalace MCP Codex Orchestratoru

### Varianta A: Instalace na Windows (PowerShell)

```powershell
# Klonování repozitáře
git clone https://github.com/your-org/mcp-codex-orchestrator.git
cd mcp-codex-orchestrator

# Vytvoření virtuálního prostředí
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Instalace závislostí
pip install -e .

# Nastavení proměnných prostředí
$env:WORKSPACE_PATH = "C:\Users\YourName\workspace"
$env:RUNS_PATH = "C:\Users\YourName\runs"
$env:SCHEMAS_PATH = ".\schemas"
$env:OPENAI_API_KEY = "your-api-key"

# Spuštění serveru
python -m mcp_codex_orchestrator.main
```

### Varianta B: Instalace v WSL

```bash
# V Ubuntu/WSL
cd /mnt/c/Users/YourName/projects

# Klonování repozitáře
git clone https://github.com/your-org/mcp-codex-orchestrator.git
cd mcp-codex-orchestrator

# Vytvoření virtuálního prostředí
python3 -m venv .venv
source .venv/bin/activate

# Instalace závislostí
pip install -e .

# Nastavení proměnných prostředí
export WORKSPACE_PATH="/mnt/c/Users/YourName/workspace"
export RUNS_PATH="/mnt/c/Users/YourName/runs"
export SCHEMAS_PATH="./schemas"
export OPENAI_API_KEY="your-api-key"

# Spuštění serveru
python -m mcp_codex_orchestrator.main
```

### Varianta C: Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  mcp-codex-orchestrator:
    build: .
    volumes:
      - //var/run/docker.sock:/var/run/docker.sock
      - ${WORKSPACE_PATH:-./workspace}:/workspace
      - ${RUNS_PATH:-./runs}:/runs
      - ./schemas:/schemas:ro
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - WORKSPACE_PATH=/workspace
      - RUNS_PATH=/runs
      - SCHEMAS_PATH=/schemas
    ports:
      - "3000:3000"
```

```powershell
# Spuštění
docker-compose up -d
```

---

## Konfigurace VS Code

### Krok 1: Instalace rozšíření

1. Nainstalujte rozšíření **GitHub Copilot**
2. Nainstalujte rozšíření **Remote - WSL** (pokud používáte WSL)
3. Nainstalujte rozšíření **Docker**

### Krok 2: Konfigurace MCP serveru

Přidejte do `.vscode/settings.json`:

```json
{
  "github.copilot.advanced": {
    "servers": {
      "delegated-task-runner": {
        "command": "python",
        "args": ["-m", "mcp_codex_orchestrator.main"],
        "cwd": "${workspaceFolder}/mcp-codex-orchestrator",
        "env": {
          "WORKSPACE_PATH": "${workspaceFolder}/workspace",
          "RUNS_PATH": "${workspaceFolder}/runs",
          "SCHEMAS_PATH": "${workspaceFolder}/mcp-codex-orchestrator/schemas"
        }
      }
    }
  }
}
```

### Krok 3: Alternativní konfigurace pro WSL

```json
{
  "github.copilot.advanced": {
    "servers": {
      "delegated-task-runner": {
        "command": "wsl",
        "args": [
          "-e", "bash", "-c",
          "source ~/.venv/bin/activate && python -m mcp_codex_orchestrator.main"
        ],
        "env": {
          "WORKSPACE_PATH": "/mnt/c/Users/YourName/workspace",
          "RUNS_PATH": "/mnt/c/Users/YourName/runs"
        }
      }
    }
  }
}
```

---

## Řešení problémů

### Docker daemon není dostupný

**Symptom:**
```
Error: Cannot connect to the Docker daemon
```

**Řešení:**
1. Ověřte, že Docker Desktop běží
2. V PowerShell:
   ```powershell
   docker info
   ```
3. V WSL:
   ```bash
   # Ověřte WSL integraci
   docker info
   
   # Pokud nefunguje, zkontrolujte Docker Desktop → Settings → Resources → WSL Integration
   ```

### Problémy s cestami Windows ↔ WSL

**Symptom:**
- Soubory nejsou viditelné v kontejneru
- Permission denied

**Řešení:**

1. Použijte správný formát cest:
   - Windows PowerShell: `C:\Users\Name\workspace`
   - WSL/Linux: `/mnt/c/Users/Name/workspace`
   - Docker: `//c/Users/Name/workspace` nebo `/c/Users/Name/workspace`

2. Nastavte správná oprávnění v WSL:
   ```bash
   sudo chown -R $(whoami):$(whoami) /mnt/c/Users/Name/workspace
   ```

### Pomalý výkon na Windows souborech z WSL

**Symptom:**
- Pomalé čtení/zápis souborů v `/mnt/c/...`

**Řešení:**
1. Přesuňte projekt do nativního WSL filesystému:
   ```bash
   # Místo /mnt/c/... použijte
   ~/projects/my-project
   ```

2. Nebo použijte WSL2 s `localhostForwarding=true` v `.wslconfig`

### OpenAI API Key není detekován

**Symptom:**
```
Error: OPENAI_API_KEY not set
```

**Řešení:**

1. **Windows (trvalé)**:
   ```powershell
   [Environment]::SetEnvironmentVariable("OPENAI_API_KEY", "sk-...", "User")
   ```

2. **WSL (trvalé)**:
   ```bash
   echo 'export OPENAI_API_KEY="sk-..."' >> ~/.bashrc
   source ~/.bashrc
   ```

3. **VS Code settings.json**:
   ```json
   {
     "github.copilot.advanced": {
       "servers": {
         "delegated-task-runner": {
           "env": {
             "OPENAI_API_KEY": "sk-..."
           }
         }
       }
     }
   }
   ```

### Timeout při spouštění kontejneru

**Symptom:**
```
Error: Container timed out after 300 seconds
```

**Řešení:**
1. Zvyšte timeout:
   ```json
   {
     "timeout_seconds": 600
   }
   ```

2. Zkontrolujte dostupnost sítě v kontejneru:
   ```powershell
   docker run -it --rm openai/codex:latest ping api.openai.com
   ```

3. Zkontrolujte firewall a proxy nastavení

---

## Bezpečnostní doporučení

### API klíče

- ❌ Nikdy necommitujte API klíče do Gitu
- ✅ Použijte environment variables
- ✅ Použijte `.env` soubor (a přidejte do `.gitignore`)
- ✅ Použijte Windows Credential Manager nebo `pass` v Linuxu

### Docker socket

- ⚠️ Sdílení Docker socketu (`/var/run/docker.sock`) umožňuje plný přístup k Dockeru
- ✅ Použijte `security_mode: "readonly"` pro read-only operace
- ✅ Použijte `security_mode: "workspace_write"` pro omezený zápis
- ❌ Používejte `security_mode: "full_access"` pouze když je to nezbytné

### Workspace izolace

```json
{
  "task": "...",
  "security_mode": "workspace_write",
  "verify": true
}
```

- `verify: true` automaticky spustí testy a lint po změnách
- Umožňuje detekci neočekávaných změn

---

## Další zdroje

- [Docker Desktop Documentation](https://docs.docker.com/desktop/windows/)
- [WSL Documentation](https://docs.microsoft.com/en-us/windows/wsl/)
- [MCP Codex Orchestrator README](../README.md)
- [Security Modes Documentation](./SECURITY.md)

---

*Poslední aktualizace: 2025*
