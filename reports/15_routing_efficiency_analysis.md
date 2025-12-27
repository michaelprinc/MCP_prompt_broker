# Analýza efektivity routingu instrukcí v MCP Prompt Broker

**Datum:** 2025-12-26  
**Autor:** GitHub Copilot  
**Verze:** 1.0

---

## Obsah

1. [Shrnutí problému](#shrnutí-problému)
2. [Implementované řešení](#implementované-řešení)
3. [Analýza příčin](#analýza-příčin)
4. [Další návrhy na zlepšení](#další-návrhy-na-zlepšení)
5. [Doporučené prioritizace](#doporučené-prioritizace)

---

## Shrnutí problému

### Pozorovaný problém

Jazykový model (LLM) často nepoužívá primární tool `get_profile` pro analýzu promptu při práci s MCP serverem `mcp-prompt-broker`. Místo toho volí jiné tooly, například `get_checklist`, což vede k suboptimálnímu routingu instrukcí.

### Důsledky

- Instrukce nejsou přizpůsobeny kontextu uživatelského požadavku
- LLM nezískává domain-specific guidance
- Snížená kvalita odpovědí v specifických doménách
- Nevyužití plného potenciálu systému profilů

---

## Implementované řešení

### 1. Přidání aliasu `resolve_prompt`

**Soubor:** `src/mcp_prompt_broker/server.py`

Byl přidán nový tool `resolve_prompt` jako alias pro `get_profile` s výraznějším a akčním popisem:

```python
types.Tool(
    name="resolve_prompt",
    description=(
        "PRIMARY TOOL: Always call this FIRST before processing any user request. "
        "Analyzes the user's prompt, detects domain/capability/complexity, "
        "and returns optimal instructions for handling the request. "
        "This is the main entry point for intelligent prompt routing."
    ),
    # ...
)
```

**Klíčové vylepšení popisu:**
- `PRIMARY TOOL` - jasná indikace priority
- `Always call this FIRST` - explicitní instrukce o pořadí
- `main entry point` - zdůraznění významu

### 2. Aktualizace agentních instrukcí

**Soubory:**
- `.github/agents/companion-agent.json`
- `.github/agents/companion-instructions.md`

Změny zahrnují:
- Nový primární tool `resolve_prompt` s aliasem `get_profile`
- Zdůraznění `priority: highest`
- Explicitní varování proti použití jiných toolů jako prvního kroku
- Verze zvýšena na 1.1.0

---

## Analýza příčin

### Proč LLM nepoužívá správný tool?

| Příčina | Vysvětlení | Závažnost |
|---------|------------|-----------|
| **Název toolu** | `get_profile` zní jako "získat metadata", ne jako "analyzovat prompt" | Vysoká |
| **Popis není dostatečně direktivní** | Chybí slova jako "FIRST", "PRIMARY", "ALWAYS" | Vysoká |
| **Konkurence s jinými tooly** | `get_checklist` může znít akčněji pro úkolové požadavky | Střední |
| **Nedostatek kontextu** | LLM neví, že routing je kritický první krok | Vysoká |
| **Sémantická nejednoznačnost** | "Profile" může znamenat různé věci | Střední |

### Jak LLM vybírá tooly?

1. **Sémantická shoda** - LLM porovnává uživatelský požadavek s názvy/popisy toolů
2. **Akční slovesa** - preferuje tooly s jasným akčním významem
3. **Specificita** - specifičtější tooly mohou být preferovány
4. **Pozice v seznamu** - může mít vliv na selekci

---

## Další návrhy na zlepšení

### Kategorie A: Vylepšení názvosloví (Vysoká priorita)

#### A1. Další aliasy pro různé mentální modely

```python
# Navrhované aliasy:
"analyze_request"      # Pro uživatele hledající analýzu
"route_prompt"         # Pro ty, kdo chápou routing
"get_instructions"     # Pro ty, kdo hledají instrukce
```

**Implementace:** Přidat do `server.py` jako další aliasy s handler podmínkou `if name in ("get_profile", "resolve_prompt", "analyze_request", ...)`.

#### A2. Prefix pro prioritní tooly

Zvážit prefix jako `@` nebo `!` pro primární tooly:
- `!resolve_prompt` 
- Může signalizovat prioritu v seznamu toolů

### Kategorie B: Vylepšení popisů toolů (Vysoká priorita)

#### B1. Negativní instrukce v popisech sekundárních toolů

Přidat do popisu `get_checklist`:
```python
description=(
    "Get the checklist for a specific instruction profile. "
    "NOTE: Call resolve_prompt FIRST to get the profile_name, "
    "then use this tool for the checklist."
)
```

#### B2. Sekvenční závislosti v popisech

Explicitně uvést závislosti v popisech:
```
get_checklist: "Requires profile_name from resolve_prompt"
get_profile_metadata: "Use after resolve_prompt for deeper analysis"
```

### Kategorie C: Architektonická vylepšení (Střední priorita)

#### C1. Sjednocený entry-point tool

Vytvořit jeden "super-tool" který kombinuje routing + checklist:

```python
types.Tool(
    name="process_request",
    description="Complete request processing: analyze → route → return instructions + checklist",
    inputSchema={
        "properties": {
            "prompt": {"type": "string"},
            "include_checklist": {"type": "boolean", "default": True}
        }
    }
)
```

**Výhody:**
- Jeden tool call místo dvou
- Nemožnost přeskočit routing
- Zjednodušený workflow

#### C2. Automatický routing přes system prompt

Místo explicitního tool call použít system prompt injection:

1. Agent před každou odpovědí automaticky routuje
2. Routing je "neviditelný" pro uživatele
3. Vždy se aplikují správné instrukce

**Nevýhody:**
- Složitější implementace
- Menší transparentnost
- Potenciální latence

### Kategorie D: Vylepšení dokumentace (Střední priorita)

#### D1. Vizuální workflow diagram

Přidat do instructions ASCII/mermaid diagram:

```
┌─────────────────────┐
│   User Request      │
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  resolve_prompt()   │  ◄─── VŽDY PRVNÍ
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  Apply Instructions │
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  Optional: checklist│
└─────────────────────┘
```

#### D2. Příklady anti-patterns

Dokumentovat, co NEDĚLAT:
```
❌ WRONG: get_checklist("technical_support") - bez předchozího routingu
✅ RIGHT: resolve_prompt("fix my bug") → get_checklist(profile_name)
```

### Kategorie E: Monitoring a zpětná vazba (Nízká priorita)

#### E1. Logování tool usage

Přidat metriky sledující:
- Který tool byl volán jako první
- Sekvence tool calls
- Případy přeskočení routingu

#### E2. Feedback loop

Implementovat mechanismus:
1. Detekce suboptimálního workflow
2. Varování nebo nápověda pro LLM
3. Statistiky pro vylepšení

### Kategorie F: MCP Protocol vylepšení (Nízká priorita - závisí na MCP spec)

#### F1. Tool priority metadata

Pokud MCP podpoří, přidat priority field:
```python
types.Tool(
    name="resolve_prompt",
    priority=1,  # Nejvyšší priorita
    # ...
)
```

#### F2. Tool categories/groups

Organizovat tooly do skupin:
- `primary`: resolve_prompt
- `secondary`: get_checklist, get_profile_metadata
- `discovery`: list_profiles, find_profiles_by_*
- `admin`: reload_profiles

---

## Doporučené prioritizace

### Okamžitě implementováno ✅

1. ✅ Alias `resolve_prompt` s výrazným popisem
2. ✅ Aktualizace agent instrukcí s důrazem na pořadí

### Doporučeno k implementaci (Vysoká priorita)

| # | Návrh | Effort | Impact |
|---|-------|--------|--------|
| 1 | B1 - Negativní instrukce v sekundárních toolech | Nízký | Vysoký |
| 2 | A1 - Další aliasy (analyze_request, route_prompt) | Nízký | Střední |
| 3 | D2 - Dokumentace anti-patterns | Nízký | Střední |

### Zvážit do budoucna (Střední priorita)

| # | Návrh | Effort | Impact |
|---|-------|--------|--------|
| 4 | C1 - Sjednocený entry-point tool | Střední | Vysoký |
| 5 | D1 - Vizuální workflow diagram | Nízký | Střední |
| 6 | E1 - Logování tool usage | Střední | Střední |

### Dlouhodobě (Nízká priorita)

| # | Návrh | Effort | Impact |
|---|-------|--------|--------|
| 7 | C2 - Automatický routing | Vysoký | Vysoký |
| 8 | F1/F2 - MCP protocol features | Závisí na spec | Vysoký |

---

## Závěr

Implementace aliasu `resolve_prompt` je správný první krok ke zlepšení efektivity routingu. Klíčové faktory úspěchu:

1. **Název je akčnější** - "resolve" implikuje řešení, "get" implikuje pasivní získání
2. **Popis je direktivnější** - obsahuje "PRIMARY", "FIRST", "ALWAYS"
3. **Instrukce jsou explicitnější** - jasně říkají, co nedělat

Pro maximální efektivitu doporučuji v následujících iteracích implementovat:
- Negativní instrukce v sekundárních toolech (B1)
- Další aliasy pro různé mentální modely (A1)
- Dokumentaci anti-patterns (D2)

Tyto změny společně vytvoří robustní systém, který minimalizuje šanci na přeskočení kritického routingového kroku.

---

## Změnový log

| Datum | Verze | Změny |
|-------|-------|-------|
| 2025-12-26 | 1.0 | Počáteční analýza a implementace aliasu |
