"""Ollama API client for LLM inference."""

from __future__ import annotations

import json
from typing import AsyncIterator, Optional

import httpx


class OllamaClient:
    """Async client for Ollama HTTP API."""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url.rstrip("/")
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create httpx client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=60.0)
        return self._client
    
    async def close(self) -> None:
        """Close the client session."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def is_running(self) -> bool:
        """Check if Ollama server is running."""
        try:
            client = await self._get_client()
            response = await client.get(f"{self.base_url}/api/tags", timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False
    
    async def is_model_available(self, model: str) -> bool:
        """Check if a model is already pulled locally."""
        try:
            client = await self._get_client()
            response = await client.get(f"{self.base_url}/api/tags", timeout=10.0)
            if response.status_code != 200:
                return False
            data = response.json()
            models = data.get("models", [])
            return any(m.get("name", "").startswith(model.split(":")[0]) for m in models)
        except Exception:
            return False
    
    async def ensure_model(self, model: str) -> bool:
        """Pull a model if not available. Returns True on success."""
        if await self.is_model_available(model):
            return True
        
        try:
            client = await self._get_client()
            response = await client.post(
                f"{self.base_url}/api/pull",
                json={"name": model, "stream": False},
                timeout=600.0,  # Models can be large
            )
            return response.status_code == 200
        except Exception:
            return False
    
    async def chat(
        self,
        model: str,
        messages: list[dict],
        system: Optional[str] = None,
        num_ctx: int = 8192,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> str:
        """Send a chat request and return the full response."""
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "num_ctx": num_ctx,
                "num_predict": max_tokens,
                "temperature": temperature,
            },
        }
        if system:
            payload["system"] = system
        
        client = await self._get_client()
        response = await client.post(
            f"{self.base_url}/api/chat",
            json=payload,
            timeout=300.0,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("message", {}).get("content", "")
    
    async def chat_stream(
        self,
        model: str,
        messages: list[dict],
        system: Optional[str] = None,
        num_ctx: int = 8192,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """Send a chat request and yield response chunks."""
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "options": {
                "num_ctx": num_ctx,
                "num_predict": max_tokens,
                "temperature": temperature,
            },
        }
        if system:
            payload["system"] = system
        
        client = await self._get_client()
        async with client.stream(
            "POST",
            f"{self.base_url}/api/chat",
            json=payload,
            timeout=300.0,
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    if "message" in data:
                        chunk = data["message"].get("content", "")
                        if chunk:
                            yield chunk
                    if data.get("done", False):
                        break
                except json.JSONDecodeError:
                    continue
    
    async def fim(
        self,
        model: str,
        prefix: str,
        suffix: str,
        max_tokens: int = 256,
        temperature: float = 0.2,
    ) -> str:
        """Fill-in-the-middle completion."""
        # FIM uses the generate endpoint with special prompt format
        prompt = f"<fim_prefix>{prefix}<fim_suffix>{suffix}<fim_middle>"
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
            },
        }
        
        client = await self._get_client()
        response = await client.post(
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=60.0,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("response", "")
