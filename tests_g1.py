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

if __name__ == "__main__":
    test_config_mode()
    test_host_login_returns_user()
    print(f"\n{'ALL PASS' if _fail == 0 else str(_fail)+' FAILED'}")
    sys.exit(1 if _fail else 0)
