# Pi Network Node - Corrected Quick Start Script

Write-Host "=== Pi Network Node Setup (Testnet) ===" -ForegroundColor Cyan

# Check Docker
Write-Host "Checking Docker..." -ForegroundColor Yellow
docker --version
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Docker is not running" -ForegroundColor Red
    exit 1
}

# Remove existing container if present
Write-Host "Removing existing Pi Node containers..." -ForegroundColor Yellow
docker stop pi-node-testnet 2>$null
docker rm pi-node-testnet 2>$null

# Pull latest image
Write-Host "Pulling latest Pi Node image..." -ForegroundColor Yellow
docker pull pinetwork/pi-node-docker:latest

# Create volumes
Write-Host "Creating volumes..." -ForegroundColor Yellow
docker volume create pi-data 2>$null
docker volume create pi-stellar 2>$null

# Run container with correct network parameter
Write-Host "Starting Pi Node container on testnet..." -ForegroundColor Yellow
docker run -d `
  --name pi-node-testnet `
  --restart unless-stopped `
  -v pi-data:/home/pi/.pi `
  -v pi-stellar:/root/.stellar `
  -p 31400:11625 `
  -p 31401:11626 `
  -p 31402:8000 `
  pinetwork/pi-node-docker:latest --testnet

if ($LASTEXITCODE -eq 0) {
    Write-Host "SUCCESS: Container started!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Waiting for initialization (30 seconds)..." -ForegroundColor Yellow
    Start-Sleep -Seconds 30
    
    Write-Host ""
    Write-Host "Container status:" -ForegroundColor Yellow
    docker ps --filter "name=pi-node-testnet" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    
    Write-Host ""
    Write-Host "Recent logs:" -ForegroundColor Yellow
    docker logs pi-node-testnet --tail 30
    
    Write-Host ""
    Write-Host "=== Setup Complete ===" -ForegroundColor Green
    Write-Host ""
    Write-Host "Network: Stellar Testnet"
    Write-Host "Ports mapping:"
    Write-Host "  31400 -> 11625 (Stellar Core Peer)"
    Write-Host "  31401 -> 11626 (Stellar Core HTTP)"
    Write-Host "  31402 -> 8000 (Horizon API)"
    Write-Host ""
    Write-Host "Useful commands:"
    Write-Host "  View logs:    docker logs -f pi-node-testnet"
    Write-Host "  Stop node:    docker stop pi-node-testnet"
    Write-Host "  Start node:   docker start pi-node-testnet"
    Write-Host "  Shell access: docker exec -it pi-node-testnet /bin/bash"
    Write-Host "  Check sync:   docker exec pi-node-testnet stellar-core http-command info"
    Write-Host ""
} else {
    Write-Host "ERROR: Failed to start container" -ForegroundColor Red
    exit 1
}
