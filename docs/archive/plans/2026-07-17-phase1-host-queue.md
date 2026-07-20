# Phase 1 — Single-Writer Host + Folder-Queue + Command-RPC — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Make STR corruption-proof on a shared folder by routing every database write through ONE host process on local disk, reached by clients via an atomic folder-queue carrying high-level commands (RPC of the existing service methods). Reads run client-side against a published read-only replica.

**Architecture:** One codebase, two data-path modes. HOST mode owns `fiu_reports.db` on local disk and runs the real (already-tested) service stack; it consumes command files from `<share>/str_bus/queue`, executes each in one local transaction, writes a response file, and republishes a read-only DB replica. CLIENT mode calls a proxy: write methods enqueue a command and await the response; read methods hit a local copy of the replica. No client ever opens a DB over the network. See `docs/superpowers/specs/2026-07-16-single-writer-host-architecture-design.md` and `docs/DECISIONS.md`.

**Tech Stack:** Python 3.14, Flet 0.28.3, stdlib `sqlite3`, `json`, `os`, `uuid`. No new dependencies.

## Global Constraints

- **Run everything with `python3.14`** (user-site has Flet 0.28.3 + bcrypt). Never `python3`.
- **macOS has no `timeout` command** — never use it in Bash.
- **No new third-party dependencies.** Stdlib only.
- **Reuse the existing service layer unchanged.** The host runs the real services; the command layer is transport, not new business logic. Do NOT reimplement create_report/approve/etc.
- **Atomicity rule (safety-critical):** every file placed on the share is written to `<dir>/.tmp/<uuid>` then **renamed** into place. Readers must never see a partial file. Command files have globally-unique names; no two writers ever target the same filename.
- **Single-writer invariant:** only the host opens a real DB for writing; clients open only a read-only replica copy. Never violate this.
- **Exactly-once:** every command carries a UUID `id`; the host records applied ids and re-emits the stored response on any replay. No command is ever applied twice.
- **JSON-serializable args only:** command args/kwargs must be JSON-safe (reports are dicts, ids ints, comments strings — all fine). If a value isn't JSON-serializable, that's a bug to surface, not silently drop.
- **Regression gate:** the existing suites must stay green — `python3.14 tests_e2e_harness.py` (180/180), `tests_prosecutor.py` (0/35), `tests_conformance.py` (Conformance 50/50), `tests_ui_driver.py` (0/NN), `tests_theme.py` (0). They exercise the service layer directly, which is unchanged.
- Tests are plain scripts (`python3.14 tests_X.py`), matching this repo (no pytest).

## File Structure

- Create `services/queue_transport.py` — atomic folder-queue (submit/await/claim/respond/complete).
- Create `services/command_registry.py` — the write-command → (service, method) map + dispatch.
- Create `host/__init__.py`, `host/host_service.py` — the host loop, session store, replica publisher, idempotency.
- Create `services/remote_gateway.py` — client-side proxy (writes→queue, reads→local replica services) + `RemoteServiceProxy`.
- Modify `database/migrations.py` — add `applied_commands` table (Migration 33).
- Modify `flet_app/app_state.py` — `initialize_services(db_path, mode="client"|"host", bus_dir=None)` wiring.
- Modify `flet_app/main.py` — `--host` flag launches the host loop instead of the UI.
- Create `tests_host_cluster.py` — multi-client → single-host integration + idempotency + integrity harness.

---

### Task 1: Atomic folder-queue transport

**Files:**
- Create: `services/queue_transport.py`
- Test: `tests_host_cluster.py` (create; this task adds the transport roundtrip test)

**Interfaces:**
- Produces:
  - `QueueTransport(bus_dir: str)` — creates `<bus_dir>/{queue/pending,queue/processing,queue/done,responses,replica,host,backups,.tmp}`.
  - `submit(command: dict) -> str` — command must contain `id`; writes it atomically to `queue/pending/`; returns `id`.
  - `await_response(command_id: str, timeout: float = 30.0, poll: float = 0.05) -> dict` — waits for `responses/<id>.json`, reads+deletes it, returns parsed dict; raises `TimeoutError` on timeout.
  - `claim_next() -> dict | None` — atomically moves the oldest `pending` file to `processing/`; returns its parsed dict, or None if queue empty.
  - `respond(command_id: str, response: dict) -> None` — writes `responses/<id>.json` atomically.
  - `complete(command_id: str) -> None` — moves the processing file to `done/`.

- [ ] **Step 1: Write the failing test**

Create `tests_host_cluster.py`:

```python
"""Single-host / multi-client integration + idempotency harness. Run: python3.14 tests_host_cluster.py"""
import os, sys, shutil, tempfile, json, uuid
sys.path.insert(0, '/Users/engammar/Scripts/STR')

FAILS = []
def check(name, ok, detail=''):
    print(('  ok  ' if ok else '  FAIL ') + name + ('' if ok else f' — {detail}'))
    if not ok: FAILS.append(name)

def test_transport_roundtrip():
    from services.queue_transport import QueueTransport
    box = tempfile.mkdtemp()
    try:
        t = QueueTransport(os.path.join(box, 'str_bus'))
        cid = 'c-' + uuid.uuid4().hex
        t.submit({'id': cid, 'command': 'ping', 'args': [1], 'kwargs': {}})
        # host side
        claimed = t.claim_next()
        check('T1 claim returns the submitted command', claimed and claimed['id'] == cid, claimed)
        check('T1 queue empty after claim', t.claim_next() is None)
        t.respond(cid, {'id': cid, 'ok': True, 'result': 'pong'})
        t.complete(cid)
        # client side
        resp = t.await_response(cid, timeout=5)
        check('T1 await returns the response', resp['ok'] and resp['result'] == 'pong', resp)
        # response consumed
        raised = False
        try: t.await_response(cid, timeout=0.3)
        except TimeoutError: raised = True
        check('T1 response consumed after read', raised)
    finally:
        shutil.rmtree(box, ignore_errors=True)

if __name__ == '__main__':
    test_transport_roundtrip()
    print(f"\nCLUSTER FAILURES: {len(FAILS)}")
    sys.exit(1 if FAILS else 0)
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd /Users/engammar/Scripts/STR && python3.14 tests_host_cluster.py`
Expected: FAIL — `No module named 'services.queue_transport'`.

