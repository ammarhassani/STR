# STR — FIU / AML Suspicious Transaction Report Management System

An in-house desktop application (Python / Flet + SQLite) that replaces a bank FIU
compliance team's corruption-prone shared Excel files with a proper report-tracking
system: report CRUD, DB-driven validation, an approval workflow, versioning, report
numbering, role-based access, audit trail, and Excel export.

> **New here? Read [docs/CONTEXT.md](docs/CONTEXT.md) first.** It explains the
> situation, the hard constraints (locked-down org, no budget, no IT, no admin, one
> shared network folder, compliance data that must not corrupt), and why the
> architecture is shaped the way it is. Then [docs/DECISIONS.md](docs/DECISIONS.md)
> for the reasoned decisions, and [docs/README.md](docs/README.md) for the full index.

## The one thing to understand

Multiple PCs writing one SQLite file on a shared drive **corrupts the data** — this
is SQLite's own documented position (see DECISIONS.md ADR-001). So the system routes
**every write through a single "host" process on local disk**, and the shared folder
is used only as a **mailbox** (command files in, responses out). This is the
distribution architecture, specified in
[docs/superpowers/specs/2026-07-16-single-writer-host-architecture-design.md](docs/superpowers/specs/2026-07-16-single-writer-host-architecture-design.md).

## Run modes (one codebase, three entry points)

- **default** — the user report UI (client mode).
- **`--host`** — the single-writer host loop (owns the DB on local disk).
- **`--panel`** — the operator control panel (setup, host designation, monitoring,
  failover, config, maintenance).

## Development

- Run everything with **`python3.14`** (user-site has Flet 0.28.3 + bcrypt). Plain
  `python3` lacks the deps.
- Launch the app: `python3.14 flet_app/main.py`.
- Test harnesses (all `python3.14 tests_*.py`, each builds its own sandbox):
  - `tests_e2e_harness.py` — 180 functional checks + 10-user stress
  - `tests_prosecutor.py` — 35 adversarial security charges (target: 0 vulnerabilities)
  - `tests_conformance.py` — BRD conformance + crash-fuzz (target: 0 uncaught)
  - `tests_ui_driver.py` — drives real Flet views/dialogs
  - `tests_theme.py` — flat-theme + component checks

## Status

Application layer: **built, hardened, tested.** Distribution/durability architecture
(single-writer host): **specified, under review, not yet implemented** — the service
layer is deliberately shaped so it bolts on without rewriting business logic.

## Distribution

Source lives on **Codeberg**; the organization workstation pulls the repo (and the
control-panel script) from there. "Remote" management means a separate local script
on the same PC — not network remote control (the locked network forbids it).
