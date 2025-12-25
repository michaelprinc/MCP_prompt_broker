import subprocess
import shlex
from typing import Dict, Optional


def run_codex_cli(prompt: str, timeout: int = 30, env: Optional[Dict[str, str]] = None, cmd: Optional[str] = None) -> Dict:
    """Run Codex CLI safely and return structured result.

    Args:
        prompt: text prompt passed to CLI via stdin
        timeout: seconds before timing out
        env: optional environment overrides
        cmd: optional CLI command (overrides env variable)

    Returns:
        dict with keys: stdout, stderr, returncode, timed_out
    """
    cli_cmd = cmd or env and env.get("CODEX_CLI_CMD") or None
    if not cli_cmd:
        # fallback to environment variable if not provided
        import os

        cli_cmd = os.environ.get("CODEX_CLI_CMD")

    if not cli_cmd:
        raise RuntimeError("Codex CLI command not configured. Set CODEX_CLI_CMD environment variable or provide cmd param.")

    # prepare command safely
    if isinstance(cli_cmd, str):
        cmd_list = shlex.split(cli_cmd)
    else:
        cmd_list = cli_cmd

    # append mode or flags if needed (left to caller to include in CODEX_CLI_CMD)

    try:
        proc = subprocess.run(
            cmd_list,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            check=False,
        )
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        # enforce output size limit to avoid memory issues
        max_out = 200_000
        if len(stdout) > max_out:
            stdout = stdout[:max_out] + "\n...[truncated]"

        return {
            "stdout": stdout,
            "stderr": stderr,
            "returncode": proc.returncode,
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as e:
        # best-effort cleanup
        return {
            "stdout": getattr(e, "output", "") or "",
            "stderr": getattr(e, "stderr", "") or "",
            "returncode": None,
            "timed_out": True,
        }
