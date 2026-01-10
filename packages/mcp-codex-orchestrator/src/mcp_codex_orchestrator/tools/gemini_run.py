"""
MCP Codex Orchestrator - Gemini Run Tool

MCP tool implementation for gemini_run().
"""

import structlog

from mcp_codex_orchestrator.models.gemini_run_request import GeminiRunRequest
from mcp_codex_orchestrator.models.run_result import RunProvider, RunResult, RunStatus
from mcp_codex_orchestrator.orchestrator.gemini_run_manager import GeminiRunManager

logger = structlog.get_logger(__name__)


async def handle_gemini_run(
    request: GeminiRunRequest,
    run_manager: GeminiRunManager,
) -> RunResult:
    """Handle gemini_run tool invocation."""
    logger.info(
        "Handling gemini_run request",
        prompt_length=len(request.prompt),
        timeout=request.timeout,
        output_format=request.output_format,
    )

    try:
        run_id = await run_manager.create_run(request)
        logger.info("Created Gemini run", run_id=run_id)

        result = await run_manager.execute_run(run_id)
        logger.info(
            "Gemini run completed",
            run_id=run_id,
            status=result.status,
            duration=result.duration,
        )
        return result
    except Exception as e:
        logger.exception("Error executing gemini_run", error=str(e))
        return RunResult(
            run_id="error",
            provider=RunProvider.GEMINI,
            status=RunStatus.ERROR,
            error=str(e),
        )
