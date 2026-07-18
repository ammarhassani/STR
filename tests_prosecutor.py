"""
STR PROSECUTOR — adversarial harness. Tries to BREAK the app.
Each 'charge' asserts the app SHOULD resist an attack. A charge that
"STANDS" = vulnerability confirmed (app failed to defend).
Also drives the UI layer via a faithful fake Page.
"""
import os, sys, shutil, sqlite3, threading, time, traceback
from datetime import datetime
from pathlib import Path

REPO = os.path.dirname(os.path.abspath(__file__))
SCRATCH = os.path.dirname(os.path.abspath(__file__))
BOX = os.path.join(SCRATCH, 'pbox')
DB = os.path.join(BOX, 'p.db')
LOGD = os.path.join(BOX, 'logs')
EXPD = os.path.join(BOX, 'exp')
sys.path.insert(0, REPO)

CHARGES = []   # (category, name, vulnerable_bool, detail)
def charge(cat, name, vulnerable, detail=''):
    CHARGES.append((cat, name, bool(vulnerable), str(detail)[:240]))
    tag = 'VULNERABLE' if vulnerable else 'defended'
    if vulnerable:
        print(f"  [{tag}] {cat}: {name} — {detail}")

def build():
    if os.path.exists(BOX): shutil.rmtree(BOX)
    os.makedirs(LOGD); os.makedirs(EXPD)
    from database.init_db import initialize_database
    from database.migrations import migrate_database
    from services.security_service import SecurityService
    ok, m = initialize_database(DB); assert ok, m
    ok, m = migrate_database(DB); assert ok, m
    conn = sqlite3.connect(DB)
    conn.execute("INSERT INTO users (username,password,full_name,role,is_active,created_by) "
                 "VALUES ('admin','x','Admin','admin',1,'SYSTEM') ON CONFLICT(username) DO NOTHING")
    conn.execute("UPDATE users SET password=?, role='admin', is_active=1, failed_login_attempts=0 "
                 "WHERE username='admin'", (SecurityService.hash_password('Admin@1234'),))
    # test fixtures (shipped schema no longer ships demo agent1/reporter1)
    conn.execute("INSERT OR IGNORE INTO users (username,password,full_name,role,is_active,created_by) "
                 "VALUES ('agent1','pass123','Test Agent','agent',1,'SYSTEM'),"
                 "('reporter1','pass123','Test Reporter','reporter',1,'SYSTEM')")
    conn.commit(); conn.close()

class Client:
    def __init__(self):
        from database.db_manager import DatabaseManager
        from services.logging_service import LoggingService
        from services.auth_service import AuthService
        from services.report_service import ReportService
        from services.dashboard_service import DashboardService
        from services.approval_service import ApprovalService
        from services.version_service import VersionService
        from services.dropdown_service import DropdownService
        from services.validation_service import ValidationService
        from services.settings_service import SettingsService
        from services.report_number_service import ReportNumberService
        from services.activity_service import ActivityService
        from services.restore_service import RestoreService
        self.db = DatabaseManager(DB)
        self.log = LoggingService(self.db, Path(LOGD))
        self.auth = AuthService(self.db, self.log)
        self.settings = SettingsService(self.db, self.auth)
        self.reports = ReportService(self.db, self.log, self.auth)
        self.dashboard = DashboardService(self.db, self.log)
        self.dropdowns = DropdownService(self.db, self.log, self.auth)
        self.validation = ValidationService(self.db, self.log)
        self.numbers = ReportNumberService(self.db, self.log)
        self.activity = ActivityService(self.db, self.log, self.auth)
        self.versions = VersionService(self.db, self.log, self.auth, self.reports, self.activity)
        self.approvals = ApprovalService(self.db, self.log, self.auth, self.versions, self.reports, self.activity)
        self.reports.set_activity_service(self.activity)
        self.versions.set_activity_service(self.activity)
        self.restore = RestoreService(self.db, self.log)
    def login(self, u, p):
        return self.auth.authenticate(u, p)
    def make_report(self, extra=None):
        u = self.auth.get_current_user()['username']
        ok, allocated, m = self.numbers.reserve_block(u, 1)
        if not ok: return False, None, m
        avail = self.numbers.get_available_numbers(u)
        if not avail: return False, None, "no available number"
        r = avail[0]
        d = {'sn': r['serial_number'], 'report_number': r['report_number'],
             'report_date': datetime.now().strftime('%d/%m/%Y'),
             'reported_entity_name': f'E{r["report_number"]}'}
        if extra: d.update(extra)
        ok, rid, m = self.reports.create_report(d)
        if ok:
            self.numbers.consume_next_available(u, rid)
        return ok, rid, m

