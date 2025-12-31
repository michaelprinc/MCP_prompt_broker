# Report: Vylepšení profilů dokumentace 3LEVEL a 4LEVEL

**Datum:** 2025-01-15
**Autor:** GitHub Copilot
**Status:** ✅ DOKONČENO

---

## Souhrn

Oba dokumentační profily (3LEVEL a 4LEVEL) byly úspěšně aktualizovány s podporou modulární dokumentace, limity délky souborů a iterativním LLM workflow.

## Implementované změny

### 1. Modulární dokumentace (Hub and Spoke model)

**Princip:**
- **HUB dokumenty** (user-guide.md, developer-guide.md) obsahují navigaci a odkazy
- **SPOKE dokumenty** v podsložkách obsahují detailní obsah
- Struktura: `docs/[hub].md` → `docs/[hub]/[spoke].md`

### 2. Limity délky souborů

| Profil | Max řádků | Preferovaná délka | HUB dokumenty |
|--------|-----------|-------------------|---------------|
| 3LEVEL | 500 | 300-400 | ≤150 řádků |
| 4LEVEL | 800 | 500-600 | ≤200 řádků |

### 3. Rozdíly mezi profily

| Aspekt | 3LEVEL (STRUČNOST) | 4LEVEL (ÚPLNOST) |
|--------|-------------------|------------------|
| Max délka | 500 řádků | 800 řádků |
| Zanoření | 2 úrovně max | 3 úrovně max |
| Stakeholdeři | 3-4 skupiny | 5-7 skupin |
| Additional/ | Ne | Ano (ops, security, testing, compliance) |
| Šablony | Kompaktní | Detailní s metadata |

### 4. Aktualizované soubory

1. ✅ `documentation_3level.md` - verze 2.0
2. ✅ `documentation_4level.md` - verze 2.0

---

## Původní návrh (archivováno)

```
┌─────────────────────────────────────────────────────────────┐
│                 ITERATIVNÍ DOKUMENTAČNÍ PROCES              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  FÁZE 1: ANALÝZA PROJEKTU                                   │
│  ├─ Identifikuj klíčové moduly/komponenty                   │
│  ├─ Odhadni komplexitu každé části                          │
│  └─ Urči cílové publikum pro každou sekci                   │
│                                                             │
│  FÁZE 2: NÁVRH STRUKTURY                                    │
│  ├─ Navrhni hierarchii dokumentů                            │
│  ├─ Definuj propojení (linky) mezi dokumenty                │
│  └─ Ověř, že žádný soubor nepřesáhne limit                  │
│                                                             │
│  FÁZE 3: GENEROVÁNÍ OBSAHU                                  │
│  ├─ Vytvoř hlavní dokumenty (hub pages)                     │
│  ├─ Vytvoř podřízené dokumenty (detail pages)               │
│  └─ Přidej navigační elementy                               │
│                                                             │
│  FÁZE 4: VALIDACE                                           │
│  ├─ Zkontroluj všechny linky                                │
│  ├─ Ověř konzistenci terminologie                           │
│  └─ Validuj délku souborů                                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Pravidla pro rozdělení souborů

| Metrika | 3LEVEL (stručnost) | 4LEVEL (úplnost) |
|---------|-------------------|------------------|
| Max řádků/soubor | 500 | 800 |
| Preferovaná délka | 300-400 | 500-600 |
| Minimální sekce pro split | 3+ podsekce | 2+ podsekce |
| Hloubka zanoření | 2 úrovně | 3 úrovně |

### 2.3 Struktura "Hub and Spoke" dokumentů

**Hub dokument (hlavní):**
```markdown
# [Název hlavního dokumentu]

## Přehled
[Stručný úvod - max 10 řádků]

## Obsah této sekce

| Dokument | Popis | Audience |
|----------|-------|----------|
| [Subsekce 1](./subsekce-1.md) | [popis] | [kdo] |
| [Subsekce 2](./subsekce-2.md) | [popis] | [kdo] |

## Quick Reference
[Nejdůležitější informace pro rychlý přístup]

## Další kroky
- [Link na související dokument]
```

**Spoke dokument (detail):**
```markdown
# [Název detailního dokumentu]

> 📍 **Navigace:** [Hlavní dokument](../hlavni.md) > Tato sekce

## [Obsah]

[Detailní obsah]

---

**Viz také:**
- [Související dokument 1](./related-1.md)
- [Zpět na přehled](../hlavni.md)
```

### 2.4 Kritéria pro vytvoření poddokumentu

```
VYTVOŘIT NOVÝ SOUBOR KDYŽ:
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  ✅ Sekce přesahuje 150 řádků (3LEVEL) / 200 řádků (4LEVEL) │
│  ✅ Sekce má 3+ logické podsekce                            │
│  ✅ Sekce má odlišné publikum než zbytek dokumentu          │
│  ✅ Sekce se často aktualizuje nezávisle                    │
│  ✅ Sekce obsahuje referenční materiál (API, config)        │
│                                                             │
│  PONECHAT V HLAVNÍM SOUBORU KDYŽ:                          │
│  ❌ Sekce je < 50 řádků                                     │
│  ❌ Sekce je kritická pro pochopení kontextu                │
│  ❌ Sekce by ztratila smysl bez okolního textu              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2.5 Best Practices pro dokumentaci

