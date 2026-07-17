"""Phase 3b operator + client-UX tests. Run: python3.14 tests_panel.py"""
import os, sys, json, time, tempfile, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_fail = 0
def check(label, cond, detail=""):
    global _fail
    ok = bool(cond)
    print(("PASS " if ok else "FAIL ") + label + ("" if ok else f"  -- {detail}"))
    if not ok:
        _fail += 1

def test_config_host_id():
    from config import Config
    Config.HOST_ID = None
    Config.CONFIG_FILE = __import__("pathlib").Path(tempfile.mkdtemp()) / "config.json"
    Config.DATABASE_PATH = os.path.join(tempfile.mkdtemp(), "db.sqlite")
    hid = Config.ensure_host_id()
    check("ensure_host_id returns a stable id", bool(hid) and Config.HOST_ID == hid)
    check("ensure_host_id is idempotent", Config.ensure_host_id() == hid)
    ob = Config.get_client_outbox_dir()
    check("client outbox dir derived + created", os.path.isdir(ob))

if __name__ == "__main__":
    test_config_host_id()
    print(f"\n{'ALL PASS' if _fail == 0 else str(_fail)+' FAILED'}")
    sys.exit(1 if _fail else 0)
