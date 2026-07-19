"""The overlay must never accumulate dead controls. Run: python tests_overlay_leak.py

Every dialog and toast was appended to page.overlay and never removed: closing
only set open=False. Dead dialogs keep drawing their modal barrier, so after a
few open/close cycles the window fills with stacked grey scrims, clicks land on
a corpse, and the app appears frozen with nothing in the UI to explain it.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'flet_app'))

_fail = 0
def check(label, cond, detail=""):
    global _fail
    ok = bool(cond)
    print(("PASS " if ok else "FAIL ") + label + ("" if ok else f"  -- {detail}"))
    if not ok:
        _fail += 1


class FakePage:
    def __init__(self):
        self.overlay = []
        self.snack_bar = None
    def update(self): pass
    def run_task(self, fn, *a): pass


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
    check("mounting clears anything already closed", len(page.overlay) == 1, len(page.overlay))


def test_repeated_dialog_cycles_do_not_pile_up():
    """The symptom the user hit: open/close a form repeatedly, screen goes grey."""
    from components.overlay import mount, dismiss
    import flet as ft
    page = FakePage()
    for _ in range(25):
        d = ft.AlertDialog(content=ft.Text("form"))
        mount(page, d)
        dismiss(page, d)
    # at most ONE closed dialog waits to be pruned -- the growth is what matters
    check("25 open/close cycles leave at most one closed dialog behind",
          len(page.overlay) <= 1, len(page.overlay))
    check("and the one left is closed, not covering the page",
          all(getattr(c, "open", None) is False for c in page.overlay),
          [getattr(c, "open", None) for c in page.overlay])
    mount(page, ft.AlertDialog(content=ft.Text("next")))
    check("the next open prunes it", len(page.overlay) == 1, len(page.overlay))


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
    test_repeated_dialog_cycles_do_not_pile_up()
    test_toasts_do_not_stack()
    test_refused_form_still_explains_itself()
    print(f"\n{'ALL PASS' if _fail == 0 else str(_fail) + ' FAILED'}")
    sys.exit(1 if _fail else 0)
