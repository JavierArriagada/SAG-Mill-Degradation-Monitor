# TS-03 — `make install` falla con error de permisos en pip upgrade

## Síntoma

```
ERROR: Could not install packages due to an OSError
```

## Diagnóstico

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

← [Índice de troubleshooting](index.md)
