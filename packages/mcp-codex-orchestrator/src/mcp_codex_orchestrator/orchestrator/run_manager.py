"""
MCP Codex Orchestrator - Run Manager v2.0

Správa životního cyklu Codex běhů.
Rozšířeno o security_mode, verify loop, JSONL output.
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiofiles
import structlog

from mcp_codex_orchestrator.models.run_request import CodexRunRequest
from mcp_codex_orchestrator.models.run_result import (
    CodexRunResult,
    RunOutput,
    RunProvider,
    RunResult,
    RunStatus,
)
from mcp_codex_orchestrator.orchestrator.docker_client import DockerCodexClient
from mcp_codex_orchestrator.orchestrator.result_collector import ResultCollector
from mcp_codex_orchestrator.security.modes import SecurityMode
from mcp_codex_orchestrator.security.patch_workflow import PatchWorkflow
from mcp_codex_orchestrator.verify.verify_loop import VerifyConfig, VerifyLoop
from mcp_codex_orchestrator.utils.markers import inject_mcp_instructions
from mcp_codex_orchestrator.utils.sanitize import sanitize_text

logger = structlog.get_logger(__name__)


class RunManager:
    """Správce životního cyklu Codex běhů."""
    
    def __init__(
        self,
        workspace_path: Path,
        runs_path: Path,
        schemas_path: Path | None = None,
        default_timeout: int = 300,
    ) -> None:
        """
        Initialize run manager.
        
        Args:
            workspace_path: Path to workspace directory
            runs_path: Path to runs directory
            schemas_path: Path to JSON schemas directory
            default_timeout: Default timeout in seconds
        """
        self.workspace_path = Path(workspace_path).resolve()
        self.runs_path = Path(runs_path).resolve()
        self.schemas_path = Path(schemas_path).resolve() if schemas_path else None
        self.default_timeout = default_timeout
        
        # Ensure directories exist
        self.workspace_path.mkdir(parents=True, exist_ok=True)
        self.runs_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.docker_client = DockerCodexClient()
        self.result_collector = ResultCollector()
        self.patch_workflow = PatchWorkflow(self.runs_path)
        
        # Track active runs
        self._active_runs: dict[str, asyncio.Task[Any]] = {}
    
    def generate_run_id(self) -> str:
        """Generate a unique run ID."""
        return str(uuid.uuid4())
    
    async def create_run(self, request: CodexRunRequest) -> str:
        """
        Create a new run.
        
        Args:
            request: The run request
            
        Returns:
            The generated run ID
        """
        run_id = self.generate_run_id()
        run_dir = self.runs_path / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        
        # Create request.json
        request_file = run_dir / "request.json"
        request_data = {
            "runId": run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "prompt": request.prompt,
            "mode": request.mode,
            "repo": request.repo,
            "workingDir": request.working_dir,
            "timeout": request.timeout,
            "envVars": request.env_vars,
            # V2.0 fields
            "securityMode": request.security_mode,
            "verify": request.verify,
            "outputSchema": request.output_schema,
            "jsonOutput": request.json_output,
        }
        
        async with aiofiles.open(request_file, "w", encoding="utf-8") as f:
            await f.write(json.dumps(request_data, indent=2, ensure_ascii=False))
        
        logger.info("Run created", run_id=run_id, run_dir=str(run_dir))
        
        return run_id
    
    async def execute_run(self, run_id: str) -> CodexRunResult:
        """
        Execute a run.
        
        Args:
            run_id: The run ID
            
        Returns:
            The run result
        """
        run_dir = self.runs_path / run_id
        request_file = run_dir / "request.json"
        log_file = run_dir / "log.txt"
        
        # Load request
        async with aiofiles.open(request_file, "r", encoding="utf-8") as f:
            request_data = json.loads(await f.read())
        
        # Extract request parameters
        prompt = request_data["prompt"]
        mode = request_data.get("mode", "full-auto")
        timeout = request_data.get("timeout", self.default_timeout)
        working_dir = request_data.get("workingDir")
        env_vars = request_data.get("envVars")
        repo = request_data.get("repo")
        # V2.0 fields
        security_mode_str = request_data.get("securityMode", "workspace_write")
        security_mode = SecurityMode(security_mode_str)
        verify_enabled = request_data.get("verify", False)
        output_schema = request_data.get("outputSchema")
        json_output = request_data.get("jsonOutput", True)
        
        # Determine workspace path
        workspace = Path(repo) if repo else self.workspace_path
        
        # Inject MCP instructions into prompt
        enhanced_prompt = inject_mcp_instructions(prompt)
        
        # Record start time
        started_at = datetime.now(timezone.utc)
        
        # Collect log output
        log_lines: list[str] = []
        
        try:
            # Check Docker availability
            if not await self.docker_client.check_docker_available():
                return CodexRunResult(
                    run_id=run_id,
                    status=RunStatus.ERROR,
                    error="Docker is not available",
                    started_at=started_at,
                    finished_at=datetime.now(timezone.utc),
                )
            
            # Execute in Docker container
            async for line in self.docker_client.run_codex(
                run_id=run_id,
                prompt=enhanced_prompt,
                mode=mode,
                workspace_path=workspace,
                runs_path=self.runs_path,
                timeout=timeout,
                env_vars=env_vars,
                working_dir=working_dir,
                # V2.0 parameters
                json_output=json_output,
                output_schema=output_schema,
                security_mode=security_mode,
                schemas_path=self.schemas_path,
            ):
                sanitized_line = sanitize_text(line)
                log_lines.append(sanitized_line)
                
                # Write to log file in real-time
                async with aiofiles.open(log_file, "a", encoding="utf-8") as f:
                    await f.write(sanitized_line)
            
            # Record finish time
            finished_at = datetime.now(timezone.utc)
            duration = (finished_at - started_at).total_seconds()
            
            # Collect and analyze result
            full_log = "".join(log_lines)
            exit_code = self._extract_exit_code(full_log)
            result = await self.result_collector.collect(
                run_id=run_id,
                log=full_log,
                started_at=started_at,
                finished_at=finished_at,
                exit_code=exit_code,
            )
            
            # Run verify loop if enabled and run was successful
            if verify_enabled and result.status == RunStatus.SUCCESS:
                logger.info("Running verify loop", run_id=run_id)
                verify_config = VerifyConfig(
                    run_tests=True,
                    run_lint=True,
                    run_build=False,  # Optional, can be enabled later
                    max_iterations=3,
                )
                verify_loop = VerifyLoop(
                    workspace_path=workspace,
                    config=verify_config,
                )
                verify_result = await verify_loop.run(run_id)
                verify_payload = verify_result.to_dict()

                # Add verify results to output
                if result.output:
                    result.output.verify_result = verify_payload

                # Update status if verify failed
                if not verify_payload.get("success", False):
                    logger.warning(
                        "Verify loop failed",
                        run_id=run_id,
                        errors=verify_payload.get("errors"),
                    )
            
            # Save result
            await self._save_result(run_id, result)
            await self._save_run_result(
                run_id=run_id,
                provider=RunProvider.CODEX,
                result=result,
                workspace=workspace,
                stdout=full_log,
                stderr="",
                exit_code=exit_code,
            )
            
            return result
            
        except asyncio.TimeoutError:
            finished_at = datetime.now(timezone.utc)
            duration = (finished_at - started_at).total_seconds()
            
            result = CodexRunResult(
                run_id=run_id,
                status=RunStatus.TIMEOUT,
                duration=duration,
                output=RunOutput(
                    full_log="".join(log_lines),
                ),
                error=f"Run timed out after {timeout} seconds",
                started_at=started_at,
                finished_at=finished_at,
            )
            
            await self._save_result(run_id, result)
            await self._save_run_result(
                run_id=run_id,
                provider=RunProvider.CODEX,
                result=result,
                workspace=workspace,
                stdout="".join(log_lines),
                stderr="",
                exit_code=None,
            )
            return result
            
        except Exception as e:
            finished_at = datetime.now(timezone.utc)
            duration = (finished_at - started_at).total_seconds()
            
            logger.exception("Run failed", run_id=run_id, error=str(e))
            
            result = CodexRunResult(
                run_id=run_id,
                status=RunStatus.ERROR,
                duration=duration,
                output=RunOutput(
                    full_log="".join(log_lines),
                ),
                error=str(e),
                started_at=started_at,
                finished_at=finished_at,
            )
            
            await self._save_result(run_id, result)
            await self._save_run_result(
                run_id=run_id,
                provider=RunProvider.CODEX,
                result=result,
                workspace=workspace,
                stdout="".join(log_lines),
                stderr="",
                exit_code=None,
            )
            return result
    
    async def cancel_run(self, run_id: str) -> None:
        """
        Cancel a running run.
        
        Args:
            run_id: The run ID to cancel
        """
        if run_id in self._active_runs:
            task = self._active_runs[run_id]
            task.cancel()
            
            try:
                await task
            except asyncio.CancelledError:
                pass
            
            del self._active_runs[run_id]
            
            logger.info("Run cancelled", run_id=run_id)
    
    async def get_run_status(self, run_id: str) -> RunStatus:
        """
        Get the status of a run.
        
        Args:
            run_id: The run ID
            
        Returns:
            The run status
        """
        run_dir = self.runs_path / run_id
        result_file = run_dir / "result.json"
        
        if result_file.exists():
            async with aiofiles.open(result_file, "r", encoding="utf-8") as f:
                result_data = json.loads(await f.read())
            return RunStatus(result_data.get("status", "error"))
        
        if run_id in self._active_runs:
            return RunStatus.RUNNING
        
        request_file = run_dir / "request.json"
        if request_file.exists():
            return RunStatus.PENDING
        
        return RunStatus.ERROR
    
    async def _save_result(self, run_id: str, result: CodexRunResult) -> None:
        """Save run result to file."""
        run_dir = self.runs_path / run_id
        result_file = run_dir / "result.json"
        
        result_data = {
            "runId": result.run_id,
            "status": result.status.value,
            "exitCode": result.exit_code,
            "duration": result.duration,
            "marker": result.marker,
            "output": {
                "summary": result.output.summary,
                "filesChanged": result.output.files_changed,
                "fullLog": result.output.full_log,
                # V2.0 fields
                "verifyResult": result.output.verify_result,
                "jsonlEvents": result.output.jsonl_events,
            },
            "error": result.error,
            "startedAt": result.started_at.isoformat() if result.started_at else None,
            "finishedAt": result.finished_at.isoformat() if result.finished_at else None,
        }
        
        async with aiofiles.open(result_file, "w", encoding="utf-8") as f:
            await f.write(json.dumps(result_data, indent=2, ensure_ascii=False))
        
        logger.debug("Result saved", run_id=run_id, result_file=str(result_file))

    async def _save_run_result(
        self,
        run_id: str,
        provider: RunProvider,
        result: CodexRunResult,
        workspace: Path,
        stdout: str,
        stderr: str,
        exit_code: int | None,
    ) -> None:
        """Save provider-agnostic run result to file."""
        run_dir = self.runs_path / run_id
        result_file = run_dir / "run_result.json"

        diff_content = ""
        files_changed: list[str] = []

        patch_result = await self.patch_workflow.generate_patch(
            workspace_path=workspace,
            run_id=run_id,
            include_untracked=True,
        )
        if patch_result.success and patch_result.patch_path:
            try:
                async with aiofiles.open(patch_result.patch_path, "r", encoding="utf-8") as f:
                    diff_content = await f.read()
            except Exception as e:
                logger.warning("Failed to read patch content", error=str(e))

            if patch_result.stats and patch_result.stats.files:
                files_changed = patch_result.stats.files

        if not files_changed:
            files_changed = result.output.files_changed

        run_result = RunResult(
            run_id=run_id,
            provider=provider,
            status=result.status,
            exit_code=exit_code,
            duration=result.duration,
            stdout=stdout,
            stderr=stderr,
            raw_events=result.output.jsonl_events or None,
            files_changed=files_changed,
            diff=diff_content,
            summary=result.output.summary,
            verify_result=result.output.verify_result,
            error=result.error,
            started_at=result.started_at,
            finished_at=result.finished_at,
        )

        async with aiofiles.open(result_file, "w", encoding="utf-8") as f:
            await f.write(run_result.json(indent=2, ensure_ascii=False))

        logger.debug("RunResult saved", run_id=run_id, result_file=str(result_file))

    @staticmethod
    def _extract_exit_code(log: str) -> int | None:
        """Extract container exit code from log output."""
        if not log:
            return None
        for line in reversed(log.splitlines()):
            line = line.strip()
            if "Container exited with code" in line:
                parts = line.rsplit(" ", 1)
                if len(parts) == 2:
                    try:
                        return int(parts[1].strip("]"))
                    except ValueError:
                        return None
        return None
    
    def close(self) -> None:
        """Close manager and cleanup resources."""
        self.docker_client.close()
