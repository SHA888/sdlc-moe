"""
Router: ties together classifier + profile + context bus + Ollama client.
One Router instance per session.
"""

from __future__ import annotations

import os
import tomllib
from collections.abc import AsyncIterator
from pathlib import Path

from ..hardware.probe import detect_tier, load_profile
from ..ollama.client import OllamaClient
from .classifier import Phase, classify
from .context_bus import ContextBus

_CONFIG_DIR = Path(
    os.environ.get("SDLC_MOE_CONFIG_DIR", Path(__file__).parent.parent.parent.parent / "config")
)


def _load_models_registry() -> dict:
    models_file = _CONFIG_DIR / "models.toml"
    if not models_file.exists():
        raise FileNotFoundError(f"Models configuration not found: {models_file}")

    try:
        with open(models_file, "rb") as f:
            data = tomllib.load(f)
            if "models" not in data:
                raise KeyError(f"'models' key not found in {models_file}")
            return data["models"]
    except tomllib.TOMLDecodeError as e:
        raise ValueError(f"Invalid TOML in {models_file}: {e}") from None


class Router:
    def __init__(
        self,
        tier: str | None = None,
        ollama_url: str = "http://localhost:11434",
        dry_run: bool = False,
    ):
        self._tier = tier or detect_tier()
        self._profile = load_profile(self._tier)
        self._models = _load_models_registry()
        self._client = OllamaClient(base_url=ollama_url)
        self._ctx = ContextBus(max_turns=3)
        self._dry_run = dry_run

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def tier(self) -> str:
        return self._tier

    @property
    def context(self) -> ContextBus:
        return self._ctx

    def dry_run_route(self, prompt: str) -> dict:
        """
        Show which phase and model would be selected without running inference.
        Useful for debugging mis-routing.
        """
        result = classify(prompt, method=self._profile.get("classifier", "heuristic"))
        model_key = self._profile["phases"].get(result.phase, "qwen25_coder_7b")
        model_info = self._models.get(model_key, {})
        return {
            "phase": result.phase,
            "confidence": round(result.confidence, 2),
            "classifier": result.method,
            "model_key": model_key,
            "ollama_tag": model_info.get("ollama", "unknown"),
            "model_name": model_info.get("name", "unknown"),
            "matched_signals": result.matched_signals[:5],
            "tier": self._tier,
        }

    async def route(
        self,
        prompt: str,
        stream: bool = False,
        file_path: str | None = None,
        task: str | None = None,
        phase_override: Phase | None = None,
    ) -> str | AsyncIterator[str]:
        """
        Classify the prompt, select the model, inject context, call Ollama.
        Returns full string (stream=False) or async iterator (stream=True).
        """
        if file_path:
            self._ctx.set_file(file_path)
        if task:
            self._ctx.set_task(task)

        if self._dry_run:
            info = self.dry_run_route(prompt)
            if stream:

                async def _dry_stream() -> AsyncIterator[str]:
                    yield f"[dry-run] phase={info['phase']} model={info['ollama_tag']}"

                return _dry_stream()
            else:
                return f"[dry-run] phase={info['phase']} model={info['ollama_tag']}"

        # Classify
        if phase_override:
            phase = phase_override
        else:
            result = classify(prompt, method=self._profile.get("classifier", "heuristic"))
            phase = result.phase

        # Resolve model with proper error handling
        phases = self._profile.get("phases", {})
        fallback_model = phases.get("codegen", "qwen25_coder_7b")
        model_key = phases.get(phase, fallback_model)

        model_info = self._models.get(model_key)
        if not model_info:
            raise ValueError(
                f"Model '{model_key}' not found in models registry " f"for phase '{phase}'"
            )

        ollama_tag = model_info.get("ollama")
        if not ollama_tag:
            raise ValueError(f"Model '{model_key}' missing 'ollama' tag in models registry")

        # Build system prompt with context bus suffix
        system = _system_prompt_for_phase(phase) + self._ctx.to_system_prompt_suffix()

        # Build message list: history + current prompt
        messages = self._ctx.to_messages() + [{"role": "user", "content": prompt}]

        # Limits from profile
        limits = self._profile.get("limits", {})
        num_ctx = limits.get("context_tokens", 8192)
        max_tokens = limits.get("max_fim_tokens", 512) if phase == "fim" else 2048

        if stream:

            async def _stream() -> AsyncIterator[str]:
                full = []
                try:
                    async for chunk in self._client.chat_stream(
                        model=ollama_tag,
                        messages=messages,
                        system=system,
                        num_ctx=num_ctx,
                        max_tokens=max_tokens,
                    ):
                        full.append(chunk)
                        yield chunk
                    # Push completed assistant turn to context bus
                    self._ctx.push("user", prompt, model=ollama_tag, phase=phase)
                    self._ctx.push("assistant", "".join(full), model=ollama_tag, phase=phase)
                except Exception:
                    # Even if streaming fails, push what we have
                    if full:
                        self._ctx.push("user", prompt, model=ollama_tag, phase=phase)
                        self._ctx.push("assistant", "".join(full), model=ollama_tag, phase=phase)
                    raise

            return _stream()
        else:
            response = await self._client.chat(
                model=ollama_tag,
                messages=messages,
                system=system,
                num_ctx=num_ctx,
                max_tokens=max_tokens,
            )
            self._ctx.push("user", prompt, model=ollama_tag, phase=phase)
            self._ctx.push("assistant", response, model=ollama_tag, phase=phase)
            return response

    async def fim(self, prefix: str, suffix: str) -> str:
        """Direct FIM call — bypasses classifier, always uses the FIM model for this tier."""
        phases = self._profile.get("phases", {})
        model_key = phases.get("fim", "qwen25_coder_7b")

        model_info = self._models.get(model_key)
        if not model_info:
            raise ValueError(f"FIM model '{model_key}' not found in models registry")

        ollama_tag = model_info.get("ollama")
        if not ollama_tag:
            raise ValueError(f"FIM model '{model_key}' missing 'ollama' tag in models registry")

        limits = self._profile.get("limits", {})
        return await self._client.fim(
            model=ollama_tag,
            prefix=prefix,
            suffix=suffix,
            max_tokens=limits.get("max_fim_tokens", 256),
        )

    async def preflight(self, pull_missing: bool = False) -> dict:
        """
        Check Ollama is running and all tier models are pulled.
        Returns status dict. If pull_missing=True, pulls absent models.
        """
        status = {"ollama_running": False, "models": {}, "tier": self._tier}

        status["ollama_running"] = await self._client.is_running()
        if not status["ollama_running"]:
            return status

        phases = self._profile.get("phases", {})
        required_keys = set(phases.values())
        orchestrator = self._profile.get("orchestrator_model")
        if orchestrator:
            required_keys.add(orchestrator)

        for key in required_keys:
            info = self._models.get(key, {})
            tag = info.get("ollama", key)
            available = await self._client.is_model_available(tag)
            status["models"][tag] = "ok" if available else "missing"
            if not available and pull_missing:
                await self._client.ensure_model(tag)
                status["models"][tag] = "pulled"

        return status


