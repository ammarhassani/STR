# Phase 3b: Operator + Client-UX Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the failover-safe host (Phase 3a) actually operable and usable end-to-end: an operator control plane (`--panel`) to designate/start/monitor/promote the host and run maintenance, the client-side host-down UX (banner + write queueing + auto-drain) wired into the live app, and the deployment artifacts (autostart + runbook) that put it on the org workstation.

**Architecture:** The operator plane is a thin CLI (`--panel`) over a headless-testable `PanelController` that reads the shared heartbeat/queue/backups and drives the Phase-3a primitives (`become_host`, `check_and_restore`, backups, `config.json` host designation). The client senses host liveness from the heartbeat (`HostStatus`), routes writes through a `RemoteGateway` backed by a durable `Outbox`, shows a read-only banner + "queued" toast when the host is down, and auto-drains the outbox (exactly-once by stable id) when a host returns. No new safety core — this layer only consumes the Phase-3a mechanisms.

**Tech Stack:** Python 3.14 (`python3.14 tests_<name>.py`), Flet 0.28.3, SQLite3. Reuses `host/failover.py`, `host/integrity.py`, `host/heartbeat.py`, `services/outbox.py`, `services/remote_gateway.py`, `services/replica_sync.py` from Phases 3a/G1.

## Global Constraints

- Tests run `python3.14 tests_<name>.py` (NO pytest). New logic tests go in `tests_panel.py` (a self-contained harness: `_fail` counter, `check(label, cond, detail="")`, `__main__` calling each test then `sys.exit(1 if _fail else 0)`). There is no `timeout` binary on macOS.
- Flet GUI cannot be driven headlessly in this environment. UI tasks (banner, dialog toast) get a STRUCTURAL test only (imports + builds without error) plus documented manual steps — do not attempt to launch a GUI in a test.
- Never commit `fields.numbers`, `fields.xlsx`, `pbox/`, `sandbox/`.
- Commit trailer: `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`
- Atomic-file rule for any shared-folder write: temp + `os.replace`.
- Do NOT modify the Phase-3a safety core (`host/host_service.py` term/step-down/lease, `host/failover.py`, `services/outbox.py` semantics) except where a task explicitly says so. This layer consumes them.
- The panel is an OPERATOR tool (run by the builder/admin, rarely). It is a CLI by design (fully testable, no GUI dependency); all its logic lives in `PanelController` so a Flet skin could wrap it later without touching logic.

---

### Task 1: Config — stable host id + client outbox dir; `--host` uses the id

**Files:**
- Modify: `config.py`
- Modify: `flet_app/main.py` (the `--host` branch passes `host_id=Config.HOST_ID`)
- Test: `tests_panel.py` (create)

**Interfaces:**
- Produces:
  - `Config.HOST_ID` — a stable id for this PC when it serves as host, persisted in `config.json`. `Config.ensure_host_id() -> str` generates one (`f"{socket.gethostname()}-{uuid4().hex[:8]}"`) and saves it if absent, returns it.
  - `Config.get_client_outbox_dir() -> str` — a LOCAL dir (next to the client replica) where the outbox persists queued writes.
  - `load()`/`save()` round-trip `host_id`.
  - The `--host` launch constructs `HostService(..., host_id=Config.ensure_host_id())`.

- [ ] **Step 1: Write the failing test** — create `tests_panel.py`:

```python
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3.14 tests_panel.py`
Expected: FAIL — `ensure_host_id`/`get_client_outbox_dir` missing.

- [ ] **Step 3: Implement in `config.py`**

Add `import socket` and `import uuid` if not present. Add the attribute + methods (mirror the existing `get_client_replica_path` style):
```python
    HOST_ID = None          # stable id for this PC when it serves as host

    @classmethod
    def ensure_host_id(cls) -> str:
        if not cls.HOST_ID:
            cls.HOST_ID = f"{socket.gethostname()}-{uuid.uuid4().hex[:8]}"
            cls.save()
        return cls.HOST_ID

    @classmethod
    def get_client_outbox_dir(cls) -> str:
        base = os.path.dirname(cls.DATABASE_PATH) if cls.DATABASE_PATH else \
            str(Path(__file__).parent / "database")
        d = os.path.join(base, "outbox")
        os.makedirs(d, exist_ok=True)
        return d
```
Add `host_id` to `load()` (`cls.HOST_ID = config_data.get('host_id')`) and `save()` (`'host_id': cls.HOST_ID`).

