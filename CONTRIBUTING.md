# Contributing to sdlc-moe

Thank you for your interest in contributing! This document provides guidelines for contributors.

## Development Setup

1. Clone the repository:
```bash
git clone https://github.com/SHA888/sdlc-moe.git
cd sdlc-moe
```

2. Install dependencies:
```bash
pip install uv
uv pip install -e .[dev]
```

3. Install pre-commit hooks:
```bash
pre-commit install
```

## Running Tests

```bash
uv run pytest tests/ -v
```

## Code Style

- Use `uv run ruff format` to format code
- Use `uv run ruff check` to lint code
- Pre-commit hooks enforce these rules

## Adding New Models

When adding a new model assignment:

1. Update `config/models.toml` with the model's Ollama tag
2. Update the appropriate tier profile in `config/profiles/`
3. Include benchmark source links in the commit message
4. Test with `sdlc-moe info` to verify the mapping

## Submitting Changes

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and pre-commit checks
5. Submit a pull request

## Translations

Translations are welcome! Add locale files to `src/sdlc_moe/i18n/` following the existing pattern.
