# Phase 2 — Reservation Redesign (owned, transferable, pre-allocated number blocks)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Replace the at-add-time report-number reservation with pre-allocated **owned, non-expiring, transferable blocks**. Users reserve a block up front; creating a report auto-consumes their next available number; the Add-Report path is gated (no number → reserve first). Removes gate G3 (raw SQL in the reservation dialog) and the whole expiry/gap/pool/cleanup machinery.

**Design source:** `docs/DECISIONS.md` ADR-007 + `docs/superpowers/specs/2026-07-16-single-writer-host-architecture-design.md` §3.6.

**Architecture:** Additive first — a new `reserved_numbers` table + new service methods, then switch `create_report` and the reservation UI onto them, then delete the dead old machinery. The host serializes everything (Phase 1), so no locking is needed here; correctness comes from single-writer + one transaction per command.

**Tech Stack:** Python 3.14, stdlib sqlite3. No new deps.

## Global Constraints

- **Run everything with `python3.14`** (never `python3`). macOS has **no `timeout`** command.
- **No new dependencies.**
- **Owned blocks, NO expiry, transferable.** A reserved number stays the user's until used or transferred. No time-based expiry, no cleanup thread.
- **Numbering stays gap-safe within the host's serialized allocation** — allocation is sequential per active numbering month (respects `close_month`, R50/R51, unchanged).
- **The host is the single writer** (Phase 1). These service methods run host-side inside one transaction per command; do not add locks or threads.
- **Regression gate:** after each task, the suites stay green — `tests_host_cluster.py` (CLUSTER FAILURES 0), `tests_conformance.py` (Conformance N/N), `tests_e2e_harness.py` (180/180 — will be updated in Task 6 for the new model), `tests_prosecutor.py` (0/35), `tests_ui_driver.py` (0/NN).
- Tests are plain scripts (`python3.14 tests_X.py`).

## File Structure

- Modify `database/migrations.py` — Migration 34: `reserved_numbers` table.
- Modify `services/report_number_service.py` — add the new block methods; later remove dead old ones.
- Modify `services/report_service.py` — `create_report` gate + consume.
- Modify `services/command_registry.py` — add new reserve/transfer commands; drop removed ones.
- Modify `flet_app/dialogs/reservation_dialog.py` — rewrite: reserve N / my numbers / transfer; remove raw SQL (G3).
- Modify `flet_app/dialogs/report_dialog.py` — add-report gate (block + message when no available number).
- Modify `tests_e2e_harness.py`, `tests_conformance.py`, `tests_host_cluster.py` — new-model reservation checks.

---

### Task 1: `reserved_numbers` table (Migration 34)

**Files:**
- Modify: `database/migrations.py` (add before final `conn.close()`)
- Test: `tests_host_cluster.py` (extend)

**Interfaces:**
- Produces: table `reserved_numbers(id INTEGER PK AUTOINCREMENT, report_number TEXT UNIQUE NOT NULL, serial_number INTEGER UNIQUE NOT NULL, owned_by TEXT NOT NULL, status TEXT CHECK(status IN ('available','used')) DEFAULT 'available', used_by_report_id INTEGER, reserved_at TEXT DEFAULT (datetime('now')), transferred_from TEXT)` + indexes on `(owned_by, status)` and `report_number`.

- [ ] **Step 1: Write the failing test**

Add to `tests_host_cluster.py` (before `__main__`):

```python
def test_reserved_numbers_table():
    import sqlite3
    from database.init_db import initialize_database
    from database.migrations import migrate_database
    box = tempfile.mkdtemp()
    try:
        db = os.path.join(box, 'r.db')
        initialize_database(db); migrate_database(db)
        cols = {r[1] for r in sqlite3.connect(db).execute("PRAGMA table_info(reserved_numbers)")}
        need = {'id','report_number','serial_number','owned_by','status','used_by_report_id','reserved_at','transferred_from'}
        check('P2T1 reserved_numbers table exists', need <= cols, cols)
    finally:
        shutil.rmtree(box, ignore_errors=True)
```
Call it in `__main__`.

