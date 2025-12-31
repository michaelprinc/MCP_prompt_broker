# Llama CPP Server - Technická dokumentace modulu

> **Verze dokumentace:** 1.0.0  
> **Datum:** 31. prosince 2025  
> **Úroveň:** 3/4 - Module Technical Documentation

---

## 📋 Obsah

1. [Přehled modulu](#přehled-modulu)
2. [Struktura adresářů](#struktura-adresářů)
3. [Konfigurace serveru](#konfigurace-serveru)
4. [GPU akcelerace](#gpu-akcelerace)
5. [API endpointy](#api-endpointy)
6. [Spouštění a správa](#spouštění-a-správa)
7. [Integrace s llama-orchestrator](#integrace-s-llama-orchestrator)
8. [Troubleshooting](#troubleshooting)

---

## Přehled modulu

**Llama CPP Server** je konfigurační wrapper pro llama.cpp inference server s optimalizací pro AMD GPU na Windows.

### Technické charakteristiky

| Vlastnost | Hodnota |
|-----------|---------|
| **Backend** | llama.cpp |
| **GPU Backend** | Vulkan (AMD RDNA 2) |
| **API** | OpenAI-compatible |
| **Port** | 8001 (default) |
| **Model** | GPT-OSS-20B Q4_K_S |
| **Výkon** | ~12 t/s (CPU), ~62 t/s (GPU)* |

*\* Pro standardní modely. GPT-OSS má specifické mxfp4 tensory.*

### Aktuální stav

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CURRENT STATUS                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ✅ Status: FUNKČNÍ                                                         │
│                                                                             │
│  Model:     GPT-OSS-20B Q4_K_S (10.81 GB)                                  │
│  Port:      8001                                                            │
│  Backend:   Vulkan                                                          │
│  Mode:      CPU inference (mxfp4 tensory nemají GPU podporu)               │
│                                                                             │
│  Performance:                                                               │
│  ├── Generation: ~12 tokens/s                                               │
│  ├── Prompt:     ~17 tokens/s                                               │
│  └── Context:    4096 tokens                                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Struktura adresářů

```
llama-cpp-server/
├── README.md               # Dokumentace modulu
├── config.json             # Konfigurace serveru
├── start-server.ps1        # Spouštěcí PowerShell skript
├── test-api.ps1            # Testovací skript API
├── bin/
│   ├── llama-server.exe    # llama.cpp server binary
│   ├── LICENSE-curl        # Licence závislostí
│   ├── LICENSE-httplib
│   ├── LICENSE-jsonhpp
│   └── LICENSE-linenoise
└── (models/)               # Symlink nebo parent folder s modely
    └── gpt-oss-20b-Q4_K_S.gguf
```

---

## Konfigurace serveru

### config.json

```json
{
    "server": {
        "host": "127.0.0.1",
        "port": 8001,
        "parallel": 4
    },
    "model": {
        "path": "../models/gpt-oss-20b-Q4_K_S.gguf",
        "context_size": 4096,
        "batch_size": 512,
        "gpu_layers": 0
    },
    "inference": {
        "threads": 16,
        "flash_attention": false,
        "rope_frequency_base": 10000,
        "rope_frequency_scale": 1.0
    },
    "logging": {
        "level": "info",
        "file": null
    }
}
```

### Konfigurační parametry

| Sekce | Parametr | Typ | Default | Popis |
|-------|----------|-----|---------|-------|
| server | host | string | 127.0.0.1 | Listen address |
| server | port | int | 8001 | Listen port |
| server | parallel | int | 4 | Max parallel requests |
| model | path | string | - | Cesta k GGUF modelu |
| model | context_size | int | 4096 | Context window |
| model | batch_size | int | 512 | Batch size |
| model | gpu_layers | int | 0 | GPU offload layers |
| inference | threads | int | 8 | CPU threads |
| inference | flash_attention | bool | false | Flash attention |

---

## GPU akcelerace

### Backend srovnání

| Backend | Výkon | Složitost | Windows | Poznámka |
|---------|-------|-----------|---------|----------|
| **Vulkan** ✓ | ~62 t/s | Snadná | ✅ | Doporučeno |
| ROCm/HIP | ~96 t/s | Složitá | ❌ | Pouze Linux |
| CUDA | ~100 t/s | Střední | ✅ | Pouze NVIDIA |
| CPU | ~12 t/s | Snadná | ✅ | Fallback |

### Vulkan setup

```powershell
# Vulkan je nativně podporován ve Windows s AMD GPU
# Není potřeba žádná dodatečná instalace

# Ověření Vulkan podpory
vulkaninfo --summary

# llama.cpp automaticky detekuje Vulkan
.\bin\llama-server.exe --help | Select-String gpu
```

### GPU Layers konfigurace

```powershell
# Standardní modely (LLaMA, Mistral, Qwen)
.\start-server.ps1 -GpuLayers 99  # Všechny vrstvy na GPU

# GPT-OSS (mxfp4 tensory - není GPU podpora)
.\start-server.ps1 -GpuLayers 0   # CPU only
```

### Proč CPU pro GPT-OSS?

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         GPT-OSS TENSOR FORMAT                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  GPT-OSS-20B používá Microsoft FP4 (mxfp4) tensor format:                  │
│                                                                             │
│  Standard GGUF:     Q4_K_S, Q5_K_M, Q8_0, F16, F32                         │
│                           ↓                                                 │
│                     Full GPU support via Vulkan/CUDA                        │
│                                                                             │
│  GPT-OSS:           mxfp4 (Microsoft FP4)                                  │
│                           ↓                                                 │
│                     Limited GPU support (work in progress)                  │
│                           ↓                                                 │
│                     Falls back to CPU inference                             │
│                                                                             │
│  Důsledek: ~12 t/s místo ~62 t/s, ale stále použitelné                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## API endpointy

### OpenAI-Compatible API

| Endpoint | Method | Popis |
|----------|--------|-------|
| `/` | GET | Web UI interface |
| `/health` | GET | Health check |
| `/v1/chat/completions` | POST | Chat completions |
| `/v1/completions` | POST | Text completions |
| `/v1/embeddings` | POST | Text embeddings |
| `/v1/models` | GET | List models |

### Chat Completions

```bash
# Request
curl -X POST http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-oss-20b",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "Hello!"}
    ],
    "max_tokens": 100,
    "temperature": 0.7
  }'

# Response
{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "created": 1735654800,
  "model": "gpt-oss-20b",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hello! How can I help you today?"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 15,
    "completion_tokens": 8,
    "total_tokens": 23
  }
}
```

### Streaming

```bash
curl -X POST http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-oss-20b",
    "messages": [{"role": "user", "content": "Tell me a joke"}],
    "stream": true
  }'
```

### Health Check

```bash
curl http://localhost:8001/health

# Response
{
  "status": "ok",
  "model": "gpt-oss-20b-Q4_K_S.gguf",
  "ctx_size": 4096
}
```

---

## Spouštění a správa

### start-server.ps1

```powershell
<#
.SYNOPSIS
    Spustí llama.cpp server s nakonfigurovaným modelem.
    
.PARAMETER ModelPath
    Cesta k GGUF modelu.
    
.PARAMETER Port
    Port pro server (default: 8001).
    
.PARAMETER GpuLayers
    Počet vrstev na GPU (default: 0 pro CPU).
    
.PARAMETER ContextSize
    Velikost context window (default: 4096).
#>

param(
    [string]$ModelPath = "..\models\gpt-oss-20b-Q4_K_S.gguf",
    [int]$Port = 8001,
    [int]$GpuLayers = 0,
    [int]$ContextSize = 4096,
    [int]$Threads = 16
)

# Načtení konfigurace
$config = Get-Content "config.json" | ConvertFrom-Json

# Override z parametrů
$modelPath = if ($ModelPath) { $ModelPath } else { $config.model.path }
$port = if ($Port) { $Port } else { $config.server.port }

# Sestavení příkazu
$llamaServer = ".\bin\llama-server.exe"
$args = @(
    "--model", $modelPath,
    "--host", "127.0.0.1",
    "--port", $port,
    "--ctx-size", $ContextSize,
    "--n-gpu-layers", $GpuLayers,
    "--threads", $Threads,
    "-fit", "off"
)

Write-Host "Starting llama.cpp server..." -ForegroundColor Green
Write-Host "Model: $modelPath"
Write-Host "Port: $port"
Write-Host "GPU Layers: $GpuLayers"

# Spuštění
& $llamaServer @args
```

### Spuštění

```powershell
# Základní spuštění
cd llama-cpp-server
.\start-server.ps1

# S parametry
.\start-server.ps1 -Port 8080 -GpuLayers 99 -ContextSize 8192

# Na pozadí
Start-Process -FilePath ".\start-server.ps1" -WindowStyle Minimized
```

### Zastavení

```powershell
# Najít a ukončit proces
Get-Process llama-server | Stop-Process

# Nebo pomocí port
netstat -ano | Select-String ":8001"
Stop-Process -Id <PID>
```

---

## Integrace s llama-orchestrator

### Automatická správa

```powershell
# Inicializace instance
llama-orch init gpt-oss `
  --model "../models/gpt-oss-20b-Q4_K_S.gguf" `
  --port 8001 `
  --context-size 4096 `
  --gpu-layers 0

# Spuštění přes orchestrator
llama-orch up gpt-oss

# Monitoring
llama-orch dashboard
```

### Konfigurace pro orchestrator

```json
// llama-orchestrator/instances/gpt-oss/config.json
{
  "name": "gpt-oss",
  "model": {
    "path": "../../llama-cpp-server/../models/gpt-oss-20b-Q4_K_S.gguf",
    "context_size": 4096,
    "batch_size": 512,
    "threads": 16
  },
  "server": {
    "host": "127.0.0.1",
    "port": 8001,
    "parallel": 4
  },
  "gpu": {
    "layers": 0,
    "backend": "vulkan"
  }
}
```

---

## Troubleshooting

### Časté problémy

| Problém | Příčina | Řešení |
|---------|---------|--------|
| Model not found | Špatná cesta | Použít absolutní cestu |
| Port in use | Jiný proces | `netstat -ano \| Select-String :8001` |
| Out of memory | Velký model | Snížit context_size |
| Slow inference | CPU mode | Ověřit gpu_layers |
| Vulkan error | Chybí driver | Aktualizovat GPU driver |

### Diagnostické příkazy

```powershell
# Ověření modelu
Test-Path "..\models\gpt-oss-20b-Q4_K_S.gguf"

# Velikost modelu
(Get-Item "..\models\gpt-oss-20b-Q4_K_S.gguf").Length / 1GB

# Ověření portu
Test-NetConnection -ComputerName localhost -Port 8001

# Health check
Invoke-RestMethod http://localhost:8001/health

# Systémové zdroje
Get-Process llama-server | Select-Object CPU, WorkingSet64
```

### Testovací skript

```powershell
# test-api.ps1
$baseUrl = "http://localhost:8001"

# Health check
Write-Host "Testing health endpoint..."
try {
    $health = Invoke-RestMethod "$baseUrl/health"
    Write-Host "✓ Health: $($health.status)" -ForegroundColor Green
} catch {
    Write-Host "✗ Health check failed" -ForegroundColor Red
    exit 1
}

# Chat completion
Write-Host "Testing chat completion..."
$body = @{
    model = "gpt-oss-20b"
    messages = @(
        @{ role = "user"; content = "Say hello in one word." }
    )
    max_tokens = 10
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod "$baseUrl/v1/chat/completions" `
        -Method POST `
        -ContentType "application/json" `
        -Body $body
    
    $answer = $response.choices[0].message.content
    Write-Host "✓ Response: $answer" -ForegroundColor Green
} catch {
    Write-Host "✗ Chat completion failed: $_" -ForegroundColor Red
}
```

---

## Performance tuning

### Optimalizace pro CPU

```powershell
# Maximální CPU využití
.\start-server.ps1 `
  -Threads $env:NUMBER_OF_PROCESSORS `
  -GpuLayers 0 `
  -ContextSize 2048  # Menší context = rychlejší
```

### Optimalizace pro GPU (standardní modely)

```powershell
# Maximální GPU offload
.\start-server.ps1 `
  -ModelPath "..\models\llama-3-8b-Q4_K_M.gguf" `
  -GpuLayers 99 `
  -ContextSize 8192
```

### Memory management

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MEMORY REQUIREMENTS                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Model Size Estimates (Q4_K quantization):                                  │
│                                                                             │
│  7B params:   ~4 GB model + ~2 GB context = ~6 GB total                    │
│  13B params:  ~8 GB model + ~2 GB context = ~10 GB total                   │
│  20B params:  ~12 GB model + ~3 GB context = ~15 GB total                  │
│  70B params:  ~40 GB model + ~4 GB context = ~44 GB total                  │
│                                                                             │
│  Context memory scales with context_size:                                   │
│  - 2K context: ~0.5 GB                                                      │
│  - 4K context: ~1 GB                                                        │
│  - 8K context: ~2 GB                                                        │
│  - 32K context: ~8 GB                                                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Související dokumenty

- **Architektura:** [../architecture/ARCHITECTURE.md](../architecture/ARCHITECTURE.md)
- **Llama Orchestrator:** [LLAMA_ORCHESTRATOR.md](LLAMA_ORCHESTRATOR.md)
- **Integrace:** [../architecture/INTEGRATION.md](../architecture/INTEGRATION.md)

---

*Tato dokumentace je součástí 4-úrovňové dokumentační struktury projektu MCP Prompt Broker.*
