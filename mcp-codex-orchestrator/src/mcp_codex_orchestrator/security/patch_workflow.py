"""
MCP Codex Orchestrator - Patch Workflow

Bezpečný workflow pro generování a aplikaci změn přes patch soubory.
"""

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import aiofiles
import structlog

from mcp_codex_orchestrator.security.sandbox import SecurityError

logger = structlog.get_logger(__name__)


@dataclass
class PatchStats:
    """Statistics from a patch file."""
    files_changed: int = 0
    insertions: int = 0
    deletions: int = 0
    files: list[str] | None = None


@dataclass
class PatchResult:
    """Result of patch operation."""
    success: bool
    patch_path: Optional[Path] = None
    stats: Optional[PatchStats] = None
    error: Optional[str] = None


class PatchWorkflow:
    """Workflow pro bezpečnou aplikaci změn přes patch."""
    
    def __init__(self, runs_path: Path):
        """
        Initialize patch workflow.
        
        Args:
            runs_path: Path to runs directory for storing patches
        """
        self.runs_path = Path(runs_path)
    
    async def generate_patch(
        self,
        workspace_path: Path,
        run_id: str,
        include_untracked: bool = True,
    ) -> PatchResult:
        """
        Generate patch from uncommitted changes.
        
        Args:
            workspace_path: Path to workspace with changes
            run_id: Run identifier for patch naming
            include_untracked: Include untracked files in patch
            
        Returns:
            PatchResult with path to generated patch
        """
        patch_path = self.runs_path / run_id / "changes.patch"
        patch_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Generate diff for tracked changes
            result = subprocess.run(
                ["git", "diff", "--no-color", "HEAD"],
                cwd=workspace_path,
                capture_output=True,
                text=True,
                timeout=30,
            )
            
            patch_content = result.stdout
            
            # Include untracked files if requested
            if include_untracked:
                untracked = subprocess.run(
                    ["git", "ls-files", "--others", "--exclude-standard"],
                    cwd=workspace_path,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                
                for file in untracked.stdout.strip().split("\n"):
                    if file:
                        file_path = workspace_path / file
                        if file_path.exists() and file_path.is_file():
                            content = file_path.read_text(encoding="utf-8", errors="replace")
                            patch_content += f"\n--- /dev/null\n+++ b/{file}\n"
                            patch_content += "@@ -0,0 +1,{} @@\n".format(len(content.splitlines()))
                            for line in content.splitlines():
                                patch_content += f"+{line}\n"
            
            # Write patch file
            async with aiofiles.open(patch_path, "w", encoding="utf-8") as f:
                await f.write(patch_content)
            
            # Get stats
            stats = await self._get_patch_stats(patch_path, workspace_path)
            
            logger.info(
                "Patch generated",
                run_id=run_id,
                patch_path=str(patch_path),
                files_changed=stats.files_changed,
            )
            
            return PatchResult(
                success=True,
                patch_path=patch_path,
                stats=stats,
            )
            
        except subprocess.TimeoutExpired:
            return PatchResult(success=False, error="Git diff timed out")
        except Exception as e:
            logger.exception("Failed to generate patch", run_id=run_id, error=str(e))
            return PatchResult(success=False, error=str(e))
    
    async def preview_patch(
        self,
        patch_path: Path,
        workspace_path: Path,
    ) -> dict:
        """
        Preview what the patch would change.
        
        Args:
            patch_path: Path to patch file
            workspace_path: Path to workspace for preview
            
        Returns:
            Dictionary with preview information
        """
        if not patch_path.exists():
            return {"error": "Patch file not found"}
        
        try:
            # Get stat output
            result = subprocess.run(
                ["git", "apply", "--stat", str(patch_path)],
                cwd=workspace_path,
                capture_output=True,
                text=True,
                timeout=30,
            )
            
            # Check if patch can be applied
            check_result = subprocess.run(
                ["git", "apply", "--check", str(patch_path)],
                cwd=workspace_path,
                capture_output=True,
                text=True,
                timeout=30,
            )
            
            can_apply = check_result.returncode == 0
            
            stats = self._parse_stat_output(result.stdout)
            
            return {
                "summary": result.stdout.strip(),
                "files_affected": stats.files or [],
                "insertions": stats.insertions,
                "deletions": stats.deletions,
                "can_apply": can_apply,
                "apply_errors": check_result.stderr if not can_apply else None,
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    async def apply_patch(
        self,
        patch_path: Path,
        workspace_path: Path,
        user_approved: bool = False,
        dry_run: bool = False,
    ) -> PatchResult:
        """
        Apply patch to workspace.
        
        Args:
            patch_path: Path to patch file
            workspace_path: Path to workspace
            user_approved: Whether user has approved the application
            dry_run: Only check if patch can be applied
            
        Returns:
            PatchResult indicating success or failure
            
        Raises:
            SecurityError: If user approval is required but not given
        """
        if not user_approved and not dry_run:
            raise SecurityError("Patch application requires user approval")
        
        if not patch_path.exists():
            return PatchResult(success=False, error="Patch file not found")
        
        try:
            cmd = ["git", "apply"]
            if dry_run:
                cmd.append("--check")
            cmd.append(str(patch_path))
            
            result = subprocess.run(
                cmd,
                cwd=workspace_path,
                capture_output=True,
                text=True,
                timeout=60,
            )
            
            if result.returncode == 0:
                logger.info(
                    "Patch applied successfully" if not dry_run else "Patch check passed",
                    patch_path=str(patch_path),
                    workspace=str(workspace_path),
                )
                return PatchResult(success=True, patch_path=patch_path)
            else:
                return PatchResult(
                    success=False,
                    patch_path=patch_path,
                    error=result.stderr or "Failed to apply patch",
                )
                
        except subprocess.TimeoutExpired:
            return PatchResult(success=False, error="Patch application timed out")
        except Exception as e:
            return PatchResult(success=False, error=str(e))
    
    async def revert_patch(
        self,
        patch_path: Path,
        workspace_path: Path,
    ) -> PatchResult:
        """
        Revert a previously applied patch.
        
        Args:
            patch_path: Path to patch file
            workspace_path: Path to workspace
            
        Returns:
            PatchResult indicating success or failure
        """
        if not patch_path.exists():
            return PatchResult(success=False, error="Patch file not found")
        
        try:
            result = subprocess.run(
                ["git", "apply", "--reverse", str(patch_path)],
                cwd=workspace_path,
                capture_output=True,
                text=True,
                timeout=60,
            )
            
            if result.returncode == 0:
                logger.info("Patch reverted", patch_path=str(patch_path))
                return PatchResult(success=True, patch_path=patch_path)
            else:
                return PatchResult(success=False, error=result.stderr)
                
        except Exception as e:
            return PatchResult(success=False, error=str(e))
    
    async def _get_patch_stats(
        self,
        patch_path: Path,
        workspace_path: Path,
    ) -> PatchStats:
        """Get statistics from patch file."""
        try:
            result = subprocess.run(
                ["git", "apply", "--stat", str(patch_path)],
                cwd=workspace_path,
                capture_output=True,
                text=True,
                timeout=30,
            )
            return self._parse_stat_output(result.stdout)
        except Exception:
            return PatchStats()
    
    def _parse_stat_output(self, stat_output: str) -> PatchStats:
        """Parse git apply --stat output."""
        lines = stat_output.strip().split("\n")
        files: list[str] = []
        insertions = 0
        deletions = 0
        
        for line in lines:
            # File lines look like: "file.py | 10 +++---"
            if "|" in line:
                parts = line.split("|")
                if len(parts) >= 1:
                    file_name = parts[0].strip()
                    if file_name:
                        files.append(file_name)
                
                if len(parts) >= 2:
                    changes = parts[1]
                    insertions += changes.count("+")
                    deletions += changes.count("-")
        
        return PatchStats(
            files_changed=len(files),
            insertions=insertions,
            deletions=deletions,
            files=files,
        )
