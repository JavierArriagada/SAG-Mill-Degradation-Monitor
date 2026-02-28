# SAG Monitor

**Dashboard de mantenimiento predictivo en tiempo real para flotas de molienda minera.**

Monitorea continuamente el estado de Molinos SAG y de Bolas, calcula un Índice de Salud compuesto (ISO 10816 / ISO 13381), estima la Vida Útil Remanente (RUL) y genera alertas automáticas — todo desde un navegador, sin infraestructura adicional.

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Dash](https://img.shields.io/badge/Dash-2.18-00BFB3?logo=plotly&logoColor=white)
![CI](https://github.com/tu-usuario/sag-monitor/actions/workflows/ci.yml/badge.svg)
![License](https://img.shields.io/badge/license-MIT-green)

---

## Características principales

| Módulo | Detalle |
|---|---|
| **Resumen ejecutivo** | KPIs de flota, gauges de salud en tiempo real, alertas recientes |
| **Vista por equipo** | Series temporales de 7 variables sensoriales con umbrales dinámicos |
| **Gestión de alertas** | Filtrado por severidad / equipo / estado, acuse de recibo |
| **Tendencias históricas** | 90 días de historia, Z-score por variable, overlay de anomalías |
| **Actualización automática** | Nuevas lecturas cada 30 segundos sin recargar la página |
| **Bilingüe** | Interfaz completa en Español e Inglés (configurable) |

---

## Motor analítico

### Índice de Salud (HI · 0–100)

El HI es un escalar compuesto que sigue la guía de ISO 13381 para monitoreo de condición:

```
HI = 0.30 · S_vibración  +  0.25 · S_térmica  +  0.20 · S_presión  +  0.25 · S_potencia
```

| Sub-índice | Variable | Norma de referencia |
|---|---|---|
| S_vibración | Vibración (mm/s RMS) | ISO 10816 — Zonas A/B/C/D |
| S_térmica | Temperatura cojinete (°C) | Umbrales por equipo |
| S_presión | Presión hidráulica (bar) | Rango operativo nominal |
| S_potencia | Potencia consumida (kW) | ±5 % de nominal |

### Zonas ISO 10816 — Molino SAG

| Zona | Vibración (mm/s) | Estado |
|---|---|---|
| A | ≤ 2.3 | Nuevo / Óptimo |
| B | ≤ 4.5 | Aceptable largo plazo |
| C | ≤ 7.1 | Insatisfactorio (corto plazo) |
| D | > 7.1 | Peligro — riesgo de parada |

### Vida Útil Remanente (RUL)

Extrapolación lineal del HI en ventana de 48 h hacia el umbral crítico HI = 20.
Se reporta en días. Retorna `N/A` si la tendencia es estable o mejorando.

### Detección de anomalías

Z-score rodante en ventana de 24 h por variable.
Umbral: **|z| > 2.5 σ** → anomalía marcada en la serie temporal y en el resumen.

---

## Equipos monitoreados

| ID | Nombre | Throughput nominal | Modos de degradación |
|---|---|---|---|
| `SAG-01` | Molino SAG | 2 200 t/h | Rodamiento, Liner, Hidráulico |
| `BALL-01` | Molino de Bolas | 1 800 t/h | Rodamiento, Desalineamiento |

---

## Guías de desarrollo

Hay tres formas de correr el proyecto localmente. Elige la que mejor se adapte a tu entorno.

---

### Opción 1 — venv local (recomendado para desarrollo activo)

#### Prerequisitos

| Entorno | Instalación |
|---|---|
| Ubuntu / Debian nativo | `sudo apt install python3.12 python3.12-venv python3.12-dev` |
| WSL con drive Windows (`/mnt/...`) | ver [Desarrollo en WSL](#desarrollo-en-wsl) abajo |
| macOS (Homebrew) | `brew install python@3.12` |

#### Inicio rápido

```bash
git clone https://github.com/tu-usuario/sag-monitor.git
cd sag-monitor

make env          # crea .env desde .env.example (solo la primera vez)
make run          # crea .venv, instala deps y levanta el servidor con hot-reload
```

La aplicación queda disponible en **http://localhost:8050**.

#### Flujo de trabajo diario

```bash
make run          # servidor Dash con hot-reload (DEBUG=true)
make check        # lint + format-check + tipos + tests (antes de commit)
make test-cov     # tests con reporte HTML de cobertura
```

---

### Opción 2 — Docker Compose (entorno idéntico al de producción)

No requiere Python local. Solo necesitas Docker instalado.

#### Prerequisitos

```bash
# Ubuntu / WSL
sudo apt install docker.io docker-compose-plugin
sudo usermod -aG docker $USER   # luego cerrar y volver a abrir la sesión
```

#### Uso

```bash
make docker-up    # build + docker compose up -d (primera vez tarda ~2 min)
make docker-logs  # ver logs en tiempo real
make docker-down  # detener y eliminar contenedores
make docker-shell # abrir shell dentro del contenedor
```

La aplicación queda disponible en **http://localhost:8050**.

> El volumen `sag_data` persiste la base de datos SQLite entre reinicios del contenedor.

---

### Opción 3 — Docker directo (solo imagen)

```bash
make docker-build                  # construye sag-monitor:local
docker run -p 8050:8050 \
  -e DEBUG=false \
  sag-monitor:local
```

---

### Desarrollo en WSL

Cuando el proyecto vive en un drive de Windows (`/mnt/c/`, `/mnt/e/`, etc.),
Python 3.12 no puede crear el symlink `lib64 → lib` que necesita `venv` en un
sistema de archivos NTFS, y falla con:

```
Error: [Errno 1] Operation not permitted: 'lib' -> '.venv/lib64'
```

**El Makefile detecta esta situación automáticamente** y usa `virtualenv --copies`
(copia archivos en lugar de crear symlinks). No necesitas hacer nada especial:

```bash
# Prerequisitos WSL — sin python3.12-venv (no es necesario en este entorno)
sudo apt update && sudo apt install python3.12 python3.12-dev python3-pip

make env && make run   # detecta WSL+NTFS, instala virtualenv si hace falta y arranca
```

Si prefieres habilitar symlinks globalmente en drives Windows (recomendado en general):

```ini
# /etc/wsl.conf — agregar estas líneas y luego ejecutar: wsl --shutdown
[automount]
options = "metadata"
```

---

## Referencia completa de comandos Make

```bash
make help   # lista todos los comandos disponibles
```

| Comando | Descripción |
|---|---|
| `make env` | Crea `.env` desde `.env.example` (omite si ya existe) |
| `make install` | Crea `.venv` e instala dependencias de producción |
| `make install-dev` | Crea `.venv` e instala todas las dependencias (dev incluidas) |
| `make run` | Servidor Dash con hot-reload (`DEBUG=true`) |
| `make serve` | Servidor Gunicorn en modo producción local |
| `make lint` | Lint con ruff |
| `make format` | Auto-formatea el código con ruff |
| `make format-check` | Verifica formato sin modificar archivos |
| `make typecheck` | Chequeo de tipos con mypy |
| `make check` | Suite completa: lint + format-check + typecheck + tests |
| `make test` | Ejecuta pytest |
| `make test-cov` | Tests con reporte de cobertura HTML (`htmlcov/index.html`) |
| `make docker-build` | Construye la imagen Docker local |
| `make docker-up` | Levanta servicios con docker compose (detached) |
| `make docker-down` | Detiene y elimina contenedores |
| `make docker-logs` | Tail de logs del contenedor |
| `make docker-shell` | Shell dentro del contenedor en ejecución |
| `make clean` | Elimina cachés y artefactos de build |
| `make clean-all` | Elimina `.venv` y todo lo generado |

---

## Variables de entorno

Copiar `.env.example` a `.env` y ajustar según el ambiente.

| Variable | Predeterminado | Descripción |
|---|---|---|
| `DEBUG` | `true` | Modo debug del servidor Dash |
| `PORT` | `8050` | Puerto de escucha |
| `HOST` | `0.0.0.0` | Interfaz de red |
| `DATABASE_URL` | `sag_monitor.db` | Ruta SQLite (o URL PostgreSQL en producción) |
| `UPDATE_INTERVAL_MS` | `30000` | Intervalo de actualización en vivo (ms) |
| `SIMULATION_SEED` | `42` | Semilla para reproducibilidad de la simulación |
| `HISTORY_DAYS` | `90` | Días de historial a generar al arrancar |
| `DEFAULT_LANG` | `es` | Idioma de la interfaz (`es` / `en`) |
| `ALERT_RETENTION_DAYS` | `30` | Días de retención de alertas |

---

## CI / CD

### Pipeline de GitHub Actions

El workflow `.github/workflows/ci.yml` ejecuta **4 etapas en serie**. Cada etapa debe pasar para que la siguiente comience:

```
┌─────────────┐     ┌──────────┐     ┌──────────────┐     ┌──────────────────┐
│   quality   │ ──► │   test   │ ──► │    docker    │ ──► │     deploy       │
│             │     │          │     │              │     │  (solo main)     │
│ ruff lint   │     │ pytest   │     │ docker build │     │  doctl deploy    │
│ ruff format │     │ coverage │     │ imagen :ci   │     │  DigitalOcean    │
│ mypy        │     │ XML      │     │              │     │                  │
└─────────────┘     └──────────┘     └──────────────┘     └──────────────────┘
```

| Job | Runner | Condición de ejecución |
|---|---|---|
| `quality` | ubuntu-latest | Siempre (push a `main`/`develop`, PR a `main`) |
| `test` | ubuntu-latest | `quality` passed |
| `docker` | ubuntu-latest | `test` passed |
| `deploy` | ubuntu-latest | `docker` passed **y** push a `main` (no en PRs) |

Los jobs `quality` y `test` usan caché de pip para acelerar ejecuciones posteriores.
El reporte de cobertura XML se sube como artefacto (retención 7 días).

> Documentación completa del pipeline: [docs/cicd.md](docs/cicd.md)

---

### Plataforma de hosting — DigitalOcean App Platform

El archivo `.do/app.yaml` describe el servicio de forma declarativa:

```yaml
spec:
  name: sag-monitor
  services:
    - name: web
      build_command: pip install -r requirements.txt
      run_command: gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 app:server
      environment_slug: python
      deploy_on_push: false   # controlado por GitHub Actions CI
```

`deploy_on_push: false` garantiza que **solo el pipeline de CI** puede desencadenar un deploy.

---

### Configurar el deploy desde GitHub Actions (una sola vez)

**1.** Crear la app en [cloud.digitalocean.com](https://cloud.digitalocean.com) → Apps → Create App → conectar este repositorio.

**2.** Desactivar **Autodeploy** en la configuración del servicio.

**3.** Agregar en GitHub → Settings:

| Nombre | Tipo | Valor |
|---|---|---|
| `DIGITALOCEAN_ACCESS_TOKEN` | Secret | Token API de DO (Read + Write) |
| `DIGITALOCEAN_APP_ID` | Secret | UUID de la app en DO |
| `DO_APP_URL` | Variable | URL pública de la app |

> Guía detallada de configuración: [docs/deployment.md](docs/deployment.md)

---

### Flujo completo en producción

```
git push origin main
        │
        ▼
┌──────────────────────┐
│    GitHub Actions    │
│                      │
│  1. ruff lint        │
│  2. ruff format      │  ◄── falla → no se deploya
│  3. mypy             │
│  4. pytest           │  ◄── falla → no se deploya
│  5. docker build     │  ◄── falla → no se deploya
│  6. doctl deploy     │
└──────────┬───────────┘
           │  doctl apps create-deployment
           ▼
  DigitalOcean App Platform
  pip install -r requirements.txt
           │
           ▼
  gunicorn app:server
  https://tu-app.ondigitalocean.app
```

---

## Estructura del proyecto

```
sag-monitor/
├── app.py                    # Punto de entrada — Dash app + gunicorn server
├── Makefile                  # Comandos de desarrollo y CI
│
├── config/
│   ├── settings.py           # Configuración desde variables de entorno
│   ├── equipment.py          # Umbrales ISO 10816 por equipo
│   └── alerts.py             # Niveles y categorías de alerta
│
├── src/
│   ├── data/
│   │   ├── models.py         # Modelos Pydantic v2 (SensorReading, Alert, HealthSummary)
│   │   ├── simulator.py      # Generador de datos sintéticos + eventos de degradación
│   │   ├── degradation.py    # Funciones de degradación por modo (bearing, liner, etc.)
│   │   └── store.py          # Capa de acceso a SQLite
│   ├── analytics/
│   │   ├── health_index.py   # Cálculo HI + RUL (ISO 13381)
│   │   ├── anomaly.py        # Detección de anomalías por Z-score rodante
│   │   └── thresholds.py     # Evaluación de umbrales en tiempo real
│   ├── pages/
│   │   ├── overview.py       # Resumen ejecutivo
│   │   ├── equipment.py      # Vista detallada por equipo
│   │   ├── alerts.py         # Gestión de alertas
│   │   └── trends.py         # Tendencias históricas
│   ├── callbacks/            # Callbacks Dash (lógica reactiva de cada página)
│   ├── layout/               # Navbar, sidebar, componentes reutilizables
│   └── i18n/                 # Sistema de traducción ES/EN
│
├── tests/                    # pytest — modelos, simulador, analítica
├── assets/styles.css         # Estilos globales (tema oscuro)
│
├── Dockerfile                # Imagen de producción (python:3.12-slim + gunicorn)
├── docker-compose.yml        # Stack local con volumen persistente
├── .do/app.yaml              # Spec declarativo de DigitalOcean App Platform
├── .env.example              # Plantilla de variables de entorno
├── pyproject.toml            # Configuración de ruff, mypy, pytest y coverage
├── requirements.txt          # Dependencias de producción
└── requirements-dev.txt      # Dependencias de desarrollo (incluye las de producción)
```

---

## Stack tecnológico

| Capa | Tecnología | Versión |
|---|---|---|
| Lenguaje | Python | 3.12 |
| Framework web | Dash + Plotly | 2.18 / 5.24 |
| UI components | Dash Bootstrap Components | 1.6 |
| Análisis de datos | Pandas + NumPy | 2.2 / 2.1 |
| Estadística / ML | SciPy + scikit-learn | 1.14 / 1.5 |
| Validación de datos | Pydantic v2 | 2.9 |
| Base de datos | SQLite (dev) | — |
| Servidor WSGI | Gunicorn | 23.0 |
| Contenedor | Docker (python:3.12-slim) | — |
| Lint / Format | Ruff | 0.7 |
| Tipado estático | Mypy | 1.13 |
| Testing | pytest + pytest-cov | 8.3 / 5.0 |
| CI/CD | GitHub Actions | — |
| Hosting | DigitalOcean App Platform | — |

---

## Normas aplicadas

- **ISO 10816** — Vibration severity zones for rotating machinery (Zonas A/B/C/D en mm/s RMS)
- **ISO 13381** — Condition monitoring and diagnostics — Prognostics (framework para HI y RUL)
