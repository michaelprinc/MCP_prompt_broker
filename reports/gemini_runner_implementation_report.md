## Gemini Runner Implementation Report

### Overview
Implemented provider-agnostic RunResult schema and added Gemini runner support (Docker image, OAuth mount, CLI execution, MCP tools) while preserving Codex compatibility.

### Key Changes
- Added `RunResult`/`RunProvider` model and `run_result.json` artifacts for provider-agnostic results.
- Added Gemini Docker runner (`Dockerfile.gemini`, `gemini-runner` compose service).
- Implemented Gemini run manager, Docker client, and MCP tools (`gemini_run`, `gemini_run_status`, `gemini_run_cancel`, `gemini_run_artifacts`, `gemini_git_diff`).
- Added OAuth bootstrap script `scripts/setup-gemini-auth.ps1` and docs in `docs/GEMINI_RUNNER.md`.
- Added log sanitization helper to mask token-like strings before writing logs.
- Updated docs/configs for Gemini environment variables and troubleshooting.

### Files Added
- `packages/mcp-codex-orchestrator/src/mcp_codex_orchestrator/utils/sanitize.py`
- `packages/mcp-codex-orchestrator/src/mcp_codex_orchestrator/models/gemini_run_request.py`
- `packages/mcp-codex-orchestrator/src/mcp_codex_orchestrator/orchestrator/docker_gemini_client.py`
- `packages/mcp-codex-orchestrator/src/mcp_codex_orchestrator/orchestrator/gemini_run_manager.py`
- `packages/mcp-codex-orchestrator/src/mcp_codex_orchestrator/tools/gemini_run.py`
- `packages/mcp-codex-orchestrator/src/mcp_codex_orchestrator/tools/gemini_status.py`
- `packages/mcp-codex-orchestrator/src/mcp_codex_orchestrator/tools/gemini_cancel.py`
- `packages/mcp-codex-orchestrator/src/mcp_codex_orchestrator/tools/gemini_artifacts.py`
- `packages/mcp-codex-orchestrator/src/mcp_codex_orchestrator/tools/gemini_git_diff.py`
- `packages/mcp-codex-orchestrator/docker/Dockerfile.gemini`
- `packages/mcp-codex-orchestrator/scripts/setup-gemini-auth.ps1`
- `packages/mcp-codex-orchestrator/docs/GEMINI_RUNNER.md`

### Files Updated
- `packages/mcp-codex-orchestrator/src/mcp_codex_orchestrator/models/run_result.py`
- `packages/mcp-codex-orchestrator/src/mcp_codex_orchestrator/models/__init__.py`
- `packages/mcp-codex-orchestrator/src/mcp_codex_orchestrator/orchestrator/run_manager.py`
- `packages/mcp-codex-orchestrator/src/mcp_codex_orchestrator/orchestrator/__init__.py`
- `packages/mcp-codex-orchestrator/src/mcp_codex_orchestrator/tools/codex_artifacts.py`
- `packages/mcp-codex-orchestrator/src/mcp_codex_orchestrator/tools/codex_status.py`
- `packages/mcp-codex-orchestrator/src/mcp_codex_orchestrator/tools/codex_git_diff.py`
- `packages/mcp-codex-orchestrator/src/mcp_codex_orchestrator/tools/__init__.py`
- `packages/mcp-codex-orchestrator/src/mcp_codex_orchestrator/server.py`
- `packages/mcp-codex-orchestrator/src/mcp_codex_orchestrator/utils/__init__.py`
- `packages/mcp-codex-orchestrator/docker/docker-compose.yml`
- `packages/mcp-codex-orchestrator/docker/.env.example`
- `packages/mcp-codex-orchestrator/README.md`
- `packages/mcp-codex-orchestrator/docs/TROUBLESHOOTING.md`
- `packages/mcp-codex-orchestrator/docs/SECURITY.md`

### Notes
- Gemini CLI runs with `--approval-mode auto_edit` for `workspace_write` and `--extensions none` by default.
- OAuth credentials are mounted from `~/.gemini` and not copied into run artifacts.
- `run_result.json` is added for provider-agnostic outputs while existing Codex `result.json` remains unchanged.

### Testing
Not run (no automated tests executed in this change).