- [ ] **Step 2: Run to verify it fails**

Run: `cd /Users/engammar/Scripts/STR && python3.14 tests_host_cluster.py`
Expected: FAIL on `P2T1 reserved_numbers table exists`.

- [ ] **Step 3: Add Migration 34**

In `database/migrations.py`, before the final `conn.close()`:

```python
        # Migration 34: owned, transferable, non-expiring reserved number blocks (Phase 2)
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='reserved_numbers'")
            if not cursor.fetchone():
                cursor.execute("""
                    CREATE TABLE reserved_numbers (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        report_number TEXT UNIQUE NOT NULL,
                        serial_number INTEGER UNIQUE NOT NULL,
                        owned_by TEXT NOT NULL,
                        status TEXT CHECK(status IN ('available','used')) DEFAULT 'available',
                        used_by_report_id INTEGER,
                        reserved_at TEXT DEFAULT (datetime('now')),
                        transferred_from TEXT
                    )
                """)
                cursor.execute("CREATE INDEX idx_reserved_owner_status ON reserved_numbers(owned_by, status)")
                cursor.execute("CREATE INDEX idx_reserved_number ON reserved_numbers(report_number)")
                conn.commit()
                messages.append("Created reserved_numbers table")
        except Exception as e:
            messages.append(f"reserved_numbers table skipped: {str(e)}")
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd /Users/engammar/Scripts/STR && python3.14 tests_host_cluster.py` → `CLUSTER FAILURES: 0`

- [ ] **Step 5: Regression + commit**

Run: `python3.14 tests_conformance.py 2>/dev/null | grep Conformance` (migrations still idempotent).

```bash
git add database/migrations.py tests_host_cluster.py
git commit -m "feat(reservation): reserved_numbers table (migration 34)"
```

---

### Task 2: New block-reservation service methods

**Files:**
- Modify: `services/report_number_service.py` (add new methods; leave old ones for now)
- Test: `tests_host_cluster.py` (extend)

**Interfaces:**
- Consumes: the existing `_generate_next_numbers(cursor)` / `_active_month(cursor)` for sequential allocation, and `db_manager`.
- Produces (all run host-side in one transaction each):
  - `reserve_block(username: str, count: int) -> Tuple[bool, list, str]` — allocate the next `count` sequential numbers to `username` as `available`. `count` clamped to [1, 100]. Returns (ok, list_of_report_numbers, msg).
  - `get_available_numbers(username: str) -> List[Dict]` — this user's `available` numbers, ascending.
  - `get_available_count(username: str) -> int`.
  - `consume_next_available(username: str, report_id: int) -> Tuple[bool, Optional[str], str]` — flip the user's lowest `available` number to `used`, link `used_by_report_id=report_id`. Returns (ok, report_number, msg). Used by create_report inside the same transaction.
  - `transfer_numbers(from_user: str, to_user: str, report_numbers: list) -> Tuple[bool, str]` — reassign `owned_by` for the given `available` numbers (must currently be owned by `from_user`), set `transferred_from=from_user`. `to_user` must be an active user.

- [ ] **Step 1: Write the failing test**

Add to `tests_host_cluster.py`:

