# TS-06 — CI falla en GitHub Actions

## Anatomía del pipeline y puntos de falla

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

## Errores comunes

| Error en CI | Causa más probable | Solución |
|---|---|---|
| `ruff check` falla | Código sin formatear o imports desordenados | `make format && make lint` y hacer commit |
| `mypy` falla | Error de tipos | `make typecheck` localmente para ver detalle |
| `pytest` falla | Test roto o import faltante | `make test` localmente |
| `docker build` falla | `requirements.txt` incompatible | Probar `make docker-build` local |
| `doctl` falla | Secret `DIGITALOCEAN_ACCESS_TOKEN` ausente o expirado | Renovar token en DO y actualizar en GitHub Secrets |

---

← [Índice de troubleshooting](index.md)
