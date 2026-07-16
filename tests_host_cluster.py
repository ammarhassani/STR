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

if __name__ == '__main__':
    test_transport_roundtrip()
    print(f"\nCLUSTER FAILURES: {len(FAILS)}")
    sys.exit(1 if FAILS else 0)
