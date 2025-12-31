"""
MCP Codex Orchestrator - Result Collector

Sběr a analýza výsledků z Codex běhů.
"""

from datetime import datetime

import structlog

from mcp_codex_orchestrator.models.run_result import CodexRunResult, RunOutput, RunStatus
from mcp_codex_orchestrator.utils.markers import (
    parse_marker,
    marker_to_status,
    extract_summary_from_log,
    extract_files_changed,
    MCP_MARKER_DONE,
    MCP_MARKER_NEED_USER,
)

logger = structlog.get_logger(__name__)


class ResultCollector:
    """Collector pro sběr a analýzu výsledků z Codex běhů."""
    
    async def collect(
        self,
        run_id: str,
        log: str,
        started_at: datetime,
        finished_at: datetime,
        exit_code: int | None = None,
    ) -> CodexRunResult:
        """
        Collect and analyze run results.
        
        Args:
            run_id: The run ID
            log: Full log output from the container
            started_at: Run start time
            finished_at: Run finish time
            exit_code: Container exit code (optional)
            
        Returns:
            Analyzed CodexRunResult
        """
        duration = (finished_at - started_at).total_seconds()
        
        # Parse marker from log
        marker = parse_marker(log)
        logger.debug("Parsed marker", run_id=run_id, marker=marker)
        
        # Determine status
        status = self._determine_status(marker, exit_code, log)
        
        # Extract summary and files changed
        summary = extract_summary_from_log(log)
        files_changed = extract_files_changed(log)
        
        # Build output
        output = RunOutput(
            summary=summary,
            files_changed=files_changed,
            full_log=log,
        )
        
        # Build result
        result = CodexRunResult(
            run_id=run_id,
            status=status,
            exit_code=exit_code,
            duration=duration,
            marker=marker,
            output=output,
            error=None if status in (RunStatus.DONE, RunStatus.NEED_USER) else self._extract_error(log),
            started_at=started_at,
            finished_at=finished_at,
        )
        
        logger.info(
            "Result collected",
            run_id=run_id,
            status=status.value,
            marker=marker,
            files_changed=len(files_changed),
        )
        
        return result
    
    def _determine_status(
        self,
        marker: str | None,
        exit_code: int | None,
        log: str,
    ) -> RunStatus:
        """
        Determine run status from marker, exit code, and log.
        
        Priority:
        1. Marker (most reliable)
        2. Exit code
        3. Log analysis
        """
        # Try marker first
        if marker:
            status_str = marker_to_status(marker)
            if status_str:
                return RunStatus(status_str)
        
        # Fallback to exit code
        if exit_code is not None:
            if exit_code == 0:
                return RunStatus.DONE
            else:
                return RunStatus.ERROR
        
        # Analyze log for common patterns
        if self._looks_like_success(log):
            return RunStatus.DONE
        
        if self._looks_like_needs_input(log):
            return RunStatus.NEED_USER
        
        # Default to error if we can't determine
        return RunStatus.ERROR
    
    def _looks_like_success(self, log: str) -> bool:
        """Check if log indicates successful completion."""
        success_indicators = [
            "completed successfully",
            "done",
            "finished",
            "task completed",
            "úspěšně dokončeno",
            "hotovo",
            "dokončeno",
        ]
        
        log_lower = log.lower()
        return any(indicator in log_lower for indicator in success_indicators)
    
    def _looks_like_needs_input(self, log: str) -> bool:
        """Check if log indicates user input is needed."""
        input_indicators = [
            "please provide",
            "need more information",
            "unclear",
            "which option",
            "please specify",
            "could you clarify",
            "prosím upřesněte",
            "potřebuji více informací",
            "nejasné",
        ]
        
        log_lower = log.lower()
        return any(indicator in log_lower for indicator in input_indicators)
    
    def _extract_error(self, log: str) -> str | None:
        """Extract error message from log if present."""
        if not log:
            return None
        
        lines = log.strip().split("\n")
        
        # Look for error patterns
        error_lines = []
        in_error_block = False
        
        for line in lines:
            line_lower = line.lower()
            
            # Start of error block
            if any(indicator in line_lower for indicator in [
                "error:", "exception:", "failed:", "traceback",
                "chyba:", "selhalo:",
            ]):
                in_error_block = True
            
            if in_error_block:
                error_lines.append(line)
                
                # End of error block (blank line or new section)
                if not line.strip():
                    in_error_block = False
        
        if error_lines:
            return "\n".join(error_lines[:20])  # Limit to 20 lines
        
        # If no structured error found, return last few lines if they look like errors
        last_lines = lines[-5:]
        for line in last_lines:
            if any(indicator in line.lower() for indicator in ["error", "failed", "chyba"]):
                return "\n".join(last_lines)
        
        return None
