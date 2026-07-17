# Phase 3a: Failover Safety Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the single-writer host survivable — no two processes can both write (term/lease + step-down), the host self-heals and self-protects on start (integrity-check, sleep-guard, session-timeout, periodic backups), a designated teammate can manually promote a backup PC ("Become Host") without an election race, and clients queue writes safely while the host is briefly down (stable command ids, exactly-once).

**Architecture:** Every host owns its LOCAL DB and broadcasts liveness + a monotonic **term** via `host/heartbeat.json` on the share. A host steps down the instant it sees a heartbeat with a higher term from a different host — so a promoted backup (higher term) always wins and the woken old host retires itself; because each host only ever wrote its own local DB and the queue is idempotent by command `id`, the worst case is a small reconciliation window, never corruption. Manual "Become Host" adopts the newest published replica, re-queues in-flight commands, and bumps the term. Clients that time out against a down host persist the command (with its stable id) to a local outbox and drain it — same id — when a host returns, so the idempotency ledger applies it exactly once.

**Tech Stack:** Python 3.14 (tests: `python3.14 tests_<name>.py`), SQLite3, existing `host/host_service.py`, `services/queue_transport.py`, `services/remote_gateway.py`, `database/migrations.py`.

## Global Constraints

- Tests are standalone scripts run with `python3.14 tests_<name>.py` (NO pytest). New tests go in `tests_failover.py` following the existing harness pattern: a module-level `_fail` counter, a `check(label, cond, detail="")` helper that prints `PASS`/`FAIL` and increments `_fail`, a `__main__` block that calls each test then `sys.exit(1 if _fail else 0)`. There is no `timeout` binary on macOS — never wrap commands in it.
- Never commit `fields.numbers`, `fields.xlsx`, `pbox/`, `sandbox/`.
- Commit trailer on every commit: `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`
- Atomic-file rule (already used across the codebase): any write to the shared folder or to a file another process may read goes to a `.tmp` sibling then `os.replace` — never in place. `QueueTransport.__init__` already creates the bus subdirs (`queue/pending|processing|done`, `responses`, `replica`, `host`, `backups`, `.tmp`) — do not re-create them.
- **Single-writer invariant is the whole point:** never allow two processes to serve (apply writes) against data that feeds the same clients at once. Term/step-down is the mechanism; every task must preserve it.
- The command protocol and `resp.ok` contract are unchanged: `ok=True` for any dispatched command (business `(False,msg)` rides through as the result), `ok=False` only for host-level failures. `applied_commands(command_id PK, response_json)` dedups redelivered commands.
- Do not modify the Phase-2 reservation logic or the service layer except where a task explicitly says so.

---

### Task 1: Host lease table + term helpers

**Files:**
- Modify: `database/migrations.py` (add migration block, same existence-gated style as `reserved_numbers`)
- Create: `host/lease.py`
- Test: `tests_failover.py` (create)

**Interfaces:**
- Produces:
  - Table `host_lease(id PK CHECK(id=1), host_id TEXT, term INTEGER NOT NULL DEFAULT 0, updated_at TEXT)` seeded with one row `(1, NULL, 0)`.
  - `host.lease.read_lease(db_manager) -> (host_id, term)` — returns `(None, 0)` if unseeded.
  - `host.lease.bump_lease(db_manager, host_id, min_term=0) -> new_term` — atomically sets term to `max(current, min_term) + 1` and records `host_id`; returns the new term.

- [ ] **Step 1: Write the failing test** — create `tests_failover.py`:

```python
"""Phase 3a failover safety core tests. Run: python3.14 tests_failover.py"""
import os, sys, json, time, tempfile, shutil, sqlite3
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_fail = 0
def check(label, cond, detail=""):
    global _fail
    ok = bool(cond)
    print(("PASS " if ok else "FAIL ") + label + ("" if ok else f"  -- {detail}"))
    if not ok:
        _fail += 1

def _fresh_db():
    from database.init_db import initialize_database
    from database.migrations import migrate_database
    from database.db_manager import DatabaseManager
    d = tempfile.mkdtemp()
    db = os.path.join(d, "h.db")
    initialize_database(db); migrate_database(db)
    return d, DatabaseManager(db)

def test_lease():
    from host.lease import read_lease, bump_lease
    d, dbm = _fresh_db()
    try:
        check("lease starts unseeded-or-zero", read_lease(dbm)[1] == 0, read_lease(dbm))
        t1 = bump_lease(dbm, "hostA")
        t2 = bump_lease(dbm, "hostB")
        check("lease term monotonic", t2 > t1, (t1, t2))
        hid, term = read_lease(dbm)
        check("lease records host + term", hid == "hostB" and term == t2, (hid, term))
        t3 = bump_lease(dbm, "hostC", min_term=100)
        check("lease honors min_term floor", t3 == 101, t3)
    finally:
        shutil.rmtree(d, ignore_errors=True)

if __name__ == "__main__":
    test_lease()
    print(f"\n{'ALL PASS' if _fail == 0 else str(_fail)+' FAILED'}")
    sys.exit(1 if _fail else 0)
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3.14 tests_failover.py`
Expected: FAIL — `host.lease` does not exist (ImportError), or migration missing.

- [ ] **Step 3: Add migration** in `database/migrations.py`, immediately before the final `conn.close()` of `migrate_database` (same place the `reserved_numbers` block lives), following that block's exact style:

```python
        # host_lease: single-row monotonic term for manual failover (Phase 3a)
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='host_lease'")
            if not cursor.fetchone():
                cursor.execute("""
                    CREATE TABLE host_lease (
                        id INTEGER PRIMARY KEY CHECK(id = 1),
                        host_id TEXT,
                        term INTEGER NOT NULL DEFAULT 0,
                        updated_at TEXT DEFAULT (datetime('now'))
                    )
                """)
                cursor.execute("INSERT OR IGNORE INTO host_lease (id, host_id, term) VALUES (1, NULL, 0)")
                conn.commit()
                messages.append("Created host_lease table")
        except Exception as e:
            messages.append(f"host_lease table skipped: {str(e)}")
```

- [ ] **Step 4: Create `host/lease.py`**

```python
"""Single-row monotonic host term. The term is the failover coordination
primitive: a promoted host bumps it, and any other host that sees a higher
term (via the heartbeat) steps down. Stored in each host's LOCAL DB."""


def read_lease(db_manager):
    rows = db_manager.execute_with_retry("SELECT host_id, term FROM host_lease WHERE id = 1")
    if not rows:
        return (None, 0)
    return (rows[0][0], rows[0][1])


def bump_lease(db_manager, host_id, min_term=0):
    """Set term = max(current, min_term) + 1, record host_id, return new term."""
    with db_manager.get_connection() as conn:
        row = conn.execute("SELECT term FROM host_lease WHERE id = 1").fetchone()
        current = row[0] if row else 0
        new_term = max(current, min_term) + 1
        conn.execute(
            "UPDATE host_lease SET host_id = ?, term = ?, updated_at = datetime('now') WHERE id = 1",
            (host_id, new_term))
    return new_term
```

- [ ] **Step 5: Run to verify it passes**

Run: `python3.14 tests_failover.py`
Expected: PASS all `lease ...` lines; `ALL PASS`.

- [ ] **Step 6: Commit**

```bash
git add database/migrations.py host/lease.py tests_failover.py
git commit -m "feat(3a): host_lease table + monotonic term helpers"
```

---

### Task 2: Heartbeat (write/read/staleness) + host emits it each loop

**Files:**
- Create: `host/heartbeat.py`
- Modify: `host/host_service.py` (identity + term in `__init__`; capture db_version in `publish_replica`; emit heartbeat in the loop)
- Test: `tests_failover.py`

**Interfaces:**
- Consumes: `host.lease.read_lease`.
- Produces:
  - `host.heartbeat.write_heartbeat(bus_dir, host_id, term, db_version, pid, hostname)` — atomic write of `host/heartbeat.json`.
  - `host.heartbeat.read_heartbeat(bus_dir) -> dict|None` (None on missing/torn).
  - `host.heartbeat.is_stale(hb, stale_seconds=60) -> bool` (True if `hb` is None or older than the threshold).
  - `HostService.__init__` now sets `self.host_id`, `self.hostname`, `self.pid`, `self.term` (read from the lease at construction), `self._db_version` (updated by `publish_replica`).
  - `HostService.publish_replica()` stores the version it wrote in `self._db_version`.
  - The serve loop calls `write_heartbeat(...)` after each `publish_replica`.

- [ ] **Step 1: Write the failing test** — add to `tests_failover.py` and register in `__main__`:

```python
def test_heartbeat():
    from host.heartbeat import write_heartbeat, read_heartbeat, is_stale
    from services.queue_transport import QueueTransport
    d = tempfile.mkdtemp()
    bus = os.path.join(d, "bus"); QueueTransport(bus)  # creates host/ + .tmp/
    try:
        check("no heartbeat -> stale", is_stale(read_heartbeat(bus)) is True)
        write_heartbeat(bus, "hostA", 3, 1234, 999, "PC1")
        hb = read_heartbeat(bus)
        check("heartbeat round-trips", hb["host_id"] == "hostA" and hb["term"] == 3 and hb["db_version"] == 1234, hb)
        check("fresh heartbeat not stale", is_stale(hb, stale_seconds=60) is False)
        old = dict(hb); old["epoch_ms"] = int(time.time() * 1000) - 120000
        check("old heartbeat is stale", is_stale(old, stale_seconds=60) is True)
    finally:
        shutil.rmtree(d, ignore_errors=True)
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3.14 tests_failover.py`
Expected: FAIL — `host.heartbeat` missing.

- [ ] **Step 3: Create `host/heartbeat.py`**

```python
"""Host liveness + term broadcast on the share. Clients and other hosts read
this to sense host-down and to detect a higher-term promotion."""
import os
import json
import time
import uuid


def write_heartbeat(bus_dir, host_id, term, db_version, pid, hostname):
    hb = {"host_id": host_id, "term": term, "db_version": db_version,
          "pid": pid, "hostname": hostname, "epoch_ms": int(time.time() * 1000)}
    dest = os.path.join(bus_dir, "host", "heartbeat.json")
    tmp = os.path.join(bus_dir, ".tmp", uuid.uuid4().hex + ".hb")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(hb, f)
    os.replace(tmp, dest)


def read_heartbeat(bus_dir):
    path = os.path.join(bus_dir, "host", "heartbeat.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def is_stale(hb, stale_seconds=60):
    if not hb:
        return True
    return (time.time() * 1000 - hb.get("epoch_ms", 0)) > stale_seconds * 1000
```

