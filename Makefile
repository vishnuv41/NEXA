.PHONY: help setup dev build test lint format train evaluate clean up down logs

# Default target
help:
	@echo "NEXA WAF - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make setup        - Install all dependencies"
	@echo "  make dev          - Start development environment (Docker Compose)"
	@echo ""
	@echo "Backend:"
	@echo "  make backend-dev  - Start backend locally"
	@echo "  make backend-test - Run backend tests"
	@echo "  make backend-lint - Lint backend code"
	@echo "  make backend-fmt  - Format backend code"
	@echo ""
	@echo "Frontend:"
	@echo "  make frontend-dev - Start frontend locally"
	@echo "  make frontend-test - Run frontend tests"
	@echo "  make frontend-lint - Lint frontend code"
	@echo "  make frontend-fmt - Format frontend code"
	@echo ""
	@echo "ML:"
	@echo "  make train        - Train model"
	@echo "  make evaluate     - Evaluate model"
	@echo ""
	@echo "Docker:"
	@echo "  make up           - Start all services"
	@echo "  make down         - Stop all services"
	@echo "  make logs         - View logs"
	@echo "  make clean        - Clean build artifacts"
	@echo ""

# Setup
setup:
	cd backend && python -m venv .venv && .venv/bin/pip install -e ".[dev]"
	cd frontend && npm install
	cd demo-app && pip install -r requirements.txt

# Development
dev:
	docker compose up --build

# Backend
backend-dev:
	cd backend && .venv/bin/python -m app.main

backend-test:
	cd backend && .venv/bin/pytest -v

backend-lint:
	cd backend && .venv/bin/ruff check .

backend-fmt:
	cd backend && .venv/bin/ruff format .

# Frontend
frontend-dev:
	cd frontend && npm run dev

frontend-test:
	cd frontend && npm test

frontend-lint:
	cd frontend && npm run lint

frontend-fmt:
	cd frontend && npx prettier --write .

# ML
train:
	cd backend && .venv/bin/python scripts/train_model.py

evaluate:
	cd backend && .venv/bin/python scripts/evaluate_model.py

# Docker
up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f

clean:
	docker compose down -v
	rm -rf backend/.venv frontend/node_modules frontend/.next ml/artifacts/*.pt

# Database
db-migrate:
	cd backend && .venv/bin/alembic upgrade head

db-revision:
	cd backend && .venv/bin/alembic revision --autogenerate -m "$(msg)"

# Demo
demo-traffic:
	curl -X POST http://localhost:8000/api/waf/inspect-and-proxy \
	  -H "Content-Type: application/json" \
	  -d '{"method":"GET","path":"/","query":"","headers":{},"body":"","source_ip":"127.0.0.1"}'
	curl -X POST http://localhost:8000/api/waf/inspect-and-proxy \
	  -H "Content-Type: application/json" \
	  -d '{"method":"GET","path":"/products","query":"","headers":{},"body":"","source_ip":"127.0.0.1"}'
	curl -X POST http://localhost:8000/api/waf/inspect-and-proxy \
	  -H "Content-Type: application/json" \
	  -d '{"method":"GET","path":"/products/1","query":"","headers":{},"body":"","source_ip":"127.0.0.1"}'
	curl -X POST http://localhost:8000/api/waf/inspect-and-proxy \
	  -H "Content-Type: application/json" \
	  -d '{"method":"GET","path":"/search","query":"q=laptop","headers":{},"body":"","source_ip":"127.0.0.1"}'

demo-attack:
	curl -X POST http://localhost:8000/api/waf/inspect-and-proxy \
	  -H "Content-Type: application/json" \
	  -d '{"method":"GET","path":"/search","query":"q=test'\'' OR '\''1'\''='\''1","headers":{},"body":"","source_ip":"127.0.0.1"}'
	curl -X POST http://localhost:8000/api/waf/inspect-and-proxy \
	  -H "Content-Type: application/json" \
	  -d '{"method":"GET","path":"/search","query":"q=<script>alert(1)</script>","headers":{},"body":"","source_ip":"127.0.0.1"}'
	curl -X POST http://localhost:8000/api/waf/inspect-and-proxy \
	  -H "Content-Type: application/json" \
	  -d '{"method":"GET","path":"/products/../../../etc/passwd","query":"","headers":{},"body":"","source_ip":"127.0.0.1"}'