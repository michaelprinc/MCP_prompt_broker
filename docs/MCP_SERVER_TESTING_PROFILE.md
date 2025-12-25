# MCP Server Testing and Validation Profile - Dokumentace

**Datum vytvoření:** 2025-12-25  
**Profil:** `mcp_server_testing_and_validation.md`  
**Účel:** Systematické testování a validace MCP Prompt Broker serveru  

---

## 📋 Přehled

Vytvořil jsem nový profil pro **testování a validaci MCP serveru "prompt broker"**, který využívá poznatky z provedené analýzy routovacích problémů.

### Vytvořené soubory

1. **[src/mcp_prompt_broker/copilot-profiles/mcp_server_testing_and_validation.md](../src/mcp_prompt_broker/copilot-profiles/mcp_server_testing_and_validation.md)**
   - Hlavní profil pro testování a validaci
   - Obsahuje správnou strukturu s `## Instructions`
   - Komplexní checklist pro systematické testování
   - Validní YAML metadata s capabilities a keywords

2. **[tests/test_mcp_server_validation.py](../tests/test_mcp_server_validation.py)**
   - Automatizovaný validační skript
   - Implementuje všech 5 fází testování
   - Generuje JSON report s výsledky

3. **[tests/test_testing_profile_routing.py](../tests/test_testing_profile_routing.py)**
   - Test detekce testovacího profilu
   - Ověřuje routing pro validační prompty

---

## 🎯 Funkce profilu

### 1. Systematické testování

Profil poskytuje strukturovaný přístup k testování:

- **Fáze 1:** Validace struktury profilů
- **Fáze 2:** Testování načítání profilů
- **Fáze 3:** Testování metadata parseru
- **Fáze 4:** Testování routovací logiky
- **Fáze 5:** Testování hot reload

### 2. Detekce obvyklých problémů

Profil identifikuje typické chyby:

✅ Chybějící sekce `## Instructions`  
✅ Nevalidní YAML frontmatter  
✅ Prázdná pole `required` nebo `weights`  
✅ Chybějící keywords  
✅ Silent failures při hot reload  
✅ Nesoulad mezi soubory a načtenými profily  

### 3. Automatizované testování

Skript `test_mcp_server_validation.py` provádí:

- Skenování všech `.md` souborů
- Parsování a validace struktury
- Testování metadata parseru s různými prompty
- Testování routovací logiky
- Ověření hot reload konzistence

---

## 📊 Výsledky prvního testu

### Celkové statistiky

```
📋 Profile Validation:
  Valid: 4/17 (23.5%)
  Warnings: 11
  Errors: 2

🔄 Profile Loading:
  Success rate: 88.2%
  Missing profiles: 2

🧪 Metadata Parser:
  Passed: 2/5 (40%)

🎯 Routing Logic:
  Passed: 1/5 (20%)

🔄 Hot Reload:
  Consistent: Yes
```

### Nalezené problémy

#### ❌ Kritické chyby (2)

1. **codex_cli.md** - Chybí YAML frontmatter
2. **python_code_generation_complex_with_codex.md** - Chybí `## Instructions`

#### ⚠️ Warnings (11 profilů)

Většina profilů má jeden nebo více z těchto problémů:
- Chybí `short_description`
- Žádné keywords definované
- Prázdné `required` field

---

## 🔧 Konfigurace profilu

### YAML Metadata

```yaml
---
name: mcp_server_testing_and_validation
short_description: Systematic testing and validation of MCP Prompt Broker
extends: null
default_score: 7
fallback: false

required:
  capabilities: ["testing", "validation", "mcp_server", "debugging"]

weights:
  priority:
    high: 3
    critical: 4
  complexity:
    medium: 2
    high: 3
  domain:
    testing: 5
    quality_assurance: 4
    debugging: 4
  keywords:
    - mcp server
    - prompt broker
    - test
    - testing
    - validation
    - validate
    - verify
    - check
    - debug
    - diagnose
    - profile
    - routing
    - hot reload
    - metadata
    - parser
    - funkčnost
    - kontrola
---
```

### Klíčové vlastnosti

- **default_score: 7** - Vyšší než generic profiles (1-2), nižší než specialized (8-10)
- **required.capabilities** - Obsahuje testing, validation, mcp_server, debugging
- **weights.keywords** - Rozšířený seznam včetně českých termínů
- **weights.domain** - testing, quality_assurance, debugging s vysokými váhami

---

## 🧪 Použití

### Manuální testování

```bash
# Spustit kompletní validační sadu
python tests/test_mcp_server_validation.py

# Výstup: JSON report v tests/mcp_server_validation_report.json
```

### Programatické použití

