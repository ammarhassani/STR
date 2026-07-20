"""#8 — supervisor role + approval routing + RBAC. Run: python3.14 tests_roles.py"""
import os, sys, tempfile, sqlite3
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
    from services.report_service import ReportService
    from services.report_number_service import ReportNumberService
    from services.activity_service import ActivityService
    from services.version_service import VersionService
    from services.approval_service import ApprovalService
    from services.security_service import SecurityService
    d = tempfile.mkdtemp(); db = os.path.join(d, "r.db")
    initialize_database(db); migrate_database(db)
    dbm = DatabaseManager(db); log = LoggingService(dbm, None, db_logging=False)
    conn = sqlite3.connect(db)
    conn.execute("UPDATE users SET password=?, must_change_password=0 WHERE username='admin'",
                 (SecurityService.hash_password('Admin@1234'),))
    conn.commit(); conn.close()
    auth = AuthService(dbm, log)
    activity = ActivityService(dbm, log, auth)
    numbers = ReportNumberService(dbm, log)
    reports = ReportService(dbm, log, auth); reports.set_activity_service(activity)
    reports.set_report_number_service(numbers)
    versions = VersionService(dbm, log, auth, reports, activity)
    approvals = ApprovalService(dbm, log, auth, versions, reports, activity)
    return dbm, auth, numbers, reports, approvals


def _make_and_submit(dbm, auth, numbers, reports, username, approvals=None):
    """Log in as `username`, reserve + create a report, then walk it through the
    real working order: a saved report waits in the pending-FIU basket until the
    FIU number is typed back in, and only then can it be submitted.
    Returns (ok, report_id, approval_id, message)."""
    auth.authenticate(username, 'Pass@123')
    numbers.reserve_block(username, 2)
    ok, rid, msg = reports.create_report({
        'report_date': '01/07/2026', 'reported_entity_name': f'E {username}',
        'nationality': 'Saudi Arabian', 'total_transaction': '1000',
        # filed on the FIU portal in the same sitting -- the agent's choice
        'fiu_number': f'FIU-{username}-001', 'fiu_date': '02/07/2026'})
    if ok and approvals is not None:
        approvals.request_approval(rid, 'submitted for review')
    ap = dbm.execute_with_retry(
        "SELECT approval_id FROM report_approvals WHERE report_id=? AND approval_status='pending' "
        "ORDER BY approval_id DESC LIMIT 1", (rid,)) if ok else None
    return (ok, rid, ap[0][0] if ap else None, msg)


def test_permissions_map():
    from utils.permissions import has_permission
    check("supervisor CAN approve_reports", has_permission('supervisor', 'approve_reports'))
    check("agent CANNOT approve_reports", not has_permission('agent', 'approve_reports'))
    check("reporter CANNOT approve_reports", not has_permission('reporter', 'approve_reports'))
    check("admin CAN approve_reports", has_permission('admin', 'approve_reports'))
    check("supervisor CAN add_report (has agent powers)", has_permission('supervisor', 'add_report'))
    check("reporter CANNOT add_report", not has_permission('reporter', 'add_report'))
    check("supervisor edit_report own-only (own)", has_permission('supervisor', 'edit_report', 'sup1', 'sup1'))
    check("supervisor edit_report own-only (other -> no)", not has_permission('supervisor', 'edit_report', 'ag1', 'sup1'))


def test_role_creation_and_routing():
    dbm, auth, numbers, reports, approvals = _services()
    auth.authenticate('admin', 'Admin@1234')
    for u, role in [('sup1', 'supervisor'), ('sup2', 'supervisor'), ('ag1', 'agent'), ('rep1', 'reporter')]:
        ok, msg = auth.create_user(u, 'Pass@123', u.title(), role)
        check(f"admin creates {role} '{u}'", ok, msg)
    got = dbm.execute_with_retry("SELECT role FROM users WHERE username='sup1'")
    check("supervisor role persisted (DB CHECK allows it)", got and got[0][0] == 'supervisor', got)
    check("invalid role rejected", not auth.create_user('bad', 'x', 'x', 'wizard')[0])

    # agent submits -> supervisor approves
    ok, rid, apid, msg = _make_and_submit(dbm, auth, numbers, reports, 'ag1', approvals)
    check("agent report reaches approval once its FIU details are in", ok and apid, msg)
    auth.authenticate('sup1', 'Pass@123')
    pend_ids = [p['approval_id'] for p in approvals.get_pending_approvals()]
    check("supervisor sees the pending approval", apid in pend_ids, pend_ids)
    oka, msga = approvals.approve_report(apid, 'looks good')
    check("supervisor approves the agent's report", oka, msga)

    # agent cannot approve
    ok2, rid2, apid2, _ = _make_and_submit(dbm, auth, numbers, reports, 'ag1', approvals)
    auth.authenticate('ag1', 'Pass@123')
    check("agent sees no approval queue", approvals.get_pending_approvals() == [])
    okd, _ = approvals.approve_report(apid2, 'x')
    check("agent CANNOT approve", not okd)

    # reporter cannot create nor approve
    auth.authenticate('rep1', 'Pass@123')
    okc, _r, _m = reports.create_report({'report_date': '01/07/2026', 'reported_entity_name': 'x'})
    check("reporter CANNOT create a report", not okc)
    okr, _ = approvals.approve_report(apid2, 'x')
    check("reporter CANNOT approve", not okr)

    # SoD: a supervisor cannot approve their OWN submission; another approver can
    oks, rids, apids, _ = _make_and_submit(dbm, auth, numbers, reports, 'sup1', approvals)
    check("supervisor's own report reaches approval too", oks and apids)
    auth.authenticate('sup1', 'Pass@123')
    okself, msgself = approvals.approve_report(apids, 'self')
    check("supervisor CANNOT approve own report (SoD)", not okself, msgself)
    auth.authenticate('sup2', 'Pass@123')
    okother, msgother = approvals.approve_report(apids, 'peer ok')
    check("a DIFFERENT approver can approve it", okother, msgother)


