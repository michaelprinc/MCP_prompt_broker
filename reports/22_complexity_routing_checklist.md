# Complexity-Based Profile Routing - Implementation Checklist

> Generated: 2024-12-31  
> Complexity: **Complex**  
> Estimated Total Effort: **4-6 hours**  
> Status: 🚧 In Progress

---

## Overview

Implementace automatického preferování `_complex` variant profilů u dlouhých/komplexních promptů v MCP Prompt Broker serveru.

---

## Phase 1: Metadata Extension (Est: 1 hour)

### 1.1 Parser Enhancement

- [ ] **1.1.1** Přidat konstanty `COMPLEXITY_KEYWORDS` do [parser.py](../src/mcp_prompt_broker/metadata/parser.py)
  - Acceptance: Slovník s 10+ klíčových slov a jejich váhami
  - Keywords: `complex`, `enterprise`, `migration`, `refactor`, `architecture`, `distributed`, `scalable`, `multi-module`, `infrastructure`, `cross-team`

- [ ] **1.1.2** Rozšířit funkci `_estimate_complexity()` o detekci klíčových slov
  - Acceptance: Funkce vrací tuple `(complexity_level: str, word_count: int, keyword_bonus: int)`
  - Acceptance: Testy projdou s 90%+ přesností

- [ ] **1.1.3** Přidat atribut `prompt_length: int` do dataclass `ParsedMetadata`
  - Acceptance: Atribut je dostupný v `as_dict()` výstupu

### 1.2 EnhancedMetadata Extension

- [ ] **1.2.1** Přidat atribut `complexity: str | None` do [profile_router.py](../src/mcp_prompt_broker/router/profile_router.py) `EnhancedMetadata`
  - Acceptance: Atribut je propagován z `ParsedMetadata`

- [ ] **1.2.2** Přidat atribut `prompt_length: int` do `EnhancedMetadata`
  - Acceptance: Atribut je dostupný přes `as_mutable()`

- [ ] **1.2.3** Upravit `ParsedMetadata.to_enhanced_metadata()` pro propagaci nových atributů
  - Acceptance: Komplexita a délka promptu jsou předány do EnhancedMetadata

---

## Phase 2: Router Extension (Est: 2 hours)

### 2.1 Configuration Constants

- [ ] **2.1.1** Vytvořit konfigurační soubor [complexity_config.py](../src/mcp_prompt_broker/router/complexity_config.py)
  - Acceptance: Obsahuje všechny konfigurační konstanty
  
  ```python
  # Prahy pro preferenci _complex variant
  COMPLEXITY_ROUTING_ENABLED = True
  COMPLEX_SUFFIX = "_complex"
  
  # Word count prahy
  WORD_COUNT_HIGH = 80      # > 80 slov = vysoká komplexita
  WORD_COUNT_MEDIUM = 40    # > 40 slov = střední komplexita
  
  # Keyword bonus prahy
  KEYWORD_BONUS_HIGH = 4    # >= 4 = vysoká komplexita
  KEYWORD_BONUS_MEDIUM = 2  # >= 2 = střední komplexita
  
  # Minimum score ratio pro přepnutí na _complex
  COMPLEX_VARIANT_MIN_SCORE_RATIO = 0.8
  ```

### 2.2 Profile Variant Discovery

- [ ] **2.2.1** Implementovat metodu `ProfileRouter._find_complex_variant()`
  - Input: `profile_name: str`
  - Output: `InstructionProfile | None`
  - Acceptance: Vrací `_complex` variantu pokud existuje, jinak None

- [ ] **2.2.2** Implementovat metodu `ProfileRouter._find_simple_variant()`
  - Input: `profile_name: str` (s `_complex` suffixem)
  - Output: `InstructionProfile | None`
  - Acceptance: Vrací základní variantu pokud existuje

- [ ] **2.2.3** Vytvořit index párových profilů při inicializaci routeru
  - Acceptance: `self._profile_pairs: Dict[str, str]` mapující base → complex

### 2.3 Complexity Preference Logic

- [ ] **2.3.1** Implementovat metodu `ProfileRouter._should_prefer_complex()`
  - Input: `metadata: EnhancedMetadata`
  - Output: `bool`
  - Acceptance: Vrací True pokud prompt splňuje kritéria pro komplexní profil

- [ ] **2.3.2** Implementovat metodu `ProfileRouter._should_prefer_simple()`
  - Input: `metadata: EnhancedMetadata`
  - Output: `bool`
  - Acceptance: Vrací True pro krátké/jednoduché prompty

### 2.4 Route Method Enhancement

- [ ] **2.4.1** Upravit `ProfileRouter.route()` pro aplikaci komplexitní preference
  - Acceptance: Po výběru nejlepšího profilu zkontroluje komplexitu
  - Acceptance: Pokud `_should_prefer_complex()` a existuje `_complex` varianta, přepne
  - Acceptance: Pokud `_should_prefer_simple()` a vybrán `_complex`, zkusí základní

- [ ] **2.4.2** Přidat `complexity_adjusted: bool` do `RoutingResult`
  - Acceptance: Indikuje zda byl profil upraven na základě komplexity

- [ ] **2.4.3** Přidat `original_profile: str | None` do `RoutingResult`
  - Acceptance: Obsahuje původní profil před úpravou (pro debugging)