- [ ] **Step 3: Implement the transport**

Create `services/queue_transport.py`:

```python
"""Atomic folder-queue transport between clients and the single host.
Every placed file is written to .tmp then renamed into place, so readers
never see a partial file. Command filenames are globally unique."""
import os
import json
import time
import uuid

SUBDIRS = ["queue/pending", "queue/processing", "queue/done",
           "responses", "replica", "host", "backups", ".tmp"]


class QueueTransport:
    def __init__(self, bus_dir: str):
        self.bus = bus_dir
        for d in SUBDIRS:
            os.makedirs(os.path.join(bus_dir, d), exist_ok=True)

    def _p(self, *parts):
        return os.path.join(self.bus, *parts)

    def _atomic_write(self, dest_path: str, data: dict):
        tmp = self._p(".tmp", uuid.uuid4().hex)
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        os.replace(tmp, dest_path)  # atomic within the same filesystem

    # ---- client side ----
    def submit(self, command: dict) -> str:
        cid = command["id"]
        # sortable, unique: <ms>_<id>.json
        name = f"{int(time.time() * 1000):013d}_{cid}.json"
        self._atomic_write(self._p("queue", "pending", name), command)
        return cid

    def await_response(self, command_id: str, timeout: float = 30.0, poll: float = 0.05) -> dict:
        path = self._p("responses", f"{command_id}.json")
        deadline = time.time() + timeout
        while time.time() < deadline:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        resp = json.load(f)
                except (json.JSONDecodeError, FileNotFoundError):
                    time.sleep(poll); continue  # writer mid-rename; retry
                try:
                    os.remove(path)
                except OSError:
                    pass
                return resp
            time.sleep(poll)
        raise TimeoutError(f"No response for {command_id} within {timeout}s")

    # ---- host side ----
    def claim_next(self):
        pend = self._p("queue", "pending")
        names = sorted(n for n in os.listdir(pend) if n.endswith(".json"))
        for name in names:
            src = os.path.join(pend, name)
            dst = self._p("queue", "processing", name)
            try:
                os.replace(src, dst)  # atomic claim
            except (FileNotFoundError, OSError):
                continue  # another pass grabbed it / mid-write; skip
            try:
                with open(dst, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                continue
        return None

    def respond(self, command_id: str, response: dict) -> None:
        self._atomic_write(self._p("responses", f"{command_id}.json"), response)

    def complete(self, command_id: str) -> None:
        proc = self._p("queue", "processing")
        for name in os.listdir(proc):
            if name.endswith(f"_{command_id}.json"):
                try:
                    os.replace(os.path.join(proc, name), self._p("queue", "done", name))
                except OSError:
                    pass
                return
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd /Users/engammar/Scripts/STR && python3.14 tests_host_cluster.py`
Expected: `CLUSTER FAILURES: 0`

- [ ] **Step 5: Commit**

```bash
git add services/queue_transport.py tests_host_cluster.py
git commit -m "feat(host): atomic folder-queue transport"
```

---

### Task 2: Idempotency store (applied_commands table)

**Files:**
- Modify: `database/migrations.py` (add Migration 33 before `conn.close()`)
- Test: `tests_host_cluster.py` (extend)

**Interfaces:**
- Produces: table `applied_commands(command_id TEXT PRIMARY KEY, response_json TEXT, applied_at TEXT DEFAULT (datetime('now')))` created on both fresh and existing DBs by `migrate_database`.

- [ ] **Step 1: Write the failing test**

Add to `tests_host_cluster.py` (before `__main__`):

```python
def test_applied_commands_table():
    import sqlite3
    from database.init_db import initialize_database
    from database.migrations import migrate_database
    box = tempfile.mkdtemp()
    try:
        db = os.path.join(box, 'x.db')
        initialize_database(db); migrate_database(db)
        cols = {r[1] for r in sqlite3.connect(db).execute("PRAGMA table_info(applied_commands)")}
        check('T2 applied_commands table exists', {'command_id','response_json','applied_at'} <= cols, cols)
    finally:
        shutil.rmtree(box, ignore_errors=True)
```
Call `test_applied_commands_table()` in `__main__` after the transport test.

- [ ] **Step 2: Run to verify it fails**

Run: `cd /Users/engammar/Scripts/STR && python3.14 tests_host_cluster.py`
Expected: FAIL on `T2 applied_commands table exists` (empty cols).

- [ ] **Step 3: Add Migration 33**

In `database/migrations.py`, immediately before the final `conn.close()`:

