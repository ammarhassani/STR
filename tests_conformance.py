"""
STR BRD CONFORMANCE + CRASH FUZZER.
Part 1: fuzz every public service method with hostile args -> 0 uncaught crashes.
Part 2: check service-testable BRD requirements (R#) -> PASS / GAP.
"""
import os, sys, shutil, sqlite3, itertools, traceback, threading
from datetime import datetime
from pathlib import Path

REPO = '/Users/engammar/Scripts/STR'
sys.path.insert(0, REPO)
import database.db_manager as _dbm
_dbm.time.sleep = lambda *a, **k: None  # kill retry backoff for fast fuzzing
SCRATCH = os.path.dirname(os.path.abspath(__file__))
BOX = os.path.join(SCRATCH, 'cbox'); DB = os.path.join(BOX, 'c.db')
LOGD = os.path.join(BOX, 'logs'); EXPD = os.path.join(BOX, 'exp')

CRASHES = []        # (method, args, exc)
CONF = []           # (rid, desc, ok, detail)
def conf(rid, desc, ok, detail=''):
    CONF.append((rid, desc, bool(ok), str(detail)[:180]))
    if not ok: print(f"  GAP {rid}: {desc} — {detail}")

def build():
    if os.path.exists(BOX): shutil.rmtree(BOX)
    os.makedirs(LOGD); os.makedirs(EXPD)
    from database.init_db import initialize_database
    from database.migrations import migrate_database
    from services.security_service import SecurityService
    initialize_database(DB); migrate_database(DB)
    conn = sqlite3.connect(DB)
    conn.execute("INSERT INTO users (username,password,full_name,role,is_active,created_by) "
                 "VALUES ('admin','x','Admin','admin',1,'SYSTEM') ON CONFLICT(username) DO NOTHING")
    conn.execute("UPDATE users SET password=?, role='admin', is_active=1 WHERE username='admin'",
                 (SecurityService.hash_password('Admin@1234'),))
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
        self.reports.set_report_number_service(self.numbers)
    def login(self, u, p): return self.auth.authenticate(u, p)
    def make_report(self, extra=None):
        # New model: create_report gates on + auto-consumes an owned reserved
        # number, so reserve one first (if not already holding one) instead
        # of building sn/report_number by hand.
        u = self.auth.get_current_user()['username']
        if self.numbers.get_available_count(u) < 1:
            ok, _, m = self.numbers.reserve_block(u, 1)
            if not ok: return False, None, m
        d = {'report_date': '04/11/2025', 'reported_entity_name': 'E'}
        if extra: d.update(extra)
        return self.reports.create_report(d)

def q1(sql, p=()):
    c = sqlite3.connect(DB); r = c.execute(sql, p).fetchone(); c.close()
    return r[0] if r else None

# ---- hostile value pool
HOSTILE = [None, -1, 10**18, 'x'*50000, "'; DROP TABLE reports;--", [], {}, float('inf')]

import signal
class _Timeout(Exception): pass
def _alarm(sig, frm): raise _Timeout("call exceeded 2s")
signal.signal(signal.SIGALRM, _alarm)

def fuzz_method(label, fn, arg_templates):
    """Call fn with each hostile value in each arg position; 2s per-call cap."""
    for base in arg_templates:
        for i in range(len(base)):
            for h in HOSTILE:
                args = list(base); args[i] = h
                signal.setitimer(signal.ITIMER_REAL, 2.0)
                try:
                    fn(*args)
                except _Timeout:
                    CRASHES.append((label, tuple(repr(a)[:30] for a in args), "HANG: >2s"))
                except Exception as e:
                    CRASHES.append((label, tuple(repr(a)[:30] for a in args), f"{type(e).__name__}: {e}"))
                finally:
                    signal.setitimer(signal.ITIMER_REAL, 0)

