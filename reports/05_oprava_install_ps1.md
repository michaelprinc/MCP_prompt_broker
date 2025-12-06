# Oprava instalačního skriptu install.ps1

**Soubor:** `install.ps1`  
**Priorita:** Střední  
**Komplexita:** Střední

---

## Popis problému

Aktuální instalační skript má několik nedostatků:

1. **Žádná validace instalace** - nekontroluje, zda instalace proběhla úspěšně
2. **Žádné testování serveru** - neověřuje, že server lze spustit
3. **Slabé error handling** - chyby pip install nejsou správně zachyceny
4. **Neaktualizuje existující instalaci** - může ponechat starou verzi
5. **Chybí dev závislosti** - neinstaluje pytest pro testování
6. **Absolutní cesty v konfiguraci** - nepoužívá správný escape

---

## Aktuální problematický kód

```powershell
function Install-Dependencies {
    param([string]$VenvPython)
    Write-Info "Installing package into virtual environment"
    & $VenvPython -m pip install --upgrade pip
    & $VenvPython -m pip install .
}
```

**Problémy:**
- Neověřuje exit code
- Neloguje výstup při chybě
- Neinstaluje dev závislosti

---

## Opravený install.ps1

```powershell
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
        
        # Parse version
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
    
    # Test import
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
    
    # Normalize path for JSON (use forward slashes)
    $normalizedPython = $VenvPython -replace '\\', '/'
    
    $config = @{ mcpServers = @{} }
    
    if (Test-Path $ConfigPath) {
        try {
            $existingContent = Get-Content -Raw -Path $ConfigPath -ErrorAction Stop
            if ($existingContent -and $existingContent.Trim()) {
                $existingJson = $existingContent | ConvertFrom-Json -ErrorAction Stop
                if ($existingJson.mcpServers) {
                    # Convert PSCustomObject to Hashtable
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

    # Add or update mcp-prompt-broker entry
    $config.mcpServers["mcp-prompt-broker"] = @{
        command = $normalizedPython
        args    = @("-m", "mcp_prompt_broker")
    }

    # Write config with proper formatting
    $jsonContent = $config | ConvertTo-Json -Depth 10
    Set-Content -Path $ConfigPath -Value $jsonContent -Encoding UTF8
    
    Write-Success "MCP configuration updated at $ConfigPath"
    return $true
}

function Show-Summary {
    param(
        [bool]$InstallSuccess,
        [bool]$TestsSuccess,
        [bool]$ConfigSuccess,
        [string]$ConfigPath
    )
    
    Write-Host ""
    Write-Host "=" * 60 -ForegroundColor Cyan
    Write-Host "Installation Summary" -ForegroundColor Cyan
    Write-Host "=" * 60 -ForegroundColor Cyan
    
    if ($InstallSuccess) {
        Write-Success "✓ Package installation: SUCCESS"
    }
    else {
        Write-Error-Custom "✗ Package installation: FAILED"
    }
    
    if ($TestsSuccess) {
        Write-Success "✓ Tests: PASSED"
    }
    else {
        Write-Warning-Custom "⚠ Tests: SKIPPED or FAILED"
    }
    
    if ($ConfigSuccess) {
        Write-Success "✓ MCP Configuration: SUCCESS"
        Write-Info "  Config path: $ConfigPath"
    }
    else {
        Write-Error-Custom "✗ MCP Configuration: FAILED"
    }
    
    Write-Host "=" * 60 -ForegroundColor Cyan
    
    if ($InstallSuccess -and $ConfigSuccess) {
        Write-Host ""
        Write-Success "Installation complete!"
        Write-Info "Restart VS Code to activate the MCP server."
        Write-Host ""
        Write-Info "To test the server manually:"
        Write-Host "  $VenvPath\Scripts\python.exe -m mcp_prompt_broker" -ForegroundColor White
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
    # Linux/Mac fallback
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

# Step 6: Update MCP configuration
$configPath = Get-McpConfigPath
$configSuccess = $false
if ($installSuccess) {
    $configSuccess = Update-McpConfig -ConfigPath $configPath -VenvPython $venvPython
}

# Step 7: Show summary
$exitCode = Show-Summary `
    -InstallSuccess $installSuccess `
    -TestsSuccess $testsSuccess `
    -ConfigSuccess $configSuccess `
    -ConfigPath $configPath

exit $exitCode
```

