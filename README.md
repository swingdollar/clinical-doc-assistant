# Clinical Documentation Assistant

A modular Python-based system for generating SOAP notes from patient encounter data, optimized for Android and cloud deployment.

## Features

- **PII Stripping**: HIPAA-compliant PHI detection/removal before processing
- **SOAP Note Generation**: LLM-powered clinical documentation from raw text
- **JSON Validation**: EHR-compatible output schema
- **Multi-Provider Support**: OpenAI, Anthropic, Ollama, custom endpoints
- **Optimized for Android**: Low latency, caching, async support

## Stack

- Flask + Gunicorn for REST API
- Requests with connection pooling
- In-memory LLM response cache

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/v1/generate-soap` | POST | Generate SOAP note |
| `/api/v1/strip-pii` | POST | Strip PII from text |
| `/api/v1/validate` | POST | Validate SOAP note |

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set API key
export LLM_API_KEY="your-key"

# Run server
python run.py

# Or with Flask
flask run
```

## Deployment

### Render

1. Push to GitHub
2. Create Web Service on Render
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `gunicorn src.api.main:app --workers 2 --timeout 120 --bind 0.0.0.0:$PORT`
5. Add env var: `LLM_API_KEY`

## Usage

```bash
# CLI
python run.py -t "Patient presents with chest pain..."

# REST API
curl -X POST http://localhost:5000/api/v1/generate-soap \
  -H "Content-Type: application/json" \
  -d '{"encounter_text": "Patient presents with..."}'
```

## Project Structure

```
clinical-doc-assistant/
├── run.py                  # CLI script
├── requirements.txt       # Dependencies
├── Procfile              # Render deployment
└── src/
    ├── api/
    │   ├── main.py        # Flask app
    │   └── android_client.py
    ├── firecrawl_client/
    ├── llm_client/
    ├── pii_stripper/
    ├── prompt_engine/
    └── validators/
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LLM_API_KEY` | API key for LLM provider | - |
| `LLM_PROVIDER` | Provider (openai/anthropic/ollama) | openai |
| `LLM_MODEL` | Model name | gpt-4 |
| `LLM_BASE_URL` | Custom API endpoint | - |
| `PORT` | Server port | 5000 |