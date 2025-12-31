"""
MCP Codex Orchestrator - Build Runner

Runner pro build příkazy (npm build, cargo build, etc.).
"""

import asyncio
import subprocess
from pathlib import Path
from typing import Optional

import structlog

from mcp_codex_orchestrator.models.verify_result import CheckResult, VerifyStatus

logger = structlog.get_logger(__name__)


class BuildRunner:
    """Runner pro build příkazy."""
    
    def __init__(
        self,
        workspace_path: Path,
        timeout: int = 300,
    ):
        """
        Initialize build runner.
        
        Args:
            workspace_path: Path to workspace to build
            timeout: Timeout for build execution in seconds
        """
        self.workspace_path = Path(workspace_path)
        self.timeout = timeout
    
    async def run(
        self,
        command: str,
        args: Optional[list[str]] = None,
    ) -> CheckResult:
        """
        Run build command and return result.
        
        Args:
            command: Build command (e.g., "npm run build", "cargo build")
            args: Additional arguments
            
        Returns:
            CheckResult with build outcome
        """
        # Parse command if it contains spaces
        if " " in command:
            parts = command.split()
            cmd = parts[0]
            cmd_args = parts[1:]
        else:
            cmd = command
            cmd_args = []
        
        if args:
            cmd_args.extend(args)
        
        full_command = [cmd] + cmd_args
        
        logger.info(
            "Running build",
            command=" ".join(full_command),
            workspace=str(self.workspace_path),
        )
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Run build
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: subprocess.run(
                    full_command,
                    cwd=self.workspace_path,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    shell=True if " " in command else False,
                )
            )
            
            duration = asyncio.get_event_loop().time() - start_time
            output = result.stdout + "\n" + result.stderr
            
            if result.returncode == 0:
                status = VerifyStatus.PASSED
                logger.info("Build succeeded", duration=duration)
            else:
                status = VerifyStatus.FAILED
                logger.warning("Build failed", exit_code=result.returncode)
            
            return CheckResult(
                name="build",
                status=status,
                output=output,
                duration_seconds=duration,
            )
            
        except subprocess.TimeoutExpired:
            duration = asyncio.get_event_loop().time() - start_time
            logger.error("Build timed out", timeout=self.timeout)
            return CheckResult(
                name="build",
                status=VerifyStatus.ERROR,
                output="",
                duration_seconds=duration,
                error=f"Build timed out after {self.timeout}s",
            )
            
        except FileNotFoundError:
            return CheckResult(
                name="build",
                status=VerifyStatus.SKIPPED,
                output="",
                error=f"Build command '{cmd}' not found",
            )
            
        except Exception as e:
            logger.exception("Error running build", error=str(e))
            return CheckResult(
                name="build",
                status=VerifyStatus.ERROR,
                output="",
                error=str(e),
            )
    
    async def detect_build_command(self) -> Optional[str]:
        """
        Auto-detect build command based on project files.
        
        Returns:
            Detected build command or None
        """
        # Check for common project files
        checks = [
            ("package.json", "npm run build"),
            ("Cargo.toml", "cargo build"),
            ("Makefile", "make"),
            ("pyproject.toml", "python -m build"),
            ("setup.py", "python setup.py build"),
            ("CMakeLists.txt", "cmake --build ."),
            ("go.mod", "go build ./..."),
        ]
        
        for filename, command in checks:
            if (self.workspace_path / filename).exists():
                logger.debug("Detected build command", file=filename, command=command)
                return command
        
        return None
