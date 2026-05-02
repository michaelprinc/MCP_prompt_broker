# Pi Network Node - Connection Test Script

Write-Host "=== Pi Network Node Connection Test ===" -ForegroundColor Cyan
Write-Host ""

# Check container status
Write-Host "1. Container Status Check..." -ForegroundColor Yellow
$containerStatus = docker ps --filter "name=pi-node-testnet" --format "{{.Status}}"

if ($containerStatus) {
    Write-Host "OK Container is running: $containerStatus" -ForegroundColor Green
} else {
    Write-Host "ERROR: Container is not running" -ForegroundColor Red
    Write-Host "Start it with: .\start-testnet.ps1" -ForegroundColor Yellow
    exit 1
}

# Check listening ports
Write-Host ""
Write-Host "2. Port Status Check..." -ForegroundColor Yellow
$expectedPorts = @(31400, 31401, 31402)
$openPorts = @()

foreach ($port in $expectedPorts) {
    $connection = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if ($connection) {
        Write-Host "  OK Port $port is LISTENING" -ForegroundColor Green
        $openPorts += $port
    } else {
        Write-Host "  ERROR Port $port is NOT listening" -ForegroundColor Red
    }
}

# Check Stellar Core status
Write-Host ""
Write-Host "3. Stellar Core Status..." -ForegroundColor Yellow
try {
    $coreInfo = docker exec pi-node-testnet stellar-core http-command info 2>&1 | Select-String -Pattern '"state"' | Select-Object -First 1
    Write-Host "  $coreInfo" -ForegroundColor White
} catch {
    Write-Host "  ERROR: Could not retrieve core info" -ForegroundColor Red
}

# Test HTTP endpoint
Write-Host ""
Write-Host "4. HTTP Endpoint Test..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:31402/" -TimeoutSec 5 -ErrorAction Stop
    Write-Host "  OK Horizon API is responding (Status: $($response.StatusCode))" -ForegroundColor Green
} catch {
    Write-Host "  WARNING: Horizon API not yet available" -ForegroundColor Yellow
    Write-Host "  (This is normal during initial sync)" -ForegroundColor White
}

# Display recent logs
Write-Host ""
Write-Host "5. Recent Logs (last 15 lines)..." -ForegroundColor Yellow
docker logs pi-node-testnet --tail 15

# Summary
Write-Host ""
Write-Host "=== Test Summary ===" -ForegroundColor Cyan
if ($openPorts.Count -eq $expectedPorts.Count) {
    Write-Host "Status: HEALTHY" -ForegroundColor Green
    Write-Host "All required ports are open and container is running." -ForegroundColor Green
} else {
    Write-Host "Status: PARTIAL" -ForegroundColor Yellow
    Write-Host "Container is running but some ports may not be ready yet." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Open Ports: $($openPorts -join ', ')" -ForegroundColor White
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  - Monitor sync status: docker exec pi-node-testnet stellar-core http-command info" -ForegroundColor White
Write-Host "  - View live logs: docker logs -f pi-node-testnet" -ForegroundColor White
Write-Host "  - Access Horizon API: http://localhost:31402" -ForegroundColor White
Write-Host ""
