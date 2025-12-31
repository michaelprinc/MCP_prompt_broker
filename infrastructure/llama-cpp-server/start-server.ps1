<#
.SYNOPSIS
    Spuštění llama.cpp serveru s AMD GPU akcelerací (Vulkan backend)
    
.DESCRIPTION
    Tento skript stáhne (pokud neexistuje) a spustí llama.cpp server
    s podporou Vulkan akcelerace pro AMD RDNA 2+ grafické karty.
    
.PARAMETER ConfigFile
    Cesta ke konfiguračnímu souboru (výchozí: config.json)
    
.PARAMETER ModelPath
    Přímá cesta k modelu (přepíše hodnotu z konfigurace)
    
.PARAMETER Port
    Port pro server (přepíše hodnotu z konfigurace)
    
.PARAMETER Download
    Vynutí stažení nové verze llama.cpp
    
.EXAMPLE
    .\start-server.ps1
    
.EXAMPLE
    .\start-server.ps1 -ModelPath "..\models\my-model.gguf" -Port 8080
    
.NOTES
    Pro AMD RDNA 2 (gfx1030) na Windows je Vulkan backend doporučený.
    ROCm/HIP je teoreticky rychlejší (~30-50%), ale vyžaduje složitější konfiguraci.
#>

[CmdletBinding()]
param(
    [Parameter()]
    [string]$ConfigFile = "config.json",
    
    [Parameter()]
    [string]$ModelPath,
    
    [Parameter()]
    [int]$Port,
    
    [Parameter()]
    [int]$GpuLayers = -1,
    
    [Parameter()]
    [switch]$Download,
    
    [Parameter()]
    [switch]$ShowVersion
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Verze llama.cpp k stažení (aktualizujte podle potřeby)
$LLAMA_CPP_VERSION = "b7548"

# URL pro stažení - Vulkan build pro Windows
$DOWNLOAD_URL = "https://github.com/ggml-org/llama.cpp/releases/download/$LLAMA_CPP_VERSION/llama-$LLAMA_CPP_VERSION-bin-win-vulkan-x64.zip"

$BIN_DIR = Join-Path $ScriptDir "bin"
$LLAMA_SERVER_EXE = Join-Path $BIN_DIR "llama-server.exe"

function Write-Header {
    param([string]$Text)
    Write-Host ""
    Write-Host ("=" * 70) -ForegroundColor Cyan
    Write-Host " $Text" -ForegroundColor Cyan
    Write-Host ("=" * 70) -ForegroundColor Cyan
}

function Write-Step {
    param([string]$Text)
    Write-Host "[*] $Text" -ForegroundColor Yellow
}

function Write-Success {
    param([string]$Text)
    Write-Host "[OK] $Text" -ForegroundColor Green
}

function Write-Error-Custom {
    param([string]$Text)
    Write-Host "[ERROR] $Text" -ForegroundColor Red
}

function Get-LlamaConfig {
    param([string]$ConfigPath)
    
    $fullPath = if ([System.IO.Path]::IsPathRooted($ConfigPath)) {
        $ConfigPath
    } else {
        Join-Path $ScriptDir $ConfigPath
    }
    
    if (-not (Test-Path $fullPath)) {
        Write-Error-Custom "Konfigurační soubor nenalezen: $fullPath"
        exit 1
    }
    
    try {
        $config = Get-Content $fullPath -Raw | ConvertFrom-Json
        Write-Success "Konfigurace načtena z: $fullPath"
        return $config
    } catch {
        Write-Error-Custom "Chyba při čtení konfigurace: $_"
        exit 1
    }
}

function Install-LlamaCpp {
    Write-Header "Instalace llama.cpp s Vulkan backendem"
    
    $zipPath = Join-Path $ScriptDir "llama-cpp.zip"
    
    Write-Step "Stahuji llama.cpp verze $LLAMA_CPP_VERSION..."
    Write-Host "    URL: $DOWNLOAD_URL" -ForegroundColor Gray
    
    try {
        Invoke-WebRequest -Uri $DOWNLOAD_URL -OutFile $zipPath -UseBasicParsing
        Write-Success "Staženo úspěšně"
        
        Write-Step "Rozbaluji do: $BIN_DIR"
        
        if (Test-Path $BIN_DIR) {
            Remove-Item -Path $BIN_DIR -Recurse -Force
        }
        
        Expand-Archive -Path $zipPath -DestinationPath $BIN_DIR -Force
        
        $nestedDir = Get-ChildItem -Path $BIN_DIR -Directory | Select-Object -First 1
        if ($nestedDir -and (Test-Path (Join-Path $nestedDir.FullName "llama-server.exe"))) {
            Get-ChildItem -Path $nestedDir.FullName | Move-Item -Destination $BIN_DIR -Force
            Remove-Item -Path $nestedDir.FullName -Force
        }
        
        Remove-Item -Path $zipPath -Force
        
        if (Test-Path $LLAMA_SERVER_EXE) {
            Write-Success "llama.cpp nainstalováno úspěšně"
        } else {
            Write-Error-Custom "llama-server.exe nenalezen po instalaci"
            exit 1
        }
        
    } catch {
        Write-Error-Custom "Chyba při instalaci: $_"
        if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
        exit 1
    }
}

function Test-VulkanSupport {
    Write-Step "Kontroluji Vulkan podporu..."
    
    try {
        $adapters = Get-WmiObject Win32_VideoController | Where-Object { $_.Name -match "AMD|Radeon" }
        if ($adapters) {
            foreach ($adapter in $adapters) {
                Write-Host "    Nalezena AMD GPU: $($adapter.Name)" -ForegroundColor Green
            }
        } else {
            Write-Host "    Varování: AMD GPU nedetekována" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "    Nelze detekovat GPU (pokračuji)" -ForegroundColor Yellow
    }
}

function Start-LlamaServer {
    param(
        [object]$Config,
        [string]$OverrideModel,
        [int]$OverridePort,
        [int]$OverrideGpuLayers
    )
    
    Write-Header "Spouštím llama.cpp server"
    
    $modelPath = if ($OverrideModel) { $OverrideModel } else { $Config.model.path }
    
    if (-not [System.IO.Path]::IsPathRooted($modelPath)) {
        $modelPath = Join-Path $ScriptDir $modelPath
    }
    
    if (-not (Test-Path $modelPath)) {
        Write-Error-Custom "Model nenalezen: $modelPath"
        exit 1
    }
    
    $serverPort = if ($OverridePort -gt 0) { $OverridePort } else { $Config.server.port }
    $gpuLayers = if ($OverrideGpuLayers -ge 0) { $OverrideGpuLayers } else { $Config.model.gpu_layers }
    $contextSize = $Config.model.context_size
    $batchSize = $Config.model.batch_size
    $threads = $Config.model.threads
    
    Write-Step "Konfigurace serveru:"
    Write-Host "    Model: $modelPath" -ForegroundColor Gray
    Write-Host "    Port: $serverPort" -ForegroundColor Gray
    Write-Host "    GPU vrstvy: $gpuLayers" -ForegroundColor Gray
    Write-Host "    Kontext: $contextSize tokens" -ForegroundColor Gray
    Write-Host "    Batch size: $batchSize" -ForegroundColor Gray
    Write-Host "    Threads: $threads" -ForegroundColor Gray
    
    $args = @(
        "--model", $modelPath,
        "--host", $Config.server.host,
        "--port", $serverPort,
        "--ctx-size", $contextSize,
        "--batch-size", $batchSize,
        "--threads", $threads,
        "--n-gpu-layers", $gpuLayers,
        "--timeout", $Config.server.timeout,
        "-fit", "off"
    )
    
    if ($Config.api.api_key) {
        $args += "--api-key", $Config.api.api_key
    }
    
    if ($Config.api.parallel) {
        $args += "--parallel", $Config.api.parallel
    }
    
    Write-Step "Spouštím server..."
    Write-Host ""
    Write-Host ("=" * 70) -ForegroundColor Green
    Write-Host " Server poběží na: http://$($Config.server.host):$serverPort" -ForegroundColor Green
    Write-Host " OpenAI-compatible API: http://$($Config.server.host):$serverPort/v1" -ForegroundColor Green
    Write-Host " Pro ukončení stiskněte Ctrl+C" -ForegroundColor Green
    Write-Host ("=" * 70) -ForegroundColor Green
    Write-Host ""
    
    & $LLAMA_SERVER_EXE @args
}

function Show-Version {
    if (Test-Path $LLAMA_SERVER_EXE) {
        Write-Host "llama.cpp server verze:"
        & $LLAMA_SERVER_EXE --version
    } else {
        Write-Host "llama.cpp server není nainstalován"
        Write-Host "Spusťte: .\start-server.ps1 -Download"
    }
}

Write-Header "llama.cpp Server Launcher"
Write-Host "Backend: Vulkan (optimální pro AMD RDNA 2+ na Windows)"
Write-Host "Verze: $LLAMA_CPP_VERSION"

if ($ShowVersion) {
    Show-Version
    exit 0
}

if ($Download -or -not (Test-Path $LLAMA_SERVER_EXE)) {
    Install-LlamaCpp
}

Test-VulkanSupport

$config = Get-LlamaConfig -ConfigPath $ConfigFile

Start-LlamaServer -Config $config -OverrideModel $ModelPath -OverridePort $Port -OverrideGpuLayers $GpuLayers
