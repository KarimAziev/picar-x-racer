FRONTEND_DIR := frontend
BACKEND_DIR := backend
VENV_DIR := .venv


.PHONY: all
all: dev


.PHONY: dev
dev: frontend-backend-dev

.PHONY: frontend-backend-dev
frontend-backend-dev:
	cd $(FRONTEND_DIR) && npx concurrently -k "npm run dev" "bash -c 'cd .. && source $(VENV_DIR)/bin/activate && python3 -u $(BACKEND_DIR)/run.py'"

.PHONY: frontend-dev
frontend-dev:
	cd $(FRONTEND_DIR) && npm run dev

.PHONY: backend-dev
backend-dev:
	bash -c "source $(VENV_DIR)/bin/activate && python3 -u $(BACKEND_DIR)/run.py"


.PHONY: build
build: frontend-build backend-run

.PHONY: frontend-build
frontend-build:
	cd $(FRONTEND_DIR) && npm run build

.PHONY: backend-run
backend-run:
	sudo python3 $(BACKEND_DIR)/run.py


.PHONY: raspberry
raspberry: frontend-build raspberry-backend

.PHONY: raspberry-backend
raspberry-backend:
	sudo python3 $(BACKEND_DIR)/run.py


.PHONY: clean
clean:
	rm -rf $(FRONTEND_DIR)/dist
	find . -type d -name "__pycache__" -exec rm -r {} +

.PHONY: help
help:
	@echo "Usage:"
	@echo "  make all            - Run both frontend and backend in development mode"
	@echo "  make dev            - Alias for all, run both frontend and backend in development mode"
	@echo "  make frontend-dev   - Run frontend in development mode"
	@echo "  make backend-dev    - Run backend in development mode"
	@echo "  make build          - Build frontend and run backend (production mode)"
	@echo "  make frontend-build - Build frontend"
	@echo "  make backend-run    - Run backend (production mode)"
	@echo "  make raspberry      - Build frontend and run backend for Raspberry OS"
	@echo "  make clean          - Clean build artifacts"
	@echo "  make help           - Show this help message"