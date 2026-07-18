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
    # the STORED value is the English canonical, identical in both languages
    check("stored value is English-canonical in both langs", set(en) == set(ar), (set(en), set(ar)))
    check("value 'Male' present", 'Male' in en, en)
    check("English user sees English", en['Male'] == 'Male')
    check("Arabic user sees Arabic for the same value", ar['Male'] == 'ذكر', ar['Male'])
    check("Arabic user still STORES English 'Male'", 'Male' in ar, ar)


def test_resolve_label():
    dbm, svc = _svc()
    # stored value is the English canonical
    val = svc.get_active_options('gender', 'en')[0][0]
    check("resolve value in en", svc.resolve_label('gender', val, 'en') in
          ['Male', 'Female', 'Other', 'Not Specified'])
    check("resolve value in ar", svc.resolve_label('gender', val, 'ar') in
          ['ذكر', 'أنثى', 'آخر', 'غير محدد'])
    # stored English label -> Arabic for display
    check("stored 'Male' resolves to Arabic", svc.resolve_label('gender', 'Male', 'ar') == 'ذكر')
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


def test_admin_adds_bilingual_value():
    # admin can specify BOTH English and Arabic when adding/editing a value
    import sqlite3
    from database.init_db import initialize_database
    from database.migrations import migrate_database
    from database.db_manager import DatabaseManager
    from services.logging_service import LoggingService
    from services.auth_service import AuthService
    from services.dropdown_service import DropdownService
    from services.security_service import SecurityService
    d = tempfile.mkdtemp(); db = os.path.join(d, "r.db")
    initialize_database(db); migrate_database(db)
    conn = sqlite3.connect(db)
    conn.execute("UPDATE users SET password=?, must_change_password=0 WHERE username='admin'",
                 (SecurityService.hash_password('Admin@1234'),))
    conn.commit(); conn.close()
    dbm = DatabaseManager(db); log = LoggingService(dbm, None, db_logging=False)
    auth = AuthService(dbm, log); auth.authenticate('admin', 'Admin@1234')
    dd = DropdownService(dbm, log, auth)

    ok, _ = dd.add_dropdown_value('nationality', 'Turkish', 'admin', value_ar='تركي')
    check("add value with en+ar succeeds", ok)
    en = dict(dd.get_active_options('nationality', 'en'))
    ar = dict(dd.get_active_options('nationality', 'ar'))
    check("English mode shows the English value", en.get('Turkish') == 'Turkish', en.get('Turkish'))
    check("Arabic mode shows the Arabic value", ar.get('Turkish') == 'تركي', ar.get('Turkish'))

    row = [v for v in dd.get_all_dropdown_values('nationality') if v['value'] == 'Turkish'][0]
    check("get_all_dropdown_values returns value_ar (for edit prefill)", row.get('value_ar') == 'تركي', row)
    ok, _ = dd.update_dropdown_value(row['config_id'], 'Turkish', 'admin', value_ar='تركية')
    check("edit updates the Arabic value", ok)
    ar2 = dict(dd.get_active_options('nationality', 'ar'))
    check("edited Arabic value applied", ar2.get('Turkish') == 'تركية', ar2.get('Turkish'))

    # blank Arabic -> Arabic mode falls back to the English value
    dd.add_dropdown_value('nationality', 'Greek', 'admin', value_ar='')
    arg = dict(dd.get_active_options('nationality', 'ar'))
    check("blank Arabic falls back to English", arg.get('Greek') == 'Greek', arg.get('Greek'))


def test_arb_staff_cleaned_and_paired():
    dbm, svc = _svc()
    en = dict(svc.get_active_options('arb_staff', 'en'))
    ar = dict(svc.get_active_options('arb_staff', 'ar'))
    check("arb_staff is Yes/No (English canonical)", set(en) == {'Yes', 'No'}, en)
    check("arb_staff English labels", en.get('Yes') == 'Yes' and en.get('No') == 'No')
    check("arb_staff Arabic labels", ar.get('Yes') == 'نعم' and ar.get('No') == 'لا', ar)
    check("no MAYBE junk in arb_staff", 'MAYBE' not in en and 'Maybe' not in en, en)


def test_maybe_junk_removed_on_prod_db():
    # simulate a prod DB with a MAYBE value + a report using it
    import sqlite3
    from database.init_db import initialize_database
    from database.migrations import migrate_database
    from database.db_manager import DatabaseManager
    from services.dropdown_service import DropdownService
    d = tempfile.mkdtemp(); db = os.path.join(d, "p.db")
    initialize_database(db); migrate_database(db)   # migrate first drops the legacy CHECK
    conn = sqlite3.connect(db)
    conn.execute("INSERT INTO system_config (config_key, config_value, config_type, config_category, is_active) "
                 "VALUES ('arb_x','MAYBE','dropdown','arb_staff',1)")
    conn.execute("INSERT INTO reports (report_number, sn, report_date, reported_entity_name, arb_staff, created_by) "
                 "VALUES ('R-1',1,'01/07/2026','E','MAYBE','ag1')")
    conn.commit(); conn.close()
    migrate_database(db)   # cleanup removes MAYBE
    svc = DropdownService(DatabaseManager(db), None)
    vals = [v for v, _ in svc.get_active_options('arb_staff', 'en')]
    check("MAYBE dropdown value removed", 'MAYBE' not in vals, vals)
    check("arb_staff cleaned to Yes/No", set(vals) == {'Yes', 'No'}, vals)
    conn = sqlite3.connect(db)
    stored = conn.execute("SELECT arb_staff FROM reports WHERE report_number='R-1'").fetchone()[0]
    conn.close()
    check("stored MAYBE cleared from report", stored == '', repr(stored))


def test_second_reason_arabic_only_always():
    import re
    dbm, svc = _svc()
    ar_re = re.compile(r'[؀-ۿ]')
    vals = [v for v, _ in svc.get_active_options('second_reason_for_suspicion', 'en')]
    check("no English second-reason values remain", all(ar_re.search(v) for v in vals), vals[:2])
    en = svc.get_active_options('second_reason_for_suspicion', 'en')
    ar = svc.get_active_options('second_reason_for_suspicion', 'ar')
    check("second reason shows Arabic in BOTH localizations",
          [l for _, l in en] == [l for _, l in ar] and all(ar_re.search(l) for _, l in en[:3]),
          (en[:1], ar[:1]))


if __name__ == "__main__":
    test_arabic_labels_populated()
    test_admin_adds_bilingual_value()
    test_arb_staff_cleaned_and_paired()
    test_maybe_junk_removed_on_prod_db()
    test_second_reason_arabic_only_always()
    test_get_active_options()
    test_resolve_label()
    test_other_disambiguated_per_category()
    test_backward_compat_english_values()
    print(f"\n{'ALL PASS' if _fail == 0 else str(_fail)+' FAILED'}")
    sys.exit(1 if _fail else 0)
