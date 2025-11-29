<#!
.SYNOPSIS
Installs dependencies and registers the MCP Prompt Broker with GitHub Copilot Chat.

.DESCRIPTION
Creates a virtual environment, installs the local package, and updates the
Copilot Chat MCP configuration in VS Code to launch the server via the virtual
environment's Python interpreter.
#>

param(
    [string]$PythonPath = "python",
    [string]$VenvPath = ".venv"
)

$ErrorActionPreference = "Stop"

function Write-Info {
    param([string]$Message)
    Write-Host "[mcp-prompt-broker] $Message"
}

function Ensure-Venv {
    param([string]$Interpreter, [string]$Path)
    if (-Not (Test-Path $Path)) {
        Write-Info "Creating virtual environment at $Path"
        & $Interpreter -m venv $Path
    }
}

function Install-Dependencies {
    param([string]$VenvPython)
    Write-Info "Installing package into virtual environment"
    & $VenvPython -m pip install --upgrade pip
    & $VenvPython -m pip install .
}

function Get-McpConfigPath {
    $storageDir = Join-Path $env:APPDATA "Code\User\globalStorage\github.copilot-chat"
    if (-Not (Test-Path $storageDir)) {
        New-Item -ItemType Directory -Path $storageDir | Out-Null
    }
    return Join-Path $storageDir "mcpServers.json"
}

function Update-McpConfig {
    param([string]$ConfigPath, [string]$VenvPython)

    $config = @{ mcpServers = @{} }
    if (Test-Path $ConfigPath) {
        try {
            $existingJson = Get-Content -Raw -Path $ConfigPath | ConvertFrom-Json -ErrorAction Stop
            if ($existingJson.mcpServers) {
                $config.mcpServers = $existingJson.mcpServers
            }
        } catch {
            Write-Info "Existing configuration is invalid JSON; replacing it."
        }
    }

    $config.mcpServers."mcp-prompt-broker" = @{
        command = "${VenvPython}"
        args    = @("-m", "mcp_prompt_broker")
    }

    $config | ConvertTo-Json -Depth 5 | Set-Content -Path $ConfigPath -Encoding UTF8
    Write-Info "Updated MCP configuration at $ConfigPath"
}

Write-Info "Using Python interpreter: $PythonPath"
Ensure-Venv -Interpreter $PythonPath -Path $VenvPath
$venvPython = Join-Path $VenvPath "Scripts/python.exe"
if (-Not (Test-Path $venvPython)) {
    $venvPython = Join-Path $VenvPath "bin/python"
}

Install-Dependencies -VenvPython $venvPython
$configPath = Get-McpConfigPath
Update-McpConfig -ConfigPath $configPath -VenvPython $venvPython

Write-Info "Installation complete. Restart VS Code to pick up the MCP server."
