"""#17 + #4 — config-driven BI: safe read-only widget SQL + admin CRUD.
Run: python3.14 tests_dashboard_config.py"""
import os, sys, tempfile, sqlite3
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_fail = 0
def check(label, cond, detail=""):
    global _fail
    ok = bool(cond)
    print(("PASS " if ok else "FAIL ") + label + ("" if ok else f"  -- {detail}"))
    if not ok:
        _fail += 1


def _services():
    from database.init_db import initialize_database
    from database.migrations import migrate_database
    from database.db_manager import DatabaseManager
    from services.logging_service import LoggingService
    from services.auth_service import AuthService
    from services.dashboard_service import DashboardService
    from services.security_service import SecurityService
    d = tempfile.mkdtemp(); db = os.path.join(d, "r.db")
    initialize_database(db); migrate_database(db)
    dbm = DatabaseManager(db); log = LoggingService(dbm, None, db_logging=False)
    conn = sqlite3.connect(db)
    conn.execute("UPDATE users SET password=?, must_change_password=0 WHERE username='admin'",
                 (SecurityService.hash_password('Admin@1234'),))
    conn.commit(); conn.close()
    auth = AuthService(dbm, log)
    dash = DashboardService(dbm, log, auth)
    return dbm, auth, dash


def test_query_validation():
    from services.dashboard_service import validate_widget_query as v
    check("plain SELECT ok", v("SELECT COUNT(*) FROM reports")[0])
    check("WITH cte ok", v("WITH x AS (SELECT 1 AS n) SELECT n FROM x")[0])
    check("DELETE rejected", not v("DELETE FROM reports")[0])
    check("UPDATE rejected", not v("UPDATE reports SET cic='x'")[0])
    check("DROP rejected", not v("DROP TABLE reports")[0])
    check("ATTACH rejected", not v("SELECT 1; ATTACH DATABASE 'x' AS y")[0])
    check("PRAGMA rejected", not v("PRAGMA table_info(reports)")[0])
    check("stacked statement rejected", not v("SELECT 1; DELETE FROM reports")[0])
    check("sneaky DELETE in comment-stripped body rejected",
          not v("SELECT 1 /* comment */ ; DELETE FROM reports")[0])
    check("empty rejected", not v("")[0])
    check("non-select rejected", not v("VACUUM")[0])
    # keyword as a substring of a column name must NOT trip the word-boundary guard
    check("'created_at' is not a forbidden keyword",
          v("SELECT created_at FROM reports")[0])


def test_run_widget_query_is_readonly():
    dbm, auth, dash = _services()
    auth.authenticate('admin', 'Admin@1234')
    # a legit read works
    ok, rows, cols, err = dash.run_widget_query("SELECT COUNT(*) AS value FROM reports")
    check("read query returns rows", ok and cols == ['value'], (ok, cols, err))

    # a malicious widget query cannot mutate — blocked by validator...
    ok2, _, _, err2 = dash.run_widget_query("DELETE FROM reports")
    check("write query blocked by validator", not ok2, err2)

    # ...and even if the validator were bypassed, the connection is read-only.
    # Prove the ro-connection layer directly:
    import sqlite3 as s
    conn = s.connect(f"file:{dbm.db_path}?mode=ro", uri=True)
    raised = False
    try:
        conn.execute("DELETE FROM reports"); conn.commit()
    except s.Error:
        raised = True
    conn.close()
    check("read-only connection refuses writes (engine-level defense)", raised)


def test_admin_crud_and_gating():
    dbm, auth, dash = _services()
    # non-admin cannot configure
    auth.authenticate('admin', 'Admin@1234')
    auth.create_user('rep1', 'Pass@123', 'Rep', 'reporter')
    auth.authenticate('rep1', 'Pass@123')
    okc, msg = dash.create_widget({'widget_type': 'kpi_card', 'title': 'X',
                                   'sql_query': 'SELECT COUNT(*) AS value FROM reports'})
    check("reporter cannot create a widget", not okc, msg)
    check("reporter sees no admin widget list", dash.list_all_widgets() == [])

    # admin can create a valid widget
    auth.authenticate('admin', 'Admin@1234')
    okc, msg = dash.create_widget({'widget_type': 'kpi_card', 'title': 'My KPI',
                                   'sql_query': 'SELECT COUNT(*) AS value FROM reports',
                                   'visible_to_roles': 'admin'})
    check("admin creates a valid widget", okc, msg)

    # admin cannot create a widget with a dangerous query
    okbad, msgbad = dash.create_widget({'widget_type': 'kpi_card', 'title': 'Evil',
                                        'sql_query': 'DELETE FROM reports'})
    check("dangerous widget query rejected at save", not okbad, msgbad)

    # a broken query is rejected at save (must actually run)
    okbroken, _ = dash.create_widget({'widget_type': 'kpi_card', 'title': 'Broken',
                                      'sql_query': 'SELECT * FROM no_such_table'})
    check("broken widget query rejected at save", not okbroken)

    widgets = dash.list_all_widgets()
    mine = [w for w in widgets if w['title'] == 'My KPI']
    check("created widget appears in admin list", len(mine) == 1, widgets)
    wid = mine[0]['widget_id']

    # update
    oku, msgu = dash.update_widget(wid, {'widget_type': 'kpi_card', 'title': 'Renamed KPI',
                                         'sql_query': 'SELECT COUNT(*) AS value FROM reports',
                                         'visible_to_roles': 'admin'})
    check("admin updates a widget", oku, msgu)
    check("update persisted",
          any(w['title'] == 'Renamed KPI' for w in dash.list_all_widgets()))

    # delete
    okd, _ = dash.delete_widget(wid)
    check("admin deletes a widget", okd)
    check("deleted widget gone",
          all(w['widget_id'] != wid for w in dash.list_all_widgets()))


