# STR / FIU Report Management System — Documentation Index

**Version:** 1.2 | **Updated:** July 2026

---

## Start here (context & rationale — read in this order)

| Document | Description |
|----------|-------------|
| [CONTEXT.md](CONTEXT.md) | **The situation & hard constraints** — org, budget, locked-down environment, stakes, why the architecture is what it is. Read first. |
| [DECISIONS.md](DECISIONS.md) | **Architecture Decision Records** — each major choice with its context, alternatives, and research-backed rationale. |
| [superpowers/specs/2026-07-16-single-writer-host-architecture-design.md](superpowers/specs/2026-07-16-single-writer-host-architecture-design.md) | **The active design spec** — single-writer host + folder-queue + control panel. The distribution/durability architecture. |

## Business requirements (what the app must do)

| Document | Description |
|----------|-------------|
| [00_Scope_Amendment.md](00_Scope_Amendment.md) | **ACTIVE amendment — external integrations removed, standalone program** |
| [01_BRD_Main.md](01_BRD_Main.md) | System overview, scope, and requirements |
| [02_Data_Fields.md](02_Data_Fields.md) | Report fields and dropdown values |
| [03_Integrations.md](03_Integrations.md) | ~~External system integrations~~ (void — see amendment) |
| [04_Roles_Permissions.md](04_Roles_Permissions.md) | User roles and access rights |
| [05_UI_Screens.md](05_UI_Screens.md) | Screen layouts and navigation |
| [06_Developer_Decisions.md](06_Developer_Decisions.md) | Preemptive answers to common developer questions |

---

## System summary

STR manages Suspicious Transaction Reports for a bank FIU/AML team as a **standalone,
on-premises desktop app** (manual data entry, local auth, no external integrations —
see [00_Scope_Amendment.md](00_Scope_Amendment.md)).

The **application layer** (report CRUD, validation, approval workflow, versioning,
numbering, RBAC, export) is built and tested. The **distribution architecture** that
lets the whole team share it safely over a network folder without corrupting the data
is designed in the active spec above and is the current work.

**Why the architecture matters:** multiple PCs writing one SQLite file on a shared
drive corrupts compliance data (SQLite's own documented position — see DECISIONS.md
ADR-001). The design routes every write through a single host process on local disk,
with the shared folder used only as a mailbox. See CONTEXT.md.

---

*End of Index*
