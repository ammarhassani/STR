"""G1 client-mode activation tests. Run: python3.14 tests_g1.py"""
import os, sys, json, tempfile, shutil, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_fail = 0
def check(label, cond, detail=""):
    global _fail
    ok = bool(cond)
    print(("PASS " if ok else "FAIL ") + label + ("" if ok else f"  -- {detail}"))
    if not ok:
        _fail += 1

def test_config_mode():
    from config import Config
    # defaults
    Config.MODE = "local"; Config.SHARE_PATH = None
    check("cfg default mode local", Config.MODE == "local")
    # client mode is configured when SHARE_PATH is set, even with no local DB
    Config.MODE = "client"; Config.SHARE_PATH = tempfile.mkdtemp(); Config.DATABASE_PATH = None
    check("cfg client configured with share, no db", Config.is_configured() is True)
    # bus derives from SHARE_PATH
    bus = Config.get_bus_dir()
    check("cfg bus under share", bus.startswith(Config.SHARE_PATH) and bus.endswith("str_bus"))
    # client replica path is local and ends with client_replica.db
    rp = Config.get_client_replica_path()
    check("cfg client replica path", rp.endswith("client_replica.db"))
    shutil.rmtree(Config.SHARE_PATH, ignore_errors=True)
    Config.MODE = "local"; Config.SHARE_PATH = None

def test_host_login_returns_user():
    import tempfile, sqlite3
    from database.init_db import initialize_database
    from database.db_manager import DatabaseManager
    from database.migrations import migrate_database
    from services.logging_service import LoggingService
    from services.auth_service import AuthService
    from host.host_service import HostService
    from services.queue_transport import QueueTransport
    d = tempfile.mkdtemp()
    db = os.path.join(d, "h.db"); initialize_database(db); migrate_database(db)
    dbm = DatabaseManager(db)
    c = sqlite3.connect(db)
    import bcrypt
    pw = bcrypt.hashpw(b"Admin@1234", bcrypt.gensalt()).decode()
    c.execute("INSERT INTO users (username,password,full_name,role,is_active,created_by) "
              "VALUES ('admin',?,'Admin','admin',1,'SYSTEM') ON CONFLICT(username) DO UPDATE SET password=excluded.password",
              (pw,)); c.commit(); c.close()
    log = LoggingService(dbm, None)
    services = {"auth_service": AuthService(dbm, log)}
    bus = os.path.join(d, "bus"); os.makedirs(bus)
    host = HostService(services, dbm, QueueTransport(bus), bus)
    # queued login result must carry the user dict
    resp = host.handle_command({"id": "L1", "command": "login", "args": ["admin", "Admin@1234"], "kwargs": {}})
    check("host login result has token", resp["ok"] and resp["result"].get("token"))
    check("host login result has user", bool(resp["result"].get("user")), resp)
    check("host login user has role", resp["result"]["user"].get("role") == "admin")
    shutil.rmtree(d, ignore_errors=True)

def test_replica_sync():
    from services.replica_sync import bootstrap_replica, ReplicaRefresher
    d = tempfile.mkdtemp()
    bus = os.path.join(d, "bus"); os.makedirs(os.path.join(bus, "replica"))
    rep = os.path.join(bus, "replica", "fiu_ro.db")
    ver = os.path.join(bus, "replica", "version.txt")
    with open(rep, "wb") as f: f.write(b"DBv1")
    with open(ver, "w") as f: f.write("1")
    local = os.path.join(d, "client_replica.db")
    check("bootstrap copies replica", bootstrap_replica(bus, local, timeout=2.0) and os.path.exists(local))
    check("bootstrap content v1", open(local, "rb").read() == b"DBv1")
    # bootstrap timeout when no replica
    d2 = tempfile.mkdtemp(); bus2 = os.path.join(d2, "bus"); os.makedirs(os.path.join(bus2, "replica"))
    check("bootstrap times out cleanly", bootstrap_replica(bus2, os.path.join(d2, "x.db"), timeout=0.5) is False)
    # refresher picks up a version bump
    hits = {"n": 0}
    r = ReplicaRefresher(bus, local, poll=0.1, on_update=lambda: hits.__setitem__("n", hits["n"] + 1))
    r.start()
    with open(rep, "wb") as f: f.write(b"DBv2")
    with open(ver, "w") as f: f.write("2")
    for _ in range(50):
        if open(local, "rb").read() == b"DBv2": break
        time.sleep(0.1)
    r.stop()
    check("refresher hot-swaps to v2", open(local, "rb").read() == b"DBv2")
    check("refresher fired on_update", hits["n"] >= 1)
    shutil.rmtree(d, ignore_errors=True); shutil.rmtree(d2, ignore_errors=True)

