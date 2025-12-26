"""
MCP Codex Orchestrator

MCP server pro orchestraci OpenAI Codex CLI běhů v Docker kontejnerech.
"""

__version__ = "0.1.0"
__author__ = "MCP Prompt Broker Team"

from mcp_codex_orchestrator.server import create_server, run_server

__all__ = ["create_server", "run_server", "__version__"]
