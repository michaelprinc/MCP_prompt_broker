"""
Tests for Pydantic models.
"""

import pytest
from pydantic import ValidationError

from mcp_codex_orchestrator.models.run_request import CodexRunRequest
from mcp_codex_orchestrator.models.run_result import (
    CodexRunResult,
    RunOutput,
    RunStatus,
)


class TestCodexRunRequest:
    """Tests for CodexRunRequest model."""
    
    def test_minimal_request(self) -> None:
        """Test creating request with only required fields."""
        request = CodexRunRequest(task="Test task")

        assert request.task == "Test task"
        assert request.execution_mode == "full-auto"
        assert request.timeout_seconds == 300
        assert request.repository_path is None
        assert request.working_directory is None
        assert request.environment_variables is None
    
    def test_full_request(self) -> None:
        """Test creating request with all fields."""
        request = CodexRunRequest(
            task="Test task",
            execution_mode="suggest",
            repository_path="/path/to/repo",
            working_directory="src",
            timeout_seconds=600,
            environment_variables={"DEBUG": "1"},
        )

        assert request.task == "Test task"
        assert request.execution_mode == "suggest"
        assert request.repository_path == "/path/to/repo"
        assert request.working_directory == "src"
        assert request.timeout_seconds == 600
        assert request.environment_variables == {"DEBUG": "1"}
    
    def test_empty_task_fails(self) -> None:
        """Test that empty task raises validation error."""
        with pytest.raises(ValidationError):
            CodexRunRequest(task="")
    
    def test_invalid_execution_mode_fails(self) -> None:
        """Test that invalid execution mode raises validation error."""
        with pytest.raises(ValidationError):
            CodexRunRequest(task="Test", execution_mode="invalid")  # type: ignore
    
    def test_timeout_too_low_fails(self) -> None:
        """Test that timeout below minimum raises error."""
        with pytest.raises(ValidationError):
            CodexRunRequest(task="Test", timeout_seconds=5)
    
    def test_timeout_too_high_fails(self) -> None:
        """Test that timeout above maximum raises error."""
        with pytest.raises(ValidationError):
            CodexRunRequest(task="Test", timeout_seconds=10000)
    
    def test_all_modes(self) -> None:
        """Test all valid modes."""
        for mode in ["full-auto", "suggest", "ask"]:
            request = CodexRunRequest(task="Test", execution_mode=mode)  # type: ignore
            assert request.execution_mode == mode


class TestRunOutput:
    """Tests for RunOutput model."""
    
    def test_default_output(self) -> None:
        """Test creating output with defaults."""
        output = RunOutput()
        
        assert output.summary == ""
        assert output.files_changed == []
        assert output.full_log == ""
    
    def test_full_output(self) -> None:
        """Test creating output with all fields."""
        output = RunOutput(
            summary="Created new file",
            files_changed=["src/test.py", "tests/test_test.py"],
            full_log="Full log content...",
        )
        
        assert output.summary == "Created new file"
        assert len(output.files_changed) == 2
        assert "src/test.py" in output.files_changed


class TestCodexRunResult:
    """Tests for CodexRunResult model."""
    
    def test_minimal_result(self) -> None:
        """Test creating result with only required fields."""
        result = CodexRunResult(
            run_id="test-id",
            status=RunStatus.DONE,
        )
        
        assert result.run_id == "test-id"
        assert result.status == RunStatus.DONE
        assert result.exit_code is None
        assert result.duration == 0.0
        assert result.error is None
    
    def test_full_result(self) -> None:
        """Test creating result with all fields."""
        from datetime import datetime, timezone
        
        now = datetime.now(timezone.utc)
        
        result = CodexRunResult(
            run_id="test-id",
            status=RunStatus.DONE,
            exit_code=0,
            duration=45.5,
            marker="::MCP_STATUS::DONE",
            output=RunOutput(
                summary="Task completed",
                files_changed=["test.py"],
                full_log="Log...",
            ),
            error=None,
            started_at=now,
            finished_at=now,
        )
        
        assert result.exit_code == 0
        assert result.duration == 45.5
        assert result.marker == "::MCP_STATUS::DONE"
        assert result.output.summary == "Task completed"
    
    def test_all_statuses(self) -> None:
        """Test all valid statuses."""
        for status in RunStatus:
            result = CodexRunResult(run_id="test", status=status)
            assert result.status == status
    
    def test_format_response_done(self) -> None:
        """Test formatting response for done status."""
        result = CodexRunResult(
            run_id="test-id",
            status=RunStatus.DONE,
            exit_code=0,
            duration=10.0,
            marker="::MCP_STATUS::DONE",
            output=RunOutput(
                summary="Created file",
                files_changed=["test.py"],
            ),
        )
        
        response = result.format_response()
        
        assert "test-id" in response
        assert "done" in response.lower()
        assert "10.00s" in response
        assert "test.py" in response
    
    def test_format_response_error(self) -> None:
        """Test formatting response for error status."""
        result = CodexRunResult(
            run_id="test-id",
            status=RunStatus.ERROR,
            error="Something went wrong",
        )
        
        response = result.format_response()
        
        assert "error" in response.lower()
        assert "Something went wrong" in response
    
    def test_format_response_truncates_long_log(self) -> None:
        """Test that long logs are truncated."""
        long_log = "x" * 10000
        
        result = CodexRunResult(
            run_id="test-id",
            status=RunStatus.DONE,
            output=RunOutput(full_log=long_log),
        )
        
        response = result.format_response()
        
        assert "truncated" in response.lower()
        assert len(response) < len(long_log)
