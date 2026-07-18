"""#3 Phase 1a — bilingual dropdown labels + resolution.
Run: python3.14 tests_dropdown_i18n.py"""
import os, sys, tempfile, sqlite3
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_fail = 0
def check(label, cond, detail=""):
    global _fail
    ok = bool(cond)
    print(("PASS " if ok else "FAIL ") + label + ("" if ok else f"  -- {detail}"))
    if not ok:
        _fail += 1

_CATEGORIES = ['gender', 'nationality', 'report_classification', 'report_source',
               'reporting_entity', 'fiu_feedback', 'type_of_suspected_transaction']


def _svc():
    from database.init_db import initialize_database
    from database.migrations import migrate_database
    from database.db_manager import DatabaseManager
    from services.dropdown_service import DropdownService
    d = tempfile.mkdtemp(); db = os.path.join(d, "r.db")
    initialize_database(db); migrate_database(db)
    dbm = DatabaseManager(db)
    return dbm, DropdownService(dbm, None)


def test_arabic_labels_populated():
    dbm, svc = _svc()
    for cat in _CATEGORIES:
        rows = dbm.execute_with_retry(
            "SELECT config_value, config_value_ar FROM system_config "
            "WHERE config_type='dropdown' AND config_category=? AND is_active=1", (cat,))
        missing = [r[0] for r in rows if not (r[1] and r[1].strip())]
        check(f"every active '{cat}' value has an Arabic label", not missing, missing)


def test_get_active_options():
    dbm, svc = _svc()
    en = dict(svc.get_active_options('gender', 'en'))
    ar = dict(svc.get_active_options('gender', 'ar'))
    # codes are config_keys (language-neutral), same set in both languages
    check("same codes regardless of language", set(en) == set(ar), (set(en), set(ar)))
    check("English labels", 'Male' in en.values(), en)
    check("Arabic labels", 'ذكر' in ar.values(), ar)
    # a code maps to different text per language
    code = [k for k, v in en.items() if v == 'Male'][0]
    check("code -> Male (en)", en[code] == 'Male')
    check("same code -> ذكر (ar)", ar[code] == 'ذكر', ar[code])


def test_resolve_label():
    dbm, svc = _svc()
    # resolve by code
    code = svc.get_active_options('gender', 'en')[0][0]
    check("resolve code in en", svc.resolve_label('gender', code, 'en') in
          ['Male', 'Female', 'Other', 'Not Specified'])
    check("resolve code in ar", svc.resolve_label('gender', code, 'ar') in
          ['ذكر', 'أنثى', 'آخر', 'غير محدد'])
    # resolve by legacy stored English label -> Arabic
    check("legacy 'Male' resolves to Arabic", svc.resolve_label('gender', 'Male', 'ar') == 'ذكر')
    check("legacy 'Male' resolves to English", svc.resolve_label('gender', 'Male', 'en') == 'Male')
    # resolve by Arabic value
    check("Arabic value resolves to English", svc.resolve_label('gender', 'ذكر', 'en') == 'Male')
    # unknown / legacy free text passes through
    check("unknown value passes through", svc.resolve_label('gender', 'Xyz', 'ar') == 'Xyz')
    check("empty -> empty", svc.resolve_label('gender', '', 'ar') == '')


def test_other_disambiguated_per_category():
    # 'Other' is آخر for gender but أخرى elsewhere — per-category pairing must hold
    dbm, svc = _svc()
    check("gender Other -> آخر", svc.resolve_label('gender', 'Other', 'ar') == 'آخر')
    check("nationality Other -> أخرى", svc.resolve_label('nationality', 'Other', 'ar') == 'أخرى')


def test_backward_compat_english_values():
    # the legacy getter still returns English labels (unchanged callers keep working)
    dbm, svc = _svc()
    vals = svc.get_active_dropdown_values('gender')
    check("legacy getter still English", 'Male' in vals and 'ذكر' not in vals, vals)


if __name__ == "__main__":
    test_arabic_labels_populated()
    test_get_active_options()
    test_resolve_label()
    test_other_disambiguated_per_category()
    test_backward_compat_english_values()
    print(f"\n{'ALL PASS' if _fail == 0 else str(_fail)+' FAILED'}")
    sys.exit(1 if _fail else 0)
