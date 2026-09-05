FRONTEND_DIR ?= frontend
BACKEND_DIR ?= backend
VENV_DIR ?= $(abspath $(BACKEND_DIR)/.venv)
VENV_PYTHON := $(VENV_DIR)/bin/python

# Phony targets

.PHONY: all check check-backend check-frontend test dev dev-debug dev-setup frontend-dev \
	backend-run setup-and-run build-all frontend-install frontend-build backend-venv-install \
	clean clean-pyc help clean-build update-robot-hat update-robot-hat-git test-backend \
	test-frontend type-check-backend type-check-frontend format-backend format-check-backend

# Default target
all: build-all

check: check-backend check-frontend

check-backend: type-check-backend format-check-backend test-backend

check-frontend: type-check-frontend test-frontend frontend-build

test: test-backend test-frontend

# Development environment setup
dev:
	cd $(BACKEND_DIR) && $(VENV_PYTHON) -u run.py --dev

dev-debug:
	cd $(BACKEND_DIR) && $(VENV_PYTHON) -u run.py --dev --log-level=DEBUG

dev-setup: frontend-install backend-venv-install dev

update-robot-hat:
	$(VENV_PYTHON) -m pip install --upgrade --force-reinstall robot-hat

update-robot-hat-git:
	$(VENV_PYTHON) -m pip install "git+https://github.com/KarimAziev/robot-hat.git@main#egg=robot_hat"

# Frontend installation and build
frontend-install:
	cd $(FRONTEND_DIR) && npm install

frontend-dev:
	cd $(FRONTEND_DIR) && npm run dev

frontend-build:
	cd $(FRONTEND_DIR) && npm run build

test-frontend:
	cd $(FRONTEND_DIR) && npm run test

type-check-frontend:
	cd $(FRONTEND_DIR) && npm run type-check


# Install, build, and run the project
setup-and-run: frontend-install frontend-build backend-venv-install backend-run

# Install dependencies and build the frontend
build-all: frontend-install frontend-build
	$(MAKE) backend-venv-install INSTALL_FLAGS="$(INSTALL_FLAGS)"


# Backend setup in virtual environment
backend-venv-install:
	cd $(BACKEND_DIR) && VENV_DIR="$(VENV_DIR)" bash ./setup_env.sh $(INSTALL_FLAGS)


# Run backend tests in virtual environment
test-backend:
	cd $(BACKEND_DIR) && $(VENV_PYTHON) -m unittest discover

type-check-backend:
	cd $(BACKEND_DIR) && VIRTUAL_ENV="$(VENV_DIR)" PATH="$(VENV_DIR)/bin:$$PATH" pyright

format-backend:
	cd $(BACKEND_DIR) && $(VENV_PYTHON) -m black .

format-check-backend:
	cd $(BACKEND_DIR) && $(VENV_PYTHON) -m black --check .

# Launch server in virtual environment
backend-run:
	cd $(BACKEND_DIR) && $(VENV_PYTHON) -u run.py $(if $(strip $(LOG_LEVEL)),--log-level="$(LOG_LEVEL)")


# Cleanup targets
clean: clean-pyc clean-build

clean-pyc:
	find . -type d -name "__pycache__" -exec rm -r {} +

clean-build:
	cd $(FRONTEND_DIR) && rm -rf dist

help:
	@printf '%s\n' \
		'Usage: make <target> [VARIABLE=value]' \
		'' \
		'Common targets:'
	@printf '  %-27s %s\n' \
		'all' 'Install dependencies and build the project (default).' \
		'check' 'Run all backend and frontend CI checks.' \
		'dev' 'Run the development environment without installing dependencies.' \
		'test' 'Run the backend and frontend test suites.' \
		'help' 'Show this help.'
	@printf '%s\n' '' 'Setup and build:'
	@printf '  %-27s %s\n' \
		'build-all' 'Install dependencies and build the frontend.' \
		'setup-and-run' 'Install, build, and run the project.' \
		'frontend-install' 'Install frontend dependencies with npm.' \
		'frontend-build' 'Build the production frontend bundle.' \
		'backend-venv-install' 'Create the backend virtual environment and install dependencies.'
	@printf '%s\n' '' 'Development and run:'
	@printf '  %-27s %s\n' \
		'dev-debug' 'Run the development environment with DEBUG logging.' \
		'dev-setup' 'Install dependencies, then run the development environment.' \
		'frontend-dev' 'Run the frontend development server.' \
		'backend-run' 'Run the backend; optionally set LOG_LEVEL.'
	@printf '%s\n' '' 'Checks and tests:'
	@printf '  %-27s %s\n' \
		'check-backend' 'Run backend type, format, and test checks.' \
		'check-frontend' 'Run frontend type, test, and build checks.' \
		'type-check-backend' 'Run Pyright against the backend.' \
		'format-backend' 'Format backend Python files with Black.' \
		'format-check-backend' 'Check backend formatting with Black.' \
		'type-check-frontend' 'Run vue-tsc without emitting files.' \
		'test-backend' 'Run the backend test suite.' \
		'test-frontend' 'Run the frontend test suite.'
	@printf '%s\n' '' 'Maintenance:'
	@printf '  %-27s %s\n' \
		'update-robot-hat' 'Reinstall the latest released robot-hat package.' \
		'update-robot-hat-git' 'Install robot-hat from the main Git branch.' \
		'clean' 'Remove Python caches and the frontend build.' \
		'clean-pyc' 'Remove Python bytecode caches.' \
		'clean-build' 'Remove the frontend production build.'
	@printf '%s\n' \
		'' \
		'Variables:'
	@printf '  %-27s %s\n' \
		'FRONTEND_DIR=<path>' 'Frontend directory (default: frontend).' \
		'BACKEND_DIR=<path>' 'Backend directory (default: backend).' \
		'VENV_DIR=<path>' 'Backend virtual environment directory.' \
		'INSTALL_FLAGS="<flags>"' 'Flags passed to backend/setup_env.sh.' \
		'LOG_LEVEL=<level>' 'Backend log level, such as DEBUG or WARNING.'
