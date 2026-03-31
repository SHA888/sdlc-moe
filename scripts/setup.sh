#!/usr/bin/env bash
# sdlc-moe setup script
# Installs Ollama (if missing) and pulls the right models for your hardware tier.
# Safe to re-run — already-pulled models are skipped automatically.
#
# Usage:
#   bash setup.sh              # auto-detect tier
#   bash setup.sh --tier nano  # force nano tier (8 GB RAM)
#   bash setup.sh --tier base  # force base tier (16 GB RAM)

set -euo pipefail

TIER="${SDLC_MOE_TIER:-}"
OLLAMA_URL="${OLLAMA_URL:-http://localhost:11434}"

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --tier) TIER="$2"; shift 2 ;;
    --ollama-url) OLLAMA_URL="$2"; shift 2 ;;
    *) echo "Unknown arg: $1" >&2; exit 1 ;;
  esac
done

# ── Colours ────────────────────────────────────────────────────────────────
if [[ -t 1 ]]; then
  GRN="\033[0;32m"; YLW="\033[0;33m"; RED="\033[0;31m"; RST="\033[0m"; BLD="\033[1m"
else
  GRN=""; YLW=""; RED=""; RST=""; BLD=""
fi

info()  { echo -e "${GRN}✓${RST}  $*"; }
warn()  { echo -e "${YLW}!${RST}  $*"; }
error() { echo -e "${RED}✗${RST}  $*" >&2; }
step()  { echo -e "\n${BLD}$*${RST}"; }

