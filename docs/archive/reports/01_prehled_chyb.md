# MCP Prompt Broker - Přehled nalezených chyb

**Datum analýzy:** 4. prosince 2025  
**Verze projektu:** 0.1.0  
**Analyzovaná verze MCP:** 1.23.1

---

## Shrnutí

Při analýze projektu MCP Prompt Broker bylo identifikováno **5 kritických chyb**, které brání správné instalaci a spuštění MCP serveru. Tento dokument poskytuje přehled všech nalezených problémů s doporučeními pro jejich opravu.

---

## 1. Kritická chyba: Nekompatibilní MCP Server API

### Popis problému
Server používá zastaralé API `server.run_stdio()`, které v aktuální verzi MCP knihovny (1.23.1) neexistuje.

### Projev chyby
```
AttributeError: 'Server' object has no attribute 'run_stdio'
```

### Lokace
- **Soubor:** `src/mcp_prompt_broker/server.py`
- **Řádek:** 134
- **Problematický kód:**
  ```python
  asyncio.run(server.run_stdio())
  ```

### Příčina
MCP knihovna změnila API mezi verzemi. Nová verze vyžaduje použití `stdio_server` jako async context manager a explicitní volání `server.run()` s `read_stream`, `write_stream` a `InitializationOptions`.

### Dopad
- **Kritický** - MCP server nelze spustit
- Instalační skript dokončí instalaci, ale server nefunguje

### Reference na opravu
Viz dokument: `02_oprava_mcp_server.md`

---

## 2. Kritická chyba: Špatná struktura balíčku v pyproject.toml

### Popis problému
Konfigurace `pyproject.toml` neobsahuje správné nastavení `packages` pro setuptools. Při instalaci nejsou nalezeny všechny potřebné moduly.

### Projev chyby
Při importu modulů z nainstalovaného balíčku:
```
ModuleNotFoundError: No module named 'config'
ModuleNotFoundError: No module named 'metadata'
ModuleNotFoundError: No module named 'router'
```

### Lokace
- **Soubor:** `pyproject.toml`
- **Chybějící sekce:** `[tool.setuptools.packages.find]`

### Příčina
`pyproject.toml` nespecifikuje, kde se nacházejí Python balíčky. Setuptools nedokáže automaticky najít všechny sub-balíčky v `src/` adresáři.

### Dopad
- **Kritický** - Importy v server.py selhávají po instalaci
- Balíček se nainstaluje, ale nelze jej použít

### Reference na opravu
Viz dokument: `04_oprava_pyproject.md`

---

## 3. Kritická chyba: Absolutní importy místo relativních

### Popis problému
Soubory v `src/` používají absolutní importy (`from config.profiles import ...`), které nefungují po instalaci balíčku.

### Projev chyby
```python
# server.py - problematické importy
from config.profiles import InstructionProfile, get_instruction_profiles
from metadata.parser import ParsedMetadata, analyze_prompt
from router.profile_router import EnhancedMetadata, ProfileRouter, RoutingResult
```

### Lokace
| Soubor | Problematický import |
|--------|---------------------|
| `src/mcp_prompt_broker/server.py` | `from config.profiles import ...` |
| `src/mcp_prompt_broker/server.py` | `from metadata.parser import ...` |
| `src/mcp_prompt_broker/server.py` | `from router.profile_router import ...` |
| `src/metadata/parser.py` | `from router.profile_router import ...` |
| `src/router/profile_router.py` | `from config.profiles import ...` |

### Příčina
Projekt používá `pytest.ini` s `pythonpath = src`, což funguje pro testy, ale po instalaci balíčku tyto cesty nejsou dostupné.

### Dopad
- **Kritický** - Server nelze spustit po instalaci pomocí `python -m mcp_prompt_broker`
- Testy fungují lokálně, ale nainstalovaný balíček ne

### Reference na opravu
Viz dokument: `03_oprava_importu.md`

---

## 4. Střední chyba: Instalační skript neobsahuje ověření

### Popis problému
Skript `install.ps1` neověřuje úspěšnost instalace ani nespouští žádné testy.

### Lokace
- **Soubor:** `install.ps1`
- **Funkce:** `Install-Dependencies`

### Projev chyby
- Skript reportuje úspěch, i když instalace selhala
- Žádná validace, že server lze skutečně spustit

### Dopad
- **Střední** - Uživatel neví, že instalace selhala
- Chyba se projeví až při pokusu o použití serveru

### Reference na opravu
Viz dokument: `05_oprava_install_ps1.md`

---

## 5. Nízká chyba: Chybějící pytest v závislostech

### Popis problému
`pyproject.toml` neobsahuje `pytest` jako dev závislost, ačkoliv projekt obsahuje testy.

### Lokace
- **Soubor:** `pyproject.toml`
- **Chybějící sekce:** `[project.optional-dependencies]`

### Projev chyby
```
ModuleNotFoundError: No module named 'pytest'
```

### Dopad
- **Nízká** - Vývojáři musí manuálně instalovat pytest

### Doporučená oprava
Přidat do `pyproject.toml`:
```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.0",
]
```

---

## Tabulka priorit oprav

| # | Chyba | Priorita | Komplexita | Soubor opravy |
|---|-------|----------|------------|---------------|
| 1 | MCP Server API | Kritická | Vysoká | `02_oprava_mcp_server.md` |
| 2 | pyproject.toml packages | Kritická | Nízká | `04_oprava_pyproject.md` |
| 3 | Absolutní importy | Kritická | Střední | `03_oprava_importu.md` |
| 4 | install.ps1 validace | Střední | Střední | `05_oprava_install_ps1.md` |
| 5 | Chybějící pytest | Nízká | Nízká | `04_oprava_pyproject.md` |

---

## Doporučený postup oprav

1. **Nejprve opravit `pyproject.toml`** - správná konfigurace balíčku
2. **Opravit importy** - změnit na relativní cesty v rámci balíčku
3. **Aktualizovat `server.py`** - implementovat nové MCP API
4. **Vylepšit `install.ps1`** - přidat validaci a lepší error handling
5. **Přidat dev závislosti** - pytest pro testování

---

## Další zjištění

### Funkční části projektu
- ✅ Testy procházejí (po manuální instalaci pytest)
- ✅ Logika routeru a profileů je správná
- ✅ Metadata parser funguje korektně
- ✅ Struktura kódu je čistá a dobře organizovaná

### Poznámky k architektuře
- Projekt správně odděluje config, metadata, router a server
- Použití dataclasses a frozen objektů je dobrou praxí
- Typové anotace jsou konzistentní

---

## Další dokumenty

- `02_oprava_mcp_server.md` - Detailní oprava MCP server API
- `03_oprava_importu.md` - Oprava importů pro správnou instalaci balíčku
- `04_oprava_pyproject.md` - Oprava konfigurace pyproject.toml
- `05_oprava_install_ps1.md` - Vylepšení instalačního skriptu