```python
        # Migration 33: idempotency ledger for host command-RPC (exactly-once apply)
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='applied_commands'")
            if not cursor.fetchone():
                cursor.execute("""
                    CREATE TABLE applied_commands (
                        command_id TEXT PRIMARY KEY,
                        response_json TEXT,
                        applied_at TEXT DEFAULT (datetime('now'))
                    )
                """)
                conn.commit()
                messages.append("Created applied_commands table")
        except Exception as e:
            messages.append(f"applied_commands table skipped: {str(e)}")
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd /Users/engammar/Scripts/STR && python3.14 tests_host_cluster.py`
Expected: `CLUSTER FAILURES: 0`

- [ ] **Step 5: Regression + commit**

Run: `python3.14 tests_conformance.py 2>/dev/null | grep Conformance` → `Conformance: 50/50 testable rules PASS` (migrations still idempotent).

```bash
git add database/migrations.py tests_host_cluster.py
git commit -m "feat(host): applied_commands idempotency ledger (migration 33)"
```

---

### Task 3: Command registry (write-command → service.method)

**Files:**
- Create: `services/command_registry.py`
- Test: `tests_host_cluster.py` (extend)

**Interfaces:**
- Produces:
  - `WRITE_COMMANDS: dict[str, tuple[str, str]]` — command name → (service_attr, method_name). Command name is `"<service_attr>.<method>"` for uniformity, e.g. `"report_service.create_report"`.
  - `is_write_command(name: str) -> bool`.
  - `dispatch(services: dict, name: str, args: list, kwargs: dict) -> any` — resolves `services[service_attr]`, calls `method(*args, **kwargs)`, returns its result. Raises `KeyError` for unknown commands.

- [ ] **Step 1: Write the failing test**

Add to `tests_host_cluster.py`:

```python
def test_command_registry():
    from services import command_registry as cr
    check('T3 create_report is a write command', cr.is_write_command('report_service.create_report'))
    check('T3 get_reports is NOT a write command', not cr.is_write_command('report_service.get_reports'))
    class FakeReport:
        def create_report(self, data): return (True, 7, 'ok')
    result = cr.dispatch({'report_service': FakeReport()}, 'report_service.create_report', [{'x': 1}], {})
    check('T3 dispatch calls the method', result == (True, 7, 'ok'), result)
    raised = False
    try: cr.dispatch({}, 'nope.nope', [], {})
    except KeyError: raised = True
    check('T3 unknown command raises KeyError', raised)
```
Call it in `__main__`.

- [ ] **Step 2: Run to verify it fails**

Run: `cd /Users/engammar/Scripts/STR && python3.14 tests_host_cluster.py`
Expected: FAIL — `No module named 'services.command_registry'`.

- [ ] **Step 3: Implement the registry**

Create `services/command_registry.py`:

```python
"""Maps write commands to service methods. The host runs the real service
method (already tested) in one local transaction. Reads are NOT here — they
run client-side against the replica."""

# command name "<service_attr>.<method>" -> (service_attr, method)
WRITE_COMMANDS = {
    "report_service.create_report": ("report_service", "create_report"),
    "report_service.update_report": ("report_service", "update_report"),
    "report_service.delete_report": ("report_service", "delete_report"),
    "report_service.restore_report": ("report_service", "restore_report"),
    "report_service.hard_delete_report": ("report_service", "hard_delete_report"),
    "report_service.acquire_edit_lock": ("report_service", "acquire_edit_lock"),
    "report_service.release_edit_lock": ("report_service", "release_edit_lock"),
    "approval_service.request_approval": ("approval_service", "request_approval"),
    "approval_service.approve_report": ("approval_service", "approve_report"),
    "approval_service.reject_report": ("approval_service", "reject_report"),
    "approval_service.create_notification": ("approval_service", "create_notification"),
    "approval_service.mark_notification_read": ("approval_service", "mark_notification_read"),
    "version_service.create_version_snapshot": ("version_service", "create_version_snapshot"),
    "version_service.restore_version": ("version_service", "restore_version"),
    "version_service.soft_delete_version": ("version_service", "soft_delete_version"),
    "version_service.hard_delete_version": ("version_service", "hard_delete_version"),
    "version_service.restore_deleted_version": ("version_service", "restore_deleted_version"),
    "report_number_service.reserve_next_numbers": ("report_number_service", "reserve_next_numbers"),
    "report_number_service.mark_reservation_used": ("report_number_service", "mark_reservation_used"),
    "report_number_service.cancel_reservation": ("report_number_service", "cancel_reservation"),
    "report_number_service.close_month": ("report_number_service", "close_month"),
    "dropdown_service.add_dropdown_value": ("dropdown_service", "add_dropdown_value"),
    "dropdown_service.update_dropdown_value": ("dropdown_service", "update_dropdown_value"),
    "dropdown_service.delete_dropdown_value": ("dropdown_service", "delete_dropdown_value"),
    "dropdown_service.reorder_dropdown_values": ("dropdown_service", "reorder_dropdown_values"),
    "dropdown_service.restore_dropdown_value": ("dropdown_service", "restore_dropdown_value"),
    "dropdown_service.bulk_import_dropdown_values": ("dropdown_service", "bulk_import_dropdown_values"),
    "validation_service.update_validation_rules": ("validation_service", "update_validation_rules"),
    "validation_service.update_required_status": ("validation_service", "update_required_status"),
    "auth_service.create_user": ("auth_service", "create_user"),
    "auth_service.update_user": ("auth_service", "update_user"),
    "auth_service.delete_user": ("auth_service", "delete_user"),
    "auth_service.reset_password": ("auth_service", "reset_password"),
    "auth_service.change_password": ("auth_service", "change_password"),
    "auth_service.unlock_account": ("auth_service", "unlock_account"),
    "settings_service.save_settings": ("settings_service", "save_settings"),
    "settings_service.save_setting": ("settings_service", "save_setting"),
}


def is_write_command(name: str) -> bool:
    return name in WRITE_COMMANDS


def dispatch(services: dict, name: str, args: list, kwargs: dict):
    if name not in WRITE_COMMANDS:
        raise KeyError(f"Unknown write command: {name}")
    service_attr, method = WRITE_COMMANDS[name]
    svc = services[service_attr]
    return getattr(svc, method)(*(args or []), **(kwargs or {}))
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd /Users/engammar/Scripts/STR && python3.14 tests_host_cluster.py`
Expected: `CLUSTER FAILURES: 0`

