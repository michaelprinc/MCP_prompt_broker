<#
.SYNOPSIS
Installs dependencies and registers the MCP Prompt Broker with GitHub Copilot Chat.

.DESCRIPTION
Creates a virtual environment, installs the local package with development
dependencies, validates the installation, and updates the Copilot Chat MCP
configuration in VS Code to launch the server via the virtual environment's
Python interpreter.

.PARAMETER PythonPath
Path to the Python interpreter to use for creating the virtual environment.
Defaults to "python".

.PARAMETER VenvPath
Path where the virtual environment should be created.
Defaults to ".venv".

.PARAMETER SkipTests
Skip running tests after installation.

.EXAMPLE
./install.ps1
./install.ps1 -PythonPath "python3.11" -VenvPath ".venv311"
./install.ps1 -SkipTests
#>

param(
    [string]$PythonPath = "python",
    [string]$VenvPath = ".venv",
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
$script:HasErrors = $false

function Write-Info {
    param([string]$Message)
    Write-Host "[mcp-prompt-broker] " -ForegroundColor Cyan -NoNewline
    Write-Host $Message
}

function Write-Success {
    param([string]$Message)
    Write-Host "[mcp-prompt-broker] " -ForegroundColor Green -NoNewline
    Write-Host $Message -ForegroundColor Green
}

function Write-Error-Custom {
    param([string]$Message)
    Write-Host "[mcp-prompt-broker] ERROR: " -ForegroundColor Red -NoNewline
    Write-Host $Message -ForegroundColor Red
    $script:HasErrors = $true
}

function Write-Warning-Custom {
    param([string]$Message)
    Write-Host "[mcp-prompt-broker] WARNING: " -ForegroundColor Yellow -NoNewline
    Write-Host $Message -ForegroundColor Yellow
}

function Test-PythonVersion {
    param([string]$Interpreter)
    
    Write-Info "Checking Python version..."
    
    try {
        $version = & $Interpreter --version 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Error-Custom "Failed to get Python version"
            return $false
        }
        
        if ($version -match "Python (\d+)\.(\d+)\.(\d+)") {
            $major = [int]$Matches[1]
            $minor = [int]$Matches[2]
            
            if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 10)) {
                Write-Error-Custom "Python 3.10 or higher is required. Found: $version"
                return $false
            }
            
            Write-Success "Python version OK: $version"
            return $true
        }
        
        Write-Warning-Custom "Could not parse Python version: $version"
        return $true
    }
    catch {
        Write-Error-Custom "Python interpreter not found: $Interpreter"
        return $false
    }
}

function Ensure-Venv {
    param([string]$Interpreter, [string]$Path)
    
    if (-Not (Test-Path $Path)) {
        Write-Info "Creating virtual environment at $Path"
        & $Interpreter -m venv $Path
        
        if ($LASTEXITCODE -ne 0) {
            Write-Error-Custom "Failed to create virtual environment"
            return $false
        }
    }
    else {
        Write-Info "Virtual environment already exists at $Path"
    }
    
    return $true
}

function Install-Dependencies {
    param([string]$VenvPython)
    
    Write-Info "Upgrading pip..."
    & $VenvPython -m pip install --upgrade pip --quiet
    if ($LASTEXITCODE -ne 0) {
        Write-Error-Custom "Failed to upgrade pip"
        return $false
    }
    
    Write-Info "Uninstalling old version (if exists)..."
    & $VenvPython -m pip uninstall mcp-prompt-broker -y --quiet 2>$null
    
    Write-Info "Installing package with dev dependencies..."
    $output = & $VenvPython -m pip install -e ".[dev]" 2>&1
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error-Custom "Failed to install package"
        Write-Host $output -ForegroundColor Red
        return $false
    }
    
    Write-Success "Package installed successfully"
    return $true
}

function Test-Installation {
    param([string]$VenvPython)
    
    Write-Info "Validating installation..."
    
    $importTest = & $VenvPython -c "from mcp_prompt_broker import run; print('OK')" 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Error-Custom "Import test failed: $importTest"
        return $false
    }
    
    Write-Success "Import test passed"
    return $true
}

function Run-Tests {
    param([string]$VenvPython)
    
    Write-Info "Running tests..."
    
    $testOutput = & $VenvPython -m pytest tests/ -v --tb=short 2>&1
    $testExitCode = $LASTEXITCODE
    
    if ($testExitCode -ne 0) {
        Write-Warning-Custom "Some tests failed"
        Write-Host $testOutput
        return $false
    }
    
    Write-Success "All tests passed"
    return $true
}

function Get-McpConfigPath {
    $storageDir = Join-Path $env:APPDATA "Code\User\globalStorage\github.copilot-chat"
    if (-Not (Test-Path $storageDir)) {
        New-Item -ItemType Directory -Path $storageDir -Force | Out-Null
    }
    return Join-Path $storageDir "mcpServers.json"
}