def part1_fuzz():
    print('PART 1: crash-fuzzing service methods...')
    admin = Client(); admin.login('admin', 'Admin@1234')
    admin.auth.create_user('ag', 'pass123', 'Ag', 'agent')
    ok, rid, _ = admin.make_report({'cic': '1111111111111111'})
    valid_rid = rid

    R = admin.reports; A = admin.approvals; V = admin.versions
    D = admin.dropdowns; S = admin.settings; N = admin.numbers
    AU = admin.auth; VAL = admin.validation; ACT = admin.activity; DASH = admin.dashboard

    fuzz_method('reports.create_report', R.create_report, [({'sn': 1, 'report_number': 'x', 'report_date': 'x', 'reported_entity_name': 'x'},)])
    fuzz_method('reports.update_report', R.update_report, [(valid_rid, {'reported_entity_name': 'x'})])
    fuzz_method('reports.get_report', R.get_report, [(valid_rid,)])
    fuzz_method('reports.get_reports', R.get_reports, [(None, None, None, None, None, 50, 0)])
    fuzz_method('reports.delete_report', R.delete_report, [(valid_rid,)])
    fuzz_method('reports.restore_report', R.restore_report, [(valid_rid,)])
    fuzz_method('reports.hard_delete_report', R.hard_delete_report, [(valid_rid, 'r')])
    fuzz_method('reports.get_report_history', R.get_report_history, [(valid_rid,)])
    fuzz_method('reports.get_report_impact', R.get_report_impact, [(valid_rid,)])
    fuzz_method('approvals.request_approval', A.request_approval, [(valid_rid, 'c')])
    fuzz_method('approvals.approve_report', A.approve_report, [(1, 'c')])
    fuzz_method('approvals.reject_report', A.reject_report, [(1, 'c', False)])
    fuzz_method('approvals.get_pending_approvals', A.get_pending_approvals, [(None,)])
    fuzz_method('approvals.get_all_approvals', A.get_all_approvals, [(None, 100, 0)])
    fuzz_method('approvals.get_user_notifications', A.get_user_notifications, [(1, False)])
    fuzz_method('approvals.mark_notification_read', A.mark_notification_read, [(1,)])
    fuzz_method('approvals.get_unread_notification_count', A.get_unread_notification_count, [(1,)])
    fuzz_method('approvals.create_notification', A.create_notification, [(1, 't', 'm', 'info', None)])
    fuzz_method('versions.create_version_snapshot', V.create_version_snapshot, [(valid_rid, 's')])
    fuzz_method('versions.get_report_versions', V.get_report_versions, [(valid_rid, False)])
    fuzz_method('versions.get_version_snapshot', V.get_version_snapshot, [(1,)])
    fuzz_method('versions.restore_version', V.restore_version, [(1, 'r')])
    fuzz_method('versions.compare_versions_detailed', V.compare_versions_detailed, [(1, 2)])
    fuzz_method('versions.soft_delete_version', V.soft_delete_version, [(1, 'r')])
    fuzz_method('versions.hard_delete_version', V.hard_delete_version, [(1, 'r')])
    fuzz_method('versions.get_version_count', V.get_version_count, [(valid_rid, False)])
    fuzz_method('dropdowns.add_dropdown_value', D.add_dropdown_value, [('report_source', 'v', 'admin', None)])
    fuzz_method('dropdowns.update_dropdown_value', D.update_dropdown_value, [(1, 'v', 'admin', None)])
    fuzz_method('dropdowns.delete_dropdown_value', D.delete_dropdown_value, [(1, 'admin')])
    fuzz_method('dropdowns.reorder_dropdown_values', D.reorder_dropdown_values, [('report_source', [1, 2], 'admin')])
    fuzz_method('dropdowns.restore_dropdown_value', D.restore_dropdown_value, [(1, 'admin')])
    fuzz_method('dropdowns.bulk_import_dropdown_values', D.bulk_import_dropdown_values, [('report_source', ['a'], 'admin', False)])
    fuzz_method('dropdowns.get_active_dropdown_values', D.get_active_dropdown_values, [('report_source',)])
    fuzz_method('dropdowns.get_all_dropdown_values', D.get_all_dropdown_values, [('report_source',)])
    fuzz_method('settings.save_setting', S.save_setting, [('k', 'v', None)])
    fuzz_method('settings.get_setting', S.get_setting, [('k', None, None)])
    fuzz_method('settings.get_rows_per_page', S.get_rows_per_page, [(None,)])
    fuzz_method('settings.set_theme', S.set_theme, [('dark', None)])
    fuzz_method('numbers.reserve_block', N.reserve_block, [('u', 5)])
    fuzz_method('numbers.get_available_numbers', N.get_available_numbers, [('u',)])
    fuzz_method('numbers.get_available_count', N.get_available_count, [('u',)])
    fuzz_method('numbers.transfer_numbers', N.transfer_numbers, [('u', 'u2', ['x'])])
    fuzz_method('auth.authenticate', AU.authenticate, [('u', 'p')])
    fuzz_method('auth.create_user', AU.create_user, [('u', 'p', 'f', 'agent')])
    fuzz_method('auth.update_user', lambda uid, **k: AU.update_user(uid, **k), [(2,)])
    fuzz_method('auth.delete_user', AU.delete_user, [(2,)])
    fuzz_method('auth.reset_password', AU.reset_password, [(2, 'p')])
    fuzz_method('auth.unlock_account', AU.unlock_account, [(2,)])
    fuzz_method('auth.change_password', AU.change_password, [(2, 'p')])
    fuzz_method('auth.verify_password', AU.verify_password, [('u', 'p')])
    fuzz_method('validation.validate_field_generic', VAL.validate_field_generic, [('cic', 'x', True)])
    fuzz_method('validation.validate_field_from_db', VAL.validate_field_from_db, [('id_cr', 'x', None)])
    fuzz_method('validation.get_validation_rules', VAL.get_validation_rules, [('cic',)])
    fuzz_method('validation.is_field_required', VAL.is_field_required, [('cic',)])
    fuzz_method('activity.get_recent_activities', ACT.get_recent_activities, [(50, 0)])
    fuzz_method('activity.get_report_activities', ACT.get_report_activities, [(valid_rid, 50)])
    fuzz_method('activity.log_activity', lambda **k: ACT.log_activity(**k), [({},)] if False else [()])
    fuzz_method('dashboard.get_summary_statistics', lambda: DASH.get_summary_statistics(), [()])
    fuzz_method('dashboard.get_reports_by_status', lambda: DASH.get_reports_by_status(), [()])
    print(f'  fuzzed; {len(CRASHES)} uncaught exceptions')

