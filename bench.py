"""
bench — runs a fixed set of SDLC prompts through both:
  (A) the orchestrated stack for this tier
  (B) a single baseline model (default: qwen2.5-coder:7b)

Prints a side-by-side latency table and writes full responses to bench_results/.

Usage:
  sdlc-moe bench
  sdlc-moe bench --baseline qwen2.5-coder:32b --tier base
  sdlc-moe bench --output results.json
"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table

from sdlc_moe.ollama.client import OllamaClient
from sdlc_moe.orchestrator.router import Router, _system_prompt_for_phase

console = Console()

# Fixed benchmark suite — one representative prompt per SDLC phase
BENCH_SUITE = [
    {
        "phase": "requirements",
        "prompt": "The app should let users sign up, log in, reset their password, and delete their account. Write structured requirements.",
    },
    {
        "phase": "algorithm",
        "prompt": "Design an efficient algorithm to find all duplicate elements in an unsorted array of integers. State time and space complexity.",
    },
    {
        "phase": "codegen",
        "prompt": "Write a Python function that reads a CSV file and returns a list of dicts, handling missing values as None.",
    },
    {
        "phase": "testgen",
        "prompt": "Write pytest unit tests for a function `def divide(a, b)` that raises ZeroDivisionError when b=0.",
    },
    {
        "phase": "debug",
        "prompt": "Why does this Python code fail: `result = [x for x in range(10) if x % 2 = 0]`? Fix it.",
    },
    {
        "phase": "docs",
        "prompt": "Write a docstring for this function: `def merge_dicts(base, override): return {**base, **override}`",
    },
    {
        "phase": "security",
        "prompt": "Review this SQL query for vulnerabilities: `query = f\"SELECT * FROM users WHERE name = '{username}'\"`. How do you fix it?",
    },
]


async def _run_orchestrated(prompt: str, phase: str, router: Router) -> tuple[str, float]:
    start = time.monotonic()
    response = await router.route(prompt, stream=False, phase_override=phase)
    elapsed = time.monotonic() - start
    return response, elapsed


async def _run_baseline(
    prompt: str, phase: str, model: str, client: OllamaClient, num_ctx: int
) -> tuple[str, float]:
    system = _system_prompt_for_phase(phase)
    messages = [{"role": "user", "content": prompt}]
    start = time.monotonic()
    response = await client.chat(
        model=model,
        messages=messages,
        system=system,
        num_ctx=num_ctx,
    )
    elapsed = time.monotonic() - start
    return response, elapsed


async def run_bench(
    tier: str | None,
    baseline: str,
    ollama_url: str,
    output: Path | None,
):
    router = Router(tier=tier, ollama_url=ollama_url)
    baseline_client = OllamaClient(base_url=ollama_url)

    # Check baseline model is available
    if not await baseline_client.is_model_available(baseline):
        rprint(f"[red]Baseline model '{baseline}' is not pulled. Run: ollama pull {baseline}[/red]")
        raise typer.Exit(1)

    profile_limits = router._profile.get("limits", {})
    num_ctx = profile_limits.get("context_tokens", 8192)

    results = []
    table = Table(
        "Phase",
        "Orchestrated model",
        "Time A",
        "Baseline model",
        "Time B",
        box=None,
        padding=(0, 1),
        show_header=True,
    )

    rprint(
        f"\n[bold]Bench:[/bold] tier=[cyan]{router.tier}[/cyan]  baseline=[cyan]{baseline}[/cyan]\n"
    )

    for item in BENCH_SUITE:
        phase = item["phase"]
        prompt = item["prompt"]

        # Resolve which model the orchestrator would use for this phase
        model_key = router._profile["phases"].get(phase, "qwen25_coder_7b")
        model_info = router._models.get(model_key, {})
        orch_tag = model_info.get("ollama", "unknown")

        with console.status(f"[{phase}] running..."):
            orch_resp, orch_time = await _run_orchestrated(prompt, phase, router)
            base_resp, base_time = await _run_baseline(
                prompt, phase, baseline, baseline_client, num_ctx
            )

        results.append(
            {
                "phase": phase,
                "prompt": prompt,
                "orchestrated": {
                    "model": orch_tag,
                    "time_s": round(orch_time, 2),
                    "response": orch_resp,
                },
                "baseline": {
                    "model": baseline,
                    "time_s": round(base_time, 2),
                    "response": base_resp,
                },
            }
        )

        faster = "A" if orch_time <= base_time else "B"
        time_a = f"[green]{orch_time:.1f}s[/green]" if faster == "A" else f"{orch_time:.1f}s"
        time_b = f"[green]{base_time:.1f}s[/green]" if faster == "B" else f"{base_time:.1f}s"

        table.add_row(phase, orch_tag, time_a, baseline, time_b)

    console.print(table)

    # Write full results if requested
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(results, indent=2, ensure_ascii=False))
        rprint(f"\nFull responses written to [bold]{output}[/bold]")
    else:
        out_path = Path("bench_results.json")
        try:
            out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False))
            rprint(f"\nFull responses written to [bold]{out_path}[/bold]")
        except OSError as e:
            rprint(f"\n[red]Failed to write bench_results.json: {e}[/red]")
            rprint("[yellow]Use --output to specify a writable path[/yellow]")

    # Summary
    orch_total = sum(r["orchestrated"]["time_s"] for r in results)
    base_total = sum(r["baseline"]["time_s"] for r in results)
    rprint(
        f"\nTotal time — orchestrated: [bold]{orch_total:.1f}s[/bold]  baseline: [bold]{base_total:.1f}s[/bold]"
    )


def bench_command(
    tier: str | None = typer.Option(None, "--tier", "-t"),
    baseline: str = typer.Option(
        "qwen2.5-coder:7b", "--baseline", help="Single model to compare against"
    ),
    ollama_url: str = typer.Option("http://localhost:11434", "--ollama-url"),
    output: Path | None = typer.Option(
        None, "--output", "-o", help="Write full responses to JSON file"
    ),
):
    """Side-by-side latency comparison: orchestrated stack vs a single model."""
    asyncio.run(run_bench(tier=tier, baseline=baseline, ollama_url=ollama_url, output=output))
