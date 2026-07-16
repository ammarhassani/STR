# Scope Amendment — Standalone Development (July 2026)

**Status: ACTIVE — overrides all integration references in documents 01–06.**

## Background

The v1.0 BRD (January 2026) was written for an organizational development
handoff that assumed access to bank infrastructure. The organization rejected
the handoff. Development continues independently as a standalone program with
no external system access.

## What is removed from scope

| Removed | BRD references now void |
|---------|------------------------|
| RBS (Core Banking) customer lookup | Auto-populate by CIC, customer field locking, re-lookup button |
| SAS Visual Investigator case lookup | Case ID / Case Date retrieval, 1-to-many Case ID dropdown |
| Identity Self Service (SSO) | SSO authentication, directory-sourced usernames/display names |
| All external integrations generally | Section 03_Integrations.md in its entirety |

## What replaces them

- **All report fields are manual entry.** Fields documented as "RBS Lookup" or
  "SAS Lookup" in 02_Data_Fields.md are typed by the user. Required flags and
  validation rules are unchanged and enforced locally (column_settings).
- **No field locking.** The Agent/Admin lock-icon behavior for
  integration-sourced fields does not apply; normal role permissions govern
  editing.
- **Authentication stays local** — username/password with bcrypt, as already
  implemented. Account management via the Admin Panel.
- **All dropdowns are locally managed** via Dropdown Management. The
  05_UI_Screens.md note excluding "RBS-sourced" dropdowns does not apply.
- **Case ID** remains a manual optional field; its local uniqueness check is
  kept.
- **Source System** dropdown (SAS / INCIDENT) is kept as a plain label — it
  records where a case originated, implies no connectivity.

## Unchanged

Everything else in the BRD stands: approval workflow, roles/permissions,
version history, report numbering/reservations, export, backups, UI screens
(minus integration affordances).