def test_client_replica_readonly():
    """C1: the client's local replica must be opened read-only (no WAL
    sidecars), must pick up a host republish, and must reject writes."""
    import sqlite3
    from services.replica_sync import bootstrap_replica, ReplicaRefresher
    from database.db_manager import DatabaseManager
    from services.queue_transport import QueueTransport
    from host.host_service import HostService

    d = tempfile.mkdtemp()
    bus = os.path.join(d, "bus")
    # Real host DB in WAL mode (DatabaseManager forces WAL, like production).
    # journal_mode is stored in the file header, so publish_replica() must emit
    # a NON-WAL replica or read-only clients spawn -wal/-shm sidecars. Seeding
    # via a plain connect() would hide that bug (the file would never be WAL) —
    # this test drives the REAL host publish pipeline instead.
    host_db = os.path.join(d, "host.db")
    hdbm = DatabaseManager(host_db)  # writable -> WAL
    hdbm.execute_write("CREATE TABLE t (id INTEGER PRIMARY KEY, val TEXT)")
    hdbm.execute_write("INSERT INTO t (val) VALUES ('row1')")

    class _DummyAuth: pass
    transport = QueueTransport(bus)  # creates replica/.tmp/... dirs
    host = HostService({"auth_service": _DummyAuth()}, hdbm, transport, bus)
    host.publish_replica()  # writes bus/replica/fiu_ro.db (DELETE mode) + version.txt

    # Confirm the published replica is NOT WAL-tagged (the actual C1 root cause).
    pubjm = sqlite3.connect(os.path.join(bus, "replica", "fiu_ro.db")).execute(
        "PRAGMA journal_mode").fetchone()[0]
    check("g1ro published replica is non-WAL", pubjm.lower() != "wal", pubjm)

    local = os.path.join(d, "client_replica.db")
    check("g1ro bootstrap ok", bootstrap_replica(bus, local, timeout=2.0) and os.path.exists(local))

    dbm = DatabaseManager(local, read_only=True)
    rows = dbm.execute_with_retry("SELECT val FROM t ORDER BY id")
    check("g1ro reads seed row", [r[0] for r in rows] == ["row1"], rows)
    check("g1ro no wal/shm after read",
          not os.path.exists(local + "-wal") and not os.path.exists(local + "-shm"))

    # Start the refresher BEFORE the host republishes (it snapshots the current
    # version at construction time — it must see the first version, not the second).
    r = ReplicaRefresher(bus, local, poll=0.1)
    r.start()

    # Real host republish: another row, then publish_replica() (full atomic swap
    # + version bump) exactly as the running host would.
    hdbm.execute_write("INSERT INTO t (val) VALUES ('row2')")
    host.publish_replica()

    for _ in range(50):
        if dbm.execute_with_retry("SELECT COUNT(*) FROM t")[0][0] == 2:
            break
        time.sleep(0.1)
    r.stop()

    n = dbm.execute_with_retry("SELECT COUNT(*) FROM t")[0][0]
    check("g1ro sees republished row after refresh", n == 2, n)
    check("g1ro no wal/shm after refresh",
          not os.path.exists(local + "-wal") and not os.path.exists(local + "-shm"))

    try:
        dbm.execute_write("INSERT INTO t (val) VALUES ('nope')")
        check("g1ro write rejected", False, "write succeeded on read-only handle")
    except sqlite3.OperationalError as e:
        check("g1ro write rejected", "readonly" in str(e).lower(), str(e))

    shutil.rmtree(d, ignore_errors=True)


