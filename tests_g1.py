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

if __name__ == "__main__":
    test_config_mode()
    print(f"\n{'ALL PASS' if _fail == 0 else str(_fail)+' FAILED'}")
    sys.exit(1 if _fail else 0)
