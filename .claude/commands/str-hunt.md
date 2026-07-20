---
description: "One autonomous bug-hunt iteration on the STR AML system"
allowed-tools: ["Bash", "Read", "Edit", "Write", "Grep", "Glob"]
disable-model-invocation: true
---

You are running ONE iteration of an unattended bug hunt on a bank's AML / STR
system. Nobody is watching, and you have no memory of previous iterations —
every fact you need is in files. The rules below are enforced by git hooks:
breaking one fails the commit, it does not pass quietly.

## Step 1 — read the state

```!
python3.14 tests/loop_gate.py 2>&1 | tail -25
```

```!
grep -n '^todo ' tests/LOOP_LEDGER.md | head -3
```

Take the **first** `todo ` line. That is your assignment. Do not pick a
different one because it looks easier. Do not invent one.

If there are no `todo ` lines and the suites are green, say `LEDGER DRY` and
stop. Nothing else.

## Step 2 — reproduce before you believe it

Write a throwaway probe under `/tmp/` that drives the **real** services and
prints the behaviour you actually observe. The ledger line is a claim written by
something that was reading, not running. It may be wrong.

If the probe shows correct behaviour, the assignment was a false finding.
Change the prefix `todo ` to `void ` with a one-line reason, commit **only** the
ledger, and stop. Voiding a bad assignment is a successful iteration — it is the
main thing keeping this loop honest.

## Step 3 — make it fail in the suite, RED, before any fix

Add the check as a charge in `tests/tests_prosecutor.py` or as a rule in
`tests/tests_conformance.py`. Run it. It **must fail now**, against unmodified
product code. Commit the failing test on its own:

    git add tests/tests_prosecutor.py tests/LOOP_LEDGER.md
    git commit -m "test(prosecutor): <charge> -- RED, reproduces <ledger id>"

A test that passes before the fix is not evidence of a bug. If you cannot make
it fail, go back to Step 2 — you are probably about to fix something that works.

## Step 4 — fix the root cause

- `grep -rn` every caller of the function you are about to touch. First, not after.
- One guard in the shared function beats a guard in each caller. If an earlier
  fix was applied at a call site instead of in the function, that *is* the bug.
- The **service layer is the authorization boundary**. A fix that moves an authz
  check out of `services/` into a view, a router, or `command_registry.py` is
  wrong by construction. Adding a guard inside the service does **not** license
  removing the existing `IDENTITY_ARGS` entry — defence in depth stays.
- No minimalism on this project. It is an AML system. Fix the cause.
- Check the `auth_service is None` path still works — maintenance and CLI
  callers pass no auth service.

## Step 5 — cite evidence, or it is an opinion

Your commit message MUST contain a line shaped exactly like:

    Evidence: <path>:<line>

pointing at one of:

- a conformance/BRD rule the code violates,
- a docstring or comment in the file you edited that states the intended behaviour,
- two code paths that contradict each other — cite both.

If you cannot cite one, this is a **product decision, not a defect**. Move the
ledger line to `ask ` with your question and stop. The `commit-msg` hook rejects
messages with no `Evidence:` line.

## Step 6 — prove it and close the line

```!
python3.14 tests/loop_gate.py
```

Every suite green. Then flip the ledger line `todo ` → `done ` and append the
commit sha. Commit the fix with **named paths only**:

    git add <the files you actually changed> tests/LOOP_LEDGER.md
    git commit -m "fix(<scope>): <what changed>

    Evidence: <path>:<line>"

Never `git add -A`. Never `git add .`.

## Step 7 — Windows and packaged-build suspicions get parked, not fixed

If your root cause lands on `sys.platform`, `os.name`, `sys.frozen`,
`_MEIPASS`, `ctypes.windll`, PyInstaller, or real SMB: **stop**. You are on
macOS. You cannot falsify it here, and a green test run is not evidence about
the packaged Windows executable.

Append a row to `tests/WINDOWS_MANUAL.md`, set the ledger line to `park `, and
do not touch the code. Two Mac-authored fixes with passing tests have already
shipped broken to Windows in this repo.

## FORBIDDEN — the hooks enforce these

- Editing `tests/run_all.py`, `tests/loop_gate.py`, `tests/windows_only.txt`,
  `.gitignore`, `.claude/**`, or anything under `.git/`.
- Deleting or weakening any existing `check(`, `finding(`, `assert`, or
  `sys.exit` in `tests/`. Tests may only gain assertions, never lose them.
- Moving a suite into `LONG` in run_all.py to hide it from the gate.
- Editing any file listed in `tests/windows_only.txt`.
- `git push`, `git commit --amend`, `git clean`, `git restore`, `git checkout`,
  `git reset`, `git rebase`, `git config`, `--no-verify`.

## If you get stuck

Leave the test RED. Set the ledger line to `blocked ` with one line explaining
what you could not work out, and commit the red test plus the ledger.

A red test you do not understand is the correct end state. Do not delete it, do
not skip it, and do not claim the work is done.
