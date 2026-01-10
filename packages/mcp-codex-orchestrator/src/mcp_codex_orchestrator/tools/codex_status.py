"""
MCP Codex Orchestrator - Codex Status Tool

Tool pro získání stavu běžícího Codex jobu.
"""

import json
from pathlib import Path
from typing import Optional

import aiofiles
import structlog

from mcp_codex_orchestrator.orchestrator.run_manager import RunManager
from mcp_codex_orchestrator.orchestrator.jsonl_parser import JSONLParser

logger = structlog.get_logger(__name__)


async def handle_codex_status(
    run_id: str,
    run_manager: RunManager,
) -> dict:
    """
    Get status of a Codex run without reading full logs.
    
    Args:
        run_id: The run identifier
        run_manager: RunManager instance
        
    Returns:
        Status dictionary with run information
    """
    logger.info("Getting run status", run_id=run_id)
    
    run_dir = run_manager.runs_path / run_id
    
    if not run_dir.exists():
        return {
            "status": "not_found",
            "run_id": run_id,
            "error": f"Run {run_id} not found",
        }
    
    # Check status file (created when run completes)
    status_file = run_dir / "status.json"
    if status_file.exists():
        try:
            async with aiofiles.open(status_file, "r", encoding="utf-8") as f:
                status_data = json.loads(await f.read())
            return {
                "status": status_data.get("status", "completed"),
                "run_id": run_id,
                **status_data,
            }
        except Exception as e:
            logger.warning("Failed to read status file", error=str(e))
    
    # Check result file
    result_file = run_dir / "result.json"
    if result_file.exists():
        try:
            async with aiofiles.open(result_file, "r", encoding="utf-8") as f:
                result_data = json.loads(await f.read())
            return {
                "status": result_data.get("status", "completed"),
                "run_id": run_id,
                "duration": result_data.get("duration"),
                "completed_at": result_data.get("finished_at"),
            }
        except Exception as e:
            logger.warning("Failed to read result file", error=str(e))

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
    
    # Check if container is still running
    container_running = await _check_container_running(run_id, run_manager)
    
    if container_running:
        # Parse partial JSONL for progress
        progress = await _get_run_progress(run_id, run_manager)
        return {
            "status": "running",
            "run_id": run_id,
            "progress": progress,
        }
    
    # Check for events.jsonl to determine if it completed
    events_file = run_dir / "events.jsonl"
    if events_file.exists():
        return {
            "status": "completed",
            "run_id": run_id,
            "has_events": True,
        }
    
    # Check for log.txt
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
    run_manager: RunManager,
) -> bool:
    """Check if container for run is still running."""
    try:
        container_name = f"codex-run-{run_id}"
        container = run_manager.docker_client.client.containers.get(container_name)
        return container.status == "running"
    except Exception:
        return False


async def _get_run_progress(
    run_id: str,
    run_manager: RunManager,
) -> dict:
    """Get progress from partial JSONL events."""
    run_dir = run_manager.runs_path / run_id
    events_file = run_dir / "events.jsonl"
    
    progress = {
        "events_count": 0,
        "files_changed": 0,
        "commands_run": 0,
        "last_event_type": None,
    }
    
    if not events_file.exists():
        return progress
    
    try:
        parser = JSONLParser()
        events = await parser.parse_file(events_file)
        
        progress["events_count"] = len(events)
        
        file_changes = [e for e in events if e.type.value == "file.change"]
        commands = [e for e in events if e.type.value == "command.run"]
        
        progress["files_changed"] = len(file_changes)
        progress["commands_run"] = len(commands)
        
        if events:
            progress["last_event_type"] = events[-1].type.value
            
    except Exception as e:
        logger.warning("Failed to parse events for progress", error=str(e))
    
    return progress
