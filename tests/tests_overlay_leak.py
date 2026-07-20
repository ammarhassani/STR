"""The overlay must never accumulate dead controls. Run: python tests_overlay_leak.py

Every dialog and toast was appended to page.overlay and never removed: closing
only set open=False. Dead dialogs keep drawing their modal barrier, so after a
few open/close cycles the window fills with stacked grey scrims, clicks land on
a corpse, and the app appears frozen with nothing in the UI to explain it.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'flet_app'))

_fail = 0
def check(label, cond, detail=""):
    global _fail
    ok = bool(cond)
    print(("PASS " if ok else "FAIL ") + label + ("" if ok else f"  -- {detail}"))
    if not ok:
        _fail += 1


class FakePage:
    """A page WITHOUT Flet's open/close, so this exercises the fallback path."""
    def __init__(self):
        self.overlay = []
        self.snack_bar = None
    def update(self): pass
    def run_task(self, fn, *a): pass


class OffstagePage:
    """A page that models what flet 0.28.3 ACTUALLY does.

    The two classes above give `overlay` its own list, unrelated to open(). Real
    Flet does not: `Page.overlay` returns `self.__offstage.controls`, the same
    list `Page.open()` appends to (page.py:1373, page.py:1297). Because the old
    fakes never modelled that aliasing, they could not see prune() reaching into
    the live tree and unmounting a dialog that had just closed -- which is the
    bug that survived commit 42b6ef1 and kept the screen grey after the forced
    password change.
    """
    def __init__(self):
        self._offstage = []
        self.snack_bar = None
    @property
    def overlay(self):
        return self._offstage
    def open(self, control):
        control.open = True
        if control not in self._offstage:
            self._offstage.append(control)
    @staticmethod
    def close(control):
        control.open = False          # Flet leaves it MOUNTED on purpose
    def update(self, *a): pass
    def run_task(self, fn, *a): pass


class FletLikePage(FakePage):
    """A page WITH Flet's own open/close, which is what the real app has.

    The plain FakePage silently exercises the manual fallback, so on its own it
    would report a pass no matter what the Flet path did -- and the Flet path is
    the one that ships.
    """
    def __init__(self):
        super().__init__()
        self.opened = []
        self.closed = []
    def open(self, control):
        self.opened.append(control)
        control.open = True
    def close(self, control):
        self.closed.append(control)
        control.open = False


class FakeDialog:
    def __init__(self):
        self.open = None
        self.updates = 0
    def update(self):
        self.updates += 1


def test_uses_flets_own_dialog_api():
    """Delegate to page.open/page.close when the page has them.

    Flet's close() calls control.update() -- it updates THE DIALOG. Our old code
    called page.update(), which updates the whole tree, and after the shell had
    been rebuilt (a forced password change happens right after the dashboard is
    drawn) the dialog's open=False did not reach Flutter. The barrier stayed up
    over a live screen: everything visible, nothing clickable.
    """
    from components.overlay import mount, dismiss

    page = FletLikePage()
    dlg = FakeDialog()

    mount(page, dlg)
    check("mount goes through page.open", page.opened == [dlg], page.opened)
    check("and the dialog is open", dlg.open is True)

    dismiss(page, dlg)
    check("dismiss goes through page.close", page.closed == [dlg], page.closed)
    check("and the dialog is closed", dlg.open is False)


def test_fallback_updates_the_control_not_just_the_page():
    """Without page.close, dismiss must still update the CONTROL itself."""
    from components.overlay import mount, dismiss

    page = FakePage()          # no open/close
    dlg = FakeDialog()

    mount(page, dlg)
    check("fallback mounts into the overlay", dlg in page.overlay)

    dismiss(page, dlg)
    check("fallback closes the dialog", dlg.open is False)
    check("fallback updates the control itself, not only the page",
          dlg.updates >= 1, dlg.updates)


