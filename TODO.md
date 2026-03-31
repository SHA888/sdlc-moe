# sdlc-moe — Comprehensive TODO

**Repo:** https://github.com/SHA888/sdlc-moe
**Primary target:** 16 GB RAM, Windows, offline-first
**Last audited:** 2026-03-31

Status markers: `[x]` done · `[ ]` not started · `[~]` partial / exists but broken

---

## Phase 0 — Fix Broken State (do before any new feature)

These are verified breakages in the current committed code. The project is not installable as-is.

### 0.1 Dependency mismatch — `pyproject.toml`

- [x] Replace `aiohttp>=3.9` with `httpx[http2]>=0.28` — the Ollama client uses `httpx`, not `aiohttp`; `aiohttp` is not imported anywhere in the codebase
- [x] Add `psutil>=6.1` — `hardware/probe.py` imports it; not declared
- [x] Bump `typer>=0.15` — current stable is 0.15.x; `>=0.9` is 18 months stale
- [x] Add `tomli>=2.2; python_version < "3.11"` — `tomllib` is stdlib on 3.11+, but the i18n loader uses it; guard for safety
- [x] Audit: confirm `rich>=13.7` (current stable) — current constraint `>=13.0` works but pin tighter
- [x] Dev extras: add `httpx[http2]` mock support → add `pytest-httpx>=0.35` to `[dev]`

### 0.2 Package layout mismatch

- [x] Resolve conflict: GitHub has flat layout (`sdlc_moe/`), local disk has `src/` layout (`src/sdlc_moe/`)
  - Decision: pick one. Recommendation: keep flat layout to match what is already on GitHub
  - If keeping flat: remove `src/` prefix from all local paths, confirm `[tool.hatch.build.targets.wheel] packages = ["sdlc_moe"]` is correct
  - If switching to `src/`: update `pyproject.toml` to `packages = ["src/sdlc_moe"]`
- [x] Verify entry point: `sdlc_moe.cli:main` — confirm the `main` symbol is exported from `cli.py` (Typer apps need `app()` wrapped in a `main()` function or use `app` directly)

### 0.3 Windows gap — primary target has no setup path