```python
def test_block_reservation():
    box = tempfile.mkdtemp()
    try:
        host, t, dbm = _build_host(box)
        nums = host.services['report_number_service']
        ok, block, msg = nums.reserve_block('ali', 5)
        check('P2T2 reserve_block allocates 5', ok and len(block) == 5, msg)
        check('P2T2 available count = 5', nums.get_available_count('ali') == 5)
        # consume lowest
        ok, rn, _ = nums.consume_next_available('ali', 999)
        check('P2T2 consume returns a number', ok and rn == block[0], (rn, block[0]))
        check('P2T2 available now 4', nums.get_available_count('ali') == 4)
        import sqlite3
        row = sqlite3.connect(dbm.db_path).execute(
            "SELECT status, used_by_report_id FROM reserved_numbers WHERE report_number=?", (rn,)).fetchone()
        check('P2T2 consumed marked used+linked', row[0] == 'used' and row[1] == 999, row)
        # transfer 2 of ali's remaining to sara (seed sara active)
        dbm.execute_with_retry("INSERT INTO users (username,password,full_name,role,is_active,created_by) "
                               "VALUES ('sara','x','Sara','agent',1,'admin')")
        remaining = [r['report_number'] for r in nums.get_available_numbers('ali')]
        okt, mt = nums.transfer_numbers('ali', 'sara', remaining[:2])
        check('P2T2 transfer ok', okt, mt)
        check('P2T2 sara has 2', nums.get_available_count('sara') == 2)
        check('P2T2 ali has 2', nums.get_available_count('ali') == 2)
        # cannot transfer numbers you do not own
        okbad, _ = nums.transfer_numbers('ali', 'sara', ['9999/99/999'])
        check('P2T2 cannot transfer unowned', not okbad)
        check('P2T2 report_numbers are unique', dbm.execute_with_retry(
            "SELECT report_number,COUNT(*) c FROM reserved_numbers GROUP BY report_number HAVING c>1") == [])
    finally:
        shutil.rmtree(box, ignore_errors=True)
```
Call it in `__main__`.

- [ ] **Step 2: Run to verify it fails**

Run: `python3.14 tests_host_cluster.py`
Expected: FAIL — `AttributeError: 'ReportNumberService' object has no attribute 'reserve_block'`.

- [ ] **Step 3: Implement the methods**

Add to `services/report_number_service.py` (inside the class). Use a single connection/transaction per method (mirror the existing `_generate_next_numbers`/`reserve_batch_numbers` connection pattern already in the file — open `sqlite3.connect(self.db_manager.db_path)`, `BEGIN`, allocate, commit). Reference implementation:

```python
    def reserve_block(self, username, count):
        try:
            count = int(count)
        except (TypeError, ValueError):
            return False, [], "Invalid count"
        if count < 1 or count > 100:
            return False, [], "Count must be between 1 and 100"
        conn = sqlite3.connect(self.db_manager.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("BEGIN IMMEDIATE")
            allocated = []
            for _ in range(count):
                report_number, serial_number = self._generate_next_numbers(cursor)
                cursor.execute(
                    "INSERT INTO reserved_numbers (report_number, serial_number, owned_by, status) "
                    "VALUES (?, ?, ?, 'available')", (report_number, serial_number, username))
                allocated.append(report_number)
            conn.commit()
            self.logger.info(f"Reserved block of {count} numbers for {username}")
            return True, allocated, f"Reserved {count} numbers"
        except Exception as e:
            conn.rollback()
            self.logger.error(f"reserve_block error: {e}")
            return False, [], f"Error: {e}"
        finally:
            conn.close()

    def get_available_numbers(self, username):
        rows = self.db_manager.execute_with_retry(
            "SELECT id, report_number, serial_number, reserved_at, transferred_from "
            "FROM reserved_numbers WHERE owned_by = ? AND status = 'available' "
            "ORDER BY serial_number", (username,))
        return [{'id': r[0], 'report_number': r[1], 'serial_number': r[2],
                 'reserved_at': r[3], 'transferred_from': r[4]} for r in (rows or [])]

    def get_available_count(self, username):
        r = self.db_manager.execute_with_retry(
            "SELECT COUNT(*) FROM reserved_numbers WHERE owned_by = ? AND status = 'available'", (username,))
        return r[0][0] if r else 0

    def consume_next_available(self, username, report_id):
        # atomic claim of the user's lowest available number
        n = self.db_manager.execute_write(
            "UPDATE reserved_numbers SET status='used', used_by_report_id=? "
            "WHERE id = (SELECT id FROM reserved_numbers WHERE owned_by=? AND status='available' "
            "ORDER BY serial_number LIMIT 1)", (report_id, username))
        if n != 1:
            return False, None, "You have no reserved numbers available"
        r = self.db_manager.execute_with_retry(
            "SELECT report_number FROM reserved_numbers WHERE used_by_report_id=? ORDER BY id DESC LIMIT 1",
            (report_id,))
        return True, (r[0][0] if r else None), "ok"

    def transfer_numbers(self, from_user, to_user, report_numbers):
        if not report_numbers:
            return False, "No numbers selected"
        tgt = self.db_manager.execute_with_retry(
            "SELECT is_active FROM users WHERE username = ?", (to_user,))
        if not tgt or not tgt[0][0]:
            return False, "Recipient must be an active user"
        moved = 0
        for rn in report_numbers:
            n = self.db_manager.execute_write(
                "UPDATE reserved_numbers SET owned_by=?, transferred_from=? "
                "WHERE report_number=? AND owned_by=? AND status='available'",
                (to_user, from_user, rn, from_user))
            moved += n
        if moved == 0:
            return False, "No transferable numbers (must be yours and unused)"
        return True, f"Transferred {moved} number(s) to {to_user}"
```
Confirm `_generate_next_numbers(cursor)` returns `(report_number, serial_number)` in this file before use (it does — see `reserve_batch_numbers`).

