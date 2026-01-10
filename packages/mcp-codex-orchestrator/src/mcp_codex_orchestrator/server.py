"""
MCP Codex Orchestrator - Server v2.0

Hlavní MCP server implementace s registrací toolů.
Includes: codex_run, codex_run_status, codex_run_cancel, codex_run_artifacts, codex_git_diff
"""

import json
import os
from pathlib import Path

import structlog
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from mcp_codex_orchestrator.models.gemini_run_request import GeminiRunRequest
from mcp_codex_orchestrator.models.run_request import CodexRunRequest
from mcp_codex_orchestrator.models.run_result import CodexRunResult
from mcp_codex_orchestrator.orchestrator.run_manager import RunManager
from mcp_codex_orchestrator.orchestrator.gemini_run_manager import GeminiRunManager
from mcp_codex_orchestrator.tools.codex_run import handle_codex_run
from mcp_codex_orchestrator.tools.codex_status import handle_codex_status
from mcp_codex_orchestrator.tools.codex_cancel import handle_codex_cancel
from mcp_codex_orchestrator.tools.codex_artifacts import handle_codex_artifacts
from mcp_codex_orchestrator.tools.codex_git_diff import handle_codex_git_diff
from mcp_codex_orchestrator.tools.gemini_run import handle_gemini_run
from mcp_codex_orchestrator.tools.gemini_status import handle_gemini_status
from mcp_codex_orchestrator.tools.gemini_cancel import handle_gemini_cancel
from mcp_codex_orchestrator.tools.gemini_artifacts import handle_gemini_artifacts
from mcp_codex_orchestrator.tools.gemini_git_diff import handle_gemini_git_diff

logger = structlog.get_logger(__name__)

# Default paths
DEFAULT_WORKSPACE_PATH = Path(os.getenv("WORKSPACE_PATH", "./workspace")).resolve()
DEFAULT_RUNS_PATH = Path(os.getenv("RUNS_PATH", "./runs")).resolve()
DEFAULT_SCHEMAS_PATH = Path(os.getenv("SCHEMAS_PATH", "./schemas")).resolve()
DEFAULT_TIMEOUT = int(os.getenv("DEFAULT_TIMEOUT", "300"))


