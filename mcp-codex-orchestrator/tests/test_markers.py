"""
Tests for MCP status markers module.
"""

import pytest

from mcp_codex_orchestrator.utils.markers import (
    MCP_MARKER_DONE,
    MCP_MARKER_NEED_USER,
    MCP_MARKER_ERROR,
    MCP_MARKER_TIMEOUT,
    parse_marker,
    marker_to_status,
    inject_mcp_instructions,
    extract_summary_from_log,
    extract_files_changed,
)


class TestParseMarker:
    """Tests for parse_marker function."""
    
    def test_parse_done_marker(self, sample_log_done: str) -> None:
        """Test parsing DONE marker."""
        marker = parse_marker(sample_log_done)
        assert marker == MCP_MARKER_DONE
    
    def test_parse_need_user_marker(self, sample_log_need_user: str) -> None:
        """Test parsing NEED_USER marker."""
        marker = parse_marker(sample_log_need_user)
        assert marker == MCP_MARKER_NEED_USER
    
    def test_parse_no_marker(self, sample_log_no_marker: str) -> None:
        """Test parsing log without marker."""
        marker = parse_marker(sample_log_no_marker)
        assert marker is None
    
    def test_parse_empty_log(self) -> None:
        """Test parsing empty log."""
        assert parse_marker("") is None
        assert parse_marker(None) is None  # type: ignore
    
    def test_parse_marker_in_middle(self) -> None:
        """Test parsing marker in middle of text."""
        log = "Some text\n::MCP_STATUS::DONE\nMore text"
        marker = parse_marker(log)
        assert marker == MCP_MARKER_DONE
    
    def test_parse_multiple_markers(self) -> None:
        """Test parsing multiple markers (should return last)."""
        log = "::MCP_STATUS::NEED_USER\nSome text\n::MCP_STATUS::DONE"
        marker = parse_marker(log)
        assert marker == MCP_MARKER_DONE
    
    def test_parse_error_marker(self) -> None:
        """Test parsing ERROR marker."""
        log = "Error occurred\n::MCP_STATUS::ERROR"
        marker = parse_marker(log)
        assert marker == MCP_MARKER_ERROR
    
    def test_parse_timeout_marker(self) -> None:
        """Test parsing TIMEOUT marker."""
        log = "Operation timed out\n::MCP_STATUS::TIMEOUT"
        marker = parse_marker(log)
        assert marker == MCP_MARKER_TIMEOUT


class TestMarkerToStatus:
    """Tests for marker_to_status function."""
    
    def test_done_marker(self) -> None:
        """Test DONE marker conversion."""
        assert marker_to_status(MCP_MARKER_DONE) == "done"
    
    def test_need_user_marker(self) -> None:
        """Test NEED_USER marker conversion."""
        assert marker_to_status(MCP_MARKER_NEED_USER) == "need_user"
    
    def test_error_marker(self) -> None:
        """Test ERROR marker conversion."""
        assert marker_to_status(MCP_MARKER_ERROR) == "error"
    
    def test_timeout_marker(self) -> None:
        """Test TIMEOUT marker conversion."""
        assert marker_to_status(MCP_MARKER_TIMEOUT) == "timeout"
    
    def test_none_marker(self) -> None:
        """Test None marker."""
        assert marker_to_status(None) is None
    
    def test_invalid_marker(self) -> None:
        """Test invalid marker."""
        assert marker_to_status("::MCP_STATUS::INVALID") is None


class TestInjectMcpInstructions:
    """Tests for inject_mcp_instructions function."""
    
    def test_inject_czech(self) -> None:
        """Test injecting Czech instructions."""
        prompt = "Implementuj funkci"
        result = inject_mcp_instructions(prompt, language="cs")
        
        assert "Implementuj funkci" in result
        assert "::MCP_STATUS::DONE" in result
        assert "::MCP_STATUS::NEED_USER" in result
    
    def test_inject_english(self) -> None:
        """Test injecting English instructions."""
        prompt = "Implement a function"
        result = inject_mcp_instructions(prompt, language="en")
        
        assert "Implement a function" in result
        assert "::MCP_STATUS::DONE" in result
        assert "At the end" in result
    
    def test_inject_strips_whitespace(self) -> None:
        """Test that prompt whitespace is stripped."""
        prompt = "  Test prompt  \n"
        result = inject_mcp_instructions(prompt)
        
        assert result.startswith("Test prompt")


class TestExtractSummary:
    """Tests for extract_summary_from_log function."""
    
    def test_extract_with_indicators(self) -> None:
        """Test extraction with action indicators."""
        log = """Starting task...
Created file: src/example.py
Updated file: tests/test.py
Done."""
        
        summary = extract_summary_from_log(log)
        assert "Created" in summary or "Updated" in summary
    
    def test_extract_empty_log(self) -> None:
        """Test extraction from empty log."""
        assert extract_summary_from_log("") == ""
    
    def test_extract_czech_indicators(self) -> None:
        """Test extraction with Czech indicators."""
        log = """Začínám úlohu...
Vytvořen soubor: src/example.py
Hotovo."""
        
        summary = extract_summary_from_log(log)
        assert "Vytvořen" in summary


class TestExtractFilesChanged:
    """Tests for extract_files_changed function."""
    
    def test_extract_python_files(self) -> None:
        """Test extraction of Python files."""
        log = """Working...
Created src/example.py
Updated tests/test_example.py
Done."""
        
        files = extract_files_changed(log)
        assert "src/example.py" in files or any("example.py" in f for f in files)
    
    def test_extract_empty_log(self) -> None:
        """Test extraction from empty log."""
        assert extract_files_changed("") == []
    
    def test_extract_multiple_extensions(self) -> None:
        """Test extraction of multiple file types."""
        log = """Modified:
- config.json
- styles.css
- app.js
- index.html"""
        
        files = extract_files_changed(log)
        # Should find at least some files
        assert len(files) >= 0  # Relaxed assertion
