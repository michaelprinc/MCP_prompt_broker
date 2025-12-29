# llama.cpp Version Scaling - Implementation Checklist

> Generated: 2025-12-29
> Complexity: **Complex** (multi-module, new dependencies, schema changes)
> Estimated Total Effort: **8-12 hours**

---

## Overview

This checklist covers the implementation of a scalable llama.cpp binary version management system for `llama-orchestrator`. The system enables:

- Multiple llama.cpp versions to coexist
- UUID4-based binary folder isolation
- Automatic download and installation from GitHub releases
- Per-instance version pinning via config.json

---

## Phase 1: Schema & Configuration Updates

**Estimated Effort:** 2 hours

### 1.1 Extend Instance Config Schema
- [ ] Add `binary` section to `InstanceConfig` (Pydantic model)
  - [ ] `version`: str (e.g., "b7572", "latest")
  - [ ] `variant`: Literal["cpu-x64", "vulkan-x64", "cuda-12.4-x64", ...]
  - [ ] `source_url`: Optional[str] (custom download URL override)
  - [ ] `sha256`: Optional[str] (checksum verification)
- [ ] Acceptance: New fields validated by Pydantic, optional with defaults
- [ ] Update JSON Schema file if exists

### 1.2 Create Binary Registry Schema
- [ ] Create `BinaryVersion` Pydantic model
  - [ ] `id`: UUID4 (unique identifier)
  - [ ] `version`: str (llama.cpp version tag)
  - [ ] `variant`: str (platform/GPU variant)
  - [ ] `download_url`: str
  - [ ] `sha256`: Optional[str]
  - [ ] `installed_at`: datetime
  - [ ] `path`: Path (relative path under `bins/`)
- [ ] Create `BinaryRegistry` model for tracking all installed versions
- [ ] Acceptance: Models serialize/deserialize correctly

### 1.3 Update Instance Config Template
- [ ] Update `instances/<name>/config.json` to include `binary` section
- [ ] Add example config for `gpt-oss` with Vulkan binary reference
- [ ] Acceptance: Existing configs still load (backward compatible)

---

## Phase 2: Binary Management Module

**Estimated Effort:** 3-4 hours

### 2.1 Create Binary Manager Module
- [ ] Create `src/llama_orchestrator/binaries/__init__.py`
- [ ] Create `src/llama_orchestrator/binaries/manager.py`
  - [ ] `BinaryManager` class with methods:
    - [ ] `install(version, variant) -> BinaryVersion`
    - [ ] `uninstall(binary_id: UUID) -> bool`
    - [ ] `get(binary_id: UUID) -> BinaryVersion | None`
    - [ ] `list_installed() -> list[BinaryVersion]`
    - [ ] `get_by_version(version, variant) -> BinaryVersion | None`
    - [ ] `resolve_latest() -> str` (fetch latest version from GitHub API)
- [ ] Acceptance: All methods have unit tests

### 2.2 Implement Download & Extraction
- [ ] Create `src/llama_orchestrator/binaries/downloader.py`
  - [ ] `download_binary(url, dest_path) -> Path`
  - [ ] `extract_archive(archive_path, dest_dir) -> Path`
  - [ ] `verify_checksum(file_path, expected_sha256) -> bool`
- [ ] Use `httpx` for async downloads with progress
- [ ] Support `.zip` (Windows) and `.tar.gz` (Linux/macOS)
- [ ] Acceptance: Downloads complete, checksums verified, archives extracted

### 2.3 Implement GitHub API Client
- [ ] Create `src/llama_orchestrator/binaries/github.py`
  - [ ] `get_latest_release() -> dict` (version, assets)
  - [ ] `get_release(version: str) -> dict`
  - [ ] `build_download_url(version, variant) -> str`
  - [ ] Handle rate limiting gracefully
- [ ] Acceptance: API calls return expected data, rate limits handled

### 2.4 Create Binary Registry Storage
- [ ] Create `src/llama_orchestrator/binaries/registry.py`
  - [ ] Store registry in `state/binaries.json`
  - [ ] CRUD operations for binary versions
  - [ ] Atomic writes with temp file + rename
- [ ] Acceptance: Registry persists across restarts

---

## Phase 3: Directory Structure Changes

**Estimated Effort:** 1-2 hours

### 3.1 Implement Scalable Bin Directory Structure
- [ ] Create new directory layout:
  ```
  llama-orchestrator/
  ├── bins/                          # NEW: Versioned binaries
  │   ├── {uuid4}/                   # Unique ID per installation
  │   │   ├── version.json           # Metadata
  │   │   ├── llama-server.exe
  │   │   ├── *.dll
  │   │   └── ...
  │   └── {uuid4}/
  │       └── ...
  ├── bin/                           # DEPRECATED: Keep for backward compat
  │   └── llama-server.exe           # Symlink or fallback
  ```
- [ ] Update `get_bin_dir()` to return version-specific path
- [ ] Create `get_bins_root()` for the `bins/` directory
- [ ] Acceptance: Old and new paths both work