---

## Phase 3: HybridRouter Extension (Est: 1 hour)

### 3.1 Integrate with HybridProfileRouter

- [ ] **3.1.1** Aplikovat komplexitní logiku do [hybrid_router.py](../src/mcp_prompt_broker/router/hybrid_router.py)
  - Acceptance: `HybridProfileRouter.route()` respektuje komplexitní preference

- [ ] **3.1.2** Rozšířit `HybridRoutingResult` o komplexitní metadata
  - Acceptance: Obsahuje `complexity_adjusted`, `original_profile`

---

## Phase 4: Configuration & Environment (Est: 30 min)

### 4.1 Environment Variables

- [ ] **4.1.1** Přidat ENV proměnnou `MCP_COMPLEXITY_ROUTING`
  - Values: `true`, `false`, `auto`
  - Default: `true`
  - Acceptance: Lze vypnout komplexitní routing

- [ ] **4.1.2** Přidat ENV proměnnou `MCP_COMPLEXITY_WORD_THRESHOLD`
  - Default: `60`
  - Acceptance: Konfigurovatelný práh počtu slov

### 4.2 Server Integration

- [ ] **4.2.1** Upravit [server.py](../src/mcp_prompt_broker/server.py) pro čtení ENV proměnných
  - Acceptance: Konfigurace je načtena při startu serveru

- [ ] **4.2.2** Přidat komplexitní info do response `get_profile`/`resolve_prompt`
  - Acceptance: Response obsahuje `complexity_routing` sekci

---

## Phase 5: Testing (Est: 1 hour)

### 5.1 Unit Tests

- [ ] **5.1.1** Vytvořit [test_complexity_routing.py](../tests/test_complexity_routing.py)
  - Acceptance: 100% pokrytí nové funkcionality

- [ ] **5.1.2** Test case: Krátký prompt → základní profil
  - Input: "Vytvoř funkci pro sčítání" (5 slov)
  - Expected: `python_code_generation` (ne `_complex`)

- [ ] **5.1.3** Test case: Dlouhý prompt → complex profil
  - Input: 100+ slov popis komplexní migrace
  - Expected: Preferuje `_complex` variantu

- [ ] **5.1.4** Test case: Krátký prompt s complexity keywords → complex profil
  - Input: "Navrhni enterprise microservices architekturu" (4 slova, 2 keywords)
  - Expected: Preferuje `_complex` variantu

- [ ] **5.1.5** Test case: Profil bez _complex varianty
  - Expected: Vrací původní profil bez chyby

- [ ] **5.1.6** Test case: ENV disable
  - Setup: `MCP_COMPLEXITY_ROUTING=false`
  - Expected: Komplexitní routing je vypnutý

### 5.2 Integration Tests

- [ ] **5.2.1** E2E test přes MCP server tools
  - Acceptance: `get_profile` vrací správný profil podle komplexity

- [ ] **5.2.2** Test kompatibility s HybridRouter
  - Acceptance: Sémantický scoring + komplexitní preference fungují společně

---

## Phase 6: Documentation (Est: 30 min)

### 6.1 Code Documentation

- [ ] **6.1.1** Přidat docstringy ke všem novým metodám
  - Acceptance: Google-style docstrings s příklady

- [ ] **6.1.2** Aktualizovat module-level docstring v `profile_router.py`
  - Acceptance: Popisuje komplexitní routing

### 6.2 User Documentation

- [ ] **6.2.1** Aktualizovat [USER_GUIDE.md](../docs/USER_GUIDE.md)
  - Sekce: "Complexity-Based Profile Selection"
  - Acceptance: Vysvětluje chování a konfiguraci

- [ ] **6.2.2** Aktualizovat [DEVELOPER_GUIDE.md](../docs/DEVELOPER_GUIDE.md)
  - Sekce: "Complexity Routing Architecture"
  - Acceptance: Obsahuje diagram a API dokumentaci

### 6.3 Profile Documentation

- [ ] **6.3.1** Aktualizovat README.md
  - Acceptance: Zmiňuje automatické přepínání profilů

---

## Rollback Procedure

V případě problémů:

1. Nastavit `MCP_COMPLEXITY_ROUTING=false`
2. Restart MCP serveru
3. Verify: Komplexitní routing je vypnutý

---

## Definition of Done

- [ ] Všechny unit testy projdou
- [ ] Všechny integration testy projdou  
- [ ] Lint a type check bez chyb
- [ ] Dokumentace aktualizována
- [ ] Code review schválen
- [ ] Funkčnost ověřena na produkčních promptech

---

## Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| `ParsedMetadata` | ✅ Existuje | Rozšířit o `prompt_length` |
| `EnhancedMetadata` | ✅ Existuje | Rozšířit o `complexity` |
| `ProfileRouter` | ✅ Existuje | Přidat nové metody |
| Párové profily | ✅ 9 párů | Připraveny k použití |

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Falešně pozitivní komplexita | Medium | Low | Kombinovat délku s keywords |
| Breaking change v API | Low | Medium | Přidat jako opt-in s default=true |
| Performance overhead | Low | Low | Index párů při inicializaci |
| Nekonzistentní chování | Medium | Medium | Extensive testing |
