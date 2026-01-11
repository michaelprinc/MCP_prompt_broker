---
name: codex_cli
short_description: Integration profile for Codex via MCP delegated-task-runner server with Docker isolation, timeout management, and structured responses
extends: null
default_score: 0
fallback: false

utterances:
  - "Use Codex CLI to implement this feature"
  - "Run this task with the Codex orchestrator"
  - "Execute code generation using Codex in Docker"
  - "Delegate this implementation to Codex"
  - "Use MCP Codex server for this coding task"
  - "Spusť Codex CLI pro tento úkol"
  - "Let Codex handle the autonomous implementation"
utterance_threshold: 0.75
min_match_ratio: 0.3

required:
  context_tags: ["codex_cli", "mcp_integration", "codex_orchestrator"]

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
    codex orchestrator: 15
    mcp server: 8
    docker isolation: 6
    timeout: 2
    sandbox: 4
---

# Codex MCP Orchestrator Integration Profile

## Instructions

This profile provides guidelines for **integration with OpenAI Codex via the MCP `delegated-task-runner` server**. The orchestrator runs Codex CLI in isolated Docker containers, providing safety, timeout management, and structured responses.

Use this profile when:

- Delegating code generation or modification tasks to Codex
- Running autonomous coding tasks with proper isolation
- Managing complex multi-step implementations via Codex
- Requiring structured, auditable Codex outputs

### Core Principles

1. **Docker Isolation**: All Codex runs execute in isolated Docker containers
2. **MCP Protocol**: Use the `codex_run` tool via MCP for structured communication
3. **Timeout Management**: Configure appropriate timeouts (default: 600s)
4. **Structured Responses**: Receive `CodexRunResult` with status, outputs, and metrics
5. **Audit Trail**: All runs are logged with unique `run_id` for traceability

### MCP Tool: `codex_run`

The `delegated-task-runner` MCP server exposes the `codex_run` tool with the following schema:

```json
{
  "name": "codex_run",
  "description": "Spusti OpenAI Codex CLI v izolovanem Docker kontejneru.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "task": {
        "type": "string",
        "description": "Zadani pro Codex CLI - co ma udelat"
      },
      "execution_mode": {
        "type": "string",
        "enum": ["full-auto", "suggest", "ask"],
        "default": "full-auto",
        "description": "Rezim behu Codex CLI"
      },
      "repository_path": {
        "type": "string",
        "description": "Cesta k repository (default: aktualni workspace)"
      },
      "working_directory": {
        "type": "string",
        "description": "Working directory uvnitr repository"
      },
      "timeout_seconds": {
        "type": "integer",
        "default": 600,
        "description": "Timeout v sekundach"
      },
      "environment_variables": {
        "type": "object",
        "additionalProperties": {"type": "string"},
        "description": "Extra environment variables"
      },
      "security_mode": {
        "type": "string",
        "enum": ["readonly", "workspace_write", "full_access"],
        "default": "workspace_write",
        "description": "Security mode pro sandbox izolaci"
      },
      "intent": {
        "type": "string",
        "enum": ["code_change", "analysis", "refactor", "test_fix"],
        "description": "Routing hint pro delegovani ulohy"
      },
      "verify": {
        "type": "boolean",
        "default": false,
        "description": "Automaticky spustit verify loop (testy, lint)"
      },
      "output_schema": {
        "type": "string",
        "description": "Nazev JSON schematu pro validaci vystupu"
      },
      "json_output": {
        "type": "boolean",
        "default": true,
        "description": "Pouzit JSONL vystup z Codex CLI"
      }
    },
    "required": ["task"]
  }
}
```

### Integration Flow

1. **Prepare prompt**: Craft a precise, context-rich prompt for Codex
2. **Call MCP tool**: Invoke `mcp_delegated-task-runner_codex_run` with parameters
3. **Receive result**: Get structured `CodexRunResult` with status and outputs
4. **Audit output**: Review generated code for correctness and quality
5. **Iterate if needed**: Refine prompt and re-run for improvements

### Example Usage

Instead of calling Codex CLI directly via subprocess, use the MCP tool:

```python
# OLD WAY (deprecated - do not use):
# result = subprocess.run(["codex", prompt], ...)

# NEW WAY - via MCP delegated-task-runner:
# Use the mcp_delegated-task-runner_codex_run tool with these parameters:
{
    "task": "Create a Python function that calculates fibonacci numbers with memoization",
    "execution_mode": "full-auto",
    "timeout_seconds": 600,
    "environment_variables": {
        "PYTHON_VERSION": "3.11"
    }
}
```

### Modes of Operation

| Mode | Description | Use Case |
|------|-------------|----------|
| `full-auto` | Codex executes autonomously | Simple, well-defined tasks |
| `suggest` | Codex suggests but doesn't execute | Code review, planning |
| `ask` | Interactive mode with confirmation | Complex, risky operations |

## Checklist

- [ ] MCP `delegated-task-runner` server is running and accessible
- [ ] Docker environment is available for container isolation
- [ ] Appropriate timeout configured for task complexity
- [ ] Prompt is specific and includes context
- [ ] Output validation implemented after receiving results
- [ ] Fallback behavior defined for failures
- [ ] Error handling for MCP communication issues

## Security Guidelines

- Codex runs in isolated Docker containers (no host access)
- Sensitive data should not be included in prompts
- Review all generated code before deployment
- Use `suggest` mode for security-critical operations
- Monitor `run_id` for audit trail

## Response Structure

The `codex_run` tool returns a structured response:

```json
{
  "run_id": "uuid-of-the-run",
  "status": "success|error|timeout",
  "output": "Generated code or response",
  "error": "Error message if any",
  "duration_seconds": 45.2,
  "files_changed": ["src/module.py", "tests/test_module.py"]
}
```

## Notes

- This profile uses the MCP `delegated-task-runner` server instead of direct CLI calls
- For complex Python projects, use `python_code_generation_complex_with_codex` profile
- Ensure the MCP server is configured in your VS Code settings or MCP configuration
