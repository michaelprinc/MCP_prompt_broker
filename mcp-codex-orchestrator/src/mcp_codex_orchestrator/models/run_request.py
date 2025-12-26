"""
MCP Codex Orchestrator - Run Request Model

Model pro požadavek na spuštění Codex CLI.
"""

from typing import Literal

from pydantic import BaseModel, Field


class CodexRunRequest(BaseModel):
    """Request pro spuštění Codex CLI."""
    
    prompt: str = Field(
        ...,
        description="Zadání pro Codex CLI - co má udělat",
        min_length=1,
        max_length=10000,
    )
    
    mode: Literal["full-auto", "suggest", "ask"] = Field(
        default="full-auto",
        description="Režim běhu Codex CLI",
    )
    
    repo: str | None = Field(
        default=None,
        description="Cesta k repository (default: aktuální workspace)",
    )
    
    working_dir: str | None = Field(
        default=None,
        description="Working directory uvnitř repository",
    )
    
    timeout: int = Field(
        default=300,
        ge=10,
        le=3600,
        description="Timeout v sekundách (10-3600)",
    )
    
    env_vars: dict[str, str] | None = Field(
        default=None,
        description="Extra environment variables",
    )
    
    class Config:
        """Pydantic config."""
        
        json_schema_extra = {
            "example": {
                "prompt": "Implementuj funkci pro validaci emailové adresy",
                "mode": "full-auto",
                "timeout": 300,
                "env_vars": {"DEBUG": "1"},
            }
        }