- [ ] **Step 4: Run to verify it passes**

Run: `python3.14 tests_host_cluster.py` → `CLUSTER FAILURES: 0`

- [ ] **Step 5: Commit**

```bash
git add services/report_number_service.py tests_host_cluster.py
git commit -m "feat(reservation): owned-block reserve/consume/transfer service methods"
```

---

### Task 3: create_report gate + auto-consume

**Files:**
- Modify: `services/report_service.py` (`create_report`)
- Test: `tests_host_cluster.py` (extend) + `tests_conformance.py` (R-check update)

**Interfaces:**
- Consumes: `report_number_service.get_available_count` / `consume_next_available`.
- Produces: `create_report` now requires the creating user to have an available reserved number; it **auto-consumes** the next one and uses it as the report's `report_number`/`sn`. If the caller passes explicit `report_number`/`sn` (admin/import paths), honor them and skip consumption; otherwise consume. Returns `(False, None, "You have no reserved numbers — reserve first")` when the user has none and none was supplied.

Note: `create_report` needs access to the report_number_service. It is not injected today. Add an optional setter `set_report_number_service(self, svc)` on `ReportService` (like `set_activity_service`), wire it in `app_state.initialize_services` and in the test `_build_host` helper.

- [ ] **Step 1: Write the failing test**

Add to `tests_host_cluster.py`:

```python
def test_create_report_gate():
    box = tempfile.mkdtemp()
    try:
        host, t, dbm = _build_host(box)
        host.services['report_service'].set_report_number_service(host.services['report_number_service'])
        host.services['auth_service'].current_user = {'user_id':1,'username':'admin','role':'admin'}
        R = host.services['report_service']; N = host.services['report_number_service']
        # no reserved numbers -> gated
        ok, rid, msg = R.create_report({'report_date':'04/11/2025','reported_entity_name':'X','cic':'1'*16})
        check('P2T3 create blocked without reserved number', not ok and 'reserve' in msg.lower(), msg)
        # reserve then create -> uses the reserved number
        N.reserve_block('admin', 2)
        block = [x['report_number'] for x in N.get_available_numbers('admin')]
        ok, rid, msg = R.create_report({'report_date':'04/11/2025','reported_entity_name':'X','cic':'2'*16})
        check('P2T3 create ok after reserve', ok, msg)
        rn = dbm.execute_with_retry("SELECT report_number FROM reports WHERE report_id=?", (rid,))[0][0]
        check('P2T3 report uses reserved number', rn == block[0], (rn, block[0]))
        check('P2T3 reserved number consumed', N.get_available_count('admin') == 1)
    finally:
        shutil.rmtree(box, ignore_errors=True)
```
Call it in `__main__`.

- [ ] **Step 2: Run to verify it fails**

Run: `python3.14 tests_host_cluster.py`
Expected: FAIL (set_report_number_service missing / no gate).

- [ ] **Step 3: Implement**