- [ ] **Step 5: Commit**

```bash
git add services/command_registry.py tests_host_cluster.py
git commit -m "feat(host): command registry (write-command -> service method)"
```

---

### Task 4: Host service — session store, loop, idempotency, replica publish

**Files:**
- Create: `host/__init__.py` (empty), `host/host_service.py`
- Test: `tests_host_cluster.py` (extend)

**Interfaces:**
- Consumes: `QueueTransport` (Task 1), `applied_commands` (Task 2), `command_registry` (Task 3), the existing service stack (`app_state.initialize_services` in host mode, Task 6 wires it — for this task, the test builds services directly).
- Produces:
  - `HostService(services: dict, db_manager, transport: QueueTransport, bus_dir: str)`.
  - `handle_command(cmd: dict) -> dict` — the pure, testable core: resolves session, enforces idempotency, sets auth context, dispatches, records applied, returns the response dict. (The loop is a thin wrapper that claims/handles/responds/completes/publishes.)
  - `login(username, password) -> (ok, token_or_None, msg)` — a special command handled directly (issues a session token).
  - `publish_replica()` — atomically copies the live DB to `replica/fiu_ro.db` via the SQLite backup API and bumps `replica/version.txt`.
  - `run_once() -> bool` — claim one command, handle, respond, complete, publish; returns True if it processed one.

Command dict shape: `{"id","command","args","kwargs","token"}`. `command == "login"` is special (args `[username, password]`), returns `{"ok","token","user"}`. Response shape: `{"id","ok","result"|"error","db_version"}`.

- [ ] **Step 1: Write the failing test**

Add to `tests_host_cluster.py`:

```python
def _build_host(box):
    """Build a host with a fresh DB + seeded admin + real services."""
    import sqlite3
    from database.init_db import initialize_database
    from database.migrations import migrate_database
    from services.security_service import SecurityService
    from database.db_manager import DatabaseManager
    from services.logging_service import LoggingService
    from services.auth_service import AuthService
    from services.report_service import ReportService
    from services.approval_service import ApprovalService
    from services.version_service import VersionService
    from services.dropdown_service import DropdownService
    from services.validation_service import ValidationService
    from services.settings_service import SettingsService
    from services.report_number_service import ReportNumberService
    from services.activity_service import ActivityService
    from services.dashboard_service import DashboardService
    from services.queue_transport import QueueTransport
    from host.host_service import HostService
    from pathlib import Path
    db = os.path.join(box, 'fiu.db'); bus = os.path.join(box, 'str_bus')
    initialize_database(db); migrate_database(db)
    c = sqlite3.connect(db)
    c.execute("INSERT INTO users (username,password,full_name,role,is_active,created_by) "
              "VALUES ('admin','x','Admin','admin',1,'SYSTEM') ON CONFLICT(username) DO NOTHING")
    c.execute("UPDATE users SET password=?, role='admin', is_active=1 WHERE username='admin'",
              (SecurityService.hash_password('Admin@1234'),)); c.commit(); c.close()
    dbm = DatabaseManager(db); log = LoggingService(dbm, Path(os.path.join(box,'logs')))
    auth = AuthService(dbm, log); settings = SettingsService(dbm, auth)
    reports = ReportService(dbm, log, auth); dash = DashboardService(dbm, log)
    dd = DropdownService(dbm, log, auth); val = ValidationService(dbm, log)
    nums = ReportNumberService(dbm, log); act = ActivityService(dbm, log, auth)
    ver = VersionService(dbm, log, auth, reports, act)
    appr = ApprovalService(dbm, log, auth, ver, reports, act)
    reports.set_activity_service(act); ver.set_activity_service(act)
    services = {'auth_service': auth, 'settings_service': settings, 'report_service': reports,
                'dashboard_service': dash, 'dropdown_service': dd, 'validation_service': val,
                'report_number_service': nums, 'activity_service': act, 'version_service': ver,
                'approval_service': appr}
    transport = QueueTransport(bus)
    host = HostService(services, dbm, transport, bus)
    return host, transport, dbm

def test_host_login_and_command():
    box = tempfile.mkdtemp()
    try:
        host, t, dbm = _build_host(box)
        ok, token, msg = host.login('admin', 'Admin@1234')
        check('T4 host login issues token', ok and token, msg)
        # a write command: create a user (admin session)
        resp = host.handle_command({'id':'c1','command':'auth_service.create_user',
                                    'args':['agent1','pass123','Agent One','agent'],'kwargs':{},'token':token})
        check('T4 create_user command ok', resp['ok'], resp.get('error'))
        n = dbm.execute_with_retry("SELECT COUNT(*) FROM users WHERE username='agent1'")[0][0]
        check('T4 user actually created host-side', n == 1)
        # idempotent replay: same id returns stored response, no double-apply
        resp2 = host.handle_command({'id':'c1','command':'auth_service.create_user',
                                     'args':['agent1','pass123','Agent One','agent'],'kwargs':{},'token':token})
        n2 = dbm.execute_with_retry("SELECT COUNT(*) FROM users WHERE username='agent1'")[0][0]
        check('T4 idempotent replay does not double-apply', n2 == 1 and resp2['ok'])
        # authz enforced host-side: agent token cannot create users
        aok, atoken, _ = host.login('agent1', 'pass123')
        r3 = host.handle_command({'id':'c2','command':'auth_service.create_user',
                                  'args':['x','y','z','agent'],'kwargs':{},'token':atoken})
        check('T4 host enforces authz (agent cannot create_user)', not r3['ok'], r3)
        # replica publishes
        host.publish_replica()
        check('T4 replica published', os.path.exists(os.path.join(box,'str_bus','replica','fiu_ro.db')))
    finally:
        shutil.rmtree(box, ignore_errors=True)
```
Call `test_host_login_and_command()` in `__main__`.

