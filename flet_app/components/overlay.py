"""Showing and hiding dialogs and toasts without leaving a dead grey screen.

Two separate bugs live in this file's history; both produced the same symptom
and they need different fixes.

1. Dialogs and toasts were appended to `page.overlay` and never removed.
   Closing one only set `open = False`, so it stayed mounted. Open the report
   form ten times and the overlay held ten dead dialogs, each still drawing its
   modal barrier.

2. Closing was done with `page.update()`. Flet's own `Page.close()` calls
   `control.update()` -- it updates THE DIALOG, not the page. That difference
   is the "greyed out and unclickable" screen: after the shell is rebuilt (a
   forced password change happens right after `_show_main_app()` clears and
   redraws everything), a whole-page update does not reliably carry the
   dialog's `open = False` to Flutter. The barrier stays up over a fully
   rendered dashboard, and every click is swallowed.

So this module now delegates to Flet's own `page.open()` / `page.close()`,
which put the control in the offstage container and update the control itself.
The manual path is kept only as a fallback for objects Flet will not take.
"""
import flet as ft


def _is_dead(control) -> bool:
    """A dialog/sheet/snackbar that is mounted but no longer open."""
    return getattr(control, "open", None) is False


def prune(page) -> int:
    """Drop every closed control from page.overlay. Returns how many went.

    Only touches `page.overlay` -- what Flet's own open() uses (the offstage
    container) is Flet's to manage.
    """
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
    """Show `control`, preferring Flet's own dialog handling."""
    prune(page)
    opener = getattr(page, "open", None)
    if callable(opener):
        try:
            opener(control)
            return
        except Exception:
            pass  # fall through to the manual path below
    if control not in page.overlay:
        page.overlay.append(control)
    control.open = True
    if update:
        page.update()


def dismiss(page, control, update: bool = True):
    """Close `control` so its modal barrier actually goes away.

    page.close() updates the CONTROL. That is the part that matters: a
    page-wide update can lose the close when the page has been rebuilt
    underneath the dialog, which leaves the barrier painted over a live screen.

    The control is not removed from the tree here. Taking a dialog out in the
    same breath as closing it leaves Flutter believing the barrier is still up
    -- an earlier version of this file did exactly that. Cleanup happens in
    mount(), which prunes closed controls before adding a new one.
    """
    closer = getattr(page, "close", None)
    if callable(closer):
        try:
            closer(control)
            return
        except Exception:
            pass  # fall through

    control.open = False
    # Update the control itself first; the page update is a belt-and-braces
    # follow-up for the manual path.
    try:
        control.update()
    except Exception:
        pass
    if update:
        try:
            page.update()
        except Exception:
            pass
