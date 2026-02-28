# TS-05 — La app arranca pero muestra pantalla en blanco

## Síntoma

`make run` ejecuta sin errores pero `http://localhost:8050` no muestra nada.

## Diagnóstico

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

← [Índice de troubleshooting](index.md)
