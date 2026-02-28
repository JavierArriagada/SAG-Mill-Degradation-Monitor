# Troubleshooting — SAG Monitor

> Los diagramas Mermaid se renderizan en GitHub, VS Code (extensión Markdown Preview Mermaid), y Obsidian.

---

## 1. `make install` falla en WSL sobre drive de Windows

### Síntoma

```
Error: [Errno 1] Operation not permitted: 'lib' -> '.venv/lib64'
```

### Causa

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

### Árbol de decisión

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

### Solución aplicada en el Makefile

```python
# El Makefile ejecuta este one-liner al detectar WSL + /mnt/X/
import venv, os
_o = os.symlink
os.symlink = lambda s, d, *a, **k: None if 'lib64' in d else _o(s, d, *a, **k)
venv.EnvBuilder(with_pip=True, symlinks=False).create('.venv')
```

**Porqué funciona:**
- `symlinks=False` → Python copia los binarios en lugar de enlazarlos (evita EPERM en `bin/`)
- El patch de `os.symlink` → solo silencia el symlink `lib64 → lib`, el único que falla en NTFS
- `with_pip=True` → usa `ensurepip` (incluido en `python3.12-venv`) sin necesitar pip del sistema

### Alternativa permanente — habilitar symlinks en WSL

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

## 2. `python3.12: No module named pip`

### Síntoma

```
/usr/bin/python3.12: No module named pip
```

### Causa y solución

```mermaid
flowchart TD
    A[python3.12 -m pip] --> B{¿python3.12-venv<br>instalado?}
    B -- No --> C["sudo apt install<br>python3.12-venv"]
    C --> B
    B -- Sí --> D{¿Aun falla<br>ensurepip?}
    D -- Sí --> E["Ubuntu deshabilita ensurepip<br>por política EXTERNALLY_MANAGED"]
    E --> F["Solución del Makefile:<br>EnvBuilder con with_pip=True<br>(usa ensurepip interno,<br>no el del sistema)"]
    F --> G([✅ OK])
    D -- No --> G

    style G fill:#1a4a2a,color:#fff,stroke:#27ae60
    style E fill:#5c3a00,color:#fff,stroke:#e67e22
```

En Ubuntu, `python3.12` desde apt **no incluye pip** como módulo del sistema. La solución del Makefile usa `venv.EnvBuilder(with_pip=True)` que llama a `ensurepip` internamente (distinto al `python3.12 -m ensurepip` del sistema, que sí puede estar bloqueado).

---

## 3. `make install` falla con error de permisos en pip upgrade

### Síntoma

```
ERROR: Could not install packages due to an OSError
```

### Diagnóstico

```mermaid
flowchart TD
    A[pip upgrade falla] --> B{¿.venv existe<br>y es válido?}
    B -- No --> C[make clean-all && make install]
    B -- Sí --> D{¿pip apunta<br>al venv?}
    D -- No --> E["which pip<br>Debe ser .venv/bin/pip"]
    E --> F[source .venv/bin/activate]
    F --> G([✅ OK])
    D -- Sí --> H{¿Drive NTFS<br>con permisos?}
    H -- Sí --> I["chmod -R u+w .venv"]
    I --> J[make install]
    J --> G

    style G fill:#1a4a2a,color:#fff,stroke:#27ae60
```

---

## 4. Docker build falla localmente

### Síntoma

```
ERROR [internal] load metadata for docker.io/library/python:3.12-slim
```
o
```
permission denied while trying to connect to the Docker daemon
```

### Árbol de diagnóstico

```mermaid
flowchart TD
    A[make docker-build falla] --> B{¿Docker instalado?}
    B -- No --> C["sudo apt install<br>docker.io docker-compose-plugin"]
    C --> D["sudo usermod -aG docker $USER<br>+ cerrar y reabrir sesión"]
    D --> A

    B -- Sí --> E{¿Error de<br>permisos al socket?}
    E -- Sí --> D

    E -- No --> F{¿Error de<br>conexión/red?}
    F -- Sí --> G["docker pull python:3.12-slim<br>para verificar conectividad"]
    G --> H{¿Falla pull?}
    H -- Sí --> I["Verificar proxy / DNS en WSL<br>/etc/resolv.conf"]
    H -- No --> J[make docker-build]
    J --> K([✅ OK])

    F -- No --> L["docker build -t test . --no-cache<br>para ver el error completo"]

    style K fill:#1a4a2a,color:#fff,stroke:#27ae60
    style C fill:#5c3a00,color:#fff,stroke:#e67e22
    style D fill:#5c3a00,color:#fff,stroke:#e67e22
```

