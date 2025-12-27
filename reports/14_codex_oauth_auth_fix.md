# Report: Oprava OAuth autentizace pro MCP Codex Orchestrator

**Datum:** 2025-12-26  
**Autor:** GitHub Copilot  
**Verze:** 1.0

---

## 📋 Shrnutí

Tento report dokumentuje analýzu a opravu problému s OAuth autentizací u MCP serveru `codex-orchestrator`. Autentizace pomocí ChatGPT Plus předplatného nefungovala, protože Docker kontejner neměl přístup k souboru `auth.json` obsahujícímu OAuth tokeny.

---

## 🔍 Analýza problému

### Příznaky
- MCP server `codex-orchestrator` nedokázal autentizovat Codex CLI v Docker kontejneru
- OAuth autentizace s ChatGPT Plus selhávala
- Chyba: "Not signed in" nebo podobné autentizační chyby

### Kořenová příčina

**Nesoulad mezi `docker-compose.yml` a Python kódem `docker_client.py`:**

1. **V `docker-compose.yml`** byl mount správně definován:
   ```yaml
   volumes:
     - ${CODEX_AUTH_PATH:-~/.codex}/auth.json:/home/node/.codex/auth.json:ro
   ```

2. **V `docker_client.py`** v metodě `_build_volumes()` tento mount **chyběl**:
   ```python
   def _build_volumes(self, workspace_path, runs_path, run_id):
       return {
           str(workspace_path.resolve()): {"bind": "/workspace", "mode": "rw"},
           str(run_dir.resolve()): {"bind": f"/runs/{run_id}", "mode": "rw"},
           # ❌ CHYBĚL mount pro auth.json!
       }
   ```

### Jak Codex CLI autentizace funguje

Podle [dokumentace OpenAI Codex](https://github.com/openai/codex):

1. **Přihlášení:** `codex login` spustí OAuth flow s ChatGPT
2. **Uložení tokenů:** Tokeny se ukládají do `$CODEX_HOME/auth.json` (výchozí: `~/.codex/auth.json`)
3. **Struktura `auth.json`:**
   ```json
   {
     "OPENAI_API_KEY": null,
     "tokens": {
       "id_token": "...",
       "access_token": "...",
       "refresh_token": "...",
       "account_id": "..."
     },
     "last_refresh": "2025-12-26T10:00:00Z"
   }
   ```
4. **V kontejneru:** Codex CLI očekává `auth.json` v `/home/node/.codex/auth.json`

---

## ✅ Implementovaná oprava

### 1. Úprava `docker_client.py`

**Soubor:** `mcp-codex-orchestrator/src/mcp_codex_orchestrator/orchestrator/docker_client.py`

**Přidána konstanta pro cestu k autentizaci:**
```python
# Default path for Codex authentication file
DEFAULT_CODEX_AUTH_PATH = Path(
    os.getenv("CODEX_AUTH_PATH", os.path.expanduser("~/.codex"))
)
```

**Rozšířena metoda `_build_volumes()`:**
```python
def _build_volumes(self, workspace_path, runs_path, run_id):
    """Build volume mounts for container.
    
    Includes:
    - Workspace directory (read-write)
    - Run-specific logs directory (read-write)
    - Codex auth.json for OAuth/ChatGPT Plus authentication (read-only)
    """
    run_dir = runs_path / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    
    volumes = {
        str(workspace_path.resolve()): {"bind": "/workspace", "mode": "rw"},
        str(run_dir.resolve()): {"bind": f"/runs/{run_id}", "mode": "rw"},
    }
    
    # Mount auth.json for OAuth/ChatGPT Plus authentication
    auth_file = DEFAULT_CODEX_AUTH_PATH / "auth.json"
    if auth_file.exists():
        volumes[str(auth_file.resolve())] = {
            "bind": "/home/node/.codex/auth.json",
            "mode": "ro",  # Read-only for security
        }
        logger.debug("Mounting auth.json for OAuth authentication")
    else:
        logger.warning(
            "auth.json not found - OAuth authentication may fail",
            hint="Run 'codex login' to authenticate with ChatGPT Plus"
        )
    
    return volumes
```

### 2. Úprava MCP konfigurace

**Soubor:** `.vscode/mcp.json`

**Přidána proměnná prostředí `CODEX_AUTH_PATH`:**
```json
"codex-orchestrator": {
    "env": {
        "DOCKER_COMPOSE_PATH": "${workspaceFolder}/mcp-codex-orchestrator/docker",
        "WORKSPACE_PATH": "${workspaceFolder}/mcp-codex-orchestrator/workspace",
        "RUNS_PATH": "${workspaceFolder}/mcp-codex-orchestrator/runs",
        "CODEX_AUTH_PATH": "${env:USERPROFILE}/.codex"  // ✅ PŘIDÁNO
    }
}
```

---

## 🧪 Testování

### Unit testy
```
53 passed, 2 warnings in 1.05s
```

Všechny existující testy prošly bez regresí.

### Ověření existence auth.json
```powershell
Test-Path "$env:USERPROFILE\.codex\auth.json"
# Výsledek: True
```

---

## 📁 Změněné soubory

| Soubor | Typ změny | Popis |
|--------|-----------|-------|
| `mcp-codex-orchestrator/src/mcp_codex_orchestrator/orchestrator/docker_client.py` | Modifikace | Přidán mount pro auth.json |
| `.vscode/mcp.json` | Modifikace | Přidána env proměnná CODEX_AUTH_PATH |

---

## 🔧 Konfigurace

### Environment proměnné

| Proměnná | Výchozí hodnota | Popis |
|----------|-----------------|-------|
| `CODEX_AUTH_PATH` | `~/.codex` | Cesta k adresáři s auth.json |
| `OPENAI_API_KEY` | (volitelné) | API klíč pro fallback autentizaci |

### Požadavky

1. **Před použitím** je nutné spustit `codex login` pro vytvoření `auth.json`
2. Soubor `auth.json` musí být čitelný uživatelem spouštějícím MCP server
3. Docker musí mít přístup k cestě definované v `CODEX_AUTH_PATH`

---

## 📚 Reference

- [OpenAI Codex CLI - Authentication](https://github.com/openai/codex/blob/main/docs/authentication.md)
- [Codex CLI - Config](https://github.com/openai/codex/blob/main/docs/config.md)
- [Docker SDK for Python - Volumes](https://docker-py.readthedocs.io/en/stable/containers.html)

---

## ⚠️ Bezpečnostní poznámky

1. **Read-only mount:** `auth.json` je mountován jako read-only (`ro`) pro prevenci nechtěné modifikace
2. **Citlivá data:** `auth.json` obsahuje OAuth tokeny - nepřidávejte do Git!
3. **Oprávnění:** Kontejner běží jako uživatel `node` (UID 1000) pro bezpečnost

---

## 🚀 Další kroky

- [ ] Přidat integrační test pro OAuth autentizaci v Docker kontejneru
- [ ] Aktualizovat dokumentaci v `TROUBLESHOOTING.md`
- [ ] Zvážit podporu pro keyring jako alternativní credential store
