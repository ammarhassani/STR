"""Single-host / multi-client integration + idempotency harness. Run: python3.14 tests_host_cluster.py"""
import os, sys, shutil, tempfile, json, uuid
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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
        ok, token, msg, _u = host.login('admin', 'Admin@1234')
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
        aok, atoken, _, _u2 = host.login('agentnew1', 'pass123')
        r3 = host.handle_command({'id':'c2','command':'auth_service.create_user',
                                  'args':['x','y','z','agent'],'kwargs':{},'token':atoken})
        check('T4 host enforces authz (agent cannot create_user)',
              r3['ok'] and isinstance(r3['result'], (list, tuple)) and r3['result'][0] is False, r3)
        # replica publishes
        host.publish_replica()
        check('T4 replica published', os.path.exists(os.path.join(box,'str_bus','replica','fiu_ro.db')))
    finally:
        shutil.rmtree(box, ignore_errors=True)

def test_end_to_end_via_queue():
    import threading, time
    box = tempfile.mkdtemp()
    try:
        host, t, dbm = _build_host(box)
        stop = {'v': False}
        def loop():
            while not stop['v']:
                if not host.run_once():
                    time.sleep(0.02)
        th = threading.Thread(target=loop, daemon=True); th.start()

        from services.queue_transport import QueueTransport
        client = QueueTransport(os.path.join(box, 'str_bus'))
        # login via queue
        import uuid as _u
        lid = _u.uuid4().hex
        client.submit({'id': lid, 'command': 'login', 'args': ['admin','Admin@1234'], 'kwargs': {}})
        lresp = client.await_response(lid, timeout=10)
        check('T5 login via queue', lresp['ok'] and lresp['result']['token'], lresp)
        token = lresp['result']['token']
        # create_user via queue
        cid = _u.uuid4().hex
        client.submit({'id': cid, 'command': 'auth_service.create_user',
                       'args': ['agentq','pass123','Agent Q','agent'], 'kwargs': {}, 'token': token})
        cresp = client.await_response(cid, timeout=10)
        check('T5 create_user via queue', cresp['ok'], cresp)
        check('T5 user present host-side', dbm.execute_with_retry(
            "SELECT COUNT(*) FROM users WHERE username='agentq'")[0][0] == 1)
        stop['v'] = True; th.join(timeout=2)
    finally:
        shutil.rmtree(box, ignore_errors=True)

def test_client_proxy_routing():
    import threading, time, shutil as _sh
    box = tempfile.mkdtemp()
    try:
        host, t, dbm = _build_host(box)
        stop = {'v': False}
        def loop():
            while not stop['v']:
                if not host.run_once(): time.sleep(0.02)
        th = threading.Thread(target=loop, daemon=True); th.start()
        host.publish_replica()

        from services.queue_transport import QueueTransport
        from services.remote_gateway import RemoteGateway, RemoteServiceProxy
        from database.db_manager import DatabaseManager
        from services.auth_service import AuthService
        from services.report_service import ReportService
        from services.logging_service import LoggingService
        from pathlib import Path
        bus = os.path.join(box, 'str_bus')
        # client read DB = copy of replica
        client_db = os.path.join(box, 'client_ro.db')
        _sh.copy(os.path.join(bus,'replica','fiu_ro.db'), client_db)
        gw = RemoteGateway(QueueTransport(bus))
        ok, _u, msg = gw.login('admin', 'Admin@1234')
        check('T6 gateway login', ok, msg)
        rdbm = DatabaseManager(client_db)
        rlog = LoggingService(rdbm, Path(os.path.join(box,'clog')))
        rauth = AuthService(rdbm, rlog)
        local_reports = ReportService(rdbm, rlog, rauth)
        proxy = RemoteServiceProxy('auth_service', AuthService(rdbm, rlog), gw)
        # write via proxy -> goes through queue -> host applies
        ok2, m2 = proxy.create_user('agentp', 'pass123', 'Agent P', 'agent')
        check('T6 proxy write routed to host', ok2, m2)
        check('T6 host applied proxy write', dbm.execute_with_retry(
            "SELECT COUNT(*) FROM users WHERE username='agentp'")[0][0] == 1)
        # read via proxy delegates locally (no crash); read method exists
        users = RemoteServiceProxy('auth_service', AuthService(rdbm, rlog), gw).get_all_users()
        check('T6 proxy read delegates locally', isinstance(users, list))
        stop['v'] = True; th.join(timeout=2)
    finally:
        _sh.rmtree(box, ignore_errors=True)

