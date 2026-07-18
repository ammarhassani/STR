"""#19 — self-update: host publishes to the share, clients copy from it.
Run: python3.14 tests_updater.py"""
import os, sys, tempfile, subprocess
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_fail = 0
def check(label, cond, detail=""):
    global _fail
    ok = bool(cond)
    print(("PASS " if ok else "FAIL ") + label + ("" if ok else f"  -- {detail}"))
    if not ok:
        _fail += 1


def _git(args, cwd):
    subprocess.run(["git"] + args, cwd=cwd, check=True, capture_output=True, text=True)


def _make_repo():
    d = tempfile.mkdtemp()
    repo = os.path.join(d, "repo"); os.makedirs(repo)
    _git(["init", "-b", "main"], repo)
    _git(["config", "user.email", "t@t"], repo)
    _git(["config", "user.name", "t"], repo)
    # a couple of tracked code files + a gitignored local file
    Path(repo, "main.py").write_text("print('v1')\n")
    os.makedirs(os.path.join(repo, "services"))
    Path(repo, "services", "svc.py").write_text("VER = 1\n")
    Path(repo, ".gitignore").write_text("config/\nlogs/\n*.db\n")
    _git(["add", "."], repo)
    _git(["commit", "-m", "v1"], repo)
    return repo


def test_host_publish_then_client_consume():
    from updater import publish_to_share, update_from_share, current_version
    repo = _make_repo()
    share = tempfile.mkdtemp()

    # HOST publishes
    ok, msg = publish_to_share(repo, share)
    check("host publishes a snapshot", ok, msg)
    ver = current_version(repo)
    app_dir = Path(share) / "app" / ver
    check("snapshot dir named by version exists", app_dir.is_dir(), str(app_dir))
    check("snapshot has tracked code", (app_dir / "main.py").exists() and (app_dir / "services" / "svc.py").exists())
    check("snapshot excludes gitignored/db (only tracked)", not (app_dir / "config").exists())
    latest = Path(share) / "app" / "latest.txt"
    check("latest.txt points at the version", latest.read_text().strip() == ver, latest.read_text())

    # publishing again is a no-op (idempotent)
    ok2, _ = publish_to_share(repo, share)
    check("re-publish same version is a no-op", not ok2)

    # CLIENT (stale) consumes
    client = tempfile.mkdtemp()
    Path(client, "main.py").write_text("print('OLD')\n")          # stale code
    os.makedirs(os.path.join(client, "config"))
    Path(client, "config", "config.json").write_text("{}")        # local, must survive
    Path(client, "app.db").write_text("localdb")                  # local, must survive

    up, umsg = update_from_share(client, share)
    check("client pulls the new version from the share", up, umsg)
    check("client code is updated", Path(client, "main.py").read_text().strip() == "print('v1')")
    check("client got nested files too", Path(client, "services", "svc.py").exists())
    check("client-local config untouched", Path(client, "config", "config.json").read_text() == "{}")
    check("client-local db untouched", Path(client, "app.db").read_text() == "localdb")
    check("client records the version", Path(client, ".str_version").read_text().strip() == ver)

    # second run is a no-op (already current)
    up2, umsg2 = update_from_share(client, share)
    check("client already-current is a no-op", not up2, umsg2)


def test_client_updates_across_two_publishes():
    from updater import publish_to_share, update_from_share, current_version
    repo = _make_repo(); share = tempfile.mkdtemp(); client = tempfile.mkdtemp()
    publish_to_share(repo, share)
    update_from_share(client, share)
    v1 = current_version(repo)

    # host advances + republishes
    Path(repo, "main.py").write_text("print('v2')\n")
    _git(["add", "."], repo); _git(["commit", "-m", "v2"], repo)
    ok, _ = publish_to_share(repo, share)
    v2 = current_version(repo)
    check("second publish creates a new version", ok and v2 != v1, (v1, v2))
    check("latest.txt advanced", (Path(share) / "app" / "latest.txt").read_text().strip() == v2)

    up, _ = update_from_share(client, share)
    check("client rolls forward to v2", up and Path(client, "main.py").read_text().strip() == "print('v2')")
    # old version kept on the share for rollback
    check("previous version retained on the share for rollback", (Path(share) / "app" / v1).is_dir())


def test_never_clobbers_per_machine_config():
    # even if a snapshot wrongly contains config/ or .str_version, the client's
    # own per-machine files must survive (config bleed guard).
    from updater import update_from_share
    from pathlib import Path
    import os
    share = tempfile.mkdtemp(); client = tempfile.mkdtemp()
    app = Path(share) / "app" / "v1"; (app / "config").mkdir(parents=True)
    (app / "main.py").write_text("print('new')\n")
    (app / "config" / "config.json").write_text('{"mode":"HOST"}')   # bad: snapshot has config
    (Path(share) / "app" / "latest.txt").write_text("v1\n")
    os.makedirs(os.path.join(client, "config"))
    Path(client, "config", "config.json").write_text('{"mode":"client","share":"Z:"}')

    up, msg = update_from_share(client, share)
    check("code still updates", up and Path(client, "main.py").read_text().strip() == "print('new')", msg)
    check("client's own config.json is NOT clobbered by the snapshot",
          '"mode":"client"' in Path(client, "config", "config.json").read_text())


def test_safe_when_share_empty_or_missing():
    from updater import update_from_share
    client = tempfile.mkdtemp(); share = tempfile.mkdtemp()
    up, msg = update_from_share(client, share)
    check("no published version -> no-op, no crash", not up, msg)
    up2, msg2 = update_from_share(client, "/no/such/share")
    check("missing share -> no-op, no crash", not up2, msg2)


def test_launchers_windowless_and_self_updating():
    root = os.path.dirname(os.path.abspath(__file__))
    for name in ['start_host.vbs', 'start_client.vbs']:
        p = os.path.join(root, 'deploy', name)
        check(f"{name} exists", os.path.exists(p))
        src = open(p, encoding="utf-8").read()
        check(f"{name} runs hidden (window style 0)", ".Run " in src and ", 0, " in src)
        check(f"{name} uses pythonw (no console)", "pythonw" in src)
        check(f"{name} self-updates first (#19)", "updater.py" in src)


def test_runbook_documents_updates_and_windowless():
    rb = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           'docs/HOST_RUNBOOK.md'), encoding='utf-8').read()
    check("runbook documents software updates (#19)", 'Software Updates' in rb and 'updater.py' in rb)
    check("runbook documents windowless operation (#23)", 'Windowless' in rb and 'start_host.vbs' in rb)
    check("runbook explains host-publishes-to-share model",
          'share' in rb.lower() and ('publish' in rb.lower() or 'snapshot' in rb.lower()))


if __name__ == "__main__":
    test_host_publish_then_client_consume()
    test_client_updates_across_two_publishes()
    test_safe_when_share_empty_or_missing()
    test_launchers_windowless_and_self_updating()
    test_runbook_documents_updates_and_windowless()
    print(f"\n{'ALL PASS' if _fail == 0 else str(_fail)+' FAILED'}")
    sys.exit(1 if _fail else 0)
