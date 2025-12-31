"""
Tests for security modes module.
"""

import pytest

from mcp_codex_orchestrator.security.modes import (
    SecurityMode,
    SECURITY_MODE_FLAGS,
    get_security_flags,
)


class TestSecurityModes:
    """Test suite for security modes."""

    def test_readonly_mode_flags(self):
        """Test READONLY mode has correct flags."""
        flags = SECURITY_MODE_FLAGS[SecurityMode.READONLY]
        
        assert "--read-only" in flags
        assert "--no-network" in flags or any("network" in f for f in flags)

    def test_workspace_write_mode_flags(self):
        """Test WORKSPACE_WRITE mode has correct flags."""
        flags = SECURITY_MODE_FLAGS[SecurityMode.WORKSPACE_WRITE]
        
        # Should allow workspace writes but restrict other access
        assert len(flags) > 0

    def test_full_access_mode_flags(self):
        """Test FULL_ACCESS mode has minimal restrictions."""
        flags = SECURITY_MODE_FLAGS[SecurityMode.FULL_ACCESS]
        
        # Full access should have fewer restrictions
        assert isinstance(flags, list)

    def test_get_security_flags_valid_mode(self):
        """Test getting flags for a valid mode."""
        flags = get_security_flags(SecurityMode.READONLY)
        
        assert isinstance(flags, list)

    def test_security_mode_enum_values(self):
        """Test SecurityMode enum has expected values."""
        assert SecurityMode.READONLY.value == "readonly"
        assert SecurityMode.WORKSPACE_WRITE.value == "workspace_write"
        assert SecurityMode.FULL_ACCESS.value == "full_access"

    def test_security_mode_from_string(self):
        """Test creating SecurityMode from string."""
        mode = SecurityMode("readonly")
        assert mode == SecurityMode.READONLY
        
        mode = SecurityMode("workspace_write")
        assert mode == SecurityMode.WORKSPACE_WRITE
        
        mode = SecurityMode("full_access")
        assert mode == SecurityMode.FULL_ACCESS

    def test_invalid_security_mode(self):
        """Test that invalid mode raises ValueError."""
        with pytest.raises(ValueError):
            SecurityMode("invalid_mode")
