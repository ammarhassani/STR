"""Localized report field labels (#3), sourced from column_settings
(display_name_en / display_name_ar) so an admin's field-management edits and the
Arabic labels stay in one place. Cached per language; cleared when labels change.
"""
_cache = {}   # lang -> {column_name: label}


def _load(db_manager, lang):
    rows = db_manager.execute_with_retry(
        "SELECT column_name, display_name_en, COALESCE(NULLIF(display_name_ar,''), display_name_en) "
        "FROM column_settings")
    m = {}
    for col, en, ar in (rows or []):
        m[col] = (ar if lang == 'ar' else en) or col
    return m


def field_label(db_manager, column_name, lang='en', default=None, strict=False):
    """Label for a report column in `lang`. Unknown columns fall back to
    `default` (or a humanized column name) — unless `strict`, which returns None
    so the caller can try another source (e.g. the static catalog)."""
    if db_manager is not None:
        if lang not in _cache:
            try:
                _cache[lang] = _load(db_manager, lang)
            except Exception:
                _cache[lang] = {}
        hit = _cache[lang].get(column_name)
        if hit:
            return hit
    if strict:
        return None
    return default or column_name.replace('_', ' ').title()


def clear_cache():
    """Call after an admin edits field labels so the next read reloads."""
    _cache.clear()
