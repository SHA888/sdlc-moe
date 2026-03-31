#!/usr/bin/env python3
"""
CLI entry point for sdlc-moe.

Provides commands for:
- info: Show hardware tier and model configuration
- preflight: Check Ollama and models
- run: Interactive chat with SDLC-aware routing
- bench: Benchmark orchestrated vs single model
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Optional

import typer
from rich import print as rprint
from rich.console import Console

from sdlc_moe.orchestrator.router import Router
from sdlc_moe.hardware.probe import detect_tier, ram_summary
from sdlc_moe.ollama.client import OllamaClient
from sdlc_moe.orchestrator.classifier import classify
from sdlc_moe.bench import run_bench

console = Console()
app = typer.Typer(help="SDLC-aware local LLM orchestrator", no_args_is_help=True)


@app.command()
def info(
    tier: Optional[str] = typer.Option(None, "--tier", "-t", help="Override detected tier"),
    ollama_url: str = typer.Option("http://localhost:11434", "--ollama-url", help="Ollama server URL"),
) -> None:
    """Show hardware tier and model configuration."""
    detected_tier = tier or detect_tier()
    
    rprint(f"[bold]Hardware Tier:[/bold] {detected_tier}")
    rprint(f"[bold]Ollama URL:[/bold] {ollama_url}")
    
    # Show RAM info
    try:
        ram_info = ram_summary()
        rprint(f"[bold]RAM:[/bold] {ram_info['total_gb']:.1f} GB total")
    except (FileNotFoundError, PermissionError, OSError) as e:
        rprint(f"[yellow]Warning: Could not detect RAM: {e}[/yellow]")
    
    # Show model mapping for this tier
    try:
        router = Router(tier=detected_tier, ollama_url=ollama_url)
        phases = router._profile.get("phases", {})
        rprint("\n[bold]Model Mapping:[/bold]")
        for phase, model_key in phases.items():
            model_info = router._models.get(model_key, {})
            ollama_tag = model_info.get("ollama", "unknown")
            rprint(f"  {phase:12} → {ollama_tag}")
    except (FileNotFoundError, KeyError, ValueError) as e:
        rprint(f"\n[red]Error loading model config: {e}[/red]")


@app.command()
def preflight(
    tier: Optional[str] = typer.Option(None, "--tier", "-t", help="Override detected tier"),
    ollama_url: str = typer.Option("http://localhost:11434", "--ollama-url", help="Ollama server URL"),
    pull_missing: bool = typer.Option(False, "--pull", help="Pull missing models"),
) -> None:
    """Check Ollama is running and all tier models are available."""
    async def _preflight() -> None:
        router = Router(tier=tier, ollama_url=ollama_url)
        status = await router.preflight(pull_missing=pull_missing)
        
        rprint(f"[bold]Tier:[/bold] {status['tier']}")
        rprint(f"[bold]Ollama:[/bold] {'✓ Running' if status['ollama_running'] else '✗ Not running'}")
        
        rprint("\n[bold]Models:[/bold]")
        for tag, state in status['models'].items():
            icon = "✓" if state == "ok" else "↓" if state == "pulled" else "✗"
            color = "green" if state == "ok" else "yellow" if state == "pulled" else "red"
            rprint(f"  {icon} [{color}]{tag}[/{color}] ({state})")
    
    asyncio.run(_preflight())


@app.command()
def run(
    prompt: str = typer.Argument(..., help="Prompt to process"),
    tier: Optional[str] = typer.Option(None, "--tier", "-t", help="Override detected tier"),
    ollama_url: str = typer.Option("http://localhost:11434", "--ollama-url", help="Ollama server URL"),
    stream: bool = typer.Option(False, "--stream", "-s", help="Stream response"),
    file_path: Optional[str] = typer.Option(None, "--file", "-f", help="File context"),
    task: Optional[str] = typer.Option(None, "--task", help="Task description"),
    phase: Optional[str] = typer.Option(None, "--phase", help="Force SDLC phase"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show routing without inference"),
) -> None:
    """Process a prompt with SDLC-aware routing."""
    async def _run() -> None:
        router = Router(tier=tier, ollama_url=ollama_url, dry_run=dry_run)
        
        if stream:
            async for chunk in router.route(
                prompt,
                stream=True,
                file_path=file_path,
                task=task,
                phase_override=phase,
            ):
                print(chunk, end="", flush=True)
            print()
        else:
            response = await router.route(
                prompt,
                stream=False,
                file_path=file_path,
                task=task,
                phase_override=phase,
            )
            rprint(response)
    
    asyncio.run(_run())


@app.command()
def bench(
    tier: Optional[str] = typer.Option(None, "--tier", "-t", help="Override detected tier"),
    baseline: str = typer.Option("qwen2.5-coder:7b", "--baseline", help="Single model to compare against"),
    ollama_url: str = typer.Option("http://localhost:11434", "--ollama-url", help="Ollama server URL"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Write full responses to JSON file"),
) -> None:
    """Side-by-side latency comparison: orchestrated stack vs a single model."""
    asyncio.run(run_bench(tier=tier, baseline=baseline, ollama_url=ollama_url, output=output))


def main() -> None:
    """Entry point for the CLI."""
    try:
        app()
    except KeyboardInterrupt:
        rprint("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(130)
    except (ConnectionError, TimeoutError) as e:
        rprint(f"\n[red]Connection error: {e}[/red]")
        sys.exit(2)
    except Exception as e:
        rprint(f"\n[red]Unexpected error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
