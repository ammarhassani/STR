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
    """Close `control` AND unmount it, so it cannot linger over the page."""
    control.open = False
    try:
        page.overlay.remove(control)
    except (ValueError, AttributeError):
        pass
    if update:
        try:
            page.update()
        except Exception:
            pass
