"""
Tests for RunManager.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_codex_orchestrator.models.run_request import CodexRunRequest
from mcp_codex_orchestrator.models.run_result import RunStatus
from mcp_codex_orchestrator.orchestrator.run_manager import RunManager


class TestRunManager:
    """Tests for RunManager class."""
    
    @pytest.fixture
    def run_manager(
        self,
        temp_workspace: Path,
        temp_runs: Path,
    ) -> RunManager:
        """Create a RunManager with temporary directories."""
        return RunManager(
            workspace_path=temp_workspace,
            runs_path=temp_runs,
            default_timeout=60,
        )
    
    def test_generate_run_id(self, run_manager: RunManager) -> None:
        """Test run ID generation."""
        run_id = run_manager.generate_run_id()
        
        assert run_id is not None
        assert len(run_id) == 36  # UUID format
        assert "-" in run_id
    
    def test_generate_unique_run_ids(self, run_manager: RunManager) -> None:
        """Test that generated run IDs are unique."""
        ids = {run_manager.generate_run_id() for _ in range(100)}
        assert len(ids) == 100
    
    @pytest.mark.asyncio
    async def test_create_run(
        self,
        run_manager: RunManager,
        sample_request_data: dict,
    ) -> None:
        """Test creating a new run."""
        request = CodexRunRequest(**sample_request_data)
        
        run_id = await run_manager.create_run(request)
        
        assert run_id is not None
        
        # Check that run directory was created
        run_dir = run_manager.runs_path / run_id
        assert run_dir.exists()
        
        # Check that request.json was created
        request_file = run_dir / "request.json"
        assert request_file.exists()
        
        # Verify request content
        with open(request_file) as f:
            saved_request = json.load(f)
        
        assert saved_request["task"] == sample_request_data["task"]
        assert saved_request["executionMode"] == sample_request_data["execution_mode"]
        assert saved_request["runId"] == run_id
    
    @pytest.mark.asyncio
    async def test_create_run_with_all_fields(
        self,
        run_manager: RunManager,
    ) -> None:
        """Test creating a run with all optional fields."""
        request = CodexRunRequest(
            task="Test task",
            execution_mode="suggest",
            repository_path="/custom/repo",
            working_directory="src",
            timeout_seconds=120,
            environment_variables={"KEY": "value"},
        )
        
        run_id = await run_manager.create_run(request)
        
        request_file = run_manager.runs_path / run_id / "request.json"
        with open(request_file) as f:
            saved_request = json.load(f)
        
        assert saved_request["workingDirectory"] == "src"
        assert saved_request["environmentVariables"] == {"KEY": "value"}
    
    @pytest.mark.asyncio
    async def test_execute_run_docker_not_available(
        self,
        run_manager: RunManager,
        sample_request_data: dict,
    ) -> None:
        """Test executing run when Docker is not available."""
        # Mock Docker client to return not available
        run_manager.docker_client.check_docker_available = AsyncMock(return_value=False)
        
        request = CodexRunRequest(**sample_request_data)
        run_id = await run_manager.create_run(request)
        
        result = await run_manager.execute_run(run_id)
        
        assert result.status == RunStatus.ERROR
        assert "Docker" in result.error
    
    @pytest.mark.asyncio
    async def test_get_run_status_pending(
        self,
        run_manager: RunManager,
        sample_request_data: dict,
    ) -> None:
        """Test getting status of pending run."""
        request = CodexRunRequest(**sample_request_data)
        run_id = await run_manager.create_run(request)
        
        status = await run_manager.get_run_status(run_id)
        
        assert status == RunStatus.PENDING
    
    @pytest.mark.asyncio
    async def test_get_run_status_nonexistent(
        self,
        run_manager: RunManager,
    ) -> None:
        """Test getting status of non-existent run."""
        status = await run_manager.get_run_status("nonexistent-id")
        
        assert status == RunStatus.ERROR
    
    def test_close(self, run_manager: RunManager) -> None:
        """Test closing the manager."""
        # Should not raise
        run_manager.close()
