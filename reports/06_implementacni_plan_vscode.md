# Implementační plán: Rozšíření install.ps1 o .vscode konfiguraci

**Datum:** 6. prosince 2025  
**Verze:** 1.0

---

## Cíl

Rozšířit instalační skript `install.ps1` o automatickou konfiguraci `.vscode/mcp.json` pro workspace, aby byl MCP server ihned připraven k použití po instalaci.

---

## Požadavky

1. **Vytvoření adresáře** - Vytvořit `.vscode` adresář pokud neexistuje
2. **Merge konfigurace** - Nepřepisovat existující nastavení, pouze přidat/aktualizovat MCP server
3. **Přenositelnost** - Použít `${workspaceFolder}` pro relativní cesty
4. **Cross-platform** - Podpora Windows i Linux/Mac (virtuální prostředí)

---

## Struktura mcp.json

```json
{
  "servers": {
    "mcp-prompt-broker": {
      "type": "stdio",
      "command": "${workspaceFolder}/.venv/Scripts/python.exe",
      "args": ["-m", "mcp_prompt_broker"],
      "env": {}
    }
  }
}
```

**Pro Linux/Mac:**
```json
{
  "servers": {
    "mcp-prompt-broker": {
      "type": "stdio",
      "command": "${workspaceFolder}/.venv/bin/python",
      "args": ["-m", "mcp_prompt_broker"],
      "env": {}
    }
  }
}
```

---

## Implementační kroky

### Krok 1: Přidat funkci Ensure-VscodeDir

```powershell
function Ensure-VscodeDir {
    param([string]$WorkspacePath)
    
    $vscodeDir = Join-Path $WorkspacePath ".vscode"
    if (-Not (Test-Path $vscodeDir)) {
        Write-Info "Creating .vscode directory"
        New-Item -ItemType Directory -Path $vscodeDir -Force | Out-Null
    }
    return $vscodeDir
}
```

### Krok 2: Přidat funkci Get-McpServerConfig

```powershell
function Get-McpServerConfig {
    param([string]$VenvPath)
    
    # Detekce OS pro správnou cestu k Python interpretu
    $isWindows = $env:OS -eq "Windows_NT"
    
    if ($isWindows) {
        $pythonRelPath = ".venv/Scripts/python.exe"
    } else {
        $pythonRelPath = ".venv/bin/python"
    }
    
    return @{
        type = "stdio"
        command = "`${workspaceFolder}/$pythonRelPath"
        args = @("-m", "mcp_prompt_broker")
        env = @{}
    }
}
```

### Krok 3: Přidat funkci Update-WorkspaceMcpConfig

```powershell
function Update-WorkspaceMcpConfig {
    param(
        [string]$VscodeDir,
        [string]$VenvPath
    )
    
    $mcpConfigPath = Join-Path $VscodeDir "mcp.json"
    
    # Načíst existující konfiguraci nebo vytvořit novou
    $config = @{ servers = @{} }
    
    if (Test-Path $mcpConfigPath) {
        try {
            $existingContent = Get-Content -Raw -Path $mcpConfigPath
            if ($existingContent -and $existingContent.Trim()) {
                $existingJson = $existingContent | ConvertFrom-Json
                if ($existingJson.servers) {
                    # Převést na hashtable
                    $existingJson.servers.PSObject.Properties | ForEach-Object {
                        $config.servers[$_.Name] = $_.Value
                    }
                }
            }
        } catch {
            Write-Warning-Custom "Existing mcp.json is invalid; creating new one."
        }
    }
    
    # Přidat/aktualizovat mcp-prompt-broker
    $serverConfig = Get-McpServerConfig -VenvPath $VenvPath
    $config.servers["mcp-prompt-broker"] = $serverConfig
    
    # Zapsat konfiguraci
    $jsonContent = $config | ConvertTo-Json -Depth 10
    Set-Content -Path $mcpConfigPath -Value $jsonContent -Encoding UTF8
    
    Write-Success "Workspace MCP configuration updated at $mcpConfigPath"
    return $true
}
```

### Krok 4: Integrovat do hlavního skriptu

Přidat volání nových funkcí do sekce po instalaci:

```powershell
# Step 7: Update workspace .vscode configuration
$vscodeDir = Ensure-VscodeDir -WorkspacePath (Get-Location)
$workspaceConfigSuccess = Update-WorkspaceMcpConfig -VscodeDir $vscodeDir -VenvPath $VenvPath
```

### Krok 5: Aktualizovat Show-Summary

Přidat informaci o workspace konfiguraci do summary.

---

## Výstupní struktura

Po spuštění `install.ps1`:

```
projekt/
├── .venv/
├── .vscode/
│   └── mcp.json          # MCP server konfigurace
├── src/
├── install.ps1
└── pyproject.toml
```

---

## Testování

1. Smazat existující `.vscode` adresář
2. Spustit `./install.ps1`
3. Ověřit vytvoření `.vscode/mcp.json`
4. Ověřit správný obsah konfigurace
5. Spustit znovu - ověřit, že existující konfigurace není přepsána
6. Ověřit funkčnost v VS Code (MCP: List Servers)

---

## Rizika a mitigace

| Riziko | Mitigace |
|--------|----------|
| Přepsání existující konfigurace | Merge logika zachovává ostatní servery |
| Nesprávná cesta na jiném OS | Dynamická detekce OS |
| Nevalidní JSON v existujícím souboru | Try-catch s varováním |

---

## Další iterace

1. Přidat podporu pro `settings.json` s doporučeným nastavením
2. Přidat `launch.json` pro debugování MCP serveru
3. Přidat podporu pro `tasks.json` pro build tasky
