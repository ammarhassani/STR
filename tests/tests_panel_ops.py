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

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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

    Packaged there is no interpreter and no main.py, so the app exe is launched
    directly. The old code built `python main.py`, which on a client .exe points
    at two things that do not exist there -- the buttons would have done nothing
    on exactly the machines they matter on.

    The frozen case is checked from BOTH executables. It used to be checked only
    from FIU_System.exe, the single identity where `sys.executable` happens to
    be the right answer, which is why the real bug walked straight past it.
    """
    from panel.panel_controller import PanelController

    src = PanelController._launch_cmd("--host")
    check("from source, launches main.py with the flag",
          src[-1] == "--host" and any("main.py" in str(p) for p in src), src)

    # A real directory, not a literal C:\STR\... : the code under test calls
    # os.path.dirname, and on the POSIX box this suite also runs on a backslash
    # is an ordinary character, so a Windows literal would prove nothing.
    install = tempfile.mkdtemp()
    old_frozen, old_exe = getattr(sys, "frozen", None), sys.executable
    sys.frozen = True
    try:
        sys.executable = os.path.join(install, "FIU_System.exe")
        frozen = PanelController._launch_cmd("--host")
        check("packaged in the app, launches the app",
              frozen == [os.path.join(install, "FIU_System.exe"), "--host"], frozen)
        check("packaged, no main.py is referenced",
              not any("main.py" in str(p) for p in frozen), frozen)

        # The bug: from the standalone panel, sys.executable is the PANEL. This
        # launched a second Control Panel, which shared the first one's
        # PyInstaller _MEIxxxxx directory; whichever exited first deleted it out
        # from under the other -- "Failed to remove temporary directory", then a
        # missing base_library.zip in the survivor.
        sys.executable = os.path.join(install, "FIU_Control_Panel.exe")
        from_panel = PanelController._launch_cmd("--host")
        check("packaged in the PANEL, launches the APP and not itself",
              os.path.basename(from_panel[0]) == "FIU_System.exe", from_panel)
        check("and it looks for it beside the panel",
              os.path.dirname(from_panel[0]) == install, from_panel)
    finally:
        if old_frozen is None:
            del sys.frozen
        else:
            sys.frozen = old_frozen
        sys.executable = old_exe


def test_panel_exe_refuses_arguments_meant_for_the_app():
    """FIU_Control_Panel.exe silently ignored --host, so a misroute looked fine."""
    import subprocess as _sp
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    r = _sp.run([sys.executable, os.path.join(root, "panel", "panel_main.py"), "--host"],
                capture_output=True, text=True, timeout=60)
    check("the panel entry point rejects --host instead of ignoring it",
          r.returncode != 0 and "no arguments" in (r.stderr + r.stdout).lower(),
          (r.returncode, r.stderr[-200:]))


def test_start_host_reports_failure_when_the_process_dies():
    """Popen not raising only proves Windows found the file.

    FIU_System.exe --host exits within a second on a PC with no database, and it
    is a windowed exe with nowhere to print why. The panel used to answer
    "host started (pid N)" and the operator went looking for a network fault.
    """
    from panel.panel_controller import PanelController
    import subprocess as _sp
    d, bus, db = _seed()
    c = PanelController(bus, db, "h1")

    class Died:
        pid = 4321
        def wait(self, timeout=None): return 2

    class Lives:
        pid = 4322
        def wait(self, timeout=None): raise _sp.TimeoutExpired("x", timeout)

    ok, msg = c.start_host(spawn=lambda *a, **k: Died())
    check("a host that exits immediately is reported as a failure", ok is False, msg)
    check("and the message says so", "exited" in msg.lower(), msg)

    ok, msg = c.start_host(spawn=lambda *a, **k: Lives())
    check("a host still running after the grace period is a success", ok is True, msg)


def test_client_kit_ships_the_app_not_the_panel():
    """The kit built from FIU_Control_Panel.exe contained no app at all.

    make_client_kit fell back to sys.executable when given no exe. Run from the
    panel that is the PANEL, the isfile() guard passed, and the README told the
    user to double-click a diagnostic tool.
    """
    from panel.panel_controller import PanelController
    d, bus, db = _seed()
    c = PanelController(bus, db, "h1")

    inst = os.path.join(d, "install")
    os.makedirs(inst, exist_ok=True)
    panel_exe = os.path.join(inst, "FIU_Control_Panel.exe")
    app_exe = os.path.join(inst, "FIU_System.exe")
    for p in (panel_exe, app_exe):
        with open(p, "wb") as f:
            f.write(b"MZ")

    dest = os.path.join(d, "kit")
    old_frozen, old_exe = getattr(sys, "frozen", None), sys.executable
    sys.frozen = True
    sys.executable = panel_exe
    try:
        ok, msg = c.make_client_kit(dest, r"\\server\share")
        check("the kit builds", ok, msg)
        shipped = os.listdir(dest)
        check("it contains FIU_System.exe", "FIU_System.exe" in shipped, shipped)
        # The panel ships TOO, and that is the point of it shipping: its stated
        # reason for existing is "the app will not start, so the button on the
        # login screen is unreachable". It was absent from every client PC --
        # precisely the machines where nobody can diagnose anything.
        check("and the Control Panel, so a broken client can be diagnosed",
              "FIU_Control_Panel.exe" in shipped, shipped)
        with open(os.path.join(dest, "READ ME FIRST.txt"), encoding="utf-8") as f:
            readme = f.read()
        check("the README still tells the user to open the APP, not the panel",
              "DOUBLE-CLICK FIU_System.exe" in readme, readme[:200])

        # no app beside the panel -> a plain refusal, never a wrong binary
        os.remove(app_exe)
        ok2, msg2 = c.make_client_kit(os.path.join(d, "kit2"), r"\\server\share")
        check("with no app to copy it refuses rather than shipping the panel",
              ok2 is False and "FIU_System.exe" in msg2, msg2)
    finally:
        if old_frozen is None:
            del sys.frozen
        else:
            sys.frozen = old_frozen
        sys.executable = old_exe


def test_health_measures_THIS_pc_not_the_share():
    """The panel reported the opposite of the truth on every client PC.

    Two separate bugs, one screen -- and docs/OPERATIONS.md opens by telling the
    operator to read that screen every morning.

    1. "Data copy updated" stat'd the replica on the SHARE, which is when the
       HOST last published. A client whose ReplicaRefresher had died showed a
       perfectly fresh timestamp while serving hours-old AML data.
    2. "Waiting to save" counted the SHARED queue. A client's unsent writes live
       in its LOCAL outbox, so an analyst with 40 stuck reports read 0.
    """
    from panel.panel_controller import PanelController
    d, bus, db = _seed()

    # a local replica that is old, and a share replica that is fresh
    local_replica = os.path.join(d, "client_replica.db")
    with open(local_replica, "wb") as f:
        f.write(b"x")
    os.utime(local_replica, (time.time() - 7200, time.time() - 7200))  # 2h old
    share_replica_dir = os.path.join(bus, "replica")
    os.makedirs(share_replica_dir, exist_ok=True)
    with open(os.path.join(share_replica_dir, "fiu_ro.db"), "wb") as f:
        f.write(b"x")                                                  # just now

    outbox = os.path.join(d, "outbox")
    os.makedirs(outbox, exist_ok=True)
    for i in range(3):
        with open(os.path.join(outbox, f"cmd{i}.json"), "w") as f:
            f.write("{}")

    c = PanelController(bus, local_replica, "h1", mode="client",
                        outbox_dir=outbox, config_file=os.path.join(d, "config.json"))
    h = c.health(share_path=os.path.dirname(bus))

    check("a client is told about ITS OWN replica, not the host's",
          h["replica_age_seconds"] > 3600, h["replica_age_seconds"])
    check("and the stale copy is reported as a problem",
          any("copy of the data" in p for p in h["problems"]), h["problems"])
    check("the path it measured is named on screen",
          h["replica_path"] == local_replica, h["replica_path"])
    check("unsent writes on THIS PC are counted",
          h["outbox_pending"] == 3, h["outbox_pending"])
    check("and they are reported as a problem",
          any("not been sent" in p for p in h["problems"]), h["problems"])
    check("the client is not nagged about backups (that is the host's job)",
          not any("backups" in p for p in h["problems"]), h["problems"])
    check("the screen says what this PC is set up as", h["mode"] == "client")
    check("and where its settings live", h["config_file"].endswith("config.json"))

    # A HOST keeps measuring the share -- that IS its own copy, and blinding the
    # host operator to their own host having stopped republishing would be a
    # second bug wearing the first one's clothes.
    hc = PanelController(bus, db, "h1", mode="host")
    hh = hc.health(share_path=os.path.dirname(bus))
    check("a host still measures the published replica",
          hh["replica_path"].startswith(bus), hh["replica_path"])


def test_panel_opens_when_the_share_is_gone():
    """The only time anyone opens the diagnostic tool is when things are broken.

    __init__ did makedirs() on the share and let OSError out, so an unreachable
    share killed the window before it drew: no window, no message, at exactly
    the moment the operator needed one.
    """
    from panel.panel_controller import PanelController
    # Under a root that cannot be created, not just one that does not exist yet:
    # makedirs() builds intermediate directories, so a path under a writable
    # temp dir would have been MADE reachable by the very constructor under
    # test. That is what a real dead UNC path behaves like.
    unreachable = os.path.join(os.sep, "str_no_such_root_9c1f", "share", "str_bus")
    try:
        c = PanelController(unreachable, "", "h1", mode="client")
    except OSError as e:
        check("constructing against an unreachable share must not raise", False, e)
        return
    check("constructing against an unreachable share does not raise", True)
    h = c.health(share_path=os.path.dirname(unreachable))
    check("and health() still answers, naming the share as the problem",
          h["share_ok"] is False and any("Shared folder" in p for p in h["problems"]),
          h["problems"])


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
    root = pathlib.Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
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
    test_panel_exe_refuses_arguments_meant_for_the_app()
    test_start_host_reports_failure_when_the_process_dies()
    test_client_kit_ships_the_app_not_the_panel()
    test_health_measures_THIS_pc_not_the_share()
    test_panel_opens_when_the_share_is_gone()
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
