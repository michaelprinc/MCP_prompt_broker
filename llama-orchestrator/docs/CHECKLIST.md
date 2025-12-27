# llama-orchestrator — Implementation Checklist

> **Generated:** 2024-12-27  
> **Complexity:** Critical  
> **Estimated Total Effort:** 40-60 hours  
> **Link:** [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)

---

## Phase 0: Foundations
**Effort:** 4-6 hours | **Dependencies:** None

### 0.1 Project Scaffolding
- [x] Create `llama-orchestrator/` directory structure
  - Acceptance: All directories exist as per plan
- [x] Create `pyproject.toml` with uv/pip compatibility
  - Acceptance: `uv sync` completes without errors
- [x] Add dependencies: pydantic, typer, rich, httpx, psutil
  - Acceptance: All packages installable
- [x] Create `src/llama_orchestrator/__init__.py`
  - Acceptance: Package importable

### 0.2 Entry Point
- [x] Create `src/llama_orchestrator/__main__.py`
  - Acceptance: `python -m llama_orchestrator` runs
- [x] Setup basic Typer app structure
  - Acceptance: `--help` shows command list
- [x] Add version command
  - Acceptance: `--version` shows version

### 0.3 Development Setup
- [x] Create `.gitignore` for Python project
- [x] Setup pytest configuration
- [ ] Add pre-commit hooks (optional)

---

## Phase 1: Configuration Model + Validation
**Effort:** 6-8 hours | **Dependencies:** Phase 0

### 1.1 Pydantic Schemas
- [ ] Define `ModelConfig` schema
  - Fields: path, context_size, batch_size, threads
  - Acceptance: Validates all fields correctly
- [ ] Define `ServerConfig` schema
  - Fields: host, port, timeout, parallel
  - Acceptance: Port range validation works
- [ ] Define `GpuConfig` schema
  - Fields: backend (cpu|vulkan|cuda), device_id, layers
  - Acceptance: Enum validation works
- [ ] Define `HealthcheckConfig` schema
  - Fields: path, interval, timeout, retries, start_period
  - Acceptance: All fields have sensible defaults
- [ ] Define `RestartPolicy` schema
  - Fields: enabled, max_retries, backoff_multiplier
  - Acceptance: Backoff calculation works
- [ ] Define `InstanceConfig` (root schema)
  - Acceptance: Full config validates

### 1.2 Config Loading
- [ ] Implement `load_config(path: Path) -> InstanceConfig`
  - Acceptance: Loads JSON, returns Pydantic model
- [ ] Handle missing optional fields gracefully
  - Acceptance: Uses defaults
- [ ] Implement config discovery (`instances/*/config.json`)
  - Acceptance: Finds all instance configs

### 1.3 Validation Logic
- [ ] Validate model file exists
  - Acceptance: Clear error if missing
- [ ] Validate port not already in use
  - Acceptance: Uses `psutil.net_connections()`
- [ ] Validate unique ports across instances
  - Acceptance: Detects collisions
- [ ] Validate log directory writable
  - Acceptance: Creates if missing

### 1.4 CLI Commands
- [ ] Implement `llama-orch config validate <path>`
  - Acceptance: Exit 0 if valid, 1 if invalid
- [ ] Implement `llama-orch config lint`
  - Acceptance: Validates all instances, reports issues
- [ ] Pretty-print validation errors (rich)
  - Acceptance: Colored, structured output

### 1.5 Tests
- [ ] Unit tests for all Pydantic schemas
- [ ] Test invalid configs raise ValidationError
- [ ] Test port collision detection

---

## Phase 2: Process Engine
**Effort:** 8-10 hours | **Dependencies:** Phase 1

### 2.1 Command Builder
- [ ] Build llama-server command from config
  - Args: --host, --port, --model, --ctx-size, --batch-size, etc.
  - Acceptance: Matches existing start-server.ps1 logic
- [ ] Add --alias flag (= instance name)
  - Acceptance: Alias appears in API responses
- [ ] Handle extra args from config
  - Acceptance: Appended correctly

### 2.2 Environment Setup
- [ ] Set GGML_VULKAN_DEVICE from config.gpu.device_id
  - Acceptance: Vulkan uses correct GPU
