"""
MCP Codex Orchestrator - Server

Hlavní MCP server implementace s registrací toolů.
"""

import os
from pathlib import Path

import structlog
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from mcp_codex_orchestrator.models.run_request import CodexRunRequest
from mcp_codex_orchestrator.models.run_result import CodexRunResult
from mcp_codex_orchestrator.orchestrator.run_manager import RunManager
from mcp_codex_orchestrator.tools.codex_run import handle_codex_run

logger = structlog.get_logger(__name__)

# Default paths
DEFAULT_WORKSPACE_PATH = Path(os.getenv("WORKSPACE_PATH", "./workspace")).resolve()
DEFAULT_RUNS_PATH = Path(os.getenv("RUNS_PATH", "./runs")).resolve()
DEFAULT_TIMEOUT = int(os.getenv("DEFAULT_TIMEOUT", "300"))


def create_server() -> Server:
    """Create and configure the MCP server."""
    server = Server("mcp-codex-orchestrator")
    
    # Initialize run manager
    run_manager = RunManager(
        workspace_path=DEFAULT_WORKSPACE_PATH,
        runs_path=DEFAULT_RUNS_PATH,
        default_timeout=DEFAULT_TIMEOUT,
    )
    
    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """List available MCP tools."""
        return [
            Tool(
                name="codex.run",
                description=(
                    "Spustí OpenAI Codex CLI v izolovaném Docker kontejneru. "
                    "Codex provede zadanou úlohu nad workspace a vrátí výsledek."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": "Zadání pro Codex CLI - co má udělat",
                        },
                        "mode": {
                            "type": "string",
                            "enum": ["full-auto", "suggest", "ask"],
                            "default": "full-auto",
                            "description": "Režim běhu Codex CLI",
                        },
                        "repo": {
                            "type": "string",
                            "description": "Cesta k repository (default: aktuální workspace)",
                        },
                        "working_dir": {
                            "type": "string",
                            "description": "Working directory uvnitř repository",
                        },
                        "timeout": {
                            "type": "integer",
                            "default": 300,
                            "description": "Timeout v sekundách",
                        },
                        "env_vars": {
                            "type": "object",
                            "additionalProperties": {"type": "string"},
                            "description": "Extra environment variables",
                        },
                    },
                    "required": ["prompt"],
                },
            ),
        ]
    
    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        """Handle tool calls."""
        logger.info("Tool called", tool=name, arguments=arguments)
        
        if name == "codex.run":
            # Validate and create request
            request = CodexRunRequest(
                prompt=arguments["prompt"],
                mode=arguments.get("mode", "full-auto"),
                repo=arguments.get("repo"),
                working_dir=arguments.get("working_dir"),
                timeout=arguments.get("timeout", DEFAULT_TIMEOUT),
                env_vars=arguments.get("env_vars"),
            )
            
            # Execute the run
            result = await handle_codex_run(request, run_manager)
            
            # Format response
            return [
                TextContent(
                    type="text",
                    text=result.format_response(),
                )
            ]
        
        raise ValueError(f"Unknown tool: {name}")
    
    return server


async def run_server(
    transport: str = "stdio",
    host: str = "localhost",
    port: int = 3000,
) -> None:
    """Run the MCP server."""
    server = create_server()
    
    logger.info(
        "Starting MCP Codex Orchestrator",
        transport=transport,
        host=host if transport == "http" else None,
        port=port if transport == "http" else None,
    )
    
    if transport == "stdio":
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options(),
            )
    elif transport == "http":
        # HTTP transport (placeholder for future implementation)
        raise NotImplementedError("HTTP transport not yet implemented")
    else:
        raise ValueError(f"Unknown transport: {transport}")