- [x] Write `setup.ps1` — PowerShell equivalent of `setup.sh`
  - Detect RAM via `(Get-CimInstance Win32_PhysicalMemory | Measure-Object Capacity -Sum).Sum`
  - Map to tier: nano / base / standard / extended
  - Check if Ollama is installed (`Get-Command ollama`); prompt to install if not
  - Pull tier-appropriate models with resume support (`ollama pull` is already resumable)
  - Add execution policy note: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`
- [x] Update README Quick Start section to show Windows path first (primary target = Windows)
- [x] Test `sdlc-moe` CLI on Windows: confirm `asyncio` event loop policy — Python on Windows defaults to `ProactorEventLoop`; `httpx` async works fine but verify no `SelectorEventLoop` assumption in the code

---

## Phase 1 — Source Sync (commit local work to GitHub)

- [x] Reconcile local `src/` vs GitHub flat layout (see 0.2)
- [x] Push all local files not yet on GitHub:
  - [x] `config/models.toml`
  - [x] `config/profiles/tier-nano.toml`
  - [x] `config/profiles/tier-base.toml`
  - [x] `config/profiles/tier-standard.toml`
  - [x] `config/profiles/tier-extended.toml`
  - [x] `src/sdlc_moe/hardware/probe.py`
  - [x] `src/sdlc_moe/orchestrator/classifier.py`
  - [x] `src/sdlc_moe/orchestrator/context_bus.py`
  - [x] `src/sdlc_moe/orchestrator/router.py`
  - [x] `src/sdlc_moe/ollama/client.py`
  - [x] `src/sdlc_moe/i18n/` (all locale files)
  - [x] `src/sdlc_moe/bench.py` (moved to tests/)
  - [x] `src/sdlc_moe/cli.py`
  - [x] `tests/routing/test_classifier.py`
  - [x] `.github/workflows/ci.yml`
  - [x] `CONTRIBUTING.md`
  - [x] `MODELS.md`
- [x] Add `.github/workflows/ci.yml` if not already — matrix: Python 3.12, 3.13; OS: ubuntu-latest, windows-latest
- [ ] Tag `v0.1.0` after push and verify CI passes

---

## Phase 2 — Core Quality

### 2.1 Tests

- [x] `tests/routing/test_classifier.py` — 28 cases, 100% pass (local only, not on GitHub yet)
- [ ] Add edge cases to classifier:
  - Mixed-phase prompts: "write a function AND test it" → should route to `codegen`, not split
  - Non-English prompts in supported locales (ID, HI, PT-BR) → must not mis-classify
  - Very short prompts: "fix it", "help" → graceful fallback to `codegen`
  - FIM-specific: prefix/suffix pattern detection
  - Ambiguous: "review my code" → `security` or `debug`? Define and test the tie-break
- [ ] Add `tests/ollama/test_client.py` — use `pytest-httpx` to mock Ollama HTTP responses
  - Test: chat, stream, FIM, connection refused → clean error message
  - Test: model not found (404) → user-readable error, not stack trace
- [ ] Add `tests/hardware/test_probe.py`
  - Mock `psutil.virtual_memory()` for 8/16/32/64 GB scenarios
  - Verify tier selection boundaries
- [ ] Add `tests/integration/test_preflight.py` — mark with `@pytest.mark.integration` and skip in CI unless `OLLAMA_URL` env is set

### 2.2 Type checking and linting

- [ ] `mypy --strict` clean — currently not verified
- [ ] `ruff check` clean — Ruff config is in `pyproject.toml` but not run in CI yet
- [ ] Add both to CI workflow as separate steps before pytest

### 2.3 Error handling audit

- [ ] Ollama not running → `sdlc-moe run` should print actionable message, not `httpx.ConnectError` traceback
- [ ] Model not pulled → detect from Ollama 404, print `ollama pull <model>` command
- [ ] RAM below nano threshold (<8 GB) → warn but do not crash; let user proceed with explicit `--tier` override
- [ ] `--file` flag with binary file → detect and reject early, not mid-inference

---

## Phase 3 — Windows-First Hardening

- [ ] Test full install flow on a clean Windows 11 machine with 16 GB RAM
- [ ] Verify `setup.ps1` pulls correct `base` tier models
- [ ] Confirm `sdlc-moe run` round-trip works end-to-end (Ollama → response → Rich output)
- [ ] Confirm streaming output renders correctly in Windows Terminal and PowerShell 7
- [ ] Test `sdlc-moe fim` with a real editor (VS Code terminal) on Windows
- [ ] Path handling: confirm no hardcoded POSIX paths in any config or code
- [ ] Document Windows-specific note: Ollama requires WSL2 on Windows for GPU; CPU-only works natively

---

## Phase 4 — Editor Integration

### 4.1 VS Code Extension

- [ ] Scaffold a minimal VS Code extension: `pnpm init` in `editors/vscode/`
- [ ] Language: TypeScript, target `vscode` engine `^1.90.0` (current stable)
- [ ] Commands to expose:
  - `sdlc-moe.run` — send selection or current file to `sdlc-moe run`
  - `sdlc-moe.fim` — trigger FIM at cursor position (prefix = text before cursor, suffix = text after)
  - `sdlc-moe.dryRun` — show routing decision in output panel without inference
- [ ] Transport: spawn `sdlc-moe` subprocess from the extension (not HTTP); reads stdout stream
- [ ] Configuration keys:
  - `sdlc-moe.ollamaUrl` (default: `http://localhost:11434`)
  - `sdlc-moe.tier` (default: auto)
  - `sdlc-moe.lang` (default: auto)
- [ ] Publish to VS Code Marketplace under `SHA888` publisher (requires Microsoft account)
- [ ] Gate: do not publish until Phase 0 + Phase 1 are complete

### 4.2 Neovim Plugin

- [ ] Scaffold `editors/neovim/` as a standard Neovim plugin (Lua, lazy.nvim compatible)
- [ ] Expose `:SdlcRun`, `:SdlcFim`, `:SdlcDryRun` commands
- [ ] FIM: use `nvim_buf_get_text` to extract prefix (line 0 to cursor) and suffix (cursor to end)
- [ ] Stream output into a split buffer using `vim.loop` (libuv) for non-blocking I/O
- [ ] Document in `editors/neovim/README.md` with lazy.nvim snippet

---

## Phase 5 — Model Registry Maintenance

- [ ] `config/models.toml` — add model hash/digest field per entry for integrity verification
- [ ] Add `sdlc-moe verify` command: checks SHA256 of pulled model blobs against registry
- [ ] Track model update cadence: DeepSeek R1, Qwen2.5-Coder, Phi-4 all have active release cycles — define a review schedule (quarterly)
- [ ] Add `tier-base` fallback chain: if primary model pull fails on slow connection, define explicit fallback model per phase (e.g., DeepSeek R1 14B → Qwen2.5-Coder 7B)
- [ ] Document RAM headroom: 16 GB machine with OS overhead leaves ~12–13 GB for models; verify Qwen2.5-Coder 7B (Q4_K_M ≈ 4.7 GB) + StarCoder2 15B (Q4 ≈ 9.5 GB) do not co-load simultaneously — they must not

