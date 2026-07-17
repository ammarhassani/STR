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

if __name__ == "__main__":
    test_lease()
    test_heartbeat()
    test_integrity_and_session()
    test_session_timeout()
    test_step_down()
    test_become_host()
    print(f"\n{'ALL PASS' if _fail == 0 else str(_fail)+' FAILED'}")
    sys.exit(1 if _fail else 0)
