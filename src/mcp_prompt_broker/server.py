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
from .config.profiles import InstructionProfile, get_instruction_profiles
from .metadata.parser import ParsedMetadata, analyze_prompt
from .router.profile_router import EnhancedMetadata, ProfileRouter, RoutingResult


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
