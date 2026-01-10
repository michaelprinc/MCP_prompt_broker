"""
MCP Codex Orchestrator - Gemini Git Diff Tool

Wrapper around codex git diff for Gemini runs.
"""

from mcp_codex_orchestrator.orchestrator.gemini_run_manager import GeminiRunManager
from mcp_codex_orchestrator.tools.codex_git_diff import handle_codex_git_diff


async def handle_gemini_git_diff(
    run_id: str,
    run_manager: GeminiRunManager,
    format: str = "unified",
) -> dict:
    """Get standardized git diff output for a Gemini run."""
    return await handle_codex_git_diff(run_id=run_id, run_manager=run_manager, format=format)