### 3.2 Update Path Resolution
- [ ] Modify `get_llama_server_path(config: InstanceConfig) -> Path`
  - [ ] Accept config to resolve binary version
  - [ ] Fall back to legacy `bin/` if no version specified
- [ ] Update `build_command()` to use instance-specific binary
- [ ] Acceptance: Commands use correct binary per instance

### 3.3 Migration Script
- [ ] Create `scripts/migrate-bins.py`
  - [ ] Move existing `bin/` contents to `bins/{uuid}/`
  - [ ] Create registry entry for migrated binary
  - [ ] Update existing instance configs
- [ ] Acceptance: Migration is non-destructive, reversible

---

## Phase 4: CLI Commands

**Estimated Effort:** 2 hours

### 4.1 Add Binary Management Commands
- [ ] `llama-orch binary install <version> [--variant vulkan-x64]`
  - [ ] Downloads and installs specified version
  - [ ] Returns UUID of installed binary
- [ ] `llama-orch binary list`
  - [ ] Lists all installed binary versions
- [ ] `llama-orch binary remove <uuid|version>`
  - [ ] Removes binary (with safety check for in-use)
- [ ] `llama-orch binary info <uuid|version>`
  - [ ] Shows detailed info about binary
- [ ] Acceptance: All commands work end-to-end

### 4.2 Update Instance Commands
- [ ] Update `llama-orch init` to accept `--binary-version`
- [ ] Update `llama-orch up` to validate binary exists before start
- [ ] Add `llama-orch upgrade <name> [--binary-version]`
  - [ ] Upgrades instance to new binary version
- [ ] Acceptance: Instance lifecycle respects binary versions

### 4.3 Add Configuration Command
- [ ] `llama-orch config set-binary <name> <uuid|version>`
  - [ ] Updates instance config to use specific binary
- [ ] Acceptance: Config updates persist correctly

---

## Phase 5: Testing & Documentation

**Estimated Effort:** 2 hours

### 5.1 Unit Tests
- [ ] `tests/test_binary_manager.py`
- [ ] `tests/test_binary_downloader.py`
- [ ] `tests/test_binary_registry.py`
- [ ] `tests/test_github_api.py`
- [ ] Acceptance: >80% code coverage for new modules

### 5.2 Integration Tests
- [ ] Test full install → configure → run → stop workflow
- [ ] Test multiple versions running simultaneously
- [ ] Test backward compatibility with legacy `bin/`
- [ ] Acceptance: All integration tests pass

### 5.3 Update Documentation
- [ ] Update `README.md` with binary management section
- [ ] Add `docs/BINARY_MANAGEMENT.md` detailed guide
- [ ] Document config.json `binary` section
- [ ] Add migration guide from legacy `bin/`
- [ ] Acceptance: Documentation is complete and accurate

---

## Phase 6: Polish & Edge Cases

**Estimated Effort:** 1 hour

### 6.1 Error Handling
- [ ] Handle download failures gracefully
- [ ] Handle corrupt archives
- [ ] Handle disk space issues
- [ ] Handle permission errors
- [ ] Acceptance: Clear error messages for all failure modes

### 6.2 Cleanup & Optimization
- [ ] Add `llama-orch binary prune` (remove unused versions)
- [ ] Add download caching in temp directory
- [ ] Add concurrent download support (future)
- [ ] Acceptance: No orphaned files, efficient downloads

### 6.3 Security
- [ ] Verify checksums for all downloads
- [ ] Validate GitHub URLs (prevent injection)
- [ ] Secure file permissions on binaries
- [ ] Acceptance: No security vulnerabilities

---

## Acceptance Criteria Summary

| Criteria | Status |
|----------|--------|
| Multiple llama.cpp versions can coexist | [ ] |
| Each binary has unique UUID4 identifier | [ ] |
| Instances can pin specific binary versions | [ ] |
| Automatic download from GitHub releases | [ ] |
| SHA256 checksum verification | [ ] |
| Backward compatible with legacy `bin/` | [ ] |
| CLI commands for binary management | [ ] |
| Unit tests with >80% coverage | [ ] |
| Documentation complete | [ ] |

---

## Rollback Plan

If issues arise:
1. Keep legacy `bin/` directory intact
2. `binary` config section is optional (defaults to legacy)
3. Migration script creates backups
4. Can revert by removing `bins/` and `binary` config sections

---

## Dependencies

- **New**: None (uses existing `httpx`, `pydantic`)
- **Updated**: `aiosqlite` for async registry operations (optional)

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| GitHub rate limiting | Medium | Medium | Cache API responses, respect limits |
| Large download sizes (~50-400MB) | High | Low | Progress indicators, resume support |
| Disk space exhaustion | Low | High | Check free space before download |
| Checksum mismatch | Low | Medium | Clear error, retry option |
| Breaking existing configs | Medium | High | Backward compatibility layer |