In `services/report_service.py`:
1. Add `self._report_number_service = None` in `__init__` and:
```python
    def set_report_number_service(self, svc):
        self._report_number_service = svc
```
2. At the start of `create_report`, after the auth/permission checks and BEFORE the required-field/report_number checks, when no `report_number` was supplied and the number service is wired:
```python
            rns = self._report_number_service
            consumed_number = None
            if rns and not report_data.get('report_number'):
                if rns.get_available_count(current_user['username']) < 1:
                    return False, None, "You have no reserved numbers — reserve first"
                # consumed after we know the new report_id; reserve the value now
                avail = rns.get_available_numbers(current_user['username'])
                consumed_number = avail[0]['report_number']
                report_data = dict(report_data)
                report_data['report_number'] = consumed_number
                report_data['sn'] = avail[0]['serial_number']
```
3. After the report row is inserted and `report_id` is known, if `consumed_number` was set, consume it linking the new report:
```python
            if consumed_number and rns:
                rns.consume_next_available(current_user['username'], report_id)
```
(Consuming the *lowest available* equals `consumed_number` since nothing else runs between — the host is single-writer.)

Keep the existing dup-check on report_number/sn/cic (defensive) and everything else unchanged.

- [ ] **Step 4: Run to verify it passes + conformance**

Run: `python3.14 tests_host_cluster.py` → `CLUSTER FAILURES: 0`

Update `tests_conformance.py`: the old reservation-gate rows should now assert the new model. Find any check using `reserve_next_numbers` and replace the create-a-report helper to first `reserve_block(user, N)`. Then:
Run: `python3.14 tests_conformance.py 2>/dev/null | grep Conformance` → all pass.

- [ ] **Step 5: Commit**

```bash
git add services/report_service.py tests_host_cluster.py tests_conformance.py
git commit -m "feat(reservation): create_report gated on + auto-consumes an owned reserved number"
```

---

### Task 4: Command registry — add reserve/transfer commands, drop removed ones

**Files:**
- Modify: `services/command_registry.py`
- Test: `tests_host_cluster.py` (extend)

**Interfaces:**
- Produces: WRITE_COMMANDS gains `report_number_service.reserve_block` and `report_number_service.transfer_numbers`. Removes the now-dead `reserve_next_numbers`, `mark_reservation_used`, `cancel_reservation`, `cleanup_expired_reservations_public` (dropped in Task 7 from the service; remove from the map here).

- [ ] **Step 1: Write the failing test**

Add to `tests_host_cluster.py`:
```python
def test_registry_reservation_commands():
    from services import command_registry as cr
    check('P2T4 reserve_block is a write command', cr.is_write_command('report_number_service.reserve_block'))
    check('P2T4 transfer_numbers is a write command', cr.is_write_command('report_number_service.transfer_numbers'))
    check('P2T4 old reserve_next_numbers removed', not cr.is_write_command('report_number_service.reserve_next_numbers'))
```
Call it in `__main__`.

- [ ] **Step 2: Run to verify it fails**

Run: `python3.14 tests_host_cluster.py` (fails on the new/removed entries).

- [ ] **Step 3: Edit the map**

In `services/command_registry.py` WRITE_COMMANDS: add
```python
    "report_number_service.reserve_block": ("report_number_service", "reserve_block"),
    "report_number_service.transfer_numbers": ("report_number_service", "transfer_numbers"),
```
and remove the four old entries: `reserve_next_numbers`, `mark_reservation_used`, `cancel_reservation`, `cleanup_expired_reservations_public`.

- [ ] **Step 4: Run to verify it passes**

Run: `python3.14 tests_host_cluster.py` → `CLUSTER FAILURES: 0`

- [ ] **Step 5: Commit**

```bash
git add services/command_registry.py tests_host_cluster.py
git commit -m "feat(reservation): registry gains reserve_block/transfer_numbers, drops old reserve commands"
```

---

### Task 5: Reservation UI rewrite + add-report gate (removes G3 raw SQL)

**Files:**
- Modify: `flet_app/dialogs/reservation_dialog.py` (rewrite around the new model)
- Modify: `flet_app/dialogs/report_dialog.py` (gate the open path)
- Test: `tests_ui_driver.py` (extend — dialogs build; no raw SQL remains)