- [ ] **Step 4: `--host` uses the id** in `flet_app/main.py` (the `--host` branch):
```python
        bus_dir = Config.get_bus_dir()
        HostService(host_services, app_state.db_manager, QueueTransport(bus_dir),
                    bus_dir, host_id=Config.ensure_host_id()).serve_forever()
```

- [ ] **Step 5: Run to verify it passes**

Run: `python3.14 tests_panel.py`
Expected: PASS all `test_config_host_id` lines.

- [ ] **Step 6: Commit**

```bash
git add config.py flet_app/main.py tests_panel.py
git commit -m "feat(3b): stable Config.HOST_ID + client outbox dir; --host serves under it"
```

---

### Task 2: PanelController — operator logic (headless-tested)

**Files:**
- Create: `panel/__init__.py` (empty), `panel/panel_controller.py`
- Test: `tests_panel.py`

**Interfaces:**
- Produces `panel.panel_controller.PanelController(bus_dir, local_db_path, host_id)` with:
  - `status() -> dict`: `{"heartbeat": <hb-or-None>, "host_online": bool, "host_id": str, "term": int, "queue_pending": int, "queue_processing": int, "replica_version": str|None, "backups": [names newest-first]}`.
  - `designate_host(config) -> (ok, msg)`: sets `config.MODE = "host"`, ensures a host id, `config.save()`.
  - `start_host(spawn=subprocess.Popen) -> (ok, msg)`: launches `python <main.py> --host` detached via the injected `spawn` (injectable so tests don't spawn a real host); returns the pid in the message.
  - `become_host_now(stale_seconds=60, force=False) -> (ok, msg, term)`: wraps `host.failover.become_host(bus_dir, local_db_path, host_id, stale_seconds, force)`.
  - `run_integrity() -> (ok, msg)`: wraps `host.integrity.check_and_restore(local_db_path, backups_dir)`.
  - `manual_backup() -> (ok, msg)`: atomic DELETE-mode backup to `backups/fiu_<ms>.db` (same pattern as host `_maybe_backup`).
  - `list_backups() -> [names newest-first]`.
  - `restore_backup(name) -> (ok, msg)`: atomically copy `backups/<name>` over `local_db_path` (clean `-wal`/`-shm`); refuse if name not found.

- [ ] **Step 1: Write the failing test** — add to `tests_panel.py`, register in `__main__`:

```python
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3.14 tests_panel.py`
Expected: FAIL — `panel.panel_controller` missing.

- [ ] **Step 3: Implement `panel/panel_controller.py`**

```python
"""Operator-plane logic (UI-free, fully testable). Reads the shared heartbeat/
queue/backups and drives the Phase-3a primitives."""
import os
import sys
import glob
import uuid
import shutil
import sqlite3
import subprocess

from host.heartbeat import read_heartbeat, is_stale
from host.integrity import check_and_restore
from host.failover import become_host


class PanelController:
    def __init__(self, bus_dir, local_db_path, host_id):
        self.bus = bus_dir
        self.db_path = local_db_path
        self.host_id = host_id
        self.backups_dir = os.path.join(bus_dir, "backups")
        os.makedirs(self.backups_dir, exist_ok=True)

    def status(self):
        hb = read_heartbeat(self.bus)
        pend = os.path.join(self.bus, "queue", "pending")
        proc = os.path.join(self.bus, "queue", "processing")
        ver_path = os.path.join(self.bus, "replica", "version.txt")
        version = None
        try:
            with open(ver_path) as f:
                version = f.read().strip()
        except OSError:
            pass
        return {
            "heartbeat": hb,
            "host_online": not is_stale(hb),
            "host_id": hb.get("host_id") if hb else None,
            "term": hb.get("term", 0) if hb else 0,
            "queue_pending": len([n for n in os.listdir(pend) if n.endswith(".json")]) if os.path.isdir(pend) else 0,
            "queue_processing": len([n for n in os.listdir(proc) if n.endswith(".json")]) if os.path.isdir(proc) else 0,
            "replica_version": version,
            "backups": self.list_backups(),
        }

    def designate_host(self, config):
        config.MODE = "host"
        config.ensure_host_id()
        config.save()
        return True, f"This PC designated as host (mode=host, id={config.HOST_ID})"

    def start_host(self, spawn=subprocess.Popen):
        main_py = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "flet_app", "main.py")
        cmd = [sys.executable, main_py, "--host"]
        try:
            p = spawn(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True, f"host started (pid {getattr(p, 'pid', '?')})"
        except Exception as e:
            return False, f"could not start host: {e}"

    def become_host_now(self, stale_seconds=60, force=False):
        return become_host(self.bus, self.db_path, self.host_id, stale_seconds, force)

    def run_integrity(self):
        return check_and_restore(self.db_path, self.backups_dir)

    def manual_backup(self):
        try:
            import time
            dest = os.path.join(self.backups_dir, f"fiu_{int(time.time() * 1000)}.db")
            tmp = os.path.join(self.bus, ".tmp", uuid.uuid4().hex + ".bak")
            src = sqlite3.connect(self.db_path); dst = sqlite3.connect(tmp)
            try:
                with dst:
                    src.backup(dst)
                dst.execute("PRAGMA journal_mode=DELETE")
            finally:
                dst.close(); src.close()
            os.replace(tmp, dest)
            return True, f"backup written: {os.path.basename(dest)}"
        except Exception as e:
            return False, f"backup failed: {e}"

    def list_backups(self):
        files = sorted(glob.glob(os.path.join(self.backups_dir, "*.db")), key=os.path.getmtime, reverse=True)
        return [os.path.basename(f) for f in files]

    def restore_backup(self, name):
        src = os.path.join(self.backups_dir, name)
        if not os.path.exists(src):
            return False, f"backup not found: {name}"
        tmp = self.db_path + ".restore-" + uuid.uuid4().hex
        shutil.copyfile(src, tmp)
        os.replace(tmp, self.db_path)
        for sfx in ("-wal", "-shm"):
            try:
                os.remove(self.db_path + sfx)
            except OSError:
                pass
        return True, f"restored from {name}"
```

- [ ] **Step 4: Run to verify it passes**

Run: `python3.14 tests_panel.py`
Expected: PASS all `test_panel_controller` lines.

- [ ] **Step 5: Commit**

```bash
git add panel/__init__.py panel/panel_controller.py tests_panel.py
git commit -m "feat(3b): PanelController — status, designate/start host, become-host, integrity, backup/restore"
```

---

### Task 3: `--panel` CLI

**Files:**
- Create: `panel/control_panel.py`
- Modify: `flet_app/main.py` (add a `--panel` branch)
- Test: `tests_panel.py` (dispatch smoke, no real menu loop)

**Interfaces:**
- Produces:
  - `panel.control_panel.build_controller() -> PanelController` — builds a controller from `Config` (loads config, resolves bus dir, local db/replica path, host id).
  - `panel.control_panel.run_action(controller, choice, config) -> str` — pure dispatch for one menu choice (`"status"`, `"designate"`, `"start"`, `"become"`, `"integrity"`, `"backup"`, `"list"`, `"restore:<name>"`, `"quit"`) returning a printable string. The interactive `main()` loop reads stdin and calls `run_action` — the loop itself is thin and not unit-tested.

- [ ] **Step 1: Write the failing test** — add to `tests_panel.py`, register in `__main__`:

```python
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3.14 tests_panel.py`
Expected: FAIL — `panel.control_panel` missing.

- [ ] **Step 3: Implement `panel/control_panel.py`**

```python
"""`--panel` operator CLI. Thin text menu over PanelController; all logic lives
in the controller so this file stays trivial + a Flet skin could replace it."""
import os
from config import Config
from panel.panel_controller import PanelController


def build_controller():
    Config.load()
    bus = Config.get_bus_dir()
    # host/panel operate on the real local DB; a client-only PC uses its replica copy
    local_db = Config.DATABASE_PATH or Config.get_client_replica_path()
    return PanelController(bus, local_db, Config.ensure_host_id())


def _fmt_status(st):
    hb = st["heartbeat"]
    who = f"{st['host_id']} (term {st['term']})" if hb else "— none —"
    online = "ONLINE" if st["host_online"] else "OFFLINE/STALE"
    return (f"Host: {online}  {who}\n"
            f"Queue: {st['queue_pending']} pending, {st['queue_processing']} processing\n"
            f"Replica version: {st['replica_version']}\n"
            f"Backups: {len(st['backups'])} (newest: {st['backups'][0] if st['backups'] else '—'})")


def run_action(controller, choice, config):
    if choice == "status":
        return _fmt_status(controller.status())
    if choice == "designate":
        return controller.designate_host(config)[1]
    if choice == "start":
        return controller.start_host()[1]
    if choice == "become":
        ok, msg, term = controller.become_host_now()
        return msg
    if choice == "integrity":
        return controller.run_integrity()[1]
    if choice == "backup":
        return controller.manual_backup()[1]
    if choice == "list":
        b = controller.list_backups()
        return "\n".join(b) if b else "(no backups)"
    if choice.startswith("restore:"):
        return controller.restore_backup(choice.split(":", 1)[1])[1]
    return f"unknown choice: {choice}"


MENU = """
STR Host Control Panel
  1) status        2) designate this PC as host   3) start host (this PC)
  4) become host now (promote)   5) integrity check   6) manual backup
  7) list backups  8) restore backup   q) quit
> """


def main():
    controller = build_controller()
    actions = {"1": "status", "2": "designate", "3": "start", "4": "become",
               "5": "integrity", "6": "backup", "7": "list"}
    while True:
        choice = input(MENU).strip().lower()
        if choice in ("q", "quit"):
            break
        if choice == "8":
            name = input("backup filename to restore: ").strip()
            print(run_action(controller, f"restore:{name}", Config))
        else:
            print(run_action(controller, actions.get(choice, choice), Config))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Add `--panel` to `flet_app/main.py`** `__main__`, before `ft.app(target=main)`:
```python
    if "--panel" in sys.argv:
        from panel.control_panel import main as panel_main
        panel_main()
        sys.exit(0)
```

- [ ] **Step 5: Run to verify it passes**

Run: `python3.14 tests_panel.py`
Expected: PASS all `test_panel_cli_dispatch` lines.

- [ ] **Step 6: Commit**

```bash
git add panel/control_panel.py flet_app/main.py tests_panel.py
git commit -m "feat(3b): --panel operator CLI over PanelController"
```

---

### Task 4: Client host-status sensing + outbox-backed gateway + auto-drain

**Files:**
- Create: `services/host_status.py`
- Modify: `flet_app/app_state.py` (client gateway gets an `Outbox`; expose `host_status`; add `drain_outbox()`)
- Test: `tests_panel.py`

**Interfaces:**
- Produces:
  - `services.host_status.HostStatus(bus_dir, stale_seconds=60)` with `.online() -> bool` (fresh heartbeat) and `.info() -> dict|None` (raw heartbeat).
  - `AppState` in client mode: builds `RemoteGateway(transport, outbox=Outbox(Config.get_client_outbox_dir()))`, sets `self.host_status = HostStatus(bus_dir)`, and `self.pending_writes() -> int` (outbox depth).
  - `AppState.drain_outbox() -> (sent, remaining)` — calls `self._gateway.drain()` if a gateway+outbox exist, else `(0,0)`. Safe to call when host offline (drain no-ops/returns quickly).

- [ ] **Step 1: Write the failing test** — add to `tests_panel.py`, register in `__main__`:

```python
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3.14 tests_panel.py`
Expected: FAIL — `services.host_status` missing.

- [ ] **Step 3: Create `services/host_status.py`**

```python
"""Client-side host liveness sensor (reads the shared heartbeat)."""
from host.heartbeat import read_heartbeat, is_stale


class HostStatus:
    def __init__(self, bus_dir, stale_seconds=60):
        self.bus = bus_dir
        self.stale_seconds = stale_seconds

    def info(self):
        return read_heartbeat(self.bus)

    def online(self):
        return not is_stale(read_heartbeat(self.bus), self.stale_seconds)
```

- [ ] **Step 4: Wire the client** in `flet_app/app_state.py`. In the `mode == "client" and bus_dir` block, build the gateway WITH an outbox and expose status/drain:
```python
            if mode == "client" and bus_dir:
                from services.queue_transport import QueueTransport
                from services.remote_gateway import RemoteGateway, RemoteServiceProxy
                from services.outbox import Outbox
                from services.host_status import HostStatus
                from config import Config
                gw = RemoteGateway(QueueTransport(bus_dir), outbox=Outbox(Config.get_client_outbox_dir()))
                self._gateway = gw
                self.host_status = HostStatus(bus_dir)
                for attr in ("auth_service", "report_service", "approval_service",
                             "version_service", "report_number_service", "dropdown_service",
                             "validation_service", "settings_service"):
                    local = getattr(self, attr)
                    setattr(self, attr, RemoteServiceProxy(attr, local, gw))
```
Add methods on `AppState`:
```python
    def pending_writes(self) -> int:
        gw = self._gateway
        if gw is not None and getattr(gw, "outbox", None) is not None:
            return len(gw.outbox.pending())
        return 0

    def drain_outbox(self):
        gw = self._gateway
        if gw is not None and getattr(gw, "outbox", None) is not None:
            return gw.drain()
        return (0, 0)
```
Add a default `host_status: Any = None` field to the `AppState` dataclass (near the other service fields).

- [ ] **Step 5: Run to verify it passes**

Run: `python3.14 tests_panel.py && python3.14 tests_g1.py`
Expected: failover/panel PASS; g1 still ALL PASS (client wiring change must not break g1's client roundtrip).

- [ ] **Step 6: Commit**

```bash
git add services/host_status.py flet_app/app_state.py tests_panel.py
git commit -m "feat(3b): client host-status sensor + outbox-backed gateway + drain_outbox"
```

---

### Task 5: Client host-down banner + "queued" toast + drain-on-refresh

**Files:**
- Create: `flet_app/components/host_banner.py`
- Modify: `flet_app/main.py` (mount the banner; drain on the refresher tick)
- Modify: `flet_app/dialogs/report_dialog.py` (catch `HostOfflineError` → "queued" toast instead of an error)
- Test: `tests_panel.py` (structural: the banner module imports + builds a control; no GUI)

**Interfaces:**
- Consumes: `app_state.host_status`, `app_state.pending_writes()`, `app_state.drain_outbox()`, `services.remote_gateway.HostOfflineError`.
- Produces:
  - `flet_app.components.host_banner.build_host_banner(app_state) -> ft.Control` — a container that, when refreshed, shows "Host offline — read-only. New entries are queued and will sync when the host returns (N pending)" iff `not app_state.host_status.online()`, else hidden. Exposes a `refresh()` the caller can call on a timer.
  - The client's `ReplicaRefresher` `on_update` (in `main.py`) additionally calls `app_state.drain_outbox()` and refreshes the banner — so queued writes drain when the host republishes (which it does right after processing).

- [ ] **Step 1: Write the failing structural test** — add to `tests_panel.py`, register in `__main__`:

```python
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3.14 tests_panel.py`
Expected: FAIL — `flet_app.components.host_banner` missing.

- [ ] **Step 3: Create `flet_app/components/host_banner.py`**

```python
"""Host-down banner: read-only + queued-writes notice, shown when the client
cannot see a live host. Hidden when the host is online."""
import flet as ft


def build_host_banner(app_state):
    text = ft.Text("", size=13, color=ft.Colors.WHITE)
    container = ft.Container(
        content=ft.Row([ft.Icon(ft.Icons.CLOUD_OFF, color=ft.Colors.WHITE, size=18), text], spacing=8),
        bgcolor=ft.Colors.ORANGE_800, padding=ft.padding.symmetric(8, 12),
        visible=False,
    )

    def refresh():
        online = True
        try:
            online = app_state.host_status.online() if app_state.host_status else True
        except Exception:
            online = True
        if online:
            container.visible = False
        else:
            n = app_state.pending_writes()
            text.value = (f"Host offline — read-only. New entries are queued and will "
                          f"sync when the host returns ({n} pending).")
            container.visible = True

    container.refresh = refresh
    refresh()
    return container
```

- [ ] **Step 4: Mount + drain** in `flet_app/main.py`. Where the client `ReplicaRefresher` is started (client branch of `_initialize_services`), change `on_update` to also drain + refresh the banner:
```python
                def _on_replica_update():
                    try:
                        app_state.drain_outbox()
                    except Exception:
                        pass
                    if getattr(self, "_host_banner", None) is not None:
                        self._host_banner.refresh()
                        try:
                            self.page.update()
                        except Exception:
                            pass
                if not getattr(self, "_refresher", None):
                    self._refresher = ReplicaRefresher(bus_dir, local_replica, poll=2.0, on_update=_on_replica_update)
                    self._refresher.start()
```
In `_build_main_layout` (or wherever the top-level content column is assembled), build the banner and keep a handle, inserting it above the content area:
```python
        from flet_app.components.host_banner import build_host_banner
        self._host_banner = build_host_banner(app_state)
```
Mount `self._host_banner` at the top of the main layout column (above the content area). (Read the current layout structure and insert it as the first child of the outermost content column; guard with `if app_state.host_status` so local/host-less mode never shows it.)

- [ ] **Step 5: "Queued" toast** in `flet_app/dialogs/report_dialog.py`. Where the save handler calls the (proxied) create/update and handles exceptions, catch `HostOfflineError` first and show a friendly toast instead of an error:
```python
        from services.remote_gateway import HostOfflineError
        try:
            ... existing save call ...
        except HostOfflineError:
            show_success(page, "Host offline — your entry is queued and will sync when the host returns.")
            # close the dialog as if saved; the outbox will apply it exactly once
            close_dialog()
            return
```
(Place the `except HostOfflineError` BEFORE any broad `except Exception`. Read the current save handler to wire it into the real control flow.)

- [ ] **Step 6: Run structural test + regressions**

Run: `python3.14 tests_panel.py && python3.14 tests_g1.py && python3.14 tests_failover.py`
Expected: panel PASS (incl. banner builds); g1 + failover unaffected.

- [ ] **Step 7: Commit**

```bash
git add flet_app/components/host_banner.py flet_app/main.py flet_app/dialogs/report_dialog.py tests_panel.py
git commit -m "feat(3b): host-down banner + queued-write toast + drain on replica refresh"
```

---

### Task 6: Autostart script + operator runbook

**Files:**
- Create: `deploy/start_host.bat`, `deploy/start_panel.bat`
- Create: `docs/HOST_RUNBOOK.md`
- Test: `tests_panel.py` (presence/shape smoke)

**Interfaces:**
- Produces: a Windows launcher for the host (for the Startup folder), a launcher for the panel, and the operator runbook covering setup, host designation, daily/weekly checks, failover, restore, and the known limits.

- [ ] **Step 1: Write the failing smoke test** — add to `tests_panel.py`, register in `__main__`:

```python
def test_deploy_artifacts_exist():
    root = os.path.dirname(os.path.abspath(__file__))
    for rel in ("deploy/start_host.bat", "deploy/start_panel.bat", "docs/HOST_RUNBOOK.md"):
        check(f"{rel} exists", os.path.exists(os.path.join(root, rel)), rel)
    runbook = open(os.path.join(root, "docs/HOST_RUNBOOK.md")).read().lower()
    for term in ("become host", "restore", "startup folder", "integrity", "session"):
        check(f"runbook covers '{term}'", term in runbook)
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3.14 tests_panel.py`
Expected: FAIL — artifacts missing.

- [ ] **Step 3: Create `deploy/start_host.bat`**

```bat
@echo off
REM Launch the STR host on this PC (designated host workstation).
REM Put a shortcut to this file in the Startup folder (Win+R -> shell:startup)
REM so the host starts on login. Screen-lock keeps it running; after a cold
REM reboot the operator must log in once (Startup runs at login, not boot).
cd /d "%~dp0.."
python "flet_app\main.py" --host
```

- [ ] **Step 4: Create `deploy/start_panel.bat`**

```bat
@echo off
REM Open the STR operator control panel (status, designate host, failover, backups).
cd /d "%~dp0.."
python "flet_app\main.py" --panel
```

- [ ] **Step 5: Create `docs/HOST_RUNBOOK.md`** — a complete operator runbook. It MUST cover (each as a real section with steps, not placeholders):
  - **What runs where:** one designated host workstation runs `--host` (owns the DB on local disk, publishes the replica + heartbeat to the share); every other PC runs the normal app in client mode (reads the replica, sends writes through the queue).
  - **Initial setup:** on the host PC, run the setup wizard → choose Host, set the shared-folder path; run `deploy/start_host.bat`; put a shortcut to it in the Startup folder (`shell:startup`) so it relaunches on login. On each client PC, run the wizard → choose Client, set the same shared-folder path.
  - **Daily/weekly checks (via `--panel`):** open the panel, check Host ONLINE + queue near 0; run a manual backup weekly; run an integrity check monthly.
  - **Failover ("Become Host") — when the host PC is down:** on the designated BACKUP PC, open `--panel` → confirm Host shows OFFLINE/STALE → choose "become host now" → then "start host (this PC)". The old host, if it wakes, sees the newer term and steps down automatically. **Only ONE operator promotes ONE backup** (simultaneous promotions are unsupported — see Limits).
  - **Restore from backup:** in `--panel` → list backups → restore the newest good one (used automatically on startup if integrity fails; manual restore for a bad-data rollback).
  - **Session timeout:** host expires idle logins after 30 minutes (R3); users re-login — queued writes are unaffected.
  - **Known limits:** unattended-after-cold-reboot needs one Windows login (Startup runs at login); simultaneous promotion of two backups is out of the operational model (bounded, self-reconciling, never corrupting — but don't do it); the host PC must have the app + share access.

- [ ] **Step 6: Run to verify it passes**

Run: `python3.14 tests_panel.py`
Expected: PASS all `test_deploy_artifacts_exist` lines.

- [ ] **Step 7: Commit**

```bash
git add deploy/start_host.bat deploy/start_panel.bat docs/HOST_RUNBOOK.md tests_panel.py
git commit -m "docs(3b): host autostart launchers + operator runbook"
```

---

## Deferred (non-blocking, documented)

- **One-txn exactly-once collapse**: fold the service write and the `applied_commands` INSERT into one transaction (needs threading a connection through service methods — invasive). Today's fallback (DB uniqueness + idempotent-by-id resubmit) covers the common paths; the residual is a host crash exactly between the service commit and the ledger INSERT. Low-volume, rare.
- **Outbox per-attempt response correlation**: give each submit attempt a distinct response filename so `drain()` never reads a stale response (today it self-heals via the ledger re-emit on the next drain). Wire when higher write concurrency warrants it.
- **Flet-skinned control panel**: the operator logic is fully in `PanelController`; a Flet view could replace the CLI if operators prefer a GUI.

## Self-Review

- **Spec coverage (§3.5a + deferred lists):** panel setup/designate/monitor/failover/maintenance (Tasks 2,3) ✓; host designation via config (Task 1,2) ✓; client host-down banner + queueing + drain (Tasks 4,5) ✓; autostart + runbook (Task 6) ✓. Host step-down→relaunch-as-client is N/A (the UI is always a client; the host runs headless via `--host` and exits on step-down — the operator/panel restarts or promotes elsewhere; covered in the runbook).
- **Placeholder scan:** all logic tasks carry complete code; UI/doc tasks carry complete code + a concrete content checklist for the runbook.
- **Type consistency:** `PanelController` methods return the documented tuples; `status()` keys match the CLI formatter + tests; `HostStatus.online()->bool`; `AppState.drain_outbox()->(sent,remaining)`, `pending_writes()->int`; `build_host_banner(app_state)->ft.Control` with a `.refresh()`.
- **Safety:** no change to the Phase-3a safety core; the panel/client only consume `become_host`, `check_and_restore`, `drain`, heartbeat. Backups/restore use atomic temp+replace + DELETE-mode + sidecar cleanup.
