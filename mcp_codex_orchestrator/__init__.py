"""Compatibility shim for `mcp_codex_orchestrator` package.

When the repository isn't installed in editable mode, some processes
expect `mcp_codex_orchestrator` to be importable from sys.path. This
module extends the package `__path__` to include the real package
located under `packages/mcp-codex-orchestrator/src/mcp_codex_orchestrator`.

This is a minimal, non-invasive fix to restore imports without
requiring an editable pip install.
"""
from __future__ import annotations

from pathlib import Path
import os

# Resolve repository root (parent of this shim directory)
# shim dir: <repo>/mcp_codex_orchestrator, repo root is its parent
_SHIM_DIR = Path(__file__).resolve().parent
_ROOT = _SHIM_DIR.parent

# Candidate locations where the real package lives
_candidates = [
    _ROOT / "packages" / "mcp-codex-orchestrator" / "src" / "mcp_codex_orchestrator",
    _ROOT / "packages" / "mcp_codex_orchestrator" / "src" / "mcp_codex_orchestrator",
]

for _p in _candidates:
    if _p.exists():
        # Insert the package directory itself so submodules are discoverable
        if str(_p) not in __path__:
            __path__.insert(0, str(_p))
        break

__all__ = []
