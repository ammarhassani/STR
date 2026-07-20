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
    from panel.control_panel_ui import main as panel_main
    panel_main()


if __name__ == "__main__":
    main()
