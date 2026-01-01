# Llama Orchestrator V2 - Implementation Checklist

> **Generated:** 2026-01-01  
> **Version:** 2.0.0  
> **Complexity:** Critical  
> **Total Tasks:** 35  
> **Estimated Effort:** 40-60 hours

---

## Overview

Tento checklist sleduje implementaci Llama Orchestrator V2 dle [Implementation Plan](./LLAMA_ORCH_V2_IMPLEMENTATION_PLAN.md).

### Status Legend

| Symbol | Meaning |
|--------|---------|
| [ ] | Not started |
| [~] | In progress |
| [x] | Completed |
| [!] | Blocked |
| [-] | Skipped/N/A |

---

## Pre-Flight Checks

- [ ] **Backup current state database** - `state/state.sqlite`
- [ ] **Run existing tests** - All pass before changes
- [ ] **Create feature branch** - `feature/llama-orch-v2`
- [ ] **Review dependencies** - Confirm psutil, httpx versions

---

## Phase 1: State & Process Reliability (15h)

### 1.1 Enhanced State Schema (3h)

- [ ] Design new `runtime` table schema
- [ ] Design new `events` table schema
- [ ] Implement schema version detection
- [ ] Implement migration from v1 to v2
- [ ] Add backup-before-migrate safety
- [ ] Write unit tests for migration
- [ ] **Acceptance:** Migration preserves existing data

**File:** `src/llama_orchestrator/engine/state.py`

### 1.2 Process Validator (4h)

- [ ] Create `ProcessValidation` dataclass
- [ ] Implement `validate_process()` with cmdline check
- [ ] Implement `find_orphaned_processes()`
- [ ] Implement port verification
- [ ] Handle edge cases (zombie, access denied)
- [ ] Write unit tests with mocked psutil
- [ ] **Acceptance:** 99% accuracy in process ownership detection

**File:** `src/llama_orchestrator/engine/validator.py` (new)

### 1.3 File Locking (2h)

- [ ] Implement Windows file locking (`msvcrt.locking`)
- [ ] Create `instance_lock()` context manager
- [ ] Add timeout mechanism
- [ ] Implement stale lock detection
- [ ] Write unit tests (parallel access simulation)
- [ ] **Acceptance:** No race conditions in concurrent CLI calls

**File:** `src/llama_orchestrator/engine/locking.py` (new)

### 1.4 Port Collision Detection (2h)

- [ ] Implement `check_port_available()`
- [ ] Check against existing instance states
- [ ] Check actual socket binding
- [ ] Update `start_instance()` to use port check
- [ ] Add descriptive error messages
- [ ] Write unit tests
- [ ] **Acceptance:** Clear error when port already in use

**File:** `src/llama_orchestrator/engine/process.py` (update)

### 1.5 Event Logging (2h)

- [ ] Implement `log_event()` function
- [ ] Implement `get_recent_events()` query
- [ ] Implement `cleanup_old_events()` retention
- [ ] Add events to existing operations (start, stop, health change)
- [ ] Write unit tests
- [ ] **Acceptance:** Events queryable by instance and time range

**File:** `src/llama_orchestrator/engine/events.py` (new)

### 1.6 State Reconciliation (2h)

- [ ] Implement `reconcile_instance()` single check
- [ ] Implement `reconcile_all()` batch check
- [ ] Handle "process died" case
- [ ] Handle "different process on port" case
- [ ] Log reconciliation events
- [ ] Write integration tests
- [ ] **Acceptance:** Stale states auto-corrected within 30s

**File:** `src/llama_orchestrator/engine/reconciler.py` (new)

### Phase 1 Validation

- [ ] All Phase 1 unit tests pass
- [ ] Integration test: Instance survives CLI restart
- [ ] Integration test: Orphan detection works
- [ ] Integration test: Port collision detected
- [ ] Code review completed
- [ ] Documentation updated

---

## Phase 2: Logging & Daemon Reliability (12h)

### 2.1 Rotating Log Handler (3h)

