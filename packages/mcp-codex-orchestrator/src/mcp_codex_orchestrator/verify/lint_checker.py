"""
MCP Codex Orchestrator - Lint Checker

Integrace s ruff/black pro automatickou kontrolu kódu.
"""

import asyncio
import subprocess
from pathlib import Path
from typing import Optional

import structlog

from mcp_codex_orchestrator.models.verify_result import CheckResult, VerifyStatus

logger = structlog.get_logger(__name__)


class LintChecker:
    """Checker pro lint nástroje (ruff, black, flake8)."""
    
    DEFAULT_COMMAND = "ruff"
    DEFAULT_ARGS = ["check", "."]
    
    def __init__(
        self,
        workspace_path: Path,
        timeout: int = 60,
    ):
        """
        Initialize lint checker.
        
        Args:
            workspace_path: Path to workspace to lint
            timeout: Timeout for lint execution in seconds
        """
        self.workspace_path = Path(workspace_path)
        self.timeout = timeout
    
    async def check(
        self,
        command: Optional[str] = None,
        args: Optional[list[str]] = None,
    ) -> CheckResult:
        """
        Run lint check and return result.
        
        Args:
            command: Lint command (default: ruff check .)
            args: Additional arguments
            
        Returns:
            CheckResult with lint outcome
        """
        # Parse command if it's a string with arguments
        if command and " " in command:
            parts = command.split()
            cmd = parts[0]
            cmd_args = parts[1:]
        else:
            cmd = command or self.DEFAULT_COMMAND
            cmd_args = args or self.DEFAULT_ARGS.copy()
        
        full_command = [cmd] + cmd_args
        
        logger.info(
            "Running lint check",
            command=" ".join(full_command),
            workspace=str(self.workspace_path),
        )
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Run lint
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: subprocess.run(
                    full_command,
                    cwd=self.workspace_path,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                )
            )
            
            duration = asyncio.get_event_loop().time() - start_time
            output = result.stdout + "\n" + result.stderr
            
            if result.returncode == 0:
                status = VerifyStatus.PASSED
                logger.info("Lint check passed", duration=duration)
            else:
                status = VerifyStatus.FAILED
                logger.warning(
                    "Lint check failed",
                    exit_code=result.returncode,
                    issues=self._count_issues(output),
                )
            
            return CheckResult(
                name="lint",
                status=status,
                output=output,
                duration_seconds=duration,
            )
            
        except subprocess.TimeoutExpired:
            duration = asyncio.get_event_loop().time() - start_time
            logger.error("Lint check timed out", timeout=self.timeout)
            return CheckResult(
                name="lint",
                status=VerifyStatus.ERROR,
                output="",
                duration_seconds=duration,
                error=f"Lint check timed out after {self.timeout}s",
            )
            
        except FileNotFoundError:
            logger.warning("Lint command not found, trying fallback", command=cmd)
            # Try fallback linters
            return await self._try_fallback_linters()
            
        except Exception as e:
            logger.exception("Error running lint check", error=str(e))
            return CheckResult(
                name="lint",
                status=VerifyStatus.ERROR,
                output="",
                error=str(e),
            )
    
    async def _try_fallback_linters(self) -> CheckResult:
        """Try fallback linters if primary is not available."""
        fallbacks = [
            (["python", "-m", "ruff", "check", "."], "ruff"),
            (["flake8", "."], "flake8"),
            (["python", "-m", "flake8", "."], "flake8"),
        ]
        
        for cmd, name in fallbacks:
            try:
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda c=cmd: subprocess.run(
                        c,
                        cwd=self.workspace_path,
                        capture_output=True,
                        text=True,
                        timeout=self.timeout,
                    )
                )
                
                output = result.stdout + "\n" + result.stderr
                status = VerifyStatus.PASSED if result.returncode == 0 else VerifyStatus.FAILED
                
                return CheckResult(
                    name="lint",
                    status=status,
                    output=output,
                )
                
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        
        return CheckResult(
            name="lint",
            status=VerifyStatus.SKIPPED,
            output="",
            error="No lint tool available (tried ruff, flake8)",
        )
    
    def _count_issues(self, output: str) -> int:
        """Count number of lint issues in output."""
        # Simple heuristic: count lines with file paths and error codes
        count = 0
        for line in output.split("\n"):
            # Ruff/flake8 format: path:line:col: CODE message
            if ":" in line and any(c in line for c in ["E", "F", "W", "I", "N"]):
                count += 1
        return count
    
    async def fix(
        self,
        command: Optional[str] = None,
    ) -> CheckResult:
        """
        Run lint auto-fix.
        
        Args:
            command: Fix command (default: ruff check --fix .)
            
        Returns:
            CheckResult with fix outcome
        """
        if command:
            parts = command.split()
            cmd = parts[0]
            cmd_args = parts[1:]
        else:
            cmd = "ruff"
            cmd_args = ["check", "--fix", "."]
        
        full_command = [cmd] + cmd_args
        
        logger.info("Running lint auto-fix", command=" ".join(full_command))
        
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: subprocess.run(
                    full_command,
                    cwd=self.workspace_path,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                )
            )
            
            output = result.stdout + "\n" + result.stderr
            
            return CheckResult(
                name="lint-fix",
                status=VerifyStatus.PASSED if result.returncode == 0 else VerifyStatus.FAILED,
                output=output,
            )
            
        except Exception as e:
            return CheckResult(
                name="lint-fix",
                status=VerifyStatus.ERROR,
                output="",
                error=str(e),
            )
