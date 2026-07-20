"""Run the STR test suites.

    python tests/run_all.py            # the standard suites (a few minutes)
    python tests/run_all.py --all      # including the long simulations
    python tests/run_all.py roles fiu  # only suites matching these words

Run it from the repo root. Each suite is a normal script that exits non-zero on
failure; this just runs them and reports which ones failed.
"""
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

# These take minutes each (multi-process simulations, browser drivers), so they
# are opt-in. They are NOT less important -- the warzone and the fortnight
# simulation have found defects nothing else did.
LONG = {
    "tests_warzone.py",
    "tests_simulation_fortnight.py",
    "tests_smb_faults.py",
    "tests_ui_nuke.py",
    "tests_ui_driver.py",
}


def suites():
    return sorted(f for f in os.listdir(HERE)
                  if f.startswith("tests_") and f.endswith(".py"))


def main():
    args = [a for a in sys.argv[1:]]
    run_long = "--all" in args
    filters = [a.lower() for a in args if not a.startswith("--")]

    chosen = []
    for name in suites():
        if name in LONG and not run_long:
            continue
        if filters and not any(f in name.lower() for f in filters):
            continue
        chosen.append(name)

    if not chosen:
        print("no suites matched")
        return 1

    print(f"running {len(chosen)} suite(s)\n")
    failed, started = [], time.time()

    for name in chosen:
        t0 = time.time()
        r = subprocess.run([sys.executable, os.path.join(HERE, name)],
                           cwd=REPO, capture_output=True, text=True)
        # Each suite reports its own way. Missing a keyword here means a suite
        # that found real defects still prints a blank summary line, which is
        # the opposite of what a runner is for -- so cover every wording used.
        tail = [l for l in (r.stdout or "").splitlines()
                if any(k in l for k in ("TOTAL", "ALL PASS", "FAILED",
                                        "FAILURES", "Conformance", "VULNERAB",
                                        "VERDICT", "distinct defects",
                                        "SIMULATION", "checks passed"))]
        status = "ok  " if r.returncode == 0 else "FAIL"
        print(f"{status} {name:<34} {time.time() - t0:5.1f}s  "
              f"{tail[-1].strip() if tail else ''}")
        if r.returncode != 0:
            failed.append(name)
            # On failure the detail is what matters, so show it rather than
            # making someone re-run the suite by hand to find out why.
            for line in (r.stdout or "").splitlines():
                if "FAIL" in line:
                    print("        " + line.strip())
            if r.stderr:
                print("        " + r.stderr.strip().splitlines()[-1])

    print(f"\n{len(chosen) - len(failed)}/{len(chosen)} suites passed "
          f"in {time.time() - started:.0f}s")
    if failed:
        print("FAILED: " + ", ".join(failed))
    if not run_long:
        print(f"({len(LONG)} long simulations skipped -- run with --all)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
