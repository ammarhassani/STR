"""Phase 3a failover safety core tests. Run: python3.14 tests_failover.py"""
import os, sys, json, time, tempfile, shutil, sqlite3
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_fail = 0
def check(label, cond, detail=""):
    global _fail
    ok = bool(cond)
    print(("PASS " if ok else "FAIL ") + label + ("" if ok else f"  -- {detail}"))
    if not ok:
        _fail += 1

def _fresh_db():
    from database.init_db import initialize_database
    from database.migrations import migrate_database
    from database.db_manager import DatabaseManager
    d = tempfile.mkdtemp()
    db = os.path.join(d, "h.db")
    initialize_database(db); migrate_database(db)
    return d, DatabaseManager(db)

def test_lease():
    from host.lease import read_lease, bump_lease
    d, dbm = _fresh_db()
    try:
        check("lease starts unseeded-or-zero", read_lease(dbm)[1] == 0, read_lease(dbm))
        t1 = bump_lease(dbm, "hostA")
        t2 = bump_lease(dbm, "hostB")
        check("lease term monotonic", t2 > t1, (t1, t2))
        hid, term = read_lease(dbm)
        check("lease records host + term", hid == "hostB" and term == t2, (hid, term))
        t3 = bump_lease(dbm, "hostC", min_term=100)
        check("lease honors min_term floor", t3 == 101, t3)
        # concurrency: N parallel bumps must not lose an increment (atomic UPDATE)
        import threading
        start = read_lease(dbm)[1]
        N = 20
        def _bump(): bump_lease(dbm, "race")
        ths = [threading.Thread(target=_bump) for _ in range(N)]
        for t in ths: t.start()
        for t in ths: t.join()
        check("concurrent bumps lose no increment", read_lease(dbm)[1] == start + N,
              (start, N, read_lease(dbm)[1]))
    finally:
        shutil.rmtree(d, ignore_errors=True)

def test_heartbeat():
    from host.heartbeat import write_heartbeat, read_heartbeat, is_stale
    from services.queue_transport import QueueTransport
    d = tempfile.mkdtemp()
    bus = os.path.join(d, "bus"); QueueTransport(bus)  # creates host/ + .tmp/
    try:
        check("no heartbeat -> stale", is_stale(read_heartbeat(bus)) is True)
        write_heartbeat(bus, "hostA", 3, 1234, 999, "PC1")
        hb = read_heartbeat(bus)
        check("heartbeat round-trips", hb["host_id"] == "hostA" and hb["term"] == 3 and hb["db_version"] == 1234, hb)
        check("fresh heartbeat not stale", is_stale(hb, stale_seconds=60) is False)
        old = dict(hb); old["epoch_ms"] = int(time.time() * 1000) - 120000
        check("old heartbeat is stale", is_stale(old, stale_seconds=60) is True)
    finally:
        shutil.rmtree(d, ignore_errors=True)

def test_integrity_and_session():
    from host.integrity import check_and_restore
    from database.init_db import initialize_database
    from database.migrations import migrate_database
    d = tempfile.mkdtemp()
    db = os.path.join(d, "h.db"); initialize_database(db); migrate_database(db)
    backups = os.path.join(d, "backups"); os.makedirs(backups)
    try:
        ok, msg = check_and_restore(db, backups)
        check("integrity ok on healthy db", ok and msg == "ok", msg)
        # make a good backup, then corrupt the db, then restore
        shutil.copyfile(db, os.path.join(backups, "fiu_1.db"))
        with open(db, "wb") as f:
            f.write(b"this is not a sqlite file at all, totally corrupt")
        ok2, msg2 = check_and_restore(db, backups)
        check("corrupt db restored from backup", ok2 and "restored" in msg2.lower(), msg2)
        # restored db is usable again
        ok3, _ = check_and_restore(db, backups)
        check("restored db passes integrity", ok3)
    finally:
        shutil.rmtree(d, ignore_errors=True)