- [ ] **Step 4: Wire the host** in `host/host_service.py`.

Add imports at top: `import socket` and `from host.lease import read_lease`, `from host import heartbeat as hb`.

In `__init__`, after the existing assignments:
```python
        self.hostname = socket.gethostname()
        self.pid = os.getpid()
        self.host_id = f"{self.hostname}-{uuid.uuid4().hex[:8]}"
        _hid, self.term = read_lease(self.db)   # term this host serves under
        self._db_version = 0
```

In `publish_replica`, capture the version written. Change the version write so the value is stored:
```python
        version = int(time.time() * 1000)
        vtmp = os.path.join(self.bus, ".tmp", uuid.uuid4().hex + ".ver")
        with open(vtmp, "w") as f:
            f.write(str(version))
        os.replace(vtmp, os.path.join(self.bus, "replica", "version.txt"))
        self._db_version = version
```

In `serve_forever`, emit a heartbeat right after the initial publish and after each loop publish. Replace the loop body's publish/idle with heartbeat emission. The minimal change: add a helper and call it after `publish_replica()` in both `run_once` and the initial publish:
```python
    def _beat(self):
        hb.write_heartbeat(self.bus, self.host_id, self.term, self._db_version, self.pid, self.hostname)
```
Call `self._beat()` immediately after `self.publish_replica()` in `run_once` (after the existing publish call), and after the initial `self.publish_replica()` at the top of `serve_forever`. Also emit a heartbeat on each idle pass so liveness updates even with no commands — in `serve_forever`, when `run_once()` returns False, call `self._beat()` before `time.sleep(poll)`.

- [ ] **Step 5: Run to verify it passes**

Run: `python3.14 tests_failover.py && python3.14 tests_host_cluster.py`
Expected: failover PASS all `heartbeat ...`; cluster still 0 (heartbeat emission must not break the existing loop).

- [ ] **Step 6: Commit**

```bash
git add host/heartbeat.py host/host_service.py tests_failover.py
git commit -m "feat(3a): host heartbeat with term + db_version, emitted each loop"
```

---

### Task 3: Host startup hardening — integrity-check, sleep-guard, session timeout, periodic backup

**Files:**
- Create: `host/integrity.py`
- Create: `host/sleep_guard.py`
- Modify: `host/host_service.py` (`_resolve` timeout; a `startup()` method; periodic backup in the loop)
- Test: `tests_failover.py`

**Interfaces:**
- Produces:
  - `host.integrity.check_and_restore(db_path, backups_dir, log=None) -> (ok, message)` — runs `PRAGMA integrity_check`; if not `ok`, copies the newest `backups_dir/*.db` over `db_path` (atomic) and returns `(True, "restored ...")`; if integrity is fine returns `(True, "ok")`; if broken and no backup exists returns `(False, "integrity failed, no backup")`.
  - `host.sleep_guard.prevent_sleep()` — on Windows calls `SetThreadExecutionState(ES_CONTINUOUS|ES_SYSTEM_REQUIRED)`; elsewhere a no-op. Never raises.
  - `HostService.startup()` — runs integrity check/restore, `prevent_sleep()`, publishes initial replica + heartbeat. (Refactor of the top of `serve_forever`.)
  - `HostService._resolve(token)` — additionally returns `None` when the session's `last_seen` is older than `SESSION_TIMEOUT_SECONDS` (1800).
  - `HostService` periodic backup: every `BACKUP_EVERY_SECONDS` (default 300) the loop copies the DB to `backups/fiu_<epoch_ms>.db` (atomic) and keeps the newest `BACKUP_KEEP` (default 20).

- [ ] **Step 1: Write the failing test** — add to `tests_failover.py`, register in `__main__`:

```python
def test_integrity_and_session():
    from host.integrity import check_and_restore
    from database.init_db import initialize_database
    from database.migrations import migrate_database
    d = tempfile.mkdtemp()
    db = os.path.join(d, "h.db"); initialize_database(db); migrate_database(db)
    backups = os.path.join(d, "backups"); os.makedirs(backups)
    try:
        ok, msg = check_and_restore(db, backups)
        check("integrity ok on healthy db", ok and msg == "ok", msg)
        # make a good backup, then corrupt the db, then restore
        shutil.copyfile(db, os.path.join(backups, "fiu_1.db"))
        with open(db, "wb") as f:
            f.write(b"this is not a sqlite file at all, totally corrupt")
        ok2, msg2 = check_and_restore(db, backups)
        check("corrupt db restored from backup", ok2 and "restored" in msg2.lower(), msg2)
        # restored db is usable again
        ok3, _ = check_and_restore(db, backups)
        check("restored db passes integrity", ok3)
    finally:
        shutil.rmtree(d, ignore_errors=True)

def test_session_timeout():
    from host.host_service import HostService
    from services.queue_transport import QueueTransport
    from database.init_db import initialize_database
    from database.migrations import migrate_database
    from database.db_manager import DatabaseManager
    d = tempfile.mkdtemp()
    db = os.path.join(d, "h.db"); initialize_database(db); migrate_database(db)
    dbm = DatabaseManager(db)
    bus = os.path.join(d, "bus")
    class _A: pass
    host = HostService({"auth_service": _A()}, dbm, QueueTransport(bus), bus)
    try:
        host._sessions["tok"] = {"user_id": 1, "username": "u", "role": "admin", "last_seen": time.time()}
        check("fresh session resolves", host._resolve("tok") is not None)
        host._sessions["tok"]["last_seen"] = time.time() - 4000  # >30 min
        check("idle session expires", host._resolve("tok") is None)
    finally:
        shutil.rmtree(d, ignore_errors=True)
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3.14 tests_failover.py`
Expected: FAIL — `host.integrity` missing; session does not expire.

