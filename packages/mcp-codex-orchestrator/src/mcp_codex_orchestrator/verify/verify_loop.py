"""
MCP Codex Orchestrator - Verify Loop

Automatický verify loop po Codex změnách.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Callable, Awaitable

import structlog

from mcp_codex_orchestrator.verify.verify_result import CheckResult, VerifyResult, VerifyStatus
from mcp_codex_orchestrator.verify.test_runner import TestRunner
from mcp_codex_orchestrator.verify.lint_checker import LintChecker
from mcp_codex_orchestrator.verify.build_runner import BuildRunner

logger = structlog.get_logger(__name__)


@dataclass
class VerifyConfig:
    """Konfigurace verify loop."""
    
    # Which checks to run
    run_tests: bool = True
    run_lint: bool = True
    run_build: bool = False
    
    # Auto-fix settings
    max_fix_attempts: int = 2
    max_iterations: int = 3  # Alias for max_fix_attempts
    auto_fix_lint: bool = True
    
    # Commands (None = auto-detect/default)
    test_command: Optional[str] = None
    lint_command: Optional[str] = None
    build_command: Optional[str] = None
    
    # Timeouts
    test_timeout: int = 120
    lint_timeout: int = 60
    build_timeout: int = 300
    
    # Behavior
    fail_fast: bool = False  # Stop on first failure
    continue_on_lint_failure: bool = True  # Continue even if lint fails


# Type alias for Codex runner callback
CodexRunnerCallback = Callable[[str], Awaitable[None]]


class VerifyLoop:
    """Automatický verify loop po Codex změnách."""
    
    def __init__(
        self,
        workspace_path: Path,
        config: Optional[VerifyConfig] = None,
    ):
        """
        Initialize verify loop.
        
        Args:
            workspace_path: Path to workspace to verify
            config: Verification configuration
        """
        self.workspace_path = Path(workspace_path)
        self.config = config or VerifyConfig()
        
        # Initialize runners
        self.test_runner = TestRunner(
            workspace_path=self.workspace_path,
            timeout=self.config.test_timeout,
        )
        self.lint_checker = LintChecker(
            workspace_path=self.workspace_path,
            timeout=self.config.lint_timeout,
        )
        self.build_runner = BuildRunner(
            workspace_path=self.workspace_path,
            timeout=self.config.build_timeout,
        )
    
    async def run(self, run_id: str) -> VerifyResult:
        """
        Run full verify loop (single pass).
        
        Args:
            run_id: Run identifier for logging
            
        Returns:
            VerifyResult with all check outcomes
        """
        logger.info("Starting verify loop", run_id=run_id)
        start_time = asyncio.get_event_loop().time()
        
        result = VerifyResult(passed=True)
        
        try:
            # Step 1: Run lint
            if self.config.run_lint:
                result.lint = await self._run_lint()
                if not result.lint.passed:
                    result.passed = False
                    if self.config.fail_fast and not self.config.continue_on_lint_failure:
                        return self._finalize_result(result, start_time)
            
            # Step 2: Run tests
            if self.config.run_tests:
                result.tests = await self._run_tests()
                if not result.tests.passed:
                    result.passed = False
                    if self.config.fail_fast:
                        return self._finalize_result(result, start_time)
            
            # Step 3: Run build (optional)
            if self.config.run_build:
                result.build = await self._run_build()
                if not result.build.passed:
                    result.passed = False
            
            return self._finalize_result(result, start_time)
            
        except Exception as e:
            logger.exception("Verify loop error", run_id=run_id, error=str(e))
            result.passed = False
            result.error = str(e)
            return self._finalize_result(result, start_time)
    
    async def run_with_auto_fix(
        self,
        run_id: str,
        codex_runner: Optional[CodexRunnerCallback] = None,
    ) -> VerifyResult:
        """
        Run verify loop with automatic fix attempts.
        
        Args:
            run_id: Run identifier
            codex_runner: Callback to run Codex for fixes
            
        Returns:
            VerifyResult with fix attempts tracked
        """
        logger.info(
            "Starting verify loop with auto-fix",
            run_id=run_id,
            max_attempts=self.config.max_fix_attempts,
        )
        
        start_time = asyncio.get_event_loop().time()
        attempt = 0
        last_result: Optional[VerifyResult] = None
        
        while attempt <= self.config.max_fix_attempts:
            result = await self.run(run_id)
            result.fix_attempts = attempt
            last_result = result
            
            if result.passed:
                logger.info("Verify loop passed", attempt=attempt)
                return self._finalize_result(result, start_time)
            
            if attempt >= self.config.max_fix_attempts:
                logger.warning(
                    "Max fix attempts reached",
                    attempts=attempt,
                    failed_checks=result.failed_checks,
                )
                return self._finalize_result(result, start_time)
            
            # Try auto-fix for lint
            if result.lint and not result.lint.passed and self.config.auto_fix_lint:
                logger.info("Attempting lint auto-fix")
                await self.lint_checker.fix()
            
            # Use Codex to fix remaining issues
            if codex_runner and (not result.all_checks_passed):
                fix_prompt = self._generate_fix_prompt(result)
                result.fix_prompts.append(fix_prompt)
                
                logger.info("Running Codex auto-fix", attempt=attempt + 1)
                try:
                    await codex_runner(fix_prompt)
                except Exception as e:
                    logger.warning("Codex fix failed", error=str(e))
            
            attempt += 1
        
        # Return last result
        if last_result:
            return self._finalize_result(last_result, start_time)
        
        return VerifyResult(passed=False, error="No verification results")
    
    async def _run_lint(self) -> CheckResult:
        """Run lint check."""
        return await self.lint_checker.check(
            command=self.config.lint_command,
        )
    
    async def _run_tests(self) -> CheckResult:
        """Run tests."""
        return await self.test_runner.run(
            command=self.config.test_command,
        )
    
    async def _run_build(self) -> CheckResult:
        """Run build."""
        command = self.config.build_command
        
        # Auto-detect if not specified
        if not command:
            command = await self.build_runner.detect_build_command()
        
        if not command:
            return CheckResult(
                name="build",
                status=VerifyStatus.SKIPPED,
                output="",
                error="No build command configured or detected",
            )
        
        return await self.build_runner.run(command=command)
    
    def _generate_fix_prompt(self, result: VerifyResult) -> str:
        """Generate fix prompt from failed verification."""
        parts = ["Fix the following issues:\n"]
        
        if result.lint and not result.lint.passed:
            output = result.lint.output[:2000]  # Limit output size
            parts.append(f"## Lint errors:\n```\n{output}\n```\n")
        
        if result.tests and not result.tests.passed:
            output = result.tests.output[:2000]
            parts.append(f"## Test failures:\n```\n{output}\n```\n")
        
        if result.build and not result.build.passed:
            output = result.build.output[:2000]
            parts.append(f"## Build errors:\n```\n{output}\n```\n")
        
        parts.append("\nFix all issues and ensure all checks pass.")
        
        return "\n".join(parts)
    
    def _finalize_result(
        self,
        result: VerifyResult,
        start_time: float,
    ) -> VerifyResult:
        """Finalize result with duration."""
        result.duration_seconds = asyncio.get_event_loop().time() - start_time
        result.timestamp = datetime.utcnow()
        
        logger.info(
            "Verify loop completed",
            passed=result.passed,
            duration=result.duration_seconds,
            failed_checks=result.failed_checks,
            fix_attempts=result.fix_attempts,
        )
        
        return result


# Convenience functions

async def verify_workspace(
    workspace_path: Path,
    run_tests: bool = True,
    run_lint: bool = True,
    run_build: bool = False,
) -> VerifyResult:
    """
    Quick verify of workspace.
    
    Args:
        workspace_path: Path to workspace
        run_tests: Run tests
        run_lint: Run lint
        run_build: Run build
        
    Returns:
        VerifyResult
    """
    config = VerifyConfig(
        run_tests=run_tests,
        run_lint=run_lint,
        run_build=run_build,
    )
    
    loop = VerifyLoop(workspace_path, config)
    return await loop.run("quick-verify")