**Interfaces:**
- Consumes: `report_number_service.reserve_block / get_available_numbers / transfer_numbers`, and (for the transfer target list) `approval_service.get_active_agents`.
- Produces: a reservation screen that lets a user **Reserve N**, see **My Numbers** (available), and **Transfer** selected numbers to an active agent. NO raw SQL / no `execute_with_retry` in the dialog. The Add-Report open path checks `get_available_count(current_user) >= 1`; if zero, it shows "You have no reserved numbers — reserve first" and does not open the form.

- [ ] **Step 1: Write the failing check**

In `tests_ui_driver.py`, in the `E = 'UI Feature wiring'` section:
```python
    rsv = open(os.path.join(REPO, 'flet_app/dialogs/reservation_dialog.py')).read()
    finding(E, 'reservation dialog still runs raw SQL (must use service methods)',
            'execute_with_retry' in rsv or 'DELETE FROM' in rsv)
    finding(E, 'reservation dialog missing reserve_block wiring',
            'reserve_block' not in rsv)
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3.14 tests_ui_driver.py 2>/dev/null | grep -E "✗|UI failures"` (raw-SQL finding present).

- [ ] **Step 3: Rewrite the dialog + gate**

Rewrite `flet_app/dialogs/reservation_dialog.py` to use only `app_state.report_number_service` methods (read the current file first to preserve the `show_reservation_dialog(page, app_state)` signature and theme usage). Sections: a number input + "Reserve" button (calls `reserve_block(current_user, n)`), a list of the current user's available numbers (from `get_available_numbers`), and a transfer control (pick target from `get_active_agents`, select numbers, call `transfer_numbers`). Show results via the existing toast/snackbar. Remove every `db_manager.execute_with_retry(...)` and raw SQL.

In `flet_app/dialogs/report_dialog.py`, in `show_report_dialog`, for the **create** path (not edit), before building/opening the form:
```python
    if not is_edit_mode and report_number_service and current_user:
        if report_number_service.get_available_count(current_user['username']) < 1:
            show_error_dialog("You have no reserved numbers — reserve numbers first (Ctrl+R).")
            return
```
(Place it near the existing edit-lock acquisition block; `show_error_dialog` is already defined in this file.)

- [ ] **Step 4: Run to verify it passes**

Run: `python3.14 tests_ui_driver.py 2>/dev/null | grep -E "✗|UI failures"` → `UI failures: 0/NN`, no raw-SQL finding.
Confirm app still imports: `cd flet_app && python3.14 -c "import sys;sys.path.insert(0,'..');sys.path.insert(0,'.');import main;print('BOOT OK')"`.

- [ ] **Step 5: Commit**

```bash
git add flet_app/dialogs/reservation_dialog.py flet_app/dialogs/report_dialog.py tests_ui_driver.py
git commit -m "feat(reservation): reserve/my-numbers/transfer UI + add-report gate; remove raw SQL (G3)"
```

---

### Task 6: Update e2e harness to the new model + full regression

**Files:**
- Modify: `tests_e2e_harness.py` (the `make_report` helper + reservation feature checks)
- Test: the whole suite.

**Interfaces:**
- Produces: e2e `make_report` reserves a block once per user then creates; the reservation-feature section asserts the new model (reserve_block, available count, consume-on-create, transfer). No references to `reserve_next_numbers` / `mark_reservation_used` / `cancel_reservation`.

- [ ] **Step 1: Update the harness**

In `tests_e2e_harness.py`, change `Client.make_report` to ensure the user has an available number (reserve a block of e.g. 20 on first use), then call `create_report` without passing `report_number`/`sn` (let the gate consume). Wire `report_service.set_report_number_service(...)` in the Client constructor. Replace the "03 Report number reservations" feature checks with the new-model equivalents (reserve_block returns N, available count, consume-on-create decrements, transfer moves ownership, uniqueness holds).

- [ ] **Step 2: Run the full suite**