def test_get_dashboard_widgets_normalizes_and_survives_bad_widget():
    dbm, auth, dash = _services()
    auth.authenticate('admin', 'Admin@1234')
    # seed widgets ship in schema; ensure a bad one doesn't crash the whole board
    dbm.execute_write(
        "INSERT INTO dashboard_config (widget_type, title, sql_query, visible_to_roles, "
        "is_active, display_order, created_by) VALUES "
        "('kpi_card','Bad','DELETE FROM reports','admin',1,99,'SYSTEM')")
    widgets = dash.get_dashboard_widgets('admin')
    check("dashboard still returns widgets despite a bad one", len(widgets) > 0, len(widgets))
    bad = [w for w in widgets if w['title'] == 'Bad']
    check("bad widget carries an error and empty data, not a crash",
          bad and bad[0]['error'] and bad[0]['data'] == [], bad)
    good = [w for w in widgets if w['title'] == 'Total Reports']
    check("good seed widget has normalized dict data",
          good and isinstance(good[0]['data'], list)
          and (not good[0]['data'] or isinstance(good[0]['data'][0], dict)), good)


def test_all_seeded_widgets_valid_and_runnable():
    """Every widget shipped in schema + seeded by migration must pass validation
    and actually run read-only — otherwise it renders a broken error card."""
    dbm, auth, dash = _services()
    auth.authenticate('admin', 'Admin@1234')
    from services.dashboard_service import validate_widget_query
    rows = dbm.execute_with_retry("SELECT title, sql_query FROM dashboard_config")
    check("there are seeded widgets", len(rows) > 6, len(rows))
    for title, sql in rows:
        ok, reason = validate_widget_query(sql)
        check(f"widget validates: {title}", ok, reason)
        run_ok, _r, _c, err = dash.run_widget_query(sql)
        check(f"widget runs read-only: {title}", run_ok, err)

    # the specific #17/#4 charts are present
    titles = {r[0] for r in rows}
    for expected in ['Rework Rate %', 'Reports in Rework', 'Top Reported Entities',
                     'Reports by Classification', 'Repeat CICs (multiple reports)',
                     'Repeat Accounts (possible structuring)', 'Approvals per Month']:
        check(f"BI chart seeded: {expected}", expected in titles, titles)


def test_migration_seed_is_idempotent():
    import os, tempfile
    from database.init_db import initialize_database
    from database.migrations import migrate_database
    from database.db_manager import DatabaseManager
    d = tempfile.mkdtemp(); db = os.path.join(d, "r.db")
    initialize_database(db)
    migrate_database(db); migrate_database(db)  # run twice
    dbm = DatabaseManager(db)
    n = dbm.execute_with_retry(
        "SELECT COUNT(*) FROM dashboard_config WHERE title='Rework Rate %'")[0][0]
    check("re-running migration does not duplicate seeded widgets", n == 1, n)


def test_widgets_never_print_python_at_the_user():
    """A NULL metric reached the dashboard as the literal word "None".

    'Rework Rate %' divides by NULLIF(COUNT(*),0), so with no reports the value
    is NULL -- correct SQL, since a rate over nothing is unknown, not zero. The
    renderer did str(None) and the tile read "None".
    """
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'flet_app'))
    from components.widget_renderer import _single_value
    shown = _single_value([{'value': None}])
    check("a NULL metric is not rendered as the word 'None'", shown != 'None', shown)
    check("it shows an em dash for 'unknown'", shown == '—', shown)
    check("zero is still zero, not unknown", _single_value([{'value': 0}]) == '0')
    check("a whole float loses its .0", _single_value([{'value': 12.0}]) == '12')
    for junk in ([{'value': ''}], [{}], []):
        out = _single_value(junk)
        check(f"{junk!r} renders as text, never a Python repr",
              'None' not in out and '{' not in out, out)


def test_widget_chrome_is_translated():
    """The dashboard was mostly Arabic with English 'no data' and English table
    headers sitting inside a right-to-left layout."""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'flet_app'))
    from i18n import set_language, t
    try:
        for key in ('dash.no_data', 'dash.col.cic', 'dash.col.reports',
                    'dash.col.entities', 'dash.col.account'):
            set_language('en')
            en = t(key)
            set_language('ar')
            ar = t(key)
            check(f"'{key}' has an English string", en != key, en)
            check(f"'{key}' is actually translated for Arabic", ar != key and ar != en,
                  f"en={en!r} ar={ar!r}")
    finally:
        set_language('en')


if __name__ == "__main__":
    test_query_validation()
    test_run_widget_query_is_readonly()
    test_admin_crud_and_gating()
    test_get_dashboard_widgets_normalizes_and_survives_bad_widget()
    test_all_seeded_widgets_valid_and_runnable()
    test_migration_seed_is_idempotent()
    test_widgets_never_print_python_at_the_user()
    test_widget_chrome_is_translated()
    print(f"\n{'ALL PASS' if _fail == 0 else str(_fail)+' FAILED'}")
    sys.exit(1 if _fail else 0)
