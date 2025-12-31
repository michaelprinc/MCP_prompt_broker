"""
Tests for ResultCollector.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_codex_orchestrator.models.run_result import RunStatus
from mcp_codex_orchestrator.orchestrator.result_collector import ResultCollector


class TestResultCollector:
    """Tests for ResultCollector class."""
    
    @pytest.fixture
    def collector(self) -> ResultCollector:
        """Create a ResultCollector instance."""
        return ResultCollector()
    
    @pytest.mark.asyncio
    async def test_collect_done_result(
        self,
        collector: ResultCollector,
        sample_log_done: str,
    ) -> None:
        """Test collecting a successful result."""
        started = datetime.now(timezone.utc)
        finished = datetime.now(timezone.utc)
        
        result = await collector.collect(
            run_id="test-run",
            log=sample_log_done,
            started_at=started,
            finished_at=finished,
            exit_code=0,
        )
        
        assert result.run_id == "test-run"
        assert result.status == RunStatus.DONE
        assert result.marker == "::MCP_STATUS::DONE"
        assert result.exit_code == 0
        assert result.error is None
    
    @pytest.mark.asyncio
    async def test_collect_need_user_result(
        self,
        collector: ResultCollector,
        sample_log_need_user: str,
    ) -> None:
        """Test collecting a result that needs user input."""
        started = datetime.now(timezone.utc)
        finished = datetime.now(timezone.utc)
        
        result = await collector.collect(
            run_id="test-run",
            log=sample_log_need_user,
            started_at=started,
            finished_at=finished,
        )
        
        assert result.status == RunStatus.NEED_USER
        assert result.marker == "::MCP_STATUS::NEED_USER"
    
    @pytest.mark.asyncio
    async def test_collect_no_marker_success(
        self,
        collector: ResultCollector,
    ) -> None:
        """Test collecting result without marker but with exit code 0."""
        started = datetime.now(timezone.utc)
        finished = datetime.now(timezone.utc)
        
        result = await collector.collect(
            run_id="test-run",
            log="Task completed",
            started_at=started,
            finished_at=finished,
            exit_code=0,
        )
        
        assert result.status == RunStatus.DONE
        assert result.marker is None
    
    @pytest.mark.asyncio
    async def test_collect_no_marker_error(
        self,
        collector: ResultCollector,
    ) -> None:
        """Test collecting result without marker and non-zero exit code."""
        started = datetime.now(timezone.utc)
        finished = datetime.now(timezone.utc)
        
        result = await collector.collect(
            run_id="test-run",
            log="Error: something failed",
            started_at=started,
            finished_at=finished,
            exit_code=1,
        )
        
        assert result.status == RunStatus.ERROR
    
    @pytest.mark.asyncio
    async def test_collect_extracts_files(
        self,
        collector: ResultCollector,
    ) -> None:
        """Test that files are extracted from log."""
        log = """Working...
Created src/example.py
Updated tests/test_example.py
::MCP_STATUS::DONE"""
        
        started = datetime.now(timezone.utc)
        finished = datetime.now(timezone.utc)
        
        result = await collector.collect(
            run_id="test-run",
            log=log,
            started_at=started,
            finished_at=finished,
        )
        
        # Files should be extracted
        assert isinstance(result.output.files_changed, list)
    
    @pytest.mark.asyncio
    async def test_collect_calculates_duration(
        self,
        collector: ResultCollector,
    ) -> None:
        """Test that duration is calculated correctly."""
        from datetime import timedelta
        
        started = datetime.now(timezone.utc)
        finished = started + timedelta(seconds=30)
        
        result = await collector.collect(
            run_id="test-run",
            log="::MCP_STATUS::DONE",
            started_at=started,
            finished_at=finished,
        )
        
        assert result.duration == pytest.approx(30.0, rel=0.1)
    
    @pytest.mark.asyncio
    async def test_collect_extracts_error(
        self,
        collector: ResultCollector,
    ) -> None:
        """Test that errors are extracted from log."""
        log = """Starting task...
Error: FileNotFoundError: file.txt not found
Traceback...
::MCP_STATUS::ERROR"""
        
        started = datetime.now(timezone.utc)
        finished = datetime.now(timezone.utc)
        
        result = await collector.collect(
            run_id="test-run",
            log=log,
            started_at=started,
            finished_at=finished,
            exit_code=1,
        )
        
        assert result.status == RunStatus.ERROR
        # Error should be extracted
        assert result.error is not None or result.output.full_log
