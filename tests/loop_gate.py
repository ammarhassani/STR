#!/usr/bin/env python3.14
"""The bug-hunt loop's only success oracle. Exit 0 means STOP.

Why this exists rather than pointing the loop at run_all.py:

run_all.py is a pure function of the source tree, over a suite that is mostly
frozen tripwires. Once it is green it stays green, so a loop driven by it gets
an identical prompt against an identical world on every iteration after the
first. That is where autonomous loops go wrong -- with no work left and no way
to say so, an agent invents findings or refactors code that was fine.

So the gate reads a LEDGER as well. The ledger only ever shrinks, which gives
the loop an input that converges and a termination condition that is a shell
exit code rather than a sentence the agent is free to type.

Exit 0 requires BOTH:
  - every suite in run_all.py passes, and
  - no `todo ` or `blocked ` lines remain in LOOP_LEDGER.md

Run: python3.14 tests/loop_gate.py
"""
import os
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).parent
LEDGER = HERE / "LOOP_LEDGER.md"
OPEN_PREFIXES = ("todo ", "blocked ")


def main():
    # Printed every iteration on purpose. A green run here is evidence about
    # this interpreter on this OS -- it says nothing about the packaged Windows
    # executable the bank actually runs, and the loop must not forget that.
    print(f"interpreter: {sys.version.split()[0]} / {sys.platform}"
          f"   (workstation is 3.11 / win32)")
    print(f"STR_SEED={os.environ.get('STR_SEED', '0')}")
    print(flush=True)   # ahead of the subprocess, not buffered behind it

    rc = subprocess.run([sys.executable, str(HERE / "run_all.py")]).returncode

    if not LEDGER.exists():
        print(f"\nno ledger at {LEDGER} -- nothing to hunt")
        return rc

    lines = LEDGER.read_text(encoding="utf-8").splitlines()
    open_items = [l for l in lines if l.startswith(OPEN_PREFIXES)]
    counts = {}
    for l in lines:
        p = l.split(" ", 1)[0]
        if p in ("todo", "done", "void", "park", "ask", "blocked"):
            counts[p] = counts.get(p, 0) + 1

    print("\nledger: " + "  ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    if open_items:
        print("NEXT: " + open_items[0])
    elif rc == 0:
        print("LEDGER DRY -- suites green and no assignments left")

    # rc wins: a red suite is never "done", even with an empty ledger.
    return rc or (1 if open_items else 0)


if __name__ == "__main__":
    sys.exit(main())
