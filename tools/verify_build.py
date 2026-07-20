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

# The native window is launched by this. Without it the app silently falls back
# to a browser view, and a windowed exe has no stdout, so uvicorn's logger dies
# with "Unable to configure formatter 'default'" before anything is drawn. That
# is what happened on the first real client PC: this developer machine had the
# client cached in ~/.flet and never took the fallback.
REQUIRED_BINARY = os.path.join("flet_desktop", "app", "flet", "flet.exe")

# The panel reads the heartbeat, the queue and config; it never opens the
# report database or builds app views, so it needs far less than the app. This
# list is the actual import closure of panel_main -> control_panel_ui ->
# panel_controller -> host.*, not a guess at what "an app" needs.
PANEL_MODULES = ("panel", "config", "utils", "host")
PANEL_DATA = (os.path.join("assets", "logo.png"),)


def verify(exe_path, panel=False):
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

    want_modules = PANEL_MODULES if panel else REQUIRED_MODULES
    want_data = PANEL_DATA if panel else REQUIRED_DATA

    for mod in want_modules:
        # a package appears as its own name or as `name.something`
        if not any(n == mod or n.startswith(mod + ".") for n in modules):
            problems.append(
                f"module '{mod}' is missing from the bundle -- the exe will "
                f"raise ModuleNotFoundError on a PC without the source tree")

    for data in want_data:
        if data not in outer:
            problems.append(
                f"data file '{data}' is missing from the bundle -- the app "
                f"looks for it at runtime")

    if REQUIRED_BINARY not in outer:
        problems.append(
            f"'{REQUIRED_BINARY}' is missing -- without the bundled desktop "
            f"client the app falls back to a browser view and then dies in "
            f"uvicorn, because a windowed exe has no stdout")

    return problems


def _report(exe, panel=False):
    problems = verify(exe, panel=panel)
    label = "Control Panel" if panel else "App"
    if problems:
        print(f"\n{label} FAILED VERIFICATION: {len(problems)} problem(s)")
        for p in problems:
            print("  - " + p)
        return 1
    size_mb = os.path.getsize(exe) / (1024 * 1024)
    print(f"ok  {label:<14} {os.path.basename(exe)} ({size_mb:.1f} MB)")
    return 0


def main():
    if len(sys.argv) > 1:
        # An explicit path: verify just that one, guessing its kind by name.
        exe = sys.argv[1]
        return _report(exe, panel="panel" in os.path.basename(exe).lower())

    rc = _report(os.path.join("dist", "FIU_System.exe"))
    panel_exe = os.path.join("dist", "FIU_Control_Panel.exe")
    if os.path.exists(panel_exe):
        rc |= _report(panel_exe, panel=True)
    else:
        print("note: dist\\FIU_Control_Panel.exe not built")

    if rc:
        print("\nDo NOT distribute these.")
    return rc


if __name__ == "__main__":
    sys.exit(main())
