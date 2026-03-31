"""Hardware probing and tier detection."""

from __future__ import annotations

import os
import platform
import subprocess


def detect_tier() -> str:
    """Auto-detect hardware tier based on available RAM."""
    ram_gb = _get_total_ram_gb()

    if ram_gb < 12:
        return "nano"
    elif ram_gb < 24:
        return "base"
    elif ram_gb < 64:
        return "standard"
    else:
        return "extended"


def _get_total_ram_gb() -> float:
    """Get total system RAM in GB."""
    system = platform.system()

    if system == "Linux":
        try:
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        kb = int(line.split()[1])
                        return kb / 1024 / 1024
        except (OSError, ValueError):
            pass

    elif system == "Darwin":  # macOS
        try:
            result = subprocess.run(
                ["sysctl", "-n", "hw.memsize"],
                capture_output=True,
                text=True,
                check=True,
            )
            bytes_val = int(result.stdout.strip())
            return bytes_val / 1024 / 1024 / 1024
        except (subprocess.CalledProcessError, ValueError):
            pass

    # Fallback: check environment variable
    env_ram = os.environ.get("SDLC_MOE_RAM_GB")
    if env_ram:
        try:
            return float(env_ram)
        except ValueError:
            pass

    # Default to nano tier if detection fails
    return 8.0


def ram_summary() -> dict:
    """Return RAM summary for display."""
    total_gb = _get_total_ram_gb()
    tier = detect_tier()

    return {
        "total_gb": round(total_gb, 1),
        "tier": tier,
        "tier_description": _tier_description(tier),
    }


def _tier_description(tier: str) -> str:
    """Get human-readable tier description."""
    descriptions = {
        "nano": "8 GB RAM - Single model (Qwen2.5-Coder 7B)",
        "base": "16 GB RAM - 7 phase specialists",
        "standard": "32 GB RAM - Full 9 phase stack",
        "extended": "64 GB+ RAM - Full stack + Llama3.3 70B",
    }
    return descriptions.get(tier, "Unknown tier")


def load_profile(tier: str) -> dict:
    """Load configuration profile for the given tier."""
    # Default profiles embedded here
    # In production, these would be loaded from config files
    profiles = {
        "nano": {
            "phases": {
                "requirements": "qwen25_coder_7b",
                "architecture": "qwen25_coder_7b",
                "algorithm": "qwen25_coder_7b",
                "codegen": "qwen25_coder_7b",
                "fim": "qwen25_coder_7b",
                "testgen": "qwen25_coder_7b",
                "debug": "qwen25_coder_7b",
                "docs": "qwen25_coder_7b",
                "security": "qwen25_coder_7b",
            },
            "limits": {
                "context_tokens": 8192,
                "max_fim_tokens": 256,
            },
            "classifier": "heuristic",
        },
        "base": {
            "phases": {
                "requirements": "phi4_14b",
                "architecture": "deepseek_r1_14b",
                "algorithm": "deepseek_r1_14b",
                "codegen": "qwen25_coder_7b",
                "fim": "starcoder2_15b",
                "testgen": "deepseek_coder_v2_16b",
                "debug": "deepseek_r1_14b",
                "docs": "gemma3_12b",
                "security": "phi4_14b",
            },
            "limits": {
                "context_tokens": 8192,
                "max_fim_tokens": 512,
            },
            "classifier": "heuristic",
        },
        "standard": {
            "phases": {
                "requirements": "mistral_small3_24b",
                "architecture": "qwen25_coder_32b",
                "algorithm": "deepseek_r1_14b",
                "codegen": "qwen25_coder_32b",
                "fim": "starcoder2_15b",
                "testgen": "deepseek_coder_v2_16b",
                "debug": "deepseek_r1_14b",
                "docs": "gemma3_12b",
                "security": "phi4_14b",
            },
            "limits": {
                "context_tokens": 16384,
                "max_fim_tokens": 512,
            },
            "classifier": "heuristic",
        },
        "extended": {
            "phases": {
                "requirements": "mistral_small3_24b",
                "architecture": "qwen25_coder_32b",
                "algorithm": "deepseek_r1_14b",
                "codegen": "qwen25_coder_32b",
                "fim": "starcoder2_15b",
                "testgen": "deepseek_coder_v2_16b",
                "debug": "deepseek_r1_14b",
                "docs": "gemma3_12b",
                "security": "phi4_14b",
            },
            "limits": {
                "context_tokens": 32768,
                "max_fim_tokens": 512,
            },
            "classifier": "heuristic",
            "orchestrator_model": "llama33_70b",
        },
    }

    return profiles.get(tier, profiles["nano"])
