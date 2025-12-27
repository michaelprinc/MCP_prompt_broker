# Report: Implementation Planner Profile

> Generated: 2025-12-27T14:45:32
> Author: GitHub Copilot
> Status: Complete

## Executive Summary

Vytvořeny dva nové profily pro MCP Prompt Broker server:
1. **`implementation_planner`** - Základní profil pro generování checklistů a implementačních plánů
2. **`implementation_planner_complex`** - Rozšířený profil pro komplexní, multi-modulové projekty

Oba profily dodržují standardy Spec Kit a jsou plně integrované do routing systému.

## Deliverables

### Nové soubory

| Soubor | Popis |
|--------|-------|
| `src/mcp_prompt_broker/copilot-profiles/implementation_planner.md` | Základní planning profil |
| `src/mcp_prompt_broker/copilot-profiles/implementation_planner_complex.md` | Komplexní planning profil |

### Funkcionalita profilů

#### implementation_planner

**Spouštěcí klíčová slova (CZ/EN):**
- implementační plán / implementation plan
- checklist / kontrolní seznam
- naplánuj / rozplánuj
- vytvoř plán / project plan
- roadmap, breakdown, milestones

**Výstupy:**
1. `docs/CHECKLIST.md` - Detailní úkolový checklist s acceptance criteria
2. `docs/IMPLEMENTATION_PLAN.md` - Kompletní implementační plán
3. Doporučený prompt pro implementaci

#### implementation_planner_complex

**Rozšířená funkcionalita:**
- Risk register a dependency mapping
- Phased rollout strategies
- Stakeholder communication plan
- Feature flag strategy
- Monitoring & alerting setup
- Rollback playbook

## Routing Tests

```
Prompt: "Vytvor implementacni plan a checklist pro novou REST API"
→ Selected: implementation_planner (score: 49)

Prompt: "Create an implementation plan with detailed checklist for user authentication"
→ Selected: implementation_planner (score: 61)

Prompt: "Naplanuj projekt a vytvor kontrolni seznam ukolu"
→ Selected: implementation_planner (score: 49)

Prompt: "Design complex multi-module architecture with migration plan"
→ Selected: implementation_planner_complex (score: 34)
```

## Použití profilu

### Aktivace profilu

Profil se automaticky aktivuje při detekci klíčových slov v promptu. Alternativně lze explicitně zavolat:

```python
# Via MCP tool
{
    "tool": "get_profile",
    "arguments": {
        "prompt": "Vytvoř implementační plán pro REST API s autentizací",
        "metadata": {
            "context_tags": ["implementation_planner"]
        }
    }
}
```

### Příklad výstupu

Po aktivaci profilu agent vygeneruje:

1. **CHECKLIST.md** se strukturou:
   - Phase 1: Setup & Prerequisites
   - Phase 2: Core Implementation
   - Phase 3: Testing & Validation
   - Phase 4: Documentation & Cleanup
   - Verification Checklist

2. **IMPLEMENTATION_PLAN.md** se strukturou:
   - Executive Summary
   - Current State Snapshot
   - Goal & Scope
   - Key Challenges & Risks
   - Architecture Overview (ASCII diagram)
   - Implementation Phases
   - Testing Strategy
   - Rollback Plan
   - Timeline & Milestones

3. **Doporučený prompt** pro zahájení implementace

## Spec Kit Compliance

Oba profily splňují standardy Spec Kit:

- ✅ YAML frontmatter s required fields (name, required, weights)
- ✅ `## Instructions` section
- ✅ `## Checklist` section
- ✅ Keywords v češtině i angličtině (s diakritikou i bez)
- ✅ Pre-flight analysis framework
- ✅ Complexity assessment criteria
- ✅ Terminal protocol integration
- ✅ Markdown best practices

## Test Results

```
======================== 32 passed, 1 warning in 1.05s ========================
```

Všechny existující testy prošly, nové profily nenarušují stávající funkcionalitu.

## Metadata Registry Update

Po reload:
- Total profiles: 19
- Dynamic topics added: 19
- Parser keywords updated automatically

## Next Steps

1. Přidat unit testy specifické pro implementation_planner profily
2. Případně vytvořit ukázkové výstupy CHECKLIST.md a IMPLEMENTATION_PLAN.md
3. Aktualizovat USER_GUIDE.md s dokumentací nových profilů

## Files Changed

```diff
+ src/mcp_prompt_broker/copilot-profiles/implementation_planner.md
+ src/mcp_prompt_broker/copilot-profiles/implementation_planner_complex.md
M src/mcp_prompt_broker/copilot-profiles/profiles_metadata.json (auto-updated)
```