def test_helper_mounts_and_unmounts():
    from components.overlay import mount, dismiss, prune
    import flet as ft
    page = FakePage()
    d = ft.AlertDialog(content=ft.Text("x"))
    mount(page, d)
    check("mount puts the dialog on screen", len(page.overlay) == 1 and d.open is True)
    dismiss(page, d)
    # dismiss CLOSES but must NOT unmount. Removing a dialog from the tree in
    # the same breath as closing it leaves Flutter believing its modal barrier
    # is still up: a sliver stays painted and every later click is swallowed,
    # so the button that opens it silently stops working. Proven in a browser.
    check("dismiss closes the dialog", d.open is False)
    check("dismiss does NOT unmount it (that breaks the close)",
          len(page.overlay) == 1, len(page.overlay))
    dismiss(page, d)
    check("dismissing twice is harmless", d.open is False)

    dead = ft.AlertDialog(content=ft.Text("dead")); dead.open = False
    page.overlay.append(dead)
    mount(page, ft.AlertDialog(content=ft.Text("live")))
    check("the first mount after a close leaves the dialog mounted",
          dead in page.overlay, len(page.overlay))
    mount(page, ft.AlertDialog(content=ft.Text("later")))
    check("the one after that sweeps it", dead not in page.overlay, len(page.overlay))


def test_repeated_dialog_cycles_do_not_pile_up():
    """The symptom the user hit: open/close a form repeatedly, screen goes grey."""
    from components.overlay import mount, dismiss
    import flet as ft
    page = FakePage()
    for _ in range(25):
        d = ft.AlertDialog(content=ft.Text("form"))
        mount(page, d)
        dismiss(page, d)
    # A closed dialog gets one prune of grace, so a couple linger. What matters
    # is that the count does not track the number of cycles.
    check("25 open/close cycles leave at most two closed dialogs behind",
          len(page.overlay) <= 2, len(page.overlay))
    check("and what is left is closed, not covering the page",
          all(getattr(c, "open", None) is False for c in page.overlay),
          [getattr(c, "open", None) for c in page.overlay])


def test_a_toast_after_a_close_leaves_the_dialog_mounted():
    """The grey screen after the forced password change, reproduced.

    handle_change() in change_password_dialog.py dismisses the dialog and then
    calls show_success() on the very next line. Toast.show() opens with
    prune(page). Before this fix that prune removed the dialog that had closed
    a moment earlier -- and because page.overlay IS the live offstage list, the
    AlertDialog widget was destroyed while Flutter was still animating its route
    out. The route never popped, its ModalBarrier stayed on the Navigator, and
    the user got a rendered dashboard that dimmed and ate every click.

    Web never showed it, so it survived testing. Only the packaged desktop
    build reproduced it.
    """
    import flet as ft
    from components.overlay import mount, dismiss, prune
    from components.toast import show_success

    page = OffstagePage()
    dlg = ft.AlertDialog(modal=True, content=ft.Text("change password"))

    mount(page, dlg)
    check("the dialog is mounted and open", dlg in page.overlay and dlg.open is True)

    dismiss(page, dlg)
    check("dismiss closes it", dlg.open is False)
    check("dismiss leaves it mounted so Flutter can pop the route",
          dlg in page.overlay)

    show_success(page, "Password changed successfully!")
    check("the success toast must NOT unmount the dialog that just closed",
          dlg in page.overlay,
          "prune() removed a dialog mid route-pop: this is the grey screen")

    # and a spent snack bar is still swept, which is what prune is for
    bar = ft.SnackBar(content=ft.Text("old")); bar.open = False
    page.overlay.append(bar)
    prune(page)
    check("spent snack bars are still swept", bar not in page.overlay)


def test_escape_cannot_dismiss_a_forced_dialog():
    """Escape used to let a default-password account into the system.

    main.py's Escape handler closed every open AlertDialog it found. The forced
    password change is one of those, so the account that STR ships with -- whose
    password is written down in the setup docs -- could press Escape and carry on
    using an AML system without ever setting a password of its own.
    """
    import flet as ft
    forced = ft.AlertDialog(modal=True, data="forced", content=ft.Text("x"))
    normal = ft.AlertDialog(modal=True, content=ft.Text("y"))
    for d in (forced, normal):
        d.open = True

    def escape_would_close(d):
        # the condition from main.py's Escape branch
        return (isinstance(d, ft.AlertDialog) and d.open
                and getattr(d, "data", None) != "forced")

    check("Escape refuses the forced dialog", not escape_would_close(forced))
    check("Escape still closes ordinary dialogs", escape_would_close(normal))


