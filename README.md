# MCP Prompt Broker

A Python-based Model Context Protocol (MCP) server that picks the most relevant
instruction profile for a user's prompt. The server exposes tools for listing
available profiles and selecting the best-fit guidance so Copilot Chat can
apply the right context automatically.

## Project layout

- `src/mcp_prompt_broker/` – MCP server implementation and tool wiring.
- `install.ps1` – PowerShell helper for installing dependencies and registering
  the server with GitHub Copilot Chat in VS Code.
- `pyproject.toml` – Python package configuration.
- `src/metadata/` – Rule-based prompt metadata extraction utilities.

## Running the server locally

```bash
python -m mcp_prompt_broker
```

Optionally provide a JSON file containing instruction profile objects
(`name`, `instructions`, `required`, `weights`) using `--instructions`.

## Installing and registering with Copilot Chat (Windows/PowerShell)

Run the helper script from the repository root:

```powershell
./install.ps1
```

The script will:

1. Create a virtual environment and install the package.
2. Register the MCP server with GitHub Copilot Chat by updating the VS Code
   `mcpServers.json` configuration.
3. Leave the configuration ready for use under
   `%APPDATA%\Code\User\globalStorage\github.copilot-chat`.

If you prefer manual setup, ensure `python -m pip install .` succeeds and then
add an entry for `mcp-prompt-broker` to your Copilot Chat MCP configuration that
runs `python -m mcp_prompt_broker`.
