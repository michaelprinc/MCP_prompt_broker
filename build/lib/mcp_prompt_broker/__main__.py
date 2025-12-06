"""Module entrypoint for `python -m mcp_prompt_broker`."""
from .server import run

if __name__ == "__main__":
    raise SystemExit(run())
