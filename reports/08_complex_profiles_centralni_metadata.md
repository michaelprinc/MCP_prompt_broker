# Implementační report: Komplexní profily a centrální metadata registr

**Datum:** 2025-12-06  
**Autor:** GitHub Copilot

---

## Cíl

1. Vytvořit rozšířené komplexní profily (`*_complex.md`) pro zlepšení kvality agentních LLM
2. Implementovat centrální metadata registr s dynamickým parsováním
3. Hot reload automaticky aktualizuje centrální `profiles_metadata.json`
4. MCP tooly čtou metadata z centrálního souboru

---

## Architektura

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           MCP Server                                    │
│                                                                         │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐  │
│  │list_profiles│  │ get_profile  │  │reload_profiles│  │get_checklist│  │
│  └──────┬──────┘  └──────┬───────┘  └──────┬───────┘  └──────┬──────┘  │
│         │                │                 │                  │         │
│         └────────────────┴─────────┬───────┴──────────────────┘         │
│                                    │                                    │
│                         ┌──────────▼──────────┐                         │
│                         │  MetadataRegistry   │◄─── Čte/Zapisuje        │
│                         │  (metadata_registry.py)                       │
│                         └──────────┬──────────┘                         │
│                                    │                                    │
│                    ┌───────────────┼───────────────┐                    │
│                    │               │               │                    │
│             ┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐             │
│             │ProfileLoader│ │ JSON Export │ │Dynamic Parse│             │
│             └──────┬──────┘ └──────┬──────┘ └──────┬──────┘             │
│                    │               │               │                    │
│                    │      ┌────────▼────────┐      │                    │
│                    │      │profiles_metadata│      │                    │
│                    │      │     .json       │      │                    │
│                    │      └─────────────────┘      │                    │
│                    │                               │                    │
│     ┌──────────────┴───────────────────────────────┴───────────────┐    │
│     │                   copilot-profiles/                          │    │
│     │  ┌──────────────┐ ┌──────────────┐ ┌───────────────────────┐ │    │
│     │  │creative_     │ │privacy_      │ │technical_             │ │    │
│     │  │brainstorm.md │ │sensitive.md  │ │support.md             │ │    │
│     │  └──────────────┘ └──────────────┘ └───────────────────────┘ │    │
│     │  ┌──────────────┐ ┌──────────────┐ ┌───────────────────────┐ │    │
│     │  │creative_     │ │privacy_      │ │technical_             │ │    │
│     │  │brainstorm_   │ │sensitive_    │ │support_               │ │    │
│     │  │complex.md    │ │complex.md    │ │complex.md             │ │    │
│     │  └──────────────┘ └──────────────┘ └───────────────────────┘ │    │
│     │  ┌──────────────┐                                            │    │
│     │  │general_      │                                            │    │
│     │  │default_      │                                            │    │
│     │  │complex.md    │                                            │    │
│     │  └──────────────┘                                            │    │
│     └──────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Checklist implementace

### Fáze 1: Komplexní profily
- [ ] `creative_brainstorm_complex.md` - Chain-of-thought, self-reflection, meta-cognition
- [ ] `general_default_complex.md` - Adaptivní reasoning, multi-step verification
- [ ] `privacy_sensitive_complex.md` - Zero-trust, adversarial awareness, compliance matrix
- [ ] `technical_support_complex.md` - Root cause analysis framework, escalation patterns

### Fáze 2: Centrální metadata registr
- [ ] `metadata_registry.py` - MetadataRegistry třída
- [ ] `profiles_metadata.json` - Centrální metadata soubor
- [ ] Dynamické parsování metadat z markdown profilů

### Fáze 3: Aktualizace existujícího kódu
- [ ] Aktualizovat `profile_parser.py` - export do JSON
- [ ] Aktualizovat `server.py` - čtení z centrálního souboru
- [ ] Hot reload zapisuje do `profiles_metadata.json`

### Fáze 4: Verifikace
- [ ] Spustit existující testy
- [ ] Ověřit parsování nových profilů
- [ ] Ověřit MCP tooly

---

## Struktura profiles_metadata.json

```json
{
  "version": "1.0",
  "generated_at": "2025-12-06T10:00:00Z",
  "profiles": {
    "creative_brainstorm": {
      "name": "creative_brainstorm",
      "short_description": "Encourage creative exploration...",
      "source_file": "creative_brainstorm.md",
      "default_score": 3,
      "fallback": false,
      "complexity": "standard",
      "required": {...},
      "weights": {...},
      "capabilities": ["ideation", "divergent_thinking"],
      "checklist_count": 8,
      "last_modified": "2025-12-06T10:00:00Z"
    },
    "creative_brainstorm_complex": {
      "name": "creative_brainstorm_complex",
      "short_description": "Advanced creative with meta-cognition...",
      "complexity": "complex",
      "extends": "creative_brainstorm",
      ...
    }
  },
  "statistics": {
    "total_profiles": 8,
    "complex_profiles": 4,
    "standard_profiles": 4,
    "fallback_profile": "general_default"
  }
}
```

---

## Komplexní profily - Principy návrhu

### 1. Chain-of-Thought (CoT)
Explicitní krokové myšlení pro zlepšení reasoning.

### 2. Self-Reflection
Profily instruují model k sebehodnocení a iterativnímu zlepšování.

### 3. Meta-Cognition
Uvědomění si vlastních omezení a kognitivních biasů.

### 4. Adversarial Awareness
Anticipace edge cases a potenciálních problémů.

### 5. Structured Output Patterns
Konzistentní formáty výstupu pro lepší parsovatelnost.

---

## Dynamické parsování metadat

Metadata budou automaticky odvozena z:

1. **YAML frontmatter** - explicitní metadata
2. **Markdown struktura** - sekce `## Instructions`, `## Checklist`
3. **Obsah instrukcí** - inference capabilities z klíčových slov
4. **Filename pattern** - `*_complex.md` → `complexity: complex`

---

## Závěr

Implementace přináší:
- Výrazně kvalitnější agentní chování díky komplexním profilům
- Centralizovanou správu metadat pro snadnou integraci
- Hot reload s automatickým exportem do JSON
- Škálovatelnou architekturu pro budoucí rozšíření
