# Guía de desarrollo — SAG Monitor

Dos flujos de trabajo según el entorno disponible:

| Flujo | Cuándo usarlo |
|---|---|
| **[Nativo (venv)](#flujo-nativo-venv)** | Ubuntu, WSL2 con Ubuntu, macOS |
| **[Docker](#flujo-docker)** | Windows sin WSL, cualquier OS con Docker instalado |

---

## Flujo nativo (venv)

### Requisitos previos

- Python 3.12
- `make`

### Setup inicial (una sola vez)

```bash
git clone <repo>
cd SAG-Mill-Degradation-Monitor
make install-dev   # crea .venv e instala todas las dependencias
make env           # crea .env desde .env.example
```

### Ciclo de desarrollo diario

```bash
make run           # levanta el servidor Dash con hot-reload en http://localhost:8050
```

En otra terminal, mientras desarrollás:

```bash
make test-watch    # corre tests automáticamente al guardar archivos (Ctrl+C para salir)
```

### Verificación de calidad antes de commitear

```bash
make format        # formatea el código con ruff
make check         # lint + format-check + typecheck + tests (suite completa)
```

### Comandos de referencia rápida

| Comando | Acción |
|---|---|
| `make run` | Servidor dev con hot-reload |
| `make test` | Corre tests una vez |
| `make test-watch` | Tests en modo watch |
| `make test-cov` | Tests con reporte de cobertura |
| `make format` | Formatea código |
| `make lint` | Solo linting |
| `make typecheck` | Solo mypy |
| `make check` | Suite completa de calidad |
| `make clean` | Limpia caches y artefactos |
| `make clean-all` | Limpia caches + elimina `.venv` |

---

## Flujo Docker

Para equipos sin Ubuntu/WSL o cuando se quiere un entorno idéntico al de producción.

### Requisitos previos

```bash
# Ubuntu / WSL
sudo apt install -y docker.io docker-compose-v2
sudo usermod -aG docker $USER
newgrp docker
sudo service docker start   # WSL no tiene systemd; correr en cada sesión

# Windows (sin WSL)
# → Instalar Docker Desktop: https://www.docker.com/products/docker-desktop/
```

### Setup inicial (una sola vez)

```bash
git clone <repo>
cd SAG-Mill-Degradation-Monitor
make docker-build   # construye la imagen local sag-monitor:local
```

### Levantar y operar

```bash
make docker-up      # levanta el stack en background → http://localhost:8050
make docker-logs    # ver logs en tiempo real
make docker-down    # detiene y elimina los containers
```

### Iterar con cambios de código

Cada vez que modificás código fuente, reconstruí la imagen:

```bash
make docker-down
make docker-build
make docker-up
```

> **Tip:** Para desarrollo iterativo activo, el flujo nativo (venv) es más cómodo.
> Docker es ideal para validar el build final o cuando no se puede instalar Python localmente.

### Acceder al container

```bash
make docker-shell   # abre /bin/sh dentro del container en ejecución
```

### Persistencia de datos

El `docker-compose.yml` monta el volumen `sag_data` sobre `/app`.
La base SQLite (`sag_monitor.db`) sobrevive reinicios del container.

Para resetear la base de datos:

```bash
make docker-down
docker volume rm sag-mill-degradation-monitor_sag_data
make docker-up
```

### Comandos de referencia rápida

| Comando | Acción |
|---|---|
| `make docker-build` | Construye la imagen |
| `make docker-up` | Levanta el stack (detached) |
| `make docker-down` | Detiene y elimina containers |
| `make docker-logs` | Tail de logs del container |
| `make docker-shell` | Shell interactivo dentro del container |

---

## Tests en ambos flujos

Los tests siempre se corren en el entorno nativo (no dentro de Docker):

```bash
make test           # rápido, una pasada
make test-watch     # modo watch durante desarrollo (solo flujo nativo)
make test-cov       # con cobertura → htmlcov/index.html
```

---

## Estructura de entornos

```
┌─────────────────────────────────────────────────────┐
│  Desarrollo nativo (venv)                           │
│  .venv/ → dependencias                              │
│  app.py → servidor Dash con DEBUG=true              │
│  Puerto: http://localhost:8050                      │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│  Docker local                                       │
│  sag-monitor:local → imagen con gunicorn            │
│  sag_data volume → SQLite persistente               │
│  Puerto: http://localhost:8050                      │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│  Producción (DigitalOcean App Platform)             │
│  Deploy automático via GitHub Actions               │
│  Ver: deployment.md                                 │
└─────────────────────────────────────────────────────┘
```

---

← [Documentación principal](index.md) | [Troubleshooting](troubleshooting/index.md)
