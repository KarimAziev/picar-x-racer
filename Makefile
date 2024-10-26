FRONTEND_DIR := frontend
BACKEND_DIR := backend
VENV_DIR := $(BACKEND_DIR)/.venv

# Phony targets
.PHONY: all dev dev-without-install dev-with-install frontend-dev backend-venv-run build-dev-all sudo-build-all backend-sudo-run backend-sudo-install frontend-install frontend-build backend-venv-install clean clean-pyc help backend-venv-run-debug backend-venv-run-warning

# Default target
all: build-all-no-sudo

# Development environment setup
dev: dev-without-install

# Development environment setup
dev-debug:
	cd $(BACKEND_DIR) && bash -c "source .venv/bin/activate && python3 -u run.py --dev --log-level=DEBUG"

dev-without-install:
	cd $(BACKEND_DIR) && bash -c "source .venv/bin/activate && python3 -u run.py --dev"

dev-with-install: frontend-install backend-venv-install dev-without-install

# Frontend installation and build
frontend-install:
	cd $(FRONTEND_DIR) && npm install

frontend-dev:
	cd $(FRONTEND_DIR) && npm run dev

frontend-build:
	cd $(FRONTEND_DIR) && npm run build

# Build targets for production
build-dev-all: frontend-install frontend-build backend-venv-install backend-venv-run

# Build targets for production
build-all-no-sudo: frontend-install frontend-build backend-venv-install


# Backend setup in virtual environment
backend-venv-install:
	cd $(BACKEND_DIR) && bash ./setup_env.sh


# Launch server in virtual environment
backend-venv-run:
	cd $(BACKEND_DIR) && bash -c "source .venv/bin/activate && python3 -u run.py"

backend-venv-run-debug:
	cd $(BACKEND_DIR) && bash -c "source .venv/bin/activate && python3 -u run.py --log-level=DEBUG"

backend-venv-run-warning:
	cd $(BACKEND_DIR) && bash -c "source .venv/bin/activate && python3 -u run.py --log-level=WARNING"


# Launch backend in sudo
backend-sudo-run:
	sudo python3 $(BACKEND_DIR)/run.py

# Sudo setup
sudo-build-all: frontend-install frontend-build backend-sudo-install backend-sudo-run

# Sudo installation
backend-sudo-install:
	sudo python3 -m pip install -r $(BACKEND_DIR)/requirements.txt


# Cleanup targets
clean: clean-pyc clean-build

clean-pyc:
	find . -type d -name "__pycache__" -exec rm -r {} +

clean-build:
	cd $(FRONTEND_DIR) && npm run clean

# Help target
help:
	@echo "Usage:"
	@echo ""
	@echo "Makefile targets available:"
	@echo ""
	@echo "all                      - Default target, alias for 'build-all-no-sudo'."
	@echo "dev                      - Setup development environment without installation, alias for 'dev-without-install'."
	@echo "dev-without-install      - Run both frontend and backend in development mode without installing dependencies."
	@echo "dev-with-install         - Install frontend and backend dependencies, then run both in development mode."
	@echo "frontend-install         - Install frontend dependencies using npm."
	@echo "frontend-dev             - Run frontend in development mode."
	@echo "frontend-build           - Build frontend for production."
	@echo "backend-venv-install     - Setup backend virtual environment and install dependencies."
	@echo "backend-venv-run         - Run backend server in virtual environment."
	@echo "backend-venv-run-debug   - Run backend server in virtual environment with DEBUG logging level."
	@echo "backend-venv-run-warning - Run backend server in virtual environment with WARNING logging level."
	@echo "backend-sudo-run         - Run backend server with sudo privileges."
	@echo "sudo-build-all           - Install dependencies and build the project with sudo privileges."
	@echo "backend-sudo-install     - Install backend dependencies with sudo privileges."
	@echo "build-dev-all            - Install dependencies and build the entire project for development."
	@echo "build-all-no-sudo        - Install dependencies and build the entire project without sudo."
	@echo "clean                    - Clean the project, remove build artifacts and Python cache."
	@echo "clean-pyc                - Remove Python file caches."
	@echo "clean-build              - Clean frontend build artifacts."