def test_multiclient_stress_and_replay():
    import threading, time, sqlite3
    box = tempfile.mkdtemp()
    try:
        host, t, dbm = _build_host(box)
        stop = {'v': False}
        def loop():
            while not stop['v']:
                if not host.run_once(): time.sleep(0.01)
        th = threading.Thread(target=loop, daemon=True); th.start()

        from services.queue_transport import QueueTransport
        from services.remote_gateway import RemoteGateway
        bus = os.path.join(box, 'str_bus')
        # seed agents via one admin gateway
        admin_gw = RemoteGateway(QueueTransport(bus)); admin_gw.login('admin','Admin@1234')
        NUSERS = 6
        for i in range(NUSERS):
            admin_gw.call('auth_service.create_user', [f'ag{i}', 'pass123', f'Agent {i}', 'agent'], {})
        errors = []
        def worker(i):
            try:
                gw = RemoteGateway(QueueTransport(bus)); gw.login(f'ag{i}','pass123')
                # each agent reserves numbers then creates reports via commands
                # a per-user "already has an active reservation" business result is a
                # normal returned (False, msg) tuple, not a thrown error — only real
                # exceptions from the gateway/host count as worker errors here.
                gw.call('report_number_service.reserve_block', [f'ag{i}', 5], {})
            except Exception as e:
                errors.append(f'ag{i}: {e}')
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(NUSERS)]
        [x.start() for x in threads]; [x.join() for x in threads]
        check('T7 no worker errors', not errors, errors[:2])

        # integrity + no dup applied commands
        integ = sqlite3.connect(dbm.db_path).execute("PRAGMA integrity_check").fetchone()[0]
        check('T7 integrity ok', integ == 'ok', integ)
        dup = dbm.execute_with_retry(
            "SELECT command_id, COUNT(*) c FROM applied_commands GROUP BY command_id HAVING c>1")
        check('T7 no command applied twice', not dup, dup[:3])

        # crash-replay: re-handle an already-applied command id -> no change, same response
        applied = dbm.execute_with_retry("SELECT command_id FROM applied_commands LIMIT 1")
        check('T7 ledger recorded commands (replay check is non-vacuous)', len(applied) >= 1, len(applied))
        if applied:
            cid = applied[0][0]
            before = dbm.execute_with_retry("SELECT COUNT(*) FROM users")[0][0]
            host.handle_command({'id': cid, 'command': 'auth_service.create_user',
                                 'args': ['dupe','p','d','agent'], 'kwargs': {}, 'token': None})
            after = dbm.execute_with_retry("SELECT COUNT(*) FROM users")[0][0]
            check('T7 replay of applied id is a no-op', before == after)
        stop['v'] = True; th.join(timeout=2)
    finally:
        shutil.rmtree(box, ignore_errors=True)

def test_serve_forever_survives_poison_command():
    """A single bad command must not kill the host loop (serve_forever try/except),
    and a non-JSON-native response value must not blow up respond() (default=str)."""
    import threading, time, datetime
    from services.queue_transport import QueueTransport

    # FIX 1: respond() must serialize non-JSON-native values (e.g. datetime) via default=str.
    box1 = tempfile.mkdtemp()
    try:
        t = QueueTransport(os.path.join(box1, 'str_bus'))
        raised = False
        try:
            t.respond('poison-1', {'id': 'poison-1', 'ok': True, 'result': datetime.datetime.now()})
        except TypeError:
            raised = True
        check('T8 respond() serializes non-JSON values (default=str)', not raised)
    finally:
        shutil.rmtree(box1, ignore_errors=True)

    # FIX 2: serve_forever must survive an exception raised inside run_once.
    box2 = tempfile.mkdtemp()
    try:
        host, t, dbm = _build_host(box2)
        calls = {'n': 0}
        real_run_once = host.run_once
        def poison_run_once():
            calls['n'] += 1
            if calls['n'] == 1:
                raise RuntimeError('poison command exploded')
            return real_run_once()
        host.run_once = poison_run_once
        th = threading.Thread(target=host.serve_forever, kwargs={'poll': 0.01}, daemon=True)
        th.start()
        time.sleep(0.5)
        check('T8 serve_forever loop survives a poisoned run_once', th.is_alive())
        check('T8 loop kept iterating after the exception', calls['n'] > 1, calls['n'])
    finally:
        shutil.rmtree(box2, ignore_errors=True)

