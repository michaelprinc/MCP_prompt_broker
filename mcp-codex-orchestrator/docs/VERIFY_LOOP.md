# Verify Loop Documentation

MCP Codex Orchestrator v2.0 zavádí automatický verify loop pro validaci změn provedených Codex CLI.

## Přehled

Verify loop automaticky spouští:
1. **Testy** (pytest) - ověření funkčnosti
2. **Lint** (ruff/flake8) - kontrola kvality kódu
3. **Build** (volitelně) - ověření sestavení projektu

## Konfigurace

### Základní použití

```json
{
  "prompt": "Implementuj funkci pro parsování JSON",
  "verify": true
}
```

### Pokročilá konfigurace

```python
from mcp_codex_orchestrator.verify.verify_loop import VerifyConfig, VerifyLoop

config = VerifyConfig(
    run_tests=True,
    run_lint=True,
    run_build=False,
    max_iterations=3,
    test_command="pytest -v --tb=short",
    lint_command="ruff check .",
    build_command=None,
)

loop = VerifyLoop(
    workspace_path="/path/to/workspace",
    config=config,
)

result = await loop.run()
```

## Komponenty

### TestRunner

Spouští pytest a parsuje výsledky:

```python
from mcp_codex_orchestrator.verify.test_runner import TestRunner

runner = TestRunner(workspace_path="/path/to/workspace")
result = await runner.run()

print(f"Passed: {result.passed}")
print(f"Failed: {result.failed}")
print(f"Errors: {result.errors}")
```

**Výstup:**
```json
{
  "status": "passed",
  "passed": 15,
  "failed": 0,
  "skipped": 2,
  "duration": 3.45,
  "errors": []
}
```

### LintChecker

Kontroluje kvalitu kódu pomocí ruff nebo flake8:

```python
from mcp_codex_orchestrator.verify.lint_checker import LintChecker

checker = LintChecker(workspace_path="/path/to/workspace")

# Kontrola
result = await checker.check()

# Automatická oprava (pokud je podporována)
fixed = await checker.fix()
```

**Výstup:**
```json
{
  "status": "warnings",
  "errors": 0,
  "warnings": 5,
  "issues": [
    {
      "file": "src/main.py",
      "line": 10,
      "code": "F401",
      "message": "imported but unused"
    }
  ]
}
```

### BuildRunner

Volitelné spouštění build příkazů:

```python
from mcp_codex_orchestrator.verify.build_runner import BuildRunner

runner = BuildRunner(workspace_path="/path/to/workspace")

# Automatická detekce build příkazu
command = runner.detect_build_command()  # "python setup.py build" nebo "npm run build"

# Spuštění buildu
result = await runner.run()
```

## Workflow

```
┌─────────────────────────────────────────────────────────┐
│                      Codex Run                          │
├─────────────────────────────────────────────────────────┤
│  1. Execute prompt                                       │
│  2. Apply file changes                                   │
│  3. IF verify=true:                                     │
│     ┌─────────────────────────────────────────────────┐ │
│     │              Verify Loop                        │ │
│     ├─────────────────────────────────────────────────┤ │
│     │  Iteration 1:                                   │ │
│     │    → Run tests                                  │ │
│     │    → Run lint                                   │ │
│     │    → IF all pass: DONE ✅                       │ │
│     │    → IF fail: Continue to Iteration 2          │ │
│     ├─────────────────────────────────────────────────┤ │
│     │  Iteration 2-N:                                 │ │
│     │    → Collect errors                             │ │
│     │    → (Optional) Auto-fix lint                   │ │
│     │    → Re-run checks                              │ │
│     │    → IF max_iterations reached: Report errors   │ │
│     └─────────────────────────────────────────────────┘ │
│  4. Return result with verify_result                    │
└─────────────────────────────────────────────────────────┘
```

## VerifyResult

```python
from mcp_codex_orchestrator.verify.verify_result import VerifyResult, VerifyStatus

# Úspěšný výsledek
result = VerifyResult(
    status=VerifyStatus.PASSED,
    passed=10,
    failed=0,
    iterations=1,
)

# Neúspěšný výsledek
result = VerifyResult(
    status=VerifyStatus.FAILED,
    passed=8,
    failed=2,
    iterations=3,
    errors=[
        "test_api.py::test_validation FAILED - AssertionError",
        "test_api.py::test_edge_case FAILED - TypeError",
    ],
)
```

### VerifyStatus Enum

| Status | Popis |
|--------|-------|
| `PASSED` | Všechny kontroly prošly |
| `FAILED` | Některé kontroly selhaly |
| `SKIPPED` | Kontroly byly přeskočeny (např. žádné testy) |
| `ERROR` | Chyba při spouštění kontrol |

## Auto-Fix

Verify loop může automaticky opravit některé problémy:

```python
config = VerifyConfig(
    run_lint=True,
    auto_fix_lint=True,  # Automaticky spustí "ruff --fix"
)
```

**Automaticky opravitelné problémy:**
- Nepoužité importy
- Formátování (trailing whitespace, atd.)
- Jednoduché syntaktické problémy

**Nelze automaticky opravit:**
- Selhávající testy
- Logické chyby
- Komplexní refactoring

## Integrace s MCP Response

Výsledek verify loop je zahrnut v MCP response:

```json
{
  "runId": "abc123",
  "status": "success",
  "output": {
    "summary": "Implemented JSON parser",
    "filesChanged": ["src/parser.py", "tests/test_parser.py"],
    "verifyResult": {
      "status": "passed",
      "iterations": 1,
      "tests": {
        "passed": 5,
        "failed": 0
      },
      "lint": {
        "errors": 0,
        "warnings": 2
      }
    }
  }
}
```

## Best Practices

### 1. Vždy povolte verify pro produkční kód

```json
{
  "prompt": "...",
  "verify": true
}
```

### 2. Nastavte rozumný max_iterations

```python
config = VerifyConfig(
    max_iterations=3,  # Default, dostatečné pro většinu případů
)
```

### 3. Používejte specifické test příkazy

```python
config = VerifyConfig(
    test_command="pytest tests/unit -v --tb=short",  # Pouze unit testy
)
```

### 4. Kombinujte s security_mode

```json
{
  "prompt": "...",
  "security_mode": "workspace_write",
  "verify": true
}
```

## Troubleshooting

### "No tests found"

**Příčina:** pytest nenašel žádné testy

**Řešení:**
1. Ověřte, že existuje `tests/` adresář
2. Ověřte, že test soubory začínají `test_`
3. Zkontrolujte `pytest.ini` nebo `pyproject.toml`

### Lint errors po úspěšných testech

**Příčina:** Kód prošel testy, ale má style issues

**Řešení:**
```python
config = VerifyConfig(
    auto_fix_lint=True,
)
```

### Timeout při verify loop

**Příčina:** Testy trvají příliš dlouho

**Řešení:**
1. Omezte scope testů:
   ```python
   config = VerifyConfig(
       test_command="pytest tests/unit -x",  # Stop on first failure
   )
   ```
2. Zvyšte timeout:
   ```json
   {
     "timeout": 600
   }
   ```

---

## Reference

- [pytest documentation](https://docs.pytest.org/)
- [ruff documentation](https://docs.astral.sh/ruff/)
- [MCP Codex Orchestrator README](../README.md)