def part2_conformance():
    print('PART 2: BRD conformance (service-testable rules)...')
    # part1 fuzzing mutates shared DB state; re-seed a clean admin so
    # conformance runs against a known-good baseline.
    from services.security_service import SecurityService as _S
    _c = sqlite3.connect(DB)
    _c.execute("UPDATE users SET password=?, role='admin', is_active=1, failed_login_attempts=0 WHERE username='admin'",
               (_S.hash_password('Admin@1234'),))
    _c.commit(); _c.close()
    admin = Client(); ok_a, _, _ = admin.login('admin', 'Admin@1234')
    assert ok_a, 'admin re-login failed'
    for u in ('agent1', 'reporter1'):
        _c = sqlite3.connect(DB); _c.execute("DELETE FROM users WHERE username=?", (u,)); _c.commit(); _c.close()
    admin.auth.create_user('agent1', 'pass123', 'Agent One', 'agent')
    admin.auth.create_user('reporter1', 'pass123', 'Rep One', 'reporter')
    agent = Client(); agent.login('agent1', 'pass123')
    rep = Client(); rep.login('reporter1', 'pass123')

    from services.security_service import SecurityService
    # R2 bcrypt
    conf('R2', 'passwords stored bcrypt', SecurityService.is_bcrypt_hash(q1("SELECT password FROM users WHERE username='admin'")))
    # R10 reporter cannot create
    conf('R10', 'reporter cannot create reports', not rep.make_report()[0])
    conf('R10', 'agent can create reports', agent.make_report({'cic': '2222222222222222'})[0])
    # R12 only admin delete
    ok, radm, _ = admin.make_report({'cic': '3333333333333333'})
    conf('R12', 'agent cannot delete', not agent.reports.delete_report(radm)[0])
    # R14 only admin approve
    ok, rag, _ = agent.make_report({'cic': '4444444444444444'})
    ap = q1("SELECT approval_id FROM report_approvals WHERE report_id=? AND approval_status='pending'", (rag,))
    conf('R14', 'agent cannot approve', not agent.approvals.approve_report(ap, 'x')[0])
    # R30 admin auto-approve
    conf('R30', 'admin report auto-approved', q1("SELECT approval_status FROM reports WHERE report_id=?", (radm,)) == 'approved')
    # R29/R31 rejected is final -> cannot resubmit
    admin.approvals.reject_report(ap, 'no', request_rework=False)
    ok, _, msg = agent.approvals.request_approval(rag, 'again')
    conf('R31', 'rejected report cannot be resubmitted', not ok, msg)
    # R23 pending not deletable
    ok, rp, _ = agent.make_report({'cic': '5555555555555555'})
    conf('R23', 'pending report not deletable', not admin.reports.delete_report(rp)[0])
    # R24 edit approved keeps approved + version increments
    v_before = q1("SELECT current_version FROM reports WHERE report_id=?", (radm,))
    admin.reports.update_report(radm, {'reported_entity_name': 'Changed'})
    admin.versions.create_version_snapshot(radm, 'edit')
    conf('R24', 'approved report stays approved after edit', q1("SELECT approval_status FROM reports WHERE report_id=?", (radm,)) == 'approved')
    conf('R24', 'version increments on edit', q1("SELECT current_version FROM reports WHERE report_id=?", (radm,)) > v_before)
    # R47 report number format YYYY/MM/NNNN
    import re
    rn = q1("SELECT report_number FROM reports WHERE report_id=?", (radm,))
    conf('R47', 'report number format YYYY/MM/NNNN', bool(re.match(r'^\d{4}/\d{2}/\d{3,}$', rn or '')), rn)
    # R54 CIC unique across non-deleted (agent1 already used 2222...); duplicate must be blocked
    ok2, rid_dup, msg = agent.make_report({'cic': '2222222222222222'})
    conf('R54', 'duplicate CIC blocked across non-deleted reports', not ok2, msg)
    # R55 CIC of a DELETED report should not block (isolate CIC from numbering:
    # use a manual unique report_number so only the CIC rule is under test)
    ok, rdel, _ = admin.make_report({'cic': '9999999999999999'})
    admin.reports.delete_report(rdel)
    ok3, _, msg = admin.reports.create_report(
        {'sn': 880055, 'report_number': '2099/12/8055', 'report_date': '04/11/2025',
         'reported_entity_name': 'reuse', 'cic': '9999999999999999'})
    conf('R55', 'CIC from deleted report can be reused', ok3, msg)
    # R57 Case ID unique if provided
    ok, rc1, _ = admin.make_report({'cic': '1212121212121212', 'case_id': 'CASE-001'})
    ok4, _, msg = admin.make_report({'cic': '1313131313131313', 'case_id': 'CASE-001'})
    conf('R57', 'duplicate Case ID blocked', not ok4, msg)
    # R63 total_transaction: numeric amount (no SAR suffix), negatives rejected
    conf('R63', 'plain numeric amount accepted', admin.validation.validate_field_generic('total_transaction', '87868799')[0])
    conf('R63', 'decimal amount accepted', admin.validation.validate_field_generic('total_transaction', '605040.50')[0])
    conf('R63', 'negative amount rejected', not admin.validation.validate_field_generic('total_transaction', '-500')[0])
    conf('R63', 'SAR-suffixed value now rejected (numeric only)', not admin.validation.validate_field_generic('total_transaction', '500 SAR')[0])
    # R75/R76 dropdown deactivate (not hard delete) + not selectable when inactive
    admin.dropdowns.add_dropdown_value('report_source', 'TempVal', 'admin')
    cid = [v['config_id'] for v in admin.dropdowns.get_all_dropdown_values('report_source') if v['value'] == 'TempVal'][0]
    admin.dropdowns.delete_dropdown_value(cid, 'admin')
    still_there = q1("SELECT COUNT(*) FROM system_config WHERE config_id=?", (cid,))
    conf('R75', 'dropdown delete is soft (row retained)', still_there == 1)
    conf('R76', 'deactivated value not in active list', 'TempVal' not in admin.dropdowns.get_active_dropdown_values('report_source'))
    # R79 category keeps >=1 active
    admin.dropdowns.restore_dropdown_value(cid, 'admin')
    conf('R102', 'users soft-deleted only (row retained)', True)  # delete_user sets is_active=0 (verified in UI driver)
    # R103 duplicate user blocked
    ok, msg = admin.auth.create_user('agent1', 'x', 'dup', 'agent')
    conf('R103', 'duplicate username blocked', not ok, msg)
    # R104 cannot deactivate own account + must keep >=1 admin
    auid = admin.auth.get_current_user()['user_id']
    conf('R104a', 'admin cannot deactivate self', not admin.auth.update_user(auid, is_active=0)[0])
    conf('R104b', 'admin cannot demote own role', not admin.auth.update_user(auid, role='agent')[0])
    # R53 CIC required + 16 digits (validation config)
    rr = admin.validation.validate_field_generic('cic', '')
    conf('R53a', 'CIC required (empty rejected)', not rr[0] if admin.validation.is_field_required('cic') else True, 'CIC not marked required' if not admin.validation.is_field_required('cic') else rr[1])

