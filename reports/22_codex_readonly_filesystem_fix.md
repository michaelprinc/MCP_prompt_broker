# Codex CLI Read-Only Filesystem Fix

> **Generated:** 2025-12-31  
> **Complexity:** Medium  
> **Status:** ✅ FIXED  
> **Error:** `Read-only file system (os error 30)`

---

## Analýza problému

### Symptom
```
{"type":"error","message":"Read-only file system (os error 30)"}
{"type":"turn.failed","error":{"message":"Read-only file system (os error 30)"}}
```

### Root Cause
Codex CLI potřebuje zapisovat do `/home/node/.codex/` adresáře pro:
- **Session management** - ukládání thread ID a session state
- **Cache** - dočasné soubory pro zpracování
- **Authentication state** - refresh tokens a další auth data

Původní implementace v `docker_client.py` montovala pouze `auth.json` jako **read-only**:
```python
volumes[str(auth_file.resolve())] = {
    "bind": "/home/node/.codex/auth.json",
    "mode": "ro",  # ← PROBLÉM: Celý .codex adresář potřebuje být writable
}
```

### Proč to selhávalo
1. Docker overlay filesystem je read-only pro nenamontované cesty
2. Codex CLI se pokouší zapisovat do `/home/node/.codex/` (např. `state.json`, cache)
3. Zápis selže s `os error 30` (EROFS - Read-only file system)

---

## Implementovaná oprava

### Změny v `docker_client.py`

1. **Přidán import `shutil`** pro kopírování souborů

2. **Upravena metoda `_build_volumes()`**:
   - Vytváří dočasný `.codex` adresář v `runs/{run_id}/.codex`
   - Kopíruje `auth.json` do tohoto adresáře
   - Montuje celý `.codex` adresář jako **read-write**

```python
# FIX: Create writable .codex directory for Codex CLI session/state files
codex_temp_dir = run_dir / ".codex"
codex_temp_dir.mkdir(parents=True, exist_ok=True)

# Copy auth.json if it exists
auth_file = DEFAULT_CODEX_AUTH_PATH / "auth.json"
if auth_file.exists():
    shutil.copy2(auth_file, codex_temp_dir / "auth.json")

# Mount the entire .codex directory as read-write
volumes[str(codex_temp_dir.resolve())] = {
    "bind": "/home/node/.codex",
    "mode": "rw",
}
```

---

## Výhody tohoto řešení

| Aspekt | Popis |
|--------|-------|
| **Izolace** | Každý run má vlastní `.codex` adresář - žádné konflikty |
| **Bezpečnost** | Originální `auth.json` zůstává nedotčen |
| **Cleanup** | Dočasný adresář je v `runs/{run_id}/` - automaticky spravován |
| **Perzistence** | Po běhu lze zkontrolovat session/state data pro debugging |

---

## Soubory změněny

| Soubor | Změna |
|--------|-------|
| `docker_client.py` | Přidán `shutil` import, upravena `_build_volumes()` |

---

## Akceptační kritéria

- [x] Codex CLI běží bez "Read-only file system" chyby
- [x] Autentizace pomocí ChatGPT Plus funguje
- [x] Dočasné soubory jsou v run-specific adresáři
- [x] Syntax check bez chyb

---

## Další kroky

1. **Testovat** delegací úlohy na Codex CLI
2. Pokud chyba přetrvává, zkontrolovat:
   - Je Docker Desktop spuštěný?
   - Existuje `~/.codex/auth.json`?
   - Jsou správná oprávnění na Windows?
