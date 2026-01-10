## Gemini Runner Prerequisites

Gemini CLI runs inside its own per-run container. OAuth is handled on the host
and mounted into the container at runtime.

### Host OAuth bootstrap

1. Install Gemini CLI:
   ```powershell
   npm install -g @google/gemini-cli
   ```

2. Run the login flow:
   ```powershell
   gemini
   ```

3. Verify the cache directory exists:
   ```powershell
   Test-Path "$env:USERPROFILE\.gemini"
   ```

Or use the helper script:
```powershell
.\scripts\setup-gemini-auth.ps1
```

### Container mount

The runner mounts the OAuth cache read-write to allow token refresh:

- Host: `~/.gemini` (Windows: `%USERPROFILE%\.gemini`)
- Container: `/home/runner/.gemini`

### Docker image

Build the image:
```powershell
cd docker
docker-compose build gemini-runner
```

### Minimal headless run

```powershell
docker-compose run --rm gemini-runner -p "Summarize the repo" --output-format json
```

### Security modes and approval

Recommended flags when running via the orchestrator:

- `workspace_write`: `--approval-mode auto_edit --extensions none`
- `readonly`: mount workspace read-only, use `--approval-mode default`
- `full_access`: only if you fully isolate the container

### OAuth vs API key

Gemini CLI switches to API-key mode when `GEMINI_API_KEY` or `GOOGLE_API_KEY`
is present in the environment. The runner does **not** forward these variables
by default to keep OAuth behavior consistent.

### Org licenses

Some org licenses require a Google Cloud project. Set:

```
GOOGLE_CLOUD_PROJECT=your-project-id
```

### Limits and telemetry

- OAuth free tier limits can be around 60 req/min and 1000 req/day (may change).
- Gemini CLI exposes telemetry flags; pass them via `env_vars` if needed.