- [ ] Merge custom env vars from config.env
  - Acceptance: All vars set

### 2.3 Process Management
- [ ] Implement `start_instance(name: str)`
  - Uses subprocess.Popen
  - Redirects stdout/stderr to log files
  - Acceptance: Process starts, PID captured
- [ ] Implement `stop_instance(name: str)`
  - Terminates process + children (Windows tree kill)
  - Acceptance: All child processes stopped
- [ ] Implement `restart_instance(name: str)`
  - stop + start sequence
  - Acceptance: Clean restart

### 2.4 State Persistence
- [ ] Create SQLite state schema
  - Table: instances (name, pid, start_time, status, health, etc.)
  - Acceptance: Schema created on first run
- [ ] Implement `save_state(instance_state)`
  - Acceptance: Persists to SQLite
- [ ] Implement `load_state(name) -> InstanceState`
  - Acceptance: Reads from SQLite
- [ ] Handle stale PIDs (process died externally)
  - Acceptance: Detects and cleans up

### 2.5 CLI Commands
- [ ] Implement `llama-orch up <name>`
  - Acceptance: Starts instance, shows status
- [ ] Implement `llama-orch down <name>`
  - Acceptance: Stops instance, shows status
- [ ] Implement `llama-orch restart <name>`
  - Acceptance: Restarts instance

### 2.6 Tests
- [ ] Mock subprocess for unit tests
- [ ] Test state persistence roundtrip
- [ ] Test Windows process tree termination

---

## Phase 3: Health Monitoring
**Effort:** 6-8 hours | **Dependencies:** Phase 2

### 3.1 Health Check Implementation
- [ ] Implement HTTP GET /health check
  - Uses httpx with timeout
  - Acceptance: Returns health status
- [ ] Parse health response (status: ok|loading|error)
  - Acceptance: Correctly interprets all states
- [ ] Fallback to /v1/health if /health fails
  - Acceptance: Works with older llama.cpp versions
- [ ] Handle connection errors gracefully
  - Acceptance: Returns "unreachable" state

### 3.2 Health State Machine
- [ ] Define states: UNKNOWN, LOADING, HEALTHY, UNHEALTHY, ERROR
- [ ] Implement state transitions
  - Acceptance: Correct transition logic
- [ ] Track consecutive failures
  - Acceptance: Counter increments correctly
- [ ] Reset counter on success
  - Acceptance: Counter resets

### 3.3 Health Polling
- [ ] Implement polling loop
  - Respects config.healthcheck.interval
  - Acceptance: Polls at correct interval
- [ ] Update state on each check
  - Acceptance: SQLite updated
- [ ] Handle start_period (grace period)
  - Acceptance: No false alarms during startup

### 3.4 Auto-Restart
- [ ] Implement restart trigger logic
  - Trigger: N consecutive failures (retries)
  - Acceptance: Restarts after threshold
- [ ] Implement exponential backoff
  - Acceptance: Delays increase correctly
- [ ] Respect max_retries limit
  - Acceptance: Stops trying after limit
- [ ] Log restart attempts
  - Acceptance: Clear log entries

### 3.5 CLI Commands
- [ ] Implement `llama-orch health <name>`
  - Shows current health status
  - Acceptance: Clear status output
- [ ] Implement `llama-orch health --all`
  - Shows all instances
  - Acceptance: Table format

### 3.6 Tests
- [ ] Mock HTTP responses for health states
- [ ] Test state machine transitions
- [ ] Test backoff algorithm

---

## Phase 4: CLI + Dashboard
**Effort:** 8-10 hours | **Dependencies:** Phase 3

### 4.1 List Command
- [ ] Implement `llama-orch ps`
  - Lists all instances with status
  - Columns: Name, PID, Port, Backend, Health, Uptime
  - Acceptance: Rich table output
- [ ] Show running/stopped/loading states
  - Acceptance: Color-coded status
- [ ] Handle no instances case
  - Acceptance: Friendly message

### 4.2 Logs Command
- [ ] Implement `llama-orch logs <name>`
  - Shows stdout log
  - Acceptance: Outputs log content
