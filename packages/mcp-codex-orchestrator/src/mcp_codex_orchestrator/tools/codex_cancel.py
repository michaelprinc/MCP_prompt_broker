"""
MCP Codex Orchestrator - Codex Cancel Tool

Tool pro zrušení běžícího Codex jobu.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import aiofiles
import structlog

from mcp_codex_orchestrator.orchestrator.run_manager import RunManager

logger = structlog.get_logger(__name__)


async def handle_codex_cancel(
    run_id: str,
    run_manager: RunManager,
) -> dict:
    """
    Cancel a running Codex job.
    
    Args:
        run_id: The run identifier
        run_manager: RunManager instance
        
    Returns:
        Result dictionary indicating success or failure
    """
    logger.info("Cancelling run", run_id=run_id)
    
    run_dir = run_manager.runs_path / run_id
    
    if not run_dir.exists():
        return {
            "success": False,
            "run_id": run_id,
            "error": f"Run {run_id} not found",
        }
    
    # Try to find and stop the container
    container = await _get_container(run_id, run_manager)
    
    if container is None:
        # Container not found - check if already completed
        result_file = run_dir / "result.json"
        if result_file.exists():
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
        # Stop the container
        await run_manager.docker_client.stop_container(container)
        
        # Update status file
        await _update_status(run_id, run_manager, "cancelled")
        
        logger.info("Run cancelled successfully", run_id=run_id)
        
        return {
            "success": True,
            "run_id": run_id,
            "status": "cancelled",
            "cancelled_at": datetime.now(timezone.utc).isoformat(),
        }
        
    except Exception as e:
        logger.exception("Failed to cancel run", run_id=run_id, error=str(e))
        return {
            "success": False,
            "run_id": run_id,
            "error": str(e),
        }


async def _get_container(run_id: str, run_manager: RunManager):
    """Get container for run if it exists."""
    try:
        container_name = f"codex-run-{run_id}"
        return run_manager.docker_client.client.containers.get(container_name)
    except Exception:
        return None


async def _update_status(
    run_id: str,
    run_manager: RunManager,
    status: str,
) -> None:
    """Update status file for run."""
    run_dir = run_manager.runs_path / run_id
    status_file = run_dir / "status.json"
    
    status_data = {
        "status": status,
        "run_id": run_id,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    
    async with aiofiles.open(status_file, "w", encoding="utf-8") as f:
        await f.write(json.dumps(status_data, indent=2))
