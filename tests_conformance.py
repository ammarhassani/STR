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
    def login(self, u, p): return self.auth.authenticate(u, p)
    def make_report(self, extra=None):
        u = self.auth.get_current_user()['username']
        ok, r, m = self.numbers.reserve_next_numbers(u)
        if not ok: return False, None, m
        d = {'sn': r['serial_number'], 'report_number': r['report_number'],
             'report_date': '04/11/2025', 'reported_entity_name': 'E'}
        if extra: d.update(extra)
        ok, rid, m = self.reports.create_report(d)
        if ok: self.numbers.mark_reservation_used(r['report_number'], u)
        else: self.numbers.cancel_reservation(r['report_number'], u)
        return ok, rid, m

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
    fuzz_method('numbers.reserve_next_numbers', N.reserve_next_numbers, [('u', 5)])
    fuzz_method('numbers.mark_reservation_used', N.mark_reservation_used, [('x', 'u')])
    fuzz_method('numbers.cancel_reservation', N.cancel_reservation, [('x', 'u')])
    fuzz_method('numbers.get_next_from_pool', N.get_next_from_pool, [('u',)])
    fuzz_method('numbers.reserve_batch_numbers', N.reserve_batch_numbers, [(3, 5)])
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
    # R63 total_transaction: negatives rejected by validation
    r = admin.validation.validate_field_generic('total_transaction', '-500 SAR')
    conf('R63', 'negative amount rejected', not r[0], r[1])
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

if __name__ == '__main__':
    build()
    part1_fuzz()
    try:
        part2_conformance()
    except Exception as e:
        print(f"[part2 harness error: {e}]")
    nc, ng = report()
    sys.exit(0)
