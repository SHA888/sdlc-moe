"""Ollama API client for LLM inference."""

from __future__ import annotations

import json
from typing import AsyncIterator, Optional

import aiohttp


class OllamaClient:
    """Async client for Ollama HTTP API."""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url.rstrip("/")
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def close(self) -> None:
        """Close the client session."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def is_running(self) -> bool:
        """Check if Ollama server is running."""
        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/api/tags", timeout=aiohttp.ClientTimeout(total=5)):
                return True
        except Exception:
            return False
    
    async def is_model_available(self, model: str) -> bool:
        """Check if a model is already pulled locally."""
        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/api/tags", timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return False
                data = await resp.json()
                models = data.get("models", [])
                return any(m.get("name", "").startswith(model.split(":")[0]) for m in models)
        except Exception:
            return False
    
    async def ensure_model(self, model: str) -> bool:
        """Pull a model if not available. Returns True on success."""
        if await self.is_model_available(model):
            return True
        
        try:
            session = await self._get_session()
            async with session.post(
                f"{self.base_url}/api/pull",
                json={"name": model, "stream": False},
                timeout=aiohttp.ClientTimeout(total=600),  # Models can be large
            ) as resp:
                return resp.status == 200
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
        
        session = await self._get_session()
        async with session.post(
            f"{self.base_url}/api/chat",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=300),
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()
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
        
        session = await self._get_session()
        async with session.post(
            f"{self.base_url}/api/chat",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=300),
        ) as resp:
            resp.raise_for_status()
            async for line in resp.content:
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
        
        session = await self._get_session()
        async with session.post(
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=60),
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()
            return data.get("response", "")
