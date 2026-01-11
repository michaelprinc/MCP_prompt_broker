"""
MCP Codex Orchestrator - Gemini Run Manager

Manage Gemini CLI runs inside Docker containers.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiofiles
import structlog

from mcp_codex_orchestrator.models.gemini_run_request import GeminiRunRequest
from mcp_codex_orchestrator.models.run_result import RunProvider, RunResult, RunStatus
from mcp_codex_orchestrator.orchestrator.docker_gemini_client import DockerGeminiClient
from mcp_codex_orchestrator.security.patch_workflow import PatchWorkflow
from mcp_codex_orchestrator.utils.markers import (
    extract_summary_from_log,
    inject_mcp_instructions,
    marker_to_status,
    parse_marker,
)
from mcp_codex_orchestrator.utils.sanitize import sanitize_text
from mcp_codex_orchestrator.verify.verify_loop import VerifyConfig, VerifyLoop

logger = structlog.get_logger(__name__)


class GeminiRunManager:
    """Manager for Gemini CLI runs."""

    def __init__(
        self,
        workspace_path: Path,
        runs_path: Path,
        default_timeout: int = 300,
    ) -> None:
        self.workspace_path = Path(workspace_path).resolve()
        self.runs_path = Path(runs_path).resolve()
        self.default_timeout = default_timeout

        self.workspace_path.mkdir(parents=True, exist_ok=True)
        self.runs_path.mkdir(parents=True, exist_ok=True)

        self.docker_client = DockerGeminiClient()
        self.patch_workflow = PatchWorkflow(self.runs_path)

        self._active_runs: dict[str, asyncio.Task[Any]] = {}

    def generate_run_id(self) -> str:
        """Generate a unique run ID."""
        return str(uuid.uuid4())

    async def create_run(self, request: GeminiRunRequest) -> str:
        """Create a new Gemini run and persist request data."""
        run_id = self.generate_run_id()
        run_dir = self.runs_path / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        request_file = run_dir / "request.json"
        request_data = {
            "runId": run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "provider": "gemini",
            "task": request.task,
            "accessMode": request.access_mode,
            "repositoryPath": request.repository_path,
            "workingDirectory": request.working_directory,
            "timeoutSeconds": request.timeout_seconds,
            "environmentVariables": request.environment_variables,
            "securityMode": request.security_mode,
            "intent": request.intent,
            "verify": request.verify,
            "outputFormat": request.output_format,
        }

        async with aiofiles.open(request_file, "w", encoding="utf-8") as f:
            await f.write(json.dumps(request_data, indent=2, ensure_ascii=False))

        logger.info("Gemini run created", run_id=run_id, run_dir=str(run_dir))
        return run_id

    async def execute_run(self, run_id: str) -> RunResult:
        """Execute a Gemini run."""
        run_dir = self.runs_path / run_id
        request_file = run_dir / "request.json"
        log_file = run_dir / "log.txt"

        async with aiofiles.open(request_file, "r", encoding="utf-8") as f:
            request_data = json.loads(await f.read())

        task = request_data.get("task") or request_data.get("prompt")
        timeout = request_data.get("timeoutSeconds", request_data.get("timeout", self.default_timeout))
        working_dir = request_data.get("workingDirectory", request_data.get("workingDir"))
        env_vars = request_data.get("environmentVariables", request_data.get("envVars"))
        repo = request_data.get("repositoryPath", request_data.get("repo"))
        output_format = request_data.get("outputFormat", "json")
        security_mode = request_data.get("securityMode", "workspace_write")
        access_mode = request_data.get("accessMode", request_data.get("mode"))
        verify_enabled = request_data.get("verify", False)

        if access_mode:
            if access_mode == "suggest":
                security_mode = "readonly"
            else:
                security_mode = access_mode

        approval_mode = self._map_approval_mode(security_mode)
        extensions = "none"

        workspace = Path(repo) if repo else self.workspace_path

        enhanced_prompt = self._build_prompt(task, security_mode)

        started_at = datetime.now(timezone.utc)
        log_lines: list[str] = []

        try:
            if not await self.docker_client.check_docker_available():
                return RunResult(
                    run_id=run_id,
                    provider=RunProvider.GEMINI,
                    status=RunStatus.ERROR,
                    error="Docker is not available",
                    started_at=started_at,
                    finished_at=datetime.now(timezone.utc),
                )

            async for line in self.docker_client.run_gemini(
                run_id=run_id,
                prompt=enhanced_prompt,
                workspace_path=workspace,
                runs_path=self.runs_path,
                timeout=timeout,
                env_vars=env_vars,
                working_dir=working_dir,
                output_format=output_format,
                approval_mode=approval_mode,
                extensions=extensions,
                security_mode=security_mode,
            ):
                sanitized_line = sanitize_text(line)
                log_lines.append(sanitized_line)
                async with aiofiles.open(log_file, "a", encoding="utf-8") as f:
                    await f.write(sanitized_line)

            finished_at = datetime.now(timezone.utc)
            duration = (finished_at - started_at).total_seconds()

            full_log = "".join(log_lines)
            exit_code = self._extract_exit_code(full_log)

            response_payload = self._extract_json_payload(full_log)
            response_text = ""
            error_text: str | None = None

            if response_payload:
                response_text = str(response_payload.get("response", "")).strip()
                error_data = response_payload.get("error")
                if error_data:
                    error_text = error_data.get("message") if isinstance(error_data, dict) else str(error_data)

            raw_events = None
            if output_format == "stream-json":
                raw_events = self._extract_ndjson_events(full_log)

            marker = parse_marker(response_text or full_log)
            status = self._determine_status(marker, exit_code, error_text)

            summary = extract_summary_from_log(response_text or full_log)

            diff_content, files_changed = await self._collect_diff(workspace, run_id)

            verify_result = None
            if verify_enabled and status in (RunStatus.SUCCESS, RunStatus.DONE):
                verify_config = VerifyConfig(
                    run_tests=True,
                    run_lint=True,
                    run_build=False,
                    max_iterations=3,
                )
                verify_loop = VerifyLoop(
                    workspace_path=workspace,
                    config=verify_config,
                )
                verify_result = (await verify_loop.run(run_id)).to_dict()

            run_result = RunResult(
                run_id=run_id,
                provider=RunProvider.GEMINI,
                status=status,
                exit_code=exit_code,
                duration=duration,
                stdout=full_log,
                stderr=error_text or "",
                raw_events=raw_events,
                files_changed=files_changed,
                diff=diff_content,
                summary=summary,
                verify_result=verify_result,
                error=error_text,
                started_at=started_at,
                finished_at=finished_at,
            )

            await self._save_run_result(run_id, run_result)
            if response_payload:
                await self._save_response_payload(run_id, response_payload)
            if raw_events is not None:
                await self._save_events(run_id, raw_events)

            return run_result

        except asyncio.TimeoutError:
            finished_at = datetime.now(timezone.utc)
            duration = (finished_at - started_at).total_seconds()

            run_result = RunResult(
                run_id=run_id,
                provider=RunProvider.GEMINI,
                status=RunStatus.TIMEOUT,
                duration=duration,
                stdout="".join(log_lines),
                stderr="",
                summary="",
                error=f"Run timed out after {timeout} seconds",
                started_at=started_at,
                finished_at=finished_at,
            )

            await self._save_run_result(run_id, run_result)
            return run_result

        except Exception as e:
            finished_at = datetime.now(timezone.utc)
            duration = (finished_at - started_at).total_seconds()
            logger.exception("Gemini run failed", run_id=run_id, error=str(e))

            run_result = RunResult(
                run_id=run_id,
                provider=RunProvider.GEMINI,
                status=RunStatus.ERROR,
                duration=duration,
                stdout="".join(log_lines),
                stderr="",
                error=str(e),
                started_at=started_at,
                finished_at=finished_at,
            )

            await self._save_run_result(run_id, run_result)
            return run_result

    async def _save_run_result(self, run_id: str, result: RunResult) -> None:
        run_dir = self.runs_path / run_id
        result_file = run_dir / "run_result.json"
        payload = result.model_dump(mode="json") if hasattr(result, "model_dump") else result.dict()
        async with aiofiles.open(result_file, "w", encoding="utf-8") as f:
            await f.write(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
        logger.debug("Gemini RunResult saved", run_id=run_id, result_file=str(result_file))

    async def _save_response_payload(self, run_id: str, payload: dict[str, Any]) -> None:
        run_dir = self.runs_path / run_id
        response_file = run_dir / "response.json"
        async with aiofiles.open(response_file, "w", encoding="utf-8") as f:
            await f.write(json.dumps(payload, indent=2, ensure_ascii=False))

    async def _save_events(self, run_id: str, events: list[dict[str, Any]]) -> None:
        run_dir = self.runs_path / run_id
        events_file = run_dir / "events.jsonl"
        async with aiofiles.open(events_file, "w", encoding="utf-8") as f:
            for event in events:
                await f.write(json.dumps(event, ensure_ascii=False) + "\n")

    async def _collect_diff(self, workspace: Path, run_id: str) -> tuple[str, list[str]]:
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

        return diff_content, files_changed

    @staticmethod
    def _build_prompt(prompt: str, security_mode: str) -> str:
        base = inject_mcp_instructions(prompt)
        if security_mode == "readonly":
            return (
                f"{base}\n\n"
                "Do not edit files. Provide suggestions only. "
                "Avoid shell commands and external network access."
            )
        return base

    @staticmethod
    def _map_approval_mode(security_mode: str) -> str:
        if security_mode == "readonly":
            return "default"
        if security_mode == "full_access":
            return "yolo"
        return "auto_edit"

    @staticmethod
    def _extract_json_payload(log: str) -> dict[str, Any] | None:
        if not log:
            return None
        for line in log.splitlines():
            line = line.strip()
            if not line or not line.startswith("{"):
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict) and (
                "response" in data or "stats" in data or "error" in data
            ):
                return data
        try:
            data = json.loads(log.strip())
            if isinstance(data, dict):
                return data
        except Exception:
            return None
        return None

    @staticmethod
    def _extract_ndjson_events(log: str) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        for line in log.splitlines():
            line = line.strip()
            if not line or not line.startswith("{"):
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict):
                events.append(data)
        return events

    @staticmethod
    def _determine_status(
        marker: str | None,
        exit_code: int | None,
        error_text: str | None,
    ) -> RunStatus:
        if marker:
            status_str = marker_to_status(marker)
            if status_str:
                return RunStatus(status_str)
        if error_text:
            return RunStatus.ERROR
        if exit_code is not None:
            if exit_code == 0:
                return RunStatus.SUCCESS
            return RunStatus.ERROR
        return RunStatus.SUCCESS

    @staticmethod
    def _extract_exit_code(log: str) -> int | None:
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
        """Close manager resources."""
        self.docker_client.close()
