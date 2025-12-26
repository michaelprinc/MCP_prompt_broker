"""
MCP Codex Orchestrator - Exceptions

Custom exception třídy pro orchestrátor.
"""


class OrchestratorError(Exception):
    """Base exception for orchestrator errors."""
    pass


class DockerNotAvailableError(OrchestratorError):
    """Raised when Docker daemon is not available."""
    pass


class ImageNotFoundError(OrchestratorError):
    """Raised when Docker image cannot be found or pulled."""
    pass


class ContainerError(OrchestratorError):
    """Raised when container fails to start or run."""
    pass


class RunTimeoutError(OrchestratorError):
    """Raised when a run exceeds its timeout."""
    pass


class RunNotFoundError(OrchestratorError):
    """Raised when a run ID is not found."""
    pass


class MarkerNotFoundError(OrchestratorError):
    """Raised when MCP marker is not found in output."""
    pass
