"""Operator actions added for the multi-PC rollout. Run: python tests_panel_ops.py

These cover the panel buttons an operator presses on a client PC, where a
mistake is least visible and most expensive.
"""
import os
import sys
import json
import time
import socket
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_fail = 0


def check(label, cond, detail=""):
    global _fail
    ok = bool(cond)
    print(("PASS " if ok else "FAIL ") + label + ("" if ok else f"  -- {detail}"))
    if not ok:
        _fail += 1


def _seed():
    from services.queue_transport import QueueTransport
    from database.init_db import initialize_database
    from database.migrations import migrate_database
    d = tempfile.mkdtemp()
    bus = os.path.join(d, "share", "str_bus")
    QueueTransport(bus)
    db = os.path.join(d, "local.db")
    initialize_database(db)
    migrate_database(db)
    return d, bus, db


def test_launch_command_survives_being_packaged():
    """The start buttons must work on a PC with no Python and no main.py.

    Packaged, sys.executable IS the app, so it relaunches itself. The old code
    always built `python main.py`, which on a client .exe points at an
    interpreter and a script that do not exist there -- the buttons would have
    done nothing on exactly the machines they matter on.
    """
    from panel.panel_controller import PanelController

    src = PanelController._launch_cmd("--host")
    check("from source, launches main.py with the flag",
          src[-1] == "--host" and any("main.py" in str(p) for p in src), src)

    old_frozen, old_exe = getattr(sys, "frozen", None), sys.executable
    sys.frozen = True
    sys.executable = r"C:\STR\FIU_System.exe"
    try:
        frozen = PanelController._launch_cmd("--host")
        check("packaged, the exe relaunches ITSELF",
              frozen == [r"C:\STR\FIU_System.exe", "--host"], frozen)
        check("packaged, no main.py is referenced",
              not any("main.py" in str(p) for p in frozen), frozen)
    finally:
        if old_frozen is None:
            del sys.frozen
        else:
            sys.frozen = old_frozen
        sys.executable = old_exe


def test_stop_host_refuses_to_kill_another_pc_s_pid():
    """A pid from a SHARED heartbeat may belong to a different machine.

    The heartbeat lives on the share, so it usually describes a host on another
    PC. Acting on that pid locally would kill whatever unrelated process holds
    that number here -- a random process on an analyst's workstation.
    """
    from panel.panel_controller import PanelController
    from host.heartbeat import write_heartbeat
    d, bus, db = _seed()
    pc = PanelController(bus, db, host_id="THIS-PC")

    killed = []

    ok, msg = pc.stop_host(killer=killed.append)
    check("no heartbeat -> refuses", not ok, msg)

    write_heartbeat(bus, "HOSTX", 1, 123, 4242, "SOME-OTHER-PC")
    ok, msg = pc.stop_host(killer=killed.append)
    check("host on another PC -> refuses", not ok, msg)
    check("and kills nothing", killed == [], killed)
    check("and says where it is running", "SOME-OTHER-PC" in msg, msg)

    write_heartbeat(bus, "HOSTX", 1, 123, 4242, socket.gethostname())
    ok, msg = pc.stop_host(killer=killed.append)
    check("host on THIS PC -> acts", ok, msg)
    check("and targets the heartbeat's pid", killed == [4242], killed)


def test_check_share_requires_write_not_just_read():
    """A client that cannot write cannot queue a single change."""
    from panel.panel_controller import PanelController
    d, bus, db = _seed()
    pc = PanelController(bus, db, host_id="P")

    ok, msg = pc.check_share(os.path.dirname(bus))
    check("a good share reports reachable and writable", ok, msg)

    ok, msg = pc.check_share(os.path.join(d, "does_not_exist"))
    check("a missing share is reported, not crashed on", not ok, msg)

    ok, msg = pc.check_share(None)
    check("an unconfigured share is reported", not ok, msg)


def test_health_names_the_actual_problem():
    from panel.panel_controller import PanelController
    from host.heartbeat import write_heartbeat
    d, bus, db = _seed()
    pc = PanelController(bus, db, host_id="P")

    h = pc.health(share_path=os.path.dirname(bus))
    check("no host -> not healthy", not h["healthy"])
    check("and says nobody can save changes",
          any("host" in p.lower() for p in h["problems"]), h["problems"])
    check("no backups is called out",
          any("backup" in p.lower() for p in h["problems"]), h["problems"])

    write_heartbeat(bus, "HOSTX", 1, 123, os.getpid(), socket.gethostname())
    pc.manual_backup()
    h = pc.health(share_path=os.path.dirname(bus))
    check("with a live host and a backup, it is healthy", h["healthy"], h["problems"])
    check("heartbeat age is reported", h["heartbeat_age_seconds"] is not None)


def test_client_kit_is_ready_to_double_click():
    """The kit must remove every chance to hand-write a config wrong."""
    from panel.panel_controller import PanelController
    d, bus, db = _seed()
    pc = PanelController(bus, db, host_id="P")

    fake_exe = os.path.join(d, "FIU_System.exe")
    with open(fake_exe, "wb") as f:
        f.write(b"MZ fake")

    dest = os.path.join(d, "kit")
    ok, msg = pc.make_client_kit(dest, r"\\ENGAMMARPC\STR_data", exe_path=fake_exe)
    check("kit builds", ok, msg)

    check("exe is in the kit", os.path.isfile(os.path.join(dest, "FIU_System.exe")))
    cfgp = os.path.join(dest, "config", "config.json")
    check("config.json is in the kit", os.path.isfile(cfgp))
    check("a readme is in the kit",
          os.path.isfile(os.path.join(dest, "READ ME FIRST.txt")))

    raw = open(cfgp, "rb").read()
    check("config.json has NO byte-order mark", raw[:3] != b"\xef\xbb\xbf", raw[:4])

    cfg = json.loads(raw.decode("utf-8"))
    check("mode is client", cfg["mode"] == "client", cfg)
    check("share path is set exactly", cfg["share_path"] == r"\\ENGAMMARPC\STR_data", cfg)

    ok, msg = pc.make_client_kit(dest, "")
    check("refuses without a share path", not ok, msg)
    ok, msg = pc.make_client_kit(dest, r"\\X\y", exe_path=os.path.join(d, "nope.exe"))
    check("refuses when the exe is missing, and says to build it",
          not ok and "build" in msg.lower(), msg)


