"""#22 — hard reset wipes test data, keeps config. Run: python3.14 tests_hard_reset.py"""
import os, sys, tempfile, sqlite3
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_fail = 0
def check(label, cond, detail=""):
    global _fail
    ok = bool(cond)
    print(("PASS " if ok else "FAIL ") + label + ("" if ok else f"  -- {detail}"))
    if not ok:
        _fail += 1


def _seed_db():
    from database.init_db import initialize_database
    from database.migrations import migrate_database
    d = tempfile.mkdtemp(); db = os.path.join(d, "r.db")
    initialize_database(db); migrate_database(db)
    conn = sqlite3.connect(db)
    # test data across transactional tables
    conn.execute("INSERT INTO reports (report_number, sn, report_date, reported_entity_name, created_by) "
                 "VALUES ('R-1', 1, '01/07/2026', 'Test Entity', 'ag1')")
    rid = conn.execute("SELECT report_id FROM reports").fetchone()[0]
    conn.execute("INSERT INTO report_approvals (report_id, approval_status, requested_by) VALUES (?, 'pending', 'ag1')", (rid,))
    conn.execute("INSERT INTO reserved_numbers (report_number, serial_number, owned_by, status) "
                 "VALUES ('R-2', 2, 'ag1', 'available')")
    conn.execute("INSERT INTO system_logs (log_level, module, message) VALUES ('INFO', 'test', 'test log')")
    # extra (test) users
    conn.execute("INSERT INTO users (username, password, full_name, role) VALUES ('ag1','x','Agent One','agent')")
    conn.execute("INSERT INTO users (username, password, full_name, role) VALUES ('rep1','x','Rep One','reporter')")
    conn.commit(); conn.close()
    return db


def _has_cols(conn, table, cols):
    have = [r[1] for r in conn.execute(f"PRAGMA table_info({table})")]
    return all(c in have for c in cols)


def _count(db, table):
    conn = sqlite3.connect(db)
    try:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    finally:
        conn.close()


def test_hard_reset():
    from reset_to_production import hard_reset
    db = _seed_db()

    # config counts BEFORE
    cfg_before = {t: _count(db, t) for t in ['column_settings', 'dashboard_config', 'system_config']}
    check("setup: reports exist", _count(db, 'reports') == 1)
    check("setup: config seeded", all(v > 0 for v in cfg_before.values()), cfg_before)

    summary = hard_reset(db)

    # transactional wiped
    check("reports wiped", _count(db, 'reports') == 0)
    check("approvals wiped", _count(db, 'report_approvals') == 0)
    check("reserved_numbers wiped", _count(db, 'reserved_numbers') == 0)
    check("system_logs wiped", _count(db, 'system_logs') == 0)

    # config preserved (untouched)
    cfg_after = {t: _count(db, t) for t in cfg_before}
    check("column_settings preserved", cfg_after['column_settings'] == cfg_before['column_settings'], cfg_after)
    check("dashboard_config preserved", cfg_after['dashboard_config'] == cfg_before['dashboard_config'], cfg_after)
    check("system_config preserved", cfg_after['system_config'] == cfg_before['system_config'], cfg_after)

    # users -> single fresh admin, must change password
    conn = sqlite3.connect(db)
    users = conn.execute("SELECT username, role, must_change_password FROM users").fetchall()
    lease = conn.execute("SELECT id, host_id, term FROM host_lease").fetchall()
    conn.close()
    check("exactly one user remains", len(users) == 1, users)
    check("the user is admin", users and users[0][0] == 'admin' and users[0][1] == 'admin', users)
    check("admin must change password", users and users[0][2] == 1, users)
    check("host lease reset to unclaimed", lease == [(1, None, 0)], lease)

    # The go-live admin password is GENERATED and returned once -- never a
    # literal. 'admin123' used to be hardcoded here and printed in SETUP.md: a
    # published credential for the only account that exists on a bank's AML
    # system at the moment it goes live with real data.
    from services.security_service import SecurityService
    conn = sqlite3.connect(db)
    pw = conn.execute("SELECT password FROM users WHERE username='admin'").fetchone()[0]
    conn.close()
    generated = summary.get("password")
    check("the reset returns the admin password so it can be shown once",
          bool(generated), summary)
    check("and that password is what the admin account actually has",
          SecurityService.verify_password(generated, pw))
    check("it is NOT the old hardcoded literal",
          not SecurityService.verify_password("admin123", pw))
    check("it is long enough to not be guessable", len(generated) >= 12, generated)

    # ...and a second reset must not produce the same one.
    import importlib
    rp = importlib.import_module("reset_to_production")
    check("two resets do not share a password",
          rp._fresh_admin_password() != rp._fresh_admin_password())

    check("summary reports cleared rows", summary['cleared'].get('reports') == 1, summary)


def test_setup_guide_documents_going_live():
    """A destructive, irreversible step must be written down where it is found.

    This used to check HOST_RUNBOOK.md, which is archived: it described the
    .vbs launchers that no longer exist. The reset now lives in SETUP.md, at
    the end of the path an operator actually walks.
    """
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    guide = open(os.path.join(root, 'docs/SETUP.md'), encoding='utf-8').read()
    check("setup guide documents the hard reset",
          'reset_to_production.py' in guide)
    check("it says the reset cannot be undone",
          'no undo' in guide.lower() or 'cannot be undone' in guide.lower())
    check("it tells the operator to back up FIRST",
          'back up now' in guide.lower())
    check("it says what survives the reset",
          'users' in guide.lower() and 'settings' in guide.lower())


if __name__ == "__main__":
    test_hard_reset()
    test_setup_guide_documents_going_live()
    print(f"\n{'ALL PASS' if _fail == 0 else str(_fail)+' FAILED'}")
    sys.exit(1 if _fail else 0)
