# STR documentation

**Pick the row that matches what you're doing.**

| I want to... | Read |
|---|---|
| Set STR up on a PC | [SETUP.md](SETUP.md) |
| Run it day to day, or fix a problem | [OPERATIONS.md](OPERATIONS.md) |
| Test it across real PCs | [TEST_DAY.md](TEST_DAY.md) |
| Understand why it's built this way | [CONTEXT.md](CONTEXT.md) |
| Change the code | [DECISIONS.md](DECISIONS.md), then the specs below |

The first three need no technical background. The last two assume you write code.

---

## For whoever runs STR

**[SETUP.md](SETUP.md)** — installing the host and the client PCs. Ordered
steps, one action each, with a symptom-to-fix section at the end.

**[OPERATIONS.md](OPERATIONS.md)** — the daily check, backups, what to do when
the host PC dies, and the handful of problems you will actually meet.

**[TEST_DAY.md](TEST_DAY.md)** — one-page checklist for testing across real
machines. Print it.

---

## For whoever maintains the code

**[CONTEXT.md](CONTEXT.md)** — the situation and the hard constraints: a
locked-down bank environment, no budget, no admin rights, one shared folder, and
compliance data that must not corrupt. Read this before judging any design
choice; most of them are forced.

**[DECISIONS.md](DECISIONS.md)** — every significant decision with its context,
alternatives and rationale. Includes the FIU round-trip workflow, which is
domain knowledge you cannot infer from the code.

**[superpowers/specs/](superpowers/specs/)** — designs for the larger pieces:
the single-writer host architecture, the retrospective import, the UI redesign.

**Why the architecture matters:** several PCs writing one SQLite file on a
shared drive corrupts compliance data — SQLite's own documented position, see
DECISIONS.md ADR-001. Every write goes through a single host process on local
disk; the shared folder is only a mailbox.

### Requirements baseline

`01_BRD_Main.md` and companions (`02_Data_Fields`, `03_Integrations`,
`04_Roles_Permissions`, `05_UI_Screens`, `06_Developer_Decisions`,
`00_Scope_Amendment`) are the original agreed requirements. They record what was
asked for, so they stay even where the build has moved on.
`03_Integrations` is void — see the amendment.

### Tests

```
python tests/run_all.py          # standard suites, a few minutes
python tests/run_all.py --all    # including the long simulations
python tests/run_all.py roles    # only suites matching "roles"
```

The long simulations are opt-in because they take minutes, **not** because they
matter less — the warzone and fortnight simulations have each found defects
nothing else did.

---

## [archive/](archive/)

Superseded, kept for history: the old host runbook and VM test plan (both
describe `.vbs` launchers that no longer exist), the 20-item roadmap, the i18n
plan, and implementation plans for work that shipped. **Nothing in there
describes how STR works today.** Git holds the full history if these are ever
deleted.
