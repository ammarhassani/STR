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

3. Same symptom, third cause, and the one that survived fix 2: `prune()` was
   unmounting the closed dialog a moment later, from Toast.show(). See prune().
"""
import weakref

import flet as ft

# Dialogs that have already survived one prune since they closed. The second
# prune takes them out. See prune() for why a closed dialog cannot be unmounted
# straight away, and why it must not be kept forever either.
_seen_closed = weakref.WeakSet()


def _is_dead(control) -> bool:
    """A dialog/sheet/snackbar that is mounted but no longer open."""
    return getattr(control, "open", None) is False


def prune(page) -> int:
    """Drop spent controls from page.overlay. Returns how many went.

    Snack bars go immediately. A dialog gets one prune of grace first, and that
    delay is the fix for the grey screen this module exists for:

    `page.overlay` is not a separate list from the one `page.open()` uses -- in
    flet 0.28.3 `Page.overlay` returns `self.__offstage.controls`, the very list
    `Page.open()` appends to (page.py:1373, page.py:1297). Removing a control
    from it emits a `remove` command against the LIVE tree. Flet pops an
    AlertDialog's Flutter route only when the widget rebuilds with `open=False`;
    unmount it in the same breath and the widget is destroyed mid-animation, the
    route never pops, and its ModalBarrier stays painted over a fully rendered
    screen that swallows every click.

    Commit 42b6ef1 took that removal out of dismiss() but left it here -- and
    Toast.show() calls prune() one line after a dialog closes. That is why the
    forced password change still greyed out after the "fix".

    One prune of grace, not forever: a closed dialog still costs an offstage
    entry, and this file's first bug was an analyst opening the report form over
    and over. Two prunes never land in the same frame -- each one is a separate
    user action -- so by the second the route has long since popped.
    """
    overlay = getattr(page, "overlay", None)
    if not overlay:
        return 0
    removed = 0
    for c in list(overlay):
        if not _is_dead(c):
            continue
        if not isinstance(c, ft.SnackBar) and c not in _seen_closed:
            try:
                _seen_closed.add(c)   # goes on the NEXT prune, not this one
            except TypeError:
                pass                  # not weak-referenceable: leave it mounted
            continue
        try:
            overlay.remove(c)
            _seen_closed.discard(c)
            removed += 1
        except ValueError:
            pass
    return removed


def mount(page, control, update: bool = True):
    """Show `control`, preferring Flet's own dialog handling."""
    prune(page)
    # Reopening a dialog object that was closed earlier: it is live again, so it
    # must earn its prune of grace afresh when it next closes.
    _seen_closed.discard(control)
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