# ------------------------------------------------------------------
# Phase-specific system prompts
# ------------------------------------------------------------------

_PHASE_PROMPTS: dict[str, str] = {
    "requirements": (
        "You are a software requirements analyst. Convert user input into clear, "
        "structured requirements. Use numbered lists. Be precise, not verbose."
    ),
    "architecture": (
        "You are a senior software architect. Reason through system design trade-offs "
        "explicitly. Consider scalability, maintainability, and the team's constraints."
    ),
    "algorithm": (
        "You are an algorithms expert. Think step by step before writing any code. "
        "State your approach, its time and space complexity, and edge cases first."
    ),
    "codegen": (
        "You are an expert software engineer. Write clean, idiomatic, production-ready code. "
        "Include brief inline comments only where the logic is non-obvious."
    ),
    "fim": (
        "You are a code completion engine. Complete the code at the cursor position. "
        "Output only the completion text, no explanation, no markdown fences."
    ),
    "testgen": (
        "You are a test engineer. Write comprehensive tests covering happy path, "
        "edge cases, and failure modes. Follow the project's existing test style."
    ),
    "debug": (
        "You are a debugger. Reason through the problem step by step. Identify the root "
        "cause before suggesting a fix. Show your reasoning chain explicitly."
    ),
    "docs": (
        "You are a technical writer. Write clear, concise documentation. "
        "Use the same language and style as the existing codebase."
    ),
    "security": (
        "You are a security engineer. Audit the code for vulnerabilities systematically. "
        "Reference OWASP categories where applicable. Be specific about risk severity."
    ),
}


def _system_prompt_for_phase(phase: str) -> str:
    return _PHASE_PROMPTS.get(phase, _PHASE_PROMPTS["codegen"])
