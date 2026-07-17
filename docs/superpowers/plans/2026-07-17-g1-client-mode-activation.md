# G1: Client-Mode Activation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the already-built-and-tested host/queue/command-RPC machinery actually usable across multiple PCs by wiring the real launch and login paths to run in `client` mode against a shared-folder host.

**Architecture:** A single config `MODE` selects one of three launch behaviors: `local` (today's single-PC install — unchanged), `host` (headless single-writer, the existing `--host` path), `client` (UI that reads a locally-copied replica and routes writes to the host over the shared-folder queue). In `client` mode the client bootstraps a local copy of the host's published read-only replica, refreshes it in the background when the host republishes, logs in through the host (which owns the real password + session), and directs all reads at the local copy while writes go through the `RemoteGateway`. The host and queue code (Phase 1) and reservation model (Phase 2) are reused **unchanged**.

**Tech Stack:** Python 3.14 (tests run `python3.14 tests_*.py`), Flet 0.28.3, SQLite3, existing services in `services/`, host in `host/`.

## Global Constraints

- Tests are standalone scripts run with `python3.14 tests_<name>.py` — no pytest. A harness prints `PASS`/`FAIL` lines and exits. New tests follow this same pattern (a `tests_g1.py` script with a `check(label, cond, detail)` helper, exit non-zero on any failure). There is no `timeout` binary on macOS — never wrap commands in `timeout`.
- Never commit `fields.numbers`, `fields.xlsx`, `pbox/`, or `sandbox/`.
- Commit trailer on every commit: `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`
- The service layer, `host/host_service.py` command dispatch, `services/command_registry.py`, `services/queue_transport.py`, and the Phase 2 reservation logic are **not** to be modified except where a task explicitly says so. Client mode reuses them as-is.
- Atomic file transport rule: any write to the shared folder or to a file another process/connection may read is written to a `.tmp` sibling then `os.replace`d into place — never written in place.
- `resp.ok` contract (do not regress): `ok=True` for any dispatched command (business `(False, msg)` rejections ride through as the return value); `ok=False` only for host-level failures. The gateway raises `RemoteError` only on `ok=False`.
- Single-writer invariant: exactly one `host` process writes the real DB. Clients never open the real DB; they open a local throwaway copy of the replica. Nothing a client does may write to that local copy in a way that diverges from the host.

---

### Task 1: Config — launch mode + share path

**Files:**
- Modify: `config.py`
- Test: `tests_g1.py` (create)

**Interfaces:**
- Produces:
  - `Config.MODE` — one of `"local"`, `"host"`, `"client"` (default `"local"`).
  - `Config.SHARE_PATH` — the shared-folder root (client & host). May be `None` in `local` mode.
  - `Config.get_client_replica_path() -> str` — absolute local path where a client keeps its copy of the replica DB (under the app's `database/` dir, filename `client_replica.db`).
  - `Config.get_bus_dir()` — unchanged signature, but when `SHARE_PATH` is set it derives the bus from `SHARE_PATH` (so client and host agree on one bus). Precedence: `SHARE_PATH` → `BACKUP_PATH` → dir of `DATABASE_PATH` → `"."`, with `str_bus` appended.
  - `Config.is_configured()` — mode-aware (see Step 3).

- [ ] **Step 1: Write the failing test**

Add to a new `tests_g1.py`:

```python
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3.14 tests_g1.py`
Expected: FAIL on `cfg client configured with share` / `get_client_replica_path` (attributes/methods don't exist yet), or an AttributeError.

- [ ] **Step 3: Implement in `config.py`**

Add class attributes near `DATABASE_PATH`:
```python
    MODE = "local"          # "local" | "host" | "client"
    SHARE_PATH = None       # shared-folder root (host & client); None in local mode
```
Extend `load()` to read them (with defaults) and `save()` to write them:
```python
    # inside load(), after existing gets:
                    cls.MODE = config_data.get('mode', 'local')
                    cls.SHARE_PATH = config_data.get('share_path')
    # inside save() config_data dict:
                'mode': cls.MODE,
                'share_path': cls.SHARE_PATH,
```
Add the replica-path helper:
```python
    @classmethod
    def get_client_replica_path(cls) -> str:
        """Local file a client keeps its copy of the host replica in."""
        base = os.path.dirname(cls.DATABASE_PATH) if cls.DATABASE_PATH else \
            str(Path(__file__).parent / "database")
        os.makedirs(base, exist_ok=True)
        return os.path.join(base, "client_replica.db")
```
Change `get_bus_dir()` precedence so `SHARE_PATH` wins:
```python
        base = cls.SHARE_PATH or cls.BACKUP_PATH
        if not base:
            base = os.path.dirname(cls.DATABASE_PATH) if cls.DATABASE_PATH else "."
```
Make `is_configured()` mode-aware:
```python
    @classmethod
    def is_configured(cls) -> bool:
        if cls.MODE == "client":
            return bool(cls.SHARE_PATH) and os.path.isdir(cls.SHARE_PATH)
        # local / host: need a real local DB (existing behavior)
        if cls.DATABASE_PATH is None or cls.BACKUP_PATH is None:
            return False
        return Path(cls.DATABASE_PATH).exists()
```

- [ ] **Step 4: Run to verify it passes**

Run: `python3.14 tests_g1.py`
Expected: PASS all `cfg ...` lines, `ALL PASS`.

- [ ] **Step 5: Commit**

```bash
git add config.py tests_g1.py
git commit -m "feat(g1): mode-aware config (local/host/client) + share/replica paths"
```

---

### Task 2: Host login returns the user; unified auth in app_state

**Files:**
- Modify: `host/host_service.py` (login result only — add `user`, keep `token`)
- Modify: `services/remote_gateway.py` (`RemoteGateway.login` returns user)
- Modify: `flet_app/app_state.py` (`login_remote` returns user; new `authenticate()`; `login()` sets local auth context in client mode)
- Test: `tests_g1.py`, and confirm `tests_host_cluster.py` still green

**Interfaces:**
- Consumes: `HostService.login(username, password) -> (ok, token, msg)` (tuple unchanged), `resp["result"]` for a queued login = `{"token", "message", "user"}`.
- Produces:
  - `RemoteGateway.login(username, password) -> (ok, user_or_None, msg)` (was `(ok, msg)`).
  - `AppState.login_remote(username, password) -> (ok, user_or_None, msg)`.
  - `AppState.authenticate(username, password) -> (ok, user_or_None, msg)` — gateway when in client mode, else local `auth_service.authenticate`.
  - `AppState.login(user)` — additionally sets the underlying local `auth_service.current_user` so local (replica) permission checks work in client mode.

- [ ] **Step 1: Write the failing test**

Add to `tests_g1.py`:
```python
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
```
Register it in `__main__`: add `test_host_login_returns_user()`.

- [ ] **Step 2: Run to verify it fails**

Run: `python3.14 tests_g1.py`
Expected: FAIL `host login result has user` (result has only token/message today).

- [ ] **Step 3: Implement**

In `host/host_service.py` `login()`, return the user too and thread it into the queued-login result. Change `login` to return the user in the tuple's place is risky (cluster test unpacks 3) — keep the 3-tuple `(ok, token, msg)` but stash the user so `handle_command` can include it. Simplest: have `login` also return user via a 4th internal path. Concretely, change `login`:
```python
    def login(self, username, password):
        ok, user, msg = self.auth.authenticate(username, password)
        if not ok:
            return False, None, msg, None
        token = uuid.uuid4().hex
        self._sessions[token] = {"user_id": user["user_id"], "username": user["username"],
                                 "role": user["role"], "last_seen": time.time()}
        return True, token, "ok", user
```
Update the two callers of `login`:
- In `handle_command`, the `name == "login"` branch:
```python
            if name == "login":
                ok, token, msg, user = self.login(cmd["args"][0], cmd["args"][1])
                resp = {"id": cid, "ok": ok,
                        "result": {"token": token, "message": msg,
                                   "user": {"user_id": user["user_id"], "username": user["username"],
                                            "full_name": user.get("full_name"), "role": user["role"]}}} if ok \
                    else {"id": cid, "ok": False, "error": msg}
```
- **`tests_host_cluster.py` calls `host.login(...)` expecting a 3-tuple.** Update those call sites (lines ~108 and ~122) to unpack 4: `ok, token, msg, _user = host.login(...)`. (This is the one sanctioned edit to that test file.)

In `services/remote_gateway.py` `RemoteGateway.login`:
```python
    def login(self, username, password):
        cid = uuid.uuid4().hex
        self.t.submit({"id": cid, "command": "login", "args": [username, password], "kwargs": {}})
        resp = self.t.await_response(cid, timeout=self.timeout)
        if resp.get("ok"):
            self.token = resp["result"]["token"]
            return True, resp["result"].get("user"), "ok"
        return False, None, resp.get("error", "login failed")
```

In `flet_app/app_state.py`:
```python
    def login_remote(self, username: str, password: str):
        if not self._gateway:
            return False, None, "Not in client mode (no gateway configured)"
        return self._gateway.login(username, password)

    def authenticate(self, username: str, password: str):
        """Unified login: host (client mode) or local auth_service."""
        if self._gateway:
            return self.login_remote(username, password)
        return self.auth_service.authenticate(username, password)
```
And in `login(self, user, ...)`, after setting state, set the local auth context so replica-side permission checks resolve in client mode:
```python
        # In client mode auth_service is a proxy; set current_user on the real
        # local service so has_permission()/RBAC reads work against the replica.
        try:
            local_auth = getattr(self.auth_service, "_local", self.auth_service)
            local_auth.current_user = user
        except Exception:
            pass
```

- [ ] **Step 4: Run tests**

Run: `python3.14 tests_g1.py && python3.14 tests_host_cluster.py`
Expected: `tests_g1.py` PASS all; `tests_host_cluster.py` still green (0 failures).

- [ ] **Step 5: Commit**

```bash
git add host/host_service.py services/remote_gateway.py flet_app/app_state.py tests_g1.py tests_host_cluster.py
git commit -m "feat(g1): host login returns user; unified app_state.authenticate for client/local"
```

---

### Task 3: Client replica sync (bootstrap + background refresh)

**Files:**
- Create: `services/replica_sync.py`
- Test: `tests_g1.py`

**Interfaces:**
- Produces:
  - `bootstrap_replica(bus_dir, local_path, timeout=30.0) -> bool` — copies `bus_dir/replica/fiu_ro.db` to `local_path` (atomic temp+replace). Waits up to `timeout` for the replica to appear (host may still be starting); returns `True` on success, `False` on timeout.
  - `class ReplicaRefresher(bus_dir, local_path, poll=2.0, on_update=None)` with `.start()` and `.stop()`. A daemon thread reads `bus_dir/replica/version.txt`; when it changes, re-copies the replica to `local_path` (atomic) and calls `on_update()` if given. Copy failures are swallowed and retried next poll (the share may be briefly unavailable) — never crash the thread.

- [ ] **Step 1: Write the failing test**

Add to `tests_g1.py`:
```python
def test_replica_sync():
    from services.replica_sync import bootstrap_replica, ReplicaRefresher
    d = tempfile.mkdtemp()
    bus = os.path.join(d, "bus"); os.makedirs(os.path.join(bus, "replica"))
    rep = os.path.join(bus, "replica", "fiu_ro.db")
    ver = os.path.join(bus, "replica", "version.txt")
    with open(rep, "wb") as f: f.write(b"DBv1")
    with open(ver, "w") as f: f.write("1")
    local = os.path.join(d, "client_replica.db")
    check("bootstrap copies replica", bootstrap_replica(bus, local, timeout=2.0) and os.path.exists(local))
    check("bootstrap content v1", open(local, "rb").read() == b"DBv1")
    # bootstrap timeout when no replica
    d2 = tempfile.mkdtemp(); bus2 = os.path.join(d2, "bus"); os.makedirs(os.path.join(bus2, "replica"))
    check("bootstrap times out cleanly", bootstrap_replica(bus2, os.path.join(d2, "x.db"), timeout=0.5) is False)
    # refresher picks up a version bump
    hits = {"n": 0}
    r = ReplicaRefresher(bus, local, poll=0.1, on_update=lambda: hits.__setitem__("n", hits["n"] + 1))
    r.start()
    with open(rep, "wb") as f: f.write(b"DBv2")
    with open(ver, "w") as f: f.write("2")
    for _ in range(50):
        if open(local, "rb").read() == b"DBv2": break
        time.sleep(0.1)
    r.stop()
    check("refresher hot-swaps to v2", open(local, "rb").read() == b"DBv2")
    check("refresher fired on_update", hits["n"] >= 1)
    shutil.rmtree(d, ignore_errors=True); shutil.rmtree(d2, ignore_errors=True)
```
Register `test_replica_sync()` in `__main__`.

- [ ] **Step 2: Run to verify it fails**

Run: `python3.14 tests_g1.py`
Expected: FAIL — `services.replica_sync` does not exist (ImportError).

- [ ] **Step 3: Implement `services/replica_sync.py`**

```python
"""Client-side replica sync: copy the host's published read-only replica to a
local file and keep it fresh. The client reads its LOCAL copy so the shared
file (which the host republishes via os.replace) is never read mid-swap."""
import os
import time
import uuid
import shutil
import threading


def _paths(bus_dir):
    rep = os.path.join(bus_dir, "replica", "fiu_ro.db")
    ver = os.path.join(bus_dir, "replica", "version.txt")
    return rep, ver


def _atomic_copy(src, dst):
    """Copy src -> dst atomically (temp in dst's dir, then os.replace)."""
    tmp = dst + ".tmp-" + uuid.uuid4().hex
    shutil.copyfile(src, tmp)
    os.replace(tmp, dst)


def bootstrap_replica(bus_dir, local_path, timeout=30.0):
    """Wait (up to timeout) for the host replica to exist, copy it locally."""
    rep, _ = _paths(bus_dir)
    deadline = time.time() + timeout
    while time.time() < deadline:
        if os.path.exists(rep):
            try:
                _atomic_copy(rep, local_path)
                return True
            except Exception:
                pass  # mid-republish on the host; retry
        time.sleep(0.2)
    return False


def _read_version(ver):
    try:
        with open(ver) as f:
            return f.read().strip()
    except Exception:
        return None


class ReplicaRefresher:
    """Daemon thread: when version.txt changes, re-copy the replica locally."""
    def __init__(self, bus_dir, local_path, poll=2.0, on_update=None):
        self.rep, self.ver = _paths(bus_dir)
        self.local = local_path
        self.poll = poll
        self.on_update = on_update
        self._last = _read_version(self.ver)
        self._stop = threading.Event()
        self._thread = None

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2.0)

    def _run(self):
        while not self._stop.is_set():
            v = _read_version(self.ver)
            if v is not None and v != self._last:
                try:
                    _atomic_copy(self.rep, self.local)
                    self._last = v
                    if self.on_update:
                        self.on_update()
                except Exception:
                    pass  # share briefly unavailable / mid-swap; retry next poll
            self._stop.wait(self.poll)
```

- [ ] **Step 4: Run to verify it passes**

Run: `python3.14 tests_g1.py`
Expected: PASS all `bootstrap ...` / `refresher ...` lines.

- [ ] **Step 5: Commit**

```bash
git add services/replica_sync.py tests_g1.py
git commit -m "feat(g1): client replica sync — bootstrap + background hot-swap refresher"
```

---

### Task 4: Suppress client-side DB log writes to the replica copy

**Files:**
- Modify: `services/logging_service.py` (accept a flag to skip the DB handler)
- Modify: `flet_app/app_state.py` (pass the flag in client mode)
- Test: `tests_g1.py`

**Interfaces:**
- Consumes: `LoggingService(db_manager, log_dir)`.
- Produces: `LoggingService(db_manager, log_dir, db_logging=True)`. When `db_logging=False`, the `DatabaseLogHandler` is not attached (file + console only). In client mode the local DB is a throwaway replica copy that the refresher overwrites — writing logs to it is pointless and risks holding a write connection open during `os.replace`.

- [ ] **Step 1: Write the failing test**

Add to `tests_g1.py`:
```python
def test_logging_no_db_handler_client():
    import tempfile
    from database.init_db import initialize_database
    from database.db_manager import DatabaseManager
    from services.logging_service import LoggingService
    d = tempfile.mkdtemp(); db = os.path.join(d, "l.db"); initialize_database(db)
    dbm = DatabaseManager(db)
    from services.logging_service import DatabaseLogHandler
    ls = LoggingService(dbm, None, db_logging=False)
    has_db = any(isinstance(h, DatabaseLogHandler) for h in ls.logger.handlers)
    check("client logging has no DB handler", not has_db)
    ls2 = LoggingService(dbm, None)  # default keeps DB handler (host/local)
    has_db2 = any(isinstance(h, DatabaseLogHandler) for h in ls2.logger.handlers)
    check("default logging keeps DB handler", has_db2)
    shutil.rmtree(d, ignore_errors=True)
```
Register `test_logging_no_db_handler_client()`.

- [ ] **Step 2: Run to verify it fails**

Run: `python3.14 tests_g1.py`
Expected: FAIL — `LoggingService()` has no `db_logging` kwarg (TypeError).

- [ ] **Step 3: Implement**

In `services/logging_service.py`, add the param to `__init__` (keep existing default behavior) and guard the DB handler attach:
```python
    def __init__(self, db_manager, log_dir, db_logging=True):
        ...
        if db_logging:
            self.db_handler = DatabaseLogHandler(db_manager)
            ...
            self.logger.addHandler(self.db_handler)
        else:
            self.db_handler = None
```
Guard any later use of `self.db_handler` against `None` (e.g. `set_user_context` if it touches the handler).

In `flet_app/app_state.py` `initialize_services`, construct logging with the flag off in client mode:
```python
            self.logging_service = LoggingService(
                self.db_manager, log_dir,
                db_logging=(mode != "client" or not bus_dir))
```

- [ ] **Step 4: Run to verify it passes**

Run: `python3.14 tests_g1.py`
Expected: PASS both logging lines.

- [ ] **Step 5: Commit**

```bash
git add services/logging_service.py flet_app/app_state.py tests_g1.py
git commit -m "feat(g1): skip DB log handler in client mode (throwaway replica)"
```

---

### Task 5: Wire the launch path — mode-driven startup, client login, setup wizard mode selection

**Files:**
- Modify: `flet_app/main.py` (mode-driven `_initialize_services`, client bootstrap + refresher, `__main__` host/client dispatch)
- Modify: `flet_app/views/login_view.py` (both auth call sites use `app_state.authenticate`)
- Modify: `flet_app/views/setup_wizard_view.py` (mode + share-path selection)
- Test: manual smoke (documented), plus `tests_g1.py` end-to-end client-roundtrip

**Interfaces:**
- Consumes: `Config.MODE`, `Config.SHARE_PATH`, `Config.get_bus_dir()`, `Config.get_client_replica_path()`, `bootstrap_replica`, `ReplicaRefresher`, `app_state.initialize_services(db_path, mode, bus_dir)`, `app_state.authenticate`.

- [ ] **Step 1: Write the failing end-to-end test**

Add to `tests_g1.py` — a full client→host round trip through the queue proving the UI-facing `authenticate` + a proxied write work against a running host loop:
```python
def test_client_roundtrip():
    import tempfile, sqlite3, threading, bcrypt
    from database.init_db import initialize_database
    from database.db_manager import DatabaseManager
    from database.migrations import migrate_database
    from services.logging_service import LoggingService
    from services.auth_service import AuthService
    from host.host_service import HostService
    from services.queue_transport import QueueTransport
    from services.remote_gateway import RemoteGateway, RemoteServiceProxy
    d = tempfile.mkdtemp()
    db = os.path.join(d, "h.db"); initialize_database(db); migrate_database(db)
    dbm = DatabaseManager(db)
    pw = bcrypt.hashpw(b"Admin@1234", bcrypt.gensalt()).decode()
    c = sqlite3.connect(db)
    c.execute("INSERT INTO users (username,password,full_name,role,is_active,created_by) "
              "VALUES ('admin',?,'Admin','admin',1,'SYSTEM') ON CONFLICT(username) DO UPDATE SET password=excluded.password",
              (pw,)); c.commit(); c.close()
    log = LoggingService(dbm, None)
    services = {"auth_service": AuthService(dbm, log)}
    bus = os.path.join(d, "bus")
    for sub in ("", "replica", ".tmp", "cmd", "resp", "done"):
        os.makedirs(os.path.join(bus, sub), exist_ok=True)
    host = HostService(services, dbm, QueueTransport(bus), bus)
    stop = threading.Event()
    def run():
        host.publish_replica()
        while not stop.is_set():
            if not host.run_once():
                time.sleep(0.02)
    th = threading.Thread(target=run, daemon=True); th.start()
    try:
        gw = RemoteGateway(QueueTransport(bus), timeout=10.0)
        ok, user, msg = gw.login("admin", "Admin@1234")
        check("roundtrip login ok", ok and user and user["role"] == "admin", msg)
        proxy = RemoteServiceProxy("auth_service", AuthService(dbm, log), gw)
        res = proxy.create_user("agz", "Passw0rd!", "Ag Z", "agent")
        # create_user returns (ok, msg) business tuple through the queue
        okc = res[0] if isinstance(res, (list, tuple)) else bool(res)
        check("roundtrip proxied create_user", okc, res)
        n = dbm.execute_with_retry("SELECT COUNT(*) FROM users WHERE username='agz'")[0][0]
        check("roundtrip user created host-side", n == 1)
    finally:
        stop.set(); th.join(timeout=2.0); shutil.rmtree(d, ignore_errors=True)
```
Register `test_client_roundtrip()`.

- [ ] **Step 2: Run to verify it fails or passes**

Run: `python3.14 tests_g1.py`
Expected: This test exercises only existing Phase-1 machinery + Task 2's user-in-login, so it should PASS once Task 2 is in. If it FAILs, fix the wiring it exposes before touching the UI. (It guards the contract the UI depends on.)

- [ ] **Step 3: Implement launch wiring in `flet_app/main.py`**

Replace `_initialize_services` body to branch on mode. Keep the local/host path identical to today; add the client path:
```python
    def _initialize_services(self) -> bool:
        try:
            from config import Config
            if Config.MODE == "client":
                from services.replica_sync import bootstrap_replica, ReplicaRefresher
                bus_dir = Config.get_bus_dir()
                local_replica = Config.get_client_replica_path()
                if not bootstrap_replica(bus_dir, local_replica, timeout=30.0):
                    self._show_error("Cannot reach the host replica on the shared folder.\n"
                                     "Make sure a host PC is running and the share is available.")
                    return False
                ok = app_state.initialize_services(local_replica, mode="client", bus_dir=bus_dir)
                if not ok:
                    return False
                # keep the local read replica fresh
                self._refresher = ReplicaRefresher(
                    bus_dir, local_replica, poll=2.0,
                    on_update=lambda: None)
                self._refresher.start()
                theme_manager.initialize(self.page, app_state.settings_service, app_state.auth_service)
                return True
            # local / host (unchanged)
            db_path = Config.DATABASE_PATH
            if not db_path:
                return False
            success = app_state.initialize_services(db_path)
            if success:
                theme_manager.initialize(self.page, app_state.settings_service, app_state.auth_service)
            return success
        except Exception as e:
            print(f"Error initializing services: {e}")
            import traceback; traceback.print_exc()
            return False
```
**Do NOT touch the `__main__` block or `main(page)`.** `FletApp.__init__` already calls `Config.load()` (main.py:79) before `_start()`, so `Config.MODE` is set by the time `_initialize_services` runs — the existing `ft.app(target=main)` launch and the existing `--host` branch stay exactly as they are. All the client wiring lives inside `_initialize_services` (above). This task changes only `_initialize_services` in `main.py`.

- [ ] **Step 4: Point LoginView at unified auth**

In `flet_app/views/login_view.py`, both call sites (~line 111 and ~429) change:
```python
            success, user, message = await loop.run_in_executor(
                None, app_state.authenticate, username, password)
```
(and the class variant: `self.app_state.authenticate`). Everything after (`app_state.login(user)`, `on_login_success(user)`) is unchanged.

- [ ] **Step 5: Add mode selection to the setup wizard**

In `flet_app/views/setup_wizard_view.py`, add a mode `ft.RadioGroup` (Local / Host / Client) and a share-path field shown for Host/Client. Change `on_complete` to pass mode + share path. Update the wizard's completion handler and `main.py`'s `on_setup_complete` to persist them:
```python
    # setup_wizard_view build(): add
    mode_group = ft.RadioGroup(value="local", content=ft.Column([
        ft.Radio(value="local", label="Single PC (local database)"),
        ft.Radio(value="host",  label="Host PC (this PC serves the shared team)"),
        ft.Radio(value="client",label="Client PC (connect to a host over the shared folder)"),
    ]))
    share_path_input = ft.TextField(label="Shared folder path (host/client)", value="")
    # on the finish handler, call:
    #   on_complete(db_path, backup_path, mode_group.value, share_path_input.value.strip() or None)
```
In `flet_app/main.py` `_show_setup_wizard`:
```python
        def on_setup_complete(db_path, backup_path, mode="local", share_path=None):
            Config.DATABASE_PATH = db_path
            Config.BACKUP_PATH = backup_path
            Config.MODE = mode
            Config.SHARE_PATH = share_path
            Config.save()
            if self._initialize_services():
                self._show_login()
            else:
                self._show_error("Failed to initialize after setup.")
```
For **client** mode the wizard must not require a local DB (there is none yet) — when `mode == "client"`, skip the "create/validate database" steps and only validate the share path is reachable (`os.path.isdir(share_path)`). Keep `db_path`/`backup_path` optional/blank in that case; `get_client_replica_path()` derives a local file regardless.

- [ ] **Step 6: Manual smoke test (documented, run by controller)**

Two-terminal smoke (record the commands + observed result in the task report):
```bash
# terminal A — host (uses an existing configured local DB + a scratch share)
python3.14 flet_app/main.py --host   # after setting SHARE_PATH in config to a scratch dir
# terminal B — client UI
#   set config.json mode=client, share_path=<same scratch dir>, then:
python3.14 flet_app/main.py
```
Expected: client window opens, login against host succeeds, dashboard reads render from the replica, creating a report round-trips to the host and appears after the next replica refresh. If Flet cannot run headless in this environment, state that and rely on `test_client_roundtrip` as the automated proof; the manual steps are then documented for the operator runbook.

- [ ] **Step 7: Run the full suite**

Run:
```bash
python3.14 tests_g1.py && python3.14 tests_host_cluster.py && python3.14 tests_e2e_harness.py && python3.14 tests_conformance.py && python3.14 tests_prosecutor.py
```
Expected: all green (g1 ALL PASS; cluster 0; e2e 183/183; conformance 50/50; prosecutor 0/35).

- [ ] **Step 8: Commit**

```bash
git add flet_app/main.py flet_app/views/login_view.py flet_app/views/setup_wizard_view.py tests_g1.py
git commit -m "feat(g1): mode-driven launch, client replica bootstrap+refresh, unified login, wizard mode select"
```

---

## Deferred to Phase 3 (not in this plan)

- **G2 stable command ids** — the gateway currently mints a fresh `uuid` per `call()`. That is correct as long as there is no automatic retry (a lost response today just surfaces as an error to the user, never a double-apply). Stable per-logical-write ids are required only before host-down queueing/retry, which lands with Phase 3 failover. The idempotency ledger (`applied_commands`) already exists to make that safe.
- **Host heartbeat + client host-offline UX** (read-only banner, write queueing).
- **Manual "Become Host" failover** + term/lease.
- **Sleep-guard** (`SetThreadExecutionState`), **autostart**, **integrity-check-on-start**, **session timeout R3 enforcement**.
- **`--panel` operator Control Panel** + `docs/HOST_RUNBOOK.md`.

## Self-Review

- **Spec coverage (§7b G1):** login_remote wired (Task 2, 5) ✓; replica bootstrap/refresh (Task 3, 5) ✓; client replica read-only incidental-write handling (Task 4 — DB log handler; login is remote so no local session_log; settings writes are proxied) ✓; setup wizard mode selection (Task 5) ✓.
- **Placeholder scan:** every code step carries real code; the only "preserve existing" note is the `__main__` Flet-launch call, which is explicitly "keep what's there."
- **Type consistency:** `authenticate`/`login_remote`/`gateway.login` all return `(ok, user_or_None, msg)`; `host.login` returns the 4-tuple `(ok, token, msg, user)` and its two callers (handle_command + tests_host_cluster) are both updated. `RemoteServiceProxy` unchanged. `bootstrap_replica`/`ReplicaRefresher` signatures match their test usage.
- **Single-writer invariant:** clients open only the local `client_replica.db` copy; no client writes the real DB; DB log handler off in client mode.
