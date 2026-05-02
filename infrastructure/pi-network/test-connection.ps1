# Pi Network Node - Test připojení a portů
# Autor: GitHub Copilot
# Datum: 2026-01-11

Write-Host "=== Pi Network Node - Test připojení ===" -ForegroundColor Cyan
Write-Host ""

# Kontrola běžícího kontejneru
Write-Host "1. Kontrola stavu kontejneru..." -ForegroundColor Yellow
$containerStatus = docker ps --filter "name=pi-node" --format "{{.Names}} - {{.Status}}"

if ($containerStatus) {
    Write-Host "✓ Nalezen běžící kontejner:" -ForegroundColor Green
    Write-Host "  $containerStatus" -ForegroundColor White
} else {
    Write-Host "✗ Pi Node kontejner neběží" -ForegroundColor Red
    Write-Host "  Spusťte nejprve: .\start-pi-node.ps1" -ForegroundColor Yellow
    exit 1
}

# Test portů
Write-Host ""
Write-Host "2. Test naslouchání na portech..." -ForegroundColor Yellow

$ports = 31400..31409
$listeningPorts = @()
$notListeningPorts = @()

foreach ($port in $ports) {
    $connection = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if ($connection) {
        $listeningPorts += $port
        Write-Host "  ✓ Port $port - NASLOUCHÁ" -ForegroundColor Green
    } else {
        $notListeningPorts += $port
        Write-Host "  ✗ Port $port - NENASLOUCHÁ" -ForegroundColor Red
    }
}

Write-Host ""
if ($listeningPorts.Count -gt 0) {
    Write-Host "Naslouchající porty: $($listeningPorts -join ', ')" -ForegroundColor Green
}
if ($notListeningPorts.Count -gt 0) {
    Write-Host "Nenaslouchající porty: $($notListeningPorts -join ', ')" -ForegroundColor Yellow
}

# Kontrola Docker volumes
Write-Host ""
Write-Host "3. Kontrola Docker volumes..." -ForegroundColor Yellow
$volumes = docker volume ls --filter "name=pi" --format "{{.Name}}"
if ($volumes) {
    Write-Host "✓ Nalezeny volumes:" -ForegroundColor Green
    $volumes | ForEach-Object { Write-Host "  - $_" -ForegroundColor White }
} else {
    Write-Host "⚠ Nenalezeny žádné Pi volumes" -ForegroundColor Yellow
}

# Inspekce kontejneru
Write-Host ""
Write-Host "4. Detaily kontejneru..." -ForegroundColor Yellow
$containerInfo = docker inspect pi-node-testnet2 2>$null | ConvertFrom-Json

if ($containerInfo) {
    Write-Host "  Jméno:     $($containerInfo.Name)" -ForegroundColor White
    Write-Host "  Stav:      $($containerInfo.State.Status)" -ForegroundColor White
    Write-Host "  Spuštěno:  $($containerInfo.State.StartedAt)" -ForegroundColor White
    Write-Host "  Restart:   $($containerInfo.HostConfig.RestartPolicy.Name)" -ForegroundColor White
}

# Test síťového připojení
Write-Host ""
Write-Host "5. Test síťového připojení..." -ForegroundColor Yellow

# Test localhost připojení na hlavní port
$testPort = 31400
try {
    $tcpClient = New-Object System.Net.Sockets.TcpClient
    $tcpClient.Connect("localhost", $testPort)
    if ($tcpClient.Connected) {
        Write-Host "  ✓ Úspěšné připojení na localhost:$testPort" -ForegroundColor Green
        $tcpClient.Close()
    }
} catch {
    Write-Host "  ✗ Nelze se připojit na localhost:$testPort" -ForegroundColor Red
    Write-Host "    Důvod: $($_.Exception.Message)" -ForegroundColor Yellow
}

# Zobrazení logů
Write-Host ""
Write-Host "6. Poslední logy (20 řádků):" -ForegroundColor Yellow
docker logs pi-node-testnet2 --tail 20

Write-Host ""
Write-Host "=== Test dokončen ===" -ForegroundColor Cyan
Write-Host ""

# Souhrn
Write-Host "SOUHRN:" -ForegroundColor Cyan
if ($listeningPorts.Count -ge 5) {
    Write-Host "  ✓ Node pravděpodobně běží správně" -ForegroundColor Green
} elseif ($listeningPorts.Count -gt 0) {
    Write-Host "  ⚠ Node částečně běží (některé porty nenalezeny)" -ForegroundColor Yellow
} else {
    Write-Host "  ✗ Node pravděpodobně neběží správně" -ForegroundColor Red
}

Write-Host ""
Write-Host "Pro kontinuální sledování logů použijte:" -ForegroundColor Yellow
Write-Host "  docker logs -f pi-node-testnet2" -ForegroundColor White
Write-Host ""
