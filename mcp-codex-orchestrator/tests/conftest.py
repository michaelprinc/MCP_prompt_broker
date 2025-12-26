"""
MCP Codex Orchestrator - Test Configuration

Pytest fixtures and configuration.
"""

import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def temp_workspace() -> Generator[Path, None, None]:
    """Create a temporary workspace directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir) / "workspace"
        workspace.mkdir()
        yield workspace


@pytest.fixture
def temp_runs() -> Generator[Path, None, None]:
    """Create a temporary runs directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        runs = Path(tmpdir) / "runs"
        runs.mkdir()
        yield runs


@pytest.fixture
def mock_docker_client() -> MagicMock:
    """Create a mock Docker client."""
    mock = MagicMock()
    mock.ping.return_value = True
    mock.images.get.return_value = MagicMock()
    
    # Mock container
    mock_container = MagicMock()
    mock_container.short_id = "abc123"
    mock_container.logs.return_value = iter([b"Test log output\n::MCP_STATUS::DONE\n"])
    mock_container.wait.return_value = {"StatusCode": 0}
    
    mock.containers.run.return_value = mock_container
    
    return mock


@pytest.fixture
def sample_log_done() -> str:
    """Sample log with DONE marker."""
    return """Starting task...
Working on implementation...
Created file: src/example.py
Updated file: tests/test_example.py
Task completed successfully.
::MCP_STATUS::DONE"""


@pytest.fixture
def sample_log_need_user() -> str:
    """Sample log with NEED_USER marker."""
    return """Starting task...
Analyzing requirements...
I need more information about the expected behavior.
Please specify which database you want to use.
::MCP_STATUS::NEED_USER"""


@pytest.fixture
def sample_log_no_marker() -> str:
    """Sample log without marker."""
    return """Starting task...
Working on implementation...
Done."""


@pytest.fixture
def sample_request_data() -> dict:
    """Sample request data."""
    return {
        "prompt": "Implementuj funkci pro validaci emailu",
        "mode": "full-auto",
        "timeout": 300,
    }
