# sdlc-moe Windows Setup Script
# Installs Ollama (if missing) and pulls the right models for your hardware tier.
# Safe to re-run — already-pulled models are skipped automatically.
#
# Usage:
#   .\setup.ps1              # auto-detect tier
#   .\setup.ps1 -Tier nano   # force nano tier (8 GB RAM)
#   .\setup.ps1 -Tier base   # force base tier (16 GB RAM)

param(
    [string]$Tier = "",
    [string]$OllamaUrl = "http://localhost:11434"
)

# Enable TLS 1.2 for HTTPS requests
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

# ── Helper functions ─────────────────────────────────────────────────────────────
function Write-Info($Message) {
    Write-Host "✓  $Message" -ForegroundColor Green
}

function Write-Warn($Message) {
    Write-Host "!  $Message" -ForegroundColor Yellow
}

function Write-Error($Message) {
    Write-Host "✗  $Message" -ForegroundColor Red
}

function Write-Step($Message) {
    Write-Host "`n$Message" -ForegroundColor Cyan
}

# ── Detect RAM and tier ───────────────────────────────────────────────────────
function Get-DetectedTier {
    try {
        $ram = Get-CimInstance -ClassName Win32_ComputerSystem | Select-Object -ExpandProperty TotalPhysicalMemory
        $ramGB = [math]::Round($ram / 1GB, 1)

        Write-Host "Detected RAM: $ramGB GB"

        if ($ramGB -lt 12) { return "nano" }
        elseif ($ramGB -lt 24) { return "base" }
        elseif ($ramGB -lt 64) { return "standard" }
        else { return "extended" }
    }
    catch {
        Write-Warn "Cannot detect RAM. Defaulting to nano tier."
        return "nano"
    }
}

if ([string]::IsNullOrEmpty($Tier)) {
    $Tier = Get-DetectedTier
}

# Model lists per tier (Ollama tags)
$TierModels = @{
    "nano" = @("qwen2.5-coder:7b")
    "base" = @("qwen2.5-coder:7b", "deepseek-r1:14b", "phi4:14b", "starcoder2:15b", "deepseek-coder-v2:16b", "gemma3:12b")
    "standard" = @("qwen2.5-coder:7b", "qwen2.5-coder:32b", "deepseek-r1:14b", "phi4:14b", "mistral-small3:24b", "starcoder2:15b", "deepseek-coder-v2:16b", "gemma3:12b")
    "extended" = @("qwen2.5-coder:7b", "qwen2.5-coder:32b", "deepseek-r1:14b", "phi4:14b", "mistral-small3:24b", "starcoder2:15b", "deepseek-coder-v2:16b", "gemma3:12b", "llama3.3:70b")
}

if (-not $TierModels.ContainsKey($Tier)) {
    Write-Error "Unknown tier: $Tier. Valid: nano, base, standard, extended"
    exit 1
}

# ── Banner ─────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "sdlc-moe setup" -ForegroundColor Cyan
Write-Host "  Tier:   $Tier" -ForegroundColor Cyan
Write-Host "  Models: $($TierModels[$Tier] -join ' ')" -ForegroundColor Cyan
Write-Host ""

# ── 1. Python 3.12+ check ────────────────────────────────────────────────────────
Write-Step "1/4  Checking Python"
$Python = ""
$pythonCmds = @("python", "python3", "py")

foreach ($cmd in $pythonCmds) {
    try {
        $version = & $cmd --version 2>$null
        if ($LASTEXITCODE -eq 0) {
            $verParts = $version -split ' '
            $verNum = $verParts[-1]
            $major, $minor = $verNum -split '\.'
            if ([int]$major -gt 3 -or ([int]$major -eq 3 -and [int]$minor -ge 12)) {
                $Python = $cmd
                Write-Info "Found $cmd ($verNum)"
                break
            }
        }
    }
    catch { }
}

if ([string]::IsNullOrEmpty($Python)) {
    Write-Error "Python 3.12+ is required. Install from https://python.org"
    exit 1
}

# ── 2. uv check / install ────────────────────────────────────────────────────────
Write-Step "2/4  Checking uv"
try {
    $uvVersion = uv --version 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Info "uv $uvVersion"
    }
    else {
        throw "uv not found"
    }
}
catch {
    Write-Warn "uv not found. Installing..."
    try {
        # Download and install uv
        $installerUrl = "https://astral.sh/uv/install.ps1"
        $installerPath = Join-Path $env:TEMP "uv-install.ps1"
        Invoke-WebRequest -Uri $installerUrl -OutFile $installerPath
        & $installerPath
        Remove-Item $installerPath

        # Add uv to PATH for this session
        $uvPath = Join-Path $env:USERPROFILE ".cargo\bin"
        if ($env:PATH -notlike "*$uvPath*") {
            $env:PATH = "$uvPath;$env:PATH"
        }

        $uvVersion = uv --version 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Info "uv $uvVersion"
        }
        else {
            throw "uv installation failed"
        }
    }
    catch {
        Write-Error "uv installation failed. Install manually: https://docs.astral.sh/uv/getting-started/installation/"
        exit 1
    }
}

# ── 3. Ollama check / install ──────────────────────────────────────────────────────
Write-Step "3/4  Checking Ollama"
$OllamaExe = "ollama.exe"
$OllamaPath = Get-Command $OllamaExe -ErrorAction SilentlyContinue

if (-not $OllamaPath) {
    Write-Warn "Ollama not found. Installing..."
    try {
        # Download Ollama
        $ollamaUrl = "https://ollama.com/download/OllamaSetup.exe"
        $ollamaPath = Join-Path $env:TEMP "OllamaSetup.exe"
        Write-Host "Downloading Ollama..."
        Invoke-WebRequest -Uri $ollamaUrl -OutFile $ollamaPath

        Write-Host "Running Ollama installer..."
        Start-Process -FilePath $ollamaPath -Wait

        Remove-Item $ollamaPath

        # Refresh PATH
        $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "User")
    }
    catch {
        Write-Error "Ollama installation failed. Install from https://ollama.com"
        exit 1
    }
}

# Check if Ollama is available
$OllamaPath = Get-Command $OllamaExe -ErrorAction SilentlyContinue
if (-not $OllamaPath) {
    Write-Error "Ollama installation failed. Install from https://ollama.com"
    exit 1
}

try {
    $ollamaVersion = & $OllamaExe --version 2>$null
    Write-Info "Ollama $ollamaVersion"
}
catch { }

# Start Ollama server if not running
$OllamaProcess = Get-Process -Name "ollama" -ErrorAction SilentlyContinue
if (-not $OllamaProcess) {
    try {
        $response = Invoke-WebRequest -Uri "$OllamaUrl/api/tags" -TimeoutSec 5 -ErrorAction Stop
        Write-Info "Ollama server already running"
    }
    catch {
        Write-Warn "Ollama server not running. Starting in background..."
        Start-Process -FilePath $OllamaExe -ArgumentList "serve" -WindowStyle Hidden

        # Wait up to 15s for it to start
        $started = $false
        for ($i = 1; $i -le 15; $i++) {
            Start-Sleep -Seconds 1
            try {
                $response = Invoke-WebRequest -Uri "$OllamaUrl/api/tags" -TimeoutSec 5 -ErrorAction Stop
                Write-Info "Ollama server started"
                $started = $true
                break
            }
            catch { }
        }

        if (-not $started) {
            Write-Error "Ollama server did not start. Check Ollama logs."
            exit 1
        }
    }
}
else {
    Write-Info "Ollama server already running"
}

# ── 4. Pull models ─────────────────────────────────────────────────────────────
Write-Step "4/4  Pulling models for tier '$Tier'"
Write-Warn "Models are large. This will take time on slow connections."
Write-Warn "Safe to interrupt (Ctrl+C) and re-run — Ollama resumes partial downloads."
Write-Host ""

$Pulled = 0
$Skipped = 0
$Failed = 0

foreach ($model in $TierModels[$Tier]) {
    # Check if already available
    try {
        $models = & $OllamaExe list 2>$null | ConvertFrom-Json
        $modelName = ($model -split ':')[0]
        $alreadyPulled = $models.name -contains $modelName

        if ($alreadyPulled) {
            Write-Info "Already pulled: $model"
            $Skipped++
            continue
        }
    }
    catch { }

    Write-Host "↓  Pulling $model..." -ForegroundColor Yellow
    try {
        & $OllamaExe pull $model
        if ($LASTEXITCODE -eq 0) {
            Write-Info "Pulled: $model"
            $Pulled++
        }
        else {
            throw "Pull failed"
        }
    }
    catch {
        Write-Error "Failed to pull: $model (check connection and retry)"
        $Failed++
    }
}

# ── Summary ─────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "Setup complete" -ForegroundColor Cyan
Write-Host "  Pulled:  $Pulled"
Write-Host "  Skipped: $Skipped (already available)"
if ($Failed -gt 0) {
    Write-Host "  Failed:  $Failed — re-run this script to retry" -ForegroundColor Red
}

Write-Host ""
Write-Host "Next steps:"
Write-Host "  cd \path\to\this\repo"
Write-Host "  uv pip install -e .        # install locally for development"
Write-Host "  uv tool install sdlc-moe   # install from PyPI (when published)"
Write-Host "  pre-commit install         # set up git hooks (optional)"
Write-Host "  sdlc-moe info              # confirm your tier"
Write-Host "  sdlc-moe preflight         # verify all models are ready"
Write-Host "  sdlc-moe run `"write a Python function to parse CSV`""
