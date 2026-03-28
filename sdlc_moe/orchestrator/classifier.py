"""
SDLC phase classifier.

Strategy:
  - "heuristic" (nano/base): keyword-pattern matching, ~0ms, no model call.
  - "llm" (future): uses the orchestrator model for ambiguous inputs.

Phases:
  requirements, architecture, algorithm, codegen, fim,
  testgen, debug, docs, security
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

Phase = Literal[
    "requirements",
    "architecture",
    "algorithm",
    "codegen",
    "fim",
    "testgen",
    "debug",
    "docs",
    "security",
]

ALL_PHASES: list[Phase] = [
    "requirements", "architecture", "algorithm", "codegen",
    "fim", "testgen", "debug", "docs", "security",
]


@dataclass
class ClassifierResult:
    phase: Phase
    confidence: float          # 0.0–1.0
    method: Literal["heuristic", "llm"]
    matched_signals: list[str]


# ---------------------------------------------------------------------------
# Heuristic rules — ordered by specificity (most specific first)
# Each rule: (phase, [signal_patterns], weight)
# ---------------------------------------------------------------------------
_RULES: list[tuple[Phase, list[str], float]] = [
    # FIM — must come before codegen; FIM inputs have a very specific shape
    ("fim", [
        r"<fim_prefix>", r"<fim_suffix>", r"<fim_middle>",
        r"fill.{0,10}(here|blank|gap|middle|in)",
        r"complete.{0,15}function",
        r"# ?TODO", r"\.\.\..*#\s*complete",
    ], 1.0),

    # Debug — error traces, stack frames, "fix", "bug", "why does"
    ("debug", [
        r"traceback", r"stack trace", r"segfault", r"panic:",
        r"error:.*line \d+", r"fix\s+(this|the|my)\s+(bug|error|issue|crash)",
        r"why\s+(does|is|isn'?t|doesn'?t)",
        r"not\s+working", r"unexpected\s+(output|behavior|result)",
        r"exception\s+was\s+raised", r"cannot\s+find\s+symbol",
        r"undefined\s+(variable|function|method|reference)",
    ], 0.9),

    # Security / QA
    ("security", [
        r"sql\s*injection", r"xss", r"csrf", r"authentication\s+bypass",
        r"vulnerability", r"cve-\d+", r"security\s+(audit|review|scan)",
        r"penetration\s+test", r"owasp", r"sanitize\s+input",
        r"privilege\s+escalation", r"secrets?\s+(leak|exposure)",
        r"fuzz(ing)?", r"static\s+analysis",
    ], 1.0),

    # Test generation
    ("testgen", [
        r"write\s+.{0,20}test", r"generate\s+.{0,20}test",
        r"unit\s+test", r"integration\s+test", r"e2e\s+test",
        r"pytest", r"jest", r"cargo\s+test", r"test\s+case",
        r"mock", r"assert\s+.{0,30}(equal|raises|throws|true|false)",
        r"test\s+coverage",
    ], 0.9),

    # Documentation
    ("docs", [
        r"write\s+.{0,20}(doc|readme|docstring|comment|changelog)",
        r"document\s+(this|the|function|module|api|class)",
        r"add\s+(doc|comment)", r"explain\s+(this|the)\s+(code|function|module)",
        r"api\s+doc", r"jsdoc", r"rustdoc", r"pydoc", r"swagger",
        r"readme", r"changelog", r"usage\s+example",
    ], 0.85),

    # Algorithm / logic design
    ("algorithm", [
        r"algorithm\s+for", r"time\s+complexity", r"space\s+complexity",
        r"big.?o", r"dynamic\s+programming", r"recursion",
        r"data\s+structure", r"sort(ing)?", r"search(ing)?",
        r"hash\s+map", r"graph\s+(traversal|algorithm|bfs|dfs)",
        r"optimal\s+(solution|approach)", r"tradeoff",
        r"design\s+(an?\s+)?(algorithm|function|logic)",
    ], 0.9),

    # Architecture
    ("architecture", [
        r"system\s+design", r"architecture", r"microservice",
        r"monolith", r"event.driven", r"message\s+queue",
        r"kafka", r"rabbitmq", r"load\s+balanc", r"caching\s+strategy",
        r"database\s+schema", r"scalab", r"high\s+availability",
        r"service\s+mesh", r"api\s+gateway", r"design\s+pattern",
        r"how\s+(should\s+i\s+)?structure",
    ], 0.9),

    # Requirements / planning
    ("requirements", [
        r"user\s+stor(y|ies)", r"acceptance\s+criteria",
        r"product\s+requirement", r"prd", r"functional\s+requirement",
        r"non.functional", r"stakeholder", r"use\s+case",
        r"as\s+a\s+.{0,40}\s+i\s+want",   # classic user story format
        r"scope", r"milestone", r"sprint\s+plan",
        r"what\s+(should|must|will)\s+(the\s+)?(app|system|service)\s+do",
    ], 0.85),

    # Code generation — broad catch-all; lowest specificity, must come last
    ("codegen", [
        r"write\s+(a\s+)?(function|class|method|script|program|code|module)",
        r"implement\s+(a\s+)?",
        r"create\s+(a\s+)?(function|class|script|endpoint|route|handler)",
        r"generate\s+(a\s+)?(function|code|class|snippet)",
        r"(in\s+)?(python|rust|typescript|javascript|go|java|c\+\+|kotlin|swift)",
        r"def\s+\w+\(", r"fn\s+\w+\(", r"function\s+\w+\(",
        r"class\s+\w+",
    ], 0.7),
]


def classify_heuristic(prompt: str) -> ClassifierResult:
    """
    Rule-based classifier. O(n*rules), runs in <1ms.
    Returns the highest-scoring phase. Falls back to 'codegen'.
    """
    text = prompt.lower()
    scores: dict[Phase, float] = {p: 0.0 for p in ALL_PHASES}
    signals: dict[Phase, list[str]] = {p: [] for p in ALL_PHASES}

    for phase, patterns, weight in _RULES:
        matched_patterns = set()
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                # Only count each pattern once per phase to prevent inflation
                if pattern not in matched_patterns:
                    scores[phase] += weight
                    signals[phase].append(pattern)
                    matched_patterns.add(pattern)

    best_phase: Phase = max(scores, key=lambda p: scores[p])
    best_score = scores[best_phase]

    if best_score == 0.0:
        # No signals matched — default to codegen
        return ClassifierResult(
            phase="codegen",
            confidence=0.5,
            method="heuristic",
            matched_signals=[],
        )

    # Normalize to 0–1 confidence (cap at 1.0)
    # Use max possible score (sum of all weights) as denominator
    max_possible_score = sum(weight for _, _, weight in _RULES)
    confidence = min(best_score / max_possible_score, 1.0)

    return ClassifierResult(
        phase=best_phase,
        confidence=confidence,
        method="heuristic",
        matched_signals=signals[best_phase],
    )


def classify(prompt: str, method: str = "heuristic") -> ClassifierResult:
    """Public entry point. Only heuristic is implemented in v0.1."""
    if method == "heuristic":
        return classify_heuristic(prompt)
    raise NotImplementedError(f"Classifier method '{method}' not yet implemented.")