---

## Phase 6 — Classifier Improvements

- [ ] Current: heuristic keyword-based, 28/28 on existing suite
- [ ] Add confidence scoring: if top keyword match < threshold, fall back to `codegen`
- [ ] Add language-aware keyword sets for ID/HI/PT-BR — currently classifier likely only fires on English keywords
- [ ] Add `--explain` flag to `dry-run`: show which keywords triggered the phase decision
- [ ] Stretch: at `standard`/`extended` tiers, allow optional LLM-assisted classification for ambiguous prompts (single extra inference call, opt-in via config)

---

## Phase 7 — Context Bus Enhancements

- [ ] Current: passes task + file + last 3 turns
- [ ] Make turn window configurable: `context_window = 3` in profile TOML
- [ ] Add file diff support: if `--file` points to a git-tracked file, include `git diff HEAD -- <file>` in context automatically
- [ ] Add session persistence: optionally write context bus state to `~/.sdlc-moe/sessions/<timestamp>.json` so a crashed session can be resumed
- [ ] Cap context size: enforce max tokens per phase to prevent Ollama OOM on 8 GB tier; derive from model's `num_ctx` in profile

---

## Phase 8 — Benchmarking and Validation

- [ ] Run `sdlc-moe bench` on actual 16 GB hardware and commit results to `benchmarks/results/base-<date>.json`
- [ ] Add `benchmarks/README.md` with methodology: hardware specs, Ollama version, model versions, measurement approach (wall time per prompt, not token/s)
- [ ] Compare bench results across tiers — document where nano is "good enough" vs where base adds measurable value
- [ ] Add HumanEval pass@1 cross-reference for each assigned model (already planned in MODELS.md — fill in the actual numbers)
- [ ] Add SWE-bench verified scores where available (DeepSeek R1, Qwen2.5-Coder have published numbers)

---

## Phase 9 — Distribution

- [ ] Publish to PyPI as `sdlc-moe` (check name availability — do this before Phase 1 push goes public)
- [ ] `uv tool install sdlc-moe` should work after PyPI publish — test on clean environment
- [ ] Add GitHub Release workflow: tag `vX.Y.Z` → build wheel → upload to Release assets → publish to PyPI via trusted publisher (OIDC, no token required)
- [ ] Add `winget` manifest — allows `winget install sdlc-moe` on Windows (primary target)
  - Requires: stable PyPI release + SHA256 of installer
  - File: `manifests/s/SHA888/sdlc-moe/` in `winget-pkgs` repo
- [ ] Add to `pipx`-compatible install test: `pipx install sdlc-moe`
- [ ] Homebrew tap (lower priority; macOS secondary target): `tap SHA888/homebrew-sdlc-moe`

---

## Phase 10 — Community and Docs

- [ ] Add GitHub repo topics: `llm`, `ollama`, `offline-ai`, `sdlc`, `lmic`, `developer-tools`, `windows`
- [ ] Add repo description: "SDLC-aware local LLM orchestrator for low-bandwidth, offline-first developer environments"
- [ ] Write `CHANGELOG.md` starting at v0.1.0
- [ ] Add issue templates: Bug Report, Model Assignment Correction, New Translation
- [ ] Add `SECURITY.md` — responsible disclosure for any future security issues in the tool itself
- [ ] Add GitHub Discussions — better than Issues for model recommendation threads
- [ ] Translation: current i18n covers EN, ID, HI, PT-BR — next candidates: Arabic (AR), Swahili (SW), Vietnamese (VI) based on LMIC developer population

---

## Known Open Questions (not tasks yet)

- **MoE vs routing:** The name says "mixture-of-experts" but the implementation is a router. This is architecturally accurate but may cause confusion with the ML meaning of MoE. Consider renaming to `sdlc-router` or clarifying in docs. Decision needed before PyPI publish (name is permanent).
- **Ollama version floor:** What minimum Ollama version does the HTTP API require? FIM endpoint (`/api/generate` with `suffix` param) was added in 0.1.x. Pin in README.
- **StarCoder2 15B memory:** At Q4_K_M quantization ≈ 9.5 GB. On a 16 GB machine with OS overhead, this is tight for FIM. May need to drop to StarCoder2 7B for base tier or document the swap-to-disk behavior.
- **Windows GPU path:** Ollama on Windows with NVIDIA GPU works natively (no WSL2 needed as of Ollama 0.1.38+). Update docs if still claiming WSL2 is required.

---

*Generated from live GitHub audit + local state description. All pyproject.toml issues are verified against committed code. Hardware estimates use Ollama's published Q4_K_M quantization sizes.*
