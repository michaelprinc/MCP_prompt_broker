# MCP Prompt Broker - Technická dokumentace modulu

> **Verze dokumentace:** 1.0.0  
> **Verze modulu:** 0.1.0  
> **Datum:** 31. prosince 2025  
> **Úroveň:** 3/4 - Module Technical Documentation

---

## 📋 Obsah

1. [Přehled modulu](#přehled-modulu)
2. [Struktura adresářů](#struktura-adresářů)
3. [Klíčové komponenty](#klíčové-komponenty)
4. [Algoritmus routingu](#algoritmus-routingu)
5. [Systém profilů](#systém-profilů)
6. [Konfigurace](#konfigurace)
7. [Testování](#testování)
8. [Rozšíření](#rozšíření)

---

## Přehled modulu

**MCP Prompt Broker** je hlavní modul ekosystému, který poskytuje inteligentní routing promptů k optimálním instrukcím.

### Technické charakteristiky

| Vlastnost | Hodnota |
|-----------|---------|
| **Jazyk** | Python 3.10+ |
| **Protokol** | MCP (Model Context Protocol) |
| **Transport** | stdio |
| **Package** | `mcp-prompt-broker` |
| **Entry point** | `mcp_prompt_broker.server:run` |

### Závislosti

```toml
[dependencies]
mcp = ">=1.0.0"
pyyaml = ">=6.0"

[dev-dependencies]
pytest = ">=7.0"
pytest-asyncio = ">=0.21"
```

---

## Struktura adresářů

```
src/mcp_prompt_broker/
├── __init__.py              # Package init
├── __main__.py              # CLI entry point
├── server.py                # MCP server implementation
├── profile_parser.py        # Markdown profile parser
├── metadata_registry.py     # Central metadata store
├── instructions.py          # Instruction utilities
├── config/
│   ├── __init__.py
│   └── profiles.py          # Profile data models
├── metadata/
│   ├── __init__.py
│   └── parser.py            # Prompt metadata extraction
├── router/
│   ├── __init__.py
│   └── profile_router.py    # Routing engine
├── integrations/
│   └── __init__.py          # External integrations
└── copilot-profiles/
    ├── profiles_metadata.json
    ├── template/
    │   └── PROFILE_TEMPLATE.md
    ├── technical_support.md
    ├── creative_brainstorm.md
    ├── privacy_sensitive.md
    ├── general_default.md
    └── ... (45+ profiles)
```

---

## Klíčové komponenty

### 1. server.py - MCP Server

Hlavní entry point pro MCP komunikaci.

```python
# Klíčové funkce
def _build_server(loader: ProfileLoader) -> Server:
    """Vytvoří MCP server s tools."""
    
@server.list_tools()
async def list_tools() -> List[types.Tool]:
    """Registruje dostupné MCP tools."""
    
@server.call_tool()
async def call_tool(name: str, arguments: dict) -> List[types.TextContent]:
    """Zpracuje volání MCP tool."""
```

**MCP Tools:**

| Tool | Popis | Primární |
|------|-------|----------|
| `resolve_prompt` | Analyzuje prompt a vrací optimální profil | ✅ |
| `get_profile` | Alias pro resolve_prompt | ✅ |
| `list_profiles` | Seznam všech profilů | |
| `get_checklist` | Checklist pro konkrétní profil | |
| `get_profile_metadata` | Metadata profilu | |
| `find_profiles_by_capability` | Hledání podle schopnosti | |
| `find_profiles_by_domain` | Hledání podle domény | |
| `get_registry_summary` | Statistiky registry | |
| `reload_profiles` | Hot-reload profilů | |

### 2. profile_router.py - Routing Engine

Implementuje algoritmus výběru optimálního profilu.

```python
class ProfileRouter:
    """Routing engine pro výběr profilu."""
    
    def __init__(self, profiles: List[InstructionProfile]):
        self.profiles = profiles
    
    def route(
        self, 
        prompt: str, 
        metadata: EnhancedMetadata
    ) -> RoutingResult:
        """
        Provede routing na základě promptu a metadata.
        
        Returns:
            RoutingResult s vybraným profilem a skóre
        """
```

**Datové struktury:**

```python
@dataclass
class EnhancedMetadata:
    prompt: str
    intent: str
    domain: str
    topics: List[str]
    sensitivity: str
    safety_score: int
    tone: str
    complexity: str

@dataclass
class RoutingResult:
    profile: InstructionProfile
    metadata: EnhancedMetadata
    routing: RoutingScore
    
@dataclass
class RoutingScore:
    score: int
    consistency: float
```

### 3. profile_parser.py - Profile Loader

Parsuje Markdown profily s YAML frontmatter.

```python
class ProfileLoader:
    """Načítá a parsuje profily z Markdown souborů."""
    
    def __init__(self, profiles_dir: Path):
        self.profiles_dir = profiles_dir
        self.profiles: List[ParsedProfile] = []
        self._load_profiles()
    
    def reload(self) -> int:
        """Hot-reload profilů bez restartu serveru."""
        
    def get_profile_by_name(self, name: str) -> Optional[ParsedProfile]:
        """Vrací profil podle jména."""
```

### 4. metadata/parser.py - Metadata Extractor

Extrahuje metadata z uživatelského promptu.

```python
def analyze_prompt(prompt: str) -> ParsedMetadata:
    """
    Analyzuje prompt a extrahuje metadata.
    
    Detekuje:
    - Intent (code_generation, debugging, creative, ...)
    - Domain (engineering, healthcare, finance, ...)
    - Sensitivity (low, medium, high)
    - Topics (specifická klíčová slova)
    - Complexity (simple, medium, complex)
    """

@dataclass
class ParsedMetadata:
    intent: str
    domain: str
    topics: List[str]
    sensitivity: str
    safety_score: int
    tone: str
    complexity: str
```

### 5. metadata_registry.py - Central Registry

Spravuje centrální registr metadata všech profilů.

```python
def get_registry_summary() -> dict:
    """
    Vrací souhrn registru profilů.
    
    Returns:
        {
            "total_profiles": 45,
            "domains_covered": ["engineering", "healthcare", ...],
            "capabilities_covered": ["debugging", "ideation", ...],
            "complexity_distribution": {"simple": 20, "complex": 25}
        }
    """
```

---

## Algoritmus routingu

### Scoring algoritmus

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          SCORING ALGORITHM                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Pro každý profil P a metadata M:                                           │
│                                                                             │
│  1. BASE SCORE                                                              │
│     score = P.default_score                                                 │
│                                                                             │
│  2. KEYWORD MATCHING                                                        │
│     for keyword, weight in P.weights.keywords:                              │
│         if keyword.lower() in prompt.lower():                               │
│             score += weight                                                 │
│                                                                             │
│  3. DOMAIN MATCHING                                                         │
│     if M.domain in P.weights.domain:                                        │
│         score += P.weights.domain[M.domain]                                 │
│                                                                             │
│  4. COMPLEXITY MATCHING                                                     │
│     if M.complexity in P.weights.complexity:                                │
│         score += P.weights.complexity[M.complexity]                         │
│                                                                             │
│  5. PRIORITY BOOST                                                          │
│     if P.weights.priority:                                                  │
│         score += P.weights.priority.get(M.priority, 0)                      │
│                                                                             │
│  6. REQUIRED TAGS CHECK                                                     │
│     if P.required.context_tags:                                             │
│         matched = sum(1 for tag in P.required.context_tags                  │
│                       if tag in M.topics)                                   │
│         if matched == 0:                                                    │
│             score = 0  # Vyřazení profilu                                   │
│                                                                             │
│  7. SELECTION                                                               │
│     selected_profile = max(profiles, key=lambda p: p.score)                 │
│                                                                             │
│  8. CONSISTENCY CALCULATION                                                 │
│     consistency = (selected.score / sum(all_scores)) * 100                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Příklad výpočtu

```
Prompt: "Debug my Python script that throws KeyError"

Profily a skóre:
┌─────────────────────────┬───────┬────────────────────────────────────────┐
│ Profil                  │ Skóre │ Výpočet                                │
├─────────────────────────┼───────┼────────────────────────────────────────┤
│ technical_support       │  24   │ base(1) + debug(5) + python(3) +       │
│                         │       │ error(4) + engineering(4) + simple(3)  │
│                         │       │ + priority(4)                          │
├─────────────────────────┼───────┼────────────────────────────────────────┤
│ python_code_generation  │  12   │ base(2) + python(5) + script(2) +      │
│                         │       │ engineering(3)                         │
├─────────────────────────┼───────┼────────────────────────────────────────┤
│ general_default         │   5   │ base(5) - fallback profile             │
├─────────────────────────┼───────┼────────────────────────────────────────┤
│ creative_brainstorm     │   0   │ base(1) - no keyword matches           │
└─────────────────────────┴───────┴────────────────────────────────────────┘

Výsledek: technical_support (score: 24, consistency: 58.5%)
```

---

## Systém profilů

### Formát profilu (Markdown + YAML)

```markdown
---
name: technical_support
description: Profil pro technickou podporu a debugging
version: 1.0.0
domains:
  - engineering
  - debugging
  - troubleshooting
capabilities:
  - diagnostics
  - problem_solving
  - code_review
complexity: simple
keywords:
  debug: 5
  error: 4
  fix: 3
  issue: 2
  bug: 4
  crash: 3
  exception: 3
required_context_tags:
  - debugging
  - troubleshooting
priority:
  high: 3
  critical: 4
---

# Technical Support Profile

You are a technical support specialist focused on debugging and troubleshooting...

## Guidelines

1. First, identify the error type
2. Ask for relevant context (logs, stack trace)
3. Propose systematic debugging steps
4. Provide clear solutions with explanations

## Checklist

- [ ] Identifikovat typ chyby
- [ ] Reprodukovat problém
- [ ] Najít root cause
- [ ] Navrhnout řešení
- [ ] Ověřit opravu
```

### Dostupné profily (výběr)

| Kategorie | Profily |
|-----------|---------|
| **Technical** | technical_support, python_code_generation, refactoring_specialist |
| **Creative** | creative_brainstorm, decision_support_analyst |
| **Documentation** | documentation_4level, documentation_api_first, documentation_diataxis |
| **Security** | privacy_sensitive, security_compliance_reviewer |
| **ML/AI** | ml_pragmatist, model_evaluation_expert, llm_behavior_debugger |
| **DevOps** | devops_mlops_engineer, podman_container_management |
| **Testing** | python_testing_revision, mcp_server_testing_and_validation |

### Vytvoření nového profilu

1. Zkopírovat šablonu: `copilot-profiles/template/PROFILE_TEMPLATE.md`
2. Vyplnit YAML frontmatter
3. Napsat instrukce a checklist
4. Zavolat `reload_profiles` tool

---

## Konfigurace

### Environment variables

| Proměnná | Default | Popis |
|----------|---------|-------|
| `MCP_PROFILES_DIR` | `./copilot-profiles` | Adresář s profily |
| `MCP_LOG_LEVEL` | `INFO` | Úroveň logování |
| `PYTHONPATH` | - | Cesta k src/ |

### CLI argumenty

```bash
python -m mcp_prompt_broker [OPTIONS]

Options:
  --profiles-dir PATH   Adresář s profily
  --log-level LEVEL     Úroveň logování (DEBUG, INFO, WARNING, ERROR)
  --help                Nápověda
```

### VS Code MCP konfigurace

```json
{
  "mcpServers": {
    "mcp-prompt-broker": {
      "command": "python",
      "args": [
        "-m", 
        "mcp_prompt_broker",
        "--profiles-dir", 
        "./src/mcp_prompt_broker/copilot-profiles"
      ],
      "env": {
        "PYTHONPATH": "${workspaceFolder}/src",
        "MCP_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

---

## Testování

### Struktura testů

```
tests/
├── test_profile_router.py      # Testy routing engine
├── test_profile_parser.py      # Testy profile parseru
├── test_metadata_parser.py     # Testy metadata extrakce
├── test_mcp_server_validation.py # Validace MCP serveru
└── test_testing_profile_routing.py # End-to-end routing testy
```

### Spuštění testů

```bash
# Všechny testy
pytest tests/ -v

# Konkrétní modul
pytest tests/test_profile_router.py -v

# S coverage
pytest tests/ --cov=mcp_prompt_broker --cov-report=term-missing
```

### Příklad testu

```python
# tests/test_profile_router.py
import pytest
from mcp_prompt_broker.router.profile_router import ProfileRouter

@pytest.fixture
def router():
    profiles = load_test_profiles()
    return ProfileRouter(profiles)

def test_technical_prompt_routing(router):
    result = router.route(
        prompt="Debug my Python script with KeyError",
        metadata=create_test_metadata(domain="engineering")
    )
    
    assert result.profile.name == "technical_support"
    assert result.routing.score > 20
    assert result.routing.consistency > 50.0
```

---

## Rozšíření

### Přidání nového MCP tool

```python
# server.py
@server.list_tools()
async def list_tools() -> List[types.Tool]:
    return [
        # ... existing tools
        types.Tool(
            name="my_new_tool",
            description="Description of my new tool",
            inputSchema={
                "type": "object",
                "properties": {
                    "param1": {"type": "string"}
                },
                "required": ["param1"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "my_new_tool":
        result = await my_new_tool_handler(arguments["param1"])
        return [types.TextContent(type="text", text=json.dumps(result))]
```

### Vlastní metadata extractor

```python
# metadata/custom_parser.py
from .parser import ParsedMetadata

def extract_custom_metadata(prompt: str) -> dict:
    """Vlastní extrakce metadata."""
    custom_data = {}
    
    # Vlastní logika
    if "urgent" in prompt.lower():
        custom_data["priority"] = "high"
    
    return custom_data
```

---

## Známé limitace

| Limitace | Popis | Workaround |
|----------|-------|------------|
| Keyword-based routing | Závisí na přesných keywords | Přidat více synonym |
| No ML ranking | Statický scoring | Plánováno pro v2.0 |
| Single language | Pouze Python | N/A |
| File-based profiles | Není databáze | Hot-reload kompenzuje |

---

## Související dokumenty

- **Architektura:** [../architecture/ARCHITECTURE.md](../architecture/ARCHITECTURE.md)
- **API Reference:** [../api/MCP_TOOLS.md](../api/MCP_TOOLS.md)
- **User Guide:** [../USER_GUIDE.md](../USER_GUIDE.md)
- **Developer Guide:** [../DEVELOPER_GUIDE.md](../DEVELOPER_GUIDE.md)

---

*Tato dokumentace je součástí 4-úrovňové dokumentační struktury projektu MCP Prompt Broker.*