def test_only_the_owner_can_submit_for_approval():
    """Submitting is an act on the report, so it takes the same right as editing.

    request_approval checked authentication, the report's status and its FIU
    fields -- but never asked whether THIS user was entitled to the report. Any
    authenticated account could therefore push any report into a supervisor's
    queue: a reporter, who has no data-entry rights at all, or one agent
    dumping another agent's half-finished work in front of a supervisor. The
    warzone caught it only intermittently, because it needs someone else's
    submittable report to exist first; these cases make it deterministic.
    """
    dbm, auth, numbers, reports, approvals = _services()
    auth.authenticate('admin', 'Admin@1234')
    for u, role in [('ag1', 'agent'), ('ag2', 'agent'), ('rep1', 'reporter')]:
        auth.create_user(u, 'Pass@123', u.title(), role)

    # Each intruder gets its OWN untouched report. Sharing one report made the
    # second assertion pass even with the gate removed -- the first intruder's
    # successful submit left the report pending, so the second was refused as
    # "already pending approval" rather than on the rule under test.
    ok1, rid1, _a1, msg1 = _make_and_submit(dbm, auth, numbers, reports, 'ag1')
    ok2, rid2, _a2, msg2 = _make_and_submit(dbm, auth, numbers, reports, 'ag1')
    check("ag1 has two reports waiting in the basket", ok1 and ok2, msg1 or msg2)

    auth.authenticate('rep1', 'Pass@123')
    okr, _, msgr = approvals.request_approval(rid1, 'not my report')
    check("reporter CANNOT submit someone else's report", not okr, msgr)

    auth.authenticate('ag2', 'Pass@123')
    oka, _, msga = approvals.request_approval(rid2, 'not my report either')
    check("an agent CANNOT submit another agent's report", not oka, msga)

    rows = dbm.execute_with_retry(
        "SELECT approval_status FROM reports WHERE report_id IN (?,?)", (rid1, rid2))
    check("neither report left its basket",
          all(r[0] != 'pending_approval' for r in rows), [r[0] for r in rows])

    # and the owner is still able to submit their own
    auth.authenticate('ag1', 'Pass@123')
    oko, apid, msgo = approvals.request_approval(rid1, 'mine, filed with the FIU')
    check("the owner CAN still submit their own report", oko and apid, msgo)


def test_migration_rebuilds_old_check():
    """An existing DB whose users CHECK predates 'supervisor' gets rebuilt so the
    role can be inserted."""
    from database.init_db import initialize_database
    from database.migrations import migrate_database
    d = tempfile.mkdtemp(); db = os.path.join(d, "old.db")
    initialize_database(db)
    conn = sqlite3.connect(db)
    # simulate the OLD schema: rebuild users with the pre-#8 CHECK (view-safe)
    conn.execute("PRAGMA legacy_alter_table=ON")
    conn.executescript("""
        CREATE TABLE users_old (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL COLLATE NOCASE,
            password TEXT NOT NULL, full_name TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin','agent','reporter')),
            is_active INTEGER DEFAULT 1, failed_login_attempts INTEGER DEFAULT 0,
            last_login TEXT, theme_preference TEXT DEFAULT 'light',
            created_at TEXT DEFAULT (datetime('now')), created_by TEXT,
            updated_at TEXT, updated_by TEXT
        );
        INSERT INTO users_old (user_id, username, password, full_name, role)
            SELECT user_id, username, password, full_name, role FROM users;
        DROP TABLE users;
        ALTER TABLE users_old RENAME TO users;
    """)
    conn.execute("PRAGMA legacy_alter_table=OFF")
    conn.commit()
    # old CHECK must reject supervisor
    rejected = False
    try:
        conn.execute("INSERT INTO users (username,password,full_name,role) VALUES ('s','x','S','supervisor')")
    except sqlite3.IntegrityError:
        rejected = True
    conn.close()
    check("old CHECK rejects supervisor before migration", rejected)
    # run migrations -> should rebuild the CHECK
    migrate_database(db)
    conn = sqlite3.connect(db)
    ok = True
    try:
        conn.execute("INSERT INTO users (username,password,full_name,role) VALUES ('s2','x','S2','supervisor')")
        conn.commit()
    except Exception:
        ok = False
    n = conn.execute("SELECT COUNT(*) FROM users WHERE role='supervisor'").fetchone()[0]
    conn.close()
    check("after migration a supervisor can be inserted", ok and n == 1, n)