- [ ] Add `--tail N` option
  - Acceptance: Shows last N lines
- [ ] Add `--follow` option
  - Acceptance: Streams new lines
- [ ] Add `--stderr` option
  - Acceptance: Shows stderr log

### 4.3 Describe Command
- [ ] Implement `llama-orch describe <name>`
  - Shows full config + runtime info
  - Acceptance: JSON or formatted output
- [ ] Include health history
  - Acceptance: Shows recent checks
- [ ] Include restart count
  - Acceptance: Shows restart history

### 4.4 TUI Dashboard
- [ ] Create live table with rich.live
  - Acceptance: Updates every 1s
- [ ] Define columns: Name, PID, Port, Backend, Device, Model, Health, Uptime
  - Acceptance: All columns populated
- [ ] Color-code health status
  - Green=OK, Yellow=Loading, Red=Error
  - Acceptance: Visual distinction
- [ ] Add keyboard shortcuts
  - q=quit, r=refresh, h=help
  - Acceptance: Responsive to input
- [ ] Implement `llama-orch dashboard`
  - Acceptance: TUI launches

### 4.5 Tests
- [ ] Test table rendering
- [ ] Test log tailing

---

## Phase 5: Daemon + Autostart
**Effort:** 6-8 hours | **Dependencies:** Phase 4

### 5.1 Daemon Mode
- [ ] Implement `llama-orch daemon start`
  - Runs monitoring loop in background
  - Acceptance: Process detaches
- [ ] Implement `llama-orch daemon stop`
  - Sends signal to daemon
  - Acceptance: Daemon exits cleanly
- [ ] Implement `llama-orch daemon status`
  - Shows if daemon is running
  - Acceptance: Clear status
- [ ] Create PID file (state/daemon.pid)
  - Acceptance: Lock prevents duplicates

### 5.2 Daemon Loop
- [ ] Implement async monitoring loop
  - Acceptance: Checks all instances
- [ ] Trigger auto-restarts per policy
  - Acceptance: Restarts when needed
- [ ] Log daemon activity
  - Acceptance: Clear log entries

### 5.3 Startup Configuration
- [ ] Define `autostart.json` (which instances to start)
  - Acceptance: Configurable list
- [ ] Implement `llama-orch daemon autostart`
  - Starts configured instances
  - Acceptance: All instances start

### 5.4 Windows Integration
- [ ] Create NSSM wrapper script
  - Acceptance: Service installable
- [ ] Create Task Scheduler XML
  - Acceptance: Imports correctly
- [ ] Document manual service setup
  - Acceptance: Clear instructions
- [ ] Implement `llama-orch install-service`
  - Acceptance: Registers service

### 5.5 Tests
- [ ] Test daemon start/stop
- [ ] Test autostart configuration

---

## Phase 6: Extensions (Future)
**Effort:** 10+ hours | **Dependencies:** All phases

### 6.1 GPU Detection
- [ ] Parse `llama-server --list-devices` output
- [ ] Cache device list in state
- [ ] Auto-suggest device_id

### 6.2 Config Templates
- [ ] Create CPU profile template
- [ ] Create Vulkan profile template
- [ ] Implement `llama-orch init --profile <name>`

### 6.3 REST API
- [ ] Create FastAPI app
- [ ] Endpoints: /instances, /instances/{name}/start, etc.
- [ ] OpenAPI documentation

### 6.4 Web GUI
- [ ] Design simple dashboard
- [ ] React/Vue frontend
- [ ] Connect to REST API

---

## Verification Checklist

### Before Merge
- [ ] All unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing on Windows completed
- [ ] Documentation updated
- [ ] No security issues (secrets, permissions)

### After Deployment
- [ ] Daemon starts on system boot
- [ ] Health checks work correctly
- [ ] Auto-restart policy functions
- [ ] Logs rotate properly
- [ ] Multi-instance scenario tested

---

## Notes

- Prioritize Phases 0-4 for MVP
- Phase 5 (daemon) is important for production use
- Phase 6 is optional/future work
- Test on Windows with AMD Vulkan (RX 6800 setup)
- Keep existing PowerShell scripts as fallback

---

**Last Updated:** 2024-12-27
