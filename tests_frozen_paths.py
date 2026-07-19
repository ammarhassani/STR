"""Where a packaged .exe keeps its writable data. Run: python tests_frozen_paths.py

The distributable build shipped two ways of losing a client's data, and only
the first one announced itself:

  1. The exe died on a fresh PC with "No module named components", because the
     build never bundled the packages under flet_app/.
  2. Behind that, config.py resolved paths from Path(__file__), which inside a
     --onefile bundle points into ...\\Temp\\_MEIxxxxx -- a directory Windows
     deletes when the app exits. Every client would have started blank on every
     launch, silently, with no error at all.

These checks need no build: they fake the frozen environment the same way
PyInstaller sets it up.
"""
import importlib
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_fail = 0


def check(label, cond, detail=""):
    global _fail
    ok = bool(cond)
    print(("PASS " if ok else "FAIL ") + label + ("" if ok else f"  -- {detail}"))
    if not ok:
        _fail += 1


def _frozen_paths(exe_dir, meipass):
    """Values config resolves to with sys.frozen set, as PyInstaller sets it.

    Returns a SNAPSHOT, not the module. Reloading config to restore it mutates
    the same module object in place, so handing the module back would let the
    caller read post-restore values and report a pass no matter what the frozen
    behaviour was -- the first version of this test did exactly that and failed
    against a fix that was already correct.
    """
    import config as _config
    old = (getattr(sys, "frozen", None), getattr(sys, "_MEIPASS", None),
           sys.executable)
    sys.frozen = True
    sys._MEIPASS = meipass
    sys.executable = os.path.join(exe_dir, "FIU_System.exe")
    try:
        frozen = importlib.reload(_config)
        return {
            "base": str(frozen.app_base_dir()),
            "config": str(frozen.Config.CONFIG_FILE),
            "replica": frozen.Config.get_client_replica_path(),
            "outbox": frozen.Config.get_client_outbox_dir(),
        }
    finally:
        if old[0] is None:
            del sys.frozen
        else:
            sys.frozen = old[0]
        if old[1] is None:
            if hasattr(sys, "_MEIPASS"):
                del sys._MEIPASS
        else:
            sys._MEIPASS = old[1]
        sys.executable = old[2]
        importlib.reload(_config)  # leave the module as the rest of the suite expects


def test_frozen_data_lives_beside_the_exe():
    exe_dir = os.path.join(tempfile.mkdtemp(), "STR")
    meipass = os.path.join(tempfile.mkdtemp(), "_MEI12345")
    os.makedirs(exe_dir, exist_ok=True)
    os.makedirs(meipass, exist_ok=True)

    paths = _frozen_paths(exe_dir, meipass)

    base = paths["base"]
    check("app_base_dir follows the exe, not __file__",
          os.path.normcase(base) == os.path.normcase(exe_dir), base)

    cfg = paths["config"]
    check("config.json sits beside the exe",
          os.path.normcase(cfg).startswith(os.path.normcase(exe_dir)), cfg)
    check("config.json is NOT in the temp bundle",
          not os.path.normcase(cfg).startswith(os.path.normcase(meipass)), cfg)

    # These two are what a client actually writes to all day.
    replica = paths["replica"]
    outbox = paths["outbox"]
    check("the client replica sits beside the exe",
          os.path.normcase(replica).startswith(os.path.normcase(exe_dir)), replica)
    check("the outbox (queued writes) sits beside the exe",
          os.path.normcase(outbox).startswith(os.path.normcase(exe_dir)), outbox)
    check("neither is in the temp bundle",
          not os.path.normcase(replica).startswith(os.path.normcase(meipass))
          and not os.path.normcase(outbox).startswith(os.path.normcase(meipass)),
          f"{replica} | {outbox}")


def test_source_run_is_unchanged():
    """Running from source must keep using the repo root, as it always has."""
    import config as fresh
    importlib.reload(fresh)
    repo = os.path.dirname(os.path.abspath(__file__))
    check("from source, app_base_dir is still the repo root",
          os.path.normcase(str(fresh.app_base_dir())) == os.path.normcase(repo),
          fresh.app_base_dir())
    check("from source, config.json is still in the repo",
          os.path.normcase(str(fresh.Config.CONFIG_FILE)).startswith(
              os.path.normcase(repo)), fresh.Config.CONFIG_FILE)


def test_config_survives_a_byte_order_mark():
    """A BOM in config.json must not silently reset the app to unconfigured.

    Notepad and PowerShell's Out-File write UTF-8 with a BOM by default, so an
    operator editing a client's config.json produces one without knowing. With
    encoding='utf-8' json.load raises, Config.load swallows it and returns
    False, and the app opens the first-run setup wizard as if it had never been
    configured -- on a windowed .exe the printed error goes nowhere. Found when
    exactly this happened to a client test box.
    """
    import config as cfg
    importlib.reload(cfg)
    d = tempfile.mkdtemp()
    path = os.path.join(d, "config.json")
    payload = ('{"database_path": null, "backup_path": null, '
               '"session_timeout": 30, "max_login_attempts": 5, '
               '"mode": "client", "share_path": "\\\\\\\\SERVER\\\\STR_data", '
               '"host_id": null}')

    old_file, old_mode, old_share = cfg.Config.CONFIG_FILE, cfg.Config.MODE, cfg.Config.SHARE_PATH
    try:
        for label, data in (("with a BOM", "﻿" + payload),
                            ("without a BOM", payload)):
            with open(path, "w", encoding="utf-8") as f:
                f.write(data)
            cfg.Config.MODE, cfg.Config.SHARE_PATH = "local", None
            cfg.Config.CONFIG_FILE = __import__("pathlib").Path(path)
            loaded = cfg.Config.load()
            check(f"config.json loads {label}", loaded, "Config.load returned False")
            check(f"mode read correctly {label}", cfg.Config.MODE == "client",
                  cfg.Config.MODE)
    finally:
        cfg.Config.CONFIG_FILE, cfg.Config.MODE, cfg.Config.SHARE_PATH = (
            old_file, old_mode, old_share)
        importlib.reload(cfg)


def test_the_build_spec_keeps_flet_app_on_the_path():
    """The one line whose absence produced 'No module named components'."""
    spec = os.path.join(os.path.dirname(os.path.abspath(__file__)), "STR.spec")
    check("STR.spec exists", os.path.isfile(spec), spec)
    if not os.path.isfile(spec):
        return
    src = open(spec, encoding="utf-8").read()
    check("STR.spec puts flet_app on pathex", "'flet_app'" in src and "pathex" in src)
    for data in ("schema.sql", "second_reasons.json", "assets"):
        check(f"STR.spec bundles {data}", data in src)


if __name__ == "__main__":
    test_frozen_data_lives_beside_the_exe()
    test_source_run_is_unchanged()
    test_config_survives_a_byte_order_mark()
    test_the_build_spec_keeps_flet_app_on_the_path()
    print(f"\n{'ALL PASS' if _fail == 0 else str(_fail) + ' FAILED'}")
    sys.exit(1 if _fail else 0)