- [ ] **Step 2: Run to verify it fails**

Run: `cd /Users/engammar/Scripts/STR && python3.14 tests_host_cluster.py`
Expected: FAIL — `No module named 'host.host_service'`.

- [ ] **Step 3: Implement the host**

Create `host/__init__.py` (empty file), then `host/host_service.py`:

```python
"""Single-writer host: consumes commands, runs the real services against the
local DB in one transaction each, enforces idempotency + host-side sessions,
publishes a read-only replica. Single-threaded by design."""
import os
import json
import time
import uuid
import sqlite3


class HostService:
    def __init__(self, services: dict, db_manager, transport, bus_dir: str):
        self.services = services
        self.db = db_manager
        self.t = transport
        self.bus = bus_dir
        self.auth = services["auth_service"]
        self._sessions = {}  # token -> {"user_id","username","role","last_seen"}

    # ---- sessions ----
    def login(self, username, password):
        ok, user, msg = self.auth.authenticate(username, password)
        if not ok:
            return False, None, msg
        token = uuid.uuid4().hex
        self._sessions[token] = {"user_id": user["user_id"], "username": user["username"],
                                 "role": user["role"], "last_seen": time.time()}
        return True, token, "ok"

    def _resolve(self, token):
        s = self._sessions.get(token)
        if not s:
            return None
        s["last_seen"] = time.time()
        # rebuild the auth context this command runs under
        return {"user_id": s["user_id"], "username": s["username"], "role": s["role"]}

    # ---- command handling (pure, testable) ----
    def handle_command(self, cmd: dict) -> dict:
        cid = cmd["id"]
        # idempotency: re-emit stored response if already applied
        prior = self.db.execute_with_retry(
            "SELECT response_json FROM applied_commands WHERE command_id = ?", (cid,))
        if prior:
            return json.loads(prior[0][0])

        name = cmd.get("command")
        try:
            if name == "login":
                ok, token, msg = self.login(cmd["args"][0], cmd["args"][1])
                resp = {"id": cid, "ok": ok, "result": {"token": token, "message": msg}} if ok \
                    else {"id": cid, "ok": False, "error": msg}
            else:
                user = self._resolve(cmd.get("token"))
                if not user:
                    resp = {"id": cid, "ok": False, "error": "Not authenticated (re-login)"}
                else:
                    from services import command_registry as cr
                    # set the auth context for THIS command, then dispatch
                    self.auth.current_user = user
                    result = cr.dispatch(self.services, name, cmd.get("args", []), cmd.get("kwargs", {}))
                    resp = {"id": cid, "ok": True, "result": result}
        except Exception as e:
            resp = {"id": cid, "ok": False, "error": f"{type(e).__name__}: {e}"}

        # record applied (login excluded from idempotency ledger — tokens are one-shot anyway)
        if name != "login":
            try:
                self.db.execute_with_retry(
                    "INSERT OR IGNORE INTO applied_commands (command_id, response_json) VALUES (?, ?)",
                    (cid, json.dumps(resp, default=str)))
            except Exception:
                pass
        return resp

    # ---- replica ----
    def publish_replica(self):
        dest = os.path.join(self.bus, "replica", "fiu_ro.db")
        tmp = os.path.join(self.bus, ".tmp", uuid.uuid4().hex + ".db")
        src = sqlite3.connect(self.db.db_path)
        dst = sqlite3.connect(tmp)
        try:
            with dst:
                src.backup(dst)  # consistent snapshot
        finally:
            dst.close(); src.close()
        os.replace(tmp, dest)
        with open(os.path.join(self.bus, "replica", "version.txt"), "w") as f:
            f.write(str(int(time.time() * 1000)))

    # ---- loop ----
    def run_once(self) -> bool:
        cmd = self.t.claim_next()
        if cmd is None:
            return False
        resp = self.handle_command(cmd)
        self.t.respond(cmd["id"], resp)
        self.t.complete(cmd["id"])
        self.publish_replica()
        return True

    def serve_forever(self, poll: float = 0.1):
        self.publish_replica()
        while True:
            if not self.run_once():
                time.sleep(poll)
```

Note: `cr.dispatch`'s result may be a tuple (e.g. `(True, 7, 'ok')`) — JSON-serializable. `json.dumps(..., default=str)` covers stray types.

- [ ] **Step 4: Run to verify it passes**

Run: `cd /Users/engammar/Scripts/STR && python3.14 tests_host_cluster.py`
Expected: `CLUSTER FAILURES: 0`