def test_reserved_numbers_table():
    import sqlite3
    from database.init_db import initialize_database
    from database.migrations import migrate_database
    box = tempfile.mkdtemp()
    try:
        db = os.path.join(box, 'r.db')
        initialize_database(db); migrate_database(db)
        cols = {r[1] for r in sqlite3.connect(db).execute("PRAGMA table_info(reserved_numbers)")}
        need = {'id','report_number','serial_number','owned_by','status','used_by_report_id','reserved_at','transferred_from'}
        check('P2T1 reserved_numbers table exists', need <= cols, cols)
    finally:
        shutil.rmtree(box, ignore_errors=True)

def test_block_reservation():
    box = tempfile.mkdtemp()
    try:
        host, t, dbm = _build_host(box)
        nums = host.services['report_number_service']
        ok, block, msg = nums.reserve_block('ali', 5)
        check('P2T2 reserve_block allocates 5', ok and len(block) == 5, msg)
        check('P2T2 available count = 5', nums.get_available_count('ali') == 5)
        # consume lowest
        ok, rn, _ = nums.consume_next_available('ali', 999)
        check('P2T2 consume returns a number', ok and rn == block[0], (rn, block[0]))
        check('P2T2 available now 4', nums.get_available_count('ali') == 4)
        import sqlite3
        row = sqlite3.connect(dbm.db_path).execute(
            "SELECT status, used_by_report_id FROM reserved_numbers WHERE report_number=?", (rn,)).fetchone()
        check('P2T2 consumed marked used+linked', row[0] == 'used' and row[1] == 999, row)
        # transfer 2 of ali's remaining to sara (seed sara active)
        dbm.execute_with_retry("INSERT INTO users (username,password,full_name,role,is_active,created_by) "
                               "VALUES ('sara','x','Sara','agent',1,'admin')")
        remaining = [r['report_number'] for r in nums.get_available_numbers('ali')]
        okt, mt = nums.transfer_numbers('ali', 'sara', remaining[:2])
        check('P2T2 transfer ok', okt, mt)
        check('P2T2 sara has 2', nums.get_available_count('sara') == 2)
        check('P2T2 ali has 2', nums.get_available_count('ali') == 2)
        # cannot transfer numbers you do not own
        okbad, _ = nums.transfer_numbers('ali', 'sara', ['9999/99/999'])
        check('P2T2 cannot transfer unowned', not okbad)
        check('P2T2 report_numbers are unique', dbm.execute_with_retry(
            "SELECT report_number,COUNT(*) c FROM reserved_numbers GROUP BY report_number HAVING c>1") == [])
    finally:
        shutil.rmtree(box, ignore_errors=True)

def test_create_report_gate():
    box = tempfile.mkdtemp()
    try:
        host, t, dbm = _build_host(box)
        host.services['report_service'].set_report_number_service(host.services['report_number_service'])
        host.services['auth_service'].current_user = {'user_id':1,'username':'admin','role':'admin'}
        R = host.services['report_service']; N = host.services['report_number_service']
        # no reserved numbers -> gated
        ok, rid, msg = R.create_report({'report_date':'04/11/2025','reported_entity_name':'X','cic':'1'*16})
        check('P2T3 create blocked without reserved number', not ok and 'reserve' in msg.lower(), msg)
        # reserve then create -> uses the reserved number
        N.reserve_block('admin', 2)
        block = [x['report_number'] for x in N.get_available_numbers('admin')]
        ok, rid, msg = R.create_report({'report_date':'04/11/2025','reported_entity_name':'X','cic':'2'*16})
        check('P2T3 create ok after reserve', ok, msg)
        rn = dbm.execute_with_retry("SELECT report_number FROM reports WHERE report_id=?", (rid,))[0][0]
        check('P2T3 report uses reserved number', rn == block[0], (rn, block[0]))
        check('P2T3 reserved number consumed', N.get_available_count('admin') == 1)
    finally:
        shutil.rmtree(box, ignore_errors=True)

