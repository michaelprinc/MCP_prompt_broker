import subprocess
import pytest

from mcp_prompt_broker.integrations import codex_cli


class DummyProc:
    def __init__(self, stdout="ok", stderr="", returncode=0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


def test_run_codex_cli_success(monkeypatch):
    def fake_run(cmd_list, input, capture_output, text, timeout, env, check):
        return DummyProc(stdout="generated_code()\n")

    monkeypatch.setattr(subprocess, "run", fake_run)
    res = codex_cli.run_codex_cli("Make me a function", timeout=5, env={"CODEX_CLI_CMD": "codex-cli"})
    assert res["timed_out"] is False
    assert "generated_code" in res["stdout"]


def test_run_codex_cli_timeout(monkeypatch):
    class TE(Exception):
        pass

    def fake_timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="codex-cli", timeout=1)

    monkeypatch.setattr(subprocess, "run", fake_timeout)
    res = codex_cli.run_codex_cli("prompt", timeout=1, env={"CODEX_CLI_CMD": "codex-cli"})
    assert res["timed_out"] is True
