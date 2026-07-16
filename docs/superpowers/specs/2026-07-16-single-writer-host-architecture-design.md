# Single-Writer Host + Folder-Queue Architecture — Design

**Date:** 2026-07-16
**Status:** Draft for review
**Supersedes:** the current "every client opens the shared SQLite file directly" model and the at-add-time report-number reservation.

## 1. Problem & constraints

STR is an in-house AML compliance report tracker for a small team (≤10 PCs) in a
locked-down organization:

- **No IT, no admin rights, no budget, no provisioned server.** Deliverable must
  be self-contained (the app `.exe` + a shared folder).
- The only shared resource is a **Windows/SMB network folder.**
- Compliance data — **corruption or data loss ends the project.**
- Screens auto-lock after 15 min idle (OEM policy).

### Research verdict (deep-research, cited to primary sqlite.org, 3-vote verified)
Multiple SQLite clients writing one DB file on an SMB/NFS share is **never safe**:
file-locking on network filesystems is "buggy or unimplemented," causing
corruption (howtocorrupt.html, whentouse.html, lockingv3.html, useovernet.html);
WAL cannot work across machines (wal.html); advisory-lock mutexes are unreliable
on network FS; `O_EXCL`-on-SMB reliability is unverified. Official guidance: **put
one process between the clients and the data.** DuckDB does not offer a serverless
multi-writer path. Hi/Lo pre-allocation reduces contention but is not a corruption
defense.

**Conclusion:** exactly one process may ever open the database, and it must live on
**local disk** (not the share). That process is our own app in "host mode."

## 2. Architecture overview

Two run modes of the same application:

- **HOST mode** — runs on ONE teammate's PC. Owns `fiu_reports.db` on that PC's
  **local disk**. Runs the full service stack. Consumes a command queue from the
  share, executes each command atomically against the local DB, writes responses,
  publishes a read-only replica + backups to the share, emits a heartbeat, and
  prevents idle-sleep.
