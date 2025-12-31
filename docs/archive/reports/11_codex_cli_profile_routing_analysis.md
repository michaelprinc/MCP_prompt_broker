# Analýza problému routování Codex CLI profilu

**Datum:** 2025-12-25  
**Autor:** GitHub Copilot  
**Typ:** Analýza & Implementační plán  
**Priorita:** Vysoká  

---

## 📋 Shrnutí

MCP server "prompt broker" **neidentifikoval** prompt obsahující explicitní zmínku o "Codex CLI" jako úlohu pro profil `python_code_generation_complex_with_codex.md`. 

### Analyzovaný prompt

```text
Dobrý den, GitHub Copilot. Prosím, použij Codex CLI pro vytvoření ukázky modelovací 
úlohy. Modelovací úloha by měla analyzovat jednu z klasifikačních úloh v "Sci-Kit 
Learn dataset". Výsledek by měl být v novém adresáři.
```

### Výsledek routování

- **Vybraný profil:** `general_default_complex` (fallback)
- **Score:** 2
- **Consistency:** 73.11%
- **Očekávaný profil:** `python_code_generation_complex_with_codex`

---

## 🔍 Identifikované problémy

### 1. **Profil nebyl načten** ❌

Profil `python_code_generation_complex_with_codex.md` **nebyl vůbec načten** do systému.

**Důvod:** Chybí povinná sekce `## Instructions` v markdown souboru.

**Chybová hláška:**
```python
ProfileParseError: Missing '## Instructions' section: 
src\mcp_prompt_broker\copilot-profiles\python_code_generation_complex_with_codex.md
```

**Důsledek:** 
- Profil se neobjevuje v seznamu načtených profilů (14 profilů vs. očekávaných 15+)
- Nemůže být vybrán routerem
- Hot reload nefunguje pro tento profil

### 2. **Struktura profilu neodpovídá parser specifikaci**

**Parser očekává:**
```markdown
---
name: profile_name
required:
  capabilities: [...]
weights:
  keywords: ...
---

## Instructions
[Hlavní instrukce pro profil]

## Checklist
- [ ] Item 1
- [ ] Item 2
```

**Aktuální struktura Codex CLI profilu:**
```markdown
---
name: python_code_generation_complex_with_codex
required:
  capabilities: ["code_generation", "programming", "python", "architecture", "Codex CLI", "Codex"]
weights:
  keywords:
    - Codex CLI
    - Codex
---

## Primary Role
[Obsah...]

## Meta-Framework for Orchestration
[Obsah...]

## Implementation Workflow
[Obsah...]
```

