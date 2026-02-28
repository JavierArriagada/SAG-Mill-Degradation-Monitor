# TS-10 — Docker no disponible en WSL

## Síntoma 1: docker no instalado

```
$ make docker-build
make: docker: No such file or directory
make: *** [Makefile:114: docker-build] Error 127
```

## Causa

Docker no está instalado en el sistema / entorno WSL.

## Solución

Instalar Docker Engine via apt (recomendado en WSL sobre Ubuntu):

```bash
sudo apt update && sudo apt install -y docker.io
sudo usermod -aG docker $USER
newgrp docker
sudo service docker start
docker --version
```

> **Nota WSL:** El script oficial `curl -fsSL https://get.docker.com | sh` muestra un aviso
> recomendando Docker Desktop, pero si se deja correr instala Docker Engine igualmente.
> Es más directo usar `apt install docker.io`.

> **Nota daemon:** WSL2 sin systemd no arranca el daemon automáticamente.
> Hay que correr `sudo service docker start` en cada sesión, o configurar
> `/etc/wsl.conf` para usar systemd.

---

## Síntoma 2: `docker compose` no encontrado

```
$ make docker-up
unknown shorthand flag: 'd' in -d
docker: unknown command: docker compose
```

## Causa

`docker.io` instalado via apt no incluye el plugin Compose V2 (`docker compose`).
Solo instala el binario `docker` sin el subcomando `compose`.

## Solución

```bash
sudo apt install -y docker-compose-v2
docker compose version
```

Verificar:

```bash
$ docker compose version
Docker Compose version v2.x.x
```

---

## Síntoma 3: warning de buildx al hacer `docker build`

```
DEPRECATED: The legacy builder is deprecated and will be removed in a future release.
            Install the buildx component to build images with BuildKit:
            https://docs.docker.com/go/buildx/
```

## Causa

El builder legacy (`docker build`) está deprecado. Es solo un warning informativo,
el build continúa y termina correctamente.

## Solución opcional

Instalar buildx para eliminar el warning:

```bash
sudo apt install -y docker-buildx
```

---

## Síntoma 4: warning de pip corriendo como root dentro del container

```
WARNING: Running pip as the 'root' user can result in broken permissions...
```

## Causa

Es normal en entornos Docker donde el Dockerfile corre como `root`.
No afecta el funcionamiento de la imagen.

---

← [Índice de troubleshooting](index.md)
