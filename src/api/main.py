"""
Clinical Documentation Assistant API
REST API for Android integration - generates SOAP notes from patient encounter data.
"""

import os
import json
from dataclasses import dataclass
from typing import Optional

from flask import Flask, request, jsonify

from src.firecrawl_client.client import create_firecrawl_client, FirecrawlClient
from src.pii_stripper.analyzer import create_phi_analyzer, PHIAnalyzer
from src.prompt_engine.engine import create_soap_prompt_engine, SOAPPromptEngine
from src.llm_client.client import create_llm_client, LLMClient
from src.validators.soap_validator import create_validator, SOAPNoteValidator


app = Flask(__name__)


@dataclass
class ProcessingResult:
    success: bool
    soap_note: Optional[dict] = None
    error: Optional[str] = None
    warnings: list = None
    debug_info: dict = None


class ClinicalDocumentationAssistant:
    def __init__(
        self,
        llm_provider: str = "openai",
        llm_api_key: Optional[str] = None,
        llm_model: str = "gpt-4",
        firecrawl_api_key: Optional[str] = None,
        llm_base_url: Optional[str] = None
    ):
        self.phi_analyzer = create_phi_analyzer(strict_mode=True)
        self.prompt_engine = create_soap_prompt_engine()
        self.llm_client = create_llm_client(
            provider=llm_provider,
            api_key=llm_api_key,
            model=llm_model
        ) if llm_api_key else None
        self.validator = create_validator()

        self.firecrawl_client = None
        if firecrawl_api_key:
            self.firecrawl_client = create_firecrawl_client(firecrawl_api_key)

    def process_encounter(self, encounter_text: str) -> ProcessingResult:
        """Process raw encounter text into SOAP note."""
        debug_info = {}

        stripped_result = self.phi_analyzer.analyze(encounter_text)
        debug_info["phi_detected"] = len(stripped_result.detected_phi) > 0
        debug_info["phi_count"] = len(stripped_result.detected_phi)

        if not self.llm_client:
            return ProcessingResult(
                success=False,
                error="LLM client not configured",
                debug_info=debug_info
            )

        prompts = self.prompt_engine.build_prompt(stripped_result.stripped_text)

        llm_response = self.llm_client.generate(
            system_prompt=prompts["system"],
            user_prompt=prompts["user"]
        )

        if not llm_response.success:
            return ProcessingResult(
                success=False,
                error=llm_response.error,
                debug_info=debug_info
            )

        validation_result = self.validator.validate(llm_response.content)

        return ProcessingResult(
            success=validation_result.valid,
            soap_note=validation_result.validated_data,
            error=validation_result.errors[0] if validation_result.errors else None,
            warnings=validation_result.warnings,
            debug_info=debug_info
        )


assistant = None


def create_app(config: Optional[dict] = None) -> Flask:
    """Create and configure the Flask application."""
    global assistant

    config = config or {}

    llm_api_key = config.get("LLM_API_KEY") or os.environ.get("LLM_API_KEY")
    llm_provider = config.get("LLM_PROVIDER", "openai")
    llm_model = config.get("LLM_MODEL", "gpt-4")
    llm_base_url = config.get("LLM_BASE_URL")

    if llm_api_key:
        assistant = ClinicalDocumentationAssistant(
            llm_provider=llm_provider,
            llm_api_key=llm_api_key,
            llm_model=llm_model,
            llm_base_url=llm_base_url
        )

    return app


with app.app_context():
    create_app()


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy"})


@app.route("/api/v1/generate-soap", methods=["POST"])
def generate_soap_note():
    """Generate SOAP note from encounter data."""
    global assistant

    if not assistant:
        return jsonify({"error": "Assistant not configured"}), 500

    data = request.get_json()
    if not data or "encounter_text" not in data:
        return jsonify({"error": "Missing required field: encounter_text"}), 400

    encounter_text = data["encounter_text"]

    result = assistant.process_encounter(encounter_text)

    response = {
        "success": result.success,
        "soap_note": result.soap_note,
        "error": result.error,
        "warnings": result.warnings or []
    }

    if result.debug_info:
        response["debug_info"] = result.debug_info

    status_code = 200 if result.success else 400
    return jsonify(response), status_code


@app.route("/api/v1/validate", methods=["POST"])
def validate_soap():
    """Validate existing SOAP note."""
    validator = create_validator()

    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    result = validator.validate(data)

    return jsonify({
        "valid": result.valid,
        "errors": result.errors,
        "warnings": result.warnings
    })


@app.route("/api/v1/strip-pii", methods=["POST"])
def strip_pii():
    """Strip PII from text without generating SOAP note."""
    analyzer = create_phi_analyzer(strict_mode=True)

    data = request.get_json()
    if not data or "text" not in data:
        return jsonify({"error": "Missing required field: text"}), 400

    result = analyzer.analyze(data["text"])

    return jsonify({
        "original_text": result.original_text,
        "stripped_text": result.stripped_text,
        "detected_phi": result.detected_phi
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)