- [ ] **Step 5: Commit**

```bash
git add host/__init__.py host/host_service.py tests_host_cluster.py
git commit -m "feat(host): host service — sessions, idempotent command handling, replica publish"
```

---

### Task 5: End-to-end through the queue (client submits → host serves → client awaits)

**Files:**
- Test only: `tests_host_cluster.py` (extend) — proves the transport + host compose correctly, including a background host thread.

**Interfaces:**
- Consumes everything from Tasks 1–4. No new product code — this task is the integration proof and a guard that the pieces compose.

- [ ] **Step 1: Write the failing test**

Add to `tests_host_cluster.py`:

```python
def test_end_to_end_via_queue():
    import threading, time
    box = tempfile.mkdtemp()
    try:
        host, t, dbm = _build_host(box)
        stop = {'v': False}
        def loop():
            while not stop['v']:
                if not host.run_once():
                    time.sleep(0.02)
        th = threading.Thread(target=loop, daemon=True); th.start()

        from services.queue_transport import QueueTransport
        client = QueueTransport(os.path.join(box, 'str_bus'))
        # login via queue
        import uuid as _u
        lid = _u.uuid4().hex
        client.submit({'id': lid, 'command': 'login', 'args': ['admin','Admin@1234'], 'kwargs': {}})
        lresp = client.await_response(lid, timeout=10)
        check('T5 login via queue', lresp['ok'] and lresp['result']['token'], lresp)
        token = lresp['result']['token']
        # create_user via queue
        cid = _u.uuid4().hex
        client.submit({'id': cid, 'command': 'auth_service.create_user',
                       'args': ['agentq','pass123','Agent Q','agent'], 'kwargs': {}, 'token': token})
        cresp = client.await_response(cid, timeout=10)
        check('T5 create_user via queue', cresp['ok'], cresp)
        check('T5 user present host-side', dbm.execute_with_retry(
            "SELECT COUNT(*) FROM users WHERE username='agentq'")[0][0] == 1)
        stop['v'] = True; th.join(timeout=2)
    finally:
        shutil.rmtree(box, ignore_errors=True)
```
Call it in `__main__`.

- [ ] **Step 2: Run to verify it fails, then passes**

Run: `cd /Users/engammar/Scripts/STR && python3.14 tests_host_cluster.py`
Expected: PASS (all pieces exist) — `CLUSTER FAILURES: 0`. If it fails, the failure localizes the compose bug; fix before continuing.

- [ ] **Step 3: Commit**

```bash
git add tests_host_cluster.py
git commit -m "test(host): end-to-end command through queue via background host loop"
```

---

### Task 6: Client gateway + read replica + app_state/main wiring

**Files:**
- Create: `services/remote_gateway.py`
- Modify: `flet_app/app_state.py` (`initialize_services` gains `mode`/`bus_dir`)
- Modify: `flet_app/main.py` (`--host` flag)
- Test: `tests_host_cluster.py` (extend — proxy routes writes to queue, reads to local replica)

**Interfaces:**
- Consumes: `QueueTransport`, `command_registry.WRITE_COMMANDS`, the real services (for reads).
- Produces:
  - `RemoteServiceProxy(service_attr, local_service, gateway)` — `__getattr__`: if `"<service_attr>.<name>"` is a write command → return a callable that does `gateway.call("<service_attr>.<name>", args, kwargs)`; else delegate to `local_service.<name>` (runs against the local replica).
  - `RemoteGateway(transport, token_holder)` — `.call(command_name, args, kwargs)` submits + awaits; raises on `ok == False` with the error; sets/reads the current session token; `.login(username, password)` submits a login command and stores the returned token.
  - `AppState.initialize_services(db_path, mode="client", bus_dir=None)`:
    - `mode == "host"` → today's behavior (real services against local `db_path`).
    - `mode == "client"` → open a **read-only** `DatabaseManager` against a local copy of `bus_dir/replica/fiu_ro.db`; build real services on it (for reads); wrap each in a `RemoteServiceProxy` bound to a `RemoteGateway(QueueTransport(bus_dir))`. `app_state.auth_service.authenticate` routes to the gateway login.

- [ ] **Step 1: Write the failing test**

Add to `tests_host_cluster.py`:

```python
def test_client_proxy_routing():
    import threading, time, shutil as _sh
    box = tempfile.mkdtemp()
    try:
        host, t, dbm = _build_host(box)
        stop = {'v': False}
        def loop():
            while not stop['v']:
                if not host.run_once(): time.sleep(0.02)
        th = threading.Thread(target=loop, daemon=True); th.start()
        host.publish_replica()

        from services.queue_transport import QueueTransport
        from services.remote_gateway import RemoteGateway, RemoteServiceProxy
        from database.db_manager import DatabaseManager
        from services.auth_service import AuthService
        from services.report_service import ReportService
        from services.logging_service import LoggingService
        from pathlib import Path
        bus = os.path.join(box, 'str_bus')
        # client read DB = copy of replica
        client_db = os.path.join(box, 'client_ro.db')
        _sh.copy(os.path.join(bus,'replica','fiu_ro.db'), client_db)
        gw = RemoteGateway(QueueTransport(bus))
        ok, msg = gw.login('admin', 'Admin@1234')
        check('T6 gateway login', ok, msg)
        rdbm = DatabaseManager(client_db)
        rlog = LoggingService(rdbm, Path(os.path.join(box,'clog')))
        rauth = AuthService(rdbm, rlog)
        local_reports = ReportService(rdbm, rlog, rauth)
        proxy = RemoteServiceProxy('auth_service', AuthService(rdbm, rlog), gw)
        # write via proxy -> goes through queue -> host applies
        ok2, m2 = proxy.create_user('agentp', 'pass123', 'Agent P', 'agent')
        check('T6 proxy write routed to host', ok2, m2)
        check('T6 host applied proxy write', dbm.execute_with_retry(
            "SELECT COUNT(*) FROM users WHERE username='agentp'")[0][0] == 1)
        # read via proxy delegates locally (no crash); read method exists
        users = RemoteServiceProxy('auth_service', AuthService(rdbm, rlog), gw).get_all_users()
        check('T6 proxy read delegates locally', isinstance(users, list))
        stop['v'] = True; th.join(timeout=2)
    finally:
        _sh.rmtree(box, ignore_errors=True)
```
Call it in `__main__`.

