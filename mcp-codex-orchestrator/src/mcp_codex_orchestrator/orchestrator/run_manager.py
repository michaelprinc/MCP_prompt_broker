"""
MCP Codex Orchestrator - Run Manager

Správa životního cyklu Codex běhů.
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
from mcp_codex_orchestrator.models.run_result import CodexRunResult, RunOutput, RunStatus
from mcp_codex_orchestrator.orchestrator.docker_client import DockerCodexClient
from mcp_codex_orchestrator.orchestrator.result_collector import ResultCollector
from mcp_codex_orchestrator.utils.markers import inject_mcp_instructions

logger = structlog.get_logger(__name__)


class RunManager:
    """Správce životního cyklu Codex běhů."""
    
    def __init__(
        self,
        workspace_path: Path,
        runs_path: Path,
        default_timeout: int = 300,
    ) -> None:
        """
        Initialize run manager.
        
        Args:
            workspace_path: Path to workspace directory
            runs_path: Path to runs directory
            default_timeout: Default timeout in seconds
        """
        self.workspace_path = Path(workspace_path).resolve()
        self.runs_path = Path(runs_path).resolve()
        self.default_timeout = default_timeout
        
        # Ensure directories exist
        self.workspace_path.mkdir(parents=True, exist_ok=True)
        self.runs_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.docker_client = DockerCodexClient()
        self.result_collector = ResultCollector()
        
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
            ):
                log_lines.append(line)
                
                # Write to log file in real-time
                async with aiofiles.open(log_file, "a", encoding="utf-8") as f:
                    await f.write(line)
            
            # Record finish time
            finished_at = datetime.now(timezone.utc)
            duration = (finished_at - started_at).total_seconds()
            
            # Collect and analyze result
            full_log = "".join(log_lines)
            result = await self.result_collector.collect(
                run_id=run_id,
                log=full_log,
                started_at=started_at,
                finished_at=finished_at,
            )
            
            # Save result
            await self._save_result(run_id, result)
            
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
            },
            "error": result.error,
            "startedAt": result.started_at.isoformat() if result.started_at else None,
            "finishedAt": result.finished_at.isoformat() if result.finished_at else None,
        }
        
        async with aiofiles.open(result_file, "w", encoding="utf-8") as f:
            await f.write(json.dumps(result_data, indent=2, ensure_ascii=False))
        
        logger.debug("Result saved", run_id=run_id, result_file=str(result_file))
    
    def close(self) -> None:
        """Close manager and cleanup resources."""
        self.docker_client.close()