def q1(sql, params=()):
    c = sqlite3.connect(DB); r = c.execute(sql, params).fetchone(); c.close()
    return r[0] if r else None

# ================================================================= AUTHORIZATION
def prosecute_authz():
    CAT = 'A. Authorization / privilege escalation'
    admin = Client(); admin.login('admin', 'Admin@1234')
    admin.auth.create_user('agent1', 'pass123', 'Agent One', 'agent')
    admin.auth.create_user('agent2', 'pass123', 'Agent Two', 'agent')
    admin.auth.create_user('reporter1', 'pass123', 'Reporter One', 'reporter')

    agent = Client(); agent.login('agent1', 'pass123')
    rep = Client(); rep.login('reporter1', 'pass123')

    # 1. agent creates an admin account
    ok, msg = agent.auth.create_user('evil_admin', 'x', 'Evil', 'admin')
    charge(CAT, 'agent can create_user (incl. admin role)', ok, msg)

    # 2. agent escalates OWN role to admin
    my_uid = agent.auth.get_current_user()['user_id']
    ok, msg = agent.auth.update_user(my_uid, role='admin')
    escalated = q1("SELECT role FROM users WHERE user_id=?", (my_uid,)) == 'admin'
    charge(CAT, 'agent can self-escalate role to admin', ok and escalated, f"role now {q1('SELECT role FROM users WHERE user_id=?', (my_uid,))}")
    # reset for later tests
    admin.auth.update_user(my_uid, role='agent')

    # 3. reporter resets the admin password (account takeover)
    admin_uid = q1("SELECT user_id FROM users WHERE username='admin'")
    ok, msg = rep.auth.reset_password(admin_uid, 'Pwned@1234')
    taken = Client().login('admin', 'Pwned@1234')[0]
    charge(CAT, 'reporter can reset ADMIN password (takeover)', ok and taken, msg)
    if taken:
        admin.auth.reset_password(admin_uid, 'Admin@1234')  # restore

    # 4. agent disables another user
    a2 = q1("SELECT user_id FROM users WHERE username='agent2'")
    ok, msg = agent.auth.delete_user(a2)
    disabled = q1("SELECT is_active FROM users WHERE user_id=?", (a2,)) == 0
    charge(CAT, 'agent can delete/disable other users', ok and disabled, msg)
    admin.auth.update_user(a2, is_active=1)

    # 5. agent edits a report they don't own
    ok, rid_admin, _ = admin.make_report({'reported_entity_name': 'ADMIN OWNED'})
    ok, msg = agent.reports.update_report(rid_admin, {'reported_entity_name': 'HIJACKED'})
    hijacked = q1("SELECT reported_entity_name FROM reports WHERE report_id=?", (rid_admin,)) == 'HIJACKED'
    charge(CAT, "agent edits a report they don't own", ok and hijacked, msg)

    # 6. a DIFFERENT agent edits agent1's pending report (cross-user tamper)
    ok, rid_ag, _ = agent.make_report()  # owned by agent1
    ag2 = Client(); ag2.login('agent2', 'pass123')
    ok, msg = ag2.reports.update_report(rid_ag, {'reported_entity_name': 'TAMPERED BY AGENT2'})
    tampered = q1("SELECT reported_entity_name FROM reports WHERE report_id=?", (rid_ag,)) == 'TAMPERED BY AGENT2'
    charge(CAT, "another agent edits someone else's report", ok and tampered, msg)

    # 7. reporter creates a report (reporter has NO add_report permission)
    ok, rid_r, msg = rep.make_report()
    charge(CAT, 'reporter can create reports (lacks add_report perm)', ok, msg)

    # 7b. agent mutates the shared dropdown catalog (admin-only config)
    ok, msg = agent.dropdowns.add_dropdown_value('report_source', 'EVIL', 'agent1')
    added = 'EVIL' in agent.dropdowns.get_active_dropdown_values('report_source')
    charge(CAT, 'agent can add dropdown values (admin-only)', ok and added, msg)
    cid = None
    for v in admin.dropdowns.get_all_dropdown_values('report_source'):
        if v['value'] == 'nationality': cid = v['config_id']
    ok, msg = agent.dropdowns.delete_dropdown_value(cid or 999999, 'agent1')
    charge(CAT, 'agent can delete dropdown values (admin-only)', ok, msg)

    # 8. self-approval: does approve_report allow requester==approver?
    #    admin makes a 2nd admin, that admin submits, then approves own.
    admin.auth.create_user('admin2', 'Admin2@1234', 'Admin Two', 'admin')
    a2c = Client(); a2c.login('admin2', 'Admin2@1234')
    # admin-created reports auto-approve; force a pending one via direct request on an agent report reassigned:
    ok, rid_x, _ = agent.make_report()
    appr = q1("SELECT approval_id FROM report_approvals WHERE report_id=? AND approval_status='pending'", (rid_x,))
    # the requester is agent1; admin2 approves — that's fine. Test: can the REQUESTER approve? Make admin2 request.
    # Simulate: manually insert a pending request by admin2, then admin2 approves own.
    c = sqlite3.connect(DB)
    c.execute("INSERT INTO report_approvals (report_id, approval_status, requested_by, requested_at) "
              "VALUES (?, 'pending', 'admin2', datetime('now'))", (rid_x,))
    c.commit()
    own_appr = c.execute("SELECT approval_id FROM report_approvals WHERE requested_by='admin2' AND report_id=?", (rid_x,)).fetchone()[0]
    c.close()
    ok, msg = a2c.approvals.approve_report(own_appr, 'approving my own')
    charge(CAT, 'admin can approve their OWN submitted report (no SoD)', ok, msg)

    # 9. reporter exports data (reporter HAS export per matrix — should be defended=not vuln). Sanity opposite:
    from utils.export import export_reports
    try:
        p = export_reports(rep.db, output_dir=EXPD)
        charge(CAT, 'reporter export allowed (expected per matrix, not a vuln)', False, 'ok')
    except Exception as e:
        charge(CAT, 'reporter export crashed', False, str(e))
    return admin, agent, rep

