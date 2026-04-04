# Pi Network Node - Docker Setup

## Přehled
Tato složka obsahuje konfiguraci pro spuštění Pi Network Node v Docker kontejneru s připojením na testnet2.

## Požadavky
- Docker Desktop nainstalován a běžící
- Otevřené porty: 31400-31409
- Přibližně 2GB volného místa na disku

## Instalace a spuštění

### 1. Stažení nejnovějšího Docker image
```powershell
docker pull pinetwork/pi-node-docker:latest
```

### 2. Spuštění kontejneru pomocí docker-compose
```powershell
cd K:\Data_science_projects\MCP_Prompt_Broker\infrastructure\pi-network
docker-compose up -d
```

### 3. Spuštění kontejneru pomocí docker run (alternativa)
```powershell
docker run -d `
  --name pi-node-testnet2 `
  --restart unless-stopped `
  --network host `
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
```

## Užitečné příkazy

### Zobrazení logů
```powershell
docker logs -f pi-node-testnet2
```

### Zastavení kontejneru
```powershell
docker stop pi-node-testnet2
```

### Spuštění kontejneru
```powershell
docker start pi-node-testnet2
```

### Přístup do kontejneru (shell)
```powershell
docker exec -it pi-node-testnet2 /bin/bash
```

### Kontrola stavu
```powershell
docker ps | Select-String "pi-node"
```

### Restart kontejneru
```powershell
docker restart pi-node-testnet2
```

### Odstranění kontejneru
```powershell
docker stop pi-node-testnet2
docker rm pi-node-testnet2
```

## Troubleshooting

### Problém: Porty jsou již používány
Zkontrolujte, které aplikace používají porty 31400-31409:
```powershell
netstat -ano | Select-String "314"
```

### Problém: Docker kontejner se nezastaví
```powershell
docker kill pi-node-testnet2
```

### Problém: Firewall blokuje připojení
Vytvořte firewall pravidla pro příchozí a odchozí spojení:
```powershell
# Příchozí pravidlo
New-NetFirewallRule -DisplayName "Pi Node Testnet2 Inbound" -Direction Inbound -LocalPort 31400-31409 -Protocol TCP -Action Allow

# Odchozí pravidlo
New-NetFirewallRule -DisplayName "Pi Node Testnet2 Outbound" -Direction Outbound -LocalPort 31400-31409 -Protocol TCP -Action Allow
```

### Problém: Nedostatečná práva
Spusťte PowerShell jako administrátor.

## Porty

| Port  | Popis                          |
|-------|--------------------------------|
| 31400 | Stellar Core Peer Port         |
| 31401 | Stellar Core HTTP Port         |
| 31402 | Pi Consensus API               |
| 31403 | Pi Node Web Interface          |
| 31404 | Pi Blockchain Explorer         |
| 31405 | Reserved                       |
| 31406 | Reserved                       |
| 31407 | Reserved                       |
| 31408 | Reserved                       |
| 31409 | Reserved                       |

## Konfigurace

Kontejner automaticky vytvoří následující volumes:
- `pi-data`: Data Pi Node (konfigurace, databáze)
- `pi-stellar`: Stellar Core data

## Síťové režimy

Konfigurace používá `network_mode: host`, což znamená, že kontejner sdílí síťový stack s hostitelem. To je doporučeno pro Pi Node, aby mohl správně komunikovat s ostatními nody v síti.

## Aktualizace

Pro aktualizaci na nejnovější verzi:
```powershell
docker pull pinetwork/pi-node-docker:latest
docker-compose down
docker-compose up -d
```

## Monitoring

Kontrola stavu Node:
```powershell
# Stav kontejneru
docker stats pi-node-testnet2

# Využití resources
docker inspect pi-node-testnet2 | ConvertFrom-Json | Select-Object -ExpandProperty State
```

## Zálohování

Zálohování volumes:
```powershell
docker run --rm -v pi-data:/data -v ${PWD}:/backup alpine tar czf /backup/pi-data-backup.tar.gz /data
docker run --rm -v pi-stellar:/data -v ${PWD}:/backup alpine tar czf /backup/pi-stellar-backup.tar.gz /data
```

## Podpora

- Oficiální dokumentace: https://docs.minepi.com
- GitHub: https://github.com/pi-network
- Community: https://minepi.com/community