function Update-McpConfig {
    param([string]$ConfigPath, [string]$VenvPython)

    Write-Info "Updating MCP configuration..."
    
    $normalizedPython = $VenvPython -replace '\\', '/'
    
    $config = @{ mcpServers = @{} }
    
    if (Test-Path $ConfigPath) {
        try {
            $existingContent = Get-Content -Raw -Path $ConfigPath -ErrorAction Stop
            if ($existingContent -and $existingContent.Trim()) {
                $existingJson = $existingContent | ConvertFrom-Json -ErrorAction Stop
                if ($existingJson.mcpServers) {
                    $existingJson.mcpServers.PSObject.Properties | ForEach-Object {
                        $config.mcpServers[$_.Name] = $_.Value
                    }
                }
            }
        }
        catch {
            Write-Warning-Custom "Existing configuration is invalid JSON; creating new one."
        }
    }

    $config.mcpServers["mcp-prompt-broker"] = @{
        command = $normalizedPython
        args    = @("-m", "mcp_prompt_broker")
    }

    $jsonContent = $config | ConvertTo-Json -Depth 10
    Set-Content -Path $ConfigPath -Value $jsonContent -Encoding UTF8
    
    Write-Success "MCP configuration updated at $ConfigPath"
    return $true
}

function Ensure-VscodeDir {
    param([string]$WorkspacePath)
    
    $vscodeDir = Join-Path $WorkspacePath ".vscode"
    if (-Not (Test-Path $vscodeDir)) {
        Write-Info "Creating .vscode directory..."
        New-Item -ItemType Directory -Path $vscodeDir -Force | Out-Null
    }
    return $vscodeDir
}

function Get-WorkspaceMcpServerConfig {
    # Detect OS for correct Python path in venv
    $isWindows = $env:OS -eq "Windows_NT"
    
    if ($isWindows) {
        $pythonRelPath = ".venv/Scripts/python.exe"
    }
    else {
        $pythonRelPath = ".venv/bin/python"
    }
    
    return @{
        type    = "stdio"
        command = "`${workspaceFolder}/$pythonRelPath"
        args    = @("-m", "mcp_prompt_broker")
        env     = @{}
    }
}

function Update-WorkspaceMcpConfig {
    param([string]$VscodeDir)
    
    $mcpConfigPath = Join-Path $VscodeDir "mcp.json"
    
    Write-Info "Updating workspace MCP configuration..."
    
    # Load existing config or create new one
    $config = @{ servers = @{} }
    
    if (Test-Path $mcpConfigPath) {
        try {
            $existingContent = Get-Content -Raw -Path $mcpConfigPath -ErrorAction Stop
            if ($existingContent -and $existingContent.Trim()) {
                $existingJson = $existingContent | ConvertFrom-Json -ErrorAction Stop
                if ($existingJson.servers) {
                    # Convert to hashtable, preserving other servers
                    $existingJson.servers.PSObject.Properties | ForEach-Object {
                        $config.servers[$_.Name] = $_.Value
                    }
                }
                # Preserve inputs if exists
                if ($existingJson.inputs) {
                    $config.inputs = $existingJson.inputs
                }
            }
        }
        catch {
            Write-Warning-Custom "Existing mcp.json is invalid JSON; creating new one."
        }
    }
    
    # Add/update mcp-prompt-broker server
    $serverConfig = Get-WorkspaceMcpServerConfig
    $config.servers["mcp-prompt-broker"] = $serverConfig
    
    # Write configuration
    $jsonContent = $config | ConvertTo-Json -Depth 10
    Set-Content -Path $mcpConfigPath -Value $jsonContent -Encoding UTF8
    
    Write-Success "Workspace MCP configuration updated at $mcpConfigPath"
    return $true
}

function Get-VsCodeSettingsPath {
    $settingsDir = Join-Path $env:APPDATA "Code\User"
    if (-Not (Test-Path $settingsDir)) {
        New-Item -ItemType Directory -Path $settingsDir -Force | Out-Null
    }
    return Join-Path $settingsDir "settings.json"
}

function Ensure-GithubAgentsDir {
    param([string]$WorkspacePath)
    
    $agentsDir = Join-Path $WorkspacePath ".github\agents"
    if (-Not (Test-Path $agentsDir)) {
        Write-Info "Creating .github\agents directory..."
        New-Item -ItemType Directory -Path $agentsDir -Force | Out-Null
    }
    return $agentsDir
}

