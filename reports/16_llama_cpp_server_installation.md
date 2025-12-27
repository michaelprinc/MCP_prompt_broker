# Report: Instalace llama.cpp serveru s AMD GPU akcelerací

**Datum**: 2025-12-26  
**Stav**: ✅ DOKONČENO

## Shrnutí

Byl úspěšně nainstalován a nakonfigurován llama.cpp server pro model GPT-OSS-20B s OpenAI-kompatibilním API na portu 8001.

## Komponenty

### Nainstalované soubory

```
llama-cpp-server/
├── README.md              # Dokumentace
├── config.json            # Konfigurační šablona
├── start-server.ps1       # Automatizovaný spouštěcí skript
├── test-api.ps1           # Testovací skript pro API
└── bin/                   # llama.cpp binárky (b7548)
    ├── llama-server.exe   # Hlavní server
    ├── ggml-vulkan.dll    # Vulkan backend
    ├── llama.dll          # Hlavní knihovna
    └── ...                # Další DLL
```

### Model

- **Soubor**: `models/gpt-oss-20b-Q4_K_S.gguf`
- **Velikost**: 10.81 GB
- **Architektura**: GPT-OSS (MoE - Mixture of Experts)
- **Parametry**: 20.91B
- **Kvantizace**: Q4_K_S (4.44 bits per weight)
- **Experti**: 32 (4 aktivní)

## Technické detaily

### Hardware

- **CPU**: AMD Ryzen (16 vláken)
- **GPU**: AMD Radeon RX 6800 (RDNA 2, 16 GB VRAM)
- **Vulkan**: Podporován

### Omezení

Model GPT-OSS používá **mxfp4 tensory** (Microsoft FP4 format), které zatím nemají plnou podporu pro GPU offloading ve Vulkan backendu. Server proto běží na **CPU only**, což poskytuje:

- Prompt processing: ~17 tokenů/s
- Generování: ~12 tokenů/s

Pro standardní modely (LLaMA, Mistral, Qwen) by Vulkan backend poskytl ~60 t/s.

### Konfigurace serveru

| Parametr | Hodnota |
|----------|---------|
| Host | 127.0.0.1 |
| Port | 8001 |
| Context | 4096 tokens |
| GPU layers | 0 (CPU) |
| Threads | 16 |
| Parallel slots | 4 |

## API Endpoints

| Endpoint | Popis |
|----------|-------|
| `GET /health` | Health check |
| `GET /v1/models` | Seznam modelů |
| `POST /v1/chat/completions` | Chat API (OpenAI-compatible) |
| `POST /v1/completions` | Text completion |

### Příklad použití

```powershell
# Health check
Invoke-RestMethod -Uri "http://127.0.0.1:8001/health"
# Výstup: {"status":"ok"}

# Chat completion
$body = @{
    model = "gpt-oss-20b"
    messages = @(@{ role = "user"; content = "Hello!" })
    max_tokens = 100
} | ConvertTo-Json -Depth 3

Invoke-RestMethod -Uri "http://127.0.0.1:8001/v1/chat/completions" `
    -Method POST -Body $body -ContentType "application/json"
```

## Spuštění

### Automatické (doporučeno)

```powershell
cd llama-cpp-server
.\start-server.ps1
```

### Manuální

```powershell
cmd /c start /min "" "llama-cpp-server\bin\llama-server.exe" `
    --model "models\gpt-oss-20b-Q4_K_S.gguf" `
    --host 127.0.0.1 --port 8001 `
    --ctx-size 4096 --n-gpu-layers 0 `
    -fit off --threads 16
```

## Problémy a řešení

### GPU offloading selhává

**Příčina**: GPT-OSS model obsahuje mxfp4 tensory, které nejsou plně podporované ve Vulkan backendu.

**Řešení**: Použijte `--n-gpu-layers 0` a `-fit off`.

### Server padá při startu

**Příčina**: Automatické přizpůsobení paměti (`-fit on`) způsobuje pád.

**Řešení**: Přidejte `-fit off`.

## Další kroky

1. **Budoucí GPU podpora**: Sledovat aktualizace llama.cpp pro podporu mxfp4 tensorů na Vulkan
2. **Alternativní model**: Pro plnou GPU akceleraci zvážit standardní model (např. LLaMA 3, Qwen)
3. **ROCm/HIP**: Pro maximální výkon na AMD GPU zvážit instalaci ROCm SDK a použití HIP backendu

## Verze

- **llama.cpp**: b7548 (prosinec 2025)
- **Backend**: Vulkan
- **Zdroj**: https://github.com/ggml-org/llama.cpp
