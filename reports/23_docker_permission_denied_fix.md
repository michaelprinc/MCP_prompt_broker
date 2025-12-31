# Docker Permission Denied Fix

> **Generated:** 2025-12-31  
> **Complexity:** Medium  
> **Status:** ✅ FIXED  
> **Error:** `Permission denied` při zápisu do working_dir

---

## Analýza problému

### Symptom
```
/bin/bash: line 1: /workspace/example/sklearn_toy_model/data.py: Permission denied
```

### Log analýza
```
drwxr-xr-x 1 root root 512 Dec 31 20:22 /workspace/example/sklearn_toy_model
```

- **Vlastník:** `root:root`
- **Oprávnění:** `755` (rwxr-xr-x)
- **Kontejner běží jako:** `node` (UID 1000)
- **Výsledek:** `node` nemá právo zapisovat do adresáře

### Root Cause
Na Windows + Docker Desktop je volume mounting komplexní:
1. Windows souborový systém nemá skutečné UNIX permissions
2. Docker Desktop překládá oprávnění a často nastaví `root:root` jako vlastníka
3. Podadresáře mohou mít různá oprávnění podle toho, jak byly vytvořeny

Když hlavní workspace má `777` (rwxrwxrwx), ale podadresáře mají `755` (rwxr-xr-x), kontejner běžící jako `node` nemůže zapisovat do podadresářů.

---

## Možná řešení

### Řešení 1: Spustit kontejner jako root (DOPORUČENO pro Windows)
```python
container = self.client.containers.run(
    image=self.image,
    user="root",  # ← Přidat user="root" 
    # ...
)
```

**Výhody:**
- Jednoduché, funguje na Windows/Docker Desktop
- Žádné změny v Dockerfile

**Nevýhody:**
- Kontejner běží jako root (menší izolace)
- Na Linux by to mohlo vytvářet soubory vlastněné rootem

### Řešení 2: Dynamicky nastavit UID kontejneru podle hosta
```python
import os
if os.name != 'nt':  # Linux/Mac
    user = f"{os.getuid()}:{os.getgid()}"
else:  # Windows
    user = "root"

container = self.client.containers.run(
    user=user,
    # ...
)
```

**Výhody:**
- Na Linuxu zachová správná oprávnění
- Na Windows funguje jako root

### Řešení 3: Upravit Dockerfile pro běh jako root
```dockerfile
# Zakomentovat nebo odstranit:
# USER node
```

**Nevýhody:**
- Vyžaduje rebuild image
- Snižuje bezpečnost

### Řešení 4: Změnit oprávnění v init scriptu
```dockerfile
COPY entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
```
Entrypoint script by nastavil `chmod -R 777 /workspace` před spuštěním Codex.

---

## Doporučený implementační plán

### Fáze 1: Quick Fix v docker_client.py

**Změna:** Přidat parametr `user="root"` do `containers.run()`.

Pro Windows/Docker Desktop je to nejjednodušší řešení, protože:
1. Docker Desktop stejně překládá oprávnění přes CIFS/SMB
2. Soubory vytvořené v kontejneru budou přístupné na Windows
3. Bezpečnostní riziko je minimální (izolace zajištěna kontejnerem)

### Fáze 2 (volitelně): Inteligentní detekce OS

Pro cross-platform podporu přidat detekci OS a nastavit UID dynamicky.

---

## Změny k implementaci

| Soubor | Změna |
|--------|-------|
| `docker_client.py` | ✅ Přidána dynamická detekce OS a nastavení `user` parametru |

---

## Implementovaný kód

```python
# Determine user for container execution
# On Windows/Docker Desktop, run as root to avoid permission issues
if os.name == "nt":
    container_user = "root"
else:
    # On Linux/Mac, run as current user's UID:GID for proper permissions
    container_user = f"{os.getuid()}:{os.getgid()}"

container = self.client.containers.run(
    # ...
    user=container_user,  # FIX: Set user for proper permissions
    # ...
)
```

---

## Akceptační kritéria

- [x] Codex CLI může zapisovat do libovolného podadresáře workspace
- [x] Windows: Kontejner běží jako root
- [x] Linux/Mac: Kontejner běží jako aktuální uživatel
- [x] Logování informuje o zvoleném user módu
- [x] Syntax check bez chyb
