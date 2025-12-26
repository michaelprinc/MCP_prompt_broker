"""
MCP Codex Orchestrator - Entry Point

Spuštění:
    python -m mcp_codex_orchestrator
    python -m mcp_codex_orchestrator --host 0.0.0.0 --port 3000
"""

import argparse
import asyncio
import sys

from mcp_codex_orchestrator.server import run_server
from mcp_codex_orchestrator.utils.logging import setup_logging


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        prog="mcp-codex-orchestrator",
        description="MCP server for orchestrating Codex CLI runs in Docker containers",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="localhost",
        help="Host to bind to (default: localhost)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=3000,
        help="Port to bind to (default: 3000)",
    )
    parser.add_argument(
        "--transport",
        type=str,
        choices=["stdio", "http"],
        default="stdio",
        help="Transport mode (default: stdio)",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Log level (default: INFO)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
    )
    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    args = parse_args()
    
    # Setup logging
    setup_logging(level=args.log_level)
    
    try:
        # Run the server
        asyncio.run(
            run_server(
                transport=args.transport,
                host=args.host,
                port=args.port,
            )
        )
        return 0
    except KeyboardInterrupt:
        print("\nShutdown requested, exiting...")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
