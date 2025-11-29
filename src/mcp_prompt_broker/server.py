"""MCP server entrypoint and wiring for the prompt broker."""
from __future__ import annotations

import argparse
import asyncio
import json
from typing import Dict, List

import mcp.types as types
from mcp.server import Server

from .instructions import DEFAULT_INSTRUCTIONS, Instruction, InstructionCatalog


def _build_server(catalog: InstructionCatalog) -> Server:
    server = Server("mcp-prompt-broker")

    @server.list_tools()
    async def list_tools() -> List[types.Tool]:
        return [
            types.Tool(
                name="listInstructions",
                description="List available instructions and their purpose.",
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
                            "description": {"type": "string"},
                            "guidance": {"type": "string"},
                        },
                    },
                },
            ),
            types.Tool(
                name="selectInstruction",
                description="Select the best instruction for a given user prompt.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "prompt": {"type": "string"},
                    },
                    "required": ["prompt"],
                },
                outputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "guidance": {"type": "string"},
                        "description": {"type": "string"},
                    },
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: Dict):
        if name == "listInstructions":
            return [instruction.__dict__ for instruction in catalog.list()]
        if name == "selectInstruction":
            try:
                instruction = catalog.select(arguments.get("prompt", ""))
                return instruction.__dict__
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

    instructions = DEFAULT_INSTRUCTIONS
    if args.instructions:
        with open(args.instructions, "r", encoding="utf-8") as fp:
            loaded = json.load(fp)
            instructions = [Instruction(**item) for item in loaded]

    catalog = InstructionCatalog(instructions)
    server = _build_server(catalog)

    asyncio.run(server.run_stdio())
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
