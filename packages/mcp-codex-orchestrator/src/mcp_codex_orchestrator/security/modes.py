"""
MCP Codex Orchestrator - Security Modes

Definice bezpečnostních režimů pro Codex běhy.
"""

from enum import Enum
from typing import Any


class SecurityMode(str, Enum):
    """Bezpečnostní režimy pro Codex běhy."""
    
    READONLY = "readonly"
    """Read-only sandbox. Pro analýzy, návrhy, reporty.
    
    - Workspace mounted jako read-only
    - Výstup pouze jako diff/patch artefakt
    - Bezpečné pro delegaci bez kontroly
    - Vhodné pro: code review, security audit, analýza kódu
    """
    
    WORKSPACE_WRITE = "workspace_write"
    """Workspace write access s verify loop.
    
    - Workspace mounted jako read-write
    - Automatický verify loop po změnách (doporučeno)
    - Sandbox omezuje síťový přístup a systémové operace
    - Vhodné pro: implementace, refactoring, opravy bugů
    """
    
    FULL_ACCESS = "full_access"
    """Plný přístup (DANGER).
    
    - Workspace mounted jako read-write
    - Síťový přístup povolen
    - Systémové operace povoleny
    - POUZE v izolovaném runneru
    - Vyžaduje explicitní potvrzení uživatele
    - Veškeré akce jsou logovány
    - Vhodné pro: instalace dependencies, Docker operace, CI/CD
    
    ⚠️ WARNING: Používejte pouze pokud rozumíte rizikům!
    """
    
    @classmethod
    def from_string(cls, value: str) -> "SecurityMode":
        """Convert string to SecurityMode."""
        value = value.lower().replace("-", "_")
        try:
            return cls(value)
        except ValueError:
            # Default to most restrictive
            return cls.READONLY
    
    @property
    def is_dangerous(self) -> bool:
        """Check if mode is dangerous."""
        return self == SecurityMode.FULL_ACCESS
    
    @property
    def allows_write(self) -> bool:
        """Check if mode allows workspace writes."""
        return self in (SecurityMode.WORKSPACE_WRITE, SecurityMode.FULL_ACCESS)
    
    @property
    def requires_confirmation(self) -> bool:
        """Check if mode requires user confirmation."""
        return self == SecurityMode.FULL_ACCESS
    
    @property
    def description(self) -> str:
        """Get human-readable description."""
        descriptions = {
            SecurityMode.READONLY: "Read-only sandbox (safest)",
            SecurityMode.WORKSPACE_WRITE: "Workspace write with verification",
            SecurityMode.FULL_ACCESS: "Full access (dangerous)",
        }
        return descriptions.get(self, "Unknown mode")


# Mapování na Codex CLI sandbox flags
SECURITY_MODE_FLAGS: dict[SecurityMode, list[str]] = {
    SecurityMode.READONLY: ["--sandbox", "read-only"],
    SecurityMode.WORKSPACE_WRITE: ["--sandbox", "write-user"],
    SecurityMode.FULL_ACCESS: [],  # No sandbox restrictions
}

# Default security mode
DEFAULT_SECURITY_MODE = SecurityMode.WORKSPACE_WRITE


def get_sandbox_flags(mode: SecurityMode | str) -> list[str]:
    """
    Get Codex CLI sandbox flags for security mode.
    
    Args:
        mode: SecurityMode enum or string
        
    Returns:
        List of CLI flags for sandbox configuration
    """
    if isinstance(mode, str):
        mode = SecurityMode.from_string(mode)
    
    return SECURITY_MODE_FLAGS.get(mode, [])


def validate_security_mode(
    mode: SecurityMode | str,
    user_confirmed: bool = False,
) -> tuple[bool, str]:
    """
    Validate security mode and check if it can be used.
    
    Args:
        mode: SecurityMode to validate
        user_confirmed: Whether user has confirmed dangerous operations
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if isinstance(mode, str):
        mode = SecurityMode.from_string(mode)
    
    if mode.requires_confirmation and not user_confirmed:
        return False, f"Security mode '{mode.value}' requires explicit user confirmation"
    
    return True, ""


def get_security_mode_config(mode: SecurityMode | str) -> dict[str, Any]:
    """
    Get configuration dictionary for security mode.
    
    Args:
        mode: SecurityMode enum or string
        
    Returns:
        Configuration dictionary with mode settings
    """
    if isinstance(mode, str):
        mode = SecurityMode.from_string(mode)
    
    return {
        "mode": mode.value,
        "description": mode.description,
        "allows_write": mode.allows_write,
        "is_dangerous": mode.is_dangerous,
        "requires_confirmation": mode.requires_confirmation,
        "sandbox_flags": get_sandbox_flags(mode),
        "mount_mode": "ro" if mode == SecurityMode.READONLY else "rw",
    }
