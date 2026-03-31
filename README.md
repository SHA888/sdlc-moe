# sdlc-moe

**SDLC-aware local LLM orchestrator.**
Routes each software development phase to its strongest open-weight specialist model.
Runs entirely offline. Zero cost per query. Designed for 8–64 GB consumer hardware.

---

**Orkestrasi LLM lokal berbasis fase SDLC.**
Mengarahkan setiap fase pengembangan perangkat lunak ke model open-weight terbaik.
Berjalan sepenuhnya offline. Tidak ada biaya per query. Dirancang untuk hardware konsumen 8–64 GB.

---

**Orquestrador local de LLM orientado por fases do SDLC.**
Direciona cada fase de desenvolvimento ao modelo especialista mais forte.
Funciona completamente offline. Custo zero por consulta. Projetado para hardware com 8–64 GB de RAM.

---

**SDLC चरण-आधारित स्थानीय LLM ऑर्केस्ट्रेटर।**
प्रत्येक विकास चरण को उसके सबसे मजबूत open-weight विशेषज्ञ मॉडल पर भेजता है।
पूरी तरह ऑफलाइन। प्रति क्वेरी शून्य लागत। 8–64 GB RAM के उपभोक्ता हार्डवेयर के लिए।

---

## Why / Mengapa / Por quê / क्यों

A developer running 500 coding queries/day through a cloud API spends **$15–30 USD/month** — a significant fraction of a junior developer's salary in many countries. `sdlc-moe` eliminates that cost permanently after a one-time model download.

Developer yang mengirim 500 query per hari via cloud API menghabiskan **$15–30 USD/bulan**. `sdlc-moe` menghilangkan biaya tersebut setelah mengunduh model sekali saja.

---

## Hardware tiers / Tingkatan hardware

| Tier | RAM | Phases | Primary model |
|------|-----|--------|---------------|
| `nano` | 8 GB | 5 core | Qwen2.5-Coder 7B (single model) |
| `base` ⭐ | 16 GB | 7 phases | Specialists per phase |
| `standard` | 32 GB | Full 9 phases | Full stack |
| `extended` | 64 GB+ | Full 9 + Llama3.3 70B | Full stack |

⭐ = primary LMIC target

---

## Quick start / Mulai cepat / Início rápido / त्वरित प्रारंभ

```bash
# One-line setup: installs Ollama + pulls all models for your RAM tier
# (Safe to re-run — already-pulled models are skipped. Resumable on slow connections.)

# Linux/macOS:
curl -fsSL https://raw.githubusercontent.com/SHA888/sdlc-moe/main/scripts/setup.sh | bash

# Windows (PowerShell):
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned -Force
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/SHA888/sdlc-moe/main/scripts/setup.ps1" -OutFile "setup.ps1"; ./setup.ps1

# Then install the CLI
pip install uv
uv tool install sdlc-moe

# Confirm your tier
sdlc-moe info

# Verify models
sdlc-moe preflight

# Run
sdlc-moe run "write a Python function to parse CSV"
sdlc-moe run "fix this traceback" --file src/main.py

# FIM (fill-in-the-middle)
sdlc-moe fim --prefix "def add(a, b):" --suffix "    return result"

# Debug routing before running
sdlc-moe dry-run "write unit tests for the auth module"

# Benchmark: orchestrated stack vs single model
sdlc-moe bench
```

Set `SDLC_MOE_LANG=id` (Bahasa Indonesia), `hi` (Hindi), or `pt_br` (Português) for translated output.

---

## SDLC phase → model mapping

| Phase | `nano` (8 GB) | `base` (16 GB) | `standard` (32 GB) |
|-------|--------------|----------------|-------------------|
| Requirements | Qwen2.5-Coder 7B | Phi-4 14B | Mistral Small 3 24B |
| Architecture | Qwen2.5-Coder 7B | DeepSeek R1 14B | Qwen2.5-Coder 32B |
| Algorithm / CoT | Qwen2.5-Coder 7B | DeepSeek R1 14B | DeepSeek R1 14B |
| Code generation | Qwen2.5-Coder 7B | Qwen2.5-Coder 7B | Qwen2.5-Coder 32B |
| FIM / inline | Qwen2.5-Coder 7B | StarCoder2 15B | StarCoder2 15B |
| Test generation | Qwen2.5-Coder 7B | DeepSeek-Coder V2 16B | DeepSeek-Coder V2 16B |
| Debug / review | Qwen2.5-Coder 7B | DeepSeek R1 14B | DeepSeek R1 14B |
| Documentation | Qwen2.5-Coder 7B | Gemma 3 12B | Gemma 3 12B |
| Security / QA | Qwen2.5-Coder 7B | Phi-4 14B | Phi-4 14B |

Model assignments are based on published benchmark data (SWE-bench, HumanEval, LiveCodeBench).
See [MODELS.md](MODELS.md) for sources and citation links.

---

## How it works

```
prompt → [heuristic classifier] → SDLC phase
                                       ↓
                            [profile: tier-base.toml]
                                       ↓
                            resolve specialist model
                                       ↓
                  [context bus: task + file + last 3 turns]
                                       ↓
                            Ollama HTTP API → response
```

The classifier is rule-based on `nano`/`base` tiers — no second inference call, adds ~0ms latency.
Context is serialised across model switches so each specialist sees what happened in previous phases.

---

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SDLC_MOE_LANG` | auto | Override locale: `en`, `id`, `hi`, `pt_br` |
| `SDLC_MOE_TIER` | auto | Override tier: `nano`, `base`, `standard`, `extended` |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama server URL |

---

## Requirements

- Python 3.12+
- [Ollama](https://ollama.com) running locally (`ollama serve`)
- Disk space: 4.7 GB (`nano`) — 130 GB (full `extended` stack)
- No GPU required (GPU accelerates but is not mandatory)

---

## License

Licensed under either of:

- [MIT License](LICENSE-MIT)
- [Apache License, Version 2.0](LICENSE-APACHE)

at your option. Commercial use permitted.

---

## Contributing

Issues, PRs, and translations welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).
If you are adding a new model assignment, please include benchmark source links.
