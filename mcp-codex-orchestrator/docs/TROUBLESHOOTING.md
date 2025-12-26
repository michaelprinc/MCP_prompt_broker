# Troubleshooting Guide

## Common Issues and Solutions

### 1. `No module named mcp_codex_orchestrator`

**Symptom:**
```
K:\Data_science_projects\MCP_Prompt_Broker\.venv\Scripts\python.exe: No module named mcp_codex_orchestrator
Process exited with code 1
```

**Cause:**
The `mcp_codex_orchestrator` package is not installed in the virtual environment (`.venv`) that VS Code MCP is using.

**Solution:**
Install the package in the correct virtual environment:

```powershell
# Activate the virtual environment
& K:/Data_science_projects/MCP_Prompt_Broker/.venv/Scripts/Activate.ps1

# Install mcp-codex-orchestrator
pip install -e "K:/Data_science_projects/MCP_Prompt_Broker/mcp-codex-orchestrator[dev]"

# Verify installation
python -m mcp_codex_orchestrator --version
```

Then restart the MCP server in VS Code:
- Press `Ctrl+Shift+P`
- Run: "MCP: Restart All Servers"

---

### 2. Docker Build Error: `UID 1000 is not unique`

**Symptom:**
```
ERROR [4/6] RUN useradd -m -s /bin/bash -u 1000 codex
useradd: UID 1000 is not unique
```

**Cause:**
The base image `node:20-slim` already has a user with UID 1000 (`node`).

**Solution:**
Use the existing `node` user instead of creating a new one. This is already fixed in the current Dockerfile.

---

### 3. Read-only File System Error in Container

**Symptom:**
```
ERROR codex_core::codex: Failed to create session: Read-only file system (os error 30)
```

**Cause:**
The `.codex` directory is mounted as read-only, but Codex needs to write session data.

**Solution:**
Mount only `auth.json` as read-only, not the entire `.codex` directory:

```yaml
volumes:
  - ${CODEX_AUTH_PATH:-~/.codex}/auth.json:/home/node/.codex/auth.json:ro
```

This is already fixed in the current `docker-compose.yml`.

---

### 4. Git Repository Check Failed

**Symptom:**
```
Not inside a trusted directory and --skip-git-repo-check was not specified.
```

**Cause:**
Codex CLI requires a git repository for security when running in `--full-auto` mode.

**Solution:**
Initialize git in the workspace directory:

```powershell
cd mcp-codex-orchestrator/workspace
git init
git config user.email "test@test.com"
git config user.name "Test"
git add .
git commit -m "Initial commit"
```

---

### 5. ChatGPT Plus Authentication Not Working

**Symptom:**
Container cannot authenticate with OpenAI API.

**Cause:**
`auth.json` is missing or not properly mounted.

**Solution:**

1. **Authenticate locally:**
   ```powershell
   # If Codex CLI is not installed
   npm install -g @openai/codex
   
   # Run login
   codex login
   ```

2. **Verify `auth.json` exists:**
   ```powershell
   Test-Path "$env:USERPROFILE\.codex\auth.json"
   ```

3. **Check docker-compose.yml mount:**
   ```yaml
   volumes:
     - ${CODEX_AUTH_PATH:-~/.codex}/auth.json:/home/node/.codex/auth.json:ro
   ```

4. **Use the setup script:**
   ```powershell
   .\mcp-codex-orchestrator\scripts\setup-auth.ps1
   ```

---

## Getting Help

If you encounter an issue not covered here:

1. Check the [Implementation Checklist](IMPLEMENTATION_CHECKLIST.md) for known issues
2. Review the [Developer Guide](DEVELOPER_GUIDE.md) for detailed architecture information
3. Check MCP server logs in VS Code Output panel (select "MCP" from dropdown)
4. Enable debug logging:
   ```powershell
   $env:DEBUG="*"
   python -m mcp_codex_orchestrator
   ```

## Useful Commands

```powershell
# Check MCP server status
python -m mcp_codex_orchestrator --version

# Test Codex CLI in container
docker-compose run --rm codex-runner --version

# Test full workflow
docker-compose run --rm codex-runner exec --full-auto "Create hello.py"

# View container logs
docker logs codex-run-manual

# Rebuild Docker image
docker-compose build codex-runner

# Check Python environment
pip list | Select-String "mcp"
```