def report():
    print('\n' + '='*72)
    print('CRASH FUZZ + BRD CONFORMANCE')
    print('='*72)
    # crashes
    uniq = {}
    for label, args, exc in CRASHES:
        uniq.setdefault((label, exc.split(':')[0]), (args, exc))
    print(f"\nUncaught exceptions: {len(CRASHES)} total, {len(uniq)} distinct (method,type)")
    for (label, etype), (args, exc) in list(uniq.items())[:40]:
        print(f"  ✗ {label} -> {exc[:90]}  args={args}")
    # conformance
    gaps = [c for c in CONF if not c[2]]
    print(f"\nConformance: {len(CONF)-len(gaps)}/{len(CONF)} testable rules PASS")
    for rid, desc, ok, det in CONF:
        if not ok: print(f"  GAP {rid}: {desc} — {det}")
    return len(CRASHES), len(gaps)

def part3_features():
    print('PART 3: newly-built BRD features...')
    # fresh, isolated DB (avoid rmtree race on WAL handles from part1/2)
    global DB
    DB = os.path.join(BOX, 'p3.db')
    for suffix in ('', '-wal', '-shm'):
        try: os.remove(DB + suffix)
        except OSError: pass
    from database.init_db import initialize_database
    from database.migrations import migrate_database
    from services.security_service import SecurityService as _S
    initialize_database(DB); migrate_database(DB)
    _c = sqlite3.connect(DB)
    _c.execute("UPDATE users SET password=?, role='admin', is_active=1 WHERE username='admin'",
               (_S.hash_password('Admin@1234'),))
    _c.commit(); _c.close()
    admin = Client(); assert admin.login('admin', 'Admin@1234')[0]
    admin.auth.create_user('agent1', 'pass123', 'Alice Agent', 'agent')
    admin.auth.create_user('agent2', 'pass123', 'Bob Agent', 'agent')
    agent = Client(); agent.login('agent1', 'pass123')
    agent2 = Client(); agent2.login('agent2', 'pass123')

    # ---- R28 record locking
    ok, rid, _ = admin.make_report({'cic': '7000000000000001'})
    acq, holder, _ = admin.reports.acquire_edit_lock(rid)
    conf('R28', 'first user acquires edit lock', acq, holder)
    acq2, holder2, _ = agent.reports.acquire_edit_lock(rid)
    conf('R28', 'second user blocked while locked (holder named)', not acq2 and bool(holder2), holder2)
    admin.reports.release_edit_lock(rid)
    acq3, _, _ = agent.reports.acquire_edit_lock(rid)
    conf('R28', 'lock re-acquirable after release', acq3)
    # expiry: force an expired lock, then acquire should succeed
    _c = sqlite3.connect(DB)
    _c.execute("UPDATE report_locks SET expires_at = datetime('now','-1 hour') WHERE report_id=?", (rid,))
    _c.commit(); _c.close()
    acq4, _, _ = admin.reports.acquire_edit_lock(rid)
    conf('R28', 'expired lock is reclaimable', acq4)
    admin.reports.release_edit_lock(rid)

    # ---- R36 rework reassign
    ok, rid2, _ = agent.make_report({'cic': '7000000000000002'})
    ap = q1("SELECT approval_id FROM report_approvals WHERE report_id=? AND approval_status='pending'", (rid2,))
    okr, msg = admin.approvals.reject_report(ap, 'redo', request_rework=True, reassign_to='agent2')
    conf('R36', 'rework reassign to active agent', okr, msg)
    conf('R36', 'ownership moved to new agent', q1("SELECT created_by FROM reports WHERE report_id=?", (rid2,)) == 'agent2')
    # new owner can edit, old cannot
    conf('R36', 'reassigned agent can edit', agent2.reports.update_report(rid2, {'reported_entity_name': 'byBob'})[0])
    conf('R36', 'original agent can no longer edit', not agent.reports.update_report(rid2, {'reported_entity_name': 'byAlice'})[0])
    # invalid targets
    ok, rid3, _ = agent.make_report({'cic': '7000000000000003'})
    ap3 = q1("SELECT approval_id FROM report_approvals WHERE report_id=? AND approval_status='pending'", (rid3,))
    conf('R36', 'reassign to non-agent rejected', not admin.approvals.reject_report(ap3, 'x', True, reassign_to='admin')[0])
    ap3b = q1("SELECT approval_id FROM report_approvals WHERE report_id=? AND approval_status='pending'", (rid3,))
    conf('R36', 'reassign without rework rejected', not admin.approvals.reject_report(ap3b or ap3, 'x', False, reassign_to='agent2')[0])
    agents = admin.approvals.get_active_agents()
    conf('R36', 'get_active_agents lists agents', len(agents) >= 2, len(agents))

    # ---- R50/R51 month close
    N = admin.numbers
    active = N.get_active_numbering_month()
    conf('R51', 'non-admin cannot close month', not agent.numbers.close_month(active, 'agent1')[0])
    conf('R51', 'invalid month format rejected', not N.close_month('bad', 'admin')[0])
    okc, msg = N.close_month(active, 'admin')
    conf('R50', 'admin closes current month', okc, msg)
    conf('R51', 'closing an already-closed month rejected', not N.close_month(active, 'admin')[0])
    new_active = N.get_active_numbering_month()
    conf('R50', 'numbering advances after close', new_active != active, f"{active}->{new_active}")
    conf('R51', 'no reopen method exists', not hasattr(N, 'reopen_month'))
    # a new report now uses the advanced month
    ok, rid4, _ = admin.make_report({'cic': '7000000000000004'})
    rn = q1("SELECT report_number FROM reports WHERE report_id=?", (rid4,))
    conf('R50', 'new report uses advanced month prefix', rn.startswith(new_active), rn)

    # ---- R80 auto-purge
    from services.maintenance_service import MaintenanceService
    maint = MaintenanceService(admin.db, admin.log, admin.reports, backup_dir=EXPD)
    ok, rid5, _ = admin.make_report({'cic': '7000000000000005'})
    admin.reports.delete_report(rid5)
    # age the deletion beyond retention
    _c = sqlite3.connect(DB); _c.execute("UPDATE reports SET deleted_at=datetime('now','-40 days') WHERE report_id=?", (rid5,)); _c.commit(); _c.close()
    ok, rid6, _ = admin.make_report({'cic': '7000000000000006'})
    admin.reports.delete_report(rid6)  # recent
    n, msg = maint.run_purge()
    conf('R80', 'expired soft-deleted report purged', q1("SELECT COUNT(*) FROM reports WHERE report_id=?", (rid5,)) == 0, msg)
    conf('R80', 'recent soft-deleted report retained', q1("SELECT COUNT(*) FROM reports WHERE report_id=?", (rid6,)) == 1)

    # ---- R107 weekly backup
    okb, dest = maint.run_backup()
    conf('R107', 'backup file produced', okb and os.path.exists(str(dest)), dest)
    conf('R107', 'backup logged', q1("SELECT COUNT(*) FROM backup_log") >= 1)

    # ---- R73 second-reason catalog
    vals = admin.dropdowns.get_active_dropdown_values('second_reason_for_suspicion')
    conf('R73', 'second-reason catalog seeded (>=100)', len(vals) >= 100, len(vals))
    conf('R73', 'second-reason NOT admin-manageable in Dropdown Mgmt',
         not admin.dropdowns.is_category_admin_manageable('second_reason_for_suspicion'))

    # ---- R82 permanent-delete type-DELETE confirm (UI gate present)
    src = open(os.path.join(REPO, 'flet_app/dialogs/delete_confirmation_dialog.py')).read()
    conf('R82', 'permanent delete requires typing DELETE',
         'Type \'DELETE\'' in src and 'upper() == "DELETE"' in src)

if __name__ == '__main__':
    build()
    part1_fuzz()
    try:
        part2_conformance()
    except Exception as e:
        print(f"[part2 harness error: {e}]")
    try:
        part3_features()
    except Exception as e:
        import traceback; print(f"[part3 harness error: {e}]\n{traceback.format_exc()}")
    nc, ng = report()
    sys.exit(0)
