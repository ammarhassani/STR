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

if __name__ == "__main__":
    test_config_mode()
    test_host_login_returns_user()
    test_replica_sync()
    test_logging_no_db_handler_client()
    print(f"\n{'ALL PASS' if _fail == 0 else str(_fail)+' FAILED'}")
    sys.exit(1 if _fail else 0)