---

## Klíčová vylepšení

### 1. Validace Python verze

```powershell
function Test-PythonVersion {
    # Kontroluje, že Python je >= 3.10
}
```

### 2. Lepší error handling

```powershell
if ($LASTEXITCODE -ne 0) {
    Write-Error-Custom "Failed to install package"
    return $false
}
```

### 3. Validace instalace

```powershell
function Test-Installation {
    # Testuje import balíčku po instalaci
    $importTest = & $VenvPython -c "from mcp_prompt_broker import run; print('OK')"
}
```

### 4. Automatické testy

```powershell
function Run-Tests {
    # Spouští pytest a reportuje výsledky
}
```

### 5. Přehledný výstup

```
============================================================
Installation Summary
============================================================
✓ Package installation: SUCCESS
✓ Tests: PASSED
✓ MCP Configuration: SUCCESS
  Config path: C:\Users\...\mcpServers.json
============================================================
```

### 6. Podpora přepínačů

```powershell
./install.ps1 -SkipTests  # Přeskočí testy
./install.ps1 -PythonPath "python3.11"  # Použije jiný Python
```

---

## Použití

```powershell
# Standardní instalace
./install.ps1

# S vlastním Python interpreterem
./install.ps1 -PythonPath "C:\Python312\python.exe"

# Přeskočit testy
./install.ps1 -SkipTests

# Vlastní cesta k venv
./install.ps1 -VenvPath ".venv-dev"
```

---

## Očekávaný výstup

```
MCP Prompt Broker - Installation Script
========================================

[mcp-prompt-broker] Checking Python version...
[mcp-prompt-broker] Python version OK: Python 3.12.8
[mcp-prompt-broker] Virtual environment already exists at .venv
[mcp-prompt-broker] Using Python: .venv\Scripts\python.exe
[mcp-prompt-broker] Upgrading pip...
[mcp-prompt-broker] Uninstalling old version (if exists)...
[mcp-prompt-broker] Installing package with dev dependencies...
[mcp-prompt-broker] Package installed successfully
[mcp-prompt-broker] Validating installation...
[mcp-prompt-broker] Import test passed
[mcp-prompt-broker] Running tests...
[mcp-prompt-broker] All tests passed
[mcp-prompt-broker] Updating MCP configuration...
[mcp-prompt-broker] MCP configuration updated at C:\Users\...\mcpServers.json

============================================================
Installation Summary
============================================================
[mcp-prompt-broker] ✓ Package installation: SUCCESS
[mcp-prompt-broker] ✓ Tests: PASSED
[mcp-prompt-broker] ✓ MCP Configuration: SUCCESS
[mcp-prompt-broker]   Config path: C:\Users\...\mcpServers.json
============================================================

[mcp-prompt-broker] Installation complete!
[mcp-prompt-broker] Restart VS Code to activate the MCP server.

[mcp-prompt-broker] To test the server manually:
  .venv\Scripts\python.exe -m mcp_prompt_broker
```

---

## Troubleshooting

### Chyba: Python not found

```powershell
# Zkuste specifikovat cestu k Pythonu
./install.ps1 -PythonPath "C:\Python312\python.exe"
```

### Chyba: Tests failed

```powershell
# Přeskočte testy a opravte je později
./install.ps1 -SkipTests
```

### Chyba: Permission denied

```powershell
# Spusťte PowerShell jako administrator
# Nebo změňte execution policy
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## Další kroky

Po aplikaci všech oprav:

1. ✅ Upravit `pyproject.toml` (viz `04_oprava_pyproject.md`)
2. ✅ Opravit importy (viz `03_oprava_importu.md`)
3. ✅ Opravit `server.py` (viz `02_oprava_mcp_server.md`)
4. ✅ Nahradit `install.ps1` touto verzí
5. ✅ Spustit `./install.ps1`
6. ✅ Ověřit funkčnost serveru
