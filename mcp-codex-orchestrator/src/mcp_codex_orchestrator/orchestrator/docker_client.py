"""
MCP Codex Orchestrator - Docker Client

Wrapper pro Docker SDK pro správu Codex kontejnerů.
"""

import asyncio
import os
from pathlib import Path
from typing import AsyncGenerator

import docker

# Default path for Codex authentication file
DEFAULT_CODEX_AUTH_PATH = Path(
    os.getenv("CODEX_AUTH_PATH", os.path.expanduser("~/.codex"))
)
from docker.errors import DockerException, ImageNotFound, NotFound
from docker.models.containers import Container
import structlog

from mcp_codex_orchestrator.orchestrator.exceptions import (
    DockerNotAvailableError,
    ImageNotFoundError,
    ContainerError,
)

logger = structlog.get_logger(__name__)

# Default Docker image for Codex CLI
DEFAULT_CODEX_IMAGE = os.getenv("CODEX_IMAGE", "codex-runner:latest")


class DockerCodexClient:
    """Client pro správu Docker kontejnerů s Codex CLI."""
    
    def __init__(
        self,
        image: str = DEFAULT_CODEX_IMAGE,
    ) -> None:
        """
        Initialize Docker client.
        
        Args:
            image: Docker image name for Codex CLI
        """
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
        """
        Check if Docker daemon is available.
        
        Returns:
            True if Docker is available, False otherwise
        """
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.client.ping)
            return True
        except Exception as e:
            logger.warning("Docker not available", error=str(e))
            return False
    
    async def ensure_image_exists(self, image: str | None = None) -> bool:
        """
        Ensure the Codex Docker image exists.
        
        Args:
            image: Image name to check (default: self.image)
            
        Returns:
            True if image exists or was pulled successfully
            
        Raises:
            ImageNotFoundError: If image cannot be found or pulled
        """
        image_name = image or self.image
        
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, 
                self.client.images.get, 
                image_name
            )
            logger.debug("Image found", image=image_name)
            return True
            
        except ImageNotFound:
            logger.warning("Image not found locally", image=image_name)
            
            # Try to pull the image
            try:
                logger.info("Pulling image", image=image_name)
                await loop.run_in_executor(
                    None,
                    self.client.images.pull,
                    image_name
                )
                logger.info("Image pulled successfully", image=image_name)
                return True
                
            except Exception as e:
                raise ImageNotFoundError(
                    f"Cannot find or pull image '{image_name}': {e}"
                ) from e
    
    async def run_codex(
        self,
        run_id: str,
        prompt: str,
        mode: str,
        workspace_path: Path,
        runs_path: Path,
        timeout: int,
        env_vars: dict[str, str] | None = None,
        working_dir: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        Run Codex CLI in a Docker container.
        
        Args:
            run_id: Unique run identifier
            prompt: The prompt for Codex
            mode: Codex mode (full-auto, suggest, ask)
            workspace_path: Path to workspace directory
            runs_path: Path to runs directory
            timeout: Timeout in seconds
            env_vars: Additional environment variables
            working_dir: Working directory inside workspace
            
        Yields:
            Log lines from the container
            
        Raises:
            ContainerError: If container fails to start or run
        """
        # Ensure image exists
        await self.ensure_image_exists()
        
        # Build command
        command = self._build_command(prompt, mode)
        
        # Build environment
        environment = self._build_environment(env_vars)
        
        # Build volumes
        volumes = self._build_volumes(workspace_path, runs_path, run_id)
        
        # Container working directory
        container_workdir = "/workspace"
        if working_dir:
            container_workdir = f"/workspace/{working_dir.lstrip('/')}"
        
        container: Container | None = None
        
        try:
            logger.info(
                "Starting Codex container",
                run_id=run_id,
                image=self.image,
                mode=mode,
            )
            
            # Create and start container
            loop = asyncio.get_event_loop()
            container = await loop.run_in_executor(
                None,
                lambda: self.client.containers.run(
                    image=self.image,
                    command=command,
                    environment=environment,
                    volumes=volumes,
                    working_dir=container_workdir,
                    name=f"codex-run-{run_id}",
                    detach=True,
                    remove=False,  # We'll remove manually after getting logs
                    mem_limit="4g",
                    cpu_quota=200000,  # 2 CPUs
                    network_mode="bridge",
                )
            )
            
            logger.info("Container started", container_id=container.short_id)
            
            # Stream logs
            async for line in self._stream_logs(container, timeout):
                yield line
            
            # Wait for container to finish
            result = await loop.run_in_executor(
                None,
                lambda: container.wait(timeout=timeout)
            )
            
            exit_code = result.get("StatusCode", -1)
            logger.info("Container finished", exit_code=exit_code)
            
            # Yield exit code info
            yield f"\n[Container exited with code {exit_code}]"
            
        except asyncio.TimeoutError:
            logger.warning("Container timeout", run_id=run_id, timeout=timeout)
            yield f"\n[Container timeout after {timeout}s]"
            
            # Stop the container
            if container:
                await self.stop_container(container)
            
        except Exception as e:
            logger.exception("Container error", run_id=run_id, error=str(e))
            raise ContainerError(f"Container failed: {e}") from e
            
        finally:
            # Cleanup container
            if container:
                await self.cleanup(container)
    
    async def _stream_logs(
        self,
        container: Container,
        timeout: int,
    ) -> AsyncGenerator[str, None]:
        """
        Stream logs from container.
        
        Args:
            container: Docker container
            timeout: Timeout in seconds
            
        Yields:
            Log lines
        """
        loop = asyncio.get_event_loop()
        
        try:
            # Get log generator
            log_generator = container.logs(
                stream=True,
                follow=True,
                timestamps=False,
            )
            
            start_time = asyncio.get_event_loop().time()
            
            for chunk in log_generator:
                # Check timeout
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > timeout:
                    raise asyncio.TimeoutError()
                
                # Decode and yield
                if isinstance(chunk, bytes):
                    line = chunk.decode("utf-8", errors="replace")
                else:
                    line = str(chunk)
                
                yield line
                
                # Allow other tasks to run
                await asyncio.sleep(0)
                
        except Exception as e:
            if "timeout" in str(e).lower():
                raise asyncio.TimeoutError() from e
            raise
    
    async def stop_container(
        self,
        container: Container,
        timeout: int = 10,
    ) -> None:
        """
        Stop a running container.
        
        Args:
            container: Docker container to stop
            timeout: Timeout for graceful stop
        """
        try:
            loop = asyncio.get_event_loop()
            
            logger.info("Stopping container", container_id=container.short_id)
            
            # Try graceful stop first
            await loop.run_in_executor(
                None,
                lambda: container.stop(timeout=timeout)
            )
            
            logger.info("Container stopped", container_id=container.short_id)
            
        except Exception as e:
            logger.warning(
                "Error stopping container",
                container_id=container.short_id,
                error=str(e),
            )
            
            # Force kill if graceful stop failed
            try:
                await loop.run_in_executor(None, container.kill)
            except Exception:
                pass
    
    async def cleanup(self, container: Container) -> None:
        """
        Remove a container and clean up resources.
        
        Args:
            container: Docker container to remove
        """
        try:
            loop = asyncio.get_event_loop()
            
            # Refresh container state
            await loop.run_in_executor(None, container.reload)
            
            # Remove container
            await loop.run_in_executor(
                None,
                lambda: container.remove(force=True)
            )
            
            logger.debug("Container removed", container_id=container.short_id)
            
        except NotFound:
            # Container already removed
            pass
        except Exception as e:
            logger.warning(
                "Error removing container",
                container_id=container.short_id,
                error=str(e),
            )
    
    def _build_command(self, prompt: str, mode: str) -> list[str]:
        """Build Docker command for Codex CLI.
        
        Uses 'exec' subcommand for non-interactive execution.
        """
        # Use 'exec' subcommand for non-interactive mode
        cmd = ["exec"]
        
        # Add mode flag
        if mode == "full-auto":
            cmd.append("--full-auto")
        elif mode == "suggest":
            cmd.append("--suggest")
        # "ask" is the default, no flag needed
        
        # Add prompt as the task
        cmd.append(prompt)
        
        return cmd
    
    def _build_environment(
        self,
        env_vars: dict[str, str] | None,
    ) -> dict[str, str]:
        """Build environment variables for container."""
        env = {
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", ""),
            "CODEX_QUIET_MODE": "1",
        }
        
        if env_vars:
            env.update(env_vars)
        
        return env
    
    def _build_volumes(
        self,
        workspace_path: Path,
        runs_path: Path,
        run_id: str,
    ) -> dict[str, dict[str, str]]:
        """Build volume mounts for container.
        
        Includes:
        - Workspace directory (read-write)
        - Run-specific logs directory (read-write)
        - Codex auth.json for OAuth/ChatGPT Plus authentication (read-only)
        """
        # Create run-specific directory
        run_dir = runs_path / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        
        volumes = {
            str(workspace_path.resolve()): {
                "bind": "/workspace",
                "mode": "rw",
            },
            str(run_dir.resolve()): {
                "bind": f"/runs/{run_id}",
                "mode": "rw",
            },
        }
        
        # Mount auth.json for OAuth/ChatGPT Plus authentication
        # This is required for Codex CLI to authenticate with ChatGPT Plus subscription
        auth_file = DEFAULT_CODEX_AUTH_PATH / "auth.json"
        if auth_file.exists():
            volumes[str(auth_file.resolve())] = {
                "bind": "/home/node/.codex/auth.json",
                "mode": "ro",  # Read-only for security
            }
            logger.debug("Mounting auth.json for OAuth authentication", auth_file=str(auth_file))
        else:
            logger.warning(
                "auth.json not found - OAuth authentication may fail",
                expected_path=str(auth_file),
                hint="Run 'codex login' to authenticate with ChatGPT Plus"
            )
        
        return volumes
    
    def close(self) -> None:
        """Close Docker client connection."""
        if self._client:
            self._client.close()
            self._client = None
