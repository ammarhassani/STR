"""Tiny per-process i18n layer (#3, Phase 0).

The app runs one user at a time, so the active language is a module global set at
login from users.language. `t(key)` returns the string in the active language,
falling back to English (and logging) when a key is missing — so gaps show up as
English text, never as a blank or mojibake.

Translations live in catalog_en.py / catalog_ar.py as flat {key: string} dicts.
English is the source of truth for keys; Arabic is drafted and owner-reviewed.
"""
import logging

_logger = logging.getLogger(__name__)

_current = "en"
_catalogs = {}
_warned = set()


def _load():
    if _catalogs:
        return
    from . import catalog_en, catalog_ar
    _catalogs["en"] = catalog_en.STRINGS
    _catalogs["ar"] = catalog_ar.STRINGS


def available_languages():
    return [("en", "English"), ("ar", "العربية")]


def set_language(lang: str):
    """Set the active language ('en' | 'ar'). Unknown -> English."""
    global _current
    _current = lang if lang in ("en", "ar") else "en"


def get_language() -> str:
    return _current


def is_rtl() -> bool:
    return _current == "ar"


def t(key: str, **fmt) -> str:
    """Translate `key` into the active language. Missing -> English -> the key
    itself. Optional str.format kwargs."""
    _load()
    s = _catalogs.get(_current, {}).get(key)
    if s is None:
        s = _catalogs.get("en", {}).get(key)
        if s is None:
            if key not in _warned:
                _warned.add(key)
                _logger.warning("i18n: missing translation key '%s'", key)
            s = key
        elif _current != "en" and key not in _warned:
            _warned.add(key)
            _logger.info("i18n: no '%s' translation for key '%s' (using English)", _current, key)
    try:
        return s.format(**fmt) if fmt else s
    except (KeyError, IndexError):
        return s
