"""
MCP Codex Orchestrator - Codex Artifacts Tool

Tool pro získání artefaktů z dokončeného Codex běhu.
"""

import json
from pathlib import Path
from typing import Optional

import aiofiles
import structlog

from mcp_codex_orchestrator.orchestrator.run_manager import RunManager
from mcp_codex_orchestrator.orchestrator.jsonl_parser import JSONLParser, parse_jsonl_file

logger = structlog.get_logger(__name__)


async def handle_codex_artifacts(
    run_id: str,
    run_manager: RunManager,
    artifact_type: str = "all",
) -> dict:
    """
    Get artifacts from a completed Codex run.
    
    Args:
        run_id: The run identifier
        run_manager: RunManager instance
        include_diff: Include diff content
        include_jsonl: Include parsed JSONL events
        include_log: Include raw log content
        
    Returns:
        Dictionary with artifact information and content
    """
    logger.info("Getting run artifacts", run_id=run_id, artifact_type=artifact_type)
    
    run_dir = run_manager.runs_path / run_id
    
    if not run_dir.exists():
        return {
            "success": False,
            "run_id": run_id,
            "error": f"Run {run_id} not found",
        }
    
    include_diff = artifact_type in ("all", "diffs")
    include_jsonl = artifact_type in ("all", "events")
    include_log = artifact_type in ("all", "logs")

    artifacts: dict = {
        "success": True,
        "run_id": run_id,
        "paths": {},
        "content": {},
    }
    
    # Collect artifact paths and optionally content
    artifact_files = [
        ("request", "request.json", False),
        ("result", "result.json", False),
        ("run_result", "run_result.json", False),
        ("events", "events.jsonl", include_jsonl),
        ("log", "log.txt", include_log),
        ("diff", "changes.patch", include_diff),
        ("status", "status.json", False),
    ]
    
    for artifact_type, filename, include_content in artifact_files:
        path = run_dir / filename
        if path.exists():
            artifacts["paths"][artifact_type] = str(path)
            
            if include_content:
                content = await _read_artifact_content(
                    path, 
                    artifact_type,
                    run_manager,
                )
                if content is not None:
                    artifacts["content"][artifact_type] = content
    
    # Add summary from result.json if available
    result_path = run_dir / "result.json"
    if result_path.exists():
        try:
            async with aiofiles.open(result_path, "r", encoding="utf-8") as f:
                result_data = json.loads(await f.read())
            artifacts["summary"] = {
                "status": result_data.get("status"),
                "duration": result_data.get("duration"),
                "started_at": result_data.get("started_at"),
                "finished_at": result_data.get("finished_at"),
            }
        except Exception as e:
            logger.warning("Failed to read result summary", error=str(e))
    
    # Add file list from events if available
    if include_jsonl and "events" in artifacts["content"]:
        events_data = artifacts["content"]["events"]
        if isinstance(events_data, dict):
            artifacts["files_changed"] = events_data.get("changed_file_paths", [])
            artifacts["commands_run"] = events_data.get("command_list", [])
    
    return artifacts


async def _read_artifact_content(
    path: Path,
    artifact_type: str,
    run_manager: RunManager,
) -> Optional[dict | str]:
    """Read and parse artifact content."""
    try:
        if artifact_type == "events":
            # Parse JSONL events
            parsed = await parse_jsonl_file(path)
            return {
                "events_count": len(parsed.events),
                "changed_file_paths": parsed.changed_file_paths,
                "command_list": parsed.command_list,
                "has_errors": parsed.has_errors,
                "errors": [str(e) for e in parsed.errors],
            }
        
        elif artifact_type == "diff":
            # Read patch content
            async with aiofiles.open(path, "r", encoding="utf-8") as f:
                content = await f.read()
            return content
        
        elif artifact_type == "log":
            # Read log content (truncate if too large)
            async with aiofiles.open(path, "r", encoding="utf-8") as f:
                content = await f.read()
            if len(content) > 50000:  # 50KB limit
                content = content[:25000] + "\n\n... [truncated] ...\n\n" + content[-25000:]
            return content
        
        else:
            # Read JSON files
            async with aiofiles.open(path, "r", encoding="utf-8") as f:
                return json.loads(await f.read())
                
    except Exception as e:
        logger.warning(
            "Failed to read artifact content",
            path=str(path),
            artifact_type=artifact_type,
            error=str(e),
        )
        return None


async def list_run_artifacts(
    run_id: str,
    run_manager: RunManager,
) -> list[dict]:
    """
    List available artifacts for a run without content.
    
    Args:
        run_id: The run identifier
        run_manager: RunManager instance
        
    Returns:
        List of artifact metadata
    """
    run_dir = run_manager.runs_path / run_id
    
    if not run_dir.exists():
        return []
    
    artifacts = []
    
    for path in run_dir.iterdir():
        if path.is_file():
            stat = path.stat()
            artifacts.append({
                "name": path.name,
                "path": str(path),
                "size_bytes": stat.st_size,
                "modified_at": stat.st_mtime,
            })
    
    return artifacts
