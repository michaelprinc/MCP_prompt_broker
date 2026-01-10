"""
MCP Codex Orchestrator - Gemini Artifacts Tool

Collect artifacts from a completed Gemini run.
"""

import json
from pathlib import Path
from typing import Optional

import aiofiles
import structlog

from mcp_codex_orchestrator.orchestrator.gemini_run_manager import GeminiRunManager

logger = structlog.get_logger(__name__)


async def handle_gemini_artifacts(
    run_id: str,
    run_manager: GeminiRunManager,
    artifact_type: str = "all",
) -> dict:
    """Get artifacts from a completed Gemini run."""
    logger.info("Getting Gemini run artifacts", run_id=run_id, artifact_type=artifact_type)

    run_dir = run_manager.runs_path / run_id
    if not run_dir.exists():
        return {
            "success": False,
            "run_id": run_id,
            "error": f"Run {run_id} not found",
        }

    include_diff = artifact_type in ("all", "diffs")
    include_events = artifact_type in ("all", "events")
    include_log = artifact_type in ("all", "logs")
    include_response = artifact_type in ("all", "responses")
    include_result = artifact_type in ("all", "results")

    artifacts: dict = {
        "success": True,
        "run_id": run_id,
        "paths": {},
        "content": {},
    }

    artifact_files = [
        ("request", "request.json", False),
        ("run_result", "run_result.json", include_result),
        ("response", "response.json", include_response),
        ("events", "events.jsonl", include_events),
        ("log", "log.txt", include_log),
        ("diff", "changes.patch", include_diff),
        ("status", "status.json", False),
    ]

    for artifact_key, filename, include_content in artifact_files:
        path = run_dir / filename
        if path.exists():
            artifacts["paths"][artifact_key] = str(path)
            if include_content:
                content = await _read_artifact_content(path, artifact_key)
                if content is not None:
                    artifacts["content"][artifact_key] = content

    return artifacts


async def _read_artifact_content(
    path: Path,
    artifact_type: str,
) -> Optional[dict | str]:
    try:
        if artifact_type == "events":
            async with aiofiles.open(path, "r", encoding="utf-8") as f:
                lines = [line for line in (await f.read()).splitlines() if line.strip()]
            return {
                "events_count": len(lines),
            }
        if artifact_type == "diff":
            async with aiofiles.open(path, "r", encoding="utf-8") as f:
                return await f.read()
        if artifact_type == "log":
            async with aiofiles.open(path, "r", encoding="utf-8") as f:
                content = await f.read()
            if len(content) > 50000:
                content = content[:25000] + "\n\n... [truncated] ...\n\n" + content[-25000:]
            return content

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
