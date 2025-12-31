"""
MCP Codex Orchestrator - Verify Result Model

Model pro výsledek verify loop.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class VerifyStatus(str, Enum):
    """Status verify loop."""
    
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class CheckResult:
    """Result from a single check (lint, test, build)."""
    
    name: str
    status: VerifyStatus
    output: str = ""
    error: Optional[str] = None
    passed: bool = False
    duration: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Set passed based on status if not explicitly set."""
        if self.status == VerifyStatus.PASSED:
            self.passed = True
        elif self.status == VerifyStatus.SKIPPED:
            self.passed = True  # Skipped is considered passed


@dataclass
class VerifyResult:
    """Výsledek verify loop."""
    
    status: VerifyStatus = VerifyStatus.PASSED
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    iterations: int = 1
    duration: float = 0.0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    
    # Individual check results
    lint: Optional[CheckResult] = None
    tests: Optional[CheckResult] = None
    build: Optional[CheckResult] = None
    
    @property
    def is_success(self) -> bool:
        """Check if verify was successful."""
        return self.status in (VerifyStatus.PASSED, VerifyStatus.SKIPPED)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "status": self.status.value,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "iterations": self.iterations,
            "duration": self.duration,
            "errors": self.errors,
            "warnings": self.warnings,
            "message": self.message,
            "success": self.is_success,
            "details": self.details,
        }


@dataclass
class TestResult:
    """Result from test runner."""
    
    status: VerifyStatus
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    duration: float = 0.0
    errors: list[str] = field(default_factory=list)
    output: str = ""


@dataclass
class LintResult:
    """Result from lint checker."""
    
    status: VerifyStatus
    errors: int = 0
    warnings: int = 0
    issues: list[dict[str, Any]] = field(default_factory=list)
    output: str = ""
    
    @property
    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return self.errors > 0


@dataclass
class BuildResult:
    """Result from build runner."""
    
    status: VerifyStatus
    exit_code: int = 0
    output: str = ""
    errors: list[str] = field(default_factory=list)
