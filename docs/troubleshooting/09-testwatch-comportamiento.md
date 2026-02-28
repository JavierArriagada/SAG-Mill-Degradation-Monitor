# TS-09 — `make test-watch` se "cuelga" luego de correr los tests

## Síntoma

```
$ make test-watch
...
[Sat Feb 28 13:11:59 2026] Running: py.test . --tb=short -c setup.cfg
=========================================== test session starts ============================================
...
73 passed in 0.52s
============================================
# → la terminal no devuelve el prompt
```

## Causa

Es **comportamiento esperado**. `ptw` (pytest-watch) es un *file watcher*: corre los tests una vez y luego se queda escuchando cambios en el filesystem. Cuando detecta que un archivo `.py` fue modificado, vuelve a correr los tests automáticamente.

No está colgado — está esperando cambios.

## Solución

Para salir del modo watch: **`Ctrl+C`**.

## Issues previos durante la configuración

### ptw leía `pyproject.toml` como INI y fallaba

`ptw` intenta parsear un archivo de configuración como INI. Al no encontrar un config explícito, tomaba `pyproject.toml` (formato TOML), lo que causaba:

```
configparser.ParsingError: Source contains parsing errors: 'pyproject.toml'
```

**Fix:** crear `setup.cfg` con una sección `[pytest-watch]` vacía y pasar `--config setup.cfg` en el Makefile.

### pytest detectaba `/dev` como rootdir

Al usar `--config /dev/null` (intento anterior de suprimir el config de ptw), ptw corría pytest con rootdir `/dev`, lo que causaba:

```
rootdir: /dev
configfile: null
PytestCacheWarning: could not create cache path /dev/.pytest_cache/...
```

**Fix:** usar `--config setup.cfg` apuntando a un INI válido en el proyecto, y pasar `.` como directorio de watch explícito.

---

← [Índice de troubleshooting](index.md)