# ================================================================= INJECTION
def prosecute_injection(admin):
    CAT = 'B. Injection / query safety'
    # SQL injection via search term
    n_before = q1("SELECT COUNT(*) FROM reports")
    try:
        rows, total = admin.reports.get_reports(search_term="x'; DROP TABLE reports;--")
        survived = q1("SELECT COUNT(*) FROM reports") == n_before and q1("SELECT name FROM sqlite_master WHERE name='reports'")
        charge(CAT, 'SQLi in search_term drops table', not survived, 'table intact' if survived else 'TABLE GONE')
    except Exception as e:
        charge(CAT, 'SQLi in search_term raised (should be handled)', False, str(e))

    # injection via report field values
    ok, rid, msg = admin.make_report({'reported_entity_name': "Robert'); DROP TABLE users;--",
                                      'nationality': "' OR '1'='1"})
    users_ok = q1("SELECT name FROM sqlite_master WHERE name='users'") is not None
    charge(CAT, 'SQLi via report field drops users', not users_ok, 'users intact' if users_ok else 'GONE')

    # injection via username at creation
    try:
        ok, msg = admin.auth.create_user("bob'; DROP TABLE users;--", 'x', 'Bob', 'agent')
        users_ok = q1("SELECT name FROM sqlite_master WHERE name='users'") is not None
        charge(CAT, 'SQLi via username drops users', not users_ok)
    except Exception as e:
        charge(CAT, 'username injection raised', False, str(e))

    # injection via dropdown value
    try:
        ok, msg = admin.dropdowns.add_dropdown_value('report_source', "x','y'); DROP TABLE reports;--", 'admin')
        ok_tbl = q1("SELECT name FROM sqlite_master WHERE name='reports'") is not None
        charge(CAT, 'SQLi via dropdown value', not ok_tbl)
    except Exception as e:
        charge(CAT, 'dropdown injection raised', False, str(e))

    # LIKE wildcard abuse in search (not injection but correctness): '%' should be literal
    ok, rid2, _ = admin.make_report({'reported_entity_name': 'LITERAL_PERCENT_50%OFF'})
    rows, total = admin.reports.get_reports(search_term='50%OFF')
    # a raw % in LIKE would over-match; ensure it still finds the literal one at least
    charge(CAT, 'search with % errors out', total < 0, total)

