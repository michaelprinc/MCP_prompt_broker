"""
MCP Codex Orchestrator - Gemini Docker Client

Wrapper for Docker SDK to run Gemini CLI containers.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import AsyncGenerator

import docker
import structlog
from docker.errors import DockerException, ImageNotFound, NotFound
from docker.models.containers import Container

from mcp_codex_orchestrator.orchestrator.exceptions import (
    ContainerError,
    DockerNotAvailableError,
    ImageNotFoundError,
)

logger = structlog.get_logger(__name__)

DEFAULT_GEMINI_IMAGE = os.getenv("GEMINI_IMAGE", "gemini-runner:latest")
DEFAULT_GEMINI_AUTH_PATH = Path(
    os.getenv("GEMINI_AUTH_PATH", os.path.expanduser("~/.gemini"))
)


class DockerGeminiClient:
    """Client for running Gemini CLI in Docker containers."""

    def __init__(self, image: str = DEFAULT_GEMINI_IMAGE) -> None:
        self.image = image
        self._client: docker.DockerClient | None = None

    @property
    def client(self) -> docker.DockerClient:
        """Get or create Docker client."""
        if self._client is None:
            try:
                self._client = docker.from_env()
            except DockerException as e:
                raise DockerNotAvailableError(f"Cannot connect to Docker: {e}") from e
        return self._client

    async def check_docker_available(self) -> bool:
        """Check if Docker daemon is available."""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.client.ping)
            return True
        except Exception as e:
            logger.warning("Docker not available", error=str(e))
            return False

    async def ensure_image_exists(self, image: str | None = None) -> bool:
        """Ensure the Gemini Docker image exists."""
        image_name = image or self.image

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.client.images.get, image_name)
            logger.debug("Image found", image=image_name)
            return True
        except ImageNotFound:
            logger.warning("Image not found locally", image=image_name)
            try:
                logger.info("Pulling image", image=image_name)
                await loop.run_in_executor(None, self.client.images.pull, image_name)
                logger.info("Image pulled successfully", image=image_name)
                return True
            except Exception as e:
                raise ImageNotFoundError(
                    f"Cannot find or pull image '{image_name}': {e}"
                ) from e

    async def run_gemini(
        self,
        run_id: str,
        prompt: str,
        workspace_path: Path,
        runs_path: Path,
        timeout: int,
        env_vars: dict[str, str] | None = None,
        working_dir: str | None = None,
        output_format: str = "json",
        approval_mode: str = "auto_edit",
        extensions: str | None = "none",
        security_mode: str = "workspace_write",
    ) -> AsyncGenerator[str, None]:
        """
        Run Gemini CLI in a Docker container.

        Yields:
            Log lines from the container
        """
        await self.ensure_image_exists()

        command = self._build_command(
            prompt=prompt,
            output_format=output_format,
            approval_mode=approval_mode,
            extensions=extensions,
        )

        environment = self._build_environment(env_vars)
        volumes = self._build_volumes(
            workspace_path=workspace_path,
            runs_path=runs_path,
            run_id=run_id,
            security_mode=security_mode,
        )

        container_workdir = "/workspace"
        if working_dir:
            container_workdir = f"/workspace/{working_dir.lstrip('/')}"

        container: Container | None = None

        try:
            logger.info(
                "Starting Gemini container",
                run_id=run_id,
                image=self.image,
                output_format=output_format,
            )

            if os.name == "nt":
                container_user = "root"
                logger.debug("Running container as root (Windows/Docker Desktop)")
            else:
                container_user = f"{os.getuid()}:{os.getgid()}"
                logger.debug("Running container as current user", user=container_user)

            loop = asyncio.get_event_loop()
            container = await loop.run_in_executor(
                None,
                lambda: self.client.containers.run(
                    image=self.image,
                    command=command,
                    environment=environment,
                    volumes=volumes,
                    working_dir=container_workdir,
                    name=f"gemini-run-{run_id}",
                    user=container_user,
                    detach=True,
                    remove=False,
                    mem_limit="4g",
                    cpu_quota=200000,
                    network_mode="bridge",
                ),
            )

            logger.info("Container started", container_id=container.short_id)

            async for line in self._stream_logs(container, timeout):
                yield line

            result = await loop.run_in_executor(None, lambda: container.wait(timeout=timeout))
            exit_code = result.get("StatusCode", -1)
            logger.info("Container finished", exit_code=exit_code)
            yield f"\n[Container exited with code {exit_code}]"

        except asyncio.TimeoutError:
            logger.warning("Container timeout", run_id=run_id, timeout=timeout)
            yield f"\n[Container timeout after {timeout}s]"
            if container:
                await self.stop_container(container)
        except Exception as e:
            logger.exception("Container error", run_id=run_id, error=str(e))
            raise ContainerError(f"Container failed: {e}") from e
        finally:
            if container:
                await self.cleanup(container)

    async def _stream_logs(
        self,
        container: Container,
        timeout: int,
    ) -> AsyncGenerator[str, None]:
        """Stream logs from container."""
        loop = asyncio.get_event_loop()

        try:
            log_generator = container.logs(stream=True, follow=True, timestamps=False)
            start_time = asyncio.get_event_loop().time()

            for chunk in log_generator:
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > timeout:
                    raise asyncio.TimeoutError()

                if isinstance(chunk, bytes):
                    line = chunk.decode("utf-8", errors="replace")
                else:
                    line = str(chunk)

                yield line
                await asyncio.sleep(0)
        except Exception as e:
            if "timeout" in str(e).lower():
                raise asyncio.TimeoutError() from e
            raise

    async def stop_container(self, container: Container, timeout: int = 10) -> None:
        """Stop a running container."""
        try:
            loop = asyncio.get_event_loop()
            logger.info("Stopping container", container_id=container.short_id)
            await loop.run_in_executor(None, lambda: container.stop(timeout=timeout))
            logger.info("Container stopped", container_id=container.short_id)
        except Exception as e:
            logger.warning(
                "Error stopping container",
                container_id=container.short_id,
                error=str(e),
            )
            try:
                await loop.run_in_executor(None, container.kill)
            except Exception:
                pass

    async def cleanup(self, container: Container) -> None:
        """Remove container."""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, container.reload)
            await loop.run_in_executor(None, lambda: container.remove(force=True))
            logger.debug("Container removed", container_id=container.short_id)
        except NotFound:
            pass
        except Exception as e:
            logger.warning(
                "Error removing container",
                container_id=container.short_id,
                error=str(e),
            )

    def _build_command(
        self,
        prompt: str,
        output_format: str,
        approval_mode: str,
        extensions: str | None,
    ) -> list[str]:
        """Build Gemini CLI command."""
        cmd = ["-p", prompt, "--output-format", output_format]

        if approval_mode:
            cmd.extend(["--approval-mode", approval_mode])

        if extensions:
            cmd.extend(["--extensions", extensions])

        return cmd

    def _build_environment(self, env_vars: dict[str, str] | None) -> dict[str, str]:
        """Build environment variables for container."""
        env: dict[str, str] = {
            "HOME": "/home/runner",
            "GEMINI_HOME": "/home/runner/.gemini",
        }

        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        if project_id:
            env["GOOGLE_CLOUD_PROJECT"] = project_id

        if env_vars:
            filtered = {
                key: value
                for key, value in env_vars.items()
                if key.upper() not in {"GEMINI_API_KEY", "GOOGLE_API_KEY"}
            }
            env.update(filtered)

        return env

    def _build_volumes(
        self,
        workspace_path: Path,
        runs_path: Path,
        run_id: str,
        security_mode: str = "workspace_write",
    ) -> dict[str, dict[str, str]]:
        """Build volume mounts for container."""
        run_dir = runs_path / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        ws_mode = "ro" if security_mode == "readonly" else "rw"

        volumes = {
            str(workspace_path.resolve()): {"bind": "/workspace", "mode": ws_mode},
            str(run_dir.resolve()): {"bind": f"/runs/{run_id}", "mode": "rw"},
        }

        if DEFAULT_GEMINI_AUTH_PATH.exists():
            volumes[str(DEFAULT_GEMINI_AUTH_PATH.resolve())] = {
                "bind": "/home/runner/.gemini",
                "mode": "rw",
            }
        else:
            logger.warning(
                ".gemini auth directory not found",
                expected_path=str(DEFAULT_GEMINI_AUTH_PATH),
                hint="Run gemini login on the host first",
            )

        return volumes

    def close(self) -> None:
        """Close Docker client connection."""
        if self._client:
            self._client.close()
            self._client = None
