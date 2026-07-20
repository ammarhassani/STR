"""G1 client-mode activation tests. Run: python3.14 tests_g1.py"""
import os, sys, json, tempfile, shutil, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
    with open(ver, "w", encoding="utf-8") as f: f.write("1")
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
    with open(ver, "w", encoding="utf-8") as f: f.write("2")
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
    # close the handle: on Windows a leaked reader locks the file and the host's
    # next publish_replica() can never swap it.
    _pub = sqlite3.connect(os.path.join(bus, "replica", "fiu_ro.db"))
    pubjm = _pub.execute("PRAGMA journal_mode").fetchone()[0]
    _pub.close()
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


def test_outbox_drains_after_host_restart():
    """A write queued while the host was down carries the token of the session
    that died with it. A NEW host instance rejects that token, so the queued
    write only becomes drainable after a fresh login — which is why
    app_state.login() drains. Proven here without the UI."""
    import tempfile, sqlite3, threading, bcrypt
    from database.init_db import initialize_database
    from database.db_manager import DatabaseManager
    from database.migrations import migrate_database
    from services.logging_service import LoggingService
    from services.auth_service import AuthService
    from services.report_service import ReportService
    from services.report_number_service import ReportNumberService
    from services.activity_service import ActivityService
    from host.host_service import HostService
    from services.queue_transport import QueueTransport
    from services.remote_gateway import RemoteGateway, HostOfflineError
    from services.outbox import Outbox

    d = tempfile.mkdtemp()
    db = os.path.join(d, "h.db"); initialize_database(db); migrate_database(db)
    dbm = DatabaseManager(db)
    pw = bcrypt.hashpw(b"Admin@1234", bcrypt.gensalt()).decode()
    c = sqlite3.connect(db)
    c.execute("UPDATE users SET password=?, must_change_password=0 WHERE username='admin'", (pw,))
    c.commit(); c.close()
    log = LoggingService(dbm, None, db_logging=False)
    auth = AuthService(dbm, log)
    act = ActivityService(dbm, log, auth)
    nums = ReportNumberService(dbm, log)
    reports = ReportService(dbm, log, auth)
    reports.set_activity_service(act); reports.set_report_number_service(nums)
    services = {"auth_service": auth, "report_service": reports,
                "report_number_service": nums, "activity_service": act}
    bus = os.path.join(d, "bus")
    for sub in ("", "replica", ".tmp"):
        os.makedirs(os.path.join(bus, sub), exist_ok=True)

    def serve(host, stop):
        host.publish_replica()
        while not stop.is_set():
            if not host.run_once():
                time.sleep(0.02)

    # --- host #1: log in, reserve a number, then the host dies
    host1 = HostService(services, dbm, QueueTransport(bus), bus)
    stop1 = threading.Event()
    th1 = threading.Thread(target=serve, args=(host1, stop1), daemon=True); th1.start()
    outbox = Outbox(os.path.join(d, "outbox"))
    gw = RemoteGateway(QueueTransport(bus), timeout=5.0, outbox=outbox)
    ok, user, _ = gw.login("admin", "Admin@1234")
    check("restart: logged in against host #1", ok)
    gw.call("report_number_service.reserve_block", ["admin", 1], {})
    stop1.set(); th1.join(timeout=2.0)

    # --- host down: the write queues instead of failing
    try:
        gw.call("report_service.create_report",
                [{"report_date": "04/11/2025", "reported_entity_name": "Queued"}], {})
        check("restart: write queued while host down", False, "write unexpectedly succeeded")
    except HostOfflineError:
        check("restart: write queued while host down", len(outbox.pending()) == 1)

    # --- host #2 (a restart): the OLD token is unknown to it
    host2 = HostService(services, dbm, QueueTransport(bus), bus)
    stop2 = threading.Event()
    th2 = threading.Thread(target=serve, args=(host2, stop2), daemon=True); th2.start()
    try:
        gw.drain()
        check("restart: stale-token drain leaves the write queued", len(outbox.pending()) == 1,
              outbox.pending())
        # a fresh login is what makes it drainable (app_state.login drains here)
        ok2, _, _ = gw.login("admin", "Admin@1234")
        sent, left = gw.drain()
        check("restart: fresh login drains the queued write", ok2 and sent == 1 and left == 0,
              (sent, left))
        n = dbm.execute_with_retry(
            "SELECT COUNT(*) FROM reports WHERE reported_entity_name='Queued'")[0][0]
        check("restart: queued write applied exactly once", n == 1, n)
    finally:
        stop2.set(); th2.join(timeout=2.0); shutil.rmtree(d, ignore_errors=True)


def test_no_script_host_launchers_remain():
    """The .vbs launchers are gone and must not come back.

    They started the app through WScript -> cmd -> python with a hidden window,
    which is indistinguishable from a malware dropper to endpoint security; the
    bank's EDR flagged them on 2026-07-20. Clients run the packaged executable
    and need no launcher at all, so the pattern is removed rather than excluded
    from detection. This test is the guard against it being reintroduced.
    """
    import pathlib
    root = pathlib.Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    strays = [str(p.relative_to(root)) for p in root.rglob("*.vbs")
              if ".git" not in str(p)]
    check("no .vbs anywhere in the repo", not strays, strays)

    for p in (root / "deploy").glob("*.bat"):
        src = p.read_text(encoding="utf-8", errors="replace").lower()
        check(f"{p.name} does not resurrect a .vbs launcher", ".vbs" not in src)


def test_unc_share_misconfiguration_is_caught():
    """A share path meant to be UNC but written with ONE backslash.

    On Windows that is not an error: it resolves to a folder on the local C:
    drive. STR then runs happily against a directory no other PC can see -- the
    host publishes a replica nobody reads and clients queue commands nobody
    answers. Nothing fails; the unit just silently stops sharing data. Easy to
    do when hand-editing config.json, where each backslash must be doubled.
    """
    from config import Config
    B = chr(92)
    saved_mode, saved_share = Config.MODE, Config.SHARE_PATH
    try:
        Config.MODE = "host"
        check("a single-backslash share path is flagged",
              Config.warn_if_share_looks_local(B + "SERVER" + B + "share") is not None)
        check("a proper UNC path is accepted",
              Config.warn_if_share_looks_local(B + B + "SERVER" + B + "share") is None)
        check("a mapped drive is accepted",
              Config.warn_if_share_looks_local("Z:" + B + "STR_data") is None)
        check("a local path is accepted",
              Config.warn_if_share_looks_local("C:" + B + "STR_data") is None)
        Config.MODE = "local"
        check("local mode says nothing (it has no share)",
              Config.warn_if_share_looks_local(B + "SERVER" + B + "x") is None)
    finally:
        Config.MODE, Config.SHARE_PATH = saved_mode, saved_share


if __name__ == "__main__":
    test_config_mode()
    test_unc_share_misconfiguration_is_caught()
    test_host_login_returns_user()
    test_replica_sync()
    test_client_replica_readonly()
    test_logging_no_db_handler_client()
    test_client_roundtrip()
    test_outbox_drains_after_host_restart()
    test_no_script_host_launchers_remain()
    print(f"\n{'ALL PASS' if _fail == 0 else str(_fail)+' FAILED'}")
    sys.exit(1 if _fail else 0)
