"""
MCP Codex Orchestrator - Run Result Model

Model pro výsledek běhu Codex CLI.
"""

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class RunStatus(str, Enum):
    """Status běhu Codex."""
    
    DONE = "done"
    NEED_USER = "need_user"
    ERROR = "error"
    TIMEOUT = "timeout"
    RUNNING = "running"
    PENDING = "pending"


class RunOutput(BaseModel):
    """Výstup z běhu Codex."""
    
    summary: str = Field(
        default="",
        description="Shrnutí co Codex udělal",
    )
    
    files_changed: list[str] = Field(
        default_factory=list,
        description="Seznam změněných souborů",
    )
    
    full_log: str = Field(
        default="",
        description="Kompletní log výstup",
    )


class CodexRunResult(BaseModel):
    """Výsledek běhu Codex CLI."""
    
    run_id: str = Field(
        ...,
        description="Unikátní ID běhu",
    )
    
    status: RunStatus = Field(
        ...,
        description="Status běhu",
    )
    
    exit_code: int | None = Field(
        default=None,
        description="Exit code procesu (pokud dostupný)",
    )
    
    duration: float = Field(
        default=0.0,
        ge=0,
        description="Doba běhu v sekundách",
    )
    
    marker: str | None = Field(
        default=None,
        description="Detekovaný MCP status marker",
    )
    
    output: RunOutput = Field(
        default_factory=RunOutput,
        description="Výstup z běhu",
    )
    
    error: str | None = Field(
        default=None,
        description="Chybová zpráva (pokud došlo k chybě)",
    )
    
    started_at: datetime | None = Field(
        default=None,
        description="Čas začátku běhu",
    )
    
    finished_at: datetime | None = Field(
        default=None,
        description="Čas konce běhu",
    )
    
    def format_response(self) -> str:
        """Format result for MCP response."""
        lines = [
            f"# Codex Run Result",
            f"",
            f"**Run ID:** `{self.run_id}`",
            f"**Status:** {self.status.value}",
            f"**Duration:** {self.duration:.2f}s",
        ]
        
        if self.exit_code is not None:
            lines.append(f"**Exit Code:** {self.exit_code}")
        
        if self.marker:
            lines.append(f"**Marker:** `{self.marker}`")
        
        if self.error:
            lines.extend([
                f"",
                f"## Error",
                f"```",
                self.error,
                f"```",
            ])
        
        if self.output.summary:
            lines.extend([
                f"",
                f"## Summary",
                self.output.summary,
            ])
        
        if self.output.files_changed:
            lines.extend([
                f"",
                f"## Files Changed",
            ])
            for file in self.output.files_changed:
                lines.append(f"- `{file}`")
        
        if self.output.full_log:
            # Truncate log if too long
            log = self.output.full_log
            if len(log) > 5000:
                log = log[:5000] + "\n... (truncated)"
            
            lines.extend([
                f"",
                f"## Log Output",
                f"```",
                log,
                f"```",
            ])
        
        return "\n".join(lines)
    
    class Config:
        """Pydantic config."""
        
        json_schema_extra = {
            "example": {
                "run_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "done",
                "exit_code": 0,
                "duration": 45.2,
                "marker": "::MCP_STATUS::DONE",
                "output": {
                    "summary": "Vytvořen soubor src/validators/email.py",
                    "files_changed": ["src/validators/email.py"],
                    "full_log": "...",
                },
                "error": None,
            }
        }