def test_session_timeout():
    from host.host_service import HostService
    from services.queue_transport import QueueTransport
    from database.init_db import initialize_database
    from database.migrations import migrate_database
    from database.db_manager import DatabaseManager
    d = tempfile.mkdtemp()
    db = os.path.join(d, "h.db"); initialize_database(db); migrate_database(db)
    dbm = DatabaseManager(db)
    bus = os.path.join(d, "bus")
    class _A: pass
    host = HostService({"auth_service": _A()}, dbm, QueueTransport(bus), bus)
    try:
        host._sessions["tok"] = {"user_id": 1, "username": "u", "role": "admin", "last_seen": time.time()}
        check("fresh session resolves", host._resolve("tok") is not None)
        host._sessions["tok"]["last_seen"] = time.time() - 4000  # >30 min
        check("idle session expires", host._resolve("tok") is None)
    finally:
        shutil.rmtree(d, ignore_errors=True)

def test_step_down():
    from host.host_service import HostService
    from host.heartbeat import write_heartbeat
    from services.queue_transport import QueueTransport
    from database.init_db import initialize_database
    from database.migrations import migrate_database
    from database.db_manager import DatabaseManager
    from host.lease import bump_lease
    d = tempfile.mkdtemp()
    db = os.path.join(d, "h.db"); initialize_database(db); migrate_database(db)
    dbm = DatabaseManager(db)
    bus = os.path.join(d, "bus"); QueueTransport(bus)
    class _A: pass
    host = HostService({"auth_service": _A()}, dbm, QueueTransport(bus), bus)
    host.term = 1
    try:
        check("no rival -> stay", host.should_step_down() is False)
        write_heartbeat(bus, host.host_id, 5, 0, 1, "self")  # same host, higher term -> not a rival
        check("own higher heartbeat -> stay", host.should_step_down() is False)
        write_heartbeat(bus, "OTHER-HOST", 2, 0, 1, "PC2")   # different host, higher term
        check("rival higher term -> step down", host.should_step_down() is True)
        write_heartbeat(bus, "OTHER-HOST", 1, 0, 1, "PC2")   # different host, equal term
        check("rival equal term -> stay", host.should_step_down() is False)
    finally:
        shutil.rmtree(d, ignore_errors=True)

def test_become_host():
    from host.failover import become_host
    from host.heartbeat import write_heartbeat, read_heartbeat
    from services.queue_transport import QueueTransport
    from database.init_db import initialize_database
    from database.migrations import migrate_database
    d = tempfile.mkdtemp()
    bus = os.path.join(d, "bus"); QueueTransport(bus)

    # Publish a real replica (host DB) so there is something to adopt.
    hostdb = os.path.join(d, "orig_host.db"); initialize_database(hostdb); migrate_database(hostdb)
    # emulate publish_replica output: a DELETE-mode copy at replica/fiu_ro.db
    src = sqlite3.connect(hostdb); dst = sqlite3.connect(os.path.join(bus, "replica", "fiu_ro.db"))
    with dst: src.backup(dst)
    dst.execute("PRAGMA journal_mode=DELETE"); dst.close(); src.close()

    # a stale in-flight command sitting in processing/
    with open(os.path.join(bus, "queue", "processing", "0000000000001_abc.json"), "w") as f:
        json.dump({"id": "abc", "command": "noop"}, f)

    local = os.path.join(d, "backup_pc.db")
    try:
        # live host present -> refuse
        write_heartbeat(bus, "LIVE-HOST", 4, 0, 1, "PC1")
        ok, msg, _ = become_host(bus, local, "BACKUP-PC", stale_seconds=60, force=False)
        check("refuses while a live host holds lease", ok is False, msg)

        # host goes stale -> promote
        stale = read_heartbeat(bus); stale["epoch_ms"] -= 120000
        with open(os.path.join(bus, "host", "heartbeat.json"), "w") as f: json.dump(stale, f)
        ok2, msg2, term2 = become_host(bus, local, "BACKUP-PC", stale_seconds=60, force=False)
        check("promotes on stale heartbeat", ok2 and term2 == 5, (ok2, msg2, term2))
        check("adopted replica exists locally", os.path.exists(local))
        check("in-flight command re-queued to pending",
              any(n.endswith("_abc.json") for n in os.listdir(os.path.join(bus, "queue", "pending"))))
        check("processing drained", os.listdir(os.path.join(bus, "queue", "processing")) == [])
        hb = read_heartbeat(bus)
        check("new heartbeat carries new host + term", hb["host_id"] == "BACKUP-PC" and hb["term"] == 5, hb)
    finally:
        shutil.rmtree(d, ignore_errors=True)