# ================================================================= BOUNDARY / MALFORMED
def prosecute_boundary(admin):
    CAT = 'C. Boundary / malformed input'
    # huge string in a field
    huge = 'A' * 200000
    try:
        ok, rid, msg = admin.make_report({'reported_entity_name': huge})
        charge(CAT, '200k-char field accepted without limit', ok and len(q1("SELECT reported_entity_name FROM reports WHERE report_id=?", (rid,)) or '') > 100000, f"len stored")
    except Exception as e:
        charge(CAT, '200k-char field crashed the create', True, str(e))

    # null byte in field — must not raise uncaught; store-or-reject both fine
    try:
        ok, rid, msg = admin.make_report({'reported_entity_name': 'evil\x00hidden'})
        charge(CAT, 'null byte handled without uncaught crash', False, msg)
    except Exception as e:
        charge(CAT, 'null byte raised uncaught', True, str(e))

    # negative / huge pagination
    try:
        rows, total = admin.reports.get_reports(limit=-1)
        charge(CAT, 'negative limit mishandled', rows is None, f"got {len(rows) if rows else rows}")
    except Exception as e:
        charge(CAT, 'negative limit crashed', True, str(e))
    try:
        rows, total = admin.reports.get_reports(limit=10, offset=-99999)
        charge(CAT, 'negative offset crashed', False, 'ok')
    except Exception as e:
        charge(CAT, 'negative offset crashed', True, str(e))
    try:
        rows, total = admin.reports.get_reports(limit=10**12)
        charge(CAT, 'gigantic limit crashed', False, 'ok')
    except Exception as e:
        charge(CAT, 'gigantic limit crashed', True, str(e))

    # wrong types to create_report
    try:
        ok, rid, msg = admin.reports.create_report({'sn': 'not-a-number', 'report_number': None,
                                                    'report_date': 12345, 'reported_entity_name': ['list']})
        charge(CAT, 'type-confused create not rejected cleanly', ok, msg)
    except Exception as e:
        charge(CAT, 'type-confused create raised uncaught', True, str(e))

    # duplicate sn via direct create bypassing reservation (race-free dup check?)
    ok, r1, _ = admin.make_report()
    sn = q1("SELECT sn FROM reports WHERE report_id=?", (r1,))
    ok, _, msg = admin.reports.create_report({'sn': sn, 'report_number': '9999/99/999',
                                           'report_date': 'x', 'reported_entity_name': 'dupsn'})
    charge(CAT, 'duplicate serial number accepted', ok, msg)

    # validation: unicode / RTL / emoji in a pattern field
    v = admin.validation
    r = v.validate_field_generic('reporter_initials', '🤖🤖')
    charge(CAT, 'emoji passes 2-uppercase-letter pattern', r[0], r[1])

    # password strength on empty / massive
    from services.security_service import SecurityService as S
    try:
        S.check_password_strength('')
        S.check_password_strength('x'*100000)
        charge(CAT, 'password strength crashes on extreme input', False, 'ok')
    except Exception as e:
        charge(CAT, 'password strength crashed', True, str(e))

# ================================================================= RACES
def prosecute_races(admin):
    CAT = 'D. Race conditions / concurrency'
    # A. concurrent duplicate report_number: two clients create same report_number
    admin.auth.create_user('r_race', 'pass123', 'Race', 'agent')
    barrier = threading.Barrier(8)
    results = []; lock = threading.Lock()
    target_rn = '2030/01/500'
    target_sn_base = 500000
    def racer(i):
        c = Client(); c.login('admin', 'Admin@1234')
        barrier.wait()
        ok, rid, msg = c.reports.create_report({'sn': target_sn_base, 'report_number': target_rn,
                                                'report_date': 'x', 'reported_entity_name': f'race{i}'})
        with lock: results.append(ok)
    ts = [threading.Thread(target=racer, args=(i,)) for i in range(8)]
    [t.start() for t in ts]; [t.join() for t in ts]
    dup = q1("SELECT COUNT(*) FROM reports WHERE report_number=?", (target_rn,))
    charge(CAT, 'concurrent same report_number -> duplicates', dup and dup > 1, f"{dup} rows, {sum(results)} claimed success")

    # B. concurrent reservation of next number: all 8 should get DISTINCT numbers
    users = [f'ru{i}' for i in range(8)]
    for u in users: admin.auth.create_user(u, 'pass123', u, 'agent')
    b2 = threading.Barrier(8); got = []; l2 = threading.Lock()
    def reserver(u):
        c = Client(); c.login(u, 'pass123')
        b2.wait()
        ok, allocated, m = c.numbers.reserve_block(u, 1)
        if ok:
            with l2: got.append(allocated[0])
    ts = [threading.Thread(target=reserver, args=(u,)) for u in users]
    [t.start() for t in ts]; [t.join() for t in ts]
    charge(CAT, 'concurrent reservations collide (dup numbers handed out)',
           len(got) != len(set(got)), f"{len(got)} reserved, {len(set(got))} unique")

    # C. double-approve the same request concurrently
    # make an agent report -> pending
    ag = Client(); ag.login('r_race', 'pass123')
    ok, rid2, _ = ag.make_report()
    appr = q1("SELECT approval_id FROM report_approvals WHERE report_id=? AND approval_status='pending'", (rid2,))
    b3 = threading.Barrier(5); wins = []; l3 = threading.Lock()
    def approver(i):
        c = Client(); c.login('admin', 'Admin@1234')
        b3.wait()
        ok, msg = c.approvals.approve_report(appr, f'approve {i}')
        if ok:
            with l3: wins.append(i)
    ts = [threading.Thread(target=approver, args=(i,)) for i in range(5)]
    [t.start() for t in ts]; [t.join() for t in ts]
    charge(CAT, 'same approval processed more than once', len(wins) > 1, f"{len(wins)} successful approvals of one request")

    # D. delete + restore race on same report
    ok, rid3, _ = admin.make_report()
    b4 = threading.Barrier(2); errs = []
    def deleter():
        c = Client(); c.login('admin', 'Admin@1234'); b4.wait()
        try: c.reports.delete_report(rid3)
        except Exception as e: errs.append(str(e))
    def restorer():
        c = Client(); c.login('admin', 'Admin@1234'); b4.wait()
        try: c.reports.restore_report(rid3)
        except Exception as e: errs.append(str(e))
    t1 = threading.Thread(target=deleter); t2 = threading.Thread(target=restorer)
    t1.start(); t2.start(); t1.join(); t2.join()
    charge(CAT, 'delete/restore race raised uncaught error', bool(errs), errs[:1])

