# MCP Codex Orchestrator - Gemini Authentication Setup Script
# This script helps set up Google OAuth for Gemini CLI

param(
    [switch]$SkipLogin,
    [switch]$Help
)

if ($Help) {
    Write-Host @"
MCP Codex Orchestrator - Gemini Auth Setup

This script helps you authenticate Gemini CLI using Google OAuth.

Usage:
    .\setup-gemini-auth.ps1           # Run full authentication flow
    .\setup-gemini-auth.ps1 -SkipLogin # Skip login (if already authenticated)
    .\setup-gemini-auth.ps1 -Help     # Show this help message

Requirements:
    - Node.js 20+ installed
    - Google account for OAuth login
    - Web browser for login flow

The script will:
    1. Check Node.js installation
    2. Install Gemini CLI if missing
    3. Run Gemini CLI for OAuth login
    4. Verify ~/.gemini was created
"@
    exit 0
}

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  MCP Orchestrator - Gemini Auth Setup " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[1/4] Checking Node.js installation..." -ForegroundColor Yellow
try {
    $nodeVersion = node --version
    Write-Host "      Node.js $nodeVersion found" -ForegroundColor Green
} catch {
    Write-Host "      ERROR: Node.js not found. Please install Node.js 20+" -ForegroundColor Red
    exit 1
}

Write-Host "[2/4] Checking Gemini CLI installation..." -ForegroundColor Yellow
try {
    $geminiVersion = gemini --version 2>&1
    Write-Host "      Gemini CLI $geminiVersion found" -ForegroundColor Green
} catch {
    Write-Host "      Gemini CLI not found. Installing..." -ForegroundColor Yellow
    npm install -g @google/gemini-cli
    $geminiVersion = gemini --version 2>&1
    Write-Host "      Gemini CLI $geminiVersion installed" -ForegroundColor Green
}

$geminiHome = "$env:USERPROFILE\.gemini"
$settingsFile = Join-Path $geminiHome "settings.json"

Write-Host "[3/4] Checking authentication status..." -ForegroundColor Yellow
if (Test-Path $settingsFile) {
    Write-Host "      settings.json found at: $settingsFile" -ForegroundColor Green
} elseif (Test-Path $geminiHome) {
    Write-Host "      .gemini directory found at: $geminiHome" -ForegroundColor Green
} else {
    Write-Host "      .gemini directory not found" -ForegroundColor Yellow
}

if (-not $SkipLogin) {
    Write-Host "[4/4] Starting Google OAuth login..." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "      A browser window will open for authentication." -ForegroundColor Cyan
    Write-Host "      Complete the login flow, then return here." -ForegroundColor Cyan
    Write-Host ""

    gemini

    if (Test-Path $settingsFile) {
        Write-Host "      Authentication successful!" -ForegroundColor Green
    } elseif (Test-Path $geminiHome) {
        Write-Host "      Authentication completed (settings.json not detected)" -ForegroundColor Yellow
    } else {
        Write-Host "      WARNING: .gemini directory not found after login" -ForegroundColor Yellow
    }
} else {
    Write-Host "[4/4] Skipping login (as requested)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Setup Complete!                      " -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Gemini OAuth credentials are stored in:" -ForegroundColor Cyan
Write-Host "  $geminiHome" -ForegroundColor Cyan
Write-Host ""
