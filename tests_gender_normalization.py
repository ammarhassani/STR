"""Gender values reconciled to English (open thread #1).
Run: python3.14 tests_gender_normalization.py"""
import os, sys, tempfile, sqlite3
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import utf8_console  # noqa: F401 - this suite prints Arabic values

_fail = 0
def check(label, cond, detail=""):
    global _fail
    ok = bool(cond)
    print(("PASS " if ok else "FAIL ") + label + ("" if ok else f"  -- {detail}"))
    if not ok:
        _fail += 1


def _fresh():
    from database.init_db import initialize_database
    from database.migrations import migrate_database
    d = tempfile.mkdtemp(); db = os.path.join(d, "r.db")
    initialize_database(db); migrate_database(db)
    return db


def _gender_dropdown(db):
    c = sqlite3.connect(db)
    try:
        return [r[0] for r in c.execute(
            "SELECT config_value FROM system_config WHERE config_type='dropdown' "
            "AND config_category='gender' AND is_active=1 ORDER BY display_order")]
    finally:
        c.close()


def test_fresh_db_gender_is_english():
    db = _fresh()
    vals = _gender_dropdown(db)
    check("fresh gender dropdown is English", 'Male' in vals and 'Female' in vals, vals)
    check("no Arabic gender values remain", 'ذكر' not in vals and 'أنثى' not in vals, vals)
    check("canonical English set present",
          set(['Male', 'Female']).issubset(set(vals)), vals)


def test_normalizes_legacy_arabic_db():
    from database.migrations import migrate_database
    db = _fresh()
    c = sqlite3.connect(db)
    # simulate a legacy DB: Arabic gender dropdown + Arabic stored report values
    c.execute("DELETE FROM system_config WHERE config_type='dropdown' AND config_category='gender'")
    c.execute("INSERT INTO system_config (config_key, config_value, config_type, config_category, display_order, is_active) "
              "VALUES ('gender_1','ذكر','dropdown','gender',1,1),('gender_2','أنثى','dropdown','gender',2,1)")
    c.execute("INSERT INTO reports (report_number, sn, report_date, reported_entity_name, gender, created_by) "
              "VALUES ('R-1', 1, '01/07/2026', 'E', 'ذكر', 'ag1')")
    c.execute("INSERT INTO reports (report_number, sn, report_date, reported_entity_name, gender, created_by) "
              "VALUES ('R-2', 2, '02/07/2026', 'E', 'أنثى', 'ag1')")
    # an admin-added custom value that must survive
    c.execute("INSERT INTO system_config (config_key, config_value, config_type, config_category, display_order, is_active) "
              "VALUES ('gender_custom','Prefer not to say','dropdown','gender',9,1)")
    c.commit(); c.close()

    migrate_database(db)  # corrective migration runs

    vals = _gender_dropdown(db)
    check("legacy Arabic dropdown values removed", 'ذكر' not in vals and 'أنثى' not in vals, vals)
    check("English canonical present after normalize", 'Male' in vals and 'Female' in vals, vals)
    check("admin-added custom gender value preserved", 'Prefer not to say' in vals, vals)

    c = sqlite3.connect(db)
    genders = dict(c.execute("SELECT report_number, gender FROM reports ORDER BY report_number"))
    c.close()
    check("stored 'ذكر' normalized to Male", genders.get('R-1') == 'Male', genders)
    check("stored 'أنثى' normalized to Female", genders.get('R-2') == 'Female', genders)


def test_idempotent():
    from database.migrations import migrate_database
    db = _fresh()
    migrate_database(db); migrate_database(db)  # extra runs
    vals = _gender_dropdown(db)
    # no duplicates from repeated INSERT OR IGNORE
    check("no duplicate gender values after repeated migrations", len(vals) == len(set(vals)), vals)


def test_service_returns_english():
    from database.db_manager import DatabaseManager
    from services.dropdown_service import DropdownService
    db = _fresh()
    svc = DropdownService(DatabaseManager(db), None)
    vals = svc.get_active_dropdown_values('gender')
    check("dropdown_service serves English gender", 'Male' in vals and 'أنثى' not in vals, vals)


if __name__ == "__main__":
    test_fresh_db_gender_is_english()
    test_normalizes_legacy_arabic_db()
    test_idempotent()
    test_service_returns_english()
    print(f"\n{'ALL PASS' if _fail == 0 else str(_fail)+' FAILED'}")
    sys.exit(1 if _fail else 0)