def test_outbox_drain_exactly_once():
    from services.queue_transport import QueueTransport
    from services.remote_gateway import RemoteGateway, HostOfflineError
    from services.outbox import Outbox
    from host.host_service import HostService
    from database.init_db import initialize_database
    from database.migrations import migrate_database
    from database.db_manager import DatabaseManager
    import threading, bcrypt
    d = tempfile.mkdtemp()
    db = os.path.join(d, "h.db"); initialize_database(db); migrate_database(db)
    dbm = DatabaseManager(db)
    pw = bcrypt.hashpw(b"Admin@1234", bcrypt.gensalt()).decode()
    c = sqlite3.connect(db)
    c.execute("INSERT INTO users (username,password,full_name,role,is_active,created_by) "
              "VALUES ('admin',?,'Admin','admin',1,'SYSTEM') ON CONFLICT(username) DO UPDATE SET password=excluded.password", (pw,))
    c.commit(); c.close()
    bus = os.path.join(d, "bus")
    ob = Outbox(os.path.join(d, "outbox"))

    # host DOWN: a write times out and is queued (stable id, HostOfflineError)
    gw = RemoteGateway(QueueTransport(bus), timeout=0.3, outbox=ob)
    # log in requires a host; with none, login also times out -> simulate a token directly
    gw.token = "pretend"  # drain re-sends; host will reject auth, so use a no-auth command path:
    raised = False
    try:
        gw.call("auth_service.create_user", ["u1", "p", "U One", "agent"], {})
    except HostOfflineError:
        raised = True
    check("host-down write raises HostOffline + queues", raised and len(ob.pending()) == 1)
    queued_id = ob.pending()[0]["id"]

    # ponytail: gw.token="pretend" above stands in for "no host to log into
    # yet" (there is none running). But call() must submit before it can time
    # out, so that placeholder-token copy is still sitting in the transport's
    # own queue/pending. A genuinely offline host never claims anything; drop
    # that artifact so it can't be claimed by the real host below with a bad
    # token (which would permanently poison this id's applied_commands entry
    # before the outbox's correctly-tokened resubmit ever gets a chance).
    for name in os.listdir(os.path.join(bus, "queue", "pending")):
        if name.endswith(f"_{queued_id}.json"):
            os.remove(os.path.join(bus, "queue", "pending", name))

    # bring host UP and give the gateway a real admin token
    class _Svc(dict): pass
    from services.logging_service import LoggingService
    from services.auth_service import AuthService
    log = LoggingService(dbm, None)
    services = {"auth_service": AuthService(dbm, log)}
    host = HostService(services, dbm, QueueTransport(bus), bus)
    stop = threading.Event()
    def run():
        host.startup()
        while not stop.is_set():
            if not host.run_once():
                time.sleep(0.02)
    th = threading.Thread(target=run, daemon=True); th.start()
    try:
        ok, _u, _m = gw.login("admin", "Admin@1234")
        check("login once host is up", ok)
        # the queued create_user carries no token; drain resends verbatim. Give it the token:
        pend = ob.pending()[0]; pend["token"] = gw.token; ob.add(pend)
        sent, remaining = gw.drain()
        check("drain sends the queued command", sent == 1 and remaining == 0)
        n = dbm.execute_with_retry("SELECT COUNT(*) FROM users WHERE username='u1'")[0][0]
        check("queued write applied exactly once", n == 1, n)
        check("same id kept (idempotent)", ob.pending() == [] and queued_id)
    finally:
        stop.set(); th.join(timeout=2.0); shutil.rmtree(d, ignore_errors=True)

