# Oprava MCP Server API

**Soubor:** `src/mcp_prompt_broker/server.py`  
**Priorita:** Kritická  
**Komplexita:** Vysoká

---

## Popis problému

Aktuální implementace serveru používá zastaralé API `server.run_stdio()`, které neexistuje v MCP knihovně verze 1.23.1. Nová verze MCP vyžaduje:

1. Použití `stdio_server` jako async context manager
2. Explicitní volání `server.run()` s read/write streamy
3. Předání `InitializationOptions` s konfigurací serveru

---

## Aktuální problematický kód

```python
# server.py - řádky 130-139
def run(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the MCP prompt broker server.")
    parser.add_argument(
        "--instructions",
        help="Path to a JSON file containing instruction definitions.",
        default=None,
    )
    args = parser.parse_args(argv)

    instruction_profiles = list(get_instruction_profiles())
    if args.instructions:
        with open(args.instructions, "r", encoding="utf-8") as fp:
            loaded = json.load(fp)
            instruction_profiles = [InstructionProfile(**item) for item in loaded]

    router = ProfileRouter(instruction_profiles)
    server = _build_server(router)

    asyncio.run(server.run_stdio())  # <-- CHYBA: run_stdio neexistuje
    return 0
```

---

## Opravený kód

### Část 1: Nové importy

Na začátek souboru `server.py` přidat:

```python
"""MCP server entrypoint and wiring for the prompt broker."""
from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any, Dict, List, Mapping

import mcp.server.stdio
import mcp.types as types
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.models import InitializationOptions

# Opravené relativní importy (viz 03_oprava_importu.md)
from ..config.profiles import InstructionProfile, get_instruction_profiles
from ..metadata.parser import ParsedMetadata, analyze_prompt
from ..router.profile_router import EnhancedMetadata, ProfileRouter, RoutingResult
```

### Část 2: Opravená funkce `_build_server`

```python
def _build_server(router: ProfileRouter) -> Server:
    """Build and configure the MCP server with tools."""
    server = Server("mcp-prompt-broker")

    @server.list_tools()
    async def list_tools() -> List[types.Tool]:
        return [
            types.Tool(
                name="list_profile",
                description="List available instruction profiles and their metadata.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            types.Tool(
                name="get_profile",
                description=(
                    "Analyze a prompt, enrich it with metadata, and return the best "
                    "matching instruction profile."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "prompt": {"type": "string"},
                        "metadata": {
                            "type": "object",
                            "description": "Optional metadata overrides to steer routing.",
                        },
                    },
                    "required": ["prompt"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]) -> Any:
        if name == "list_profile":
            return [_profile_to_dict(profile) for profile in router.profiles]

        if name == "get_profile":
            try:
                prompt = str(arguments.get("prompt", ""))
                overrides: Mapping[str, object] | None = arguments.get("metadata")
                parsed: ParsedMetadata = analyze_prompt(prompt)
                enhanced: EnhancedMetadata = parsed.to_enhanced_metadata(overrides)
                routing: RoutingResult = router.route(enhanced)
                return {
                    "profile": _profile_to_dict(routing.profile),
                    "metadata": parsed.as_dict(),
                    "routing": {
                        "score": routing.score,
                        "consistency": routing.consistency,
                    },
                }
            except (ValueError, LookupError) as exc:
                return types.TextContent(type="text", text=f"Error: {str(exc)}")

        return types.TextContent(type="text", text=f"Unknown tool: {name}")

    return server
```

### Část 3: Opravená funkce `run`

```python
async def _run_server(server: Server) -> None:
    """Run the MCP server using stdio transport."""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="mcp-prompt-broker",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


def run(argv: List[str] | None = None) -> int:
    """Parse arguments and run the MCP prompt broker server."""
    parser = argparse.ArgumentParser(description="Run the MCP prompt broker server.")
    parser.add_argument(
        "--instructions",
        help="Path to a JSON file containing instruction definitions.",
        default=None,
    )
    args = parser.parse_args(argv)

    instruction_profiles = list(get_instruction_profiles())
    if args.instructions:
        with open(args.instructions, "r", encoding="utf-8") as fp:
            loaded = json.load(fp)
            instruction_profiles = [InstructionProfile(**item) for item in loaded]

    router = ProfileRouter(instruction_profiles)
    server = _build_server(router)

    try:
        asyncio.run(_run_server(server))
    except KeyboardInterrupt:
        pass  # Graceful shutdown on Ctrl+C
    
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
```

---

## Kompletní opravený soubor

Níže je kompletní opravený `server.py`:

