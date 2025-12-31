"""
MCP Codex Orchestrator - Codex Git Diff Tool

Tool pro získání standardizovaného git diff výstupu.
"""

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import aiofiles
import structlog

from mcp_codex_orchestrator.orchestrator.run_manager import RunManager

logger = structlog.get_logger(__name__)


@dataclass
class DiffHunk:
    """Single diff hunk."""
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    content: str


@dataclass
class FileDiff:
    """Diff for a single file."""
    path: str
    old_path: Optional[str]
    status: str  # A=added, M=modified, D=deleted, R=renamed
    insertions: int
    deletions: int
    hunks: list[DiffHunk]


@dataclass
class ParsedDiff:
    """Parsed unified diff."""
    files: list[FileDiff]
    total_insertions: int
    total_deletions: int
    
    @property
    def files_changed(self) -> int:
        return len(self.files)
    
    @property
    def file_paths(self) -> list[str]:
        return [f.path for f in self.files]


async def handle_codex_git_diff(
    run_id: str,
    run_manager: RunManager,
    format: str = "unified",
) -> dict:
    """
    Get standardized git diff output for a run.
    
    Args:
        run_id: The run identifier
        run_manager: RunManager instance
        format: Diff format (unified, stat, name-only)
        
    Returns:
        Dictionary with diff information
    """
    logger.info("Getting git diff", run_id=run_id, format=format)
    
    run_dir = run_manager.runs_path / run_id
    diff_file = run_dir / "changes.patch"
    
    # Try to read existing patch file
    if diff_file.exists():
        async with aiofiles.open(diff_file, "r", encoding="utf-8") as f:
            diff_content = await f.read()
    else:
        # Generate from workspace (if run modified workspace)
        diff_content = await _generate_diff_from_workspace(
            run_manager.workspace_path,
            format,
        )
    
    if not diff_content:
        return {
            "run_id": run_id,
            "format": format,
            "raw_diff": "",
            "files_changed": 0,
            "insertions": 0,
            "deletions": 0,
            "message": "No changes detected",
        }
    
    # Parse diff based on format
    if format == "unified":
        parsed = parse_unified_diff(diff_content)
        return {
            "run_id": run_id,
            "format": format,
            "raw_diff": diff_content,
            "files_changed": parsed.files_changed,
            "file_paths": parsed.file_paths,
            "insertions": parsed.total_insertions,
            "deletions": parsed.total_deletions,
            "files": [
                {
                    "path": f.path,
                    "status": f.status,
                    "insertions": f.insertions,
                    "deletions": f.deletions,
                }
                for f in parsed.files
            ],
        }
    
    elif format == "stat":
        return {
            "run_id": run_id,
            "format": format,
            "stat": diff_content,
        }
    
    elif format == "name-only":
        files = [line.strip() for line in diff_content.split("\n") if line.strip()]
        return {
            "run_id": run_id,
            "format": format,
            "files": files,
            "files_changed": len(files),
        }
    
    return {
        "run_id": run_id,
        "format": format,
        "raw_diff": diff_content,
    }


async def _generate_diff_from_workspace(
    workspace_path: Path,
    format: str,
) -> str:
    """Generate diff from workspace using git."""
    try:
        if format == "unified":
            cmd = ["git", "diff", "--no-color", "HEAD"]
        elif format == "stat":
            cmd = ["git", "diff", "--stat", "--no-color", "HEAD"]
        elif format == "name-only":
            cmd = ["git", "diff", "--name-only", "HEAD"]
        else:
            cmd = ["git", "diff", "--no-color", "HEAD"]
        
        result = subprocess.run(
            cmd,
            cwd=workspace_path,
            capture_output=True,
            text=True,
            timeout=30,
        )
        
        return result.stdout
        
    except Exception as e:
        logger.warning("Failed to generate diff from workspace", error=str(e))
        return ""


def parse_unified_diff(diff_content: str) -> ParsedDiff:
    """
    Parse unified diff format.
    
    Args:
        diff_content: Raw unified diff string
        
    Returns:
        ParsedDiff with structured data
    """
    files: list[FileDiff] = []
    current_file: Optional[FileDiff] = None
    current_hunk: Optional[DiffHunk] = None
    hunk_lines: list[str] = []
    
    lines = diff_content.split("\n")
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # New file diff
        if line.startswith("diff --git"):
            # Save previous file
            if current_file is not None:
                if current_hunk is not None:
                    current_hunk.content = "\n".join(hunk_lines)
                    current_file.hunks.append(current_hunk)
                files.append(current_file)
            
            # Parse file paths from "diff --git a/path b/path"
            parts = line.split()
            if len(parts) >= 4:
                old_path = parts[2][2:] if parts[2].startswith("a/") else parts[2]
                new_path = parts[3][2:] if parts[3].startswith("b/") else parts[3]
            else:
                old_path = new_path = "unknown"
            
            current_file = FileDiff(
                path=new_path,
                old_path=old_path if old_path != new_path else None,
                status="M",
                insertions=0,
                deletions=0,
                hunks=[],
            )
            current_hunk = None
            hunk_lines = []
        
        # File status indicators
        elif line.startswith("new file"):
            if current_file:
                current_file.status = "A"
        elif line.startswith("deleted file"):
            if current_file:
                current_file.status = "D"
        elif line.startswith("rename"):
            if current_file:
                current_file.status = "R"
        
        # Hunk header
        elif line.startswith("@@"):
            # Save previous hunk
            if current_hunk is not None and current_file is not None:
                current_hunk.content = "\n".join(hunk_lines)
                current_file.hunks.append(current_hunk)
            
            # Parse hunk header "@@  -old_start,old_count +new_start,new_count @@"
            hunk_parts = line.split()
            old_info = hunk_parts[1] if len(hunk_parts) > 1 else "-0,0"
            new_info = hunk_parts[2] if len(hunk_parts) > 2 else "+0,0"
            
            old_start, old_count = _parse_hunk_range(old_info[1:])  # Remove -
            new_start, new_count = _parse_hunk_range(new_info[1:])  # Remove +
            
            current_hunk = DiffHunk(
                old_start=old_start,
                old_count=old_count,
                new_start=new_start,
                new_count=new_count,
                content="",
            )
            hunk_lines = []
        
        # Diff lines
        elif current_hunk is not None:
            hunk_lines.append(line)
            if current_file:
                if line.startswith("+") and not line.startswith("+++"):
                    current_file.insertions += 1
                elif line.startswith("-") and not line.startswith("---"):
                    current_file.deletions += 1
        
        i += 1
    
    # Save last file
    if current_file is not None:
        if current_hunk is not None:
            current_hunk.content = "\n".join(hunk_lines)
            current_file.hunks.append(current_hunk)
        files.append(current_file)
    
    # Calculate totals
    total_insertions = sum(f.insertions for f in files)
    total_deletions = sum(f.deletions for f in files)
    
    return ParsedDiff(
        files=files,
        total_insertions=total_insertions,
        total_deletions=total_deletions,
    )


def _parse_hunk_range(range_str: str) -> tuple[int, int]:
    """Parse hunk range like '10,5' or '10'."""
    if "," in range_str:
        parts = range_str.split(",")
        return int(parts[0]), int(parts[1])
    else:
        return int(range_str), 1
