# Delegated Task Runner Tool Pick Rate Update Report

Date: 2026-01-11

## Summary
- Renamed the MCP server to `delegated-task-runner` and updated workspace configuration and documentation references.
- Updated `codex_run` and `gemini_run` tool schemas with clearer parameter names, added `intent` routing hint, and expanded tool descriptions with usage bullets and mini examples.
- Added explicit documentation that the server supports two providers (Codex CLI and Gemini CLI) and aligned profile/tool docs with the new schema.

## Implementation Notes
- Server/tool changes: `packages/mcp-codex-orchestrator/src/mcp_codex_orchestrator/server.py`, `packages/mcp-codex-orchestrator/src/mcp_codex_orchestrator/models/run_request.py`, `packages/mcp-codex-orchestrator/src/mcp_codex_orchestrator/models/gemini_run_request.py`, `packages/mcp-codex-orchestrator/src/mcp_codex_orchestrator/orchestrator/run_manager.py`, `packages/mcp-codex-orchestrator/src/mcp_codex_orchestrator/orchestrator/gemini_run_manager.py`, `packages/mcp-codex-orchestrator/src/mcp_codex_orchestrator/tools/codex_run.py`, `packages/mcp-codex-orchestrator/src/mcp_codex_orchestrator/tools/gemini_run.py`.
- Test updates: `packages/mcp-codex-orchestrator/tests/test_models.py`, `packages/mcp-codex-orchestrator/tests/test_run_manager.py`, `packages/mcp-codex-orchestrator/tests/conftest.py`.
- Config/docs/profiles: `.vscode/mcp.json`, `packages/mcp-codex-orchestrator/README.md`, `docs/api/MCP_TOOLS.md`, `docs/modules/CODEX_ORCHESTRATOR.md`, `docs/WORKSPACE_OVERVIEW.md`, `docs/architecture/ARCHITECTURE.md`, `packages/mcp-prompt-broker/src/mcp_prompt_broker/copilot-profiles/codex_cli.md`, `packages/mcp-prompt-broker/src/mcp_prompt_broker/copilot-profiles/python_code_generation_complex_with_codex.md`, `packages/mcp-prompt-broker/src/mcp_prompt_broker/copilot-profiles/template/codex_orchestrator_integration.md`, `packages/mcp-prompt-broker/src/mcp_prompt_broker/copilot-profiles/profiles_metadata.json`.

## Tests
- `pytest packages/mcp-codex-orchestrator/tests`
  - Result: FAIL
  - Error: `ModuleNotFoundError: No module named 'mcp_codex_orchestrator'`
- `PYTHONPATH=k:\Data_science_projects\MCP_Prompt_Broker\packages\mcp-codex-orchestrator\src pytest packages/mcp-codex-orchestrator/tests`
  - Result: FAIL
  - Error: `ImportError: cannot import name 'get_security_flags' from 'mcp_codex_orchestrator.security.modes'`
  - Note: This appears to be a pre-existing test/import issue; no changes were made to `security/modes.py` in this update.
