FRONTEND_DIR := frontend
BACKEND_DIR := backend
VENV_DIR := .venv

# Phony targets
.PHONY: all dev frontend-backend-dev frontend-dev backend-dev build sudo-build backend-sudo-run backend-sudo-install frontend-install frontend-build backend-install clean clean-pyc help

# Default target
all: dev

# Development environment setup
dev: frontend-backend-dev

frontend-backend-dev: frontend-install
	cd $(FRONTEND_DIR) && npx concurrently -k \
		"bash -c 'cd .. && source $(VENV_DIR)/bin/activate && python3 -u $(BACKEND_DIR)/run.py'" \
		"npm run dev"

frontend-dev:
	cd $(FRONTEND_DIR) && npm run dev

backend-dev:
	bash -c "source $(VENV_DIR)/bin/activate && python3 -u $(BACKEND_DIR)/run.py"

# Build targets for production
build: frontend-install frontend-build backend-install backend-run

sudo-build: frontend-install frontend-build backend-sudo-install backend-sudo-run

# Backend run (production mode)
backend-sudo-run:
	sudo python3 $(BACKEND_DIR)/run.py

# Backend install (production mode)
backend-sudo-install:
	sudo python3 -m pip install -r ./requirements.txt

# Frontend installation and build
frontend-install:
	cd $(FRONTEND_DIR) && npm install

frontend-build:
	cd $(FRONTEND_DIR) && npm run build

# Backend setup for development
backend-install:
	bash ./setup_env.sh

# Backend setup (general)
backend-setup: backend-install
	@echo "Backend setup is complete."

# Cleanup targets
clean: clean-pyc clean-build

clean-pyc:
	find . -type d -name "__pycache__" -exec rm -r {} +

clean-build:
	cd $(FRONTEND_DIR) && npm run clean

# Help target
help:
	@echo "Usage:"
	@echo "  make all            - Run both frontend and backend in development mode"
	@echo "  make dev            - Alias for all, run both frontend and backend in development mode"
	@echo "  make frontend-dev   - Run frontend in development mode"
	@echo "  make backend-dev    - Run backend in development mode"
	@echo "  make build          - Build frontend and run backend (production mode)"
	@echo "  make sudo-build     - Build frontend and run backend with sudo (production mode)"
	@echo "  make clean          - Clean build and Python artifacts"
	@echo "  make clean-pyc      - Clean Python bytecode files"
	@echo "  make help           - Show this help message"