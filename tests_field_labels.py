"""#3 Phase 2 — localized field labels. Run: python3.14 tests_field_labels.py"""
import os, sys, tempfile, sqlite3
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'flet_app'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_fail = 0
def check(label, cond, detail=""):
    global _fail
    ok = bool(cond)
    print(("PASS " if ok else "FAIL ") + label + ("" if ok else f"  -- {detail}"))
    if not ok:
        _fail += 1


def _db():
    from database.init_db import initialize_database
    from database.migrations import migrate_database
    from database.db_manager import DatabaseManager
    d = tempfile.mkdtemp(); db = os.path.join(d, "r.db")
    initialize_database(db); migrate_database(db)
    return DatabaseManager(db)


def test_arabic_labels_clean():
    dbm = _db()
    rows = dbm.execute_with_retry(
        "SELECT column_name, display_name_ar FROM column_settings")
    # mojibake double-encoding shows up as the 'Ø' / 'Ù' byte-pair artifacts
    bad = [c for c, ar in rows if ar and ('Ø' in ar or 'Ù' in ar)]
    check("no mojibake left in Arabic field labels", not bad, bad)
    m = dict(rows)
    check("report_number Arabic is clean", m.get('report_number') == 'رقم التقرير', m.get('report_number'))
    check("gender Arabic is clean", m.get('gender') == 'الجنس', m.get('gender'))


def test_field_label_resolver():
    from i18n.fields import field_label, clear_cache
    clear_cache()
    dbm = _db()
    check("English label", field_label(dbm, 'report_number', 'en') == 'Report Number')
    check("Arabic label", field_label(dbm, 'report_number', 'ar') == 'رقم التقرير')
    check("unknown column humanized", field_label(dbm, 'some_new_col', 'en') == 'Some New Col')
    check("unknown column default honored",
          field_label(dbm, 'x', 'en', default='Custom') == 'Custom')
    check("no db_manager -> humanized", field_label(None, 'total_transaction', 'ar') == 'Total Transaction')


if __name__ == "__main__":
    test_arabic_labels_clean()
    test_field_label_resolver()
    print(f"\n{'ALL PASS' if _fail == 0 else str(_fail)+' FAILED'}")
    sys.exit(1 if _fail else 0)
