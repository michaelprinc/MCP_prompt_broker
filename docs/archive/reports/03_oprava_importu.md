# Oprava importů v projektu

**Priorita:** Kritická  
**Komplexita:** Střední

---

## Popis problému

Projekt používá absolutní importy, které fungují pouze při vývoji díky nastavení `pythonpath = src` v `pytest.ini`. Po instalaci balíčku tyto importy selhávají, protože Python neví, kde hledat moduly `config`, `metadata` a `router`.

---

## Aktuální stav - Problematické importy

### 1. src/mcp_prompt_broker/server.py

```python
# Řádky 12-14 - ŠPATNĚ
from config.profiles import InstructionProfile, get_instruction_profiles
from metadata.parser import ParsedMetadata, analyze_prompt
from router.profile_router import EnhancedMetadata, ProfileRouter, RoutingResult
```

### 2. src/metadata/parser.py

```python
# Řádek 7 - ŠPATNĚ
from router.profile_router import EnhancedMetadata
```

### 3. src/router/profile_router.py

```python
# Řádek 8 - ŠPATNĚ
from config.profiles import InstructionProfile, get_instruction_profiles
```

---

## Struktura balíčku

Pro pochopení opravy je důležité znát strukturu:

```
src/
├── __init__.py              # root balíček
├── config/
│   ├── __init__.py
│   └── profiles.py
├── mcp_prompt_broker/
│   ├── __init__.py
│   ├── __main__.py
│   ├── instructions.py
│   └── server.py
├── metadata/
│   ├── __init__.py
│   └── parser.py
└── router/
    ├── __init__.py
    └── profile_router.py
```

---

## Řešení - Dva možné přístupy

### Přístup A: Přesun modulů do mcp_prompt_broker (Doporučeno)

Přesunout všechny moduly přímo pod `mcp_prompt_broker`, aby tvořily jeden konzistentní balíček.

**Nová struktura:**
```
src/
└── mcp_prompt_broker/
    ├── __init__.py
    ├── __main__.py
    ├── instructions.py
    ├── server.py
    ├── config/
    │   ├── __init__.py
    │   └── profiles.py
    ├── metadata/
    │   ├── __init__.py
    │   └── parser.py
    └── router/
        ├── __init__.py
        └── profile_router.py
```

**Výhody:**
- Čistá struktura balíčku
- Jednodušší importy
- Lepší pro distribuci

### Přístup B: Relativní importy v rámci src (Rychlejší oprava)

Zachovat současnou strukturu, ale upravit importy.

---

## Implementace - Přístup A (Doporučeno)

### Krok 1: Přesun adresářů

```powershell
# PowerShell příkazy
Move-Item -Path "src/config" -Destination "src/mcp_prompt_broker/"
Move-Item -Path "src/metadata" -Destination "src/mcp_prompt_broker/"
Move-Item -Path "src/router" -Destination "src/mcp_prompt_broker/"
```

### Krok 2: Oprava importů v server.py

```python
# src/mcp_prompt_broker/server.py
"""MCP server entrypoint and wiring for the prompt broker."""
from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any, Dict, List, Mapping

import mcp.server.stdio
import mcp.types as types
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.models import InitializationOptions

# Relativní importy
from .config.profiles import InstructionProfile, get_instruction_profiles
from .metadata.parser import ParsedMetadata, analyze_prompt
from .router.profile_router import EnhancedMetadata, ProfileRouter, RoutingResult
```

### Krok 3: Oprava importů v parser.py

```python
# src/mcp_prompt_broker/metadata/parser.py
"""Lightweight prompt analysis for routing and auditing metadata."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping, MutableMapping

# Relativní import
from ..router.profile_router import EnhancedMetadata

# ... zbytek kódu beze změny
```

### Krok 4: Oprava importů v profile_router.py

```python
# src/mcp_prompt_broker/router/profile_router.py
"""Router for mapping enhanced prompt metadata to instruction profiles."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Iterable, Mapping, MutableMapping, Sequence

# Relativní import
from ..config.profiles import InstructionProfile, get_instruction_profiles

# ... zbytek kódu beze změny
```

### Krok 5: Aktualizace __init__.py souborů

**src/mcp_prompt_broker/config/__init__.py:**
```python
"""Configuration module for the prompt broker."""

from .profiles import InstructionProfile, get_instruction_profiles

__all__ = ["InstructionProfile", "get_instruction_profiles"]
```

