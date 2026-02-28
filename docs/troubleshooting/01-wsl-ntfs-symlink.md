# TS-01 — `make install` falla en WSL sobre drive de Windows

## Síntoma

```
Error: [Errno 1] Operation not permitted: 'lib' -> '.venv/lib64'
```

## Causa

```mermaid
flowchart LR
    A[python3.12 -m venv] --> B[ensure_directories]
    B --> C[os.symlink 'lib' → 'lib64']
    C --> D{NTFS soporta<br>symlinks POSIX?}
    D -- Sin metadata --> E[❌ EPERM<br>Operation not permitted]
    D -- Con metadata --> F[✅ OK]

    style E fill:#7a1e1e,color:#fff,stroke:#c0392b
    style F fill:#1a4a2a,color:#fff,stroke:#27ae60
```

**NTFS** (drives `/mnt/c/`, `/mnt/d/`, `/mnt/e/`, etc.) no soporta symlinks POSIX por defecto en WSL. Python 3.12 crea `lib64 → lib` incondicionalmente en sistemas 64-bit y no captura el `EPERM`.

## Árbol de decisión

```mermaid
flowchart TD
    START([make install]) --> DETECT{¿WSL +<br>/mnt/X/?}

    DETECT -- No --> NATIVE[python3.12 -m venv .venv]
    NATIVE --> OK1([✅ Listo])

    DETECT -- Sí --> PKG{¿python3.12-venv<br>instalado?}

    PKG -- No --> APTINSTALL["sudo apt install<br>python3.12<br>python3.12-venv<br>python3.12-dev"]
    APTINSTALL --> PKG

    PKG -- Sí --> PATCH["EnvBuilder con patch:<br>os.symlink → no-op solo para lib64<br>symlinks=False para binarios"]
    PATCH --> VENV[.venv creado sin lib64]
    VENV --> PIP[pip upgrade]
    PIP --> OK2([✅ Listo])

    style START fill:#2d2d2d,color:#eee,stroke:#555
    style OK1 fill:#1a4a2a,color:#fff,stroke:#27ae60
    style OK2 fill:#1a4a2a,color:#fff,stroke:#27ae60
    style APTINSTALL fill:#5c3a00,color:#fff,stroke:#e67e22
```

## Solución aplicada en el Makefile

```python
# El Makefile ejecuta este one-liner al detectar WSL + /mnt/X/
import venv, os
_o = os.symlink
os.symlink = lambda s, d, *a, **k: None if 'lib64' in d else _o(s, d, *a, **k)
venv.EnvBuilder(with_pip=True, symlinks=False).create('.venv')
```

**Por qué funciona:**
- `symlinks=False` → Python copia los binarios en lugar de enlazarlos (evita EPERM en `bin/`)
- El patch de `os.symlink` → solo silencia el symlink `lib64 → lib`, el único que falla en NTFS
- `with_pip=True` → usa `ensurepip` (incluido en `python3.12-venv`) sin necesitar pip del sistema

## Alternativa permanente — habilitar symlinks en WSL

```mermaid
flowchart LR
    A["Editar /etc/wsl.conf"] --> B["[automount]<br>options = 'metadata'"]
    B --> C["wsl --shutdown<br>en PowerShell"]
    C --> D["Abrir WSL nuevamente"]
    D --> E["✅ Symlinks habilitados<br>en todos los drives Windows"]

    style E fill:#1a4a2a,color:#fff,stroke:#27ae60
```

```ini
# /etc/wsl.conf
[automount]
options = "metadata"
```

---

← [Índice de troubleshooting](index.md)
