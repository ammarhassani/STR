# STR — Project Context & Constraints

> Read this first. It is the "why" behind every architectural choice in this
> codebase. If you inherit this project, this document tells you the situation it
> was built for, the constraints that shaped it, and the decisions that are
> non-negotiable versus the ones that are open. Companion documents:
> [DECISIONS.md](DECISIONS.md) (the reasoned decision records) and
> [superpowers/specs/](superpowers/specs/) (the designs).

Last updated: 2026-07-16.

---

## 1. What this is

**STR** ("Suspicious Transaction Report" management system) is an in-house desktop
application for a bank's **FIU (Financial Intelligence Unit) / AML compliance team**.
It replaces a set of **shared Excel files** the team uses to track Suspicious
Transaction Reports through their lifecycle (draft → pending approval → approved /
rejected / rework), with report numbering, versioning, an approval workflow, an
audit trail, role-based access, and Excel export.

It is a **Flet (Python)** desktop app, backed by **SQLite**. Data and terminology
are Saudi/Arabic banking context (Arabic dropdown values, FIU/CIC fields).

## 2. The situation (why this project exists, and the pressure on it)

- The team is **"trenched in corrupted Excel files."** Shared spreadsheets are
  failing them — merge conflicts, corruption, no audit trail, no access control.
  This is the pain the app removes.
- The project is **approved by the business-unit head**, who is actively pushing
  for it to be finished. Its purpose and demand are **settled** — this is not a
  prototype looking for a use; it is a needed replacement being waited on.
- It was once proposed as an **organization-wide, IT-delivered project. The vendor
  quote was ~150,000 USD. Management rejected it for insufficient budget.** The
  author then **revived it as an in-house build** and personally committed to the
  business-unit head that they would deliver it. That commitment is the reason this
  exists and the reason it must actually work.

## 3. Hard constraints (these shaped the entire architecture)

These are not preferences. They are the walls of the box the solution must fit in.

1. **No budget.** Zero. No paid software, no licenses, no cloud, no vendor.
2. **No IT involvement, no management escalation.** The author cannot file tickets,
   request servers, or get infrastructure provisioned. Raising it again risks the
   whole project being killed on cost, as before.
3. **No admin rights on the machines.** Locked-down corporate workstations. Cannot
   install system services, cannot enable auto-login, cannot install a database
   server. Software runs in **userspace** only.
4. **Locked-down network.** No open ports between workstations assumed; no agents on
   machines. Peer-to-peer sockets cannot be relied upon.
5. **The only shared resource is a Windows/SMB network folder.** That folder is the
   sole thing all the team's PCs can see in common.
6. **Compliance data — corruption or loss is fatal.** This is AML/regulatory data.
   A corrupted database is not an inconvenience; it can end the project and cause a
   compliance problem. "Can't afford to flop" is literal.
7. **Small scale.** ≤10 users, low write volume (a handful of reports per person per
   day), not a real-time/high-throughput system.
8. **Workstations auto-lock after ~15 minutes idle** (OEM policy). Power behavior
   (sleep vs just screen-lock) matters for anything that must keep running.
9. **Solo builder.** One person designs, builds, tests, and maintains this. Bus
   factor of one. The system and its docs must survive that person leaving.

## 4. The core technical problem (researched, not assumed)

The obvious design — put one SQLite file on the shared folder and let every PC open
it — **is unsafe and will eventually corrupt the data.** This is not opinion; it is
SQLite's own documented position, confirmed by a multi-source, adversarially-verified
research pass (see [DECISIONS.md](DECISIONS.md) ADR-001 for citations):

- SQLite over a network filesystem (SMB/NFS): file locking is "buggy or
  unimplemented," and broken locks let two clients corrupt the same page.
  sqlite.org: *"Your best defense is to not use SQLite for files on a network
  filesystem."*
- WAL journal mode **cannot** work across machines (it needs shared memory).
- Advisory-lock mutexes on a share are unreliable; atomic-exclusive-create on SMB is
  unverified.
- No serverless embedded database (SQLite, DuckDB) supports safe concurrent
  multi-process writes across machines.
- The authoritative fix per sqlite.org: **put one process between the clients and the
  data.**