**src/mcp_prompt_broker/metadata/__init__.py:**
```python
"""Metadata analysis utilities for the prompt broker."""

from .parser import ParsedMetadata, analyze_prompt

__all__ = ["ParsedMetadata", "analyze_prompt"]
```

**src/mcp_prompt_broker/router/__init__.py:**
```python
"""Routing module for instruction profile selection."""

from .profile_router import EnhancedMetadata, ProfileRouter, RoutingResult

__all__ = ["EnhancedMetadata", "ProfileRouter", "RoutingResult"]
```

### Krok 6: Aktualizace testů

```python
# tests/test_metadata_parser.py
import pytest

from mcp_prompt_broker.metadata.parser import analyze_prompt

# ... testy beze změny
```

```python
# tests/test_profile_router.py
import pytest

from mcp_prompt_broker.router.profile_router import EnhancedMetadata, ProfileRouter
from mcp_prompt_broker.config.profiles import get_instruction_profiles

# ... testy beze změny
```

### Krok 7: Aktualizace pytest.ini

```ini
[pytest]
pythonpath = src
testpaths = tests
```

---

## Implementace - Přístup B (Rychlá oprava)

Pokud nechcete měnit strukturu, upravte importy takto:

### server.py

```python
# Použít src. prefix
from src.config.profiles import InstructionProfile, get_instruction_profiles
from src.metadata.parser import ParsedMetadata, analyze_prompt
from src.router.profile_router import EnhancedMetadata, ProfileRouter, RoutingResult
```

A přidat do `pyproject.toml`:

```toml
[tool.setuptools.packages.find]
where = ["."]
include = ["src", "src.*"]
```

**Nevýhoda:** Méně elegantní, import cesty jsou dlouhé.

---

## Kompletní skript pro přesun (Přístup A)

```powershell
# migrate_structure.ps1
$srcPath = "src"
$targetPath = "src/mcp_prompt_broker"

# Přesun adresářů
if (Test-Path "$srcPath/config") {
    Move-Item -Path "$srcPath/config" -Destination "$targetPath/" -Force
}
if (Test-Path "$srcPath/metadata") {
    Move-Item -Path "$srcPath/metadata" -Destination "$targetPath/" -Force
}
if (Test-Path "$srcPath/router") {
    Move-Item -Path "$srcPath/router" -Destination "$targetPath/" -Force
}

# Smazat prázdný src/__init__.py pokud existuje
if ((Get-Content "$srcPath/__init__.py" -ErrorAction SilentlyContinue) -eq $null) {
    Remove-Item "$srcPath/__init__.py" -Force -ErrorAction SilentlyContinue
}

Write-Host "Struktura přesunuta. Nyní opravte importy podle dokumentace."
```

---

## Tabulka změn importů

| Soubor | Starý import | Nový import |
|--------|--------------|-------------|
| server.py | `from config.profiles import ...` | `from .config.profiles import ...` |
| server.py | `from metadata.parser import ...` | `from .metadata.parser import ...` |
| server.py | `from router.profile_router import ...` | `from .router.profile_router import ...` |
| parser.py | `from router.profile_router import ...` | `from ..router.profile_router import ...` |
| profile_router.py | `from config.profiles import ...` | `from ..config.profiles import ...` |
| test_metadata_parser.py | `from metadata.parser import ...` | `from mcp_prompt_broker.metadata.parser import ...` |
| test_profile_router.py | `from router.profile_router import ...` | `from mcp_prompt_broker.router.profile_router import ...` |
| test_profile_router.py | `from config.profiles import ...` | `from mcp_prompt_broker.config.profiles import ...` |

---

## Verifikace

Po provedení změn:

```powershell
# 1. Reinstalovat balíček
.venv\Scripts\python.exe -m pip install -e .

# 2. Ověřit importy
.venv\Scripts\python.exe -c "from mcp_prompt_broker.config.profiles import get_instruction_profiles; print('OK')"
.venv\Scripts\python.exe -c "from mcp_prompt_broker.metadata.parser import analyze_prompt; print('OK')"
.venv\Scripts\python.exe -c "from mcp_prompt_broker.router.profile_router import ProfileRouter; print('OK')"

# 3. Spustit testy
.venv\Scripts\python.exe -m pytest tests/ -v
```

---

## Další kroky

1. ✅ Provést změny dle tohoto dokumentu
2. ✅ Aktualizovat `pyproject.toml` (viz `04_oprava_pyproject.md`)
3. ✅ Reinstalovat balíček
4. ✅ Spustit testy