function Copy-CompanionAgentFiles {
    param([string]$WorkspacePath, [string]$AgentsDir)
    
    Write-Info "Copying Companion agent files to .github\agents..."
    
    $sourceInstructions = Join-Path $WorkspacePath "companion-instructions.md"
    $sourceAgent = Join-Path $WorkspacePath "companion-agent.json"
    
    # Verify source files exist
    if (-Not (Test-Path $sourceInstructions)) {
        Write-Error-Custom "Source file not found: $sourceInstructions"
        return $false
    }
    
    if (-Not (Test-Path $sourceAgent)) {
        Write-Warning-Custom "Source file not found: $sourceAgent (optional)"
    }
    
    try {
        # Copy instructions file
        $destInstructions = Join-Path $AgentsDir "companion-instructions.md"
        Copy-Item -Path $sourceInstructions -Destination $destInstructions -Force
        Write-Success "Copied companion-instructions.md to .github\agents\"
        
        # Copy agent definition (optional, for reference)
        if (Test-Path $sourceAgent) {
            $destAgent = Join-Path $AgentsDir "companion-agent.json"
            Copy-Item -Path $sourceAgent -Destination $destAgent -Force
            Write-Success "Copied companion-agent.json to .github\agents\"
        }
        
        return $true
    }
    catch {
        Write-Error-Custom "Failed to copy agent files: $_"
        return $false
    }
}

function Install-CompanionAgent {
    param([string]$WorkspacePath)
    
    Write-Info "Installing Companion custom agent..."
    
    $settingsPath = Get-VsCodeSettingsPath
    
    # Create .github\agents directory and copy files
    $agentsDir = Ensure-GithubAgentsDir -WorkspacePath $WorkspacePath
    $copySuccess = Copy-CompanionAgentFiles -WorkspacePath $WorkspacePath -AgentsDir $agentsDir
    
    if (-not $copySuccess) {
        Write-Error-Custom "Failed to copy Companion agent files"
        return $false
    }
    
    # Use path relative to .github\agents for agent registration
    $instructionsPath = Join-Path $agentsDir "companion-instructions.md"
    
    # Verify instructions file exists in target location
    if (-Not (Test-Path $instructionsPath)) {
        Write-Error-Custom "Companion instructions file not found after copy: $instructionsPath"
        return $false
    }
    
    # Load or create settings.json
    $settings = @{}
    if (Test-Path $settingsPath) {
        try {
            $existingContent = Get-Content -Raw -Path $settingsPath -ErrorAction Stop
            if ($existingContent -and $existingContent.Trim()) {
                $settings = $existingContent | ConvertFrom-Json -AsHashtable -ErrorAction Stop
            }
        }
        catch {
            Write-Warning-Custom "Could not parse existing settings.json; will create new configuration."
            $settings = @{}
        }
    }
    
    # Initialize github.copilot.chat.codeGeneration.instructions if not exists
    if (-not $settings.ContainsKey("github.copilot.chat.codeGeneration.instructions")) {
        $settings["github.copilot.chat.codeGeneration.instructions"] = @()
    }
    
    # Convert to array if not already
    $instructions = $settings["github.copilot.chat.codeGeneration.instructions"]
    if ($instructions -isnot [Array]) {
        $instructions = @($instructions)
    }
    
    # Normalize path with forward slashes for JSON
    $normalizedPath = $instructionsPath -replace '\\', '/'
    
    # Create Companion agent definition
    $companionAgent = @{
        text = "file://$normalizedPath"
    }
    
    # Check if Companion agent already exists
    $existingIndex = -1
    for ($i = 0; $i -lt $instructions.Count; $i++) {
        if ($instructions[$i].text -like "*companion-instructions.md*") {
            $existingIndex = $i
            break
        }
    }
    
    if ($existingIndex -ge 0) {
        Write-Info "Updating existing Companion agent configuration..."
        $instructions[$existingIndex] = $companionAgent
    }
    else {
        Write-Info "Adding new Companion agent configuration..."
        $instructions += $companionAgent
    }
    
    $settings["github.copilot.chat.codeGeneration.instructions"] = $instructions
    
    # Write settings.json
    try {
        $jsonContent = $settings | ConvertTo-Json -Depth 10
        Set-Content -Path $settingsPath -Value $jsonContent -Encoding UTF8
        Write-Success "Companion agent registered in VS Code settings"
        Write-Info "  Settings path: $settingsPath"
        Write-Info "  Agent files: .github\agents\"
        return $true
    }
    catch {
        Write-Error-Custom "Failed to write settings.json: $_"
        return $false
    }
}

