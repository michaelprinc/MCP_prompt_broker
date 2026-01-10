"""
MCP Codex Orchestrator - Log Sanitizer

Masks tokens or secrets that might appear in logs.
"""

from __future__ import annotations

import re

_TOKEN_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r'("access_token"\s*:\s*")([^"]+)(")', re.IGNORECASE), r'\1***\3'),
    (re.compile(r'("refresh_token"\s*:\s*")([^"]+)(")', re.IGNORECASE), r'\1***\3'),
    (re.compile(r"(access_token=)([^&\s]+)", re.IGNORECASE), r"\1***"),
    (re.compile(r"(refresh_token=)([^&\s]+)", re.IGNORECASE), r"\1***"),
    (re.compile(r"(Bearer\s+)([A-Za-z0-9._-]+)", re.IGNORECASE), r"\1***"),
    (re.compile(r"(ya29\.[A-Za-z0-9._-]+)", re.IGNORECASE), r"***"),
]


def sanitize_text(text: str) -> str:
    """Mask tokens in the provided text."""
    if not text:
        return text
    sanitized = text
    for pattern, replacement in _TOKEN_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized
