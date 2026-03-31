# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-03-31

### Added
- Initial release of sdlc-moe - SDLC-aware local LLM orchestrator
- **Core Architecture**
  - Migrated to src/ layout for better packaging hygiene
  - Async HTTP client using httpx (replaced aiohttp)
  - Resource management with proper context managers
  - SDLC phase classifier with heuristic routing
  - Context bus for conversation tracking

- **CLI Commands**
  - `sdlc-moe info` - Show hardware tier and model configuration
  - `sdlc-moe preflight` - Check Ollama and models availability
  - `sdlc-moe run` - Interactive chat with SDLC-aware routing
  - `sdlc-moe fim` - Fill-in-the-middle code completion
  - `sdlc-moe bench` - Benchmark orchestrated vs single model
  - `sdlc-moe dry-run` - Debug routing before execution

- **Hardware Tiers & Models**
  - Nano tier (8GB RAM): Single qwen2.5-coder:7b model
  - Base tier (16GB RAM): Specialist models per phase
  - Standard tier (32GB RAM): Larger models for complex tasks
  - Extended tier (64GB+ RAM): Full stack with llama3.3-70b

- **Cross-Platform Setup**
  - PowerShell setup script for Windows (primary target)
  - Bash setup script for Linux/macOS
  - Automatic RAM detection and tier-appropriate model pulling
  - Ollama installation and configuration

- **Internationalization**
  - Support for English, Indonesian (Bahasa), Hindi, and Portuguese (Brazil)
  - Locale-specific translations for UI elements

- **Developer Tooling**
  - Pre-commit hooks with ruff, ruff-format, and mypy
  - CI/CD pipeline testing Python 3.12/3.13 on Ubuntu/Windows
  - Comprehensive test suite for classifier
  - Benchmark suite for performance comparison

- **Documentation**
  - Contributing guidelines
  - Model assignments with benchmark sources
  - Multi-language quick start guide

### Changed
- **Breaking**: Migrated from flat `sdlc_moe/` to `src/sdlc_moe/` layout
- **Breaking**: Moved bench.py to tests/ folder
- Updated README to show Windows setup first (primary target)

### Fixed
- Resource leaks in OllamaClient with proper async context management
- Config path resolution for src layout
- Classifier confidence scoring and duplicate signal inflation
- Windows PowerShell compatibility (Get-CimInstance vs Get-WmiObject)
- Test expectations to match actual classifier behavior

### Security
- Input validation for Ollama client requests
- Proper error handling for malformed configurations
- Sanitization of user inputs in CLI commands

---

## [Unreleased]

### Planned
- LLM-based classifier for ambiguous prompts
- More granular phase detection
- Performance optimizations
- Additional language support
