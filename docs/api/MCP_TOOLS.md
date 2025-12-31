# MCP Tools - API Reference

> **Verze dokumentace:** 1.0.0  
> **Datum:** 31. prosince 2025  
> **Úroveň:** 4/4 - API Reference

---

## 📋 Obsah

1. [Přehled MCP Tools](#přehled-mcp-tools)
2. [MCP Prompt Broker Tools](#mcp-prompt-broker-tools)
3. [MCP Codex Orchestrator Tools](#mcp-codex-orchestrator-tools)
4. [Chybové stavy](#chybové-stavy)
5. [Příklady integrace](#příklady-integrace)

---

## Přehled MCP Tools

### Dostupné MCP servery

| Server | Tools | Popis |
|--------|-------|-------|
| `mcp-prompt-broker` | 9 | Inteligentní routing promptů |
| `mcp-codex-orchestrator` | 1 | Codex CLI orchestrace |

### MCP Protocol

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          MCP PROTOCOL OVERVIEW                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Transport: stdio (Standard Input/Output)                                   │
│  Format: JSON-RPC 2.0                                                       │
│                                                                             │
│  Request:                                                                   │
│  {                                                                          │
│    "jsonrpc": "2.0",                                                        │
│    "id": 1,                                                                 │
│    "method": "tools/call",                                                  │
│    "params": {                                                              │
│      "name": "tool_name",                                                   │
│      "arguments": { ... }                                                   │
│    }                                                                        │
│  }                                                                          │
│                                                                             │
│  Response:                                                                  │
│  {                                                                          │
│    "jsonrpc": "2.0",                                                        │
│    "id": 1,                                                                 │
│    "result": {                                                              │
│      "content": [{ "type": "text", "text": "..." }]                         │
│    }                                                                        │
│  }                                                                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## MCP Prompt Broker Tools

### 1. resolve_prompt

**Primární tool pro routing promptů k optimálním instrukcím.**

#### Signatura

```typescript
resolve_prompt(
  prompt: string,           // Povinný: Text promptu k analýze
  metadata?: object         // Volitelný: Metadata overrides
): RoutingResult
```

#### Input Schema

```json
{
  "type": "object",
  "properties": {
    "prompt": {
      "type": "string",
      "description": "The user's complete request text to analyze and route."
    },
    "metadata": {
      "type": "object",
      "description": "Optional metadata overrides (domain, capability, complexity).",
      "properties": {
        "domain": { "type": "string" },
        "capability": { "type": "string" },
        "complexity": { "type": "string", "enum": ["simple", "complex"] }
      }
    }
  },
  "required": ["prompt"]
}
```

#### Output Schema

```json
{
  "profile": {
    "name": "string",
    "instructions": "string",
    "required": {
      "context_tags": ["string"]
    },
    "weights": {
      "domain": { "string": "number" },
      "keywords": { "string": "number" },
      "priority": { "string": "number" },
      "complexity": { "string": "number" }
    },
    "default_score": "number",
    "fallback": "boolean"
  },
  "metadata": {
    "prompt": "string",
    "intent": "string",
    "domain": "string",
    "topics": ["string"],
    "sensitivity": "string",
    "safety_score": "number",
    "tone": "string",
    "complexity": "string"
  },
  "routing": {
    "score": "number",
    "consistency": "number"
  }
}
```

#### Příklad

```json
// Request
{
  "tool": "resolve_prompt",
  "arguments": {
    "prompt": "Debug my Python script that throws KeyError on line 42"
  }
}

// Response
{
  "profile": {
    "name": "technical_support",
    "instructions": "You are a technical support specialist focused on debugging...",
    "required": { "context_tags": ["debugging", "troubleshooting"] },
    "weights": {
      "domain": { "engineering": 4, "python": 3 },
      "keywords": { "debug": 5, "error": 4, "fix": 3 }
    },
    "default_score": 1,
    "fallback": false
  },
  "metadata": {
    "prompt": "Debug my Python script...",
    "intent": "debugging",
    "domain": "engineering",
    "topics": ["python", "debugging", "error_handling"],
    "sensitivity": "low",
    "complexity": "medium"
  },
  "routing": {
    "score": 24,
    "consistency": 87.5
  }
}
```

---

### 2. get_profile

**Alias pro resolve_prompt.**

#### Signatura

```typescript
get_profile(
  prompt: string,
  metadata?: object
): RoutingResult
```

Identické s `resolve_prompt`.

---

### 3. list_profiles

**Vrací seznam všech dostupných profilů.**

#### Signatura

```typescript
list_profiles(): ProfileList
```

#### Input Schema

```json
{
  "type": "object",
  "properties": {}
}
```

#### Output Schema

```json
{
  "profiles": [
    {
      "name": "string",
      "description": "string",
      "domains": ["string"],
      "capabilities": ["string"],
      "complexity": "string"
    }
  ],
  "count": "number"
}
```

#### Příklad

```json
// Request
{
  "tool": "list_profiles",
  "arguments": {}
}

// Response
{
  "profiles": [
    {
      "name": "technical_support",
      "description": "Profil pro technickou podporu a debugging",
      "domains": ["engineering", "debugging"],
      "capabilities": ["troubleshooting", "diagnostics"],
      "complexity": "simple"
    },
    {
      "name": "creative_brainstorm",
      "description": "Profil pro kreativní brainstorming",
      "domains": ["creative", "marketing"],
      "capabilities": ["ideation", "innovation"],
      "complexity": "simple"
    }
  ],
  "count": 45
}
```

---

### 4. get_checklist

**Vrací checklist pro konkrétní profil.**

#### Signatura

```typescript
get_checklist(
  profile_name: string    // Povinný: Název profilu
): Checklist
```

#### Input Schema

```json
{
  "type": "object",
  "properties": {
    "profile_name": {
      "type": "string",
      "description": "Name of the profile to get the checklist for."
    }
  },
  "required": ["profile_name"]
}
```

#### Output Schema

```json
{
  "profile_name": "string",
  "checklist": [
    {
      "item": "string",
      "completed": "boolean"
    }
  ]
}
```

#### Příklad

```json
// Request
{
  "tool": "get_checklist",
  "arguments": {
    "profile_name": "technical_support"
  }
}

// Response
{
  "profile_name": "technical_support",
  "checklist": [
    { "item": "Identifikovat typ chyby", "completed": false },
    { "item": "Reprodukovat problém", "completed": false },
    { "item": "Najít root cause", "completed": false },
    { "item": "Navrhnout řešení", "completed": false },
    { "item": "Ověřit opravu", "completed": false }
  ]
}
```

---

### 5. get_profile_metadata

**Vrací detailní metadata profilu.**

#### Signatura

```typescript
get_profile_metadata(
  profile_name: string
): ProfileMetadata
```

#### Input Schema

```json
{
  "type": "object",
  "properties": {
    "profile_name": {
      "type": "string",
      "description": "Name of the profile to get metadata for."
    }
  },
  "required": ["profile_name"]
}
```

#### Output Schema

```json
{
  "name": "string",
  "description": "string",
  "version": "string",
  "domains": ["string"],
  "capabilities": ["string"],
  "complexity": "string",
  "keywords": { "string": "number" },
  "required_context_tags": ["string"],
  "file_path": "string"
}
```

---

### 6. find_profiles_by_capability

**Hledá profily podle schopnosti.**

#### Signatura

```typescript
find_profiles_by_capability(
  capability: string
): ProfileList
```

#### Input Schema

```json
{
  "type": "object",
  "properties": {
    "capability": {
      "type": "string",
      "description": "The capability to search for (e.g., 'ideation', 'debugging')."
    }
  },
  "required": ["capability"]
}
```

#### Příklad

```json
// Request
{
  "tool": "find_profiles_by_capability",
  "arguments": {
    "capability": "debugging"
  }
}

// Response
{
  "profiles": [
    { "name": "technical_support", "match_score": 1.0 },
    { "name": "python_code_generation", "match_score": 0.7 },
    { "name": "llm_behavior_debugger", "match_score": 0.9 }
  ],
  "count": 3
}
```

---

### 7. find_profiles_by_domain

**Hledá profily podle domény.**

#### Signatura

```typescript
find_profiles_by_domain(
  domain: string
): ProfileList
```

#### Input Schema

```json
{
  "type": "object",
  "properties": {
    "domain": {
      "type": "string",
      "description": "The domain to search for (e.g., 'healthcare', 'engineering')."
    }
  },
  "required": ["domain"]
}
```

---

### 8. get_registry_summary

**Vrací souhrn centrálního registru.**

#### Signatura

```typescript
get_registry_summary(): RegistrySummary
```

#### Input Schema

```json
{
  "type": "object",
  "properties": {}
}
```

#### Output Schema

```json
{
  "total_profiles": "number",
  "domains_covered": ["string"],
  "capabilities_covered": ["string"],
  "complexity_distribution": {
    "simple": "number",
    "complex": "number"
  },
  "last_updated": "string"
}
```

#### Příklad

```json
// Response
{
  "total_profiles": 45,
  "domains_covered": [
    "engineering", "healthcare", "finance", "creative",
    "documentation", "security", "devops", "ml"
  ],
  "capabilities_covered": [
    "debugging", "ideation", "compliance", "code_review",
    "testing", "documentation", "optimization"
  ],
  "complexity_distribution": {
    "simple": 28,
    "complex": 17
  },
  "last_updated": "2025-12-31T10:00:00Z"
}
```

---

### 9. reload_profiles

**Hot-reload profilů bez restartu serveru.**

#### Signatura

```typescript
reload_profiles(): ReloadResult
```

#### Input Schema

```json
{
  "type": "object",
  "properties": {}
}
```

#### Output Schema

```json
{
  "success": "boolean",
  "profiles_loaded": "number",
  "errors": ["string"]
}
```

#### Příklad

```json
// Response
{
  "success": true,
  "profiles_loaded": 45,
  "errors": []
}
```

---

## MCP Codex Orchestrator Tools

### 1. codex_run

**Spustí Codex CLI v izolovaném Docker kontejneru.**

#### Signatura

```typescript
codex_run(
  prompt: string,           // Povinný: Zadání pro Codex
  mode?: string,            // Volitelný: "full-auto" | "suggest" | "ask"
  timeout?: number,         // Volitelný: Timeout v sekundách
  repo?: string,            // Volitelný: Cesta k repository
  working_dir?: string,     // Volitelný: Working directory
  env_vars?: object         // Volitelný: Extra env vars
): CodexRunResult
```

#### Input Schema

```json
{
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
    "timeout": {
      "type": "integer",
      "default": 300,
      "description": "Timeout v sekundách"
    },
    "repo": {
      "type": "string",
      "description": "Cesta k repository (default: aktuální workspace)"
    },
    "working_dir": {
      "type": "string",
      "description": "Working directory uvnitř repository"
    },
    "env_vars": {
      "type": "object",
      "additionalProperties": { "type": "string" },
      "description": "Extra environment variables"
    }
  },
  "required": ["prompt"]
}
```

#### Output Schema

```json
{
  "success": "boolean",
  "exit_code": "number",
  "output": "string",
  "files_changed": ["string"],
  "container_id": "string",
  "execution_time_ms": "number",
  "error": "string | null"
}
```

#### Příklad

```json
// Request
{
  "tool": "codex_run",
  "arguments": {
    "prompt": "Refactor the authentication module to use async/await patterns",
    "mode": "full-auto",
    "timeout": 600,
    "working_dir": "src/auth"
  }
}

// Response
{
  "success": true,
  "exit_code": 0,
  "output": "Successfully refactored authentication module.\n\nChanges made:\n- Converted login() to async\n- Added await for database calls\n- Updated session management\n\nFiles modified: 3",
  "files_changed": [
    "src/auth/login.py",
    "src/auth/session.py",
    "src/auth/middleware.py"
  ],
  "container_id": "abc123def456",
  "execution_time_ms": 45230,
  "error": null
}
```

#### Approval Modes

| Mode | Popis | Použití |
|------|-------|---------|
| `full-auto` | Automatické schválení | Důvěryhodné úlohy |
| `suggest` | Pouze navrhuje | Review mode |
| `ask` | Interaktivní | Step-by-step |

---

## Chybové stavy

### MCP Error Codes

| Kód | Název | Popis |
|-----|-------|-------|
| -32700 | Parse error | Invalid JSON |
| -32600 | Invalid Request | Malformed request |
| -32601 | Method not found | Unknown tool |
| -32602 | Invalid params | Wrong parameters |
| -32603 | Internal error | Server error |

### Aplikační chyby

| Chyba | Kód | Popis |
|-------|-----|-------|
| ProfileNotFound | 1001 | Profil neexistuje |
| RoutingFailed | 1002 | Routing selhal |
| DockerError | 2001 | Docker chyba |
| TimeoutError | 2002 | Timeout překročen |
| AuthenticationError | 2003 | Codex auth failed |

### Příklad chybové odpovědi

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32602,
    "message": "Invalid params",
    "data": {
      "details": "Missing required parameter: prompt"
    }
  }
}
```

---

## Příklady integrace

### Python klient

```python
import json
import subprocess

def call_mcp_tool(server_cmd: list, tool_name: str, arguments: dict) -> dict:
    """Call an MCP tool and return the result."""
    
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }
    
    process = subprocess.Popen(
        server_cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    stdout, stderr = process.communicate(
        input=json.dumps(request) + "\n"
    )
    
    return json.loads(stdout)

# Usage
result = call_mcp_tool(
    ["python", "-m", "mcp_prompt_broker"],
    "resolve_prompt",
    {"prompt": "Debug my Python code"}
)
print(result["result"]["content"][0]["text"])
```

### VS Code MCP Extension

```json
// .vscode/mcp.json
{
  "mcpServers": {
    "mcp-prompt-broker": {
      "command": "python",
      "args": ["-m", "mcp_prompt_broker"],
      "env": {
        "PYTHONPATH": "${workspaceFolder}/src"
      }
    }
  }
}
```

### Companion Agent

```markdown
## Workflow

1. Call resolve_prompt FIRST
2. Apply returned instructions
3. Use get_checklist for complex tasks
4. Use reload_profiles after profile edits
```

---

## Rate Limits a Performance

### Doporučené limity

| Operace | Doporučený limit | Poznámka |
|---------|------------------|----------|
| resolve_prompt | 60/min | Per-session |
| codex_run | 10/min | Docker overhead |
| reload_profiles | 1/min | File I/O |

### Latence

| Tool | Typická latence | Max latence |
|------|-----------------|-------------|
| resolve_prompt | 10-50ms | 200ms |
| list_profiles | 5-20ms | 100ms |
| get_checklist | 5-20ms | 100ms |
| codex_run | 5-300s | 3600s |

---

## Související dokumenty

- **Architektura:** [../architecture/ARCHITECTURE.md](../architecture/ARCHITECTURE.md)
- **MCP Prompt Broker:** [../modules/MCP_PROMPT_BROKER.md](../modules/MCP_PROMPT_BROKER.md)
- **Codex Orchestrator:** [../modules/CODEX_ORCHESTRATOR.md](../modules/CODEX_ORCHESTRATOR.md)
- **Profiles Schema:** [PROFILES_SCHEMA.md](PROFILES_SCHEMA.md)

---

*Tato dokumentace je součástí 4-úrovňové dokumentační struktury projektu MCP Prompt Broker.*
