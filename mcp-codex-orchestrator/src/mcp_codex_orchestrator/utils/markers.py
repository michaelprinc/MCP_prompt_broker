"""
MCP Codex Orchestrator - Status Markers

Konstanty a parsování MCP status markerů.
"""

import re
from typing import Literal

# MCP Status Markers
MCP_MARKER_DONE = "::MCP_STATUS::DONE"
MCP_MARKER_NEED_USER = "::MCP_STATUS::NEED_USER"
MCP_MARKER_ERROR = "::MCP_STATUS::ERROR"
MCP_MARKER_TIMEOUT = "::MCP_STATUS::TIMEOUT"

# All valid markers
VALID_MARKERS = frozenset({
    MCP_MARKER_DONE,
    MCP_MARKER_NEED_USER,
    MCP_MARKER_ERROR,
    MCP_MARKER_TIMEOUT,
})

# Regex pattern for marker detection
MARKER_PATTERN = re.compile(
    r"::MCP_STATUS::(DONE|NEED_USER|ERROR|TIMEOUT)",
    re.MULTILINE,
)

# MCP instruction suffix to append to prompts
MCP_INSTRUCTION_SUFFIX = """
---
Na konci své odpovědi vypiš na samostatný poslední řádek přesně jeden z následujících markerů:
::MCP_STATUS::DONE pokud je úloha dokončena.
::MCP_STATUS::NEED_USER pokud je nutný zásah uživatele nebo chybí informace.
Nevypisuj žádný jiný text za markerem.
"""

# English version (for multilingual support)
MCP_INSTRUCTION_SUFFIX_EN = """
---
At the end of your response, output exactly one of the following markers on the last line:
::MCP_STATUS::DONE if the task is completed.
::MCP_STATUS::NEED_USER if user intervention is needed or information is missing.
Do not output any other text after the marker.
"""


def parse_marker(log: str) -> str | None:
    """
    Parse MCP status marker from log output.
    
    Args:
        log: Full log output from Codex CLI
        
    Returns:
        The detected marker string (e.g., "::MCP_STATUS::DONE") or None if not found
    """
    if not log:
        return None
    
    # Search for marker pattern
    matches = MARKER_PATTERN.findall(log)
    
    if not matches:
        return None
    
    # Return the last marker found (in case there are multiple)
    last_status = matches[-1]
    return f"::MCP_STATUS::{last_status}"


def marker_to_status(marker: str | None) -> Literal["done", "need_user", "error", "timeout"] | None:
    """
    Convert marker string to status value.
    
    Args:
        marker: The marker string (e.g., "::MCP_STATUS::DONE")
        
    Returns:
        Status string or None if invalid marker
    """
    if marker is None:
        return None
    
    mapping = {
        MCP_MARKER_DONE: "done",
        MCP_MARKER_NEED_USER: "need_user",
        MCP_MARKER_ERROR: "error",
        MCP_MARKER_TIMEOUT: "timeout",
    }
    
    return mapping.get(marker)


def inject_mcp_instructions(prompt: str, language: str = "cs") -> str:
    """
    Inject MCP instructions into the prompt.
    
    Args:
        prompt: Original user prompt
        language: Language for instructions ("cs" or "en")
        
    Returns:
        Prompt with MCP instructions appended
    """
    suffix = MCP_INSTRUCTION_SUFFIX if language == "cs" else MCP_INSTRUCTION_SUFFIX_EN
    return f"{prompt.strip()}\n{suffix}"


def extract_summary_from_log(log: str) -> str:
    """
    Extract a summary from the Codex log output.
    
    Tries to find meaningful summary lines from the output.
    
    Args:
        log: Full log output
        
    Returns:
        Extracted summary or empty string
    """
    if not log:
        return ""
    
    lines = log.strip().split("\n")
    
    # Look for common summary patterns
    summary_lines = []
    
    for line in lines:
        line = line.strip()
        
        # Skip empty lines and markers
        if not line or line.startswith("::MCP_STATUS::"):
            continue
        
        # Look for action indicators
        if any(indicator in line.lower() for indicator in [
            "created", "updated", "deleted", "modified",
            "vytvořen", "aktualizován", "smazán", "změněn",
            "added", "removed", "fixed", "implemented",
            "přidán", "odstraněn", "opraven", "implementován",
        ]):
            summary_lines.append(line)
    
    # Return first few summary lines
    if summary_lines:
        return "\n".join(summary_lines[:5])
    
    # Fallback: return last non-marker lines
    non_marker_lines = [
        line.strip() for line in lines 
        if line.strip() and not line.strip().startswith("::MCP_STATUS::")
    ]
    
    if non_marker_lines:
        return "\n".join(non_marker_lines[-3:])
    
    return ""


def extract_files_changed(log: str) -> list[str]:
    """
    Extract list of changed files from the Codex log output.
    
    Args:
        log: Full log output
        
    Returns:
        List of file paths that were changed
    """
    if not log:
        return []
    
    files = set()
    
    # Common patterns for file operations
    file_patterns = [
        # Git-style output
        re.compile(r"(?:create|modify|delete|rename)\s+mode\s+\d+\s+(.+)"),
        # Direct file mentions
        re.compile(r"(?:Created|Updated|Modified|Deleted|Added|Removed)\s+[`'\"]?([^\s`'\"]+\.\w+)[`'\"]?"),
        # Czech variants
        re.compile(r"(?:Vytvořen|Aktualizován|Změněn|Smazán|Přidán|Odstraněn)\s+[`'\"]?([^\s`'\"]+\.\w+)[`'\"]?"),
        # File path patterns (common extensions)
        re.compile(r"(?:^|\s)([a-zA-Z0-9_\-./]+\.(?:py|js|ts|json|yaml|yml|md|txt|html|css|sh))\b"),
    ]
    
    for pattern in file_patterns:
        matches = pattern.findall(log)
        for match in matches:
            # Clean up the file path
            file_path = match.strip().strip("'\"")
            if file_path and "/" in file_path or "." in file_path:
                files.add(file_path)
    
    return sorted(files)
