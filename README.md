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

> **Setting it up, or running it?** You do not need this page.
> Go to **[docs/SETUP.md](docs/SETUP.md)** (install) or
> **[docs/OPERATIONS.md](docs/OPERATIONS.md)** (day to day). Both are written
> for non-technical readers.

## Run modes (one codebase, three entry points)

- **default** — the user report UI (client mode).
- **`--host`** — the single-writer host loop (owns the DB on local disk).
- **`--panel`** — the operator control panel (setup, host designation, monitoring,
  failover, config, maintenance). Also reachable from the login screen, so a user
  never needs the flag.

## Development

- Python **3.13** with Flet 0.28.3 + bcrypt.
- Launch the app: `python flet_app/main.py`
- Build the distributable exe: `build.bat` (defined by `STR.spec`; it refuses to
  produce a binary that is missing packages or data files).

### Tests

```
python tests/run_all.py          # standard suites, a few minutes
python tests/run_all.py --all    # including the long simulations
python tests/run_all.py roles    # only suites matching "roles"
```

Each suite builds its own sandbox and exits non-zero on failure. The notable ones:

| Suite | What it does |
|---|---|
| `tests_e2e_harness.py` | 192 functional checks + 10-user stress |
| `tests_prosecutor.py` | 36 adversarial security charges (target: 0) |
| `tests_conformance.py` | BRD conformance + crash-fuzz (target: 0 uncaught) |
| `tests_warzone.py` | 1 host + 16 client processes over the real queue |
| `tests_simulation_fortnight.py` | two weeks of business, 20 agents, 5 supervisors |
| `tests_frozen_paths.py` | the packaged exe keeps its data beside itself |

The last three are opt-in (`--all`) on time, not importance — the warzone and
fortnight simulations have each found defects nothing else did.

## Status

Application layer: **built, hardened, tested.** Distribution architecture
(single-writer host + folder queue): **implemented**, proven on one machine and
against a real SMB share. Not yet proven across a real network — that needs two
physical PCs, and it is the last open item.

## Distribution

Client PCs get a single packaged `FIU_System.exe` — no Python, no source, no
launcher script. It writes its config and local data beside itself, so it must
live somewhere writable (`C:\STR`), never Program Files.