def test_logging_no_db_handler_client():
    from database.init_db import initialize_database
    from database.db_manager import DatabaseManager
    from services.logging_service import LoggingService
    d = tempfile.mkdtemp(); db = os.path.join(d, "l.db"); initialize_database(db)
    dbm = DatabaseManager(db)
    from services.logging_service import DatabaseLogHandler
    ls = LoggingService(dbm, None, db_logging=False)
    has_db = any(isinstance(h, DatabaseLogHandler) for h in ls.logger.handlers)
    check("client logging has no DB handler", not has_db)
    ls2 = LoggingService(dbm, None)  # default keeps DB handler (host/local)
    has_db2 = any(isinstance(h, DatabaseLogHandler) for h in ls2.logger.handlers)
    check("default logging keeps DB handler", has_db2)
    shutil.rmtree(d, ignore_errors=True)

def test_client_roundtrip():
    import tempfile, sqlite3, threading, bcrypt
    from database.init_db import initialize_database
    from database.db_manager import DatabaseManager
    from database.migrations import migrate_database
    from services.logging_service import LoggingService
    from services.auth_service import AuthService
    from host.host_service import HostService
    from services.queue_transport import QueueTransport
    from services.remote_gateway import RemoteGateway, RemoteServiceProxy
    d = tempfile.mkdtemp()
    db = os.path.join(d, "h.db"); initialize_database(db); migrate_database(db)
    dbm = DatabaseManager(db)
    pw = bcrypt.hashpw(b"Admin@1234", bcrypt.gensalt()).decode()
    c = sqlite3.connect(db)
    c.execute("INSERT INTO users (username,password,full_name,role,is_active,created_by) "
              "VALUES ('admin',?,'Admin','admin',1,'SYSTEM') ON CONFLICT(username) DO UPDATE SET password=excluded.password",
              (pw,)); c.commit(); c.close()
    log = LoggingService(dbm, None)
    services = {"auth_service": AuthService(dbm, log)}
    bus = os.path.join(d, "bus")
    for sub in ("", "replica", ".tmp", "cmd", "resp", "done"):
        os.makedirs(os.path.join(bus, sub), exist_ok=True)
    host = HostService(services, dbm, QueueTransport(bus), bus)
    stop = threading.Event()
    def run():
        host.publish_replica()
        while not stop.is_set():
            if not host.run_once():
                time.sleep(0.02)
    th = threading.Thread(target=run, daemon=True); th.start()
    try:
        gw = RemoteGateway(QueueTransport(bus), timeout=10.0)
        ok, user, msg = gw.login("admin", "Admin@1234")
        check("roundtrip login ok", ok and user and user["role"] == "admin", msg)
        proxy = RemoteServiceProxy("auth_service", AuthService(dbm, log), gw)
        res = proxy.create_user("agz", "Passw0rd!", "Ag Z", "agent")
        # create_user returns (ok, msg) business tuple through the queue
        okc = res[0] if isinstance(res, (list, tuple)) else bool(res)
        check("roundtrip proxied create_user", okc, res)
        n = dbm.execute_with_retry("SELECT COUNT(*) FROM users WHERE username='agz'")[0][0]
        check("roundtrip user created host-side", n == 1)
    finally:
        stop.set(); th.join(timeout=2.0); shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    test_config_mode()
    test_host_login_returns_user()
    test_replica_sync()
    test_client_replica_readonly()
    test_logging_no_db_handler_client()
    test_client_roundtrip()
    print(f"\n{'ALL PASS' if _fail == 0 else str(_fail)+' FAILED'}")
    sys.exit(1 if _fail else 0)
