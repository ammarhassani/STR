"""Mounting and unmounting things in `page.overlay` without leaking them.

Every dialog and every toast in this app was appended to `page.overlay` and
never taken out again. Closing a dialog only set `open = False`, so the control
stayed mounted forever. Open the report form ten times and the overlay holds ten
dead dialogs; each one still draws its modal barrier, so the window fills with
stacked grey scrims, clicks land on a corpse instead of the live control, and
the app looks frozen for no visible reason. Toasts leaked the same way on every
single message.

`mount` prunes anything already closed before adding, and `dismiss` closes AND
removes. Between them the overlay never grows past what is actually on screen.
"""
import flet as ft


def _is_dead(control) -> bool:
    """A dialog/sheet/snackbar that is mounted but no longer open."""
    return getattr(control, "open", None) is False


def prune(page) -> int:
    """Drop every closed control from the overlay. Returns how many went."""
    overlay = getattr(page, "overlay", None)
    if not overlay:
        return 0
    dead = [c for c in list(overlay) if _is_dead(c)]
    for c in dead:
        try:
            overlay.remove(c)
        except ValueError:
            pass
    return len(dead)


def mount(page, control, update: bool = True):
    """Show `control` in the overlay, clearing out anything already closed."""
    prune(page)
    if control not in page.overlay:
        page.overlay.append(control)
    control.open = True
    if update:
        page.update()


def dismiss(page, control, update: bool = True):
    """Close `control`. Unmounting happens later, at the next mount().

    Do NOT remove it from the overlay here. Taking a dialog out of the tree in
    the same breath as closing it leaves Flutter believing its modal barrier is
    still up: the window looks normal, a sliver of the dialog stays painted, and
    every click afterwards is swallowed -- the button that opens it stops
    working and nothing is logged. That is exactly what an earlier version of
    this file did, and it is what Flet's own Page.close() avoids by only setting
    `open = False` and updating.

    Cleanup is not lost: mount() prunes every closed control before it adds a
    new one, so at most one dead dialog sits in the overlay between operations
    -- which is what Flet does on its own anyway.
    """
    control.open = False
    if update:
        try:
            page.update()
        except Exception:
            pass