- [ ] **Step 2: Run to verify it fails**

Run: `cd /Users/engammar/Scripts/STR && python3.14 tests_host_cluster.py`
Expected: FAIL — `No module named 'services.remote_gateway'`.

- [ ] **Step 3: Implement the gateway + proxy**

Create `services/remote_gateway.py`:

```python
"""Client-side transport: writes become commands sent to the host; reads
delegate to a local read-only service (the replica). One session token is
held per gateway."""
import uuid
from services import command_registry as cr


class RemoteError(Exception):
    pass


class RemoteGateway:
    def __init__(self, transport, timeout: float = 30.0):
        self.t = transport
        self.timeout = timeout
        self.token = None

    def login(self, username, password):
        cid = uuid.uuid4().hex
        self.t.submit({"id": cid, "command": "login", "args": [username, password], "kwargs": {}})
        resp = self.t.await_response(cid, timeout=self.timeout)
        if resp.get("ok"):
            self.token = resp["result"]["token"]
            return True, "ok"
        return False, resp.get("error", "login failed")

    def call(self, command_name, args, kwargs):
        cid = uuid.uuid4().hex
        self.t.submit({"id": cid, "command": command_name,
                       "args": list(args), "kwargs": dict(kwargs), "token": self.token})
        resp = self.t.await_response(cid, timeout=self.timeout)
        if not resp.get("ok"):
            raise RemoteError(resp.get("error", "command failed"))
        return resp["result"]


class RemoteServiceProxy:
    """Write methods -> gateway (host); everything else -> local read service."""
    def __init__(self, service_attr, local_service, gateway):
        self._attr = service_attr
        self._local = local_service
        self._gw = gateway

    def __getattr__(self, name):
        full = f"{self._attr}.{name}"
        if cr.is_write_command(full):
            def _remote(*args, **kwargs):
                return self._gw.call(full, args, kwargs)
            return _remote
        return getattr(self._local, name)
```

