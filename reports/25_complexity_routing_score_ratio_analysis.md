# Report: Analýza routování komplexního profilu

> **Datum:** 2026-01-01  
> **Prompt:** "Vytvoř komplexní implementační plán pro úpravu adresářové struktury workspace v souladu s nejlepší praxí. Workspace obsahuje více modulů: mcp-prompt-broker, llama-orchestrator, mcp-codex-orchestrator a další."  
> **Očekávaný profil:** `implementation_planner_complex`  
> **Skutečný profil:** `implementation_planner`

---

## Executive Summary

Router **správně identifikoval** potřebu komplexního profilu (`_should_prefer_complex = True`), ale **nepřepnul** na variantu `implementation_planner_complex` kvůli **nedostatečnému skóre** komplexní varianty vůči minimálnímu požadovanému poměru.

---

## Root Cause

### Problém: Score Ratio Threshold

Router používá `COMPLEX_VARIANT_MIN_SCORE_RATIO = 0.8` jako minimální poměr skóre komplexní varianty vůči základnímu profilu.

| Profil | Keyword Score |
|--------|---------------|
| `implementation_planner` | **38** |
| `implementation_planner_complex` | **23** |

**Výpočet:**
```
Požadované minimum = 38 × 0.8 = 30.4
Skutečné skóre komplexní varianty = 23
23 < 30.4 → NEPŘEPNUTO
```

### Proč má komplexní varianta nižší skóre?

Keyword matching z promptu:

**Prompt obsahuje tyto klíčová slova:**
- `komplexní` / `komplexni` → matchuje oba profily
- `implementační plán` / `implementacni plan` → matchuje oba profily  
- `více modulů` / `vice modulu` → matchuje `implementation_planner_complex` (12 bodů)

**Problém je v asymetrii váh:**

| Keyword | `implementation_planner` | `implementation_planner_complex` |
|---------|--------------------------|----------------------------------|
| `implementační plán` | **18** | *není definováno* |
| `plán` | **10** | *není definováno* |
| `komplexní plán` | *není definováno* | **18** |
| `více modulů` | *není definováno* | **12** |

Profil `implementation_planner_complex` **nedědí keywords** z rodičovského profilu `implementation_planner` (přestože má `extends: implementation_planner`).

---

## Detailní Flow Analýza

```
1. Prompt analyzován → complexity: "high", prompt_length: 23
2. Topics detekce → ["implementation_planner", "implementation_planner_complex", ...]
3. Matching:
   - implementation_planner: match_score=1.0, is_match=True
   - implementation_planner_complex: match_score=1.0, is_match=True
4. Scoring:
   - implementation_planner: 38 bodů (výše díky více keywords)
   - implementation_planner_complex: 23 bodů
5. Best candidate: implementation_planner (38 > 23)
6. Complexity adjustment check:
   - _should_prefer_complex = True ✓
   - complex_score (23) >= best_score * 0.8 (30.4)? ✗
   - → NEPŘEPNUTO
7. Výsledek: implementation_planner
```

---

## Doporučená řešení

### Řešení 1: Dědění keywords (Doporučeno)

Implementovat dědění `weights.keywords` z rodičovského profilu při `extends`:

```python
# V profile_parser.py
if parsed.yaml_metadata.get("extends"):
    parent_name = parsed.yaml_metadata["extends"]
    parent_profile = profiles.get(parent_name)
    if parent_profile:
        # Merge keywords: parent + child (child přepisuje)
        merged_keywords = {**parent_profile.weights.get("keywords", {})}
        merged_keywords.update(parsed.profile.weights.get("keywords", {}))
        # ... aktualizovat profil
```

### Řešení 2: Snížení score ratio thresholdu

Změnit `COMPLEX_VARIANT_MIN_SCORE_RATIO` z 0.8 na nižší hodnotu (např. 0.5):

```bash
export MCP_COMPLEXITY_SCORE_RATIO=0.5
```

**Nevýhoda:** Může způsobit přepnutí i když komplexní varianta špatně matchuje.

### Řešení 3: Přidat chybějící keywords do komplexního profilu

Doplnit do `implementation_planner_complex.md`:

```yaml
weights:
  keywords:
    # Zděděná (měla by být automaticky)
    implementační plán: 18
    implementacni plan: 18
    plán: 10
    plan: 10
    # Specifická pro complex
    komplexní plán: 18
    více modulů: 12
    ...
```

### Řešení 4: Bonus za complexity match

Přidat bonus ke skóre komplexní varianty, když `_should_prefer_complex = True`:

```python
if self._should_prefer_complex(metadata) and profile.name.endswith(COMPLEX_SUFFIX):
    score += COMPLEXITY_PREFERENCE_BONUS  # např. 15
```

---

## Testovací příkaz

Pro ověření po implementaci opravy:

```bash
cd K:\Data_science_projects\MCP_Prompt_Broker
python -c "
from src.mcp_prompt_broker.profile_parser import get_profile_loader
from src.mcp_prompt_broker.metadata.parser import analyze_prompt
from src.mcp_prompt_broker.router.hybrid_router import get_router

loader = get_profile_loader()
prompt = 'Vytvoř komplexní implementační plán pro úpravu adresářové struktury workspace v souladu s nejlepší praxí. Workspace obsahuje více modulů: mcp-prompt-broker, llama-orchestrator, mcp-codex-orchestrator a další.'

parsed = analyze_prompt(prompt)
enhanced = parsed.to_enhanced_metadata()
router = get_router(loader.profiles)
result = router.route(enhanced)

print('Profile:', result.profile.name)
print('Expected: implementation_planner_complex')
print('Match:', result.profile.name == 'implementation_planner_complex')
"
```

---

## Závěr

| Aspekt | Status |
|--------|--------|
| Complexity detekce | ✅ Funguje správně |
| Profile matching | ✅ Oba profily matchují |
| Keyword scoring | ⚠️ Asymetrické váhy |
| Score ratio check | ❌ Blokuje přepnutí |
| `extends` dědění | ❌ Není implementováno |

**Hlavní příčina:** Komplexní profil nedědí keywords z rodičovského profilu a má nižší skóre než požadované minimum (80% skóre základního profilu).

**Doporučení:** Implementovat dědění keywords při použití `extends` nebo přidat chybějící keywords do komplexního profilu.
