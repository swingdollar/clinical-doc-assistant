.PHONY: install run server test clean deploy docker docker-build docker-run lint format checkhelp

help:
	@echo "Clinical Documentation Assistant - Make Commands"
	@echo ""
	@echo "Development:"
	@echo "  make install     - Install dependencies"
	@echo "  make run         - Run development server"
	@echo "  make server      - Run production server"
	@echo ""
	@echo "Testing:"
	@echo "  make test        - Test API endpoints"
	@echo "  make test-cli   - Test CLI script"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint       - Run linter"
	@echo "  make format     - Format code"
	@echo ""
	@echo "Deployment:"
	@echo "  make deploy     - Deploy to Render"
	@echo "  make docker    - Build and run Docker"
	@echo ""
	@echo "Utility:"
	@echo "  make clean     - Clean cache files"
	@echo "  make check    - Check environment"

# =============================================
# Development
# =============================================

install:
	pip install -r requirements.txt

run:
	@echo "Starting development server..."
	FLASK_APP=src.api.main flask run --reload --host=0.0.0.0 --port=5000

server:
	@echo "Starting production server..."
	gunicorn "src.api.main:app" --workers 2 --timeout 120 --bind 0.0.0.0:$$PORT

# =============================================
# Testing
# =============================================

test:
	@echo "Testing health endpoint..."
	@curl -s -X GET http://localhost:5000/health | head -20
	@echo ""
	@echo "======================================"

test-cli:
	@echo "Testing CLI script..."
	@echo "Patient presents with chest pain | python run.py --text -

# =============================================
# Code Quality
# =============================================

lint:
	@echo "Running linter..."
	python -m py_compile src/**/*.py

format:
	@echo "Formatting code..."
	@python -m py_compile src/**/*.py

# =============================================
# Deployment
# =============================================

deploy:
	@echo "Deploy to Render:"
	@echo "1. Go to https://dashboard.render.com"
	@echo "2. New Web Service"
	@echo "3. Connect: swingdollar/clinical-doc-assistant"
	@echo "4. Build: pip install -r requirements.txt"
	@echo "5. Start: gunicorn src.api.main:app --workers 2 --timeout 120 --bind 0.0.0.0:\$$PORT"
	@echo "6. Env: LLM_API_KEY=your-key"

docker:
	@echo "Building Docker image..."
	docker build -t clinical-doc-assistant .
	@echo ""
	@echo "Running container..."
	docker run -p 5000:5000 -e LLM_API_KEY=$$LLM_API_KEY clinical-doc-assistant

docker-build:
	docker build -t clinical-doc-assistant .

docker-run:
	docker run -p 5000:5000 -e LLM_API_KEY=$$LLM_API_KEY clinical-doc-assistant

# =============================================
# Utility
# =============================================

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type f -name "*.py[co]" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleaned!"

check:
	@echo "=== Environment Check ==="
	@python --version
	@echo ""
	@echo "=== Installed Packages ==="
	@pip list | grep -E "flask|requests|gunicorn" || echo "Not installed - run make install"
	@echo ""
	@echo "=== Env Variables ==="
	@echo "LLM_API_KEY: $$(test -n \"$$LLM_API_KEY\" && echo 'Set' || echo 'Not set')"
	@echo "LLM_PROVIDER: $${LLM_PROVIDER:-openai}"
	@echo "LLM_MODEL: $${LLM_MODEL:-gpt-4}"