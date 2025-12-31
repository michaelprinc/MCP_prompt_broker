# Implementační report: Hot Reload profilů a nové MCP tooly

**Datum:** 2025-12-06  
**Autor:** GitHub Copilot

---

## Cíl

Implementovat "hot reload" funkčnost pro profily MCP serveru Prompt Broker s parsováním z markdown souborů a přidat nové MCP tooly.

## Provedené změny

### 1. Nový parser pro markdown profily

**Soubor:** `src/mcp_prompt_broker/profile_parser.py`

Vytvořen komplexní parser podporující:
- YAML frontmatter pro metadata (name, required, weights, default_score, fallback)
- Sekce `## Instructions` pro komplexní instrukce
- Sekce `## Checklist` pro kontrolní seznamy
- `ProfileLoader` třída pro správu načítání a hot-reload

### 2. Markdown profily

**Adresář:** `src/mcp_prompt_broker/copilot-profiles/`

Vytvořeny 4 profily:
- `privacy_sensitive.md` - GDPR, HIPAA, redakce citlivých dat
- `creative_brainstorm.md` - divergentní myšlení, SCAMPER, ideace
- `technical_support.md` - troubleshooting, root cause analysis
- `general_default.md` - fallback pro obecné dotazy

Každý profil obsahuje:
- Komplexní, tokenově efektivní instrukce
- Akční checklist pro ověření kvality odpovědi

### 3. Nové MCP tooly

| Tool | Popis |
|------|-------|
| `list_profiles` | Seznam dostupných profilů (přejmenováno z `list_profile`) |
| `get_profile` | Analýza promptu a výběr nejlepšího profilu |
| `reload_profiles` | Hot reload profilů z markdown souborů |
| `get_checklist` | Získání checklistu pro konkrétní profil |

### 4. Aktualizované závislosti

**pyproject.toml:** Přidána závislost `pyyaml>=6.0`

## Architektura

```
┌─────────────────────────────────────────────────────────────┐
│                     MCP Server                              │
│                                                             │
│  ┌─────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │list_profiles│    │reload_profiles│    │get_checklist │   │
│  └──────┬──────┘    └──────┬───────┘    └──────┬───────┘   │
│         │                  │                    │           │
│         └──────────────────┼────────────────────┘           │
│                            │                                │
│                    ┌───────▼───────┐                        │
│                    │ ProfileLoader │                        │
│                    └───────┬───────┘                        │
│                            │                                │
│              ┌─────────────┼─────────────┐                  │
│              │             │             │                  │
│       ┌──────▼──────┐ ┌────▼────┐ ┌─────▼──────┐           │
│       │privacy.md   │ │tech.md  │ │creative.md │           │
│       │[YAML+MD]    │ │[YAML+MD]│ │[YAML+MD]   │           │
│       └─────────────┘ └─────────┘ └────────────┘           │
│                                                             │
│                   copilot-profiles/                         │
└─────────────────────────────────────────────────────────────┘
```

## Formát markdown profilu

```markdown
---
name: profile_name
default_score: 5
fallback: false

required:
  domain:
    - engineering
    - it

weights:
  domain:
    engineering: 3
---

## Instructions

Komplexní instrukce pro LLM...

## Checklist

- [ ] Ověřit první podmínku
- [ ] Zkontrolovat druhý bod
```

## Testování

Spuštěno 28 testů:
- 10 původních testů (zachována zpětná kompatibilita)
- 18 nových testů pro profile_parser

Všechny testy prošly ✓

## Použití

### Spuštění serveru
```bash
mcp-prompt-broker
```

### S vlastním adresářem profilů
```bash
mcp-prompt-broker --profiles-dir /path/to/profiles
```

### Hot reload za běhu
Zavolat MCP tool `reload_profiles` - profily se znovu načtou bez restartu serveru.

## Rizika a mitigace

| Riziko | Mitigace |
|--------|----------|
| Nevalidní markdown soubor | Parser loguje chyby a pokračuje s ostatními |
| Chybějící YAML | Explicitní chybová hláška s cestou k souboru |
| Prázdný adresář profilů | Fallback na hardcoded general_default profil |

## Další kroky

1. Zvážit přidání file watcher pro automatický hot-reload
2. Přidat validaci schématu pro YAML frontmatter
3. Dokumentovat formát profilů v README.md