- [ ] **Step 3: Create `host/integrity.py`**

```python
"""Startup self-heal: verify the local DB, restore the newest backup if broken."""
import os
import glob
import uuid
import shutil
import sqlite3


def _newest_backup(backups_dir):
    files = glob.glob(os.path.join(backups_dir, "*.db"))
    if not files:
        return None
    return max(files, key=os.path.getmtime)


def check_and_restore(db_path, backups_dir, log=None):
    def _ok():
        try:
            conn = sqlite3.connect(db_path)
            try:
                row = conn.execute("PRAGMA integrity_check").fetchone()
                return bool(row) and row[0] == "ok"
            finally:
                conn.close()
        except sqlite3.DatabaseError:
            return False

    if _ok():
        return True, "ok"
    newest = _newest_backup(backups_dir)
    if not newest:
        if log: log.error("Integrity check FAILED and no backup to restore from")
        return False, "integrity failed, no backup"
    tmp = db_path + ".restore-" + uuid.uuid4().hex
    shutil.copyfile(newest, tmp)
    os.replace(tmp, db_path)
    # drop any stale WAL sidecars from the broken db
    for sfx in ("-wal", "-shm"):
        try:
            os.remove(db_path + sfx)
        except OSError:
            pass
    if log: log.warning(f"Integrity check failed; restored from {os.path.basename(newest)}")
    return True, f"restored from {os.path.basename(newest)}"
```

- [ ] **Step 4: Create `host/sleep_guard.py`**

```python
"""Keep the host PC awake without admin rights (userspace flag)."""
import sys

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001


def prevent_sleep():
    if not sys.platform.startswith("win"):
        return
    try:
        import ctypes
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
    except Exception:
        pass  # best-effort; never block host startup on this
```

- [ ] **Step 5: Wire the host** in `host/host_service.py`.

Add module constants near the top of the class or file:
```python
SESSION_TIMEOUT_SECONDS = 1800
BACKUP_EVERY_SECONDS = 300
BACKUP_KEEP = 20
```

`_resolve` gains a timeout check:
```python
    def _resolve(self, token):
        s = self._sessions.get(token)
        if not s:
            return None
        if time.time() - s["last_seen"] > SESSION_TIMEOUT_SECONDS:
            self._sessions.pop(token, None)
            return None
        s["last_seen"] = time.time()
        return {"user_id": s["user_id"], "username": s["username"], "role": s["role"]}
```

Add a `startup()` method and a periodic-backup helper, and call them from `serve_forever`:
```python
    def startup(self):
        from host.integrity import check_and_restore
        from host.sleep_guard import prevent_sleep
        backups_dir = os.path.join(self.bus, "backups")
        ok, msg = check_and_restore(self.db.db_path, backups_dir)
        print(f"[HOST] integrity: {msg}")
        prevent_sleep()
        self.publish_replica()
        self._beat()
        self._last_backup = 0.0

    def _maybe_backup(self):
        now = time.time()
        if now - getattr(self, "_last_backup", 0.0) < BACKUP_EVERY_SECONDS:
            return
        self._last_backup = now
        try:
            backups_dir = os.path.join(self.bus, "backups")
            dest = os.path.join(backups_dir, f"fiu_{int(now * 1000)}.db")
            tmp = os.path.join(self.bus, ".tmp", uuid.uuid4().hex + ".bak")
            src = sqlite3.connect(self.db.db_path); dst = sqlite3.connect(tmp)
            try:
                with dst:
                    src.backup(dst)
                dst.execute("PRAGMA journal_mode=DELETE")
            finally:
                dst.close(); src.close()
            os.replace(tmp, dest)
            # prune to newest BACKUP_KEEP
            import glob
            files = sorted(glob.glob(os.path.join(backups_dir, "*.db")), key=os.path.getmtime, reverse=True)
            for old in files[BACKUP_KEEP:]:
                try: os.remove(old)
                except OSError: pass
        except Exception as e:
            print(f"[HOST][WARN] backup failed: {e}")
```
In `serve_forever`, replace the initial `self.publish_replica()` with `self.startup()`, and call `self._maybe_backup()` once per loop iteration (e.g. right after `self._beat()` on the idle path and after a processed command).

- [ ] **Step 6: Run to verify it passes**

Run: `python3.14 tests_failover.py && python3.14 tests_host_cluster.py`
Expected: failover PASS all `integrity ...`/`session ...`; cluster still 0.

- [ ] **Step 7: Commit**

```bash
git add host/integrity.py host/sleep_guard.py host/host_service.py tests_failover.py
git commit -m "feat(3a): host startup hardening — integrity-restore, sleep-guard, session timeout, periodic backup"
```

---

### Task 4: Term step-down guard (never two writers)

**Files:**
- Modify: `host/host_service.py` (`serve_forever` checks the shared heartbeat each pass; a `StepDown` sentinel)
- Test: `tests_failover.py`

