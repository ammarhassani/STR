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

if __name__ == "__main__":
    test_lease()
    test_heartbeat()
    print(f"\n{'ALL PASS' if _fail == 0 else str(_fail)+' FAILED'}")
    sys.exit(1 if _fail else 0)