- [ ] Implement `setup_instance_logging()`
- [ ] Configure `RotatingFileHandler` (10MB, 3 backups)
- [ ] Update `start_instance()` to use rotating handler
- [ ] Add log file path to runtime state
- [ ] Write unit tests
- [ ] **Acceptance:** Logs rotate at size limit

**File:** `src/llama_orchestrator/engine/logging.py` (new)

### 2.2 Log Tail Command (2h)

- [ ] Add `--follow` / `-f` option to logs command
- [ ] Add `--lines` / `-n` option
- [ ] Add `--stream` option (stdout/stderr/both)
- [ ] Implement async file tailing
- [ ] Write unit tests
- [ ] **Acceptance:** `logs -f` shows real-time output

**File:** `src/llama_orchestrator/cli.py` (update)

### 2.3 Daemon V2 with Event-based Loop (5h)

- [ ] Replace `time.sleep()` with `threading.Event.wait()`
- [ ] Implement proper `stop()` method
- [ ] Add shutdown timeout (default 10s)
- [ ] Improve signal handling (SIGINT, SIGTERM)
- [ ] Update `_main_loop()` to check `_stop_event`
- [ ] Add graceful task cancellation
- [ ] Write unit tests for stop behavior
- [ ] Write integration test: stop within 5 seconds
- [ ] **Acceptance:** Daemon stops reliably within timeout

**File:** `src/llama_orchestrator/daemon/service.py` (major refactor)

### 2.4 Windows Service Support (2h)

- [ ] Research NSSM vs pywin32 approach
- [ ] Implement `install_windows_service()`
- [ ] Implement `uninstall_windows_service()`
- [ ] Create `_service_entry.py` entry point
- [ ] Add CLI commands: `daemon install`, `daemon uninstall`
- [ ] Write installation documentation
- [ ] **Acceptance:** Service visible in Windows Services

**File:** `src/llama_orchestrator/daemon/win_service.py` (new)

### Phase 2 Validation

- [ ] All Phase 2 unit tests pass
- [ ] Integration test: Logs rotate correctly
- [ ] Integration test: `logs -f` works
- [ ] Integration test: Daemon stops in <5s
- [ ] Manual test: Windows Service install/start/stop
- [ ] Code review completed
- [ ] Documentation updated

---

## Phase 3: Health Check Enhancements (8h)

### 3.1 Pluggable Health Check System (4h)

- [ ] Create `HealthProbe` abstract base class
- [ ] Implement `HTTPProbe` with configurable path
- [ ] Implement `TCPProbe` (socket connect)
- [ ] Implement `CustomProbe` (script execution)
- [ ] Create `ProbeFactory` for config-driven instantiation
- [ ] Update `HealthMonitor` to use probe system
- [ ] Write unit tests for each probe type
- [ ] **Acceptance:** Different probe types work correctly

**File:** `src/llama_orchestrator/health/probes.py` (new)

### 3.2 Config Schema Update (2h)

- [ ] Add `healthcheck.type` field (http/tcp/custom)
- [ ] Add `healthcheck.path` field (default: /health)
- [ ] Add `healthcheck.expected_status` field
- [ ] Add `healthcheck.custom_script` field
- [ ] Add `healthcheck.warmup_enabled` field
- [ ] Update schema documentation
- [ ] Write config validation tests
- [ ] Ensure backward compatibility (defaults match current behavior)
- [ ] **Acceptance:** New configs work, old configs still work

**File:** `src/llama_orchestrator/config/schema.py` (update)

### 3.3 Backoff with Jitter (2h)

- [ ] Implement `_calculate_backoff_with_jitter()`
- [ ] Add configurable jitter factor
- [ ] Update `_should_restart()` to use new calculation
- [ ] Add jitter to initial delays too
- [ ] Write property-based tests (Hypothesis)
- [ ] **Acceptance:** Restarts don't synchronize across instances

**File:** `src/llama_orchestrator/health/monitor.py` (update)

### Phase 3 Validation