def create_server() -> Server:
    """Create and configure the MCP server."""
    server = Server("mcp-codex-orchestrator")
    
    # Initialize run managers
    run_manager = RunManager(
        workspace_path=DEFAULT_WORKSPACE_PATH,
        runs_path=DEFAULT_RUNS_PATH,
        schemas_path=DEFAULT_SCHEMAS_PATH,
        default_timeout=DEFAULT_TIMEOUT,
    )
    gemini_manager = GeminiRunManager(
        workspace_path=DEFAULT_WORKSPACE_PATH,
        runs_path=DEFAULT_RUNS_PATH,
        default_timeout=DEFAULT_TIMEOUT,
    )
    
    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """List available MCP tools."""
        return [
            # Main execution tool
            Tool(
                name="codex_run",
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
                        "security_mode": {
                            "type": "string",
                            "enum": ["readonly", "workspace_write", "full_access"],
                            "default": "workspace_write",
                            "description": "Security mode pro sandbox izolaci",
                        },
                        "verify": {
                            "type": "boolean",
                            "default": False,
                            "description": "Automaticky spustit verify loop (testy, lint)",
                        },
                        "output_schema": {
                            "type": "string",
                            "description": "Název JSON schématu pro validaci výstupu",
                        },
                        "json_output": {
                            "type": "boolean",
                            "default": True,
                            "description": "Použít JSONL výstup z Codex CLI",
                        },
                    },
                    "required": ["prompt"],
                },
            ),
            Tool(
                name="gemini_run",
                description=(
                    "Spusti Gemini CLI v izolovanem Docker kontejneru. "
                    "Gemini provede zadanou ulohu nad workspace a vrati vysledek."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": "Zadani pro Gemini CLI - co ma udelat",
                        },
                        "mode": {
                            "type": "string",
                            "enum": ["suggest", "workspace_write", "full_access"],
                            "description": "Zjednoduseny rezim (prebiji security_mode)",
                        },
                        "repo": {
                            "type": "string",
                            "description": "Cesta k repository (default: aktualni workspace)",
                        },
                        "working_dir": {
                            "type": "string",
                            "description": "Working directory uvnitr repository",
                        },
                        "timeout": {
                            "type": "integer",
                            "default": 300,
                            "description": "Timeout v sekundach",
                        },
                        "env_vars": {
                            "type": "object",
                            "additionalProperties": {"type": "string"},
                            "description": "Extra environment variables",
                        },
                        "security_mode": {
                            "type": "string",
                            "enum": ["readonly", "workspace_write", "full_access"],
                            "default": "workspace_write",
                            "description": "Security mode pro workspace mount",
                        },
                        "verify": {
                            "type": "boolean",
                            "default": False,
                            "description": "Automaticky spustit verify loop (testy, lint)",
                        },
                        "output_format": {
                            "type": "string",
                            "enum": ["json", "stream-json"],
                            "default": "json",
                            "description": "Gemini CLI output format",
                        },
                    },
                    "required": ["prompt"],
                },
            ),
            # Status polling tool
            Tool(
                name="codex_run_status",
                description=(
                    "Získá aktuální stav běžícího nebo dokončeného Codex runu. "
                    "Vrací progress, events a případný výsledek."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "run_id": {
                            "type": "string",
                            "description": "UUID identifikátor runu",
                        },
                        "include_events": {
                            "type": "boolean",
                            "default": False,
                            "description": "Zahrnout seznam všech events",
                        },
                    },
                    "required": ["run_id"],
                },
            ),
            Tool(
                name="gemini_run_status",
                description=(
                    "Ziska aktualni stav beziciho nebo dokonceneho Gemini runu."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "run_id": {
                            "type": "string",
                            "description": "UUID identifikator runu",
                        },
                    },
                    "required": ["run_id"],
                },
            ),
            # Cancel tool
            Tool(
                name="codex_run_cancel",
                description=(
                    "Zruší běžící Codex run. "
                    "Vrací potvrzení o zrušení a finální stav."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "run_id": {
                            "type": "string",
                            "description": "UUID identifikátor runu k zrušení",
                        },
                        "force": {
                            "type": "boolean",
                            "default": False,
                            "description": "Force kill kontejneru (SIGKILL)",
                        },
                    },
                    "required": ["run_id"],
                },
            ),
            Tool(
                name="gemini_run_cancel",
                description=(
                    "Zrusi bezici Gemini run. Vraci potvrzeni o zruseni."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "run_id": {
                            "type": "string",
                            "description": "UUID identifikator runu k zruseni",
                        },
                    },
                    "required": ["run_id"],
                },
            ),
            # Artifacts tool
            Tool(
                name="codex_run_artifacts",
                description=(
                    "Získá artefakty z dokončeného Codex runu. "
                    "Vrací seznam souborů, diffů a logů."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "run_id": {
                            "type": "string",
                            "description": "UUID identifikátor runu",
                        },
                        "artifact_type": {
                            "type": "string",
                            "enum": ["all", "files", "diffs", "logs", "events"],
                            "default": "all",
                            "description": "Typ artefaktů k získání",
                        },
                    },
                    "required": ["run_id"],
                },
            ),
            Tool(
                name="gemini_run_artifacts",
                description=(
                    "Ziska artefakty z dokonceneho Gemini runu."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "run_id": {
                            "type": "string",
                            "description": "UUID identifikator runu",
                        },
                        "artifact_type": {
                            "type": "string",
                            "enum": ["all", "files", "diffs", "logs", "events", "responses", "results"],
                            "default": "all",
                            "description": "Typ artefaktu k ziskani",
                        },
                    },
                    "required": ["run_id"],
                },
            ),
            # Git diff tool
            Tool(
                name="codex_git_diff",
                description=(
                    "Získá standardizovaný git diff výstup pro run. "
                    "Parsuje unified diff formát do strukturovaných změn."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "run_id": {
                            "type": "string",
                            "description": "UUID identifikátor runu",
                        },
                        "file_filter": {
                            "type": "string",
                            "description": "Glob pattern pro filtrování souborů (např. '*.py')",
                        },
                        "context_lines": {
                            "type": "integer",
                            "default": 3,
                            "description": "Počet context lines v diffu",
                        },
                    },
                    "required": ["run_id"],
                },
            ),
            Tool(
                name="gemini_git_diff",
                description=(
                    "Ziska standardizovany git diff vystup pro Gemini run."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "run_id": {
                            "type": "string",
                            "description": "UUID identifikator runu",
                        },
                        "format": {
                            "type": "string",
                            "enum": ["unified", "stat", "name-only"],
                            "default": "unified",
                            "description": "Format diffu",
                        },
                    },
                    "required": ["run_id"],
                },
            ),
        ]
    
    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        """Handle tool calls."""
        logger.info("Tool called", tool=name, arguments=arguments)
        
        # Normalize tool name - VS Code may transform underscores to dots
        normalized_name = name.replace(".", "_")
        
        if normalized_name == "codex_run":
            # Validate and create request
            request = CodexRunRequest(
                prompt=arguments["prompt"],
                mode=arguments.get("mode", "full-auto"),
                repo=arguments.get("repo"),
                working_dir=arguments.get("working_dir"),
                timeout=arguments.get("timeout", DEFAULT_TIMEOUT),
                env_vars=arguments.get("env_vars"),
                security_mode=arguments.get("security_mode", "workspace_write"),
                verify=arguments.get("verify", False),
                output_schema=arguments.get("output_schema"),
                json_output=arguments.get("json_output", True),
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

        if normalized_name == "gemini_run":
            request = GeminiRunRequest(
                prompt=arguments["prompt"],
                mode=arguments.get("mode"),
                repo=arguments.get("repo"),
                working_dir=arguments.get("working_dir"),
                timeout=arguments.get("timeout", DEFAULT_TIMEOUT),
                env_vars=arguments.get("env_vars"),
                security_mode=arguments.get("security_mode", "workspace_write"),
                verify=arguments.get("verify", False),
                output_format=arguments.get("output_format", "json"),
            )
            result = await handle_gemini_run(request, gemini_manager)
            return [
                TextContent(
                    type="text",
                    text=result.json(indent=2, ensure_ascii=False),
                )
            ]
        
        elif normalized_name == "codex_run_status":
            # Get run status
            result = await handle_codex_status(
                run_id=arguments["run_id"],
                run_manager=run_manager,
                include_events=arguments.get("include_events", False),
            )
            return [
                TextContent(
                    type="text",
                    text=json.dumps(result, indent=2, ensure_ascii=False),
                )
            ]

        elif normalized_name == "gemini_run_status":
            result = await handle_gemini_status(
                run_id=arguments["run_id"],
                run_manager=gemini_manager,
            )
            return [
                TextContent(
                    type="text",
                    text=json.dumps(result, indent=2, ensure_ascii=False),
                )
            ]
        
        elif normalized_name == "codex_run_cancel":
            # Cancel run
            result = await handle_codex_cancel(
                run_id=arguments["run_id"],
                run_manager=run_manager,
                force=arguments.get("force", False),
            )
            return [
                TextContent(
                    type="text",
                    text=json.dumps(result, indent=2, ensure_ascii=False),
                )
            ]

        elif normalized_name == "gemini_run_cancel":
            result = await handle_gemini_cancel(
                run_id=arguments["run_id"],
                run_manager=gemini_manager,
            )
            return [
                TextContent(
                    type="text",
                    text=json.dumps(result, indent=2, ensure_ascii=False),
                )
            ]
        
        elif normalized_name == "codex_run_artifacts":
            # Get artifacts
            result = await handle_codex_artifacts(
                run_id=arguments["run_id"],
                run_manager=run_manager,
                artifact_type=arguments.get("artifact_type", "all"),
            )
            return [
                TextContent(
                    type="text",
                    text=json.dumps(result, indent=2, ensure_ascii=False),
                )
            ]

        elif normalized_name == "gemini_run_artifacts":
            result = await handle_gemini_artifacts(
                run_id=arguments["run_id"],
                run_manager=gemini_manager,
                artifact_type=arguments.get("artifact_type", "all"),
            )
            return [
                TextContent(
                    type="text",
                    text=json.dumps(result, indent=2, ensure_ascii=False),
                )
            ]
        
        elif normalized_name == "codex_git_diff":
            # Get git diff
            result = await handle_codex_git_diff(
                run_id=arguments["run_id"],
                run_manager=run_manager,
                file_filter=arguments.get("file_filter"),
                context_lines=arguments.get("context_lines", 3),
            )
            return [
                TextContent(
                    type="text",
                    text=json.dumps(result, indent=2, ensure_ascii=False),
                )
            ]

        elif normalized_name == "gemini_git_diff":
            result = await handle_gemini_git_diff(
                run_id=arguments["run_id"],
                run_manager=gemini_manager,
                format=arguments.get("format", "unified"),
            )
            return [
                TextContent(
                    type="text",
                    text=json.dumps(result, indent=2, ensure_ascii=False),
                )
            ]
        
        raise ValueError(f"Unknown tool: {name} (normalized: {normalized_name})")
    
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
