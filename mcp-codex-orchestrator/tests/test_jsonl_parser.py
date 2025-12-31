"""
Tests for JSONL parser module.
"""

import pytest
from io import StringIO

from mcp_codex_orchestrator.models.jsonl_events import (
    EventType,
    CodexEvent,
    FileChange,
    CommandRun,
)
from mcp_codex_orchestrator.orchestrator.jsonl_parser import JSONLParser


class TestJSONLParser:
    """Test suite for JSONLParser."""

    def test_parse_message_event(self):
        """Test parsing a message event."""
        parser = JSONLParser()
        line = '{"type": "message", "role": "assistant", "content": "Hello"}'
        
        event = parser._parse_line(line)
        
        assert event is not None
        assert event.type == EventType.MESSAGE
        assert event.role == "assistant"
        assert event.content == "Hello"

    def test_parse_file_change_event(self):
        """Test parsing a file change event."""
        parser = JSONLParser()
        line = '{"type": "file_change", "path": "src/main.py", "action": "create", "content": "print(1)"}'
        
        event = parser._parse_line(line)
        
        assert event is not None
        assert event.type == EventType.FILE_CHANGE
        assert event.path == "src/main.py"
        assert event.action == "create"
        assert event.content == "print(1)"

    def test_parse_command_run_event(self):
        """Test parsing a command run event."""
        parser = JSONLParser()
        line = '{"type": "command_run", "command": "pytest", "exit_code": 0, "output": "1 passed"}'
        
        event = parser._parse_line(line)
        
        assert event is not None
        assert event.type == EventType.COMMAND_RUN
        assert event.command == "pytest"
        assert event.exit_code == 0
        assert event.output == "1 passed"

    def test_parse_stream(self):
        """Test parsing a stream of JSONL events."""
        parser = JSONLParser()
        stream = StringIO(
            '{"type": "message", "role": "assistant", "content": "Starting..."}\n'
            '{"type": "file_change", "path": "test.py", "action": "create"}\n'
            '{"type": "completion", "status": "success"}\n'
        )
        
        events = list(parser.parse_stream(stream))
        
        assert len(events) == 3
        assert events[0].type == EventType.MESSAGE
        assert events[1].type == EventType.FILE_CHANGE
        assert events[2].type == EventType.COMPLETION

    def test_parse_invalid_json(self):
        """Test that invalid JSON lines are skipped."""
        parser = JSONLParser()
        stream = StringIO(
            '{"type": "message", "content": "valid"}\n'
            'not valid json\n'
            '{"type": "completion"}\n'
        )
        
        events = list(parser.parse_stream(stream))
        
        assert len(events) == 2

    def test_extract_summary(self):
        """Test extracting summary from events."""
        parser = JSONLParser()
        events = [
            CodexEvent(type=EventType.MESSAGE, role="assistant", content="Working on it..."),
            CodexEvent(type=EventType.FILE_CHANGE, path="src/main.py", action="create"),
            CodexEvent(type=EventType.FILE_CHANGE, path="tests/test_main.py", action="create"),
            CodexEvent(type=EventType.COMPLETION, status="success"),
        ]
        
        summary = parser.extract_summary(events)
        
        assert summary["total_events"] == 4
        assert summary["file_changes"] == 2
        assert summary["files_created"] == ["src/main.py", "tests/test_main.py"]
        assert summary["status"] == "success"

    def test_empty_stream(self):
        """Test parsing an empty stream."""
        parser = JSONLParser()
        stream = StringIO("")
        
        events = list(parser.parse_stream(stream))
        
        assert len(events) == 0
