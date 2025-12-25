# MCP Prompt Broker Implementation Plan

## Current State Snapshot
- `src/mcp_prompt_broker/server.py:45-333` exposes an MCP server named `mcp-prompt-broker` with tools for listing profiles, routing prompts, hot reloading, checklist access, and metadata queries, all backed by a shared `ProfileLoader`.
- `src/mcp_prompt_broker/profile_parser.py:1-314` parses markdown profiles, extracts instructions/checklists, and hot-reloads them (plus checklist data) into memory.
- `src/mcp_prompt_broker/metadata_registry.py:1-470` maintains a JSON metadata registry that is automatically rewritten every reload and later queried by `get_profile_metadata`, `get_registry_summary`, and profile search tools.
- Tests only cover metadata parsing, profile parsing, and router scoring (see `tests/test_metadata_parser.py`, `tests/test_profile_parser.py`, `tests/test_profile_router.py`). There is no server-level coverage, and registry persistence is exercised only indirectly during loader tests.

## Key Issues Observed
1. The registry path is hard-wired to `src/mcp_prompt_broker/copilot-profiles/profiles_metadata.json` (see `metadata_registry.py:297-311`). Running the loader against a temporary profile directory still rewrites the shipping metadata file, and installing the package into site-packages will make registry writes fail.
2. `ProfileLoader` always instantiates the global registry manager (`profile_parser.py:231`) and writes the registry inside the package directory (`profile_parser.py:287`). Tests such as `tests/test_profile_parser.py:194-269` therefore mutate the production registry, and custom deployments cannot keep metadata side-by-side with their profile directory.
3. Profiles are loaded via `self._profiles_dir.glob("*.md")` without sorting (`profile_parser.py:269`), so load order, fallback selection, and tie-breaking vary between file systems, making routing non-deterministic.
4. The MCP tools implemented in `server.py` have no automated tests. Failures in JSON encoding, argument validation, or registry wiring will only surface at runtime.
5. Documentation still describes only the four original profiles, does not mention the metadata registry, and omits the new CLI flags/behaviour (`README.md`, `docs/DEVELOPER_GUIDE.md`). `install.ps1` also never writes the registry path into generated configs, so the companion agent cannot find non-default registries.

## Implementation Steps

### 1. Decouple metadata registry storage
- Extend `ProfileLoader` to accept either a `MetadataRegistryManager` instance or an explicit registry file path derived from the active profiles directory. When `--profiles-dir` is provided (`server.py:352-389`), derive a default registry path under that directory (e.g., `<profiles-dir>/profiles_metadata.json`).
- Update `MetadataRegistryManager` so it no longer guesses its path from `__file__`. Introduce helper constructors (e.g., `MetadataRegistryManager.from_profiles_dir`) and allow overriding via environment variable for CLI or install script integration.
- Adjust all `get_*registry*` helpers to lazily create managers using the new configuration. Ensure `ProfileLoader.reload()` passes its manager into the registry helper or uses dependency injection rather than global state.
- Modify tests (`tests/test_profile_parser.py`) to inject a temporary registry path, preventing accidental writes to `src/mcp_prompt_broker/copilot-profiles/profiles_metadata.json`.

### 2. Deterministic profile loading and fallback safety
- Sort the markdown file list before parsing to guarantee stable ordering regardless of filesystem (`profile_parser.py:269`).
- Track fallback profiles explicitly (e.g., keep a list instead of `fallback_profile or profile`) so deterministic precedence can be expressed via metadata rather than incidental load order.
- Surface reload errors with enough context (filename + exception) and propagate them through MCP tool responses so operators see which profile failed.
- Add regression tests that simulate multiple fallback profiles and verify deterministic routing outcomes for identical metadata.

### 3. Server tool contract verification
- Extract the `call_tool` handlers in `server.py` into helper functions that accept the loader/registry as parameters, making them unit-testable without spinning up the stdio transport.
- Write tests that call the new helpers for every tool (`list_profiles`, `get_profile`, `get_checklist`, `reload_profiles`, `get_registry_summary`, `get_profile_metadata`, `find_profiles_by_capability`, `find_profiles_by_domain`). Cover success paths and error conditions (e.g., missing `profile_name`, registry misses, empty prompts).
- Add an integration-style async test that instantiates `_build_server(ProfileLoader(...))`, invokes `list_tools`, and asserts that the returned schema describes the new CLI/registry options. This ensures the MCP contract stays aligned with the implementation.
- Ensure JSON payloads returned by tools include structured metadata rather than stringified blobs wherever possible, simplifying downstream parsing.

### 4. Documentation and install experience
- Update `README.md` and `docs/DEVELOPER_GUIDE.md` to list the expanded profile set (creative, privacy, technical, general, python code generation, python testing, podman) and describe the metadata registry lifecycle plus the new CLI/environment knobs.
- Extend `docs/USER_GUIDE.md` with instructions for pointing the MCP server at custom profile bundles and for interpreting registry summaries/checklists.
- Update `install.ps1` and companion agent templates so they write the selected profiles directory and registry file into generated configuration files, guaranteeing that Copilot Chat can call `get_profile_metadata`.
- Provide an ADR or report entry summarizing the data-path change and documenting migration steps for existing installs.

## Testing & Validation Strategy
- Expand unit tests for `MetadataRegistryManager`, `ProfileLoader`, and the MCP tool helpers to run under `pytest` without touching repo assets. Use temporary directories and fixtures to assert that registries are written to the requested location.
- Add deterministic routing tests that confirm both standard and complex profiles get consistent scores regardless of file system order.
- Include CLI smoke tests that invoke `python -m mcp_prompt_broker --profiles-dir <tmp>` and assert the stdout warnings/success messages are informative when profiles are missing.

## Deliverables
- Configurable registry path wired through loader, CLI, install script, and documentation.
- Deterministic profile loading with explicit fallback semantics and improved error reporting.
- Automated coverage for every MCP tool along with fixtures for custom profile directories.
- Updated documentation + install assets that mirror the actual capabilities exposed by the server.
