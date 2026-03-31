"""Internationalization support for sdlc-moe."""

import os
from pathlib import Path
from typing import Dict

# Default locale
DEFAULT_LOCALE = "en"

# Supported locales
SUPPORTED_LOCALES = ["en", "id", "hi", "pt_br"]

# Translation cache
_translations: Dict[str, Dict[str, str]] = {}


def get_locale() -> str:
    """Get current locale from environment or system."""
    # Check explicit environment variable first
    locale = os.environ.get("SDLC_MOE_LANG", "").lower()

    # Map common variations
    locale_mapping = {
        "id": "id",
        "in": "id",
        "hi": "hi",
        "pt": "pt_br",
        "pt-br": "pt_br",
        "pt_br": "pt_br",
        "en": "en",
        "en_us": "en",
    }

    locale = locale_mapping.get(locale, DEFAULT_LOCALE)

    # Fallback to default if not supported
    return locale if locale in SUPPORTED_LOCALES else DEFAULT_LOCALE


def load_translations(locale: str) -> Dict[str, str]:
    """Load translations for a locale."""
    if locale in _translations:
        return _translations[locale]

    translations = {}
    locale_file = Path(__file__).parent / f"{locale}.toml"

    if locale_file.exists():
        import tomllib

        try:
            with open(locale_file, "rb") as f:
                data = tomllib.load(f)
                translations = data.get("translations", {})
        except Exception:
            pass

    _translations[locale] = translations
    return translations


def translate(key: str, locale: str = None) -> str:
    """Translate a key to the specified locale."""
    if locale is None:
        locale = get_locale()

    translations = load_translations(locale)
    return translations.get(key, key)
