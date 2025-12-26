# Report: Migrace Codex CLI profilů na MCP codex-orchestrator

**Datum:** 2024-12-26  
**Autor:** GitHub Copilot  
**Verze:** 1.0

---

## Přehled

Tento report dokumentuje migraci profilů v adresáři `src/mcp_prompt_broker/copilot-profiles/`, které doporučovaly přímé použití Codex CLI, na nový MCP server `codex-orchestrator`. Migrace přináší bezpečnější, lépe strukturovanou a auditovatelnou integraci s OpenAI Codex.

## Cíl migrace

| Aspekt | Před migrací | Po migraci |
|--------|--------------|------------|
| **Způsob volání** | Přímé CLI přes `subprocess` | MCP tool `codex_run` |
| **Izolace** | Žádná nebo manuální sandbox | Docker kontejner |
| **Timeout** | Manuální implementace (30s) | Konfigurovatelný (default 300s) |
| **Výstup** | Nestrukturovaný text | `CodexRunResult` s metadaty |
| **Audit trail** | Žádný | `run_id` pro sledování |

---

## Upravené soubory

### 1. `codex_cli.md`

**Umístění:** `src/mcp_prompt_broker/copilot-profiles/codex_cli.md`

#### Změny ve frontmatter:

```yaml
# PŘED
short_description: Integration profile for safe Codex CLI invocation...
required:
  context_tags: ["codex_cli", "cli_integration"]
keywords:
  cli integration: 6
  subprocess: 4

# PO
short_description: Integration profile for Codex via MCP codex-orchestrator server...
required:
  context_tags: ["codex_cli", "mcp_integration", "codex_orchestrator"]
keywords:
  codex orchestrator: 15
  mcp server: 8
  docker isolation: 6
```

#### Změny v obsahu:

| Sekce | Změna |
|-------|-------|
| **Název** | `Codex CLI Integration Profile` → `Codex MCP Orchestrator Integration Profile` |
| **Core Principles** | Přidána Docker izolace, MCP protokol, audit trail |
| **Integration Flow** | `subprocess.run()` → `mcp_codex-orchest_codex_run` |
| **Example Usage** | Python subprocess kód → JSON MCP tool invokace |
| **Checklist** | Aktualizován na MCP-specifické body |
| **Response Structure** | Přidána dokumentace `CodexRunResult` |

---

### 2. `python_code_generation_complex_with_codex.md`

**Umístění:** `src/mcp_prompt_broker/copilot-profiles/python_code_generation_complex_with_codex.md`

#### Změny ve frontmatter:

```yaml
# PŘED
short_description: ...use Codex CLI
required:
  context_tags: ["codex_cli", "ml_modeling"]

# PO
short_description: ...using MCP codex-orchestrator
required:
  context_tags: ["codex_cli", "ml_modeling", "codex_orchestrator"]
keywords:
  codex orchestrator: 18
  mcp codex: 15
```

#### Změny v obsahu:

| Sekce | Změna |
|-------|-------|
| **Název frameworku** | `Codex CLI Orchestration Framework` → `MCP Codex-Orchestrator Framework` |
| **Primary Role** | Delegace přes terminal → Delegace přes MCP tool |
| **Core Workflow** | Codex CLI commands → MCP `codex_run` invokace |
| **Všechny příklady** | Bash `codex "..."` → JSON `{"prompt": "...", "mode": "..."}` |
| **Preferred tool** | `Codex CLI` → `MCP codex-orchestrator` |
| **Progress reports** | `Codex CLI is working...` → `MCP codex-orchestrator is working...` |
| **Motto** | Terminal → Docker isolation via MCP |

#### Aktualizované příklady (ukázka):

**Před:**
```bash
codex "
Create file: src/models.py
Implement data models...
"
```

**Po:**
```json
{
  "prompt": "Create file: src/models.py\n\nImplement data models...",
  "mode": "full-auto",
  "timeout": 180
}
```

---

## Nová šablona

### `template/codex_orchestrator_integration.md`

**Umístění:** `src/mcp_prompt_broker/copilot-profiles/template/codex_orchestrator_integration.md`

Vytvořena nová šablona pro budoucí profily integrující MCP `codex-orchestrator`.

#### Obsah šablony:

1. **Frontmatter template** - Ukázka YAML konfigurace s MCP tagy
2. **MCP Tool Reference** - Kompletní dokumentace `codex_run` schématu
3. **Integration Patterns** - 4 vzory použití:
   - Basic Invocation
   - With Working Directory
   - With Environment Variables
   - Suggest Mode (Review Only)
4. **Response Handling** - Dokumentace stavů a error handlingu
5. **Workflow Template** - 4-krokový postup (Analyze → Prompt → Invoke → Report)
6. **Security Guidelines** - 5 bezpečnostních pravidel
7. **Customization Points** - Návod na vytvoření vlastního profilu
8. **Example** - Kompletní příklad vlastního profilu

---

## Výhody migrace

### Bezpečnost

| Feature | Popis |
|---------|-------|
| **Docker izolace** | Každý run v separátním kontejneru |
| **Bez přístupu k hostu** | Kód nemůže ovlivnit hostitelský systém |
| **Strukturované timeout** | Prevence nekonečných běhů |

### Strukturovanost

| Feature | Popis |
|---------|-------|
| **`run_id`** | Unikátní identifikátor pro audit trail |
| **`status`** | Jasný stav: `success`, `error`, `timeout` |
| **`files_changed`** | Seznam modifikovaných souborů |
| **`duration_seconds`** | Metrika pro optimalizaci |

### Údržba

| Feature | Popis |
|---------|-------|
| **Centralizovaná konfigurace** | MCP server settings |
| **Konzistentní interface** | Stejný JSON formát pro všechny profily |
| **Verzování** | MCP server lze verzovat nezávisle |

---

## Zpětná kompatibilita

Migrace je zpětně kompatibilní:

- **Keywords zachovány**: `codex cli`, `Codex CLI`, `codex` stále fungují pro routing
- **Profile names zachovány**: `codex_cli` a `python_code_generation_complex_with_codex`
- **Extends chain**: Profil stále extenduje `python_code_generation_complex`

---

## Doporučení pro další vývoj

1. **Aktualizovat `profiles_metadata.json`**
   - Přidat nové context_tags
   - Regenerovat metadata

2. **Přidat testy**
   - Unit testy pro nové MCP invokace
   - Integration testy s mock MCP serverem

3. **Dokumentace**
   - Aktualizovat USER_GUIDE.md
   - Přidat příklady do DEVELOPER_GUIDE.md

4. **Monitoring**
   - Sledovat `run_id` pro debugging
   - Logovat `duration_seconds` pro optimalizaci

---

## Soubory změněné touto migrací

```
src/mcp_prompt_broker/copilot-profiles/
├── codex_cli.md                                    [MODIFIED]
├── python_code_generation_complex_with_codex.md    [MODIFIED]
└── template/
    ├── python_code_generation_complex.md           [UNCHANGED]
    └── codex_orchestrator_integration.md           [NEW]
```

---

## Závěr

Migrace byla úspěšně dokončena. Oba profily nyní používají MCP `codex-orchestrator` server místo přímého volání Codex CLI. Nová šablona poskytuje základ pro budoucí profily s Codex integrací.

**Status:** ✅ DOKONČENO
