---
name: codex_cli
short_description: Integration profile for safe Codex CLI invocation, input/output sanitization, and fallback behavior
extends: null
default_score: 0
fallback: false

required:
  context_tags: ["codex_cli", "cli_integration"]

weights:
  priority:
    high: 2
    critical: 3
  complexity:
    medium: 2
    high: 3
  domain:
    engineering: 3
    python: 3
    code_generation: 4
  keywords:
    codex cli: 12
    codex: 10
    cli integration: 6
    subprocess: 4
    external tool: 4
    timeout: 2
    sandbox: 4
---

# Codex CLI Integration Profile

## Instructions

This profile provides guidelines for **safe integration with Codex CLI** as an external tool. Use this profile when:

- Calling Codex CLI from within an integration layer
- Managing timeouts, sandboxing, and output validation
- Implementing fallback behavior for CLI failures

### Core Principles

1. **Security First**: Never execute CLI with unverified parameters without sandboxing
2. **Timeout Management**: Always set reasonable timeouts (default: 30s)
3. **Output Validation**: Validate and sanitize all CLI outputs before use
4. **Environment Configuration**: Use environment variables for CLI paths
5. **Logging**: Log only meta-information, redact sensitive output parts

### Integration Flow

1. Receive user prompt and normalize (remove binary or dangerous sequences)
2. Call `run_codex_cli(prompt, timeout=30, env=...)` in integration layer
3. If CLI returns error or timeout, use fallback (e.g., error response with suggested fix)
4. Validate output (syntax check, length limits) before passing to user

### Example Usage

```python
import subprocess
import os

def run_codex_cli(prompt: str, timeout: int = 30) -> dict:
    """Run Codex CLI with safety measures."""
    cli_cmd = os.environ.get("CODEX_CLI_CMD", "codex-cli")
    
    try:
        result = subprocess.run(
            [cli_cmd, prompt],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return {"code": result.stdout, "error": result.stderr}
    except subprocess.TimeoutExpired:
        return {"error": "timeout", "timed_out": True}
    except Exception as e:
        return {"error": str(e)}
```

## Checklist

- [ ] `CODEX_CLI_CMD` configurable via environment
- [ ] Timeout implemented and tested
- [ ] Output limited and sanitized
- [ ] Unit test for mocked subprocess calls
- [ ] Document risks and rollback steps
- [ ] Fallback behavior defined
- [ ] Error handling complete

## Security Guidelines

- Never run CLI with unverified parameters without sandbox
- Limit timeouts and output to maximum length
- Configure `CODEX_CLI_PATH` or `CODEX_CLI_CMD` via environment variables
- Log only meta-information, redact sensitive output parts

## Notes

- This profile assumes the server runs in an environment where CLI is available
- For complex Python projects, consider using `python_code_generation_complex_with_codex` profile instead