def test_self_heal_stranded_number():
    """FIX 1: a prior partial failure can leave a reserved row 'available'
    whose report_number already exists in reports. create_report must not
    re-pick that number forever — it should retire the stranded row and
    fall through to the next available one."""
    from datetime import datetime
    box = tempfile.mkdtemp()
    try:
        host, t, dbm = _build_host(box)
        host.services['report_service'].set_report_number_service(host.services['report_number_service'])
        host.services['auth_service'].current_user = {'user_id': 1, 'username': 'admin', 'role': 'admin'}
        R = host.services['report_service']; N = host.services['report_number_service']
        ok, block, msg = N.reserve_block('admin', 2)
        check('P2T5 reserve_block allocates 2', ok and len(block) == 2, msg)
        # Simulate a stranded row: a report already exists using the block's
        # FIRST (lowest) number, but its reserved_numbers row is still
        # 'available' (as if consume_next_available never ran after insert).
        dbm.execute_with_retry(
            "INSERT INTO reports (sn, report_number, report_date, reported_entity_name, created_by, created_at) "
            "VALUES (900001, ?, '04/11/2025', 'Stranded', 'admin', ?)",
            (block[0], datetime.now().isoformat()))
        ok, rid, msg = R.create_report({'report_date': '04/11/2025', 'reported_entity_name': 'Y', 'cic': '3' * 16})
        check('P2T5 self-heal does not fail with already exists',
              ok and 'already exists' not in (msg or '').lower(), msg)
        rn = dbm.execute_with_retry("SELECT report_number FROM reports WHERE report_id=?", (rid,))[0][0]
        check('P2T5 self-heal skips stranded number and uses next', rn == block[1], (rn, block))
        stranded_status = dbm.execute_with_retry(
            "SELECT status FROM reserved_numbers WHERE report_number=?", (block[0],))[0][0]
        check('P2T5 stranded row retired to used', stranded_status == 'used', stranded_status)
    finally:
        shutil.rmtree(box, ignore_errors=True)

def test_registry_reservation_commands():
    from services import command_registry as cr
    check('P2T4 reserve_block is a write command', cr.is_write_command('report_number_service.reserve_block'))
    check('P2T4 transfer_numbers is a write command', cr.is_write_command('report_number_service.transfer_numbers'))
    check('P2T4 old reserve_next_numbers removed', not cr.is_write_command('report_number_service.reserve_next_numbers'))

def test_onboarding_through_host():
    """#1 two-way handshake across the host boundary: admin creates the ID
    (write command), the user self-registers (pre-auth complete_onboarding),
    then logs in — all via the host."""
    box = tempfile.mkdtemp()
    try:
        host, t, dbm = _build_host(box)
        ok, token, _, _ = host.login('admin', 'Admin@1234')
        check('OB admin logged in', ok and token)
        # admin creates a pending user via write command
        r = host.handle_command({'id': 'ob1', 'command': 'auth_service.create_pending_user',
                                 'args': ['newrep', 'reporter'], 'kwargs': {}, 'token': token})
        check('OB pending user created via host', r['ok'] and r['result'][0], r.get('error'))
        # a pending user cannot log in yet
        pok, *_ = host.login('newrep', 'anything')
        check('OB pending user cannot log in before registering', not pok)
        # user self-registers (pre-auth, NO token)
        r2 = host.handle_command({'id': 'ob2', 'command': 'complete_onboarding',
                                  'args': ['newrep', 'New Rep', 'StrongPass123'], 'kwargs': {}})
        check('OB complete_onboarding via host (pre-auth)', r2['ok'] and r2['result'][0], r2.get('result'))
        # now the user logs in with the password only they set
        lok, ltok, lmsg, lu = host.login('newrep', 'StrongPass123')
        check('OB onboarded user logs in via host', lok and lu['role'] == 'reporter', lmsg)
        # complete_onboarding is registered as a pre-auth special (not a write cmd)
        from services import command_registry as cr
        check('OB create_pending_user is a write command',
              cr.is_write_command('auth_service.create_pending_user'))
        check('OB reset_onboarding is a write command',
              cr.is_write_command('auth_service.reset_onboarding'))
        check('OB complete_onboarding is NOT a token-gated write command',
              not cr.is_write_command('auth_service.complete_onboarding'))
    finally:
        shutil.rmtree(box, ignore_errors=True)


