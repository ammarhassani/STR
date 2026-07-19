"""Verify a built FIU_System.exe actually contains what it needs.

This exists because the build failed silently. `pyinstaller --onefile
flet_app/main.py` exited 0, produced a 70 MB .exe, and that .exe died on the
first fresh client PC with "No module named components" -- seven of the app's
own packages had never been bundled. A green build meant nothing.

So the build now inspects the artifact itself: the module table and the data
files are read back out of the .exe. Reading the PyInstaller build log is not
enough, because the log is what said everything was fine.

Run:  python tools/verify_build.py [path-to-exe]
"""
import os
import sys

# The bare-name packages that live under flet_app/. These are exactly what the
# old build dropped: flet_app is a package, so PyInstaller filed its children
# as `flet_app.components`, while main.py imports plain `components`.
REQUIRED_MODULES = (
    "components", "views", "theme", "router", "dialogs", "i18n",
    "app_state", "config", "services", "database", "utils",
)

# Read-only files the app opens at runtime through __file__. The path on the
# left is where the code looks for them inside the unpacked bundle.
REQUIRED_DATA = (
    os.path.join("database", "schema.sql"),
    os.path.join("database", "second_reasons.json"),
    os.path.join("assets", "logo.png"),
)


def verify(exe_path):
    from PyInstaller.archive.readers import CArchiveReader

    if not os.path.isfile(exe_path):
        return [f"{exe_path} does not exist -- the build did not produce an exe"]

    reader = CArchiveReader(exe_path)
    # The outer archive holds binaries and data files...
    outer = {str(n).replace("/", os.sep) for n in reader.toc}
    # ...while pure Python modules live in the embedded PYZ. Looking for them
    # in the outer table reports every module missing, including on a build
    # that works -- which is exactly what the first version of this script did.
    pyz_names = [n for n in reader.toc if str(n).lower().endswith(".pyz")]
    if not pyz_names:
        return ["the exe contains no PYZ archive -- it is not a valid "
                "PyInstaller bundle"]
    modules = set(reader.open_embedded_archive(pyz_names[0]).toc)

    problems = []

    for mod in REQUIRED_MODULES:
        # a package appears as its own name or as `name.something`
        if not any(n == mod or n.startswith(mod + ".") for n in modules):
            problems.append(
                f"module '{mod}' is missing from the bundle -- the exe will "
                f"raise ModuleNotFoundError on a PC without the source tree")

    for data in REQUIRED_DATA:
        if data not in outer:
            problems.append(
                f"data file '{data}' is missing from the bundle -- the app "
                f"looks for it at runtime")

    return problems


def main():
    exe = sys.argv[1] if len(sys.argv) > 1 else os.path.join("dist", "FIU_System.exe")
    problems = verify(exe)

    if problems:
        print(f"BUILD VERIFICATION FAILED: {len(problems)} problem(s)\n")
        for p in problems:
            print("  - " + p)
        print("\nDo NOT distribute this exe.")
        return 1

    size_mb = os.path.getsize(exe) / (1024 * 1024)
    print(f"Build verified: {exe} ({size_mb:.1f} MB)")
    print(f"  {len(REQUIRED_MODULES)} app packages present")
    print(f"  {len(REQUIRED_DATA)} runtime data files present")
    return 0


if __name__ == "__main__":
    sys.exit(main())