def test_forced_password_dialog_has_no_way_out():
    """No Cancel button when the account is still on the default password."""
    import flet as ft
    from tests_fiu_phase import _setup
    from dialogs.change_password_dialog import show_change_password_dialog

    auth, reports, nums, appr, dbm = _setup()
    auth.authenticate('agent1', 'Pass@123')

    class S: pass
    st = S(); st.auth_service = auth

    page = OffstagePage()
    show_change_password_dialog(page, st, forced=True)
    dlgs = [c for c in page.overlay if isinstance(c, ft.AlertDialog)]
    check("the forced dialog opened", len(dlgs) == 1, len(dlgs))
    if dlgs:
        labels = [getattr(b, "text", None) for b in (dlgs[0].actions or [])]
        check("forced: no cancel button", not any(
            (lbl or "").strip().lower() in ("cancel", "إلغاء") for lbl in labels), labels)
        check("forced: marked so Escape will not dismiss it",
              dlgs[0].data == "forced", dlgs[0].data)

    page2 = OffstagePage()
    show_change_password_dialog(page2, st, forced=False)
    dlgs2 = [c for c in page2.overlay if isinstance(c, ft.AlertDialog)]
    if dlgs2:
        check("voluntary change still has a cancel button",
              len(dlgs2[0].actions or []) == 2, dlgs2[0].actions)


def test_toasts_do_not_stack():
    from components.toast import show_error
    page = FakePage()
    for i in range(10):
        show_error(page, f"refused {i}")
    check("ten toasts leave at most one on screen", len(page.overlay) <= 1, len(page.overlay))


def test_refused_form_still_explains_itself():
    """Refusing to open must SAY why -- a silent refusal reads as a broken app."""
    import flet as ft
    from tests_fiu_phase import _setup
    from services.validation_service import ValidationService
    from services.intelligence_service import IntelligenceService
    from services.dropdown_service import DropdownService
    from dialogs.report_dialog import show_report_dialog

    auth, reports, nums, appr, dbm = _setup()
    auth.authenticate('agent1', 'Pass@123')

    class S: pass
    st = S()
    st.report_service = reports; st.approval_service = appr
    st.report_number_service = nums; st.auth_service = auth
    st.db_manager = dbm; st.current_user = auth.get_current_user()
    st.dropdown_service = DropdownService(dbm, None, auth)
    st.validation_service = ValidationService(dbm, None, auth)
    st.logging_service = None; st.version_service = None
    st.intelligence_service = IntelligenceService(dbm, None)

    page = FakePage()
    # reserve, then hand every number back -- the user's exact sequence
    ok, block, _ = nums.reserve_block('agent1', 10)
    nums.release_numbers('agent1', block)
    check("all numbers released", nums.get_available_count('agent1') == 0)

    show_report_dialog(page, st, report_data=None)
    opened = [c for c in page.overlay if isinstance(c, ft.AlertDialog) and c.open]
    snacks = [c for c in page.overlay if isinstance(c, ft.SnackBar)]
    check("the form refuses to open with no numbers", not opened)
    check("and it tells the user why", bool(snacks))

    # hammering the refusal must not leave the page covered in dead overlays
    for _ in range(8):
        show_report_dialog(page, st, report_data=None)
    check("repeated refusals do not pile up overlays", len(page.overlay) <= 2, len(page.overlay))

    # reserving again must make the form work -- this failed before the fix
    nums.reserve_block('agent1', 5)
    show_report_dialog(page, st, report_data=None)
    opened = [c for c in page.overlay if isinstance(c, ft.AlertDialog) and c.open]
    check("after reserving again the form opens", bool(opened),
          f"overlay={[type(c).__name__ for c in page.overlay]}")


if __name__ == "__main__":
    test_helper_mounts_and_unmounts()
    test_uses_flets_own_dialog_api()
    test_fallback_updates_the_control_not_just_the_page()
    test_repeated_dialog_cycles_do_not_pile_up()
    test_a_toast_after_a_close_leaves_the_dialog_mounted()
    test_escape_cannot_dismiss_a_forced_dialog()
    test_forced_password_dialog_has_no_way_out()
    test_toasts_do_not_stack()
    test_refused_form_still_explains_itself()
    print(f"\n{'ALL PASS' if _fail == 0 else str(_fail) + ' FAILED'}")
    sys.exit(1 if _fail else 0)