- **CLIENT mode** — every other PC (and the host PC's own UI). The UI calls a
  **RemoteServices proxy** instead of the local DB:
  - **Writes** → serialize a command, drop it in the share queue, await the
    response file.
  - **Reads** → run against a **local copy of the host's published read replica**
    (fast, offline-capable). Reads needing strong freshness (e.g. "do I have an
    available reserved number right now") are folded into the write command and
    checked host-side.

The share is a **dumb mailbox**, never a database. The only share operations are:
create-your-own-uniquely-named-file and read/rename-your-own — the operations
network shares handle reliably. No two machines ever write the same file; no
SQLite file is ever opened over the network.

```
  Host PC (host mode, business hours)          Shared folder (mailbox)
  ┌───────────────────────────────┐            ┌──────────────────────┐
  │ fiu_reports.db  (LOCAL disk)  │  publish   │ replica/fiu_ro.db    │◄─ clients read
  │ full service stack            │ ─────────► │ queue/pending/*.json │◄─ clients write
  │ command loop ◄────────────────┼────────────┤ queue/processing/    │
  │ heartbeat, sleep-guard        │  respond   │ responses/*.json     │─► clients await
  └───────────────────────────────┘ ─────────► │ host/heartbeat.json  │─► clients sense host
                                                │ backups/*.db         │
                                                └──────────────────────┘
                    ▲ enqueue commands / read replica ▲
         Client PC2 ─┘         Client PC3 ─┘   ...  (CLIENT mode)
```

## 3. Components

### 3.1 Transport — the folder queue (`services/queue_transport.py`, new)
Directory layout under `<share>/str_bus/`:
- `queue/pending/` — new commands awaiting the host.
- `queue/processing/` — commands the host has claimed.
- `queue/done/` — applied commands (kept briefly for audit, then pruned).
- `responses/` — one response file per command, keyed by command UUID.
- `replica/` — `fiu_ro.db` read-only snapshot (+ `fiu_ro.db.meta` with version/timestamp).
- `host/` — `heartbeat.json` (host_id, pid, hostname, epoch_ms, db_version).
- `backups/` — rolling DB backups.

**Atomic write rule (safety-critical):** to place any file, write to
`<dir>/.tmp/<uuid>` then **rename** into place. Rename within one directory is the
commit; readers never see a half-written file. Command files are uniquely named
`<epoch_ms>_<client_id>_<uuid>.json` — collisions impossible, no lock needed.

**Command file (client → host):**
```json
{ "id": "<uuid>", "client_id": "PC-ALI", "user": "ali",
  "session_token": "...", "command": "create_report",
  "args": { ... }, "created_at": "<iso>" }
```
**Response file (host → client), name = `<id>.json`:**
```json
{ "id": "<uuid>", "ok": true, "result": { ... },
  "error": null, "applied_at": "<iso>", "db_version": 1234 }
```

### 3.2 Command protocol — RPC of the service layer
Clients do **not** send raw SQL (multi-statement transactions can't be shipped
statement-by-statement and stay atomic). They send **high-level commands** that map
1:1 to service methods. The host executes the real service method in ONE local
transaction — atomic by construction.

- Command registry (`services/command_registry.py`, new): `command name -> (service, method, arg schema, required permission)`. Covers every write operation:
  `create_report, update_report, delete_report, restore_report, hard_delete_report,
  request_approval, approve_report, reject_report, create_version_snapshot,
  restore_version, reserve_numbers, transfer_numbers, add/update/delete/reorder/
  restore_dropdown_value, bulk_import_dropdown_values, create_user, update_user,
  delete_user, reset_password, unlock_account, change_password, save_settings,
  close_month, acquire_edit_lock, release_edit_lock, ...`.
- The host validates the caller's session + permission **host-side** (never trust the
  client) before dispatching — the service-layer authz we already built runs here.

**Session model:** `login` is itself a command — the host authenticates
(bcrypt, lockout, all existing logic) and returns a **session token** it tracks in
memory (token → user_id, role, issued_at, expiry). Every later command carries that
token; the host resolves it to a user and **sets the auth context for that one
command** before dispatching, so `created_by`, ownership, and permission checks are
all correct and un-spoofable. Client mode never holds credentials beyond login. If
the host restarts, tokens are invalidated → clients silently re-login on the next
command (they cached the password only for the session, or re-prompt). Session
timeout (R3, 30 min idle) is enforced host-side.

### 3.3 Host process (`host/host_service.py`, new; launched via `--host`)
Single-threaded command loop:
1. Start-up: `PRAGMA integrity_check` on local DB; if fail → restore newest good
   backup, alert. Publish initial replica + heartbeat.
2. Prevent idle-sleep: `ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)` (userspace, no admin).
3. Loop:
   - Scan `queue/pending/`, oldest first. **Claim** by rename → `queue/processing/<host_id>/`.
   - **Idempotency:** if command `id` already in `applied_commands` table, skip
     re-apply, just re-emit the stored response (handles crash-replay + redelivery).
   - Dispatch to the service method in one transaction; record `id` + result in
     `applied_commands`; move command to `done/`; write the response file
     (atomic temp+rename).
   - After each command (or a small batch): republish the read replica + bump
     `db_version`; refresh heartbeat.
4. Backups: copy DB → `backups/fiu_<ts>.db` every N minutes and on shutdown; keep
   last K.

DB access here is a **normal local SQLite connection** (WAL on local disk is safe
and fast). The whole "network FS corruption" problem does not exist for the host.

### 3.4 Client proxy (`services/remote_services.py`, new)
- The UI keeps calling the same service API. In CLIENT mode a `RemoteServiceProxy`
  implements those methods: build command → enqueue → poll `responses/<id>.json`
  (with timeout + backoff) → return result or raise.
- **Reads** go to a local `db_manager` opened **read-only** against a **local copy**
  of `replica/fiu_ro.db` (the client copies it down when `db_version` changes).
  Reads never hit the share DB directly and never block on the host.
- **Host-down UX:** if `heartbeat.json` is older than `HOST_STALE_SECONDS` (e.g.
  60s), the client shows a banner "Host offline — read-only. New entries will sync
  when the host returns," still lets the user compose, and **queues** their writes
  (they get applied + acknowledged when a host returns). No acknowledged write is
  ever lost; nothing is written twice (idempotent `id`).

### 3.5 Failover (manual, confirmed — no election race)
Automatic election over an unreliable share risks two hosts → divergence. For ≤10
users, **manual confirmed promotion** is simpler AND safer:
- Clients sense host-down via stale heartbeat.
- A **designated backup teammate** clicks **"Become Host"** in the app. The app:
  verifies the heartbeat is genuinely stale; loads the newest `replica/` copy as its
  new local DB; **replays** any `pending/` + `processing/` commands (idempotent by
  `id`, so nothing double-applies); writes a new `host_lease` (host_id + monotonic
  term) into the DB and heartbeat; starts serving.
- If the old host wakes, it reads the heartbeat, sees a **newer term**, and **steps
  down to client mode** automatically (never two writers). Worst case is a tiny
  reconciliation window, not corruption — because each host only ever wrote its own
  local DB, and the queue is idempotent.
- (Optional later: auto-promote a single pre-designated backup after a long,
  human-tunable timeout — same mechanism, guarded by term numbers.)

### 3.6 Report-number reservation, redesigned (rides on the host)
Because the host serializes everything, numbering is trivially safe:
- `reserved_numbers(report_number, serial_number, owned_by, status[available|used],
  used_by_report_id, reserved_at, transferred_from)`.
- `reserve_numbers(user, n)` command → host allocates the next N sequential numbers
  to the user as `available` in one transaction. No expiry, no cleanup thread.
- **Add-report gate:** `create_report` command host-side checks the user has an
  `available` number, consumes the next one (flips `used` + links to the new report)
  in the SAME transaction as the insert. If none → command returns an error the UI
  turns into "Reserve numbers first."
- `transfer_numbers(from, to, [numbers])` command → reassign `owned_by`, log
  `transferred_from`.
- **Dropped:** at-add-time `reserve_next_numbers`, the 5-min hold, max-1 rule,
  expiry/cleanup thread, gap-queue auto-reuse. Month-close (R50/51) stays and runs
  host-side.

## 4. Reliability & limits (stated honestly)

- **Corruption: eliminated** — one machine, local disk, single process.
- **Data loss: none for acknowledged writes** — durable queue + idempotent apply +
  crash-replay + backups.
- **Screen lock:** host process keeps running while locked. ✅
- **Idle sleep:** prevented via `SetThreadExecutionState` (no admin). ✅ (Assumes OEM
  policy does idle-*sleep*, overridable per-process; a forced OS hibernate we can't
  override is the one uncontrollable case.)
- **Autostart:** host auto-launches on user **login** (Startup folder / user Task
  Scheduler, no admin). Survives lock/idle indefinitely.
- **Unattended after a cold reboot: NOT achievable without admin** (needs a Windows
  Service or auto-login). Documented limit; mitigations: keep the host PC logged in
  (locked is fine); on reboot, one login; or use manual failover to a backup PC.
- **Write latency:** host-up → sub-second (poll interval ~200ms). Host-down →
  deferred until a host returns. Fine for report entry (low volume, not real-time).
- **Read staleness:** reads are as fresh as the last published replica (seconds).
  Strong-consistency checks (reservation gate, uniqueness) are done host-side in the
  write command, so staleness never causes a bad write.

## 5. Migration from today's direct-DB app

- `db_manager` gains two roles: **host-local** (real SQLite, as today) and
  **client-read-only** (opens the local replica copy for SELECTs only).
- A `ServiceGateway` abstraction: in HOST mode it's the real services; in CLIENT mode
  it's `RemoteServiceProxy`. `app_state` wires whichever mode the app launched in.
  The **views/dialogs call the same service API** — no UI rewrite, only the wiring
  under `app_state` changes.
- Setup wizard gains: pick mode (host/client), pick share path, (host) pick local DB
  path, (client) auto-discover host via heartbeat.

## 6. Phased delivery (each phase independently shippable/testable)

1. **Phase 1 — Transport + command RPC core.** Folder queue, command registry, host
   loop, client proxy, host-side authz, idempotency, replica publish, read path.
   Replaces direct-DB access. All existing service logic reused unchanged.
2. **Phase 2 — Reservation redesign.** `reserved_numbers`, reserve/transfer/gate
   commands, drop old numbering logic.
3. **Phase 3 — Resilience.** Heartbeat + host-offline UX, manual failover
   ("Become Host") + term/lease, backups + integrity-check-on-start, sleep-guard,
   autostart, setup-wizard mode selection.

## 7. Testing

- **Multi-process harness (new `tests_host_cluster.py`):** spawn 1 host + N client
  processes against a temp "share" dir on local disk (simulating the folder queue);
  run the existing 10-user stress workload through the command path; assert: every
  acknowledged write applied exactly once, `PRAGMA integrity_check` ok, unique
  sn/report_number, no lost/duplicated commands, idempotent replay after a killed
  host, correct host-offline queueing, clean manual failover with no divergence.
- The existing suites (e2e 180, prosecutor 0/35, conformance 47/47) run against the
  **host-side services unchanged** — the service layer is the same code; only its
  transport changed. Reservation tests are rewritten for the new model.
- Fault injection: kill host mid-command (replay), corrupt the local DB (restore
  from backup), stale/again heartbeat (failover), half-written command file
  (temp+rename proves it's never seen).

## 8. Out of scope
Cross-site/WAN use, >~20 users, real-time sub-100ms writes, automatic election
without human confirmation (Phase 3 optional add-on), replacing the folder queue
with sockets (kept as a future option if the network ever allows ports).

## 9. Open decisions for review
- **Backup PC:** who is the designated secondary host? (affects Phase 3)
- **Read freshness:** replica republish interval (default 2s) and whether any screen
  needs live-not-snapshot reads (I believe none do — the write gate handles
  consistency).
- **Queue retention:** how long to keep `done/` commands for audit (default 7 days).
- **Reserve default N:** how many numbers a user grabs per check-in (default: user
  types the count; suggest 10).
