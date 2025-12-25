# MCP Prompt Broker Remediation Checklist

## Registry + Loader
- [x] `ProfileLoader` accepts a registry path/manager and writes metadata next to the active profiles directory instead of `src/mcp_prompt_broker/copilot-profiles/profiles_metadata.json`.
- [x] `MetadataRegistryManager` exposes a factory (or CLI/env-driven override) so the server, tests, and install script can select a writable registry location.
- [x] Tests under `tests/test_profile_parser.py` (and any new fixtures) inject temporary registry paths to avoid mutating real assets.
- [ ] Running `python -m mcp_prompt_broker --profiles-dir <tmp>` with no profiles prints a clear warning yet exits cleanly, and the registry save step does not raise because of permissions.

## Deterministic routing
- [x] Markdown files are sorted before parsing, guaranteeing stable fallback selection and tie-breaking.
- [ ] At least one test covers multiple fallback profiles and asserts deterministic routing outcomes.
- [ ] Reload summaries list filenames for each failure so operators can see which profile needs attention.

## MCP tool surface
- [ ] Each tool handler in `server.py` is unit-tested (success + error path) without spinning up stdio transport.
- [ ] Tool responses return structured JSON (not just stringified dumps) so downstream clients can parse them safely.
- [ ] Integration test (or smoke test) covers `list_tools` to ensure schemas stay aligned with the new CLI/registry options.

## Documentation & install experience
- [ ] README, Developer Guide, and User Guide document the expanded profile catalog, metadata registry lifecycle, and new CLI/env options.
- [ ] `install.ps1` plus companion-agent assets propagate the selected profiles directory and registry file so Copilot Chat can call `get_profile_metadata`.
- [ ] An ADR or report entry records the registry-path change and provides migration steps for existing users.
