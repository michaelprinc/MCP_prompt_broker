"""
MCP Codex Orchestrator - Gemini Cancel Tool

Tool for cancelling a running Gemini job.
"""

import json
from datetime import datetime, timezone

import aiofiles
import structlog

from mcp_codex_orchestrator.orchestrator.gemini_run_manager import GeminiRunManager

logger = structlog.get_logger(__name__)


async def handle_gemini_cancel(
    run_id: str,
    run_manager: GeminiRunManager,
) -> dict:
    """Cancel a running Gemini job."""
    logger.info("Cancelling Gemini run", run_id=run_id)

    run_dir = run_manager.runs_path / run_id
    if not run_dir.exists():
        return {
            "success": False,
            "run_id": run_id,
            "error": f"Run {run_id} not found",
        }

    container = await _get_container(run_id, run_manager)
    if container is None:
        run_result_file = run_dir / "run_result.json"
        if run_result_file.exists():
            return {
                "success": False,
                "run_id": run_id,
                "error": "Run already completed",
            }
        return {
            "success": False,
            "run_id": run_id,
            "error": "No running container found for this run",
        }

    try:
        await run_manager.docker_client.stop_container(container)
        await _update_status(run_id, run_manager, "cancelled")
        logger.info("Gemini run cancelled", run_id=run_id)
        return {
            "success": True,
            "run_id": run_id,
            "status": "cancelled",
            "cancelled_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.exception("Failed to cancel Gemini run", run_id=run_id, error=str(e))
        return {
            "success": False,
            "run_id": run_id,
            "error": str(e),
        }


async def _get_container(run_id: str, run_manager: GeminiRunManager):
    try:
        container_name = f"gemini-run-{run_id}"
        return run_manager.docker_client.client.containers.get(container_name)
    except Exception:
        return None


async def _update_status(
    run_id: str,
    run_manager: GeminiRunManager,
    status: str,
) -> None:
    run_dir = run_manager.runs_path / run_id
    status_file = run_dir / "status.json"

    status_data = {
        "status": status,
        "run_id": run_id,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    async with aiofiles.open(status_file, "w", encoding="utf-8") as f:
        await f.write(json.dumps(status_data, indent=2))
