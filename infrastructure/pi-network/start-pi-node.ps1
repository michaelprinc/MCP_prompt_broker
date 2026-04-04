# Pi Network Node - Spusteni a konfigurace
# Autor: GitHub Copilot
# Datum: 2026-01-11

Write-Host "=== Pi Network Node Setup ===" -ForegroundColor Cyan
Write-Host ""

# Kontrola Docker
Write-Host "1. Kontrola Docker Desktop..." -ForegroundColor Yellow
$dockerVersion = docker --version
if ($LASTEXITCODE -eq 0) {
    Write-Host "OK Docker je nainstalovany: $dockerVersion" -ForegroundColor Green
} else {
    Write-Host "CHYBA Docker neni nainstalovany nebo neni spusten" -ForegroundColor Red
    exit 1
}

# Kontrola bezicich kontejneru
Write-Host ""
Write-Host "2. Kontrola existujicich Pi Node kontejneru..." -ForegroundColor Yellow
$existingContainer = docker ps -a --filter "name=pi-node" --format "{{.Names}}"
if ($existingContainer) {
    Write-Host "POZOR Nalezen existujici kontejner: $existingContainer" -ForegroundColor Yellow
    $response = Read-Host "Chcete jej odstranit a vytvorit novy? (A/N)"
    if ($response -eq 'A' -or $response -eq 'a') {
        Write-Host "Zastavuji a odstranuji stary kontejner..." -ForegroundColor Yellow
        docker stop $existingContainer 2>$null
        docker rm $existingContainer 2>$null
        Write-Host "OK Stary kontejner odstranen" -ForegroundColor Green
    } else {
        Write-Host "Ponechavam existujici kontejner" -ForegroundColor Yellow
        exit 0
    }
}

# Kontrola portů
Write-Host ""
Write-Host "3. Kontrola dostupnosti portů 31400-31409..." -ForegroundColor Yellow
$portsInUse = @()
31400..31409 | ForEach-Object {
    $port = $_
    $connection = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    if ($connection) {
        $portsInUse += $port
    }
}

if ($portsInUse.Count -gt 0) {
    Write-Host "⚠ Následující porty jsou již používány: $($portsInUse -join ', ')" -ForegroundColor Yellow
    Write-Host "Pokračování může způsobit konflikt portů" -ForegroundColor Yellow
} else {
    Write-Host "✓ Všechny požadované porty jsou volné" -ForegroundColor Green
}

# Firewall pravidla
Write-Host ""
Write-Host "4. Kontrola firewall pravidel..." -ForegroundColor Yellow
$firewallRules = Get-NetFirewallRule -DisplayName "Pi Node*" -ErrorAction SilentlyContinue

if (-not $firewallRules) {
    Write-Host "Vytvářím firewall pravidla..." -ForegroundColor Yellow
    
    # Zkontrolujeme administrátorská práva
    $isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    
    if ($isAdmin) {
        New-NetFirewallRule -DisplayName "Pi Node Testnet2 Inbound" `
            -Direction Inbound `
            -LocalPort 31400-31409 `
            -Protocol TCP `
            -Action Allow `
            -ErrorAction SilentlyContinue
        
        New-NetFirewallRule -DisplayName "Pi Node Testnet2 Outbound" `
            -Direction Outbound `
            -LocalPort 31400-31409 `
            -Protocol TCP `
            -Action Allow `
            -ErrorAction SilentlyContinue
        
        Write-Host "✓ Firewall pravidla vytvořena" -ForegroundColor Green
    } else {
        Write-Host "⚠ Pro vytvoření firewall pravidel je třeba spustit jako administrátor" -ForegroundColor Yellow
        Write-Host "  Můžete pokračovat, ale může být třeba manuálně povolit porty" -ForegroundColor Yellow
    }
} else {
    Write-Host "✓ Firewall pravidla již existují" -ForegroundColor Green
}

# Stažení nejnovějšího image
Write-Host ""
Write-Host "5. Stahování nejnovějšího Pi Node Docker image..." -ForegroundColor Yellow
docker pull pinetwork/pi-node-docker:latest

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Image úspěšně stažen" -ForegroundColor Green
} else {
    Write-Host "✗ Chyba při stahování image" -ForegroundColor Red
    exit 1
}

# Vytvoření volumes
Write-Host ""
Write-Host "6. Vytváření Docker volumes..." -ForegroundColor Yellow
docker volume create pi-data 2>$null
docker volume create pi-stellar 2>$null
Write-Host "✓ Volumes vytvořeny" -ForegroundColor Green

# Spuštění kontejneru
Write-Host ""
Write-Host "7. Spouštím Pi Node kontejner..." -ForegroundColor Yellow

docker run -d `
  --name pi-node-testnet2 `
  --restart unless-stopped `
  -v pi-data:/home/pi/.pi `
  -v pi-stellar:/root/.stellar `
  -e NETWORK=testnet2 `
  -e PI_NODE_NAME=pi-node-local `
  -e AUTO_UPDATE=true `
  -p 31400:31400 `
  -p 31401:31401 `
  -p 31402:31402 `
  -p 31403:31403 `
  -p 31404:31404 `
  -p 31405:31405 `
  -p 31406:31406 `
  -p 31407:31407 `
  -p 31408:31408 `
  -p 31409:31409 `
  -it pinetwork/pi-node-docker:latest

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Kontejner úspěšně spuštěn!" -ForegroundColor Green
    
    # Čekání na inicializaci
    Write-Host ""
    Write-Host "8. Čekám na inicializaci Node (10 sekund)..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10
    
    # Zobrazení stavu
    Write-Host ""
    Write-Host "9. Aktuální stav kontejneru:" -ForegroundColor Yellow
    docker ps --filter "name=pi-node-testnet2" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    
    # Zobrazení logů
    Write-Host ""
    Write-Host "10. Poslední logy (prvních 20 řádků):" -ForegroundColor Yellow
    docker logs pi-node-testnet2 --tail 20
    
    Write-Host ""
    Write-Host "=== Setup dokončen ===" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Užitečné příkazy:" -ForegroundColor Yellow
    Write-Host "  Zobrazit logy:    docker logs -f pi-node-testnet2" -ForegroundColor White
    Write-Host "  Zastavit Node:    docker stop pi-node-testnet2" -ForegroundColor White
    Write-Host "  Spustit Node:     docker start pi-node-testnet2" -ForegroundColor White
    Write-Host "  Přístup do shell: docker exec -it pi-node-testnet2 /bin/bash" -ForegroundColor White
    Write-Host "  Restart Node:     docker restart pi-node-testnet2" -ForegroundColor White
    Write-Host ""
    
} else {
    Write-Host "✗ Chyba při spouštění kontejneru" -ForegroundColor Red
    Write-Host "Zkontrolujte logy Docker Desktop a zkuste to znovu" -ForegroundColor Yellow
    exit 1
}
