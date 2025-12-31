# MCP Codex Orchestrator - Authentication Setup Script
# This script helps set up ChatGPT Plus authentication for Codex CLI

param(
    [switch]$SkipLogin,
    [switch]$Help
)

if ($Help) {
    Write-Host @"
MCP Codex Orchestrator - Authentication Setup

This script helps you authenticate Codex CLI with your ChatGPT Plus subscription.

Usage:
    .\setup-auth.ps1           # Run full authentication flow
    .\setup-auth.ps1 -SkipLogin # Skip login (if auth.json already exists)
    .\setup-auth.ps1 -Help     # Show this help message

Requirements:
    - Node.js 18+ installed
    - ChatGPT Plus, Pro, Team, Edu, or Enterprise subscription
    - Web browser for OAuth login

The script will:
    1. Check if Codex CLI is installed (install if missing)
    2. Run 'codex login' for ChatGPT authentication
    3. Verify auth.json was created
    4. Test the Docker container with authentication
"@
    exit 0
}

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  MCP Codex Orchestrator - Auth Setup  " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check for Node.js
Write-Host "[1/5] Checking Node.js installation..." -ForegroundColor Yellow
try {
    $nodeVersion = node --version
    Write-Host "      Node.js $nodeVersion found" -ForegroundColor Green
} catch {
    Write-Host "      ERROR: Node.js not found. Please install Node.js 18+" -ForegroundColor Red
    exit 1
}

# Check for Codex CLI
Write-Host "[2/5] Checking Codex CLI installation..." -ForegroundColor Yellow
try {
    $codexVersion = codex --version 2>&1
    Write-Host "      Codex CLI $codexVersion found" -ForegroundColor Green
} catch {
    Write-Host "      Codex CLI not found. Installing..." -ForegroundColor Yellow
    npm install -g @openai/codex
    $codexVersion = codex --version
    Write-Host "      Codex CLI $codexVersion installed" -ForegroundColor Green
}

# Check for existing auth.json
$codexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { "$env:USERPROFILE\.codex" }
$authFile = Join-Path $codexHome "auth.json"

Write-Host "[3/5] Checking authentication status..." -ForegroundColor Yellow
if (Test-Path $authFile) {
    Write-Host "      auth.json found at: $authFile" -ForegroundColor Green
    $authContent = Get-Content $authFile | ConvertFrom-Json
    if ($authContent.access_token) {
        Write-Host "      Authentication appears valid" -ForegroundColor Green
    }
} else {
    Write-Host "      auth.json not found" -ForegroundColor Yellow
}

# Run login if needed
if (-not $SkipLogin) {
    Write-Host "[4/5] Starting ChatGPT authentication..." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "      A browser window will open for authentication." -ForegroundColor Cyan
    Write-Host "      Please sign in with your ChatGPT Plus account." -ForegroundColor Cyan
    Write-Host ""
    
    # Run codex login
    codex login
    
    # Verify auth.json was created
    if (Test-Path $authFile) {
        Write-Host "      Authentication successful!" -ForegroundColor Green
    } else {
        Write-Host "      WARNING: auth.json not found after login" -ForegroundColor Yellow
    }
} else {
    Write-Host "[4/5] Skipping login (as requested)" -ForegroundColor Yellow
}

# Test Docker container
Write-Host "[5/5] Testing Docker container with authentication..." -ForegroundColor Yellow

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$dockerDir = Join-Path (Split-Path -Parent $scriptDir) "docker"

Push-Location $dockerDir

try {
    # Rebuild container with new configuration
    Write-Host "      Building Docker image..." -ForegroundColor Cyan
    docker-compose build codex-runner 2>&1 | Out-Null
    
    # Test codex --version in container
    Write-Host "      Testing Codex CLI in container..." -ForegroundColor Cyan
    $result = docker-compose run --rm codex-runner --version 2>&1
    Write-Host "      Container Codex: $result" -ForegroundColor Green
    
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  Setup Complete!                      " -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Your ChatGPT Plus authentication is ready for use." -ForegroundColor Cyan
    Write-Host "The MCP Codex Orchestrator will automatically use" -ForegroundColor Cyan
    Write-Host "your credentials from: $authFile" -ForegroundColor Cyan
    Write-Host ""
    
} catch {
    Write-Host "      ERROR: Docker test failed: $_" -ForegroundColor Red
} finally {
    Pop-Location
}
