# Oprava pyproject.toml

**Soubor:** `pyproject.toml`  
**Priorita:** Kritická  
**Komplexita:** Nízká

---

## Popis problému

Aktuální `pyproject.toml` neobsahuje správnou konfiguraci pro nalezení balíčků v `src/` adresáři. To způsobuje, že při instalaci nejsou nalezeny všechny moduly.

---

## Aktuální obsah

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "mcp-prompt-broker"
version = "0.1.0"
description = "MCP server that selects the best instruction for a user prompt."
authors = [{name = "Prompt Broker"}]
readme = "README.md"
requires-python = ">=3.10"
dependencies = [
    "mcp>=0.3.1",
]

[project.scripts]
mcp-prompt-broker = "mcp_prompt_broker.server:run"
```

---

## Problémy v aktuální konfiguraci

1. **Chybí `[tool.setuptools.packages.find]`** - setuptools neví, kde hledat balíčky
2. **Chybí `[tool.setuptools.package-dir]`** - není specifikován `src` layout
3. **Zastaralá verze MCP** - `mcp>=0.3.1` je příliš stará
4. **Chybí dev závislosti** - pytest není v závislostech
5. **Chybí entry point pro modul** - `python -m` nemusí fungovat správně

---

## Opravený pyproject.toml

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "mcp-prompt-broker"
version = "0.1.0"
description = "MCP server that selects the best instruction for a user prompt."
authors = [{ name = "Prompt Broker" }]
readme = "README.md"
requires-python = ">=3.10"
license = { text = "MIT" }
keywords = ["mcp", "llm", "copilot", "prompt", "routing"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Software Development :: Libraries :: Python Modules",
]
dependencies = [
    "mcp>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21",
    "mypy>=1.0",
    "ruff>=0.1",
]

[project.scripts]
mcp-prompt-broker = "mcp_prompt_broker.server:run"

[project.urls]
Homepage = "https://github.com/michaelprinc/MCP_prompt_broker"
Repository = "https://github.com/michaelprinc/MCP_prompt_broker"
Issues = "https://github.com/michaelprinc/MCP_prompt_broker/issues"

# Konfigurace setuptools pro src layout
[tool.setuptools]
package-dir = { "" = "src" }

[tool.setuptools.packages.find]
where = ["src"]
include = ["mcp_prompt_broker*"]

# Pytest konfigurace
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
asyncio_mode = "auto"

# Mypy konfigurace
[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
ignore_missing_imports = true

# Ruff konfigurace
[tool.ruff]
line-length = 100
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]
ignore = ["E501"]
```

---

## Vysvětlení klíčových změn

### 1. Konfigurace setuptools

```toml
[tool.setuptools]
package-dir = { "" = "src" }

[tool.setuptools.packages.find]
where = ["src"]
include = ["mcp_prompt_broker*"]
```

- `package-dir = { "" = "src" }` - říká setuptools, že kořen balíčků je v `src/`
- `where = ["src"]` - hledá balíčky v adresáři `src/`
- `include = ["mcp_prompt_broker*"]` - zahrnuje hlavní balíček a všechny sub-balíčky

### 2. Aktualizovaná verze MCP

```toml
dependencies = [
    "mcp>=1.0.0",
]
```

- Nainstalovaná verze je 1.23.1, takže minimální požadavek by měl být alespoň 1.0.0

### 3. Dev závislosti

```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21",
    "mypy>=1.0",
    "ruff>=0.1",
]
```

- Instalace: `pip install -e ".[dev]"`
- Obsahuje nástroje pro vývoj a testování

### 4. Pytest integrace

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
asyncio_mode = "auto"
```

- Nahrazuje obsah `pytest.ini`
- Přidává podporu pro asyncio testy

---

## Varianta pro zachování současné struktury

Pokud nechcete přesouvat moduly pod `mcp_prompt_broker`, použijte tuto konfiguraci:

```toml
[tool.setuptools]
package-dir = { "" = "src" }

[tool.setuptools.packages.find]
where = ["src"]
include = [
    "mcp_prompt_broker*",
    "config*",
    "metadata*",
    "router*",
]
```

**Poznámka:** Tato varianta vyžaduje, aby `config`, `metadata` a `router` byly instalovány jako samostatné top-level balíčky, což může způsobovat konflikty s jinými knihovnami.

---

## Aktualizace pytest.ini

Po přidání pytest konfigurace do `pyproject.toml` můžete `pytest.ini` zjednodušit nebo smazat:

**Možnost 1:** Smazat pytest.ini (doporučeno)
```powershell
Remove-Item pytest.ini
```

**Možnost 2:** Minimální pytest.ini
```ini
[pytest]
# Konfigurace je v pyproject.toml
```

---

## Verifikace

```powershell
# 1. Odstranit starou instalaci
.venv\Scripts\python.exe -m pip uninstall mcp-prompt-broker -y

# 2. Reinstalovat s dev závislostmi
.venv\Scripts\python.exe -m pip install -e ".[dev]"

# 3. Ověřit instalaci
.venv\Scripts\python.exe -m pip show mcp-prompt-broker

# 4. Ověřit, že balíčky jsou dostupné
.venv\Scripts\python.exe -c "import mcp_prompt_broker; print(mcp_prompt_broker)"

# 5. Spustit testy
.venv\Scripts\python.exe -m pytest tests/ -v
```

---

## Očekávaný výstup pip show

```
Name: mcp-prompt-broker
Version: 0.1.0
Summary: MCP server that selects the best instruction for a user prompt.
Home-page: https://github.com/michaelprinc/MCP_prompt_broker
Author: Prompt Broker
License: MIT
Location: c:\data_science_projects\mcp_prompt_broker\.venv\lib\site-packages
Requires: mcp
Required-by:
```

---

## Kontrolní seznam

- [ ] Aktualizovat `pyproject.toml` s novou konfigurací
- [ ] Přesunout moduly pod `mcp_prompt_broker` (viz `03_oprava_importu.md`)
- [ ] Smazat nebo aktualizovat `pytest.ini`
- [ ] Reinstalovat balíček
- [ ] Spustit testy
- [ ] Ověřit, že server lze spustit

---

## Další kroky

1. ✅ Aplikovat změny v tomto dokumentu
2. ✅ Provést změny dle `03_oprava_importu.md`
3. ✅ Provést změny dle `02_oprava_mcp_server.md`
4. ➡️ Pokračovat na `05_oprava_install_ps1.md`