def test_submit_autosaves():
    # #3: submitting for approval auto-saves the current edits first (one action).
    # Proven at the service level (the dialog handler chains exactly this:
    # validate -> update_report -> snapshot -> request_approval).
    dbm, auth, numbers, reports, approvals = _services()
    auth.authenticate('admin', 'Admin@1234')
    auth.create_user('ag9', 'Pass@123', 'Ag9', 'agent')
    auth.create_user('sup9', 'Pass@123', 'Sup9', 'supervisor')
    ok, rid, apid, _ = _make_and_submit(dbm, auth, numbers, reports, 'ag9', approvals)
    check("setup: agent report is pending", ok and apid)
    auth.authenticate('sup9', 'Pass@123')
    okr, msgr = approvals.reject_report(apid, 'fix the entity name', request_rework=True)
    check("supervisor returns it for rework", okr, msgr)
    # agent corrects + re-submits (save-then-submit)
    auth.authenticate('ag9', 'Pass@123')
    oke, msge = reports.update_report(rid, {'reported_entity_name': 'CORRECTED ENTITY'})
    check("agent's correction saves", oke, msge)
    oks, apid2, msgs = approvals.request_approval(rid, 'resubmitted')
    check("agent re-submits", oks, msgs)
    rep = reports.get_report(rid)
    check("the correction is persisted with the submission",
          rep and rep['reported_entity_name'] == 'CORRECTED ENTITY',
          rep.get('reported_entity_name') if rep else None)
    auth.authenticate('sup9', 'Pass@123')
    pend = [p['approval_id'] for p in approvals.get_pending_approvals()]
    check("resubmitted report is pending for the supervisor again", apid2 in pend, pend)


def test_my_work_lanes_and_review_comment():
    # #2 + #11: My Work groups a user's OWN reports by status, and a returned
    # report carries the supervisor's message (get_review_comment).
    dbm, auth, numbers, reports, approvals = _services()
    auth.authenticate('admin', 'Admin@1234')
    auth.create_user('ma', 'Pass@123', 'MA', 'agent')
    auth.create_user('mb', 'Pass@123', 'MB', 'agent')
    auth.create_user('msup', 'Pass@123', 'MSup', 'supervisor')

    # ma submits two reports; msup returns ONE for rework
    ok1, rid1, apid1, _ = _make_and_submit(dbm, auth, numbers, reports, 'ma', approvals)
    ok2, rid2, apid2, _ = _make_and_submit(dbm, auth, numbers, reports, 'ma', approvals)
    check("setup: two ma reports pending", ok1 and ok2 and apid1 and apid2)
    # a different agent's report must NOT leak into ma's lanes
    okb, ridb, apidb, _ = _make_and_submit(dbm, auth, numbers, reports, 'mb', approvals)
    auth.authenticate('msup', 'Pass@123')
    okr, _ = approvals.reject_report(apid1, 'Fix the nationality field please', request_rework=True)
    check("supervisor returns rid1 for rework", okr)
    oka, _ = approvals.approve_report(apid2, 'ok')
    check("supervisor approves rid2", oka)

    # lane filtering: ma sees exactly her own report in each lane
    auth.authenticate('ma', 'Pass@123')
    rework, n_rework = reports.get_reports(status='rework', created_by='ma', limit=None)
    approved, n_appr = reports.get_reports(status='approved', created_by='ma', limit=None)
    check("ma rework lane has exactly rid1", n_rework == 1 and rework[0]['report_id'] == rid1, (n_rework, rework))
    check("ma approved lane has exactly rid2", n_appr == 1 and approved[0]['report_id'] == rid2, (n_appr, approved))
    # cross-user isolation: mb's report never appears for ma
    all_ma = sum(reports.get_reports(status=s, created_by='ma', limit=None)[1]
                 for s in ('draft', 'pending_approval', 'approved', 'rejected', 'rework'))
    check("ma sees only her own reports (no leak from mb)", all_ma == 2, all_ma)

    # #11: the returned report carries the reviewer's message
    rc = approvals.get_review_comment(rid1)
    check("rework report exposes reviewer comment", rc and rc['comment'] == 'Fix the nationality field please', rc)
    check("review comment names the reviewer (msup)", rc and rc['reviewer'] == 'msup', rc)
    check("an approved report has no rework/reject comment", approvals.get_review_comment(rid2) is None)


if __name__ == "__main__":
    test_permissions_map()
    test_role_creation_and_routing()
    test_only_the_owner_can_submit_for_approval()
    test_migration_rebuilds_old_check()
    test_submit_autosaves()
    test_my_work_lanes_and_review_comment()
    print(f"\n{'ALL PASS' if _fail == 0 else str(_fail)+' FAILED'}")
    sys.exit(1 if _fail else 0)
