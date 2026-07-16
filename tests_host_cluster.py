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

if __name__ == '__main__':
    test_transport_roundtrip()
    test_applied_commands_table()
    test_command_registry()
    print(f"\nCLUSTER FAILURES: {len(FAILS)}")
    sys.exit(1 if FAILS else 0)