# ── Detect RAM and tier ─────────────────────────────────────────────────────
detect_tier() {
  local ram_kb ram_gb
  if [[ -f /proc/meminfo ]]; then
    ram_kb=$(awk '/MemTotal/ {print $2}' /proc/meminfo)
    # Use floating point arithmetic for better accuracy
    ram_gb=$(echo "scale=1; $ram_kb / 1024 / 1024" | bc -l 2>/dev/null || echo $(( ram_kb / 1024 / 1024 )))
  elif command -v sysctl &>/dev/null; then
    # macOS
    local ram_bytes
    ram_bytes=$(sysctl -n hw.memsize 2>/dev/null || echo 0)
    ram_gb=$(echo "scale=1; $ram_bytes / 1024 / 1024 / 1024" | bc -l 2>/dev/null || echo $(( ram_bytes / 1024 / 1024 / 1024 )))
  else
    warn "Cannot detect RAM. Defaulting to nano tier."
    echo "nano"; return
  fi

  # Compare using integer arithmetic (multiply by 10 to preserve 1 decimal place)
  local ram_gb_int=${ram_gb%.*}  # integer part
  local ram_gb_dec=${ram_gb#*.} # decimal part
  local ram_gb_x10=$(( ram_gb_int * 10 + ${ram_gb_dec:-0} ))

  if   (( ram_gb_x10 < 120 )); then echo "nano"   # < 12.0 GB
  elif (( ram_gb_x10 < 240 )); then echo "base"   # < 24.0 GB
  elif (( ram_gb_x10 < 640 )); then echo "standard" # < 64.0 GB
  else                              echo "extended"
  fi
}

if [[ -z "$TIER" ]]; then
  TIER=$(detect_tier)
fi

# Model lists per tier (Ollama tags)
declare -A TIER_MODELS
TIER_MODELS[nano]="qwen2.5-coder:7b"
TIER_MODELS[base]="qwen2.5-coder:7b deepseek-r1:14b phi4:14b starcoder2:15b deepseek-coder-v2:16b gemma3:12b"
TIER_MODELS[standard]="qwen2.5-coder:7b qwen2.5-coder:32b deepseek-r1:14b phi4:14b mistral-small3:24b starcoder2:15b deepseek-coder-v2:16b gemma3:12b"
TIER_MODELS[extended]="qwen2.5-coder:7b qwen2.5-coder:32b deepseek-r1:14b phi4:14b mistral-small3:24b starcoder2:15b deepseek-coder-v2:16b gemma3:12b llama3.3:70b"

if [[ -z "${TIER_MODELS[$TIER]+_}" ]]; then
  error "Unknown tier: $TIER. Valid: nano base standard extended"
  exit 1
fi

# ── Banner ──────────────────────────────────────────────────────────────────
echo ""
echo -e "${BLD}sdlc-moe setup${RST}"
echo "  Tier:   ${BLD}${TIER}${RST}"
echo "  Models: ${TIER_MODELS[$TIER]}"
echo ""

# ── 1. Python 3.12+ check ──────────────────────────────────────────────────
step "1/4  Checking Python"
PYTHON=""
for candidate in python3.13 python3.12 python3; do
  if command -v "$candidate" &>/dev/null; then
    version=$("$candidate" -c 'import sys; print(sys.version_info[:2])')
    if "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3,12) else 1)' 2>/dev/null; then
      PYTHON="$candidate"
      info "Found $PYTHON ($version)"
      break
    fi
  fi
done
if [[ -z "$PYTHON" ]]; then
  error "Python 3.12+ is required. Install from https://python.org or your package manager."
  exit 1
fi

# ── 2. uv check / install ──────────────────────────────────────────────────
step "2/4  Checking uv"
if ! command -v uv &>/dev/null; then
  warn "uv not found. Installing..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  # Add uv to PATH for this session
  export PATH="$HOME/.cargo/bin:$HOME/.local/bin:$PATH"
fi
if command -v uv &>/dev/null; then
  info "uv $(uv --version)"
else
  error "uv installation failed. Install manually: https://docs.astral.sh/uv/getting-started/installation/"
  exit 1
fi

# ── 3. Ollama check / install ──────────────────────────────────────────────
step "3/4  Checking Ollama"
if ! command -v ollama &>/dev/null; then
  warn "Ollama not found. Installing..."
  if [[ "$(uname)" == "Darwin" ]]; then
    if command -v brew &>/dev/null; then
      brew install ollama
    else
      warn "Homebrew not found. Download Ollama from https://ollama.com/download"
      exit 1
    fi
  else
    curl -fsSL https://ollama.com/install.sh | sh
  fi
fi

if ! command -v ollama &>/dev/null; then
  error "Ollama installation failed. Install from https://ollama.com"
  exit 1
fi
info "Ollama $(ollama --version 2>/dev/null | head -1)"

# Start Ollama server if not already running
OLLAMA_PID=""
if ! curl -sf "${OLLAMA_URL}/api/tags" >/dev/null 2>&1; then
  warn "Ollama server not running. Starting in background..."
  ollama serve &>/tmp/ollama-serve.log &
  OLLAMA_PID=$!

  # Trap to clean up background process on script exit
  cleanup_ollama() {
    if [[ -n "$OLLAMA_PID" ]] && kill -0 "$OLLAMA_PID" 2>/dev/null; then
      info "Stopping Ollama server (pid $OLLAMA_PID)..."
      kill "$OLLAMA_PID" 2>/dev/null || true
      wait "$OLLAMA_PID" 2>/dev/null || true
    fi
  }
  trap cleanup_ollama EXIT INT TERM

  # Wait up to 15s for it to start
  for i in $(seq 1 15); do
    sleep 1
    if curl -sf "${OLLAMA_URL}/api/tags" >/dev/null 2>&1; then
      info "Ollama server started (pid $OLLAMA_PID)"
      break
    fi
    if [[ $i -eq 15 ]]; then
      error "Ollama server did not start. Check /tmp/ollama-serve.log"
      exit 1
    fi
  done
else
  info "Ollama server already running"
fi

# ── 4. Pull models ─────────────────────────────────────────────────────────
step "4/4  Pulling models for tier '${TIER}'"
warn "Models are large. This will take time on slow connections."
warn "Safe to interrupt (Ctrl+C) and re-run — Ollama resumes partial downloads."
echo ""

PULLED=0
SKIPPED=0
FAILED=0

for model in ${TIER_MODELS[$TIER]}; do
  # Check if already available
  if ollama list 2>/dev/null | grep -q "^${model%:*}"; then
    info "Already pulled: $model"
    (( SKIPPED++ )) || true
    continue
  fi

  echo -e "${YLW}↓${RST}  Pulling $model..."
  if ollama pull "$model"; then
    info "Pulled: $model"
    (( PULLED++ )) || true
  else
    error "Failed to pull: $model (check connection and retry)"
    (( FAILED++ )) || true
  fi
done

# ── Summary ─────────────────────────────────────────────────────────────────
echo ""
echo -e "${BLD}Setup complete${RST}"
echo "  Pulled:  $PULLED"
echo "  Skipped: $SKIPPED (already available)"
if [[ $FAILED -gt 0 ]]; then
  echo -e "  ${RED}Failed:  $FAILED${RST} — re-run this script to retry"
fi

echo ""
echo "Next steps:"
echo "  cd /path/to/this/repo"
echo "  uv pip install -e .        # install locally for development"
echo "  uv tool install sdlc-moe   # install from PyPI (when published)"
echo "  pre-commit install         # set up git hooks (optional)"
echo "  sdlc-moe info              # confirm your tier"
echo "  sdlc-moe preflight         # verify all models are ready"
echo "  sdlc-moe run \"write a Python function to parse CSV\""
