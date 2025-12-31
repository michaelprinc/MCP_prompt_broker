# Security Modes Documentation

MCP Codex Orchestrator v2.0 zavádí tři úrovně bezpečnostních režimů pro kontrolu přístupu Codex CLI k souborovému systému a síti.

## Přehled Security Modes

| Mode | Čtení | Zápis workspace | Zápis mimo workspace | Síť |
|------|-------|-----------------|---------------------|-----|
| `readonly` | ✅ | ❌ | ❌ | ❌ |
| `workspace_write` | ✅ | ✅ | ❌ | ✅ |
| `full_access` | ✅ | ✅ | ✅ | ✅ |

## Detailní popis

### 1. READONLY Mode

**Použití:** Analýza kódu, code review, generování dokumentace

```json
{
  "prompt": "Analyzuj tento kód a navrhni vylepšení",
  "security_mode": "readonly"
}
```

**Docker flags:**
- `--read-only`: Filesystem je read-only
- `--network=none`: Žádný přístup k síti
- Volumes jsou mountovány jako `:ro`

**Omezení:**
- Codex nemůže vytvářet ani měnit soubory
- Nemůže stahovat závislosti
- Nemůže komunikovat s API

**Best for:**
- Code review a analýza
- Generování reportů (uloženy do stdout)
- Bezpečné testování promptů

### 2. WORKSPACE_WRITE Mode (Default)

**Použití:** Standardní vývoj, implementace features

```json
{
  "prompt": "Implementuj validaci emailových adres",
  "security_mode": "workspace_write"
}
```

**Docker flags:**
- Workspace je writable
- Ostatní adresáře jsou read-only
- Síť je povolena

**Omezení:**
- Může zapisovat pouze do workspace adresáře
- Nemůže modifikovat systémové soubory
- Nemůže zapisovat do `/etc`, `/usr`, atd.

**Best for:**
- Běžný vývoj
- Implementace nových features
- Opravy bugů

### 3. FULL_ACCESS Mode

**Použití:** Instalace závislostí, konfigurace prostředí

```json
{
  "prompt": "Nainstaluj a nakonfiguruj pytest",
  "security_mode": "full_access"
}
```

**Docker flags:**
- Plný přístup k filesystemu
- Plný přístup k síti
- Privilegovaný mód (volitelně)

**⚠️ Varování:**
- Používejte pouze když je to nezbytné
- Vždy verifikujte změny před commitem
- Doporučeno s `verify: true`

**Best for:**
- Instalace závislostí
- Konfigurace dev prostředí
- Komplexní refactoring

---

## Implementace

### Python API

```python
from mcp_codex_orchestrator.security.modes import SecurityMode, get_security_flags

# Získání Docker flags pro daný mode
flags = get_security_flags(SecurityMode.WORKSPACE_WRITE)
# ['--tmpfs', '/tmp', '-v', '/workspace:/workspace']
```

### Docker konfigurace

```python
from mcp_codex_orchestrator.security.sandbox import SandboxEnforcer

enforcer = SandboxEnforcer()

# Validace mode pro danou operaci
if enforcer.validate_mode(SecurityMode.READONLY, operation="write"):
    raise SecurityError("READONLY mode does not allow writes")

# Získání Docker konfigurce
config = enforcer.get_docker_config(SecurityMode.WORKSPACE_WRITE)
# {
#     "read_only": False,
#     "network_mode": "bridge",
#     "volumes": {...},
#     "security_opt": [...]
# }
```

---

## Sandbox Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Docker Container                      │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐              │
│  │   /workspace    │  │     /runs       │              │
│  │   (writable*)   │  │   (writable)    │              │
│  └─────────────────┘  └─────────────────┘              │
│                                                         │
│  ┌─────────────────┐  ┌─────────────────┐              │
│  │   /schemas      │  │   /home/codex   │              │
│  │   (read-only)   │  │   (read-only*)  │              │
│  └─────────────────┘  └─────────────────┘              │
├─────────────────────────────────────────────────────────┤
│  Network: bridge | none (based on security_mode)        │
└─────────────────────────────────────────────────────────┘

* Závisí na security_mode
```

---

## Patch Workflow

Pro bezpečné aplikování změn v `readonly` nebo `workspace_write` módu:

```python
from mcp_codex_orchestrator.security.patch_workflow import PatchWorkflow

workflow = PatchWorkflow(workspace_path="/path/to/workspace")

# 1. Generování patche (v readonly módu)
patch = await workflow.generate_patch(changes)

# 2. Preview změn
preview = await workflow.preview_patch(patch)
print(preview)

# 3. Aplikování patche (vyžaduje potvrzení)
result = await workflow.apply_patch(patch)

# 4. Případný rollback
if not result.success:
    await workflow.revert_patch(patch)
```

---

## Best Practices

### 1. Výchozí mód

Vždy začněte s `workspace_write` a přepněte na jiný pouze když je to potřeba:

```json
{
  "security_mode": "workspace_write",
  "verify": true
}
```

### 2. Verify Loop

Vždy povolte verify loop pro `full_access` mód:

```json
{
  "security_mode": "full_access",
  "verify": true
}
```

### 3. Izolace workspace

Používejte samostatný workspace pro experimentální úlohy:

```bash
mkdir /tmp/sandbox-workspace
export WORKSPACE_PATH=/tmp/sandbox-workspace
```

### 4. Audit log

Všechny operace jsou logovány v `runs/{run_id}/log.txt`:

```bash
cat runs/abc123/log.txt | grep "file_change"
```

---

## Troubleshooting

### "Permission denied" v readonly módu

**Příčina:** Codex se pokouší zapisovat v readonly módu

**Řešení:**
```json
{
  "security_mode": "workspace_write"
}
```

### "Network unreachable" 

**Příčina:** Síť je zakázána v readonly módu

**Řešení:**
```json
{
  "security_mode": "workspace_write"
}
```

### Změny se neukládají

**Příčina:** Volumes nejsou správně namountovány

**Řešení:**
1. Ověřte, že WORKSPACE_PATH existuje a je přístupný
2. Ověřte oprávnění:
   ```bash
   ls -la $WORKSPACE_PATH
   ```

---

## Reference

- [Docker Security Best Practices](https://docs.docker.com/develop/security-best-practices/)
- [Linux Capabilities](https://man7.org/linux/man-pages/man7/capabilities.7.html)
- [MCP Codex Orchestrator README](../README.md)