- [ ] All Phase 3 unit tests pass
- [ ] Integration test: TCP probe on non-HTTP server
- [ ] Integration test: Custom health path
- [ ] Property test: Jitter distribution
- [ ] Code review completed
- [ ] Documentation updated

---

## Phase 4: CLI & UX Improvements (5h)

### 4.1 Exit Code Standards (2h)

- [ ] Create `ExitCode` enum
- [ ] Update all commands to use standard exit codes
- [ ] Document exit codes in `--help`
- [ ] Write tests for exit code consistency
- [ ] **Acceptance:** Exit codes match documentation

**File:** `src/llama_orchestrator/cli.py` (update)

### 4.2 Describe Command Enhancement (2h)

- [ ] Show effective command in `describe`
- [ ] Show runtime state (PID, uptime, memory)
- [ ] Show recent events (last 10)
- [ ] Show health check history
- [ ] Format output with Rich panels
- [ ] **Acceptance:** `describe` provides complete instance info

**File:** `src/llama_orchestrator/cli.py` (update)

### 4.3 Recent Events in Dashboard (1h)

- [ ] Add events panel to TUI dashboard
- [ ] Implement real-time event updates
- [ ] Add filtering by instance
- [ ] **Acceptance:** Dashboard shows live events

**File:** `src/llama_orchestrator/tui/` (if exists, update)

### Phase 4 Validation

- [ ] All Phase 4 unit tests pass
- [ ] Manual test: All CLI commands return correct exit codes
- [ ] Manual test: `describe` shows all expected info
- [ ] Manual test: Dashboard shows events
- [ ] Code review completed
- [ ] Documentation updated

---

## Final Validation

### Testing

- [ ] All unit tests pass (`pytest tests/ -v`)
- [ ] All integration tests pass
- [ ] Property-based tests pass
- [ ] Manual testing on Windows 10/11
- [ ] Test with multiple concurrent instances
- [ ] Test detach mode across terminal restarts
- [ ] Test daemon start/stop cycle 10+ times

### Documentation

- [ ] README.md updated with new features
- [ ] CLI help text complete
- [ ] Configuration schema documented
- [ ] Migration guide for existing users
- [ ] Troubleshooting guide updated

### Release Preparation

- [ ] Version bumped to 2.0.0
- [ ] CHANGELOG.md updated
- [ ] All commits squashed/organized
- [ ] PR created for review
- [ ] CI/CD pipeline green

---

## Post-Release Monitoring

- [ ] Monitor GitHub issues for 1 week
- [ ] Collect user feedback
- [ ] Address any critical bugs immediately
- [ ] Plan v2.1 based on feedback

---

## Notes

### Decisions Made

| Decision | Rationale | Date |
|----------|-----------|------|
| Use SQLite for state | Already in use, proven, no new deps | 2026-01-01 |
| Use psutil for process detection | Standard library, cross-platform | 2026-01-01 |
| File-based locking over DB locking | Simpler, works even if DB corrupted | 2026-01-01 |
| NSSM over pywin32 for services | Easier setup, no compile needed | 2026-01-01 |

### Open Questions

| Question | Status | Assigned |
|----------|--------|----------|
| Should we support Linux daemon (systemd)? | Deferred to v2.1 | - |
| Max event retention period? | Default 7 days | - |
| Include Prometheus metrics? | Deferred to v2.2 | - |

### Dependencies Added

- None (using existing psutil, httpx, sqlite3)

### Dependencies Removed

- None

---

## Progress Tracker

| Phase | Tasks | Completed | Progress |
|-------|-------|-----------|----------|
| Pre-Flight | 4 | 0 | 0% |
| Phase 1 | 35 | 0 | 0% |
| Phase 2 | 25 | 0 | 0% |
| Phase 3 | 20 | 0 | 0% |
| Phase 4 | 12 | 0 | 0% |
| Final | 15 | 0 | 0% |
| **Total** | **111** | **0** | **0%** |

---

*Last updated: 2026-01-01*
