.PHONY: install run test deploy clean help

help:
	@echo "Clinical Documentation Assistant - Make Commands"
	@echo ""
	@echo "  make install   - Install dependencies"
	@echo "  make run      - Run development server"
	@echo "  make server   - Run production server"
	@echo "  make test     - Run tests"
	@echo "  make clean    - Clean cache files"
	@echo "  make deploy  - Deploy to Render"

install:
	pip install -r requirements.txt

run:
	@echo "Starting development server..."
	FLASK_APP=src.api.main flask run --reload

server:
	@echo "Starting production server..."
	gunicorn "src.api.main:app" --workers 2 --timeout 120 --bind 0.0.0.0:$$PORT

deploy:
	@echo "Deploying to Render..."
	@echo "1. Code pushed to GitHub"
	@echo "2. Go to https://dashboard.render.com"
	@echo "3. Create Web Service from swingdollar/clinical-doc-assistant"
	@echo "4. Set Build: pip install -r requirements.txt"
	@echo "5. Set Start: gunicorn src.api.main:app --workers 2 --timeout 120 --bind 0.0.0.0:\$$PORT"
	@echo "6. Add env: LLM_API_KEY"

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete

test:
	@echo "Testing endpoint..."
	@curl -X POST http://localhost:5000/health
	@echo ""
	@echo "Generate SOAP note:"
	@curl -X POST http://localhost:5000/api/v1/generate-soap \
		-H "Content-Type: application/json" \
		-d '{"encounter_text": "Patient presents with chest pain"}'