## 5. The chosen answer (one line)

**Exactly one process ever opens the database, on a machine's local disk; every other
PC sends it commands through the shared folder as files.** That process is our own app
in "host mode," running on a **designated organization workstation** (not the author's
personal machine). The shared folder is a **mailbox, never a database.** This
eliminates the corruption class entirely. Full design:
[superpowers/specs/2026-07-16-single-writer-host-architecture-design.md](superpowers/specs/2026-07-16-single-writer-host-architecture-design.md).

## 6. Non-negotiables vs open choices

**Non-negotiable (violating these reintroduces the fatal risk):**
- Only ONE process opens any real database file, and it lives on **local disk**.
- Clients never open a database over the network. They read a **published read-only
  replica copy** and write via the **command queue**.
- All writes go through **one host at a time** (single-writer). Never two.
- Every acknowledged write is durable and applied **exactly once** (idempotent).

**Open / tunable (safe to change per deployment):**
- Which workstation is the host, and which is the backup.
- Publish/backup intervals, queue retention, reserve block size, session timeout.
- Whether failover is manual (default) or later semi-automatic.

## 7. Distribution & deployment model

- Source is pushed to **Codeberg** (git). The organization workstation **pulls** the
  repository (and the operator/control-panel script) from there. Execution on the
  locked workstation is already proven feasible (the app runs there today via a
  user-site Python 3.14 + Flet 0.28.3).
- The app has three run modes (one codebase): the **user app** (report UI), **host
  mode** (`--host`, the single writer), and the **control panel** (`--panel`, the
  local operator tool for setup, host designation, monitoring, failover, config,
  maintenance). "Remote" management means **a separate local script on the same PC**,
  not network remote control.
- Host designation is **cooperative**: the control panel writes intent to a shared
  `config.json`; a machine self-selects the host role at launch. The panel cannot
  remote-start a process on another PC (locked network, no agents) — it manages its
  own machine and shared config/state.

## 8. Succession & the exit plan (this must outlive its author)

- **Data is never stranded on one PC.** The host continuously publishes a full DB
  replica + rolling backups to the shared folder, so the folder always holds a
  recent, complete, promotable database. If the host machine is lost, another
  workstation runs host mode and promotes from the replica.
- **The host role is portable, not personal.** Everything a new host needs lives on
  the share.
- A **handoff runbook** (`docs/SETUP.md` + `docs/OPERATIONS.md`, delivered with the control panel)
  documents start/stop, promotion, integrity verification, and backup restore for a
  non-author teammate.
- **Migration to real infrastructure is a deployment change, not a rewrite.** Because
  the app talks to a service gateway rather than the database directly, when infra is
  ever granted the same host-mode app runs on an always-on server box (or the backend
  swaps to PostgreSQL) with no application rewrite. A bare "shared partition" from
  infra is **not** a fix — it is still a network share; what infra must provide is an
  always-on *machine* or a *database server*.

## 9. Stakes, in plain terms

Getting this wrong doesn't mean a slow app. It means corrupted compliance data in
front of the business-unit head who staked their approval on it, from a solo builder
who told them "I will make this." That is why the architecture refuses the easy-but-
unsafe path, why data durability and single-writer safety are non-negotiable, and why
this document exists — so the reasoning survives, whoever reads it next.

## 10. Current build status (as of this document)

The application layer is built, hardened, and tested independently of the
distribution architecture:
- Full report CRUD, 35-field form, DB-driven validation, approval workflow,
  versioning, numbering, dropdowns, export, dashboard, delete/restore, RBAC.
- Test harnesses (run with `python3.14`): `tests_e2e_harness.py` (180 checks + 10-user
  stress), `tests_prosecutor.py` (35 adversarial security charges, 0 vulnerabilities),
  `tests_conformance.py` (50 BRD rules + crash-fuzz, 0 uncaught), `tests_ui_driver.py`
  (drives real Flet views), `tests_theme.py`.
- UI redesigned flat, light-only, teal accent; window opens maximized.
- The single-writer host architecture (this document's subject) is **specified and
  under review; not yet implemented.** The service layer is deliberately shaped so
  that architecture bolts on without rewriting business logic.
