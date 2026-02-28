# TS-04 — Docker build falla localmente

## Síntoma

```
ERROR [internal] load metadata for docker.io/library/python:3.12-slim
```
o
```
permission denied while trying to connect to the Docker daemon
```

## Árbol de diagnóstico

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

← [Índice de troubleshooting](index.md)
