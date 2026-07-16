"""Single-host / multi-client integration + idempotency harness. Run: python3.14 tests_host_cluster.py"""
import os, sys, shutil, tempfile, json, uuid
sys.path.insert(0, '/Users/engammar/Scripts/STR')

FAILS = []
def check(name, ok, detail=''):
    print(('  ok  ' if ok else '  FAIL ') + name + ('' if ok else f' — {detail}'))
    if not ok: FAILS.append(name)

def test_transport_roundtrip():
    from services.queue_transport import QueueTransport
    box = tempfile.mkdtemp()
    try:
        t = QueueTransport(os.path.join(box, 'str_bus'))
        cid = 'c-' + uuid.uuid4().hex
        t.submit({'id': cid, 'command': 'ping', 'args': [1], 'kwargs': {}})
        # host side
        claimed = t.claim_next()
        check('T1 claim returns the submitted command', claimed and claimed['id'] == cid, claimed)
        check('T1 queue empty after claim', t.claim_next() is None)
        t.respond(cid, {'id': cid, 'ok': True, 'result': 'pong'})
        t.complete(cid)
        # client side
        resp = t.await_response(cid, timeout=5)
        check('T1 await returns the response', resp['ok'] and resp['result'] == 'pong', resp)
        # response consumed
        raised = False
        try: t.await_response(cid, timeout=0.3)
        except TimeoutError: raised = True
        check('T1 response consumed after read', raised)
    finally:
        shutil.rmtree(box, ignore_errors=True)

def test_applied_commands_table():
    import sqlite3
    from database.init_db import initialize_database
    from database.migrations import migrate_database
    box = tempfile.mkdtemp()
    try:
        db = os.path.join(box, 'x.db')
        initialize_database(db); migrate_database(db)
        cols = {r[1] for r in sqlite3.connect(db).execute("PRAGMA table_info(applied_commands)")}
        check('T2 applied_commands table exists', {'command_id','response_json','applied_at'} <= cols, cols)
    finally:
        shutil.rmtree(box, ignore_errors=True)

def test_command_registry():
    from services import command_registry as cr
    check('T3 create_report is a write command', cr.is_write_command('report_service.create_report'))
    check('T3 get_reports is NOT a write command', not cr.is_write_command('report_service.get_reports'))
    class FakeReport:
        def create_report(self, data): return (True, 7, 'ok')
    result = cr.dispatch({'report_service': FakeReport()}, 'report_service.create_report', [{'x': 1}], {})
    check('T3 dispatch calls the method', result == (True, 7, 'ok'), result)
    raised = False
    try: cr.dispatch({}, 'nope.nope', [], {})
    except KeyError: raised = True
    check('T3 unknown command raises KeyError', raised)

def _build_host(box):
    """Build a host with a fresh DB + seeded admin + real services."""
    import sqlite3
    from database.init_db import initialize_database
    from database.migrations import migrate_database
    from services.security_service import SecurityService
    from database.db_manager import DatabaseManager
    from services.logging_service import LoggingService
    from services.auth_service import AuthService
    from services.report_service import ReportService
    from services.approval_service import ApprovalService
    from services.version_service import VersionService
    from services.dropdown_service import DropdownService
    from services.validation_service import ValidationService
    from services.settings_service import SettingsService
    from services.report_number_service import ReportNumberService
    from services.activity_service import ActivityService
    from services.dashboard_service import DashboardService
    from services.queue_transport import QueueTransport
    from host.host_service import HostService
    from pathlib import Path
    db = os.path.join(box, 'fiu.db'); bus = os.path.join(box, 'str_bus')
    initialize_database(db); migrate_database(db)
    c = sqlite3.connect(db)
    c.execute("INSERT INTO users (username,password,full_name,role,is_active,created_by) "
              "VALUES ('admin','x','Admin','admin',1,'SYSTEM') ON CONFLICT(username) DO NOTHING")
    c.execute("UPDATE users SET password=?, role='admin', is_active=1 WHERE username='admin'",
              (SecurityService.hash_password('Admin@1234'),)); c.commit(); c.close()
    dbm = DatabaseManager(db); log = LoggingService(dbm, Path(os.path.join(box,'logs')))
    auth = AuthService(dbm, log); settings = SettingsService(dbm, auth)
    reports = ReportService(dbm, log, auth); dash = DashboardService(dbm, log)
    dd = DropdownService(dbm, log, auth); val = ValidationService(dbm, log)
    nums = ReportNumberService(dbm, log); act = ActivityService(dbm, log, auth)
    ver = VersionService(dbm, log, auth, reports, act)
    appr = ApprovalService(dbm, log, auth, ver, reports, act)
    reports.set_activity_service(act); ver.set_activity_service(act)
    services = {'auth_service': auth, 'settings_service': settings, 'report_service': reports,
                'dashboard_service': dash, 'dropdown_service': dd, 'validation_service': val,
                'report_number_service': nums, 'activity_service': act, 'version_service': ver,
                'approval_service': appr}
    transport = QueueTransport(bus)
    host = HostService(services, dbm, transport, bus)
    return host, transport, dbm

def test_host_login_and_command():
    box = tempfile.mkdtemp()
    try:
        host, t, dbm = _build_host(box)
        ok, token, msg = host.login('admin', 'Admin@1234')
        check('T4 host login issues token', ok and token, msg)
        # a write command: create a user (admin session)
        resp = host.handle_command({'id':'c1','command':'auth_service.create_user',
                                    'args':['agentnew1','pass123','Agent One','agent'],'kwargs':{},'token':token})
        check('T4 create_user command ok', resp['ok'], resp.get('error'))
        n = dbm.execute_with_retry("SELECT COUNT(*) FROM users WHERE username='agentnew1'")[0][0]
        check('T4 user actually created host-side', n == 1)
        # idempotent replay: same id returns stored response, no double-apply
        resp2 = host.handle_command({'id':'c1','command':'auth_service.create_user',
                                     'args':['agentnew1','pass123','Agent One','agent'],'kwargs':{},'token':token})
        n2 = dbm.execute_with_retry("SELECT COUNT(*) FROM users WHERE username='agentnew1'")[0][0]
        check('T4 idempotent replay does not double-apply', n2 == 1 and resp2['ok'])
        # authz enforced host-side: agent token cannot create users
        aok, atoken, _ = host.login('agentnew1', 'pass123')
        r3 = host.handle_command({'id':'c2','command':'auth_service.create_user',
                                  'args':['x','y','z','agent'],'kwargs':{},'token':atoken})
        check('T4 host enforces authz (agent cannot create_user)', not r3['ok'], r3)
        # replica publishes
        host.publish_replica()
        check('T4 replica published', os.path.exists(os.path.join(box,'str_bus','replica','fiu_ro.db')))
    finally:
        shutil.rmtree(box, ignore_errors=True)

if __name__ == '__main__':
    test_transport_roundtrip()
    test_applied_commands_table()
    test_command_registry()
    test_host_login_and_command()
    print(f"\nCLUSTER FAILURES: {len(FAILS)}")
    sys.exit(1 if FAILS else 0)
