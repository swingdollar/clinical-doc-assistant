"""
Lightweight Standalone Script for Android Clinical Documentation
Optimized for low latency and battery efficiency.
Run locally or integrate into Android via PyJNI or embedded server.
"""

import os
import sys
import json
import argparse
import logging
import threading
from typing import Optional, List
from dataclasses import dataclass, asdict


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class Config:
    """Configuration for the clinical documentation assistant."""
    llm_provider: str = "openai"
    llm_api_key: str = ""
    llm_model: str = "gpt-4"
    llm_base_url: str = ""
    llm_timeout: int = 25
    enable_cache: bool = True
    cache_ttl: int = 1800
    max_tokens: int = 2048
    temperature: float = 0.2


class LightweightClinicalScribe:
    """
    Lightweight clinical scribe optimized for battery and latency.
    Supports: OpenAI, Anthropic, Ollama (local), and custom endpoints.
    """

    def __init__(self, config: Config):
        self.config = config
        self._initialized = False
        self._init_clients()

    def _init_clients(self):
        """Lazy initialization of clients."""
        from src.pii_stripper.analyzer import create_phi_analyzer
        from src.prompt_engine.engine import create_soap_prompt_engine
        from src.llm_client.client import create_llm_client
        from src.validators.soap_validator import create_validator

        self.phi_analyzer = create_phi_analyzer(strict_mode=True)
        self.prompt_engine = create_soap_prompt_engine()

        if self.config.llm_api_key:
            self.llm_client = create_llm_client(
                provider=self.config.llm_provider,
                api_key=self.config.llm_api_key,
                model=self.config.llm_model
            )
        else:
            logger.warning("No API key provided - LLM client not initialized")
            self.llm_client = None

        self.validator = create_validator()
        self._initialized = True

    def process(self, encounter_text: str) -> dict:
        """Process encounter text to SOAP note."""
        if not self._initialized:
            self._init_clients()

        stripped = self.phi_analyzer.analyze(encounter_text)
        prompts = self.prompt_engine.build_prompt(stripped.stripped_text)

        llm_response = self.llm_client.generate(
            system_prompt=prompts["system"],
            user_prompt=prompts["user"],
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            timeout=self.config.llm_timeout
        )

        if not llm_response.success:
            return {
                "success": False,
                "error": llm_response.error
            }

        validation = self.validator.validate(llm_response.content)
        return {
            "success": validation.valid,
            "soap_note": validation.validated_data,
            "errors": validation.errors,
            "warnings": validation.warnings,
            "phi_redacted": len(stripped.detected_phi) > 0
        }

    def process_batch(self, encounters: List[str]) -> List[dict]:
        """Process multiple encounters."""
        results = []
        for text in encounters:
            result = self.process(text)
            results.append(result)
        return results


def main():
    parser = argparse.ArgumentParser(
        description="Clinical Documentation Assistant - SOAP Note Generator"
    )
    parser.add_argument(
        "--text", "-t",
        help="Raw encounter text to process"
    )
    parser.add_argument(
        "--file", "-f",
        help="Input file with encounter text (one per line)"
    )
    parser.add_argument(
        "--provider", "-p",
        default="openai",
        choices=["openai", "anthropic", "ollama", "local"],
        help="LLM provider (default: openai)"
    )
    parser.add_argument(
        "--model", "-m",
        default="gpt-4",
        help="Model name (default: gpt-4)"
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("LLM_API_KEY", ""),
        help="API key (or set LLM_API_KEY env var)"
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("LLM_BASE_URL", ""),
        help="Custom API base URL"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output JSON file"
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Process multiple texts (from --file)"
    )

    args = parser.parse_args()

    if not args.text and not args.file:
        parser.print_help()
        return

    if not args.api_key:
        logger.error("API key required. Set LLM_API_KEY or use --api-key")
        sys.exit(1)

    config = Config(
        llm_provider=args.provider,
        llm_api_key=args.api_key,
        llm_model=args.model,
        llm_base_url=args.base_url
    )

    scribe = LightweightClinicalScribe(config)

    if args.file:
        with open(args.file, "r") as f:
            texts = [line.strip() for line in f if line.strip()]

        logger.info(f"Processing {len(texts)} encounters...")
        results = scribe.process_batch(texts)

        output = json.dumps(results, indent=2)
        if args.output:
            with open(args.output, "w") as f:
                f.write(output)
            logger.info(f"Results written to {args.output}")
        else:
            print(output)
    else:
        logger.info("Processing encounter...")
        result = scribe.process(args.text)

        output = json.dumps(result, indent=2)
        if args.output:
            with open(args.output, "w") as f:
                f.write(output)
            logger.info(f"Results written to {args.output}")
        else:
            print(output)


if __name__ == "__main__":
    main()