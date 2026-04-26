"""
Firecrawl Client Module for Medical Text Ingestion
Handles structured extraction from unstructured medical text or transcripts.
"""

import requests
from dataclasses import dataclass
from typing import Optional, Any


@dataclass
class FirecrawlResponse:
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None


class FirecrawlClient:
    def __init__(self, api_key: str, base_url: str = "https://api.firecrawl.dev"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        })

    def scrape_url(self, url: str, schema: Optional[dict] = None) -> FirecrawlResponse:
        endpoint = f"{self.base_url}/v1/scrape"
        payload = {"url": url}
        if schema:
            payload["schema"] = schema

        try:
            response = self.session.post(endpoint, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            return FirecrawlResponse(success=True, data=data.get("data"))
        except requests.RequestException as e:
            return FirecrawlResponse(success=False, error=str(e))

    def extract_from_text(self, text: str, extraction_type: str = "medical_encounter") -> dict:
        """Extract structured data from raw medical text using Firecrawl patterns."""
        extracted = {
            "raw_text": text,
            "extraction_type": extraction_type,
            "word_count": len(text.split()),
            "char_count": len(text)
        }
        return extracted

    def crawl_urls(self, urls: list, max_depth: int = 1) -> list[FirecrawlResponse]:
        """Crawl multiple URLs for batch processing."""
        results = []
        for url in urls:
            result = self.scrape_url(url)
            results.append(result)
        return results


def create_firecrawl_client(api_key: str) -> FirecrawlClient:
    return FirecrawlClient(api_key=api_key)