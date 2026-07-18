# STR — Architecture Decision Records (ADRs)

Each record: the decision, the context that forced it, why it was chosen over the
alternatives, and its consequences. Read [CONTEXT.md](CONTEXT.md) first for the
situation these decisions serve.

Status legend: **Accepted** (decided), **Implemented** (in code), **Superseded**.

---

## ADR-001 — Never let multiple PCs write a shared SQLite file directly
**Status:** Accepted (non-negotiable)

**Context:** The obvious deployment is one `fiu_reports.db` on the shared SMB folder,
opened by every workstation. Compliance data must not corrupt.

**Decision:** Forbid it. Exactly one process may open any real database, on **local
disk**.

**Rationale (researched, multi-source, adversarially verified — primary sqlite.org):**
- *How To Corrupt An SQLite Database File*, *Appropriate Uses For SQLite*,
  *File Locking And Concurrency* (lockingv3), *SQLite Over a Network* (useovernet):
  file locking on network filesystems is "buggy in many implementations (on both
  Unix and Windows)," broken locks let two clients write the same page and corrupt
  the DB, and *"Your best defense is to not use SQLite for files on a network
  filesystem."*
- *Write-Ahead Logging* (wal.html): WAL "does not work over a network filesystem"
  because it needs shared memory across processes — impossible across machines.
- Advisory-lock mutexes (`flock`/`fcntl`) are documented unreliable on network FS
  (Linux flock(2) man page); atomic `O_EXCL` create on SMB is **unverified** — not
  safe to rely on for compliance data.

**Consequences:** Requires a host process (ADR-002/003). Removes the entire
network-filesystem corruption class. This is the foundation every other ADR rests on.

---

## ADR-002 — Transport is a shared-folder command queue, not network sockets
**Status:** Accepted

**Context:** Clients must reach the single host. The network is locked down — no
assured open ports between workstations, no agents.

**Decision:** Clients communicate with the host by writing **files** into queue
directories on the shared folder (`str_bus/queue/…`, `responses/…`), using
write-to-temp-then-**rename** for atomic placement. No TCP/HTTP between PCs.

**Rationale:** Creating a new, uniquely-named file is the one operation network
shares handle reliably (each client writes its own file — no shared file, no lock).
Sockets would need open ports the locked org blocks. Files sidestep firewalls
entirely.

**Consequences:** Slightly higher latency than sockets (poll-based, ~200 ms) —
irrelevant for low-volume report entry. If the network ever permits ports, a socket
transport can replace the folder queue behind the same interface (out of scope now).

---

## ADR-003 — Clients send high-level commands (RPC of the service layer), not raw SQL
**Status:** Accepted

**Context:** Many writes are multi-statement transactions (e.g. reserve-and-consume a
number while inserting a report). Shipping raw SQL statement-by-statement can't stay
atomic on the host.

**Decision:** Clients send **commands** (`create_report`, `reserve_numbers`,
`approve_report`, …) that map 1:1 to existing service methods. The host runs the real
service method in **one local transaction** — atomic by construction. The host
validates session + permission host-side before dispatch.

**Rationale:** The business logic is already built, hardened, and tested (180 e2e
checks, 0 vulnerabilities, 50 conformance rules, 0 crashes). Command-RPC **reuses it
unchanged** — it just runs on the host instead of each client. Atomicity, authz, and
correctness are preserved. It also makes the future infra migration a backend swap
behind the same interface.

**Consequences:** A command registry + a client-side service proxy + host-side session
model are needed. Reads run client-side against a published read-only replica; reads
needing strong freshness (reservation gate, uniqueness) are folded into the write
command and checked host-side.

---

## ADR-004 — Failover is manual and confirmed, guarded by term numbers (no auto-election)
**Status:** Accepted

**Context:** If the host PC is off, another must be able to take over. Automatic
election over an unreliable share risks two hosts running at once.

**Decision:** A designated backup teammate clicks **"Become Host."** The app verifies
the current host's heartbeat is genuinely stale, loads the latest published replica,
replays any unprocessed queue (idempotent by command ID), writes a **new term/lease**,
and starts serving. An old host that wakes sees the newer term and **steps down**.

**Rationale:** For ≤10 users, human-confirmed failover is simpler and strictly safer
than election. Critically, even a worst-case double-promotion writes to **separate
local DBs**, never a shared file — the failure mode is *detectable divergence*, not
*corruption*. Divergence is recoverable; corruption is not.

**Consequences:** A cold-outage recovery needs a human action (seconds). Acceptable.
Semi-automatic promotion after a long timeout is a possible later add-on using the
same term mechanism.

---

## ADR-005 — Separate Control Panel + `config.json` as single deployment source of truth
**Status:** Accepted

**Context:** The deployment needs setup, host designation, monitoring, failover,
config, and maintenance — an operator surface distinct from the user report UI.