**Problém:** Sekce `## Instructions` chybí, parser ji hledá na řádku 184 v [profile_parser.py](src/mcp_prompt_broker/profile_parser.py#L184).

### 3. **Metadata parser nezná klíčová slova "Codex CLI"**

Soubor [metadata/parser.py](src/mcp_prompt_broker/metadata/parser.py) obsahuje slovníky pro detekci:
- `INTENT_KEYWORDS`: brainstorm, bug_report, diagnosis, ...
- `DOMAIN_KEYWORDS`: healthcare, finance, engineering, ...
- `TOPIC_KEYWORDS`: pii, compliance, storytelling, ...

**"Codex CLI" není v žádném z nich.**

**Výsledek analýzy promptu:**
```python
Intent: statement
Domain: None
Topics: []
Sensitivity: low
Complexity: low-medium
```

**Důsledek:**
- Prompt je detekován jako obecný "statement" bez specifické domény
- Žádné klíčové slovo "Codex" nebo "CLI" není rozpoznáno
- Context tags jsou prázdné
- Router nemá žádná kritéria pro výběr Codex CLI profilu

### 4. **Hot reload nefunguje pro chybně strukturované profily**

Hot reload mechanismus v [server.py](src/mcp_prompt_broker/server.py#L220) volá:
```python
result = loader.reload()
```

Který iteruje přes `.md` soubory a volá `parse_profile_markdown()`. 

**Pokud parsování selže:**
- Error je zalogován do `_load_errors`
- Profil je **přeskočen**
- Hot reload reportuje úspěch, ale profil chybí

**Důsledek:**
- Uživatel neví, že profil nebyl načten
- Žádná výstraha v konzoli
- Silent failure

---

## 🎯 Hlavní příčiny

| # | Příčina | Typ | Dopad |
|---|---------|-----|-------|
| 1 | Chybějící sekce `## Instructions` v profilu | **Kritická** | Profil není načten |
| 2 | Parser nemá fallback pro neexistující `## Instructions` | **Vysoká** | Striktní validace |
| 3 | Metadata parser nezná "Codex CLI" keywords | **Vysoká** | Nulová detekce |
| 4 | Hot reload tiše selhává | **Střední** | UX problém |
| 5 | Chybí validace po hot reload | **Střední** | Debugging obtížný |

---

## 📊 Analýza routovacího procesu

### Krok 1: Analýza promptu

```python
# metadata/parser.py: analyze_prompt()
normalized = prompt.lower()
# "dobrý den, github copilot. prosím, použij codex cli..."

intent = _classify_intent(normalized)  
# -> "statement" (žádné klíčové slovo nenalezeno)

domain = _detect_domain(normalized)    
# -> None (žádná doména nenalezena)

topics = _collect_topics(normalized)   
# -> [] (žádné topics)
```

**Problém:** "codex cli", "modelovací úloha", "klasifikační úloha", "sci-kit learn" nejsou rozpoznány.

### Krok 2: Enhanced metadata

```python
# router/profile_router.py: EnhancedMetadata
{
    "prompt": "...",
    "domain": None,
    "intent": "statement",
    "context_tags": set()  # PRÁZDNÉ!
}
```

### Krok 3: Profile matching

```python
# config/profiles.py: InstructionProfile.is_match()
for profile in profiles:
    if not profile.is_match(metadata_map):
        continue
```

**Pro `python_code_generation_complex_with_codex` (kdyby byl načten):**
```python
required = {
    "capabilities": ["code_generation", "programming", "python", 
                     "architecture", "Codex CLI", "Codex"]
}
```

**Kontrola:**
```python
value = metadata.get("capabilities")  # -> None
if value is None:
    return False  # ❌ NEPROJDE
```

**Důsledek:** Ani kdyby profil byl načten, **neprojde** matchingem, protože metadata neobsahují `capabilities`.

### Krok 4: Fallback

Router vybere `general_default_complex` jako fallback profil.

---

## 💡 Doporučená řešení

### 🔧 Řešení 1: Oprava struktury profilu (OKAMŽITÉ)

**Priorita:** Kritická  
**Složitost:** Nízká  
**Dopad:** Vysoký  

#### Akce:

1. Přidat sekci `## Instructions` do profilu
2. Přesunout obsah z `## Primary Role` do `## Instructions`
3. Zachovat ostatní sekce jako dokumentaci

#### Implementace:

```markdown
---
name: python_code_generation_complex_with_codex
short_description: Advanced Python code generation with Codex CLI orchestration
extends: python_code_generation_complex
default_score: 8

required:
  capabilities: ["code_generation", "programming", "python", "architecture", "Codex CLI", "Codex"]

weights:
  priority:
    high: 3
    critical: 4
  complexity:
    high: 3
    complex: 4
  domain:
    python: 5
    backend: 3
    architecture: 4
  keywords:
    - advanced python
    - Codex CLI
    - Codex
    - complex code
    - modelovací úloha
    - klasifikační úloha
    - machine learning
---

## Instructions

You are an **orchestrator and auditor** for Codex CLI in the VS Code terminal. 

Your job is NOT to write code directly, but to:

1. **Analyze** user requests for Python development tasks
2. **Create** a detailed implementation plan
3. **Delegate** tasks to Codex CLI using precise commands
4. **Audit** Codex CLI outputs
5. **Iterate** until the desired quality is achieved

[... zbytek původního obsahu z Primary Role ...]

## Checklist

- [ ] Analyze user requirements
- [ ] Create implementation plan
- [ ] Break down into atomic tasks
- [ ] Generate Codex CLI commands
- [ ] Execute and monitor tasks
- [ ] Audit outputs
- [ ] Iterate on feedback
```

---

### 🔧 Řešení 2: Rozšíření metadata parseru (VYSOKÁ PRIORITA)

**Priorita:** Vysoká  
**Složitost:** Střední  
**Dopad:** Velmi vysoký  

#### Akce:

Přidat rozpoznávání Codex CLI keywords do metadata parseru.

#### Implementace:

**Soubor:** [src/mcp_prompt_broker/metadata/parser.py](src/mcp_prompt_broker/metadata/parser.py)

```python
# Přidat do INTENT_KEYWORDS
INTENT_KEYWORDS: Mapping[str, tuple[str, ...]] = {
    "bug_report": ("bug", "stack trace", "exception", "error", "crash"),
    "brainstorm": ("brainstorm", "ideas", "ideation", "imagine", "creative"),
    "diagnosis": ("investigate", "diagnose", "root cause", "analysis"),
    "review": ("review", "feedback", "critique", "audit"),
    "question": ("how", "what", "why", "can you"),
    "code_generation": ("vytvoř", "generuj", "implementuj", "codex cli", "použij codex"),  # ✨ NOVÉ
}

# Přidat do DOMAIN_KEYWORDS
DOMAIN_KEYWORDS: Mapping[str, tuple[str, ...]] = {
    "healthcare": ("patient", "medical", "clinic", "hospital"),
    "finance": ("payment", "invoice", "credit", "bank", "ssn", "tax"),
    "engineering": ("stack trace", "exception", "api", "deploy", "server", "debug"),
    "security": ("exploit", "payload", "vulnerability", "attack", "breach"),
    "legal": ("contract", "law", "regulation", "compliance"),
    "marketing": ("campaign", "launch", "ad copy", "audience"),
    "data_science": ("model", "dataset", "klasifikac", "sci-kit learn", "sklearn", "machine learning"),  # ✨ NOVÉ
    "python": ("python", "pip", "venv", ".py", "pytest"),  # ✨ NOVÉ
}

# Přidat do TOPIC_KEYWORDS
TOPIC_KEYWORDS: Mapping[str, tuple[str, ...]] = {
    "pii": ("ssn", "social security", "credit card", "personal data", "patient"),
    "compliance": ("hipaa", "gdpr", "pci", "regulation", "policy"),
    "storytelling": ("story", "narrative", "creative", "brainstorm"),
    "incident": ("outage", "downtime", "breach", "incident", "crash", "failure"),
    "security": ("exploit", "payload", "attack", "ransomware"),
    "codex_cli": ("codex cli", "codex", "tool orchestration", "cli tool"),  # ✨ NOVÉ
    "ml_modeling": ("modelovací úloha", "klasifikační", "classification", "regression", "dataset"),  # ✨ NOVÉ
}
```

**Výhody:**
- ✅ Automatická detekce Codex CLI promptů
- ✅ Lepší rozpoznání data science úloh
- ✅ Český jazyk podporován
- ✅ Context tags budou obsahovat relevantní topics

---

### 🔧 Řešení 3: Flexibilnější parser s fallback (STŘEDNÍ PRIORITA)

**Priorita:** Střední  
**Složitost:** Střední  
**Dopad:** Střední  

#### Akce:

Upravit parser, aby nezlyhával na chybějící sekci `## Instructions`.

#### Implementace:

**Soubor:** [src/mcp_prompt_broker/profile_parser.py](src/mcp_prompt_broker/profile_parser.py#L175-L185)

```python
def parse_profile_markdown(file_path: Path) -> ParsedProfile:
    """Parse a single profile markdown file."""
    # ... existující kód ...
    
    # Extract instructions section
    instructions = _extract_section(markdown, "Instructions")
    
    # ✨ NOVÝ FALLBACK
    if not instructions:
        # Fallback 1: Try "Primary Role"
        instructions = _extract_section(markdown, "Primary Role")
    
    if not instructions:
        # Fallback 2: Use short_instructions from metadata
        instructions = metadata.get("short_instructions", "")
    
    if not instructions:
        # Fallback 3: Use entire markdown content (bez frontmatter)
        instructions = markdown.strip()
    
    # ✨ ZMĚNA: Soft warning místo hard error
    if not _extract_section(markdown, "Instructions"):
        import warnings
        warnings.warn(
            f"Profile {name} missing '## Instructions' section, using fallback",
            UserWarning
        )
    
    # ... zbytek kódu ...
```

**Výhody:**
- ✅ Více profilů může být načteno
- ✅ Zpětně kompatibilní
- ✅ Varování místo selhání

**Nevýhody:**
- ⚠️ Méně striktní validace
- ⚠️ Možné nekonzistence

---

### 🔧 Řešení 4: Rozšířená validace a reporting (STŘEDNÍ PRIORITA)

**Priorita:** Střední  
**Složitost:** Nízká  
**Dopad:** Vysoký (UX)  

#### Akce:

Vylepšit hot reload reporting, aby uživatel viděl chyby.

#### Implementace:

**Soubor:** [src/mcp_prompt_broker/server.py](src/mcp_prompt_broker/server.py)

```python
@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> Any:
    if name == "reload_profiles":
        try:
            result = loader.reload()
            
            # ✨ NOVÉ: Detailed reporting
            response = {
                "success": result.get("success", False),
                "profiles_loaded": result.get("profiles_loaded", 0),
                "profile_names": result.get("profile_names", []),
                "profiles_dir": result.get("profiles_dir", ""),
                "errors": result.get("errors", []),
                "warnings": [],  # ✨ NOVÉ
            }
            
            # ✨ NOVÉ: Warning for low profile count
            if response["profiles_loaded"] < 15:
                response["warnings"].append(
                    f"Expected at least 15 profiles, but only {response['profiles_loaded']} loaded. "
                    f"Check for parse errors."
                )
            
            # ✨ NOVÉ: List files vs. loaded
            all_md_files = list(Path(result["profiles_dir"]).glob("*.md"))
            loaded_set = set(result["profile_names"])
            
            for md_file in all_md_files:
                expected_name = md_file.stem
                if expected_name not in loaded_set:
                    response["warnings"].append(
                        f"Profile file '{md_file.name}' exists but was not loaded. "
                        f"Check parse errors."
                    )
            
            return [types.TextContent(
                type="text",
                text=json.dumps(response, indent=2)
            )]
        except Exception as exc:
            return [types.TextContent(type="text", text=f"Error reloading profiles: {str(exc)}")]
```

**Výhody:**
- ✅ Uživatel vidí chyby okamžitě
- ✅ Transparentní debugging
- ✅ Detekce nesouladu mezi soubory a načtenými profily

---

### 🔧 Řešení 5: Automatické mapování capabilities (NÍZKÁ PRIORITA)

**Priorita:** Nízká  
**Složitost:** Vysoká  
**Dopad:** Vysoký (dlouhodobě)  

#### Koncept:

Metadata parser by mohl **automaticky odvozovat capabilities** z promptu:

```python
def _infer_capabilities(normalized: str, topics: Set[str]) -> Set[str]:
    """Infer capabilities from prompt content."""
    caps = set()
    
    if any(kw in normalized for kw in ["codex", "tool", "cli", "orchestr"]):
        caps.add("Codex CLI")
    
    if any(kw in normalized for kw in ["python", ".py", "pip"]):
        caps.add("python")
        caps.add("programming")
    
    if any(kw in normalized for kw in ["model", "klasifikac", "dataset"]):
        caps.add("machine_learning")
        caps.add("data_science")
    
    if "codex_cli" in topics:
        caps.add("Codex CLI")
        caps.add("Codex")
    
    return caps
```

**Integrace do `analyze_prompt()`:**

```python
def analyze_prompt(prompt: str) -> ParsedMetadata:
    # ... existující kód ...
    
    topics = _collect_topics(normalized)
    capabilities = _infer_capabilities(normalized, topics)  # ✨ NOVÉ
    
    return ParsedMetadata(
        prompt=prompt,
        intent=intent,
        domain=domain,
        topics=frozenset(topics),
        capabilities=frozenset(capabilities),  # ✨ NOVÉ
        sensitivity=sensitivity,
        safety_score=safety_score,
        tone=tone,
        complexity=complexity,
    )
```

**Úprava `EnhancedMetadata`:**

```python
@dataclass(frozen=True)
class EnhancedMetadata:
    prompt: str
    domain: str | None = None
    sensitivity: str | None = None
    language: str | None = None
    priority: str | None = None
    audience: str | None = None
    intent: str | None = None
    context_tags: frozenset[str] = field(default_factory=frozenset)
    capabilities: frozenset[str] = field(default_factory=frozenset)  # ✨ NOVÉ
```

**Výhody:**
- ✅ Automatická detekce bez manuální konfigurace
- ✅ Profily s `required.capabilities` budou fungovat
- ✅ Sémanticky bohatší metadata

**Nevýhody:**
- ⚠️ Vysoká složitost implementace
- ⚠️ Riziko false positives
- ⚠️ Vyžaduje testování a tuning

---

## 📋 Implementační plán

### Fáze 1: Okamžitá oprava (30 minut)

**Cíl:** Zprovoznit Codex CLI profil

- [x] **Úkol 1.1:** Přidat sekci `## Instructions` do profilu
- [ ] **Úkol 1.2:** Otestovat parsing profilu
- [ ] **Úkol 1.3:** Spustit hot reload
- [ ] **Úkol 1.4:** Ověřit, že profil je načten

**Acceptance criteria:**
- ✅ `parse_profile_markdown()` úspěšně parsuje profil
- ✅ Profil je v seznamu načtených profilů
- ✅ Hot reload funguje bez chyb

---

### Fáze 2: Rozšíření metadata parseru (1-2 hodiny)

**Cíl:** Lepší detekce Codex CLI a ML úloh

- [ ] **Úkol 2.1:** Přidat keywords do `INTENT_KEYWORDS`
- [ ] **Úkol 2.2:** Přidat keywords do `DOMAIN_KEYWORDS`
- [ ] **Úkol 2.3:** Přidat keywords do `TOPIC_KEYWORDS`
- [ ] **Úkol 2.4:** Otestovat s původním promptem
- [ ] **Úkol 2.5:** Přidat jednotkové testy

**Acceptance criteria:**
- ✅ Prompt s "Codex CLI" detekován jako `intent="code_generation"`
- ✅ Prompt s "klasifikační úloha" detekován s `topics=["ml_modeling", "codex_cli"]`
- ✅ Prompt s "Sci-Kit Learn" detekován s `domain="data_science"`

**Soubory k úpravě:**
- [src/mcp_prompt_broker/metadata/parser.py](src/mcp_prompt_broker/metadata/parser.py)
- [tests/test_metadata_parser.py](tests/test_metadata_parser.py)

---

### Fáze 3: Parser fallback (1 hodina)

**Cíl:** Robustnější parsing profilů

- [ ] **Úkol 3.1:** Implementovat fallback v `parse_profile_markdown()`
- [ ] **Úkol 3.2:** Přidat warnings pro chybějící sekce
- [ ] **Úkol 3.3:** Otestovat s různými strukturami profilů
- [ ] **Úkol 3.4:** Dokumentovat podporované formáty

**Acceptance criteria:**
- ✅ Parser nepřestane fungovat při chybějící `## Instructions`
- ✅ Warning je zalogován do `_load_errors` nebo warnings
- ✅ Fallback používá `## Primary Role` nebo `short_instructions`

**Soubory k úpravě:**
- [src/mcp_prompt_broker/profile_parser.py](src/mcp_prompt_broker/profile_parser.py#L175-L185)

---

### Fáze 4: Vylepšený reporting (1 hodina)

**Cíl:** Transparentní debugging

- [ ] **Úkol 4.1:** Rozšířit `reload_profiles` response
- [ ] **Úkol 4.2:** Přidat warnings pro chybějící profily
- [ ] **Úkol 4.3:** Porovnat soubory vs. načtené profily
- [ ] **Úkol 4.4:** Přidat debug logging

**Acceptance criteria:**
- ✅ Hot reload vrací detailní informace o chybách
- ✅ Warnings obsahují jména souborů, které nebyly načteny
- ✅ Uživatel vidí rozdíl mezi očekávanými a skutečnými profily

**Soubory k úpravě:**
- [src/mcp_prompt_broker/server.py](src/mcp_prompt_broker/server.py#L220)
- [src/mcp_prompt_broker/profile_parser.py](src/mcp_prompt_broker/profile_parser.py)

---

### Fáze 5: Capabilities inference (3-4 hodiny) [VOLITELNÉ]

**Cíl:** Automatická detekce capabilities

- [ ] **Úkol 5.1:** Navrhnout `_infer_capabilities()` funkci
- [ ] **Úkol 5.2:** Přidat `capabilities` do `ParsedMetadata`
- [ ] **Úkol 5.3:** Propagovat do `EnhancedMetadata`
- [ ] **Úkol 5.4:** Otestovat s různými prompty
- [ ] **Úkol 5.5:** Vyladit keyword matching

**Acceptance criteria:**
- ✅ Prompty s "Codex CLI" mají `capabilities=["Codex CLI", "Codex"]`
- ✅ Prompty s "Python" mají `capabilities=["python", "programming"]`
- ✅ Profily s `required.capabilities` úspěšně matchují

**Soubory k úpravě:**
- [src/mcp_prompt_broker/metadata/parser.py](src/mcp_prompt_broker/metadata/parser.py)
- [src/mcp_prompt_broker/router/profile_router.py](src/mcp_prompt_broker/router/profile_router.py)
- [tests/test_profile_router.py](tests/test_profile_router.py)

---

## 🧪 Testovací scénáře

### Test 1: Codex CLI prompt (český jazyk)

**Prompt:**
```
Prosím, použij Codex CLI pro vytvoření ukázky modelovací úlohy.
```

**Očekávaný výsledek:**
- Intent: `code_generation`
- Domain: `data_science` nebo `python`
- Topics: `["codex_cli", "ml_modeling"]`
- Vybraný profil: `python_code_generation_complex_with_codex`

---

### Test 2: Codex CLI prompt (anglický jazyk)

**Prompt:**
```
Use Codex CLI to create a classification model for the iris dataset.
```

**Očekávaný výsledek:**
- Intent: `code_generation`
- Domain: `data_science`
- Topics: `["codex_cli", "ml_modeling"]`
- Vybraný profil: `python_code_generation_complex_with_codex`

---

### Test 3: Obecný Python prompt (bez Codex CLI)

**Prompt:**
```
Create a Python script to read CSV files and plot histograms.
```

**Očekávaný výsledek:**
- Intent: `code_generation`
- Domain: `python`
- Topics: `[]` nebo `["data_visualization"]`
- Vybraný profil: `python_code_generation` nebo `python_code_generation_complex`

---

### Test 4: Hot reload s chybějící sekcí

**Akce:**
1. Vytvořit profil bez `## Instructions`
2. Spustit `reload_profiles` tool
3. Zkontrolovat response

**Očekávaný výsledek:**
- Success: `false` nebo `true` s warnings
- Errors nebo warnings obsahují jméno souboru
- Profil není načten nebo je načten s fallback

---

## 📊 Metriky úspěchu

| Metrika | Před opravou | Cíl po opravě |
|---------|-------------|---------------|
| Načtené profily | 14 | 15+ |
| Codex CLI prompt detekce | 0% | 95%+ |
| False positive rate | N/A | < 5% |
| Hot reload úspěšnost | ~93% (14/15) | 100% |
| Parse errors viditelné | Ne | Ano |

---

## 🔐 Rizika a mitigace

| Riziko | Pravděpodobnost | Dopad | Mitigace |
|--------|-----------------|-------|----------|
| Fallback parser způsobí nekonzistence | Střední | Střední | Přísná validace + unit testy |
| Nové keywords způsobí false positives | Střední | Nízký | A/B testování, tuning |
| Capabilities inference přetíží systém | Nízká | Střední | Optimalizace, caching |
| Breaking changes v existujících profilech | Nízká | Vysoký | Zpětná kompatibilita |

---

## 📝 Závěr

### Hlavní zjištění

1. ✅ **Profil nebyl načten** kvůli chybějící sekci `## Instructions`
2. ✅ **Metadata parser nezná** "Codex CLI" keywords
3. ✅ **Hot reload tiše selhává** bez upozornění uživatele
4. ✅ **Required capabilities** v profilu nejsou matchovány

### Doporučené prioritní akce

1. **Okamžitě:** Opravit strukturu Codex CLI profilu (30 min)
2. **Dnes:** Rozšířit metadata parser o Codex CLI keywords (1-2 hod)
3. **Tento týden:** Implementovat parser fallback a lepší reporting (2 hod)
4. **Volitelně:** Automatická capabilities inference (3-4 hod)

### Další kroky

- [ ] Spustit Fázi 1 (okamžitá oprava)
- [ ] Otestovat hot reload
- [ ] Iterovat na Fázi 2-4
- [ ] Vytvořit jednotkové testy
- [ ] Aktualizovat dokumentaci

---

**Status:** ✅ Analýza kompletní  
**Následující krok:** Implementace Fáze 1 (okamžitá oprava profilu)
