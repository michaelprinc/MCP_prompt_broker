"""
MCP Codex Orchestrator - Codex Run Tool

Implementace MCP tool codex.run().
"""

import structlog

from mcp_codex_orchestrator.models.run_request import CodexRunRequest
from mcp_codex_orchestrator.models.run_result import CodexRunResult, RunStatus
from mcp_codex_orchestrator.orchestrator.run_manager import RunManager

logger = structlog.get_logger(__name__)


async def handle_codex_run(
    request: CodexRunRequest,
    run_manager: RunManager,
) -> CodexRunResult:
    """
    Handle codex.run() tool invocation.
    
    Args:
        request: The run request with prompt and parameters
        run_manager: The run manager instance
        
    Returns:
        CodexRunResult with the outcome of the run
    """
    logger.info(
        "Handling codex.run request",
        prompt_length=len(request.prompt),
        mode=request.mode,
        timeout=request.timeout,
    )
    
    try:
        # Create a new run
        run_id = await run_manager.create_run(request)
        logger.info("Created run", run_id=run_id)
        
        # Execute the run
        result = await run_manager.execute_run(run_id)
        logger.info(
            "Run completed",
            run_id=run_id,
            status=result.status.value,
            duration=result.duration,
        )
        
        return result
        
    except Exception as e:
        logger.exception("Error executing codex.run", error=str(e))
        
        # Return error result
        return CodexRunResult(
            run_id="error",
            status=RunStatus.ERROR,
            error=str(e),
        )