**Interfaces:**
- Consumes: `host.heartbeat.read_heartbeat`, `self.term`, `self.host_id`.
- Produces:
  - `HostService.should_step_down() -> bool` — True when the shared heartbeat shows a DIFFERENT host with a term strictly greater than `self.term`.
  - `serve_forever` returns (stops serving) as soon as `should_step_down()` is True, logging the reason. It must check this BEFORE emitting its own heartbeat each pass (so a woken old host retires instead of clobbering the new host's heartbeat).

- [ ] **Step 1: Write the failing test** — add to `tests_failover.py`, register in `__main__`:

```python
def test_step_down():
    from host.host_service import HostService
    from host.heartbeat import write_heartbeat
    from services.queue_transport import QueueTransport
    from database.init_db import initialize_database
    from database.migrations import migrate_database
    from database.db_manager import DatabaseManager
    from host.lease import bump_lease
    d = tempfile.mkdtemp()
    db = os.path.join(d, "h.db"); initialize_database(db); migrate_database(db)
    dbm = DatabaseManager(db)
    bus = os.path.join(d, "bus"); QueueTransport(bus)
    class _A: pass
    host = HostService({"auth_service": _A()}, dbm, QueueTransport(bus), bus)
    host.term = 1
    try:
        check("no rival -> stay", host.should_step_down() is False)
        write_heartbeat(bus, host.host_id, 5, 0, 1, "self")  # same host, higher term -> not a rival
        check("own higher heartbeat -> stay", host.should_step_down() is False)
        write_heartbeat(bus, "OTHER-HOST", 2, 0, 1, "PC2")   # different host, higher term
        check("rival higher term -> step down", host.should_step_down() is True)
        write_heartbeat(bus, "OTHER-HOST", 1, 0, 1, "PC2")   # different host, equal term
        check("rival equal term -> stay", host.should_step_down() is False)
    finally:
        shutil.rmtree(d, ignore_errors=True)
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3.14 tests_failover.py`
Expected: FAIL — `should_step_down` missing.

- [ ] **Step 3: Implement** in `host/host_service.py`:

```python
    def should_step_down(self) -> bool:
        beat = hb.read_heartbeat(self.bus)
        if not beat:
            return False
        return beat.get("host_id") != self.host_id and beat.get("term", 0) > self.term
```

In `serve_forever`, at the TOP of each loop iteration (before claiming/serving and before emitting the heartbeat), check and bail:
```python
    def serve_forever(self, poll: float = 0.1):
        self.startup()
        while True:
            if self.should_step_down():
                print(f"[HOST] stepping down: a newer term holds the lease (mine={self.term})")
                return
            try:
                if not self.run_once():
                    self._beat(); self._maybe_backup()
                    time.sleep(poll)
                else:
                    self._maybe_backup()
            except Exception as e:
                print(f"[HOST][ERROR] run_once failed, continuing: {e}")
                time.sleep(poll)
```
(`run_once` still publishes + beats after a processed command as wired in Task 2/3.)

- [ ] **Step 4: Run to verify it passes**

Run: `python3.14 tests_failover.py && python3.14 tests_host_cluster.py`
Expected: failover PASS all `step down`/`stay`; cluster still 0.

- [ ] **Step 5: Commit**

```bash
git add host/host_service.py tests_failover.py
git commit -m "feat(3a): term step-down guard — host retires on a rival higher term"
```

---

### Task 5: Become Host (manual failover)

**Files:**
- Create: `host/failover.py`
- Test: `tests_failover.py`

**Interfaces:**
- Consumes: `host.heartbeat.read_heartbeat`/`is_stale`, `host.lease.bump_lease`, `services.queue_transport` dir layout.
- Produces:
  - `host.failover.become_host(bus_dir, local_db_path, host_id, stale_seconds=60, force=False) -> (ok, message, new_term)`:
    1. If a heartbeat exists, is NOT stale, and `force` is False → refuse: `(False, "A live host holds the lease (term N)", None)`.
    2. Adopt the newest replica: copy `bus_dir/replica/fiu_ro.db` → `local_db_path` (atomic temp+replace; clean `-wal`/`-shm` sidecars). If no replica exists → `(False, "no replica to adopt", None)`.
    3. Re-queue in-flight commands: move every `bus_dir/queue/processing/*.json` back to `bus_dir/queue/pending/` (atomic per file) so the new host re-claims and applies them (idempotent by `id`).
    4. Bump the term in the adopted DB: `new_term = bump_lease(DatabaseManager(local_db_path), host_id, min_term=(hb term or 0))`.
    5. Write a heartbeat under the new host_id + new_term.
    6. Return `(True, "promoted to host (term N)", new_term)`. The caller then builds services against `local_db_path`, constructs `HostService` (whose `__init__` reads the bumped term), and calls `serve_forever()`.

- [ ] **Step 1: Write the failing test** — add to `tests_failover.py`, register in `__main__`:

```python
def test_become_host():
    from host.failover import become_host
    from host.heartbeat import write_heartbeat, read_heartbeat
    from services.queue_transport import QueueTransport
    from database.init_db import initialize_database
    from database.migrations import migrate_database
    d = tempfile.mkdtemp()
    bus = os.path.join(d, "bus"); QueueTransport(bus)

    # Publish a real replica (host DB) so there is something to adopt.
    hostdb = os.path.join(d, "orig_host.db"); initialize_database(hostdb); migrate_database(hostdb)
    # emulate publish_replica output: a DELETE-mode copy at replica/fiu_ro.db
    src = sqlite3.connect(hostdb); dst = sqlite3.connect(os.path.join(bus, "replica", "fiu_ro.db"))
    with dst: src.backup(dst)
    dst.execute("PRAGMA journal_mode=DELETE"); dst.close(); src.close()

    # a stale in-flight command sitting in processing/
    with open(os.path.join(bus, "queue", "processing", "0000000000001_abc.json"), "w") as f:
        json.dump({"id": "abc", "command": "noop"}, f)

    local = os.path.join(d, "backup_pc.db")
    try:
        # live host present -> refuse
        write_heartbeat(bus, "LIVE-HOST", 4, 0, 1, "PC1")
        ok, msg, _ = become_host(bus, local, "BACKUP-PC", stale_seconds=60, force=False)
        check("refuses while a live host holds lease", ok is False, msg)

        # host goes stale -> promote
        stale = read_heartbeat(bus); stale["epoch_ms"] -= 120000
        with open(os.path.join(bus, "host", "heartbeat.json"), "w") as f: json.dump(stale, f)
        ok2, msg2, term2 = become_host(bus, local, "BACKUP-PC", stale_seconds=60, force=False)
        check("promotes on stale heartbeat", ok2 and term2 == 5, (ok2, msg2, term2))
        check("adopted replica exists locally", os.path.exists(local))
        check("in-flight command re-queued to pending",
              any(n.endswith("_abc.json") for n in os.listdir(os.path.join(bus, "queue", "pending"))))
        check("processing drained", os.listdir(os.path.join(bus, "queue", "processing")) == [])
        hb = read_heartbeat(bus)
        check("new heartbeat carries new host + term", hb["host_id"] == "BACKUP-PC" and hb["term"] == 5, hb)
    finally:
        shutil.rmtree(d, ignore_errors=True)
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3.14 tests_failover.py`
Expected: FAIL — `host.failover` missing.

- [ ] **Step 3: Create `host/failover.py`**

```python
"""Manual confirmed promotion — no election race. A designated backup adopts
the newest replica, re-queues in-flight commands, and bumps the term so the
old host (if it wakes) steps down."""
import os
import uuid
import shutil

from host.heartbeat import read_heartbeat, is_stale, write_heartbeat
from host.lease import bump_lease


def _atomic_copy(src, dst):
    tmp = dst + ".tmp-" + uuid.uuid4().hex
    shutil.copyfile(src, tmp)
    os.replace(tmp, dst)
    for sfx in ("-wal", "-shm"):
        try:
            os.remove(dst + sfx)
        except OSError:
            pass


def become_host(bus_dir, local_db_path, host_id, stale_seconds=60, force=False):
    hb = read_heartbeat(bus_dir)
    if hb and not is_stale(hb, stale_seconds) and not force:
        return False, f"A live host holds the lease (term {hb.get('term', 0)})", None

    replica = os.path.join(bus_dir, "replica", "fiu_ro.db")
    if not os.path.exists(replica):
        return False, "no replica to adopt", None
    _atomic_copy(replica, local_db_path)

    # re-queue anything the dead host had claimed but not completed
    proc = os.path.join(bus_dir, "queue", "processing")
    pend = os.path.join(bus_dir, "queue", "pending")
    for name in list(os.listdir(proc)):
        if name.endswith(".json"):
            try:
                os.replace(os.path.join(proc, name), os.path.join(pend, name))
            except OSError:
                pass

    from database.db_manager import DatabaseManager
    dbm = DatabaseManager(local_db_path)
    prior_term = hb.get("term", 0) if hb else 0
    new_term = bump_lease(dbm, host_id, min_term=prior_term)

    import socket
    write_heartbeat(bus_dir, host_id, new_term, 0, os.getpid(), socket.gethostname())
    return True, f"promoted to host (term {new_term})", new_term
```

- [ ] **Step 4: Run to verify it passes**

Run: `python3.14 tests_failover.py`
Expected: PASS all `become_host`/promote/re-queue lines.

- [ ] **Step 5: Commit**

```bash
git add host/failover.py tests_failover.py
git commit -m "feat(3a): become_host manual failover — adopt replica, re-queue in-flight, bump term"
```

---

### Task 6: Client outbox + drain (G2 stable ids, exactly-once while host down)

**Files:**
- Create: `services/outbox.py`
- Modify: `services/remote_gateway.py` (`RemoteGateway` optional outbox: queue-on-timeout, `drain()`)
- Test: `tests_failover.py`

**Interfaces:**
- Produces:
  - `services.outbox.Outbox(dir)` with `add(command)` (atomic write keyed by `command["id"]`), `pending() -> list[dict]` (oldest first), `remove(command_id)`.
  - `RemoteGateway(transport, timeout=30.0, outbox=None)`. When an `outbox` is set and `call()` times out, the command (WITH its already-generated `id`) is persisted to the outbox and a `HostOfflineError` is raised (a distinct subclass of `RemoteError`) — the id is NOT regenerated, so a later resubmit is idempotent (this is G2).
  - `RemoteGateway.drain() -> (sent, remaining)` — resubmits each outbox command **verbatim (same id)**, awaits a short response, removes it on success; returns counts. Applied exactly once because the host's `applied_commands` ledger dedups the stable id.

- [ ] **Step 1: Write the failing test** — add to `tests_failover.py`, register in `__main__`:

```python
def test_outbox_drain_exactly_once():
    from services.queue_transport import QueueTransport
    from services.remote_gateway import RemoteGateway, HostOfflineError
    from services.outbox import Outbox
    from host.host_service import HostService
    from database.init_db import initialize_database
    from database.migrations import migrate_database
    from database.db_manager import DatabaseManager
    import threading, bcrypt
    d = tempfile.mkdtemp()
    db = os.path.join(d, "h.db"); initialize_database(db); migrate_database(db)
    dbm = DatabaseManager(db)
    pw = bcrypt.hashpw(b"Admin@1234", bcrypt.gensalt()).decode()
    c = sqlite3.connect(db)
    c.execute("INSERT INTO users (username,password,full_name,role,is_active,created_by) "
              "VALUES ('admin',?,'Admin','admin',1,'SYSTEM') ON CONFLICT(username) DO UPDATE SET password=excluded.password", (pw,))
    c.commit(); c.close()
    bus = os.path.join(d, "bus")
    ob = Outbox(os.path.join(d, "outbox"))

    # host DOWN: a write times out and is queued (stable id, HostOfflineError)
    gw = RemoteGateway(QueueTransport(bus), timeout=0.3, outbox=ob)
    # log in requires a host; with none, login also times out -> simulate a token directly
    gw.token = "pretend"  # drain re-sends; host will reject auth, so use a no-auth command path:
    raised = False
    try:
        gw.call("auth_service.create_user", ["u1", "p", "U One", "agent"], {})
    except HostOfflineError:
        raised = True
    check("host-down write raises HostOffline + queues", raised and len(ob.pending()) == 1)
    queued_id = ob.pending()[0]["id"]

    # bring host UP and give the gateway a real admin token
    class _Svc(dict): pass
    from services.logging_service import LoggingService
    from services.auth_service import AuthService
    log = LoggingService(dbm, None)
    services = {"auth_service": AuthService(dbm, log)}
    host = HostService(services, dbm, QueueTransport(bus), bus)
    stop = threading.Event()
    def run():
        host.startup()
        while not stop.is_set():
            if not host.run_once():
                time.sleep(0.02)
    th = threading.Thread(target=run, daemon=True); th.start()
    try:
        ok, _u, _m = gw.login("admin", "Admin@1234")
        check("login once host is up", ok)
        # the queued create_user carries no token; drain resends verbatim. Give it the token:
        pend = ob.pending()[0]; pend["token"] = gw.token; ob.add(pend)
        sent, remaining = gw.drain()
        check("drain sends the queued command", sent == 1 and remaining == 0)
        n = dbm.execute_with_retry("SELECT COUNT(*) FROM users WHERE username='u1'")[0][0]
        check("queued write applied exactly once", n == 1, n)
        check("same id kept (idempotent)", ob.pending() == [] and queued_id)
    finally:
        stop.set(); th.join(timeout=2.0); shutil.rmtree(d, ignore_errors=True)
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3.14 tests_failover.py`
Expected: FAIL — `services.outbox` / `HostOfflineError` missing.

- [ ] **Step 3: Create `services/outbox.py`**

```python
"""Client-side durable queue for writes made while the host is down. Each
command is stored under its STABLE id, so re-submitting it is idempotent."""
import os
import json
import uuid


class Outbox:
    def __init__(self, dir_path):
        self.dir = dir_path
        os.makedirs(self.dir, exist_ok=True)

    def add(self, command):
        cid = command["id"]
        dest = os.path.join(self.dir, cid + ".json")
        tmp = os.path.join(self.dir, "." + uuid.uuid4().hex + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(command, f, default=str)
        os.replace(tmp, dest)

    def pending(self):
        out = []
        for name in sorted(n for n in os.listdir(self.dir) if n.endswith(".json")):
            try:
                with open(os.path.join(self.dir, name), "r", encoding="utf-8") as f:
                    out.append(json.load(f))
            except (OSError, json.JSONDecodeError):
                pass
        return out

    def remove(self, command_id):
        try:
            os.remove(os.path.join(self.dir, command_id + ".json"))
        except OSError:
            pass
```

- [ ] **Step 4: Modify `services/remote_gateway.py`**

Add `HostOfflineError(RemoteError)`, thread an optional `outbox`, and add `drain()`. `call()` builds the command dict once (stable id) and, on timeout with an outbox present, persists it and raises `HostOfflineError`:

```python
class HostOfflineError(RemoteError):
    pass


class RemoteGateway:
    def __init__(self, transport, timeout: float = 30.0, outbox=None):
        self.t = transport
        self.timeout = timeout
        self.token = None
        self.outbox = outbox

    # login() unchanged ...

    def call(self, command_name, args, kwargs):
        cid = uuid.uuid4().hex
        command = {"id": cid, "command": command_name,
                   "args": list(args), "kwargs": dict(kwargs), "token": self.token}
        self.t.submit(command)
        try:
            resp = self.t.await_response(cid, timeout=self.timeout)
        except TimeoutError:
            if self.outbox is not None:
                self.outbox.add(command)            # SAME id — idempotent resubmit
                raise HostOfflineError("Host offline — write queued, will sync when a host returns")
            raise
        if not resp.get("ok"):
            raise RemoteError(resp.get("error", "command failed"))
        return resp["result"]

    def drain(self):
        """Resubmit queued commands verbatim (same id); remove on success."""
        if self.outbox is None:
            return (0, 0)
        sent = 0
        for command in self.outbox.pending():
            self.t.submit(command)
            try:
                resp = self.t.await_response(command["id"], timeout=self.timeout)
            except TimeoutError:
                break  # host went away mid-drain; leave the rest queued
            if resp.get("ok"):
                self.outbox.remove(command["id"])
                sent += 1
            else:
                # host rejected it (business/auth) — remove so it doesn't wedge the queue
                self.outbox.remove(command["id"])
                sent += 1
        return (sent, len(self.outbox.pending()))
```

- [ ] **Step 5: Run to verify it passes**

Run: `python3.14 tests_failover.py && python3.14 tests_host_cluster.py`
Expected: failover PASS all (incl. `queued write applied exactly once`); cluster still 0.

- [ ] **Step 6: Commit**

```bash
git add services/outbox.py services/remote_gateway.py tests_failover.py
git commit -m "feat(3a): client outbox + drain — G2 stable ids, exactly-once while host down"
```

---

## Deferred to Phase 3b (not in this plan)

- **`--panel` operator Control Panel** (§3.5a): setup, host designation via `config.json`, live monitoring (heartbeat/queue depth), one-click "Become Host"/"Step Down", maintenance (integrity/backup/restore).
- **Client host-down UI banner** + wiring the outbox/drain into the running Flet client (this plan builds and tests the mechanism headlessly; the banner + a drain loop on the client's refresher thread are UI work).
- **Host step-down → relaunch as client** (this plan stops serving on step-down; turning that into an automatic in-app demotion is UI work).
- **Autostart** (Startup-folder script) + `docs/HOST_RUNBOOK.md`.
- **Exactly-once crash-window**: collapsing the service write and the `applied_commands` INSERT into one transaction (today's fallback remains DB uniqueness constraints; manual failover replay is idempotent by id but a host crash exactly between the service commit and the ledger INSERT is the residual window — documented, low-volume, rare). Related: exactly-once for a NON-atomic service method (one that runs several separate transactions and could raise after committing part) rests on a codebase convention (methods self-catch to `(False,msg)`, or use idempotent `WHERE` clauses like `transfer_numbers`), not a structural guarantee — a future `WRITE_COMMANDS` entry that raises uncaught after a real commit could double-apply on resubmit. Enforce structurally when the one-txn collapse lands.
- **Simultaneous-promotion two-writer window** (out of the operational model): the term step-down is convergent, not an instantaneous mutual-exclusion. If two operators promote two different backups at the same moment, both reach `prior_term+1` (equal terms) and can both pass the initial gate for a bounded (~1 poll) window before the lower-`host_id` loser reads the winner's heartbeat and retires. This is not corruption (each host writes only its own local DB; the shared queue is idempotent by command id, so the divergence reconciles), and it is outside the spec's operational model (failover is **single-operator, manual, confirmed** — §3.5). Hard mutual exclusion is architecturally unavailable in this locked org (no lock server; SMB byte-range locking is precisely what this design avoids). If concurrent promotion ever becomes a real risk, add a write-then-reread confirmation in `become_host` (abort if a higher-priority rival appeared) — it narrows but cannot fully close the window without infra-level coordination.
- **Outbox stale-response race** (needs `queue_transport` changes, so out of Phase-3a scope): `RemoteGateway.call()`'s timeout path leaves the original command in `queue/pending`, and `responses/<id>.json` is keyed only by command id with no per-attempt correlation. If a returning host answers that abandoned copy before `drain()` resubmits, `drain()` can read the stale response — the ledger still prevents any double-apply of the write, and the outbox self-heals on the next drain (the ledger re-emits the real `ok=True` response), but `drain()`'s per-call `sent`/`remaining` counts are momentarily unreliable. Fix with per-attempt response correlation (attempt token in the response filename) when the client drain loop is wired into the UI (3b).

## Self-Review

- **Spec coverage:** heartbeat+term (§3.3, T2) ✓; integrity-check-on-start + restore (§3.3.1, T3) ✓; sleep-guard (§3.3.2, T3) ✓; periodic backups (§3.3.4, T3) ✓; session timeout R3 (§7b, T3) ✓; term step-down / no-two-writers (§3.5, T4) ✓; Become Host adopt+replay+term (§3.5, T5) ✓; G2 stable ids + host-down queueing exactly-once (§3.4, §7b G2, T6) ✓.
- **Placeholder scan:** every code step carries real, runnable code; the one "wire into serve_forever" instruction shows the full rewritten loop.
- **Type consistency:** `read_lease`→`(host_id, term)`; `bump_lease(...)->int`; `read_heartbeat`→`dict|None`; `is_stale(hb, stale_seconds)`; `become_host(...)->(ok,msg,new_term)`; `check_and_restore(...)->(ok,msg)`; `RemoteGateway(transport, timeout, outbox)`, `drain()->(sent,remaining)`, `HostOfflineError(RemoteError)`. All consistent across tasks.
- **Single-writer invariant:** T4 step-down checks the rival term BEFORE emitting its own heartbeat; T5 bumps strictly above the prior term; T6 reuses the stable id so replay never double-applies. No path lets two hosts apply writes to the same client population without the lower-term one retiring.
