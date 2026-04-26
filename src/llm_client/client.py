"""
LLM Client Module for SOAP Note Generation
REST API approach for connecting to local or cloud-based LLMs.
Optimized for low latency and battery efficiency.
"""

import json
import time
import hashlib
import threading
from dataclasses import dataclass
from typing import Optional, Any
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import requests


@dataclass
class LLMResponse:
    success: bool
    content: Optional[dict] = None
    raw_response: Optional[str] = None
    error: Optional[str] = None
    model: Optional[str] = None
    usage: Optional[dict] = None


class LLMClient:
    """Optimized LLM client with caching, connection pooling, and retry logic."""
    
    SUPPORTED_PROVIDERS = ["openai", "anthropic", "ollama", "local"]

    def __init__(
        self,
        provider: str = "openai",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "gpt-4",
        timeout: int = 30,
        enable_cache: bool = True,
        cache_ttl: int = 3600,
        max_cache_size: int = 50
    ):
        if provider not in self.SUPPORTED_PROVIDERS:
            raise ValueError(f"Provider must be one of: {self.SUPPORTED_PROVIDERS}")

        self.provider = provider
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.enable_cache = enable_cache
        self.cache_ttl = cache_ttl
        self.max_cache_size = max_cache_size

        self._cache: dict = {}
        self._cache_lock = threading.Lock()

        self.session = requests.Session()

        retry_strategy = Retry(
            total=2,
            backoff_factor=0.3,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=3,
            pool_maxsize=3
        )
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        if provider == "openai":
            self.base_url = base_url or "https://api.openai.com/v1"
            self.endpoint = "/chat/completions"
            self.session.headers.update({
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            })
        elif provider == "anthropic":
            self.base_url = base_url or "https://api.anthropic.com/v1"
            self.endpoint = "/messages"
            self.session.headers.update({
                "x-api-key": api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            })
        elif provider == "ollama":
            self.base_url = base_url or "http://localhost:11434"
            self.endpoint = "/api/generate"
        elif provider == "local":
            self.base_url = base_url or "http://localhost:8000"
            self.endpoint = "/generate"

    def _get_cache_key(self, system: str, user: str) -> str:
        content = f"{system}:{user}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _get_cached(self, cache_key: str) -> Optional[LLMResponse]:
        if not self.enable_cache:
            return None
        with self._cache_lock:
            if cache_key in self._cache:
                entry = self._cache[cache_key]
                if time.time() - entry["timestamp"] < self.cache_ttl:
                    return entry["response"]
                del self._cache[cache_key]
        return None

    def _set_cached(self, cache_key: str, response: LLMResponse) -> None:
        if not self.enable_cache:
            return
        with self._cache_lock:
            if len(self._cache) >= self.max_cache_size:
                oldest_key = min(self._cache, key=lambda k: self._cache[k]["timestamp"])
                del self._cache[oldest_key]
            self._cache[cache_key] = {
                "response": response,
                "timestamp": time.time()
            }

    def generate(self, system_prompt: str, user_prompt: str, **kwargs) -> LLMResponse:
        cache_key = self._get_cache_key(system_prompt, user_prompt)
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        try:
            if self.provider == "openai":
                result = self._generate_openai(system_prompt, user_prompt, **kwargs)
            elif self.provider == "anthropic":
                result = self._generate_anthropic(system_prompt, user_prompt, **kwargs)
            elif self.provider in ["ollama", "local"]:
                result = self._generate_local(system_prompt, user_prompt, **kwargs)
            else:
                result = LLMResponse(success=False, error="Unknown provider")

            if result.success:
                self._set_cached(cache_key, result)
            return result
        except Exception as e:
            return LLMResponse(success=False, error=str(e))

    def _generate_openai(self, system: str, user: str, **kwargs) -> LLMResponse:
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ]

        payload = {
            "model": kwargs.get("model", self.model),
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.2),
            "max_tokens": kwargs.get("max_tokens", 2048),
            "response_format": {"type": "json_object"}
        }

        response = self.session.post(
            f"{self.base_url}{self.endpoint}",
            json=payload,
            timeout=kwargs.get("timeout", self.timeout)
        )
        response.raise_for_status()
        data = response.json()

        return LLMResponse(
            success=True,
            content=json.loads(data["choices"][0]["message"]["content"]),
            raw_response=json.dumps(data),
            model=data.get("model"),
            usage=data.get("usage")
        )

    def _generate_anthropic(self, system: str, user: str, **kwargs) -> LLMResponse:
        payload = {
            "model": kwargs.get("model", self.model),
            "max_tokens": kwargs.get("max_tokens", 2048),
            "temperature": kwargs.get("temperature", 0.2),
            "system": system,
            "messages": [{"role": "user", "content": user}]
        }

        response = self.session.post(
            f"{self.base_url}{self.endpoint}",
            json=payload,
            timeout=kwargs.get("timeout", self.timeout)
        )
        response.raise_for_status()
        data = response.json()

        return LLMResponse(
            success=True,
            content=json.loads(data["content"][0]["text"]),
            raw_response=json.dumps(data),
            model=data.get("model"),
            usage={"input_tokens": data.get("usage", {}).get("input_tokens"),
                   "output_tokens": data.get("usage", {}).get("output_tokens")}
        )

    def _generate_local(self, system: str, user: str, **kwargs) -> LLMResponse:
        payload = {
            "model": kwargs.get("model", self.model),
            "system": system,
            "prompt": user,
            "temperature": kwargs.get("temperature", 0.2),
            "format": "json"
        }

        response = self.session.post(
            f"{self.base_url}{self.endpoint}",
            json=payload,
            timeout=kwargs.get("timeout", self.timeout)
        )
        response.raise_for_status()
        data = response.json()

        return LLMResponse(
            success=True,
            content=json.loads(data.get("response", "{}")),
            raw_response=json.dumps(data),
            model=self.model
        )

    def test_connection(self) -> bool:
        try:
            if self.provider == "openai":
                response = self.session.get(f"{self.base_url}/models", timeout=5)
            elif self.provider == "ollama":
                response = self.session.get(f"{self.base_url}/api/tags", timeout=5)
            else:
                response = self.session.get(f"{self.base_url}/", timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def close(self):
        self.session.close()


def create_llm_client(
    provider: str = "openai",
    api_key: Optional[str] = None,
    model: str = "gpt-4"
) -> LLMClient:
    """Factory function to create optimized LLM client."""
    return LLMClient(provider=provider, api_key=api_key, model=model)