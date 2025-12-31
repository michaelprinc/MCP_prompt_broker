"""
Tests for verify loop module.
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from mcp_codex_orchestrator.verify.verify_loop import VerifyConfig, VerifyLoop
from mcp_codex_orchestrator.verify.verify_result import VerifyResult, VerifyStatus


class TestVerifyConfig:
    """Test suite for VerifyConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = VerifyConfig()
        
        assert config.run_tests is True
        assert config.run_lint is True
        assert config.run_build is False
        assert config.max_iterations == 3
        assert config.test_command is None
        assert config.lint_command is None

    def test_custom_config(self):
        """Test custom configuration values."""
        config = VerifyConfig(
            run_tests=False,
            run_lint=True,
            run_build=True,
            max_iterations=5,
            test_command="pytest -v",
            build_command="python setup.py build",
        )
        
        assert config.run_tests is False
        assert config.run_build is True
        assert config.max_iterations == 5
        assert config.test_command == "pytest -v"


class TestVerifyLoop:
    """Test suite for VerifyLoop."""

    @pytest.fixture
    def temp_workspace(self, tmp_path):
        """Create a temporary workspace."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        return workspace

    @pytest.fixture
    def verify_loop(self, temp_workspace):
        """Create a VerifyLoop instance."""
        config = VerifyConfig(
            run_tests=True,
            run_lint=True,
            run_build=False,
        )
        return VerifyLoop(workspace_path=temp_workspace, config=config)

    def test_verify_loop_initialization(self, verify_loop, temp_workspace):
        """Test VerifyLoop initialization."""
        assert verify_loop.workspace_path == temp_workspace
        assert verify_loop.config.run_tests is True
        assert verify_loop.config.run_lint is True

    @pytest.mark.asyncio
    async def test_run_empty_workspace(self, verify_loop):
        """Test running verify loop on empty workspace."""
        result = await verify_loop.run()
        
        assert isinstance(result, dict)
        assert "success" in result

    @pytest.mark.asyncio
    async def test_run_with_all_passing(self, verify_loop, temp_workspace):
        """Test verify loop when all checks pass."""
        # Create a simple Python file
        (temp_workspace / "main.py").write_text("def hello(): return 'world'\n")
        
        with patch.object(verify_loop, '_run_tests', new_callable=AsyncMock) as mock_tests:
            with patch.object(verify_loop, '_run_lint', new_callable=AsyncMock) as mock_lint:
                mock_tests.return_value = VerifyResult(
                    status=VerifyStatus.PASSED,
                    passed=1,
                    failed=0,
                )
                mock_lint.return_value = VerifyResult(
                    status=VerifyStatus.PASSED,
                    errors=[],
                )
                
                result = await verify_loop.run()
                
                assert result["success"] is True

    @pytest.mark.asyncio
    async def test_run_with_test_failures(self, verify_loop, temp_workspace):
        """Test verify loop when tests fail."""
        with patch.object(verify_loop, '_run_tests', new_callable=AsyncMock) as mock_tests:
            with patch.object(verify_loop, '_run_lint', new_callable=AsyncMock) as mock_lint:
                mock_tests.return_value = VerifyResult(
                    status=VerifyStatus.FAILED,
                    passed=2,
                    failed=1,
                    errors=["test_main.py::test_something FAILED"],
                )
                mock_lint.return_value = VerifyResult(
                    status=VerifyStatus.PASSED,
                    errors=[],
                )
                
                result = await verify_loop.run()
                
                assert result["success"] is False
                assert len(result.get("errors", [])) > 0


class TestVerifyResult:
    """Test suite for VerifyResult."""

    def test_passed_result(self):
        """Test creating a passed result."""
        result = VerifyResult(
            status=VerifyStatus.PASSED,
            passed=5,
            failed=0,
        )
        
        assert result.status == VerifyStatus.PASSED
        assert result.passed == 5
        assert result.is_success is True

    def test_failed_result(self):
        """Test creating a failed result."""
        result = VerifyResult(
            status=VerifyStatus.FAILED,
            passed=3,
            failed=2,
            errors=["Error 1", "Error 2"],
        )
        
        assert result.status == VerifyStatus.FAILED
        assert result.failed == 2
        assert result.is_success is False
        assert len(result.errors) == 2

    def test_skipped_result(self):
        """Test creating a skipped result."""
        result = VerifyResult(
            status=VerifyStatus.SKIPPED,
            message="No tests found",
        )
        
        assert result.status == VerifyStatus.SKIPPED
        # Skipped is considered success (nothing failed)
        assert result.is_success is True
