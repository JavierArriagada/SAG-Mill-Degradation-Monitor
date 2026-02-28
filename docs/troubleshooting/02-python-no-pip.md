# TS-02 — `python3.12: No module named pip`

## Síntoma

```
/usr/bin/python3.12: No module named pip
```

## Causa y solución

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

← [Índice de troubleshooting](index.md)
