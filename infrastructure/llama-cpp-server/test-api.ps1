<#
.SYNOPSIS
    Test API llama.cpp serveru
    
.DESCRIPTION
    Testuje dostupnost a funkčnost llama.cpp serveru
    
.PARAMETER BaseUrl
    URL serveru (výchozí: http://localhost:8001)
    
.PARAMETER Prompt
    Testovací prompt pro generování
#>

[CmdletBinding()]
param(
    [Parameter()]
    [string]$BaseUrl = "http://localhost:8001",
    
    [Parameter()]
    [string]$Prompt = "Hello! Please respond with a brief greeting."
)

$ErrorActionPreference = "Stop"

function Write-Header {
    param([string]$Text)
    Write-Host ""
    Write-Host ("=" * 60) -ForegroundColor Cyan
    Write-Host " $Text" -ForegroundColor Cyan
    Write-Host ("=" * 60) -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Text)
    Write-Host "[OK] $Text" -ForegroundColor Green
}

function Write-Error-Custom {
    param([string]$Text)
    Write-Host "[ERROR] $Text" -ForegroundColor Red
}

function Write-Info {
    param([string]$Text)
    Write-Host "[INFO] $Text" -ForegroundColor Yellow
}

Write-Header "Test 1: Health Check"

try {
    $response = Invoke-RestMethod -Uri "$BaseUrl/health" -Method GET -TimeoutSec 5
    
    if ($response.status -eq "ok") {
        Write-Success "Health check passed"
        Write-Info "Server status: $($response.status)"
    } else {
        Write-Error-Custom "Health check failed: unexpected status"
    }
} catch {
    Write-Error-Custom "Health check failed: $_"
    Write-Host ""
    Write-Host "Možné příčiny:" -ForegroundColor Yellow
    Write-Host "  1. Server neběží (spusťte: .\start-server.ps1)" -ForegroundColor Gray
    Write-Host "  2. Nesprávný port (ověřte: $BaseUrl)" -ForegroundColor Gray
    Write-Host "  3. Firewall blokuje připojení" -ForegroundColor Gray
    exit 1
}

Write-Header "Test 2: Model Info"

try {
    $response = Invoke-RestMethod -Uri "$BaseUrl/v1/models" -Method GET -TimeoutSec 5
    
    if ($response.data -and $response.data.Count -gt 0) {
        Write-Success "Model endpoint accessible"
        foreach ($model in $response.data) {
            Write-Info "Model ID: $($model.id)"
            Write-Info "Object: $($model.object)"
        }
    } else {
        Write-Error-Custom "No models found"
    }
} catch {
    Write-Error-Custom "Model info failed: $_"
}

Write-Header "Test 3: Chat Completion"

$body = @{
    model = "gpt-oss-20b"
    messages = @(
        @{
            role = "user"
            content = $Prompt
        }
    )
    max_tokens = 100
    temperature = 0.7
} | ConvertTo-Json -Depth 5

Write-Info "Odesílám testovací dotaz..."
Write-Host "    Prompt: $Prompt" -ForegroundColor Gray

try {
    $startTime = Get-Date
    
    $response = Invoke-RestMethod `
        -Uri "$BaseUrl/v1/chat/completions" `
        -Method POST `
        -Body $body `
        -ContentType "application/json" `
        -TimeoutSec 120
    
    $endTime = Get-Date
    $duration = ($endTime - $startTime).TotalSeconds
    
    Write-Success "Chat completion successful"
    Write-Host ""
    Write-Host "Odpověď modelu:" -ForegroundColor Cyan
    Write-Host "  $($response.choices[0].message.content.Substring(0, [Math]::Min(200, $response.choices[0].message.content.Length)))" -ForegroundColor White
    Write-Host ""
    Write-Info "Statistiky:"
    Write-Host "    Doba generování: $([math]::Round($duration, 2)) s" -ForegroundColor Gray
    Write-Host "    Prompt tokeny: $($response.usage.prompt_tokens)" -ForegroundColor Gray
    Write-Host "    Vygenerované tokeny: $($response.usage.completion_tokens)" -ForegroundColor Gray
    Write-Host "    Celkové tokeny: $($response.usage.total_tokens)" -ForegroundColor Gray
    
    if ($response.timings) {
        $tokensPerSec = [math]::Round($response.timings.predicted_per_second, 2)
        Write-Host "    Rychlost generování: $tokensPerSec tokens/s" -ForegroundColor Gray
    }
    
} catch {
    Write-Error-Custom "Chat completion failed: $_"
}

Write-Header "Test Summary"

Write-Host ""
Write-Success "Všechny testy dokončeny"
Write-Host ""
Write-Host "Server je připraven k použití:" -ForegroundColor Green
Write-Host "    API: $BaseUrl/v1/chat/completions" -ForegroundColor Cyan
Write-Host ""
