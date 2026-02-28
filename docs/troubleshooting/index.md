# Troubleshooting — SAG Monitor

Cada issue tiene su propio archivo para facilitar la búsqueda y referencia futura.

> Los diagramas Mermaid se renderizan en GitHub, VS Code (extensión Markdown Preview Mermaid), y Obsidian.

---

## Índice de issues

| ID | Título | Área |
|---|---|---|
| [TS-01](01-wsl-ntfs-symlink.md) | `make install` falla en WSL sobre drive de Windows (EPERM symlink) | Entorno / WSL |
| [TS-02](02-python-no-pip.md) | `python3.12: No module named pip` | Entorno / Python |
| [TS-03](03-pip-permisos.md) | `make install` falla con error de permisos en pip upgrade | Entorno / pip |
| [TS-04](04-docker-build.md) | Docker build falla localmente | Docker |
| [TS-05](05-pantalla-en-blanco.md) | La app arranca pero muestra pantalla en blanco | Runtime |
| [TS-06](06-ci-github-actions.md) | CI falla en GitHub Actions | CI/CD |
| [TS-07](07-compute-rul-floating-point.md) | `compute_rul` retorna valor astronómico en serie estable | Analítica / Bug |
| [TS-08](08-ruff-linting-errors.md) | 97 errores de linting ruff en `make check` | Calidad de código |
| [TS-09](09-testwatch-comportamiento.md) | `make test-watch` se "cuelga" luego de correr los tests | Tests / Dev workflow |

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

---

← [Documentación principal](../index.md)