```bash
python3.14 tests_host_cluster.py 2>/dev/null | grep "CLUSTER FAILURES"     # 0
python3.14 tests_e2e_harness.py 2>/dev/null | grep TOTAL                    # all pass
python3.14 tests_conformance.py 2>/dev/null | grep Conformance             # all pass
python3.14 tests_prosecutor.py 2>/dev/null | grep "TOTAL VULN"             # 0 / 35
python3.14 tests_ui_driver.py 2>/dev/null | grep "UI failures"             # 0/NN
```

- [ ] **Step 3: Commit**

```bash
git add tests_e2e_harness.py
git commit -m "test(reservation): e2e harness uses owned-block model"
```

---

### Task 7: Remove the dead old reservation machinery

**Files:**
- Modify: `services/report_number_service.py` — remove `reserve_next_numbers`, `mark_reservation_used`, `cancel_reservation`, `cleanup_expired_reservations_public`, `start_cleanup_task`/`stop_cleanup_task`, `reserve_batch_numbers`, `get_next_from_pool`, `get_pool_size`, gap-queue methods (`get_next_gap`, `claim_gap`, `get_gap_queue_stats`, `cleanup_gap_queue`, `_add_to_gap_queue`), `get_active_reservations`, `get_reservation_stats`, `get_gap_notification`, and the `__init__` call to `start_cleanup_task()`. Keep `_generate_next_numbers`, `_active_month`, `close_month`, `is_month_closed`, `get_active_numbering_month`, and the new Task-2 methods.
- Modify: any remaining caller (grep first).

**Interfaces:** none new — pure removal. Keep month-close intact.

- [ ] **Step 1: Find all references first**

Run: `grep -rn "reserve_next_numbers\|mark_reservation_used\|cancel_reservation\|start_cleanup_task\|reserve_batch_numbers\|get_next_from_pool\|get_active_reservations\|get_reservation_stats\|claim_gap\|get_gap_notification" flet_app services --include="*.py" | grep -v __pycache__`
Every hit outside `report_number_service.py` must be removed/rerouted before deleting the method.

- [ ] **Step 2: Remove the methods + the `__init__` cleanup-thread start**

Delete the listed methods and the `self.start_cleanup_task()` call in `__init__`. Read the file and remove cleanly (keep the retained methods).

- [ ] **Step 3: Verify nothing references the removed names**

Run the grep from Step 1 again → only definitions gone, zero references remain.
Run: `python3.14 -c "import sys;sys.path.insert(0,'.');from services.report_number_service import ReportNumberService;print('imports ok')"`

- [ ] **Step 4: Full regression**

```bash
python3.14 tests_host_cluster.py 2>/dev/null | grep "CLUSTER FAILURES"   # 0
python3.14 tests_e2e_harness.py 2>/dev/null | grep TOTAL                  # pass
python3.14 tests_conformance.py 2>/dev/null | grep Conformance           # pass
python3.14 tests_prosecutor.py 2>/dev/null | grep "TOTAL VULN"          # 0/35
python3.14 tests_ui_driver.py 2>/dev/null | grep "UI failures"          # 0/NN
cd flet_app && python3.14 -c "import sys;sys.path.insert(0,'..');sys.path.insert(0,'.');import main;print('BOOT OK')"
```

- [ ] **Step 5: Commit**

```bash
git add services/report_number_service.py flet_app/
git commit -m "refactor(reservation): remove dead expiry/gap/pool/cleanup machinery"
```

---

## Notes for the implementer

- The host is the single writer; do NOT add locks or threads in these methods. `close_month` (R50/R51) stays and still runs host-side.
- `create_report` consuming "the user's lowest available" equals the number chosen for the report because nothing else runs between (single-writer). Do not try to reserve a specific id across two connections.
- If a UI screen (dashboard, reservation) referenced old stats methods (`get_reservation_stats`, `get_active_reservations`), replace with the new `get_available_numbers`/`get_available_count` or remove the panel — grep in Task 7 Step 1 will surface these.
- Keep every change host-safe: these methods are invoked as commands in the distributed deployment (Task 4 registry), and directly in local mode.