---

## 5. La app arranca pero muestra pantalla en blanco

### Síntoma

`make run` ejecuta sin errores pero `http://localhost:8050` no muestra nada.

### Diagnóstico

```mermaid
flowchart TD
    A[Pantalla en blanco] --> B{¿.env existe?}
    B -- No --> C[make env]
    C --> D[make run]

    B -- Sí --> E{¿Puerto 8050<br>disponible?}
    E -- No --> F["lsof -i :8050<br>kill -9 PID"]
    F --> D

    E -- Sí --> G{¿Logs de error<br>en terminal?}
    G -- Sí --> H["Ver traza completa<br>e identificar módulo que falla"]
    G -- No --> I["Abrir DevTools del navegador<br>Consola → errores JS"]

    D --> J([✅ Recargar http://localhost:8050])

    style J fill:#1a4a2a,color:#fff,stroke:#27ae60
    style C fill:#5c3a00,color:#fff,stroke:#e67e22
    style F fill:#5c3a00,color:#fff,stroke:#e67e22
```

---

## 6. CI falla en GitHub Actions

### Anatomía del pipeline y puntos de falla

```mermaid
flowchart LR
    PUSH([git push<br>main]) --> Q

    subgraph Q [quality]
        Q1[ruff lint] --> Q2[ruff format --check] --> Q3[mypy]
    end

    subgraph T [test]
        T1[pytest --cov]
    end

    subgraph DO [docker]
        D1[docker build :ci]
    end

    subgraph DEP [deploy — solo main]
        DEP1[doctl apps<br>create-deployment]
    end

    Q -->|quality passed| T
    T -->|test passed| DO
    DO -->|docker passed| DEP
    DEP --> APP([✅ DigitalOcean<br>App Platform])

    Q -.->|falla| FQ([❌ No se avanza])
    T -.->|falla| FT([❌ No se deploya])
    DO -.->|falla| FD([❌ No se deploya])

    style PUSH fill:#2d2d2d,color:#eee,stroke:#555
    style APP fill:#1a4a2a,color:#fff,stroke:#27ae60
    style FQ fill:#7a1e1e,color:#fff,stroke:#c0392b
    style FT fill:#7a1e1e,color:#fff,stroke:#c0392b
    style FD fill:#7a1e1e,color:#fff,stroke:#c0392b
```

### Errores comunes

| Error en CI | Causa más probable | Solución |
|---|---|---|
| `ruff check` falla | Código sin formatear | `make format` y hacer commit |
| `mypy` falla | Error de tipos | `make typecheck` localmente para ver detalle |
| `pytest` falla | Test roto o import faltante | `make test` localmente |
| `docker build` falla | `requirements.txt` incompatible | Probar `make docker-build` local |
| `doctl` falla | Secret `DIGITALOCEAN_ACCESS_TOKEN` ausente o expirado | Renovar token en DO y actualizar en GitHub Secrets |

---

## Referencia rápida de comandos de diagnóstico

```bash
# Verificar entorno
python3.12 --version
python3.12 -c "import venv; print('venv OK')"
which pip                        # debe ser .venv/bin/pip

# Entorno WSL
cat /proc/version                # muestra si es WSL
pwd                              # debe ser /mnt/X/... si estás en drive Windows
ls -la .venv/lib/                # verificar que lib existe
ls -la .venv/lib64 2>/dev/null   # normalmente no existe en WSL+NTFS (OK)

# Docker
docker version
docker compose version
groups | grep docker             # debe aparecer 'docker'

# CI local
make check                       # lint + format + types + tests
make docker-build                # validar Dockerfile localmente
```