**Decision:** A separate local entry point (`--panel`) of the same app: the **Control
Panel**. It manages the machine it runs on + shared deployment state. All deployment
settings live in `str_bus/config.json` on the share (designated host, paths,
intervals, retention, defaults) — the panel is its only writer; every instance reads
it. `config.json` holds **no secrets** (auth stays host-side).

**Rationale:** Splitting the operator plane from the user plane keeps the report UI
clean and gives ops a real cockpit. Matches the author's vision of an external
management script.

**Consequences:** Host designation is **cooperative** — the panel writes intent; a
machine self-selects the host role at launch. The panel cannot remote-start a process
on another PC (locked network, no agents). Delivered in Phase 3.

---

## ADR-006 — Host runs on a designated organization workstation (not the author's personal PC)
**Status:** Accepted

**Context:** The host must run on a machine subject to the org's locked-down policies.
The author's personal machine will not be the host.

**Decision:** The host runs on a designated org workstation, chosen via the control
panel's config.

**Rationale:** Keeps the system inside the org's boundary and off personal hardware;
supports succession (any org workstation can host). The org policies (screen-lock,
sleep, no admin, reboot-login) therefore apply and are addressed in ADR-009.

**Consequences:** Reliability is bounded by that workstation's uptime; mitigated by
published replica + backups + manual failover.

---

## ADR-007 — Report numbers are pre-allocated in owned, transferable blocks (Hi/Lo), not reserved at add-time
**Status:** Accepted (supersedes the current at-add-time reservation)

**Context:** The current design reserves the next number at the moment of report
creation — the highest-contention hot path. Also relevant: a shared-file substrate
punishes contention.

**Decision:** Users **pre-reserve a block** of numbers (check-in). Blocks are
**owned**, **non-expiring**, and **transferable** to another user. Creating a report
auto-consumes the user's next available number. No add-time contention, no 5-minute
holds, no expiry/cleanup thread.