# ================================================================= BUSINESS LOGIC
def prosecute_logic(admin):
    CAT = 'E. Business-logic bypass'
    # delete a PENDING report (BRD: bulk delete skips pending; single delete?)
    ag = Client(); ag.login('agent1', 'pass123')
    ok, rid, _ = ag.make_report()  # pending
    ok, msg = admin.reports.delete_report(rid)
    charge(CAT, 'pending report can be soft-deleted', ok, msg)

    # reject an already-approved report
    ok, rid2, _ = ag.make_report()
    appr = q1("SELECT approval_id FROM report_approvals WHERE report_id=? AND approval_status='pending'", (rid2,))
    admin.approvals.approve_report(appr, 'ok')
    ok, msg = admin.approvals.reject_report(appr, 'change my mind')
    charge(CAT, 'already-approved request can be rejected', ok, msg)

    # restore a report that was never deleted
    ok, rid3, _ = admin.make_report()
    ok, msg = admin.reports.restore_report(rid3)
    charge(CAT, 'restore of non-deleted report succeeds silently', ok, msg)

    # reserve_block with a negative count -> should be rejected, not silently clamped
    admin.auth.create_user('negres', 'pass123', 'x', 'agent')
    nc = Client(); nc.login('negres', 'pass123')
    ok, allocated, msg = nc.numbers.reserve_block('negres', -100)
    charge(CAT, 'reserve_block with negative count accepted', ok, msg)

    # settings: inject a giant value / weird key
    try:
        admin.settings.save_setting('rows_per_page', -5)
        v = admin.settings.get_rows_per_page()
        charge(CAT, 'negative rows_per_page stored & returned', v is not None and int(v) < 0, f"got {v}")
    except Exception as e:
        charge(CAT, 'rows_per_page setting crashed', True, str(e))

    # bulk import a huge dropdown list
    try:
        admin.dropdowns.bulk_import_dropdown_values('report_source', [f'v{i}' for i in range(5000)], 'admin')
        charge(CAT, 'bulk import 5000 values crashed', False, 'ok')
    except Exception as e:
        charge(CAT, 'bulk import 5000 values crashed', True, str(e))

def report():
    print('\n' + '='*74)
    print('PROSECUTION VERDICT — vulnerabilities that STAND')
    print('='*74)
    cats = {}
    for cat, name, vuln, detail in CHARGES:
        cats.setdefault(cat, []).append((name, vuln, detail))
    total_vuln = 0
    for cat in sorted(cats):
        rows = cats[cat]
        v = [r for r in rows if r[1]]
        total_vuln += len(v)
        print(f"\n{cat}: {len(v)}/{len(rows)} charges STAND")
        for name, vuln, detail in rows:
            if vuln:
                print(f"   ✗ VULNERABLE: {name} — {detail}")
    print('\n' + '-'*74)
    print(f"TOTAL VULNERABILITIES CONFIRMED: {total_vuln} / {len(CHARGES)} charges")
    return total_vuln

if __name__ == '__main__':
    print('building sandbox...'); build()
    print('A. authorization...'); admin, agent, rep = prosecute_authz()
    print('B. injection...'); prosecute_injection(admin)
    print('C. boundary...'); prosecute_boundary(admin)
    print('D. races...'); prosecute_races(admin)
    print('E. logic...'); prosecute_logic(admin)
    n = report()
    sys.exit(0)
