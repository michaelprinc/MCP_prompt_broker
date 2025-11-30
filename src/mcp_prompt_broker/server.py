"""MCP server entrypoint and wiring for the prompt broker."""
from __future__ import annotations

import argparse
import asyncio
import json
from typing import Dict, List, Mapping

import mcp.types as types
from mcp.server import Server

from config.profiles import InstructionProfile, get_instruction_profiles
from metadata.parser import ParsedMetadata, analyze_prompt
from router.profile_router import EnhancedMetadata, ProfileRouter


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
                outputSchema={
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "instructions": {"type": "string"},
                            "required": {"type": "object"},
                            "weights": {"type": "object"},
                            "default_score": {"type": "number"},
                            "fallback": {"type": "boolean"},
                        },
                    },
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
                outputSchema={
                    "type": "object",
                    "properties": {
                        "profile": {"type": "object"},
                        "metadata": {"type": "object"},
                    },
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: Dict):
        if name == "list_profile":
            return [_profile_to_dict(profile) for profile in router.profiles]

        if name == "get_profile":
            try:
                prompt = str(arguments.get("prompt", ""))
                overrides: Mapping[str, object] | None = arguments.get("metadata")
                parsed: ParsedMetadata = analyze_prompt(prompt)
                enhanced: EnhancedMetadata = parsed.to_enhanced_metadata(overrides)
                profile = router.route(enhanced)
                return {
                    "profile": _profile_to_dict(profile),
                    "metadata": parsed.as_dict(),
                }
            except (ValueError, LookupError) as exc:
                return types.ErrorData(code=400, message=str(exc))

        return types.ErrorData(code=404, message=f"Unknown tool: {name}")

    return server


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
            # instructions file now expects profile-shaped objects
            instruction_profiles = [InstructionProfile(**item) for item in loaded]

    router = ProfileRouter(instruction_profiles)
    server = _build_server(router)

    asyncio.run(server.run_stdio())
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
