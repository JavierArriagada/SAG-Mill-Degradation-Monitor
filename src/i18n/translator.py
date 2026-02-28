"""
src/i18n/translator.py
───────────────────────
Simple translation engine using JSON locale files.

Usage:
    from src.i18n.translator import t, set_lang

    t("nav.overview")              # → "Resumen" (es) / "Overview" (en)
    t("equipment.vibration")       # → "Vibración"
    set_lang("en")
    t("nav.overview")              # → "Overview"
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_LOCALES_DIR = Path(__file__).parent / "locales"
_current_lang: str = "es"


@lru_cache(maxsize=4)
def _load_locale(lang: str) -> dict:
    path = _LOCALES_DIR / f"{lang}.json"
    if not path.exists():
        path = _LOCALES_DIR / "es.json"  # fallback
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def set_lang(lang: str) -> None:
    """Set the active language (module-level default)."""
    global _current_lang
    _current_lang = lang if lang in ("es", "en") else "es"


def t(key: str, lang: str | None = None) -> str:
    """
    Translate a dot-separated key.

    Args:
        key: Dot-separated path, e.g. "nav.overview" or "alerts.title"
        lang: Language override; uses module default if None

    Returns:
        Translated string, or the key itself if not found.
    """
    locale = _load_locale(lang or _current_lang)
    parts = key.split(".")
    node: dict | str = locale
    for part in parts:
        if isinstance(node, dict):
            node = node.get(part, key)
        else:
            return key
    return str(node)


def get_lang() -> str:
    return _current_lang
