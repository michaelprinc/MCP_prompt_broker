"""
MCP Codex Orchestrator - JSONL Parser

Parser pro JSONL stream z Codex CLI --json výstupu.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import AsyncIterator, Iterator

import aiofiles
import structlog

from mcp_codex_orchestrator.models.jsonl_events import (
    CodexEvent,
    CommandRun,
    CompletionData,
    ErrorData,
    EventType,
    FileChange,
    FileChangeAction,
    ParsedRunOutput,
    TokenUsage,
)

logger = structlog.get_logger(__name__)


class JSONLParseError(Exception):
    """Error parsing JSONL line."""
    pass


class JSONLParser:
    """Parser pro JSONL stream z Codex CLI --json výstupu."""
    
    def __init__(self) -> None:
        self._buffer = ""
    
    def parse_line(self, line: str) -> CodexEvent:
        """
        Parse single JSONL line.
        
        Args:
            line: Single line of JSONL
            
        Returns:
            Parsed CodexEvent
            
        Raises:
            JSONLParseError: If line cannot be parsed
        """
        line = line.strip()
        if not line:
            raise JSONLParseError("Empty line")
        
        try:
            data = json.loads(line)
        except json.JSONDecodeError as e:
            raise JSONLParseError(f"Invalid JSON: {e}") from e
        
        # Extract event type
        event_type_str = data.get("type", "")
        try:
            event_type = EventType(event_type_str)
        except ValueError:
            # Unknown event type - use a fallback
            logger.warning("Unknown event type", event_type=event_type_str)
            event_type = EventType.MESSAGE_DELTA
        
        # Extract timestamp
        timestamp_str = data.get("timestamp")
        if timestamp_str:
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            except ValueError:
                timestamp = datetime.utcnow()
        else:
            timestamp = datetime.utcnow()
        
        return CodexEvent(
            type=event_type,
            timestamp=timestamp,
            data=data.get("data", data),
        )
    
    async def parse_stream(
        self, 
        stream: AsyncIterator[str],
    ) -> AsyncIterator[CodexEvent]:
        """
        Parse JSONL stream in real-time.
        
        Args:
            stream: Async iterator of string chunks
            
        Yields:
            Parsed CodexEvent objects
        """
        buffer = ""
        
        async for chunk in stream:
            buffer += chunk
            
            # Process complete lines
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                
                if not line:
                    continue
                
                try:
                    event = self.parse_line(line)
                    yield event
                except JSONLParseError as e:
                    logger.warning("Failed to parse JSONL line", error=str(e), line=line[:100])
        
        # Process remaining buffer
        if buffer.strip():
            try:
                event = self.parse_line(buffer)
                yield event
            except JSONLParseError as e:
                logger.warning("Failed to parse final JSONL line", error=str(e))
    
    def parse_lines(self, lines: Iterator[str]) -> Iterator[CodexEvent]:
        """
        Parse JSONL lines synchronously.
        
        Args:
            lines: Iterator of JSONL lines
            
        Yields:
            Parsed CodexEvent objects
        """
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            try:
                yield self.parse_line(line)
            except JSONLParseError as e:
                logger.warning("Failed to parse JSONL line", error=str(e))
    
    async def parse_file(self, path: Path) -> list[CodexEvent]:
        """
        Parse completed JSONL file.
        
        Args:
            path: Path to JSONL file
            
        Returns:
            List of parsed CodexEvent objects
        """
        events: list[CodexEvent] = []
        
        async with aiofiles.open(path, "r", encoding="utf-8") as f:
            async for line in f:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    event = self.parse_line(line)
                    events.append(event)
                except JSONLParseError as e:
                    logger.warning("Failed to parse JSONL line", error=str(e), path=str(path))
        
        return events
    
    def extract_summary(self, events: list[CodexEvent]) -> ParsedRunOutput:
        """
        Extract structured summary from events.
        
        Args:
            events: List of parsed events
            
        Returns:
            ParsedRunOutput with extracted data
        """
        output = ParsedRunOutput(events=events)
        
        for event in events:
            self._process_event(event, output)
        
        return output
    
    def _process_event(self, event: CodexEvent, output: ParsedRunOutput) -> None:
        """Process single event and update output."""
        
        if event.type == EventType.FILE_CHANGE:
            file_change = self._extract_file_change(event.data)
            if file_change:
                output.file_changes.append(file_change)
        
        elif event.type == EventType.COMMAND_RUN:
            command = self._extract_command(event.data)
            if command:
                output.commands.append(command)
        
        elif event.type == EventType.ERROR:
            error = self._extract_error(event.data)
            if error:
                output.errors.append(error)
        
        elif event.type == EventType.COMPLETION:
            completion = self._extract_completion(event.data)
            if completion:
                output.completion = completion
                output.token_usage = completion.token_usage
    
    def _extract_file_change(self, data: dict) -> FileChange | None:
        """Extract FileChange from event data."""
        path = data.get("path") or data.get("file")
        if not path:
            return None
        
        action_str = data.get("action", "modified")
        try:
            action = FileChangeAction(action_str)
        except ValueError:
            action = FileChangeAction.MODIFIED
        
        return FileChange(
            path=path,
            action=action,
            diff=data.get("diff"),
            content_before=data.get("content_before"),
            content_after=data.get("content_after"),
        )
    
    def _extract_command(self, data: dict) -> CommandRun | None:
        """Extract CommandRun from event data."""
        command = data.get("command") or data.get("cmd")
        if not command:
            return None
        
        return CommandRun(
            command=command,
            exit_code=data.get("exit_code", 0),
            stdout=data.get("stdout", ""),
            stderr=data.get("stderr", ""),
            duration_ms=data.get("duration_ms", 0),
            working_dir=data.get("working_dir"),
        )
    
    def _extract_error(self, data: dict) -> ErrorData | None:
        """Extract ErrorData from event data."""
        message = data.get("message") or data.get("error") or str(data)
        
        return ErrorData(
            code=data.get("code", "unknown"),
            message=message,
            details=data.get("details"),
            recoverable=data.get("recoverable", False),
        )
    
    def _extract_completion(self, data: dict) -> CompletionData | None:
        """Extract CompletionData from event data."""
        summary = data.get("summary", "")
        
        # Extract token usage
        usage_data = data.get("token_usage", data.get("usage", {}))
        token_usage = TokenUsage(
            prompt_tokens=usage_data.get("prompt_tokens", 0),
            completion_tokens=usage_data.get("completion_tokens", 0),
            total_tokens=usage_data.get("total_tokens", 0),
        )
        
        return CompletionData(
            summary=summary,
            changed_files=data.get("changed_files", []),
            commands_run=data.get("commands_run", []),
            next_steps=data.get("next_steps"),
            token_usage=token_usage,
            duration_seconds=data.get("duration_seconds", 0.0),
        )


# Convenience functions

async def parse_jsonl_file(path: Path) -> ParsedRunOutput:
    """
    Parse JSONL file and return structured output.
    
    Args:
        path: Path to JSONL file
        
    Returns:
        ParsedRunOutput with all extracted data
    """
    parser = JSONLParser()
    events = await parser.parse_file(path)
    return parser.extract_summary(events)


def parse_jsonl_string(content: str) -> ParsedRunOutput:
    """
    Parse JSONL string content and return structured output.
    
    Args:
        content: JSONL content as string
        
    Returns:
        ParsedRunOutput with all extracted data
    """
    parser = JSONLParser()
    events = list(parser.parse_lines(content.splitlines()))
    return parser.extract_summary(events)
