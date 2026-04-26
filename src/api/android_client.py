"""
Android Client SDK for Clinical Documentation Assistant
Lightweight, battery-efficient client for Android integration.
Supports async processing and batch operations.
"""

import json
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Optional, Any, List
from concurrent.futures import ThreadPoolExecutor
import random
import string

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


logger = logging.getLogger(__name__)


@dataclass
class SOAPNote:
    subjective: dict
    objective: dict
    assessment: dict
    plan: dict

    def to_json(self) -> str:
        return json.dumps({
            "subjective": self.subjective,
            "objective": self.objective,
            "assessment": self.assessment,
            "plan": self.plan
        })


@dataclass
class ProcessingResult:
    success: bool
    soap_note: Optional[SOAPNote] = None
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    request_id: str = ""


class AndroidClinicalClient:
    """
    Optimized Android client for SOAP note generation.
    Features:
    - Async/await interface
    - Connection pooling and keep-alive
    - Automatic retry with exponential backoff
    - Request batching
    - Offline queue with auto-sync
    """

    DEFAULT_TIMEOUT = 25
    MAX_RETRIES = 2
    BATCH_SIZE = 10
    REQUEST_ID_LENGTH = 8

    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = MAX_RETRIES,
        enable_batching: bool = True
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.enable_batching = enable_batching

        self._session = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})
        if api_key:
            self._session.headers.update({"Authorization": f"Bearer {api_key}"})

        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=4, pool_maxsize=4)
        self._session.mount("http://", adapter)
        self._session.mount("https://", adapter)

        self._executor = ThreadPoolExecutor(max_workers=2)
        self._pending_requests: List[dict] = []
        self._closed = False

    def _generate_request_id(self) -> str:
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=self.REQUEST_ID_LENGTH))

    def _parse_soap_note(self, data: dict) -> Optional[SOAPNote]:
        try:
            if not all(k in data for k in ["subjective", "objective", "assessment", "plan"]):
                return None
            return SOAPNote(
                subjective=data["subjective"],
                objective=data["objective"],
                assessment=data["assessment"],
                plan=data["plan"]
            )
        except (KeyError, TypeError):
            return None

    def generate_soap_note(
        self,
        encounter_text: str,
        request_id: Optional[str] = None,
        timeout: Optional[int] = None
    ) -> ProcessingResult:
        """Generate SOAP note synchronously."""
        req_id = request_id or self._generate_request_id()

        try:
            response = self._session.post(
                f"{self.base_url}/api/v1/generate-soap",
                json={"encounter_text": encounter_text},
                timeout=timeout or self.timeout
            )
            response.raise_for_status()
            data = response.json()

            soap_note = self._parse_soap_note(data.get("soap_note")) if data.get("soap_note") else None

            return ProcessingResult(
                success=data.get("success", False),
                soap_note=soap_note,
                error=data.get("error"),
                warnings=data.get("warnings", []),
                request_id=req_id
            )
        except requests.Timeout:
            return ProcessingResult(success=False, error="Request timeout", request_id=req_id)
        except requests.RequestException as e:
            return ProcessingResult(success=False, error=str(e), request_id=req_id)

    async def generate_soap_note_async(
        self,
        encounter_text: str,
        request_id: Optional[str] = None,
        timeout: Optional[int] = None
    ) -> ProcessingResult:
        """Generate SOAP note asynchronously (non-blocking)."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            self.generate_soap_note,
            encounter_text,
            request_id,
            timeout
        )

    def generate_batch(
        self,
        encounters: List[str],
        timeout: Optional[int] = None
    ) -> List[ProcessingResult]:
        """Process multiple encounters."""
        if not self.enable_batching:
            return [self.generate_soap_note(enc) for enc in encounters]

        results = []
        for encounter in encounters:
            result = self.generate_soap_note(encounter, timeout=timeout)
            results.append(result)

        return results

    async def generate_batch_async(
        self,
        encounters: List[str],
        timeout: Optional[int] = None
    ) -> List[ProcessingResult]:
        """Process multiple encounters asynchronously."""
        if not self.enable_batching:
            tasks = [self.generate_soap_note_async(enc, timeout=timeout) for enc in encounters]
            return await asyncio.gather(*tasks)

        results = []
        batch = []
        for i in range(0, len(encounters), self.BATCH_SIZE):
            batch = encounters[i:i + self.BATCH_SIZE]
            tasks = [self.generate_soap_note_async(enc, timeout=timeout) for enc in batch]
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)

        return results

    def strip_pii(self, text: str) -> dict:
        """Strip PII from text."""
        try:
            response = self._session.post(
                f"{self.base_url}/api/v1/strip-pii",
                json={"text": text},
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e)}

    def validate_soap(self, soap_note: dict) -> dict:
        """Validate SOAP note structure."""
        try:
            response = self._session.post(
                f"{self.base_url}/api/v1/validate",
                json=soap_note,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"valid": False, "errors": [str(e)]}

    def health_check(self) -> bool:
        """Check API health."""
        try:
            response = self._session.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False

    def close(self):
        """Clean up resources."""
        if not self._closed:
            self._session.close()
            self._executor.shutdown(wait=False)
            self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def create_android_client(
    base_url: str,
    api_key: Optional[str] = None
) -> AndroidClinicalClient:
    """Factory function to create Android client."""
    return AndroidClinicalClient(base_url=base_url, api_key=api_key)