def test_nothing_shells_out_to_powershell_or_com():
    """The app must not create shortcuts via PowerShell or WScript.Shell COM.

    The bank's EDR flagged a script-host launcher, the approval covering this
    work is for Python only, and an earlier version of the panel shelled out to
    PowerShell to write a .lnk -- which would have put the same pattern back.
    Hand-writing the .lnk format instead was tried and rejected by Windows, so
    neither approach ships. This test is the guard against either returning.
    """
    import pathlib
    root = pathlib.Path(os.path.dirname(os.path.abspath(__file__)))
    for rel in ("panel/panel_controller.py", "panel/control_panel_ui.py",
                "flet_app/views/login_view.py"):
        src = (root / rel).read_text(encoding="utf-8")
        # Only executable lines: the comments explain why these are absent.
        code = "\n".join(l for l in src.splitlines()
                         if not l.strip().startswith("#"))
        # Strip docstrings, which also discuss the banned techniques.
        parts = code.split('"""')
        code = "".join(parts[::2])
        for banned in ("powershell", "ComObject", "WScript.Shell", "os.system("):
            check(f"{rel} does not use {banned}",
                  banned.lower() not in code.lower(), banned)


def test_startup_is_a_folder_the_operator_drags_into():
    """No programmatic Startup shortcut: the panel just opens the folder."""
    from panel.panel_controller import PanelController
    d, bus, db = _seed()
    pc = PanelController(bus, db, host_id="P")
    folder = pc.startup_folder()
    check("startup folder path is built", folder.endswith("Startup"), folder)
    check("no install_startup_shortcut remains",
          not hasattr(pc, "install_startup_shortcut"))
    check("no install_panel_shortcut remains",
          not hasattr(pc, "install_panel_shortcut"))


def test_client_kit_ships_no_shortcut():
    """A .lnk Windows refuses to open is worse than no .lnk at all."""
    from panel.panel_controller import PanelController
    d, bus, db = _seed()
    pc = PanelController(bus, db, host_id="P")
    fake_exe = os.path.join(d, "FIU_System.exe")
    with open(fake_exe, "wb") as f:
        f.write(b"MZ fake")
    dest = os.path.join(d, "kit2")
    ok, _ = pc.make_client_kit(dest, r"\\S\share", exe_path=fake_exe)
    check("kit still builds", ok)
    lnks = [n for n in os.listdir(dest) if n.lower().endswith(".lnk")]
    check("the kit ships no .lnk", not lnks, lnks)


def test_panel_window_builds():
    """The panel screen must construct without throwing.

    It is a thin skin, so the risk here is not logic but a typo that only
    surfaces at render: a wrong ft.Icons name, a bad attribute. An operator
    finding that on the host PC during a rollout is the worst place to find it.
    """
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "flet_app"))
    import flet as ft
    from panel import control_panel_ui

    class FakeWindow:
        width = height = None

    class FakePage:
        def __init__(self):
            self.controls = []
            self.window = FakeWindow()
            self.title = self.bgcolor = self.padding = None

        def add(self, *c):
            self.controls.extend(c)

        def update(self):
            pass

    d, bus, db = _seed()
    from config import Config
    Config.DATABASE_PATH = db
    Config.SHARE_PATH = os.path.dirname(bus)
    Config.CONFIG_FILE = __import__("pathlib").Path(d) / "config.json"

    page = FakePage()
    try:
        control_panel_ui.build_panel(page)
        check("the panel screen builds", bool(page.controls))
        check("the window is sized", page.window.width and page.window.height)
        check("it is titled", page.title == "STR Control Panel", page.title)
    except Exception as e:
        check("the panel screen builds", False, f"{type(e).__name__}: {e}")


def test_durations_are_human():
    from panel.control_panel_ui import _ago
    check("seconds stay seconds", _ago(30) == "30 seconds ago", _ago(30))
    check("minutes read as minutes", _ago(600) == "10 minutes ago", _ago(600))
    check("54065s reads as hours, not seconds", _ago(54065) == "15 hours ago",
          _ago(54065))
    check("days read as days", _ago(200000) == "2 days ago", _ago(200000))
    check("never is handled", _ago(None) == "never", _ago(None))
    check("singular is not '1 hours'", _ago(3700) == "1 hour ago", _ago(3700))


if __name__ == "__main__":
    test_launch_command_survives_being_packaged()
    test_stop_host_refuses_to_kill_another_pc_s_pid()
    test_check_share_requires_write_not_just_read()
    test_health_names_the_actual_problem()
    test_client_kit_is_ready_to_double_click()
    test_nothing_shells_out_to_powershell_or_com()
    test_startup_is_a_folder_the_operator_drags_into()
    test_client_kit_ships_no_shortcut()
    test_panel_window_builds()
    test_durations_are_human()
    print(f"\n{'ALL PASS' if _fail == 0 else str(_fail) + ' FAILED'}")
    sys.exit(1 if _fail else 0)
