"""The gate that watches the gate. Run: python tests_gate_integrity.py

Every other suite here checks the product. This one checks that the checking
still works, because a test harness fails silently: a suite that cannot go red
reports "ok" forever and nobody notices.

That is not hypothetical. tests_ui_driver.py ran 60 UI checks and always exited
0, because its __main__ called run() and threw away the failure count it
returned. run_all.py printed "ok" for it on every run it ever did.

An autonomous loop with commit rights makes this worse: the cheapest way to turn
a red suite green is to break the suite. So the properties below are asserted,
not trusted.
"""
import glob
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)


def _hooks_dir():
    """Where the hooks actually live.

    Not REPO/.git/hooks: the loop runs in a git WORKTREE, where .git is a FILE
    pointing at the real git dir, and hooks are shared from the common dir. This
    check reported every hook missing when run from the worktree -- i.e. it went
    red in exactly the place it was written to protect.
    """
    out = subprocess.run(["git", "rev-parse", "--git-common-dir"],
                         cwd=REPO, capture_output=True, text=True)
    common = out.stdout.strip() or os.path.join(REPO, ".git")
    if not os.path.isabs(common):
        common = os.path.join(REPO, common)
    return os.path.join(common, "hooks")

_fail = 0


def check(label, cond, detail=""):
    global _fail
    ok = bool(cond)
    print(("PASS " if ok else "FAIL ") + label + ("" if ok else f"  -- {detail}"))
    if not ok:
        _fail += 1


def test_every_suite_can_actually_fail():
    """A suite whose __main__ cannot exit non-zero is decoration."""
    for path in sorted(glob.glob(os.path.join(HERE, "tests_*.py"))):
        name = os.path.basename(path)
        if name == os.path.basename(__file__):
            continue
        src = open(path, encoding="utf-8").read()
        if "__main__" not in src:
            check(f"{name} has a __main__ block", False, "no entry point")
            continue
        tail = src.split("__main__")[-1]
        check(f"{name} exits non-zero on failure", "sys.exit" in tail,
              "__main__ discards the result, so run_all always sees success")


def test_the_commit_holes_are_closed():
    """An unattended loop must not be able to stage bank data or agent config."""
    for p in ("cbox/x.db", "export.xlsx", "rows.csv", "local.sqlite",
              ".claude/settings.local.json", ".loop/gate.txt"):
        rc = subprocess.run(["git", "check-ignore", "-q", p],
                            cwd=REPO).returncode
        check(f"{p} is gitignored", rc == 0)


def test_the_hooks_are_installed_and_armed():
    hooks = _hooks_dir()
    tracked = os.path.join(REPO, "tools", "hooks")
    for hook in ("pre-commit", "commit-msg", "pre-push"):
        p = os.path.join(hooks, hook)
        src = os.path.join(tracked, hook)
        check(f"{hook} is in tools/hooks (reviewable)", os.path.isfile(src), src)
        check(f"{hook} hook is installed", os.path.isfile(p),
              f"{p} -- run tools/install_hooks.sh")
        check(f"{hook} hook is executable", os.access(p, os.X_OK), p)
        # An installed hook that has drifted from the reviewed copy is a guard
        # rail nobody has read. Editing .git/hooks is also how you would quietly
        # disarm one.
        if os.path.isfile(p) and os.path.isfile(src):
            check(f"{hook} matches the reviewed copy",
                  open(p, encoding="utf-8").read()
                  == open(src, encoding="utf-8").read(),
                  "installed hook differs from tools/hooks -- rerun install_hooks.sh")

    pre = os.path.join(hooks, "pre-commit")
    if os.path.isfile(pre):
        src = open(pre, encoding="utf-8").read()
        # The rule that cannot be expressed as a prompt line.
        check("pre-commit refuses diffs that delete test assertions",
              "check\\(|finding\\(|assert |sys\\.exit" in src or "check(" in src)
        check("pre-commit runs the suite", "run_all.py" in src)


def test_the_platform_fence_names_real_lines():
    """A fence pointing at files that no longer exist protects nothing."""
    fence = os.path.join(HERE, "windows_only.txt")
    check("windows_only.txt exists", os.path.isfile(fence))
    if not os.path.isfile(fence):
        return
    listed = 0
    for raw in open(fence, encoding="utf-8"):
        line = raw.split("#")[0].strip()
        if not line:
            continue
        rel = line.split(":")[0].strip()
        listed += 1
        check(f"fenced path exists: {rel}",
              os.path.exists(os.path.join(REPO, rel)))
    check("the fence is not empty", listed > 0, listed)


def test_the_ledger_is_well_formed():
    """The loop's only convergence signal. A malformed prefix stalls it."""
    led = os.path.join(HERE, "LOOP_LEDGER.md")
    check("LOOP_LEDGER.md exists", os.path.isfile(led))
    if not os.path.isfile(led):
        return
    valid = ("todo ", "done ", "void ", "park ", "ask ", "blocked ")
    entries = 0
    for i, raw in enumerate(open(led, encoding="utf-8"), 1):
        first = raw.split(" ", 1)[0]
        if first in ("todo", "done", "void", "park", "ask", "blocked"):
            entries += 1
            check(f"ledger line {i} has an id and a target",
                  raw.count("|") >= 2, raw.strip()[:70])
            check(f"ledger line {i} uses a known prefix",
                  raw.startswith(valid), raw.strip()[:40])
    check("the ledger has entries", entries > 0, entries)


if __name__ == "__main__":
    test_every_suite_can_actually_fail()
    test_the_commit_holes_are_closed()
    test_the_hooks_are_installed_and_armed()
    test_the_platform_fence_names_real_lines()
    test_the_ledger_is_well_formed()
    print(f"\n{'ALL PASS' if _fail == 0 else str(_fail) + ' FAILED'}")
    sys.exit(1 if _fail else 0)
