# Implementační plán: Oprava po restrukturalizaci adresářů

**Datum:** 2026-01-01  
**Autor:** GitHub Copilot  
**Priorita:** Kritická  
**Stav:** Plánováno

---

## 1. Analýza problému

### 1.1 Popis chyby
```
K:\Data_science_projects\MCP_Prompt_Broker\.venv\Scripts\python.exe: No module named mcp_prompt_broker
```

### 1.2 Příčina
Po restrukturalizaci adresářové struktury workspace (přesun balíčků do `packages/`) jsou **editable instalace** v `.venv` stále nakonfigurovány na **staré cesty**, které již neexistují.

### 1.3 Identifikované nekonzistentní .pth soubory

| Soubor | Aktuální (neplatná) cesta | Správná cesta |
|--------|---------------------------|---------------|
| `__editable__.mcp_prompt_broker-0.1.0.pth` | `K:\...\src` (root) | `K:\...\packages\mcp-prompt-broker\src` |
| `_llama_orchestrator.pth` | `K:\...\llama-orchestrator\src` | `K:\...\packages\llama-orchestrator\src` |
| `_mcp_codex_orchestrator.pth` | `K:\...\mcp-codex-orchestrator\src` | `K:\...\packages\mcp-codex-orchestrator\src` |

### 1.4 Další identifikované problémy

1. **Nekonzistentní adresář `mcp_codex_orchestrator/`** v root workspace
   - Obsahuje pouze kompatibilní shim (`__init__.py`)
   - Měl by být smazán, protože skutečný kód je v `packages/mcp-codex-orchestrator/`
   
2. **Neplatné cesty v `.vscode/mcp.json`**
   - `DOCKER_COMPOSE_PATH`, `WORKSPACE_PATH`, `RUNS_PATH` odkazují na staré cesty

---

## 2. Implementační checklist

### Fáze 1: Reinstalace balíčků (kritická)

- [x] **1.1** Odinstalovat stávající editable balíčky
  ```powershell
  .venv\Scripts\pip.exe uninstall -y mcp-prompt-broker llama-orchestrator mcp-codex-orchestrator
  ```

- [x] **1.2** Reinstalovat balíčky z nových cest
  ```powershell
  .venv\Scripts\pip.exe install -e packages/mcp-prompt-broker
  .venv\Scripts\pip.exe install -e packages/llama-orchestrator
  .venv\Scripts\pip.exe install -e packages/mcp-codex-orchestrator
  ```

- [x] **1.3** Ověřit instalaci
  ```powershell
  .venv\Scripts\python.exe -m mcp_prompt_broker --help
  ```

### Fáze 2: Aktualizace konfigurace

- [x] **2.1** Aktualizovat `.vscode/mcp.json` - opravit cesty pro `delegated-task-runner`
  - Změnit `mcp-codex-orchestrator/docker` → `packages/mcp-codex-orchestrator/docker`
  - Změnit `mcp-codex-orchestrator/workspace` → `packages/mcp-codex-orchestrator/workspace`
  - Změnit `mcp-codex-orchestrator/runs` → `packages/mcp-codex-orchestrator/runs`

### Fáze 3: Úklid workspace

- [x] **3.1** Smazat zbytečný shim adresář `mcp_codex_orchestrator/`
  ```powershell
  Remove-Item -Recurse -Force mcp_codex_orchestrator
  ```

- [x] **3.2** Ověřit, že v root nejsou další nepoužívané adresáře

### Fáze 4: Verifikace

- [x] **4.1** Spustit testy (52/52 passed)
  ```powershell
  .venv\Scripts\pytest.exe tests/ -v
  ```

- [x] **4.2** Ověřit funkčnost MCP serverů
  ```powershell
  .venv\Scripts\python.exe -m mcp_prompt_broker   # OK - loaded 47 profiles
  .venv\Scripts\python.exe -m mcp_codex_orchestrator  # OK - starts MCP server
  ```

### Fáze 5: Dodatečné opravy

- [x] **5.1** Vytvořit chybějící `README.md` v `packages/mcp-prompt-broker/`

---

## 3. Rizika a mitigace

| Riziko | Pravděpodobnost | Mitigace |
|--------|-----------------|----------|
| Další závislosti na starých cestách | Střední | Grep search po celém workspace |
| Broken imports v testech | Nízká | Testy jsou relativní k balíčku |
| Nekompatibilní verze závislostí | Nízká | Použít stejné verze z pyproject.toml |

---

## 4. Rollback plán

V případě problémů:
1. Obnovit `mcp_codex_orchestrator/` ze git history
2. Reinstalovat balíčky ze starých cest (pokud existují)
3. Vrátit změny v `.vscode/mcp.json`

```powershell
git checkout HEAD~1 -- mcp_codex_orchestrator/
git checkout HEAD~1 -- .vscode/mcp.json
```

---

## 5. Akceptační kritéria

- [x] Chyba `No module named mcp_prompt_broker` je vyřešena
- [x] Všechny MCP servery se spouští bez chyb
- [x] Pytest testy procházejí (52/52 passed)
- [x] Workspace neobsahuje duplicitní/nekonzistentní adresáře

---

## 6. Provedené změny

| Soubor/Adresář | Akce | Popis |
|----------------|------|-------|
| `.venv/` | Reinstalace | Přeinstalování editable balíčků z `packages/` |
| `.vscode/mcp.json` | Úprava | Aktualizované cesty pro `delegated-task-runner` |
| `mcp_codex_orchestrator/` | Smazán | Odstraněn nekonzistentní shim adresář |
| `packages/mcp-prompt-broker/README.md` | Vytvořen | Nový README pro hatchling build |

**Datum dokončení:** 2026-01-01  
**Stav:** ✅ DONE
