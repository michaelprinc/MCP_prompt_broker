# CLI Reference - Llama Orchestrator

> **Verze dokumentace:** 1.0.0  
> **Datum:** 31. prosince 2025  
> **Úroveň:** 4/4 - API Reference

---

## 📋 Obsah

1. [Přehled CLI](#přehled-cli)
2. [Globální volby](#globální-volby)
3. [Instance příkazy](#instance-příkazy)
4. [Monitoring příkazy](#monitoring-příkazy)
5. [Daemon příkazy](#daemon-příkazy)
6. [Config příkazy](#config-příkazy)
7. [Exit kódy](#exit-kódy)

---

## Přehled CLI

```
llama-orch - Docker-like orchestration for llama.cpp servers

Usage: llama-orch [OPTIONS] COMMAND [ARGS]...

Commands:
  init        Initialize a new instance configuration
  up          Start an instance
  down        Stop an instance
  restart     Restart an instance
  ps          List all instances
  logs        View instance logs
  health      Check instance health
  describe    Show detailed instance information
  dashboard   Launch TUI dashboard
  daemon      Daemon management commands
  config      Configuration commands
```

---

## Globální volby

| Volba | Zkratka | Typ | Popis |
|-------|---------|-----|-------|
| `--help` | `-h` | flag | Zobrazí nápovědu |
| `--version` | `-v` | flag | Zobrazí verzi |
| `--verbose` | | flag | Verbose output |
| `--quiet` | `-q` | flag | Minimální output |
| `--config-dir` | `-c` | path | Custom config directory |

```powershell
# Příklady
llama-orch --version
llama-orch --help
llama-orch --verbose up gpt-oss
```

---

## Instance příkazy

### init

**Inicializuje novou instanci.**

```
llama-orch init [OPTIONS] NAME
```

#### Argumenty

| Argument | Typ | Povinný | Popis |
|----------|-----|---------|-------|
| `NAME` | string | ✅ | Název instance |

#### Volby

| Volba | Zkratka | Typ | Default | Popis |
|-------|---------|-----|---------|-------|
| `--model` | `-m` | path | - | Cesta k GGUF modelu |
| `--port` | `-p` | int | 8001 | Port serveru |
| `--host` | | string | 127.0.0.1 | Host adresa |
| `--context-size` | | int | 4096 | Context window |
| `--gpu-layers` | `-g` | int | 0 | GPU offload layers |
| `--threads` | `-t` | int | 8 | CPU threads |
| `--parallel` | | int | 4 | Parallel requests |

#### Příklady

```powershell
# Základní inicializace
llama-orch init gpt-oss --model "../models/gpt-oss-20b.gguf"

# S GPU akcelerací
llama-orch init llama3 -m "../models/llama-3-8b.gguf" -p 8002 -g 99

# Plná konfigurace
llama-orch init production `
  --model "../models/model.gguf" `
  --port 8080 `
  --host 0.0.0.0 `
  --context-size 8192 `
  --gpu-layers 40 `
  --threads 16 `
  --parallel 8
```

---

### up

**Spustí instanci.**

```
llama-orch up [OPTIONS] NAME
```

#### Argumenty

| Argument | Typ | Povinný | Popis |
|----------|-----|---------|-------|
| `NAME` | string | ✅ | Název instance |

#### Volby

| Volba | Zkratka | Typ | Default | Popis |
|-------|---------|-----|---------|-------|
| `--detach` | `-d` | flag | false | Spustit na pozadí |
| `--wait` | `-w` | flag | false | Čekat na healthy stav |
| `--timeout` | | int | 60 | Timeout pro wait (s) |

#### Příklady

```powershell
# Interaktivní spuštění
llama-orch up gpt-oss

# Na pozadí
llama-orch up gpt-oss -d

# S čekáním na healthy
llama-orch up gpt-oss -d --wait --timeout 120
```

---

### down

**Zastaví instanci.**

```
llama-orch down [OPTIONS] NAME
```

#### Argumenty

| Argument | Typ | Povinný | Popis |
|----------|-----|---------|-------|
| `NAME` | string | ✅ | Název instance |

#### Volby

| Volba | Zkratka | Typ | Default | Popis |
|-------|---------|-----|---------|-------|
| `--force` | `-f` | flag | false | Forceful kill |
| `--timeout` | | int | 10 | Graceful shutdown timeout |

#### Příklady

```powershell
# Graceful stop
llama-orch down gpt-oss

# Force kill
llama-orch down gpt-oss --force

# Custom timeout
llama-orch down gpt-oss --timeout 30
```

---

### restart

**Restartuje instanci.**

```
llama-orch restart [OPTIONS] NAME
```

#### Argumenty

| Argument | Typ | Povinný | Popis |
|----------|-----|---------|-------|
| `NAME` | string | ✅ | Název instance |

#### Volby

| Volba | Zkratka | Typ | Default | Popis |
|-------|---------|-----|---------|-------|
| `--wait` | `-w` | flag | false | Čekat na healthy |

#### Příklady

```powershell
llama-orch restart gpt-oss
llama-orch restart gpt-oss --wait
```

---

### rm

**Odstraní instanci.**

```
llama-orch rm [OPTIONS] NAME
```

#### Argumenty

| Argument | Typ | Povinný | Popis |
|----------|-----|---------|-------|
| `NAME` | string | ✅ | Název instance |

#### Volby

| Volba | Zkratka | Typ | Default | Popis |
|-------|---------|-----|---------|-------|
| `--force` | `-f` | flag | false | Odstranit i running |

#### Příklady

```powershell
llama-orch rm old-instance
llama-orch rm running-instance --force
```

---

## Monitoring příkazy

### ps

**Zobrazí seznam instancí.**

```
llama-orch ps [OPTIONS]
```

#### Volby

| Volba | Zkratka | Typ | Default | Popis |
|-------|---------|-----|---------|-------|
| `--all` | `-a` | flag | false | Včetně stopped |
| `--format` | | string | table | table/json/csv |

#### Příklady

```powershell
# Pouze running
llama-orch ps

# Všechny instance
llama-orch ps --all

# JSON output
llama-orch ps --format json
```

#### Output

```
NAME       STATUS    PORT   MODEL               UPTIME     HEALTH
gpt-oss    running   8001   gpt-oss-20b-Q4      2h 15m     healthy
llama3     running   8002   llama-3-8b-Q4       45m        healthy
test       stopped   8003   -                   -          -
```

---

### logs

**Zobrazí logy instance.**

```
llama-orch logs [OPTIONS] NAME
```

#### Argumenty

| Argument | Typ | Povinný | Popis |
|----------|-----|---------|-------|
| `NAME` | string | ✅ | Název instance |

#### Volby

| Volba | Zkratka | Typ | Default | Popis |
|-------|---------|-----|---------|-------|
| `--follow` | `-f` | flag | false | Follow mode |
| `--tail` | `-n` | int | 100 | Počet řádků |
| `--since` | | string | - | Od času (e.g., "1h") |

#### Příklady

```powershell
# Posledních 100 řádků
llama-orch logs gpt-oss

# Follow mode
llama-orch logs gpt-oss -f

# Posledních 50 řádků
llama-orch logs gpt-oss -n 50

# Od poslední hodiny
llama-orch logs gpt-oss --since 1h
```

---

### health

**Zkontroluje zdraví instance.**

```
llama-orch health [OPTIONS] NAME
```

#### Argumenty

| Argument | Typ | Povinný | Popis |
|----------|-----|---------|-------|
| `NAME` | string | ✅ | Název instance |

#### Volby

| Volba | Zkratka | Typ | Default | Popis |
|-------|---------|-----|---------|-------|
| `--json` | | flag | false | JSON output |

#### Příklady

```powershell
llama-orch health gpt-oss
```

#### Output

```
Instance: gpt-oss
Status: healthy
Response time: 45ms
Last check: 2025-12-31 10:30:00
Consecutive failures: 0
```

---

### describe

**Zobrazí detailní informace o instanci.**

```
llama-orch describe [OPTIONS] NAME
```

#### Argumenty

| Argument | Typ | Povinný | Popis |
|----------|-----|---------|-------|
| `NAME` | string | ✅ | Název instance |

#### Příklady

```powershell
llama-orch describe gpt-oss
```

#### Output

```yaml
Name: gpt-oss
Status: running
PID: 12345
Port: 8001
Host: 127.0.0.1

Model:
  Path: ../models/gpt-oss-20b-Q4_K_S.gguf
  Context Size: 4096
  GPU Layers: 0
  Threads: 16

Server:
  Parallel Requests: 4
  Started At: 2025-12-31 08:15:00
  Uptime: 2h 15m

Health:
  Status: healthy
  Last Check: 10:30:00
  Response Time: 45ms
  Failures: 0/3

Resources:
  CPU: 45%
  Memory: 12.5 GB
```

---

### dashboard

**Spustí TUI dashboard.**

```
llama-orch dashboard [OPTIONS]
```

#### Volby

| Volba | Zkratka | Typ | Default | Popis |
|-------|---------|-----|---------|-------|
| `--refresh` | `-r` | int | 5 | Refresh interval (s) |

#### Příklady

```powershell
llama-orch dashboard
llama-orch dashboard --refresh 2
```

#### Keyboard Shortcuts

| Klávesa | Akce |
|---------|------|
| `Q` | Quit |
| `R` | Refresh |
| `S` | Start selected |
| `D` | Stop selected |
| `L` | View logs |
| `↑/↓` | Navigate |
| `Enter` | Describe |

---

## Daemon příkazy

### daemon start

**Spustí daemon na pozadí.**

```
llama-orch daemon start [OPTIONS]
```

#### Volby

| Volba | Zkratka | Typ | Default | Popis |
|-------|---------|-----|---------|-------|
| `--foreground` | `-f` | flag | false | Spustit v popředí |

#### Příklady

```powershell
llama-orch daemon start
llama-orch daemon start --foreground
```

---

### daemon stop

**Zastaví daemon.**

```
llama-orch daemon stop
```

---

### daemon status

**Zobrazí stav daemonu.**

```
llama-orch daemon status
```

#### Output

```
Daemon Status: running
PID: 5678
Uptime: 4h 30m
Instances Managed: 2
Health Checks: 540
Auto-restarts: 1
```

---

## Config příkazy

### config validate

**Validuje konfiguraci instance.**

```
llama-orch config validate [NAME]
```

#### Argumenty

| Argument | Typ | Povinný | Popis |
|----------|-----|---------|-------|
| `NAME` | string | ❌ | Název instance (nebo všechny) |

#### Příklady

```powershell
# Validovat konkrétní
llama-orch config validate gpt-oss

# Validovat všechny
llama-orch config validate
```

---

### config show

**Zobrazí konfiguraci instance.**

```
llama-orch config show NAME
```

#### Příklady

```powershell
llama-orch config show gpt-oss
```

#### Output (JSON)

```json
{
  "name": "gpt-oss",
  "model": {
    "path": "../models/gpt-oss-20b-Q4_K_S.gguf",
    "context_size": 4096,
    "gpu_layers": 0
  },
  "server": {
    "host": "127.0.0.1",
    "port": 8001
  }
}
```

---

### config edit

**Otevře konfiguraci v editoru.**

```
llama-orch config edit NAME
```

#### Příklady

```powershell
llama-orch config edit gpt-oss
# Otevře $EDITOR nebo notepad
```

---

## Exit kódy

| Kód | Význam |
|-----|--------|
| 0 | Úspěch |
| 1 | Obecná chyba |
| 2 | Neplatné argumenty |
| 3 | Instance nenalezena |
| 4 | Instance už běží |
| 5 | Instance neběží |
| 6 | Konfigurační chyba |
| 7 | Timeout |
| 8 | Health check failed |
| 9 | Daemon error |

---

## Environment Variables

| Proměnná | Popis |
|----------|-------|
| `LLAMA_ORCH_CONFIG_DIR` | Config directory |
| `LLAMA_ORCH_LOG_LEVEL` | Log level (DEBUG, INFO, WARNING, ERROR) |
| `LLAMA_CPP_PATH` | Path to llama.cpp binary |
| `EDITOR` | Default editor for config edit |

---

## Shell Completion

### PowerShell

```powershell
# Přidat do $PROFILE
llama-orch --install-completion powershell
```

### Bash

```bash
# Přidat do .bashrc
eval "$(llama-orch --install-completion bash)"
```

---

## Související dokumenty

- **Llama Orchestrator:** [../modules/LLAMA_ORCHESTRATOR.md](../modules/LLAMA_ORCHESTRATOR.md)
- **Llama CPP Server:** [../modules/LLAMA_CPP_SERVER.md](../modules/LLAMA_CPP_SERVER.md)
- **Architektura:** [../architecture/ARCHITECTURE.md](../architecture/ARCHITECTURE.md)

---

*Tato dokumentace je součástí 4-úrovňové dokumentační struktury projektu MCP Prompt Broker.*
