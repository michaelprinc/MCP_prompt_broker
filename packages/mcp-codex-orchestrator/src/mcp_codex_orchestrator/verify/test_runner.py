"""
MCP Codex Orchestrator - Test Runner

Integrace s pytest pro automatické testování.
"""

import asyncio
import subprocess
from pathlib import Path
from typing import Optional

import structlog

from mcp_codex_orchestrator.models.verify_result import CheckResult, VerifyStatus

logger = structlog.get_logger(__name__)


class TestRunner:
    """Runner pro pytest testy."""
    
    DEFAULT_COMMAND = "pytest"
    DEFAULT_ARGS = ["-v", "--tb=short", "-q"]
    
    def __init__(
        self,
        workspace_path: Path,
        timeout: int = 120,
    ):
        """
        Initialize test runner.
        
        Args:
            workspace_path: Path to workspace with tests
            timeout: Timeout for test execution in seconds
        """
        self.workspace_path = Path(workspace_path)
        self.timeout = timeout
    
    async def run(
        self,
        command: Optional[str] = None,
        args: Optional[list[str]] = None,
        test_path: Optional[str] = None,
    ) -> CheckResult:
        """
        Run tests and return result.
        
        Args:
            command: Test command (default: pytest)
            args: Additional arguments
            test_path: Specific test path to run
            
        Returns:
            CheckResult with test outcome
        """
        cmd = command or self.DEFAULT_COMMAND
        cmd_args = args or self.DEFAULT_ARGS.copy()
        
        if test_path:
            cmd_args.append(test_path)
        
        full_command = [cmd] + cmd_args
        
        logger.info(
            "Running tests",
            command=" ".join(full_command),
            workspace=str(self.workspace_path),
        )
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Run tests
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
                logger.info("Tests passed", duration=duration)
            else:
                status = VerifyStatus.FAILED
                logger.warning("Tests failed", exit_code=result.returncode)
            
            return CheckResult(
                name="tests",
                status=status,
                output=output,
                duration_seconds=duration,
            )
            
        except subprocess.TimeoutExpired:
            duration = asyncio.get_event_loop().time() - start_time
            logger.error("Tests timed out", timeout=self.timeout)
            return CheckResult(
                name="tests",
                status=VerifyStatus.ERROR,
                output="",
                duration_seconds=duration,
                error=f"Tests timed out after {self.timeout}s",
            )
            
        except FileNotFoundError:
            return CheckResult(
                name="tests",
                status=VerifyStatus.SKIPPED,
                output="",
                error=f"Test command '{cmd}' not found",
            )
            
        except Exception as e:
            logger.exception("Error running tests", error=str(e))
            return CheckResult(
                name="tests",
                status=VerifyStatus.ERROR,
                output="",
                error=str(e),
            )
    
    def parse_pytest_output(self, output: str) -> dict:
        """
        Parse pytest output for summary.
        
        Args:
            output: Pytest stdout
            
        Returns:
            Dictionary with parsed results
        """
        results = {
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "errors": 0,
        }
        
        # Look for summary line like "5 passed, 2 failed, 1 skipped"
        for line in output.split("\n"):
            line_lower = line.lower()
            if "passed" in line_lower or "failed" in line_lower:
                for word in line.split():
                    if word.isdigit():
                        # Next word after number is the type
                        continue
                    if "passed" in word.lower():
                        idx = line.split().index(word) - 1
                        if idx >= 0:
                            try:
                                results["passed"] = int(line.split()[idx])
                            except ValueError:
                                pass
                    elif "failed" in word.lower():
                        idx = line.split().index(word) - 1
                        if idx >= 0:
                            try:
                                results["failed"] = int(line.split()[idx])
                            except ValueError:
                                pass
                    elif "skipped" in word.lower():
                        idx = line.split().index(word) - 1
                        if idx >= 0:
                            try:
                                results["skipped"] = int(line.split()[idx])
                            except ValueError:
                                pass
        
        return results