#### Navigace a orientace
- Každý dokument začíná breadcrumb navigací
- Každý dokument končí "Viz také" sekcí
- Hlavní dokumenty obsahují tabulku obsahu s popisem

#### Konzistence
- Jednotná terminologie napříč dokumenty
- Konzistentní formátování nadpisů
- Shodné emoji/ikony pro stejné typy obsahu

#### Údržba
- Datum poslední aktualizace v záhlaví
- Označení vlastníka dokumentu
- Status dokumentu (Draft/Review/Stable)

#### Čitelnost
- Jeden koncept = jeden odstavec
- Tabulky pro strukturovaná data
- Code snippets pro technické detaily
- Diagramy pro architekturu a flows

---

## 3. Konkrétní změny pro 3LEVEL

### 3.1 Nová struktura

```
projekt/
├── README.md                           # Hub: Exekutivní shrnutí
├── docs/
│   ├── user-guide.md                  # Hub: Uživatelská příručka
│   │   └── user-guide/                # Spoke: Podsekce (při komplexitě)
│   │       ├── getting-started.md
│   │       ├── common-tasks.md
│   │       └── troubleshooting.md
│   │
│   ├── developer-guide.md             # Hub: Vývojářská příručka
│   │   └── developer-guide/           # Spoke: Podsekce (při komplexitě)
│   │       ├── setup.md
│   │       ├── modules/
│   │       │   ├── core.md
│   │       │   └── api.md
│   │       └── testing.md
│   │
│   ├── architecture.md                # Hub: Architektura
│   └── additional/                    # Další dokumenty
```

### 3.2 Klíčové principy pro 3LEVEL
- **Stručnost:** Max 500 řádků/soubor, preferovaně 300-400
- **Pragmatismus:** Split jen když je opravdu potřeba
- **Rychlost:** Čtenář najde odpověď do 2 kliknutí

---

## 4. Konkrétní změny pro 4LEVEL

### 4.1 Nová struktura

```
projekt/
├── README.md                           # Hub: Exekutivní shrnutí
├── docs/
│   ├── user-guide.md                  # Hub: Uživatelská příručka
│   │   └── user-guide/                # Spoke: Podsekce
│   │       ├── getting-started.md
│   │       ├── installation/
│   │       │   ├── windows.md
│   │       │   ├── linux.md
│   │       │   └── docker.md
│   │       ├── features/
│   │       │   ├── feature-a.md
│   │       │   └── feature-b.md
│   │       ├── troubleshooting.md
│   │       └── checklist.md
│   │
│   ├── developer-guide.md             # Hub: Vývojářská příručka
│   │   └── developer-guide/           # Spoke: Podsekce
│   │       ├── setup.md
│   │       ├── architecture/
│   │       │   ├── overview.md
│   │       │   ├── data-flow.md
│   │       │   └── components.md
│   │       ├── modules/
│   │       │   ├── index.md
│   │       │   ├── [modul-1].md
│   │       │   └── [modul-2].md
│   │       ├── api/
│   │       │   ├── rest.md
│   │       │   └── internal.md
│   │       └── testing/
│   │           ├── unit.md
│   │           ├── integration.md
│   │           └── e2e.md
│   │
│   ├── architecture.md                # Hub: Architektura
│   └── additional/
│       ├── operations/
│       ├── security/
│       ├── testing/
│       └── compliance/
```

### 4.2 Klíčové principy pro 4LEVEL
- **Úplnost:** Pokryj všechny aspekty, ale rozděl do souborů
- **Hloubka:** Podsložky pro komplexní témata
- **Navigace:** Silná provázanost mezi dokumenty

---

## 5. Implementační plán

### Krok 1: Aktualizovat `documentation_3level.md`
- [ ] Přidat iterativní workflow
- [ ] Přidat pravidla pro split souborů (limit 500 řádků)
- [ ] Přidat šablony pro hub/spoke dokumenty
- [ ] Přidat best practices sekci

### Krok 2: Aktualizovat `documentation_4level.md`
- [ ] Přidat iterativní workflow (rozšířený)
- [ ] Přidat pravidla pro split souborů (limit 800 řádků)
- [ ] Přidat šablony pro hub/spoke dokumenty s vyšší hloubkou
- [ ] Přidat best practices sekci
- [ ] Přidat příklady modulární dokumentace

---

## 6. Očekávané výstupy

Po implementaci bude LLM schopen:

1. **Analyzovat projekt** a rozhodnout o komplexitě dokumentace
2. **Navrhnout strukturu** s ohledem na limity délky souborů
3. **Generovat propojené dokumenty** s konzistentní navigací
4. **Validovat** výslednou dokumentaci

---

**Připraveno k implementaci.**
