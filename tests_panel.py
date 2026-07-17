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

def _seed_bus_and_db():
    from services.queue_transport import QueueTransport
    from database.init_db import initialize_database
    from database.migrations import migrate_database
    d = tempfile.mkdtemp()
    bus = os.path.join(d, "bus"); QueueTransport(bus)
    db = os.path.join(d, "local.db"); initialize_database(db); migrate_database(db)
    return d, bus, db


def test_panel_controller():
    from panel.panel_controller import PanelController
    from host.heartbeat import write_heartbeat
    d, bus, db = _seed_bus_and_db()
    pc = PanelController(bus, db, host_id="PANEL-PC")
    try:
        st = pc.status()
        check("status: host offline when no heartbeat", st["host_online"] is False)
        write_heartbeat(bus, "HOSTX", 7, 123, 1, "PC1")
        st2 = pc.status()
        check("status: host online + term from heartbeat", st2["host_online"] and st2["term"] == 7, st2)
        # queue depth
        open(os.path.join(bus, "queue", "pending", "0000000000001_a.json"), "w").write("{}")
        check("status: counts pending", pc.status()["queue_pending"] == 1)
        # manual backup + list + restore
        ok, msg = pc.manual_backup()
        check("manual backup ok", ok, msg)
        check("list_backups sees it", len(pc.list_backups()) == 1)
        okr, msgr = pc.restore_backup(pc.list_backups()[0])
        check("restore ok", okr, msgr)
        check("restore refuses unknown", pc.restore_backup("nope.db")[0] is False)
        # integrity on a healthy db
        oki, _ = pc.run_integrity()
        check("integrity ok", oki)
        # start_host uses injected spawn (no real host)
        calls = {}
        def fake_spawn(cmd, **kw): calls["cmd"] = cmd; return type("P", (), {"pid": 4321})()
        oks, msgs = pc.start_host(spawn=fake_spawn)
        check("start_host launches --host detached", oks and "--host" in " ".join(calls["cmd"]), (msgs, calls))
        # become_host on a stale heartbeat
        stale = __import__("json").load(open(os.path.join(bus, "host", "heartbeat.json")))
        stale["epoch_ms"] -= 120000
        open(os.path.join(bus, "host", "heartbeat.json"), "w").write(__import__("json").dumps(stale))
        # need a replica to adopt
        import sqlite3
        src = sqlite3.connect(db); dst = sqlite3.connect(os.path.join(bus, "replica", "fiu_ro.db"))
        with dst: src.backup(dst)
        dst.execute("PRAGMA journal_mode=DELETE"); dst.close(); src.close()
        okb, msgb, term = pc.become_host_now()
        check("become_host_now promotes on stale hb", okb and term >= 8, (msgb, term))
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_panel_cli_dispatch():
    from panel.control_panel import run_action
    from panel.panel_controller import PanelController
    d, bus, db = _seed_bus_and_db()
    class _Cfg:
        MODE = "client"; HOST_ID = "H"
        @classmethod
        def ensure_host_id(cls): return cls.HOST_ID
        @classmethod
        def save(cls): pass
    pc = PanelController(bus, db, host_id="H")
    try:
        out = run_action(pc, "status", _Cfg)
        check("cli status prints host state", "host" in out.lower())
        out2 = run_action(pc, "backup", _Cfg)
        check("cli backup runs", "backup" in out2.lower())
        out3 = run_action(pc, "list", _Cfg)
        check("cli list runs", isinstance(out3, str))
        out4 = run_action(pc, "designate", _Cfg)
        check("cli designate sets host mode", _Cfg.MODE == "host", out4)
        check("cli unknown choice is handled", "unknown" in run_action(pc, "zzz", _Cfg).lower())
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_host_status_and_outbox_depth():
    from services.host_status import HostStatus
    from host.heartbeat import write_heartbeat
    from services.queue_transport import QueueTransport
    from services.outbox import Outbox
    d = tempfile.mkdtemp(); bus = os.path.join(d, "bus"); QueueTransport(bus)
    hs = HostStatus(bus, stale_seconds=60)
    try:
        check("host offline with no heartbeat", hs.online() is False)
        write_heartbeat(bus, "H", 1, 0, 1, "PC")
        check("host online with fresh heartbeat", hs.online() is True)
        ob = Outbox(os.path.join(d, "ob"))
        ob.add({"id": "w1", "command": "c", "args": [], "kwargs": {}})
        check("outbox depth reflects queued write", len(ob.pending()) == 1)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_host_banner_builds():
    # Structural only — Flet cannot be driven headlessly here.
    import flet as ft
    from flet_app.components.host_banner import build_host_banner
    class _HS:
        def online(self): return False
    class _AS:
        host_status = _HS()
        def pending_writes(self): return 3
    ctrl = build_host_banner(_AS())
    check("host banner builds a Control", isinstance(ctrl, ft.Control))


if __name__ == "__main__":
    test_config_host_id()
    test_panel_controller()
    test_panel_cli_dispatch()
    test_host_status_and_outbox_depth()
    test_host_banner_builds()
    print(f"\n{'ALL PASS' if _fail == 0 else str(_fail)+' FAILED'}")
    sys.exit(1 if _fail else 0)