```python
"""MCP server entrypoint and wiring for the prompt broker."""
from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any, Dict, List, Mapping

import mcp.server.stdio
import mcp.types as types
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.models import InitializationOptions

# Relativní importy v rámci balíčku
from ..config.profiles import InstructionProfile, get_instruction_profiles
from ..metadata.parser import ParsedMetadata, analyze_prompt
from ..router.profile_router import EnhancedMetadata, ProfileRouter, RoutingResult


def _profile_to_dict(profile: InstructionProfile) -> Dict[str, object]:
    """Serialize an :class:`InstructionProfile` into JSON-safe structure."""
    return {
        "name": profile.name,
        "instructions": profile.instructions,
        "required": {key: sorted(value) for key, value in profile.required.items()},
        "weights": {key: dict(value) for key, value in profile.weights.items()},
        "default_score": profile.default_score,
        "fallback": profile.fallback,
    }


def _build_server(router: ProfileRouter) -> Server:
    """Build and configure the MCP server with tools."""
    server = Server("mcp-prompt-broker")

    @server.list_tools()
    async def list_tools() -> List[types.Tool]:
        return [
            types.Tool(
                name="list_profile",
                description="List available instruction profiles and their metadata.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            types.Tool(
                name="get_profile",
                description=(
                    "Analyze a prompt, enrich it with metadata, and return the best "
                    "matching instruction profile."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "prompt": {"type": "string"},
                        "metadata": {
                            "type": "object",
                            "description": "Optional metadata overrides to steer routing.",
                        },
                    },
                    "required": ["prompt"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]) -> Any:
        if name == "list_profile":
            return [_profile_to_dict(profile) for profile in router.profiles]

        if name == "get_profile":
            try:
                prompt = str(arguments.get("prompt", ""))
                overrides: Mapping[str, object] | None = arguments.get("metadata")
                parsed: ParsedMetadata = analyze_prompt(prompt)
                enhanced: EnhancedMetadata = parsed.to_enhanced_metadata(overrides)
                routing: RoutingResult = router.route(enhanced)
                return {
                    "profile": _profile_to_dict(routing.profile),
                    "metadata": parsed.as_dict(),
                    "routing": {
                        "score": routing.score,
                        "consistency": routing.consistency,
                    },
                }
            except (ValueError, LookupError) as exc:
                return types.TextContent(type="text", text=f"Error: {str(exc)}")

        return types.TextContent(type="text", text=f"Unknown tool: {name}")

    return server


async def _run_server(server: Server) -> None:
    """Run the MCP server using stdio transport."""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="mcp-prompt-broker",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


def run(argv: List[str] | None = None) -> int:
    """Parse arguments and run the MCP prompt broker server."""
    parser = argparse.ArgumentParser(description="Run the MCP prompt broker server.")
    parser.add_argument(
        "--instructions",
        help="Path to a JSON file containing instruction definitions.",
        default=None,
    )
    args = parser.parse_args(argv)

    instruction_profiles = list(get_instruction_profiles())
    if args.instructions:
        with open(args.instructions, "r", encoding="utf-8") as fp:
            loaded = json.load(fp)
            instruction_profiles = [InstructionProfile(**item) for item in loaded]

    router = ProfileRouter(instruction_profiles)
    server = _build_server(router)

    try:
        asyncio.run(_run_server(server))
    except KeyboardInterrupt:
        pass  # Graceful shutdown on Ctrl+C

    return 0


if __name__ == "__main__":
    raise SystemExit(run())
```

---

## Klíčové změny

| Oblast | Stará verze | Nová verze |
|--------|-------------|------------|
| Import Server | `from mcp.server import Server` | `from mcp.server.lowlevel import Server` |
| Stdio transport | Nepoužíváno | `mcp.server.stdio.stdio_server()` |
| Inicializace | `server.run_stdio()` | `server.run(streams, InitializationOptions)` |
| Error handling | `types.ErrorData` | `types.TextContent` |
| Shutdown | Žádný | `KeyboardInterrupt` handling |

---

## Verifikace opravy

Po aplikaci opravy ověřte funkčnost:

```powershell
# 1. Reinstalovat balíček
.venv\Scripts\python.exe -m pip install -e .

# 2. Spustit server (měl by čekat na stdin)
.venv\Scripts\python.exe -m mcp_prompt_broker

# 3. Nebo testovat s JSON-RPC zprávou
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | .venv\Scripts\python.exe -m mcp_prompt_broker
```

---

## Další kroky

Po opravě tohoto souboru je nutné:

1. ✅ Opravit importy (viz `03_oprava_importu.md`)
2. ✅ Opravit `pyproject.toml` (viz `04_oprava_pyproject.md`)
3. ✅ Reinstalovat balíček

---

## Reference

- [MCP Python SDK - Low-Level Server](https://github.com/modelcontextprotocol/python-sdk#low-level-server)
- [MCP stdio_server dokumentace](https://github.com/modelcontextprotocol/python-sdk/blob/main/src/mcp/server/stdio.py)