function Show-Summary {
    param(
        [bool]$InstallSuccess,
        [bool]$TestsSuccess,
        [bool]$ConfigSuccess,
        [bool]$WorkspaceConfigSuccess,
        [bool]$CompanionAgentSuccess,
        [string]$ConfigPath,
        [string]$WorkspaceConfigPath
    )
    
    Write-Host ""
    Write-Host ("=" * 60) -ForegroundColor Cyan
    Write-Host "Installation Summary" -ForegroundColor Cyan
    Write-Host ("=" * 60) -ForegroundColor Cyan
    
    if ($InstallSuccess) {
        Write-Success "Package installation: SUCCESS"
    }
    else {
        Write-Error-Custom "Package installation: FAILED"
    }
    
    if ($TestsSuccess) {
        Write-Success "Tests: PASSED"
    }
    else {
        Write-Warning-Custom "Tests: SKIPPED or FAILED"
    }
    
    if ($ConfigSuccess) {
        Write-Success "Global MCP Configuration: SUCCESS"
        Write-Info "  Config path: $ConfigPath"
    }
    else {
        Write-Error-Custom "Global MCP Configuration: FAILED"
    }
    
    if ($WorkspaceConfigSuccess) {
        Write-Success "Workspace MCP Configuration: SUCCESS"
        Write-Info "  Config path: $WorkspaceConfigPath"
    }
    else {
        Write-Error-Custom "Workspace MCP Configuration: FAILED"
    }
    
    if ($CompanionAgentSuccess) {
        Write-Success "Companion Custom Agent: SUCCESS"
        Write-Info "  Agent: @companion (available in GitHub Copilot Chat)"
        Write-Info "  Agent files: .github\agents\"
    }
    else {
        Write-Warning-Custom "Companion Custom Agent: SKIPPED or FAILED"
    }
    
    Write-Host ("=" * 60) -ForegroundColor Cyan
    
    if ($InstallSuccess -and $ConfigSuccess -and $WorkspaceConfigSuccess) {
        Write-Host ""
        Write-Success "Installation complete!"
        Write-Info "Restart VS Code to activate the MCP server and Companion agent."
        Write-Host ""
        Write-Info "To test the server manually:"
        Write-Host "  $VenvPath\Scripts\python.exe -m mcp_prompt_broker" -ForegroundColor White
        Write-Host ""
        Write-Info "To use Companion agent in GitHub Copilot Chat:"
        Write-Host "  Type: @companion <your question>" -ForegroundColor White
        return 0
    }
    else {
        Write-Host ""
        Write-Error-Custom "Installation completed with errors. Please review the output above."
        return 1
    }
}

# =============================================================================
# Main Script
# =============================================================================

Write-Host ""
Write-Host "MCP Prompt Broker - Installation Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check Python version
if (-not (Test-PythonVersion -Interpreter $PythonPath)) {
    exit 1
}

# Step 2: Create/verify virtual environment
if (-not (Ensure-Venv -Interpreter $PythonPath -Path $VenvPath)) {
    exit 1
}

# Get venv Python path
$venvPython = Join-Path $VenvPath "Scripts\python.exe"
if (-Not (Test-Path $venvPython)) {
    $venvPython = Join-Path $VenvPath "bin/python"
}

if (-Not (Test-Path $venvPython)) {
    Write-Error-Custom "Could not find Python in virtual environment"
    exit 1
}

Write-Info "Using Python: $venvPython"

# Step 3: Install dependencies
$installSuccess = Install-Dependencies -VenvPython $venvPython

# Step 4: Validate installation
if ($installSuccess) {
    $installSuccess = Test-Installation -VenvPython $venvPython
}

# Step 5: Run tests (optional)
$testsSuccess = $false
if ($installSuccess -and -not $SkipTests) {
    $testsSuccess = Run-Tests -VenvPython $venvPython
}
elseif ($SkipTests) {
    Write-Info "Skipping tests (--SkipTests flag)"
    $testsSuccess = $true
}

# Step 6: Update global MCP configuration
$configPath = Get-McpConfigPath
$configSuccess = $false
if ($installSuccess) {
    $configSuccess = Update-McpConfig -ConfigPath $configPath -VenvPython $venvPython
}

# Step 7: Update workspace .vscode/mcp.json configuration
$workspaceConfigPath = Join-Path (Get-Location) ".vscode\mcp.json"
$workspaceConfigSuccess = $false
if ($installSuccess) {
    $vscodeDir = Ensure-VscodeDir -WorkspacePath (Get-Location)
    $workspaceConfigSuccess = Update-WorkspaceMcpConfig -VscodeDir $vscodeDir
}

# Step 8: Install Companion custom agent
$companionAgentSuccess = $false
if ($installSuccess) {
    $companionAgentSuccess = Install-CompanionAgent -WorkspacePath (Get-Location)
}

# Step 9: Show summary
$exitCode = Show-Summary `
    -InstallSuccess $installSuccess `
    -TestsSuccess $testsSuccess `
    -ConfigSuccess $configSuccess `
    -WorkspaceConfigSuccess $workspaceConfigSuccess `
    -CompanionAgentSuccess $companionAgentSuccess `
    -ConfigPath $configPath `
    -WorkspaceConfigPath $workspaceConfigPath

exit $exitCode
