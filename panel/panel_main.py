"""Entry point for the standalone Control Panel executable.

The panel is also reachable from the app's login screen, which covers the
normal case. This exists for the case that motivated it: when the app itself
will not start on a PC, the login screen never appears, so the button on it is
useless exactly when someone needs to find out why. A separate executable still
opens.

It deliberately shares no state with the app beyond config.json and the shared
folder, so it can report on a broken installation without depending on it.
"""
import os
import sys

# Same layout main.py sets up: the app's packages are imported bare
# (`from components... import`), which only resolves with flet_app on the path.
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (_ROOT, os.path.join(_ROOT, "flet_app")):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def main():
    # This executable takes no arguments. It used to accept and silently ignore
    # them, which is how "Start host on this PC" could launch a second copy of
    # the PANEL with --host and look like it had done something. Refusing loudly
    # means a future misroute names itself instead of dying later inside
    # PyInstaller's shared temp directory.
    if len(sys.argv) > 1:
        raise SystemExit(
            f"FIU_Control_Panel.exe takes no arguments (got {sys.argv[1:]}). "
            f"Host and client modes live in FIU_System.exe.")
    from panel.control_panel_ui import main as panel_main
    panel_main()


if __name__ == "__main__":
    main()