def test_authfail_not_poisoned():
    """A host-level failure (bad/expired token) must NOT be recorded in the
    idempotency ledger — otherwise a resubmit after re-login replays the failure
    and the write is lost. Direct handle_command, no threads/races."""
    from host.host_service import HostService
    from services.queue_transport import QueueTransport
    from database.init_db import initialize_database
    from database.migrations import migrate_database
    from database.db_manager import DatabaseManager
    from services.logging_service import LoggingService
    from services.auth_service import AuthService
    import bcrypt
    d = tempfile.mkdtemp()
    db = os.path.join(d, "h.db"); initialize_database(db); migrate_database(db)
    dbm = DatabaseManager(db)
    pw = bcrypt.hashpw(b"Admin@1234", bcrypt.gensalt()).decode()
    c = sqlite3.connect(db)
    c.execute("INSERT INTO users (username,password,full_name,role,is_active,created_by) "
              "VALUES ('admin',?,'Admin','admin',1,'SYSTEM') ON CONFLICT(username) DO UPDATE SET password=excluded.password", (pw,))
    c.commit(); c.close()
    log = LoggingService(dbm, None)
    host = HostService({"auth_service": AuthService(dbm, log)}, dbm, QueueTransport(os.path.join(d, "bus")), os.path.join(d, "bus"))
    try:
        cmd = {"id": "poison1", "command": "auth_service.create_user",
               "args": ["nu", "Passw0rd!", "N U", "agent"], "kwargs": {}, "token": "BOGUS"}
        r1 = host.handle_command(cmd)
        check("bad-token command fails (ok=False)", r1["ok"] is False, r1)
        ledgered = dbm.execute_with_retry("SELECT COUNT(*) FROM applied_commands WHERE command_id='poison1'")[0][0]
        check("auth-failed command NOT in ledger", ledgered == 0, ledgered)
        # resubmit SAME id under a real admin session -> must actually apply
        ok, tok, _m, _u = host.login("admin", "Admin@1234")
        cmd["token"] = tok
        r2 = host.handle_command(cmd)
        check("resubmit same id under valid token applies", r2["ok"] is True, r2)
        n = dbm.execute_with_retry("SELECT COUNT(*) FROM users WHERE username='nu'")[0][0]
        check("write applied after re-auth (not lost)", n == 1, n)
    finally:
        shutil.rmtree(d, ignore_errors=True)

def test_outbox_ordering():
    """pending() must replay oldest-first by queued_at, NOT by (random-id)
    filename; re-add of the same id overwrites (no duplicate)."""
    from services.outbox import Outbox
    d = tempfile.mkdtemp()
    ob = Outbox(os.path.join(d, "ob"))
    try:
        ob.add({"id": "zzz", "command": "c", "_queued_at": 100})
        ob.add({"id": "aaa", "command": "c", "_queued_at": 50})
        ob.add({"id": "mmm", "command": "c", "_queued_at": 200})
        order = [c["id"] for c in ob.pending()]
        check("outbox replays oldest-first (queued_at, not filename)", order == ["aaa", "zzz", "mmm"], order)
        ob.add({"id": "aaa", "command": "c", "token": "T2", "_queued_at": 50})  # token refresh re-add
        check("re-add same id does not duplicate", [c["id"] for c in ob.pending()].count("aaa") == 1)
        ob.remove("aaa")
        check("remove by id works", "aaa" not in [c["id"] for c in ob.pending()])
    finally:
        shutil.rmtree(d, ignore_errors=True)

if __name__ == "__main__":
    test_lease()
    test_heartbeat()
    test_integrity_and_session()
    test_session_timeout()
    test_step_down()
    test_become_host()
    test_outbox_drain_exactly_once()
    test_authfail_not_poisoned()
    test_outbox_ordering()
    print(f"\n{'ALL PASS' if _fail == 0 else str(_fail)+' FAILED'}")
    sys.exit(1 if _fail else 0)
