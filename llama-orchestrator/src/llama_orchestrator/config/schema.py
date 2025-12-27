"""
Configuration schemas for llama-orchestrator.

Uses Pydantic v2 for validation and serialization.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class ModelConfig(BaseModel):
    """Configuration for the LLM model."""
    
    path: Path = Field(..., description="Path to the GGUF model file")
    context_size: int = Field(default=4096, ge=512, le=131072, description="Context window size")
    batch_size: int = Field(default=512, ge=1, le=8192, description="Batch size for processing")
    threads: int = Field(default=8, ge=1, le=256, description="Number of CPU threads")
    
    @field_validator("path")
    @classmethod
    def validate_path_extension(cls, v: Path) -> Path:
        """Ensure model file has .gguf extension."""
        if v.suffix.lower() != ".gguf":
            raise ValueError(f"Model file must have .gguf extension, got: {v.suffix}")
        return v


class ServerConfig(BaseModel):
    """Configuration for the llama.cpp server."""
    
    host: str = Field(default="127.0.0.1", description="Server bind address")
    port: int = Field(default=8001, ge=1024, le=65535, description="Server port")
    timeout: int = Field(default=600, ge=0, description="Request timeout in seconds")
    parallel: int = Field(default=1, ge=1, le=64, description="Parallel request slots")
    
    @field_validator("host")
    @classmethod
    def validate_host(cls, v: str) -> str:
        """Validate host is a valid IP or hostname."""
        # Allow localhost variants and IP addresses
        if v in ("localhost", "127.0.0.1", "0.0.0.0", "::1"):
            return v
        # Basic IP pattern check
        ip_pattern = r"^(\d{1,3}\.){3}\d{1,3}$"
        if re.match(ip_pattern, v):
            return v
        # Allow hostnames
        hostname_pattern = r"^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)*$"
        if re.match(hostname_pattern, v):
            return v
        raise ValueError(f"Invalid host: {v}")


class GpuConfig(BaseModel):
    """Configuration for GPU acceleration."""
    
    backend: Literal["cpu", "vulkan", "cuda", "metal", "hip"] = Field(
        default="cpu", 
        description="GPU backend to use"
    )
    device_id: int = Field(default=0, ge=0, description="GPU device index")
    layers: int = Field(default=0, ge=0, description="Number of layers to offload to GPU")
    
    @model_validator(mode="after")
    def validate_gpu_config(self) -> "GpuConfig":
        """Validate GPU configuration consistency."""
        if self.backend == "cpu" and self.layers > 0:
            # Allow layers > 0 with CPU, just warn (handled at runtime)
            pass
        return self


class HealthcheckConfig(BaseModel):
    """Configuration for health monitoring."""
    
    path: str = Field(default="/health", description="Health check endpoint path")
    interval: int = Field(default=10, ge=1, le=3600, description="Check interval in seconds")
    timeout: int = Field(default=5, ge=1, le=60, description="Request timeout in seconds")
    retries: int = Field(default=3, ge=1, le=10, description="Retries before marking unhealthy")
    start_period: int = Field(default=60, ge=0, le=600, description="Grace period after start")


class RestartPolicy(BaseModel):
    """Configuration for automatic restart behavior."""
    
    enabled: bool = Field(default=True, description="Enable auto-restart")
    max_retries: int = Field(default=5, ge=0, le=100, description="Maximum restart attempts")
    backoff_multiplier: float = Field(default=2.0, ge=1.0, le=10.0, description="Exponential backoff multiplier")
    initial_delay: float = Field(default=1.0, ge=0.1, le=60.0, description="Initial delay in seconds")
    max_delay: float = Field(default=300.0, ge=1.0, le=3600.0, description="Maximum delay in seconds")


class LogsConfig(BaseModel):
    """Configuration for logging."""
    
    stdout: str = Field(default="logs/{name}/stdout.log", description="Stdout log path")
    stderr: str = Field(default="logs/{name}/stderr.log", description="Stderr log path")
    max_size_mb: int = Field(default=100, ge=1, le=10000, description="Max log file size in MB")
    rotation: int = Field(default=5, ge=1, le=100, description="Number of rotated files to keep")


class InstanceConfig(BaseModel):
    """
    Complete configuration for a llama.cpp server instance.
    
    This is the root schema that combines all sub-configurations.
    """
    
    name: str = Field(..., min_length=1, max_length=64, description="Unique instance name")
    model: ModelConfig
    server: ServerConfig = Field(default_factory=ServerConfig)
    gpu: GpuConfig = Field(default_factory=GpuConfig)
    env: dict[str, str] = Field(default_factory=dict, description="Environment variables")
    args: list[str] = Field(default_factory=list, description="Additional CLI arguments")
    healthcheck: HealthcheckConfig = Field(default_factory=HealthcheckConfig)
    restart_policy: RestartPolicy = Field(default_factory=RestartPolicy)
    logs: LogsConfig = Field(default_factory=LogsConfig)
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate instance name format."""
        pattern = r"^[a-z0-9][a-z0-9_-]*[a-z0-9]$|^[a-z0-9]$"
        if not re.match(pattern, v):
            raise ValueError(
                f"Name must start/end with alphanumeric, contain only lowercase letters, "
                f"numbers, hyphens, and underscores. Got: {v}"
            )
        return v
    
    def get_env_vars(self) -> dict[str, str]:
        """Get environment variables including GPU settings."""
        env = dict(self.env)
        
        # Add Vulkan device if applicable
        if self.gpu.backend == "vulkan":
            env["GGML_VULKAN_DEVICE"] = str(self.gpu.device_id)
        
        return env
    
    def get_log_paths(self) -> tuple[Path, Path]:
        """Get resolved log file paths."""
        stdout_path = Path(self.logs.stdout.format(name=self.name))
        stderr_path = Path(self.logs.stderr.format(name=self.name))
        return stdout_path, stderr_path


# =============================================================================
# Example config for testing/documentation
# =============================================================================

EXAMPLE_CONFIG = InstanceConfig(
    name="gpt-oss",
    model=ModelConfig(
        path=Path("models/gpt-oss-20b-Q4_K_S.gguf"),
        context_size=4096,
        batch_size=512,
        threads=16,
    ),
    server=ServerConfig(
        host="127.0.0.1",
        port=8001,
        parallel=4,
    ),
    gpu=GpuConfig(
        backend="vulkan",
        device_id=1,
        layers=30,
    ),
    env={
        "GGML_VULKAN_DEVICE": "1",
    },
    healthcheck=HealthcheckConfig(
        interval=10,
        timeout=5,
        retries=3,
    ),
    restart_policy=RestartPolicy(
        enabled=True,
        max_retries=5,
    ),
)
