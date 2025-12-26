---
name: codex_orchestrator_integration_template
short_description: Template for profiles integrating MCP codex-orchestrator server for automated code generation
extends: null
default_score: 0
fallback: false

required:
  context_tags: ["codex_orchestrator", "mcp_integration"]

weights:
  priority:
    high: 2
    critical: 3
  complexity:
    medium: 2
    high: 3
  domain:
    # Add your domain weights here
    python: 3
    code_generation: 4
  keywords:
    # Add your profile-specific keywords here
    codex: 10
    codex orchestrator: 15
    mcp codex: 12
---

# [Profile Name] with MCP Codex-Orchestrator Integration

## Instructions

This template demonstrates how to integrate the MCP `codex-orchestrator` server into a Copilot profile. The orchestrator provides Docker-isolated execution of OpenAI Codex CLI with structured responses and audit trails.

### Prerequisites

Before using this profile, ensure:

1. **MCP Server Running**: The `codex-orchestrator` server must be available
2. **Docker Environment**: Docker must be installed and running
3. **Codex CLI Authorization Configured**: Codex CLI authorization must be set in the environment

### MCP Tool Reference

The `codex-orchestrator` exposes the `codex_run` tool:

```json
{
  "name": "codex_run",
  "description": "Spustí OpenAI Codex CLI v izolovaném Docker kontejneru.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "prompt": {
        "type": "string",
        "description": "Zadání pro Codex CLI - co má udělat"
      },
      "mode": {
        "type": "string",
        "enum": ["full-auto", "suggest", "ask"],
        "default": "full-auto",
        "description": "Režim běhu Codex CLI"
      },
      "repo": {
        "type": "string",
        "description": "Cesta k repository (default: aktuální workspace)"
      },
      "working_dir": {
        "type": "string",
        "description": "Working directory uvnitř repository"
      },
      "timeout": {
        "type": "integer",
        "default": 300,
        "description": "Timeout v sekundách"
      },
      "env_vars": {
        "type": "object",
        "additionalProperties": {"type": "string"},
        "description": "Extra environment variables"
      }
    },
    "required": ["prompt"]
  }
}
```

## Integration Pattern

### 1. Basic Invocation

For simple code generation tasks:

```json
// Use mcp_codex-orchest_codex_run tool
{
  "prompt": "Your task description here",
  "mode": "full-auto",
  "timeout": 180
}
```

### 2. With Working Directory

When you need to target a specific folder:

```json
{
  "prompt": "Create a module with utility functions",
  "mode": "full-auto",
  "working_dir": "src/utils",
  "timeout": 240
}
```

### 3. With Environment Variables

For tasks requiring specific configuration:

```json
{
  "prompt": "Set up a test suite",
  "mode": "full-auto",
  "timeout": 300,
  "env_vars": {
    "PYTHON_VERSION": "3.11",
    "TEST_FRAMEWORK": "pytest"
  }
}
```

### 4. Suggest Mode (Review Only)

For code review or planning without execution:

```json
{
  "prompt": "Review this module for security issues",
  "mode": "suggest",
  "timeout": 120
}
```

## Response Handling

The `codex_run` tool returns a structured response:

```json
{
  "run_id": "uuid-of-the-run",
  "status": "success|error|timeout",
  "output": "Generated code or response",
  "error": "Error message if any",
  "duration_seconds": 45.2,
  "files_changed": ["path/to/file1.py", "path/to/file2.py"]
}
```

### Handling Different Statuses

```markdown
**On Success:**
- Review the `output` and `files_changed`
- Validate code quality and correctness
- Run tests if applicable

**On Error:**
- Check the `error` field for details
- Refine the prompt and retry
- Consider using `suggest` mode first

**On Timeout:**
- Increase the `timeout` value
- Break the task into smaller chunks
- Check if the task is too complex
```

## Workflow Template

### Step 1: Analyze Requirements

Before invoking Codex:

```markdown
**Task Analysis:**
- Functional requirements: [list]
- Non-functional requirements: [list]
- Expected output: [description]
- Quality criteria: [list]
```

### Step 2: Create Precise Prompt

```json
{
  "prompt": "[CONTEXT]\nProject: [name]\nArchitecture: [patterns]\nDependencies: [list]\n\n[TASK]\n[Detailed task description]\n\n[REQUIREMENTS]\n1. [Requirement 1]\n2. [Requirement 2]\n\n[QUALITY STANDARDS]\n- Type hints required\n- Docstrings with examples\n- Error handling",
  "mode": "full-auto",
  "timeout": 300
}
```

### Step 3: Invoke and Audit

1. Call `mcp_codex-orchest_codex_run` with the prompt
2. Review the response status and output
3. Validate against quality criteria
4. Iterate if necessary

### Step 4: Report Progress

```markdown
**Codex Run Summary:**
- Run ID: [run_id]
- Status: [status]
- Duration: [duration_seconds]s
- Files Changed: [files_changed]
- Audit Result: [PASS/NEEDS_REVISION]
```

## Security Guidelines

1. **Docker Isolation**: All runs execute in isolated containers
2. **No Secrets in Prompts**: Never include API keys or passwords
3. **Review Before Deploy**: Always review generated code
4. **Suggest Mode for Sensitive Operations**: Use `suggest` for security-critical tasks
5. **Audit Trail**: Use `run_id` for tracking and debugging

## Customization Points

When creating a new profile based on this template:

1. **Update `name`**: Set a unique profile name
2. **Update `short_description`**: Describe the profile's purpose
3. **Set `extends`**: Reference a parent profile if applicable
4. **Configure `weights`**: Adjust keyword weights for routing
5. **Add Domain-Specific Instructions**: Customize the workflow for your use case

## Example: Custom Profile

```yaml
---
name: my_custom_codex_profile
short_description: Custom profile for [specific use case] with Codex
extends: codex_cli
default_score: 0

required:
  context_tags: ["codex_orchestrator", "my_domain"]

weights:
  keywords:
    my keyword: 10
    codex: 8
---

# My Custom Codex Profile

## Instructions

[Your custom instructions here]

### Workflow

1. [Step 1]
2. [Step 2]
3. Invoke Codex via MCP:
   ```json
   {
     "prompt": "[Your template]",
     "mode": "full-auto"
   }
   ```
4. [Audit and iterate]
```

## Notes

- This template is designed for profiles that delegate to MCP `codex-orchestrator`
- For direct code generation without Codex, use standard Copilot profiles
- Combine with other profiles using `extends` for layered functionality
