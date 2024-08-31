FRONTEND_DIR := frontend
BACKEND_DIR := backend
VENV_DIR := $(BACKEND_DIR)/.venv

# Phony targets
.PHONY: all dev dev-without-install dev-with-install frontend-dev backend-venv-run build-dev-all sudo-build-all backend-sudo-run backend-sudo-install frontend-install frontend-build backend-dev-install clean clean-pyc help

# Default target
all: build-all-no-sudo

# Development environment setup
dev: dev-without-install

dev-without-install:
	cd $(FRONTEND_DIR) && npx concurrently -k \
		"bash -c 'cd .. && source $(VENV_DIR)/bin/activate && python3 -u $(BACKEND_DIR)/run.py'" \
		"bash -c 'sleep 2 && npm run dev'"

dev-with-install: frontend-install backend-dev-install dev-without-install

# Frontend installation and build
frontend-install:
	cd $(FRONTEND_DIR) && npm install

frontend-dev:
	cd $(FRONTEND_DIR) && npm run dev

frontend-build:
	cd $(FRONTEND_DIR) && npm run build

backend-venv-run:
	cd $(BACKEND_DIR) && bash -c "source .venv/bin/activate && python3 -u run.py"

# Build targets for production
build-dev-all: frontend-install frontend-build backend-dev-install backend-venv-run

# Build targets for production
build-all-no-sudo: frontend-install frontend-build backend-dev-install backend-venv-run

sudo-build-all: frontend-install frontend-build backend-sudo-install backend-sudo-run

# Backend run (production mode)
backend-sudo-run:
	sudo python3 $(BACKEND_DIR)/run.py

# Backend install (production mode)
backend-sudo-install:
	sudo python3 -m pip install -r $(BACKEND_DIR)/requirements.txt

# Backend setup for development
backend-dev-install:
	cd $(BACKEND_DIR) && bash ./setup_env.sh

# Cleanup targets
clean: clean-pyc clean-build

clean-pyc:
	find . -type d -name "__pycache__" -exec rm -r {} +

clean-build:
	cd $(FRONTEND_DIR) && npm run clean

# Help target
help:
	@echo "Usage:"
	@echo "  make <target>"
	@echo ""
	@echo "Targets:"
	@echo "  all                        Default target (alias for 'build-all-no-sudo')"
	@echo "  dev                        (alias for 'dev-without-install')"
	@echo "  dev-without-install        Run development environment without installing dependencies"
	@echo "  dev-with-install           Install dependencies and run development environment"
	@echo "  frontend-dev               Run frontend development server"
	@echo "  backend-venv-run           Run backend development server (with venv)"
	@echo "  build-dev-all              Install and build both front and back ends for development"
	@echo "  build-all-no-sudo          Install and build both front and back ends"
	@echo "  sudo-build-all             Install and build both front and back ends for production (with sudo)"
	@echo "  backend-sudo-run           Run backend in production mode (with sudo)"
	@echo "  backend-sudo-install       Install backend dependencies for production (with sudo)"
	@echo "  frontend-install           Install frontend dependencies"
	@echo "  frontend-build             Build frontend for production"
	@echo "  backend-dev-install        Set up backend for development (with venv)"
	@echo "  clean                      Clean all build artifacts"
	@echo "  clean-pyc                  Remove Python bytecode files"
	@echo "  clean-build                Clean frontend build artifacts"
	@echo "  help                       Display this help message"