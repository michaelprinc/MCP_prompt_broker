# Pi Network Node - Quick Start Script
# Simple installation script without special characters

Write-Host "=== Pi Network Node Setup ===" -ForegroundColor Cyan

# Check Docker
Write-Host "Checking Docker..." -ForegroundColor Yellow
docker --version
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Docker is not running" -ForegroundColor Red
    exit 1
}

# Remove existing container if present
Write-Host "Removing existing Pi Node containers..." -ForegroundColor Yellow
docker stop pi-node-testnet2 2>$null
docker rm pi-node-testnet2 2>$null

# Pull latest image
Write-Host "Pulling latest Pi Node image..." -ForegroundColor Yellow
docker pull pinetwork/pi-node-docker:latest

# Create volumes
Write-Host "Creating volumes..." -ForegroundColor Yellow
docker volume create pi-data 2>$null
docker volume create pi-stellar 2>$null

# Run container
Write-Host "Starting Pi Node container..." -ForegroundColor Yellow
docker run -d `
  --name pi-node-testnet2 `
  --restart unless-stopped `
  -v pi-data:/home/pi/.pi `
  -v pi-stellar:/root/.stellar `
  -e NETWORK=testnet2 `
  -e PI_NODE_NAME=pi-node-local `
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
  pinetwork/pi-node-docker:latest

if ($LASTEXITCODE -eq 0) {
    Write-Host "SUCCESS: Container started!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Waiting for initialization..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5
    
    Write-Host ""
    Write-Host "Container status:" -ForegroundColor Yellow
    docker ps --filter "name=pi-node-testnet2"
    
    Write-Host ""
    Write-Host "Recent logs:" -ForegroundColor Yellow
    docker logs pi-node-testnet2 --tail 15
    
    Write-Host ""
    Write-Host "=== Setup Complete ===" -ForegroundColor Green
    Write-Host ""
    Write-Host "Useful commands:"
    Write-Host "  View logs:    docker logs -f pi-node-testnet2"
    Write-Host "  Stop node:    docker stop pi-node-testnet2"
    Write-Host "  Start node:   docker start pi-node-testnet2"
    Write-Host "  Shell access: docker exec -it pi-node-testnet2 /bin/bash"
    Write-Host ""
} else {
    Write-Host "ERROR: Failed to start container" -ForegroundColor Red
    exit 1
}
