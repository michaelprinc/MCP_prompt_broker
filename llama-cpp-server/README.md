# llama.cpp Server pro MCP Prompt Broker

Tato složka obsahuje konfiguraci a skripty pro spuštění lokálního llama.cpp serveru s AMD GPU akcelerací.

## ✅ Stav: FUNKČNÍ

- **Model**: GPT-OSS-20B Q4_K_S (10.81 GB)
- **Port**: 8001
- **Backend**: Vulkan (CPU inference kvůli mxfp4 tensorům)
- **Výkon**: ~12 tokenů/s generování, ~17 tokenů/s prompt

## Rychlý start

```powershell
# Přejděte do složky
cd llama-cpp-server

# První spuštění - automaticky stáhne llama.cpp s Vulkan backendem
.\start-server.ps1

# Nebo rychlé spuštění (server již nainstalován)
cmd /c start /min "" "bin\llama-server.exe" --model "..\models\gpt-oss-20b-Q4_K_S.gguf" --host 127.0.0.1 --port 8001 --ctx-size 4096 --n-gpu-layers 0 -fit off --threads 16
```

## AMD GPU akcelerace

### Aktuální stav: CPU inference

Model GPT-OSS-20B používá architekturu s **mxfp4 tensory** (Microsoft FP4 format), které zatím **nemají plnou podporu** ve Vulkan backendu. Server proto běží na CPU, což je stále použitelné (~12 t/s).

### Doporučený backend: Vulkan

Pro **AMD RDNA 2** (RX 6000 série) na **Windows** je **Vulkan** backend nejlepší volba:

| Backend | Výkon | Složitost | Poznámka |
|---------|-------|-----------|----------|
| **Vulkan** ✓ | ~62 t/s* | Snadná | Doporučeno pro Windows |
| ROCm/HIP | ~96 t/s* | Složitá | Vyžaduje ROCm SDK, lepší na Linux |
| CPU | ~12 t/s | Snadná | Aktuálně používáno pro GPT-OSS |

*\* Pro standardní modely (LLaMA, Mistral, Qwen). GPT-OSS má specifické tensory.*

**Proč Vulkan?**
- Nativní podpora ve Windows bez dodatečné instalace
- Automaticky využije AMD GPU
- Jednoduchá konfigurace a správa
- Stabilní a otestovaný

## Konfigurace

Upravte `config.json` pro změnu nastavení:

```json
{
    "server": {
        "host": "127.0.0.1",
        "port": 8001
    },
    "model": {
        "path": "../models/gpt-oss-20b-Q4_K_S.gguf",
        "context_size": 4096,
        "gpu_layers": 0
    }
}
```

### Klíčové parametry

| Parametr | Popis | Výchozí |
|----------|-------|---------|
| `port` | Port serveru | 8001 |
| `path` | Cesta k modelu (.gguf) | GPT-OSS-20B |
| `context_size` | Max velikost kontextu | 4096 |
| `gpu_layers` | Počet vrstev na GPU (0 = CPU) | 0 |
| `threads` | Počet CPU vláken | 16 |

## Použití s jiným modelem

```powershell
# Změna modelu přes parametr
.\start-server.ps1 -ModelPath "..\models\jiný-model.gguf"

# Změna portu
.\start-server.ps1 -Port 8080

# S GPU akcelerací (pro standardní modely)
.\start-server.ps1 -ModelPath "..\models\llama-3.gguf" -GpuLayers 99
```

## API Endpointy

Po spuštění serveru jsou dostupné:

| Endpoint | Popis |
|----------|-------|
| `http://localhost:8001/` | Webové rozhraní |
| `http://localhost:8001/v1/chat/completions` | OpenAI-compatible chat API |
| `http://localhost:8001/v1/completions` | OpenAI-compatible completions |
| `http://localhost:8001/health` | Health check |

### Příklad volání API

```powershell
# Test health endpoint
Invoke-RestMethod -Uri "http://localhost:8001/health"

# Chat completion
$body = @{
    model = "gpt-oss-20b"
    messages = @(
        @{ role = "user"; content = "Hello, how are you?" }
    )
    max_tokens = 100
} | ConvertTo-Json -Depth 3

Invoke-RestMethod -Uri "http://localhost:8001/v1/chat/completions" -Method Post -Body $body -ContentType "application/json"
```

## Struktura souborů

```
llama-cpp-server/
├── README.md           # Tento soubor
├── config.json         # Hlavní konfigurace
├── start-server.ps1    # Spouštěcí skript
├── test-api.ps1        # Testovací skript
└── bin/                # llama.cpp binárky (b7548)
    ├── llama-server.exe
    ├── ggml-vulkan.dll
    └── ...
```

## Troubleshooting

### GPT-OSS model padá s GPU layery

Tento model používá mxfp4 tensory, které nemají plnou GPU podporu. Řešení:
- Použijte `-ngl 0` nebo `gpu_layers: 0`
- Přidejte `-fit off`

### Model se nenačítá na GPU (pro jiné modely)

1. Zkontrolujte, že máte aktuální AMD ovladače
2. Ověřte Vulkan podporu: `vulkaninfo`
3. Zkuste snížit `gpu_layers` nebo `context_size`

### Out of Memory

Model GPT-OSS 20B Q4_K_S vyžaduje přibližně:
- ~12 GB RAM pro CPU inference
- Pro GPU inference potřeba ~12 GB VRAM

### Server neodpovídá

1. Zkontrolujte, že port 8001 není obsazený: `netstat -an | findstr 8001`
2. Ověřte firewall nastavení
3. Zkuste `http://127.0.0.1:8001` místo `localhost`

## Hardware detekován

```
AMD Radeon RX 6800 (RDNA 2)
- Vulkan: ✓
- VRAM: 16 GB
- Device ID: 1 (diskrétní GPU)
```

## Zdroje

- [llama.cpp GitHub](https://github.com/ggml-org/llama.cpp)
- [llama.cpp Server Documentation](https://github.com/ggml-org/llama.cpp/tree/master/tools/server)
- [AMD GPUs Guide](https://llm-tracker.info/howto/AMD-GPUs)