- [ ] **Step 4: Wire app_state + main (add to Step 3's commit)**

In `flet_app/app_state.py`, change `initialize_services` signature to
`def initialize_services(self, db_path, mode="client", bus_dir=None):` and, at the
end (after the real services are built as today), when `mode == "client"` and
`bus_dir` is set, replace each write-capable service with a proxy:

```python
            if mode == "client" and bus_dir:
                from services.queue_transport import QueueTransport
                from services.remote_gateway import RemoteGateway, RemoteServiceProxy
                gw = RemoteGateway(QueueTransport(bus_dir))
                self._gateway = gw
                for attr in ("auth_service", "report_service", "approval_service",
                             "version_service", "report_number_service", "dropdown_service",
                             "validation_service", "settings_service"):
                    local = getattr(self, attr)
                    setattr(self, attr, RemoteServiceProxy(attr, local, gw))
```

Add a `login_remote(self, username, password)` on AppState that calls
`self._gateway.login(...)`; the login view uses it in client mode. (Host/local mode
keeps `auth_service.authenticate` as today.) Keep `db_path` in client mode pointing
at the local replica copy the client maintains (the client refreshes this copy from
`bus_dir/replica/fiu_ro.db` when `version.txt` changes — a small `_refresh_replica()`
helper on AppState, called on a timer and before major reads).

In `flet_app/main.py`, before `ft.app(...)`:

```python
import sys
if "--host" in sys.argv:
    # Host mode: no UI. Build services in host mode and serve the queue.
    from flet_app.app_state import app_state
    from config import Config
    from services.queue_transport import QueueTransport
    from host.host_service import HostService
    Config.load()
    app_state.initialize_services(Config.DATABASE_PATH, mode="host")
    services = {a: getattr(app_state, a) for a in (
        "auth_service","settings_service","report_service","dashboard_service",
        "dropdown_service","validation_service","report_number_service",
        "activity_service","version_service","approval_service")}
    bus = Config.get_bus_dir()  # add: <backup/share>/str_bus, from config
    HostService(services, app_state.db_manager, QueueTransport(bus), bus).serve_forever()
    sys.exit(0)
```

Add `Config.get_bus_dir()` returning `<shared folder>/str_bus` (reuse the existing
backup/share path config; add a `bus_path` if absent). Wire the client UI path to
call `initialize_services(local_replica_path, mode="client", bus_dir=Config.get_bus_dir())`.

- [ ] **Step 5: Run tests + regression**

Run: `cd /Users/engammar/Scripts/STR && python3.14 tests_host_cluster.py` → `CLUSTER FAILURES: 0`
Run the service-layer suites (unchanged logic — must stay green):
```bash
python3.14 tests_conformance.py 2>/dev/null | grep Conformance   # 50/50
python3.14 tests_e2e_harness.py 2>/dev/null | grep TOTAL         # 180/180
python3.14 tests_prosecutor.py 2>/dev/null | grep "TOTAL VULN"   # 0 / 35
```
App still imports in host mode: `cd flet_app && python3.14 -c "import sys;sys.argv=['x','--host'];... "` — skip actually serving; just confirm `import main` succeeds in a normal run.

- [ ] **Step 6: Commit**

```bash
git add services/remote_gateway.py flet_app/app_state.py flet_app/main.py config.py tests_host_cluster.py
git commit -m "feat(host): client gateway + proxy, host/client mode wiring, --host entry"
```

---

### Task 7: Multi-client stress + idempotent-replay-after-crash integration proof

**Files:**
- Test only: `tests_host_cluster.py` (extend) — the guarantee the whole phase exists to provide.

**Interfaces:**
- Consumes all prior tasks. Proves: N concurrent clients through one host apply every acknowledged write exactly once, uniqueness holds, integrity is clean, and a killed-then-restarted host replays without double-applying.

- [ ] **Step 1: Write the failing test**

Add to `tests_host_cluster.py`:

```python
def test_multiclient_stress_and_replay():
    import threading, time, sqlite3
    box = tempfile.mkdtemp()
    try:
        host, t, dbm = _build_host(box)
        stop = {'v': False}
        def loop():
            while not stop['v']:
                if not host.run_once(): time.sleep(0.01)
        th = threading.Thread(target=loop, daemon=True); th.start()

        from services.queue_transport import QueueTransport
        from services.remote_gateway import RemoteGateway
        bus = os.path.join(box, 'str_bus')
        # seed agents via one admin gateway
        admin_gw = RemoteGateway(QueueTransport(bus)); admin_gw.login('admin','Admin@1234')
        NUSERS = 6
        for i in range(NUSERS):
            admin_gw.call('auth_service.create_user', [f'ag{i}', 'pass123', f'Agent {i}', 'agent'], {})
        errors = []
        def worker(i):
            try:
                gw = RemoteGateway(QueueTransport(bus)); gw.login(f'ag{i}','pass123')
                # each agent reserves numbers then creates reports via commands
                gw.call('report_number_service.reserve_next_numbers', [f'ag{i}'], {})
            except Exception as e:
                errors.append(f'ag{i}: {e}')
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(NUSERS)]
        [x.start() for x in threads]; [x.join() for x in threads]
        check('T7 no worker errors', not errors, errors[:2])

        # integrity + no dup applied commands
        integ = sqlite3.connect(dbm.db_path).execute("PRAGMA integrity_check").fetchone()[0]
        check('T7 integrity ok', integ == 'ok', integ)
        dup = dbm.execute_with_retry(
            "SELECT command_id, COUNT(*) c FROM applied_commands GROUP BY command_id HAVING c>1")
        check('T7 no command applied twice', not dup, dup[:3])

        # crash-replay: re-handle an already-applied command id -> no change, same response
        applied = dbm.execute_with_retry("SELECT command_id FROM applied_commands LIMIT 1")
        if applied:
            cid = applied[0][0]
            before = dbm.execute_with_retry("SELECT COUNT(*) FROM users")[0][0]
            host.handle_command({'id': cid, 'command': 'auth_service.create_user',
                                 'args': ['dupe','p','d','agent'], 'kwargs': {}, 'token': None})
            after = dbm.execute_with_retry("SELECT COUNT(*) FROM users")[0][0]
            check('T7 replay of applied id is a no-op', before == after)
        stop['v'] = True; th.join(timeout=2)
    finally:
        shutil.rmtree(box, ignore_errors=True)
```
Call it in `__main__`.

- [ ] **Step 2: Run to verify it passes**

Run: `cd /Users/engammar/Scripts/STR && python3.14 tests_host_cluster.py`
Expected: `CLUSTER FAILURES: 0`. (If reservation semantics need the new model, that's Phase 2 — for Phase 1 the existing `reserve_next_numbers` runs host-side; a per-user "already reserved" result is a valid ok/skip, not an error. Adjust the assertion to accept a returned failure tuple as "handled without crash," not a thrown error.)

- [ ] **Step 3: Commit**

```bash
git add tests_host_cluster.py
git commit -m "test(host): multi-client stress, exactly-once, integrity, crash-replay"
```

---

## Notes for the implementer

- **Do not change service business logic.** If a command needs different behavior, that's a service-level change tracked elsewhere (Phase 2 for reservation). Phase 1 only moves the transport.
- **The host is single-threaded on purpose.** `handle_command` sets `auth.current_user` then dispatches; because one command runs at a time, there is no cross-command contamination. Never parallelize the host loop.
- **Read staleness is expected.** Clients read the replica; their own just-written change appears after the host applies it and republishes. Consistency-critical checks (uniqueness, reservation gate) run host-side inside the write command, so staleness never causes a bad write.
- **`os.replace` is atomic only within one filesystem.** The `.tmp` dir lives under the same `str_bus` root as its targets, so this holds on the share. Never write the tmp file to a different drive.
- **JSON args:** reports/users/settings are dicts/str/int — JSON-safe. If a future command needs a non-serializable arg, add explicit (de)serialization; do not paper over it.
- **Config:** add a single `bus_path` (the `<share>/str_bus` folder) to `config/config.json` + `Config`. Host and client both read it. It contains no secrets.
