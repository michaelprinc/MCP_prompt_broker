"""
MCP Codex Orchestrator - Sandbox Enforcement

Vynucování bezpečnostních pravidel pro Codex běhy.
"""

import structlog

from mcp_codex_orchestrator.security.modes import (
    SecurityMode,
    get_sandbox_flags,
    validate_security_mode,
)

logger = structlog.get_logger(__name__)


class SecurityError(Exception):
    """Security policy violation."""
    pass


class SandboxEnforcer:
    """Enforces sandbox security policies for Codex runs."""
    
    def __init__(
        self,
        default_mode: SecurityMode = SecurityMode.WORKSPACE_WRITE,
        require_confirmation_for_dangerous: bool = True,
    ):
        """
        Initialize sandbox enforcer.
        
        Args:
            default_mode: Default security mode to use
            require_confirmation_for_dangerous: Require confirmation for dangerous modes
        """
        self.default_mode = default_mode
        self.require_confirmation = require_confirmation_for_dangerous
    
    def validate_mode(
        self,
        mode: SecurityMode | str,
        user_confirmed: bool = False,
    ) -> SecurityMode:
        """
        Validate and normalize security mode.
        
        Args:
            mode: Security mode to validate
            user_confirmed: Whether user has confirmed dangerous operations
            
        Returns:
            Validated SecurityMode
            
        Raises:
            SecurityError: If mode cannot be used
        """
        if isinstance(mode, str):
            mode = SecurityMode.from_string(mode)
        
        if self.require_confirmation:
            is_valid, error = validate_security_mode(mode, user_confirmed)
            if not is_valid:
                logger.warning(
                    "Security mode validation failed",
                    mode=mode.value,
                    error=error,
                )
                raise SecurityError(error)
        
        logger.info("Security mode validated", mode=mode.value)
        return mode
    
    def get_docker_config(
        self,
        mode: SecurityMode,
    ) -> dict:
        """
        Get Docker configuration for security mode.
        
        Args:
            mode: Security mode
            
        Returns:
            Docker configuration dictionary
        """
        config = {
            "sandbox_flags": get_sandbox_flags(mode),
            "mount_mode": "ro" if mode == SecurityMode.READONLY else "rw",
            "network_mode": "none" if mode != SecurityMode.FULL_ACCESS else "bridge",
            "cap_drop": ["ALL"] if mode != SecurityMode.FULL_ACCESS else [],
            "read_only_rootfs": mode == SecurityMode.READONLY,
        }
        
        # Add resource limits for non-full-access modes
        if mode != SecurityMode.FULL_ACCESS:
            config["mem_limit"] = "4g"
            config["cpu_quota"] = 200000  # 2 CPUs
            config["pids_limit"] = 256
        
        return config
    
    def should_run_verify_loop(self, mode: SecurityMode) -> bool:
        """
        Check if verify loop should run after Codex execution.
        
        Args:
            mode: Security mode
            
        Returns:
            True if verify loop should run
        """
        # Verify loop recommended for workspace_write mode
        return mode == SecurityMode.WORKSPACE_WRITE
    
    def should_generate_patch(self, mode: SecurityMode) -> bool:
        """
        Check if changes should be generated as patch instead of direct writes.
        
        Args:
            mode: Security mode
            
        Returns:
            True if patch workflow should be used
        """
        # Readonly mode always generates patches (no direct writes)
        return mode == SecurityMode.READONLY
    
    def log_security_event(
        self,
        event_type: str,
        mode: SecurityMode,
        run_id: str,
        details: dict | None = None,
    ) -> None:
        """
        Log security-related event.
        
        Args:
            event_type: Type of security event
            mode: Security mode
            run_id: Run identifier
            details: Additional event details
        """
        logger.info(
            "Security event",
            event_type=event_type,
            security_mode=mode.value,
            run_id=run_id,
            is_dangerous=mode.is_dangerous,
            **(details or {}),
        )


# Convenience functions

def create_sandbox_enforcer(
    strict: bool = True,
) -> SandboxEnforcer:
    """
    Create sandbox enforcer with appropriate settings.
    
    Args:
        strict: Use strict security settings
        
    Returns:
        Configured SandboxEnforcer
    """
    return SandboxEnforcer(
        default_mode=SecurityMode.READONLY if strict else SecurityMode.WORKSPACE_WRITE,
        require_confirmation_for_dangerous=strict,
    )
