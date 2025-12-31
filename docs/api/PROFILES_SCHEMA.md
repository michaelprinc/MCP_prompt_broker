# Profile Schema - API Reference

> **Verze dokumentace:** 1.0.0  
> **Datum:** 31. prosince 2025  
> **Úroveň:** 4/4 - API Reference

---

## 📋 Obsah

1. [Přehled formátu](#přehled-formátu)
2. [YAML Frontmatter schema](#yaml-frontmatter-schema)
3. [Markdown body schema](#markdown-body-schema)
4. [Validace](#validace)
5. [Příklady](#příklady)

---

## Přehled formátu

Profily jsou Markdown soubory s YAML frontmatter, které definují instrukce a metadata pro routing.

### Struktura souboru

```markdown
---
# YAML Frontmatter (metadata)
name: profile_name
description: Profile description
...
---

# Markdown Body (instructions)

## Section 1
Instructions...

## Checklist
- [ ] Item 1
- [ ] Item 2
```

### Umístění

```
src/mcp_prompt_broker/copilot-profiles/
├── profiles_metadata.json    # Centrální registry
├── template/
│   └── PROFILE_TEMPLATE.md   # Šablona
├── technical_support.md
├── creative_brainstorm.md
└── ...
```

---

## YAML Frontmatter Schema

### Kompletní schema

```yaml
# Povinné pole
name: string                    # Unikátní identifikátor profilu
description: string             # Stručný popis (1-2 věty)

# Volitelná pole
version: string                 # Sémantická verze (default: "1.0.0")
complexity: string              # "simple" | "complex" (default: "simple")

# Klasifikace
domains: list[string]           # Seznam domén
capabilities: list[string]      # Seznam schopností

# Scoring weights
keywords: dict[string, int]     # Klíčová slova a jejich váhy
priority: dict[string, int]     # Priority boost
domain_weights: dict[string, int]  # Domain-specific weights
complexity_weights: dict[string, int]  # Complexity weights

# Requirements
required_context_tags: list[string]  # Povinné tagy pro aktivaci

# Routing behavior
default_score: int              # Základní skóre (default: 1)
fallback: bool                  # Je fallback profil? (default: false)
```

### Detailní popis polí

#### name (povinné)

```yaml
name: technical_support
```

- **Typ:** string
- **Pattern:** `^[a-z][a-z0-9_]*$`
- **Délka:** 3-50 znaků
- **Popis:** Unikátní identifikátor profilu, používá se v API

#### description (povinné)

```yaml
description: Profil pro technickou podporu a debugging problémů
```

- **Typ:** string
- **Délka:** 10-200 znaků
- **Popis:** Stručný popis účelu profilu

#### version (volitelné)

```yaml
version: "1.2.0"
```

- **Typ:** string
- **Pattern:** Semantic versioning (`MAJOR.MINOR.PATCH`)
- **Default:** "1.0.0"

#### complexity (volitelné)

```yaml
complexity: simple
```

- **Typ:** enum
- **Hodnoty:** `simple`, `complex`
- **Default:** `simple`
- **Popis:** 
  - `simple`: Jednodušší úlohy, stručnější instrukce
  - `complex`: Komplexní úlohy, detailní plánování

#### domains (volitelné)

```yaml
domains:
  - engineering
  - debugging
  - python
```

- **Typ:** list[string]
- **Příklady:** `engineering`, `healthcare`, `finance`, `creative`, `security`, `devops`, `ml`
- **Popis:** Domény, pro které je profil relevantní

#### capabilities (volitelné)

```yaml
capabilities:
  - troubleshooting
  - diagnostics
  - code_review
```

- **Typ:** list[string]
- **Příklady:** `debugging`, `ideation`, `compliance`, `optimization`, `testing`, `documentation`
- **Popis:** Schopnosti, které profil poskytuje

#### keywords (volitelné)

```yaml
keywords:
  debug: 5
  error: 4
  fix: 3
  issue: 2
  bug: 4
  crash: 3
```

- **Typ:** dict[string, int]
- **Váhy:** 1-20 (doporučeno 1-10)
- **Popis:** Klíčová slova a jejich váhy pro scoring

#### priority (volitelné)

```yaml
priority:
  high: 3
  critical: 4
  urgent: 5
```

- **Typ:** dict[string, int]
- **Popis:** Boost skóre podle priority úlohy

#### domain_weights (volitelné)

```yaml
domain_weights:
  engineering: 4
  python: 3
  backend: 2
```

- **Typ:** dict[string, int]
- **Popis:** Váhy pro shodu s detekovanou doménou

#### complexity_weights (volitelné)

```yaml
complexity_weights:
  simple: 2
  complex: 0
```

- **Typ:** dict[string, int]
- **Popis:** Váhy podle komplexity úlohy

#### required_context_tags (volitelné)

```yaml
required_context_tags:
  - debugging
  - error_handling
```

- **Typ:** list[string]
- **Popis:** Pokud je definováno, profil se aktivuje pouze když alespoň jeden tag odpovídá

#### default_score (volitelné)

```yaml
default_score: 1
```

- **Typ:** int
- **Range:** 0-10
- **Default:** 1
- **Popis:** Základní skóre před aplikací vah

#### fallback (volitelné)

```yaml
fallback: true
```

- **Typ:** bool
- **Default:** false
- **Popis:** Označuje fallback profil (použit když nic jiného nesedí)

---

## Markdown Body Schema

### Sekce instrukcí

```markdown
# Profile Title

You are a [role] specialized in [domain]...

## Guidelines

1. First guideline
2. Second guideline
3. Third guideline

## Best Practices

- Practice 1
- Practice 2

## Examples

### Example 1: [Scenario]

```python
# Example code
```

## Checklist

- [ ] Step 1
- [ ] Step 2
- [ ] Step 3
```

### Checklist formát

```markdown
## Checklist

- [ ] Identifikovat problém
- [ ] Analyzovat kontext
- [ ] Navrhnout řešení
- [ ] Implementovat opravu
- [ ] Ověřit funkčnost
```

- **Pattern:** `- [ ] <item text>`
- **Parsování:** Automatické extrahování pomocí `get_checklist` tool

### Doporučená struktura

1. **Úvodní instrukce** - Role a kontext
2. **Guidelines** - Hlavní pravidla
3. **Best Practices** - Doporučené postupy
4. **Examples** - Příklady použití (volitelné)
5. **Checklist** - Kroky k dokončení úlohy

---

## Validace

### JSON Schema pro YAML frontmatter

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Profile Frontmatter Schema",
  "type": "object",
  "required": ["name", "description"],
  "properties": {
    "name": {
      "type": "string",
      "pattern": "^[a-z][a-z0-9_]*$",
      "minLength": 3,
      "maxLength": 50
    },
    "description": {
      "type": "string",
      "minLength": 10,
      "maxLength": 200
    },
    "version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+$",
      "default": "1.0.0"
    },
    "complexity": {
      "type": "string",
      "enum": ["simple", "complex"],
      "default": "simple"
    },
    "domains": {
      "type": "array",
      "items": { "type": "string" },
      "uniqueItems": true
    },
    "capabilities": {
      "type": "array",
      "items": { "type": "string" },
      "uniqueItems": true
    },
    "keywords": {
      "type": "object",
      "additionalProperties": {
        "type": "integer",
        "minimum": 1,
        "maximum": 20
      }
    },
    "priority": {
      "type": "object",
      "additionalProperties": {
        "type": "integer",
        "minimum": 1,
        "maximum": 10
      }
    },
    "required_context_tags": {
      "type": "array",
      "items": { "type": "string" }
    },
    "default_score": {
      "type": "integer",
      "minimum": 0,
      "maximum": 10,
      "default": 1
    },
    "fallback": {
      "type": "boolean",
      "default": false
    }
  }
}
```

### Validační pravidla

| Pravidlo | Popis | Chyba |
|----------|-------|-------|
| Unique name | Název musí být unikátní | `DuplicateProfileName` |
| Valid YAML | YAML musí být validní | `YAMLParseError` |
| Required fields | `name` a `description` povinné | `MissingRequiredField` |
| Valid keywords | Váhy musí být int 1-20 | `InvalidKeywordWeight` |
| Markdown body | Musí obsahovat instrukce | `EmptyInstructions` |

### Validační příkaz

```python
# Python validace
from mcp_prompt_broker.profile_parser import validate_profile

result = validate_profile("path/to/profile.md")
if result.valid:
    print("Profile is valid")
else:
    print(f"Errors: {result.errors}")
```

---

## Příklady

### Minimální profil

```markdown
---
name: minimal_example
description: Minimální příklad profilu
---

# Minimal Example

You are a helpful assistant.
```

### Standardní profil

```markdown
---
name: technical_support
description: Profil pro technickou podporu a debugging
version: "1.0.0"
complexity: simple
domains:
  - engineering
  - debugging
capabilities:
  - troubleshooting
  - diagnostics
keywords:
  debug: 5
  error: 4
  fix: 3
  bug: 4
default_score: 1
---

# Technical Support Profile

You are a technical support specialist focused on debugging and troubleshooting.

## Guidelines

1. First, identify the error type and context
2. Ask for relevant information (logs, stack traces)
3. Propose systematic debugging steps
4. Provide clear solutions with explanations

## Best Practices

- Always reproduce the issue first
- Check logs before making assumptions
- Provide step-by-step solutions

## Checklist

- [ ] Identifikovat typ chyby
- [ ] Reprodukovat problém
- [ ] Najít root cause
- [ ] Navrhnout řešení
- [ ] Ověřit opravu
```

### Komplexní profil

```markdown
---
name: python_code_generation_complex_with_codex
description: Komplexní Python development s Codex orchestrací
version: "1.1.0"
complexity: complex
domains:
  - engineering
  - python
  - backend
  - architecture
  - data_science
  - machine_learning
capabilities:
  - code_generation
  - architecture_design
  - ml_modeling
keywords:
  advanced python: 3
  python architecture: 3
  optimize python: 2
  codex orchestrator: 18
  mcp codex: 15
  machine learning: 6
  sklearn: 6
  classification: 5
priority:
  high: 3
  critical: 4
required_context_tags:
  - codex_cli
  - codex_orchestrator
  - ml_modeling
default_score: 2
fallback: false
---

# Python Code Generation with Codex Orchestration

You are an **orchestrator and auditor** for Codex via the MCP `codex-orchestrator` server.

## Core Workflow

1. **Requirement Analysis**: Break down the request into functional and non-functional requirements
2. **Architecture Design**: Choose appropriate patterns, modules, and dependencies
3. **Task Decomposition**: Split into atomic tasks suitable for MCP `codex_run` tool
4. **Execution**: Invoke `mcp_codex-orchest_codex_run` with precise prompts
5. **Verification**: Audit outputs, run tests, iterate as needed

## When to Use

This profile is ideal for:
- Complex Python projects requiring architecture decisions
- Machine learning and data science tasks (sklearn, pandas, numpy)
- Enterprise-grade code with proper patterns
- Projects where MCP `codex-orchestrator` can automate implementation

## Checklist

- [ ] Analyze requirements and constraints
- [ ] Design architecture and select patterns
- [ ] Decompose into Codex-suitable tasks
- [ ] Execute via codex_run MCP tool
- [ ] Review and audit generated code
- [ ] Run tests and validate functionality
- [ ] Document changes and decisions
```

### Fallback profil

```markdown
---
name: general_default
description: Výchozí profil pro obecné dotazy
version: "1.0.0"
complexity: simple
default_score: 5
fallback: true
---

# General Default Profile

You are a helpful, knowledgeable assistant.

## Guidelines

1. Provide accurate and helpful information
2. Be clear and concise in your responses
3. Ask for clarification when needed
4. Offer relevant examples when helpful

## Checklist

- [ ] Understand the user's question
- [ ] Provide accurate response
- [ ] Suggest follow-up if relevant
```

---

## Central Metadata Registry

### profiles_metadata.json

```json
{
  "version": "1.0.0",
  "generated_at": "2025-12-31T10:00:00Z",
  "profiles": {
    "technical_support": {
      "name": "technical_support",
      "description": "Profil pro technickou podporu",
      "version": "1.0.0",
      "complexity": "simple",
      "domains": ["engineering", "debugging"],
      "capabilities": ["troubleshooting", "diagnostics"],
      "file_path": "copilot-profiles/technical_support.md",
      "checksum": "sha256:abc123..."
    }
  },
  "statistics": {
    "total_profiles": 45,
    "by_complexity": {
      "simple": 28,
      "complex": 17
    },
    "domains_covered": 12,
    "capabilities_covered": 18
  }
}
```

---

## Vytvoření nového profilu

### Postup

1. **Zkopírujte šablonu:**
   ```bash
   cp copilot-profiles/template/PROFILE_TEMPLATE.md copilot-profiles/my_new_profile.md
   ```

2. **Vyplňte frontmatter:**
   - Nastavte unikátní `name`
   - Napište `description`
   - Přidejte relevantní `domains` a `capabilities`
   - Nastavte `keywords` s vhodným váhami

3. **Napište instrukce:**
   - Definujte roli a kontext
   - Přidejte guidelines a best practices
   - Vytvořte checklist

4. **Reload profily:**
   ```json
   { "tool": "reload_profiles", "arguments": {} }
   ```

5. **Otestujte routing:**
   ```json
   { "tool": "resolve_prompt", "arguments": { "prompt": "test query" } }
   ```

---

## Související dokumenty

- **MCP Tools:** [MCP_TOOLS.md](MCP_TOOLS.md)
- **CLI Reference:** [CLI_REFERENCE.md](CLI_REFERENCE.md)
- **MCP Prompt Broker:** [../modules/MCP_PROMPT_BROKER.md](../modules/MCP_PROMPT_BROKER.md)

---

*Tato dokumentace je součástí 4-úrovňové dokumentační struktury projektu MCP Prompt Broker.*
