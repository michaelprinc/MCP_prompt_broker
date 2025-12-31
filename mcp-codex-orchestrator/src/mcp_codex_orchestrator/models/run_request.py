"""
MCP Codex Orchestrator - Run Request Model v2.0

Model pro požadavek na spuštění Codex CLI.
Rozšířeno o security_mode, verify, output_schema, json_output.
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
    
    # V2.0 fields
    security_mode: Literal["readonly", "workspace_write", "full_access"] = Field(
        default="workspace_write",
        description="Security mode pro sandbox izolaci",
    )
    
    verify: bool = Field(
        default=False,
        description="Automaticky spustit verify loop (testy, lint)",
    )
    
    output_schema: str | None = Field(
        default=None,
        description="Název JSON schématu pro validaci výstupu",
    )
    
    json_output: bool = Field(
        default=True,
        description="Použít JSONL výstup z Codex CLI (--json flag)",
    )
    
    class Config:
        """Pydantic config."""
        
        json_schema_extra = {
            "example": {
                "prompt": "Implementuj funkci pro validaci emailové adresy",
                "mode": "full-auto",
                "timeout": 300,
                "env_vars": {"DEBUG": "1"},
                "security_mode": "workspace_write",
                "verify": True,
                "json_output": True,
            }
        }
