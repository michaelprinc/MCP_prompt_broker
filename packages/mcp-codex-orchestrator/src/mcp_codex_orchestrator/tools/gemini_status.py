"""
MCP Codex Orchestrator - Gemini Status Tool

Tool for checking the status of a Gemini run.
"""

import json
from pathlib import Path

import aiofiles
import structlog

from mcp_codex_orchestrator.orchestrator.gemini_run_manager import GeminiRunManager

logger = structlog.get_logger(__name__)


async def handle_gemini_status(
    run_id: str,
    run_manager: GeminiRunManager,
) -> dict:
    """Get status of a Gemini run."""
    logger.info("Getting Gemini run status", run_id=run_id)

    run_dir = run_manager.runs_path / run_id
    if not run_dir.exists():
        return {
            "status": "not_found",
            "run_id": run_id,
            "error": f"Run {run_id} not found",
        }

    run_result_file = run_dir / "run_result.json"
    if run_result_file.exists():
        try:
            async with aiofiles.open(run_result_file, "r", encoding="utf-8") as f:
                result_data = json.loads(await f.read())
            return {
                "status": result_data.get("status", "completed"),
                "run_id": run_id,
                "duration": result_data.get("duration"),
                "completed_at": result_data.get("finished_at"),
            }
        except Exception as e:
            logger.warning("Failed to read run_result.json", error=str(e))

    if await _check_container_running(run_id, run_manager):
        progress = await _get_run_progress(run_id, run_manager)
        return {
            "status": "running",
            "run_id": run_id,
            "progress": progress,
        }

    log_file = run_dir / "log.txt"
    if log_file.exists():
        return {
            "status": "completed",
            "run_id": run_id,
            "has_log": True,
        }

    return {
        "status": "unknown",
        "run_id": run_id,
    }


async def _check_container_running(
    run_id: str,
    run_manager: GeminiRunManager,
) -> bool:
    try:
        container_name = f"gemini-run-{run_id}"
        container = run_manager.docker_client.client.containers.get(container_name)
        return container.status == "running"
    except Exception:
        return False


async def _get_run_progress(
    run_id: str,
    run_manager: GeminiRunManager,
) -> dict:
    run_dir = run_manager.runs_path / run_id
    events_file = run_dir / "events.jsonl"

    progress = {
        "events_count": 0,
        "last_event_keys": None,
    }

    if not events_file.exists():
        return progress

    try:
        async with aiofiles.open(events_file, "r", encoding="utf-8") as f:
            events = [line for line in (await f.read()).splitlines() if line.strip()]
        progress["events_count"] = len(events)
        if events:
            try:
                last_event = json.loads(events[-1])
                if isinstance(last_event, dict):
                    progress["last_event_keys"] = sorted(last_event.keys())
            except json.JSONDecodeError:
                pass
    except Exception as e:
        logger.warning("Failed to read events for progress", error=str(e))

    return progress