# Methods that match a write verb but must NOT route to the host. Each needs a
# reason — an unexplained entry here is how a real write goes missing.
REGISTRY_EXEMPT = {
    # pre-auth special: handled by RemoteGateway.complete_onboarding, no token yet
    'auth_service.complete_onboarding',
    # dependency injection, not a DB write
    'report_service.set_activity_service',
    'report_service.set_report_number_service',
    'report_service.set_version_service',   # wiring setter, not a write op
    'approval_service.set_activity_service',
    'version_service.set_activity_service',
    # pure static factories returning rule objects
    'validation_service.create_report_validation_rules',
    'validation_service.create_user_validation_rules',
    # host-only: MaintenanceService is never started in client mode (app_state.py)
    'report_service.purge_expired_deleted_reports',
}

def test_registry_covers_every_write_method():
    """Every write-shaped public method on a proxied service must be in
    WRITE_COMMANDS or explicitly exempt. Without this, adding a write method and
    forgetting the registry entry silently routes it to the read-only replica in
    client mode — RemoteServiceProxy defaults unknown names to the local service.
    Parsed with ast so this runs without the services' third-party deps."""
    import ast, re, pathlib
    from services import command_registry as cr
    proxied = {  # the attrs app_state.py wraps in RemoteServiceProxy
        'auth_service': 'AuthService', 'report_service': 'ReportService',
        'approval_service': 'ApprovalService', 'version_service': 'VersionService',
        'report_number_service': 'ReportNumberService', 'dropdown_service': 'DropdownService',
        'validation_service': 'ValidationService', 'settings_service': 'SettingsService',
    }
    verbs = re.compile(r'^(add|acquire|approve|bulk|change|complete|create|delete|hard_delete'
                       r'|mark|purge|reject|release|remove|reorder|request|reserve|reset'
                       r'|restore|save|set|soft_delete|transfer|unlock|update)_')
    missing = []
    for attr, cls in proxied.items():
        tree = ast.parse(pathlib.Path('services', attr + '.py').read_text(encoding='utf-8'))
        node = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == cls)
        for m in node.body:
            if not isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            full = f'{attr}.{m.name}'
            if m.name.startswith('_') or not verbs.match(m.name) or full in REGISTRY_EXEMPT:
                continue
            if not cr.is_write_command(full):
                missing.append(full)
    check('T3b every write method is registered or exempt', not missing, missing)
    stale = [n for n in REGISTRY_EXEMPT if cr.is_write_command(n)]
    check('T3b no exemption shadows a registered command', not stale, stale)


if __name__ == '__main__':
    test_transport_roundtrip()
    test_applied_commands_table()
    test_command_registry()
    test_registry_covers_every_write_method()
    test_host_login_and_command()
    test_end_to_end_via_queue()
    test_client_proxy_routing()
    test_multiclient_stress_and_replay()
    test_serve_forever_survives_poison_command()
    test_reserved_numbers_table()
    test_block_reservation()
    test_create_report_gate()
    test_self_heal_stranded_number()
    test_registry_reservation_commands()
    test_onboarding_through_host()
    print(f"\nCLUSTER FAILURES: {len(FAILS)}")
    sys.exit(1 if FAILS else 0)