```python
from tests.test_mcp_server_validation import MCPServerValidator

validator = MCPServerValidator()
results = validator.run_all_tests()

# Zkontrolovat výsledky
if results["overall_status"] == "passed":
    print("✅ All tests passed!")
else:
    print("❌ Some tests failed")
    print(f"Errors: {results['profile_validation']['errors']}")
```

### Integrace s CI/CD

```yaml
# .github/workflows/test-mcp-server.yml
- name: Validate MCP Server
  run: |
    python tests/test_mcp_server_validation.py
    
- name: Upload test report
  uses: actions/upload-artifact@v3
  with:
    name: validation-report
    path: tests/mcp_server_validation_report.json
```

---

## ⚠️ Aktuální omezení

### 1. Metadata parser nerozpoznává testovací keywords

**Problém:** Prompty jako "test MCP server" nebo "validate profiles" nejsou routovány k testovacímu profilu.

**Příčina:** `metadata/parser.py` neobsahuje keywords:
- "test", "testing", "validation", "validate"
- "mcp server", "prompt broker"
- "funkčnost", "kontrola" (česky)

**Řešení:** Implementovat Fázi 2 z implementačního plánu (rozšíření metadata parseru).

### 2. Profil vyžaduje capabilities v metadata

**Problém:** Routing funguje pouze pokud prompt metadata obsahují matching capabilities.

**Příčina:** `required.capabilities` obsahuje ["testing", "validation", "mcp_server", "debugging"], ale metadata parser je negeneruje.

**Řešení:** Implementovat Fázi 5 z implementačního plánu (capabilities inference).

---

## 🚀 Doporučené další kroky

### Krok 1: Rozšířit metadata parser (Priorita: VYSOKÁ)

Přidat do `src/mcp_prompt_broker/metadata/parser.py`:

```python
INTENT_KEYWORDS: Mapping[str, tuple[str, ...]] = {
    # ... existující ...
    "testing": ("test", "testing", "validate", "validation", "verify", "check"),
    "debugging": ("debug", "diagnose", "troubleshoot", "investigate"),
}

DOMAIN_KEYWORDS: Mapping[str, tuple[str, ...]] = {
    # ... existující ...
    "testing": ("mcp server", "prompt broker", "profile", "routing"),
    "quality_assurance": ("qa", "quality", "validation", "verification"),
}

TOPIC_KEYWORDS: Mapping[str, tuple[str, ...]] = {
    # ... existující ...
    "mcp_testing": ("mcp server", "prompt broker", "hot reload", "metadata"),
    "profile_validation": ("profile", "routing", "parser", "validation"),
}
```

### Krok 2: Opravit identifikované profily (Priorita: KRITICKÁ)

1. **codex_cli.md** - Přidat YAML frontmatter
2. **python_code_generation_complex_with_codex.md** - Přidat `## Instructions`

### Krok 3: Vylepšit warnings reporting (Priorita: STŘEDNÍ)

- Přidat `short_description` do všech profilů
- Definovat keywords tam, kde chybí
- Vyplnit `required` fields

---

## 📈 Metriky úspěchu

Po implementaci doporučených změn očekávám:

| Metrika | Před | Cíl |
|---------|------|-----|
| Profile loading success rate | 88.2% | 100% |
| Valid profiles | 23.5% (4/17) | 100% (17/17) |
| Parser test pass rate | 40% (2/5) | 100% (5/5) |
| Routing test pass rate | 20% (1/5) | 80%+ (4+/5) |
| Testing profile detection | 0% | 90%+ |

---

## 🎓 Poznatky z analýzy

Tento profil byl vytvořen na základě skutečné analýzy problému s routováním Codex CLI profilu. Klíčové poznatky:

1. **Struktura je kritická** - Bez `## Instructions` profil nebude načten
2. **Keywords musí být v parseru** - Profil může být perfektní, ale pokud parser nerozpozná klíčová slova, nebude vybrán
3. **Silent failures jsou nebezpečné** - Hot reload hlásí úspěch i když některé profily selhaly
4. **Validace je nezbytná** - Systematické testování odhalí problémy, které by jinak zůstaly skryté

---

## 📚 Související dokumenty

- [reports/11_codex_cli_profile_routing_analysis.md](../reports/11_codex_cli_profile_routing_analysis.md) - Původní analýza problému
- [src/mcp_prompt_broker/copilot-profiles/mcp_server_testing_and_validation.md](../src/mcp_prompt_broker/copilot-profiles/mcp_server_testing_and_validation.md) - Samotný profil
- [tests/test_mcp_server_validation.py](../tests/test_mcp_server_validation.py) - Validační skript

---

**Status:** ✅ Profil vytvořen a otestován  
**Následující krok:** Implementace Fáze 2 (rozšíření metadata parseru) pro plnou funkčnost
