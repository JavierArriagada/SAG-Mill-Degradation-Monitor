# ─────────────────────────────────────────────────────────────────────────────
# SAG Monitor — Makefile
# Targets for local Ubuntu development and CI/CD helpers.
# ─────────────────────────────────────────────────────────────────────────────

PYTHON      := python3.12
VENV        := .venv
PIP         := $(VENV)/bin/pip
PY          := $(VENV)/bin/python
RUFF        := $(VENV)/bin/ruff
MYPY        := $(VENV)/bin/mypy
PYTEST      := $(VENV)/bin/pytest
GUNICORN    := $(VENV)/bin/gunicorn

APP_MODULE  := app:server
PORT        := 8050
HOST        := 0.0.0.0
WORKERS     := 2

.DEFAULT_GOAL := help

# ── Helpers ───────────────────────────────────────────────────────────────────

.PHONY: help
help:  ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}' | sort

# ── Environment setup ─────────────────────────────────────────────────────────

.PHONY: env
env:  ## Copy .env.example → .env (skip if already exists)
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "Created .env from .env.example — edit it before running."; \
	else \
		echo ".env already exists, skipping."; \
	fi

$(VENV)/bin/activate:
	@# WSL + Windows drive (e.g. /mnt/e/): Python 3.12 venv fails trying to
	@# create lib64 -> lib symlink on NTFS. virtualenv --copies avoids all symlinks.
	@if grep -qiE 'microsoft|wsl' /proc/version 2>/dev/null && \
	    pwd | grep -qE '^/mnt/[a-z]/'; then \
		printf "\033[33m[WSL+WinDrive] Patching venv to skip NTFS lib64 symlink\033[0m\n"; \
		$(PYTHON) -c "import venv,os; _o=os.symlink; os.symlink=lambda s,d,*a,**k:None if 'lib64' in d else _o(s,d,*a,**k); venv.EnvBuilder(with_pip=True,symlinks=False).create('$(VENV)')"; \
	else \
		$(PYTHON) -m venv $(VENV); \
	fi
	$(PIP) install --upgrade pip --quiet

.PHONY: install
install: $(VENV)/bin/activate  ## Create venv and install production dependencies
	$(PIP) install -r requirements.txt
	@echo "Production dependencies installed."

.PHONY: install-dev
install-dev: $(VENV)/bin/activate  ## Create venv and install all dev dependencies
	$(PIP) install -r requirements-dev.txt
	@echo "Dev dependencies installed."

# ── Run ───────────────────────────────────────────────────────────────────────

.PHONY: run
run: env install-dev  ## Run the Dash dev server (hot-reload, DEBUG=true)
	@set -a && [ -f .env ] && . ./.env && set +a; \
	DEBUG=true $(PY) app.py

.PHONY: serve
serve: install  ## Run gunicorn production server locally
	@set -a && [ -f .env ] && . ./.env && set +a; \
	$(GUNICORN) --bind $(HOST):$(PORT) --workers $(WORKERS) --timeout 120 $(APP_MODULE)

# ── Quality ───────────────────────────────────────────────────────────────────

.PHONY: lint
lint: install-dev  ## Lint with ruff
	$(RUFF) check .

.PHONY: format
format: install-dev  ## Auto-format code with ruff
	$(RUFF) format .

.PHONY: format-check
format-check: install-dev  ## Check formatting without modifying files
	$(RUFF) format --check .

.PHONY: typecheck
typecheck: install-dev  ## Run mypy type checker
	$(MYPY) src/ config/

.PHONY: check
check: lint format-check typecheck test  ## Run full quality suite (lint + format + types + tests)

# ── Tests ─────────────────────────────────────────────────────────────────────

.PHONY: test
test: install-dev  ## Run tests
	$(PYTEST)

.PHONY: test-cov
test-cov: install-dev  ## Run tests with coverage report
	$(PYTEST) --cov=src --cov=config --cov-report=term-missing --cov-report=html
	@echo "HTML coverage report: htmlcov/index.html"

.PHONY: test-watch
test-watch: install-dev  ## Run tests in watch mode (requires pytest-watch)
	$(VENV)/bin/ptw --config setup.cfg . -- --tb=short

# ── Docker ────────────────────────────────────────────────────────────────────

.PHONY: docker-build
docker-build:  ## Build the Docker image
	docker build -t sag-monitor:local .

.PHONY: docker-up
docker-up:  ## Start services with docker-compose (detached)
	docker compose up -d --build
	@echo "App running at http://localhost:$(PORT)"

.PHONY: docker-down
docker-down:  ## Stop and remove containers
	docker compose down

.PHONY: docker-logs
docker-logs:  ## Tail container logs
	docker compose logs -f app

.PHONY: docker-shell
docker-shell:  ## Open a shell inside the running container
	docker compose exec app /bin/sh

# ── Cleanup ───────────────────────────────────────────────────────────────────

.PHONY: clean
clean:  ## Remove cache files and build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .coverage htmlcov .mypy_cache .ruff_cache .pytest_cache

.PHONY: clean-all
clean-all: clean  ## Remove venv and all generated files
	rm -rf $(VENV)
	@echo "Virtual environment removed."