**Rationale:** Pre-allocation (Hi/Lo) moves contention off the hot path — a recognized,
sound pattern. Under the host model it's trivially safe (the host serializes
everything). Owned+transferable blocks (per the author's requirement) mean leftovers
never rot. *Note:* pre-allocation is a contention/UX improvement, **not** a corruption
defense — the corruption fix is ADR-001/002/003; this rides on top.

**Consequences:** New `reserved_numbers` table + reserve/transfer/gate commands. The
old numbering logic (reserve_next_numbers, hold, max-1, gap-queue auto-reuse) is
dropped. Month-close (R50/R51) stays and runs host-side.

---

## ADR-008 — Rejected alternatives: direct-shared-file, DuckDB, and (for now) Postgres/rqlite
**Status:** Accepted

**Decision & rationale:**
- **Direct shared SQLite (any journal mode) + lock-file:** rejected — ADR-001; the
  primitives it relies on are the ones documented broken on network shares.
- **DuckDB:** rejected — it is an OLAP engine, single-writer-or-multi-reader, warns
  against network storage; its multi-writer path is a client-server beta. Wrong tool.
- **PostgreSQL / SQL Server:** correct long-term, but rejected **now** — needs an
  install/server the locked org + no-budget + no-IT constraints forbid. Retained as a
  documented **future migration** (ADR — backend swap behind the service gateway).
- **rqlite / dqlite / LiteFS:** viable single-writer brokers, but each is still a
  running server process to deploy; the in-app host mode achieves the same guarantee
  with code the author already owns and can maintain. Retained as alternatives if ever
  useful.

**Consequences:** The in-app single-writer host is the minimal solution that fits all
hard constraints today and upgrades cleanly to infra later.

---

## ADR-009 — Userspace reliability: sleep-prevention yes, unattended-reboot needs admin (documented limit)
**Status:** Accepted

**Context:** The host workstation auto-locks/idles; there are no admin rights.

**Decision & rationale:**
- **Screen lock:** no action needed — a locked Windows session keeps processes
  running.
- **Idle sleep:** prevented per-process via `SetThreadExecutionState(ES_CONTINUOUS |
  ES_SYSTEM_REQUIRED)` (userspace, no admin) while host mode runs.
- **Autostart:** host auto-launches on user **login** (Startup folder / user Task
  Scheduler — no admin).
- **Unattended after a cold reboot:** **not achievable without admin** (needs a
  Windows service or auto-login). Documented limit; mitigation is to keep the host PC
  logged in (locked is fine) or use manual failover. If admin is ever granted,
  install host mode as a service for full unattended operation.

**Consequences:** One honest operational limit remains; everything else works in
userspace.

---

## ADR-010 — UI is flat, light-only (dark mode removed)
**Status:** Implemented

**Context:** Material default look was unwanted; a compliance tool wants a calm,
professional surface; dark mode doubled styling surface for no stated need.

**Decision:** Flat enterprise styling, teal accent, 4px radii, hairline borders,
no ripple/elevation/page-transitions; **light mode only** (toggle and dark palette
removed); window opens maximized. Flet can't literally remove its MaterialApp shell,
so the *look* is neutralized via theme + a flat `app_button` primitive.

**Consequences:** Simpler theming, one palette, consistent look. Implemented and
tested (`tests_theme.py`, `tests_ui_driver.py`).

---

## ADR-011 — One codebase, three run modes; distributed via Codeberg
**Status:** Accepted

**Decision:** A single repository with three entry points — user app (default),
`--host`, `--panel` — pushed to **Codeberg** and pulled onto the org workstation
(plus the control-panel script). Execution on the locked workstation is proven
feasible (user-site Python 3.14 + Flet 0.28.3).

**Rationale:** One codebase shares services/config/DB code across modes and keeps
maintenance in one place for a solo builder. Codeberg is a free, no-IT git host.

**Consequences:** The launcher selects mode by flag; `app_state` wires host-local vs
client-proxy accordingly.

---

## The FIU round-trip (owner's working philosophy, 2026-07-18)

**Implemented 2026-07-18 as the `pending_fiu` phase — see "What the code does"
below. Recorded here because it is how the work actually happens.**

The real lifecycle of an STR is not "fill it in once, get it approved, done".
It has a gap in the middle where the report leaves the bank and comes back:

1. **Draft** — the agent enters what the bank knows: the customer (found from
   the CIC), the transaction, the reason for suspicion.
2. **Version 1** — the report is complete as far as the bank can complete it,
   and goes through internal review.
3. **FIU phase** — the report is submitted on the FIU's own web portal. That is
   an external system: nothing comes back at submission time. Later the FIU
   issues a number (and letter/date/feedback).
4. **Back to the same report** — the agent who filed it returns to that exact
   report and fills in the FIU details that did not exist when they wrote it:
   `fiu_number`, `fiu_letter_number`, `fiu_letter_receive_date`, `fiu_date`,
   `fiu_feedback`.
5. **Second approval phase** — the now-complete record, FIU details included, is
   confirmed and stored.

**The agent owns step 4.** They are responsible for the FIU details on their own
report. Any rule that permanently freezes a report after its first approval
would break the actual job — the FIU fields are, by their nature, filled in
after the fact.

### The phase as built

`pending_fiu` is where a saved report waits. The order is the owner's:

1. The agent fills in a new report and **saves** it. Saving does NOT submit it —
   it lands in the **Pending FIU** basket.
2. The agent files the report on the FIU portal (outside this app) and the FIU
   issues a number.
3. The agent opens the basket, adds the FIU details, and submits for approval.
   Submitting is the moment the report counts as filed with the FIU.
4. A supervisor sees it for the first time here. **A report with no FIU details
   never reaches an approval queue** — the FIU number is part of what is being
   approved.

The agent chooses the pace: fill the FIU details during initial entry and submit
in one sitting, or save now and complete it from the basket later.

`request_approval` refuses a report whose `fiu_number` or `fiu_date` is empty,
names what is missing, and says the work is saved and waiting in the basket.
The refusal lives in the service, not the dialog, so no path can push an
incomplete report into someone's queue.

**The basket is shared.** Everyone sees every report waiting for FIU details, so
one does not sit forgotten because the agent who filed it is away. It is sorted
oldest-first and shows who filed each report, how long it has waited, and which
FIU fields are still missing.

Which fields gate submission is one constant, `ReportService.REQUIRED_FIU_FIELDS`
(currently `fiu_number` and `fiu_date`). The FIU letter number, its receive date
and the FIU's feedback arrive later and stay optional.

Admin-created reports are still auto-approved and skip the basket entirely.

### What the code does today, and how it lines up

- `pending_approval` is the ONLY frozen state: someone is reviewing the report
  right now and must decide on exactly the text they were shown.
- Every other state -- draft, approved, rework, rejected -- stays editable by
  its author. An FIU report keeps growing after its first approval, so a
  permanent freeze would break the job. (Owner's rule, 2026-07-18.)
- Rejected is final only in the sense that it cannot be RESUBMITTED for
  approval; the author can still complete the record.
- Every edit is versioned inside `update_report`, so the FIU refill shows up as
  its own version rather than silently overwriting version 1.

There is no separate "FIU phase" status and no distinct second approval gate;
step 5 is an ordinary edit of an approved report. If the round-trip should
become an explicit state (with its own queue and its own approval), that is a
real feature, not a tweak — it needs a status beyond the current five, a way to
tell "waiting for the FIU" apart from "finished", and a decision about who
confirms step 5.

### Answered

The FIU number arrives after internal approval, so the single `pending_approval`
freeze does not obstruct step 4. Confirmed by the owner, 2026-07-18.

### Related: what the CIC lookup does and does not carry over

Typing a CIC brings back who the customer IS -- name, gender, nationality,
ID/CR and its type, branch, legal-owner flag -- from the most recent live report
for that CIC, filling only fields the analyst left empty.

It deliberately does NOT carry over the **account or membership number**. One
customer can hold several accounts, or an account AND a membership, so the
number on their last report says nothing about which one the new report
concerns. Prefilling it would quietly attach the wrong account to a suspicion.
(Owner's rule, 2026-07-18.)
