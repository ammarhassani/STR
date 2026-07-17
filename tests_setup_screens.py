"""Setup-wizard structural checks — the runtime nuke drives dialogs, not the
one-time setup screens, so these guard the class of bugs that slipped through:
dark-on-dark (Colors.DARK on a light-only app) and non-scrollable steps.
Flet can't render headless, so this builds the real wizard + drives Next and
asserts on the control tree. Run: python3.14 tests_setup_screens.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "flet_app"))
import flet as ft

_fail = 0
def check(label, cond, detail=""):
    global _fail
    ok = bool(cond)
    print(("PASS " if ok else "FAIL ") + label + ("" if ok else f"  -- {detail}"))
    if not ok:
        _fail += 1


class FakePage:
    def __init__(self):
        self.overlay = []; self.controls = []
    def update(self): pass
    def add(self, *c): self.controls.extend(c)
    def run_task(self, fn, *a): return None


def walk(c, seen=None):
    seen = seen or set()
    if c is None or id(c) in seen:
        return
    seen.add(id(c)); yield c
    for attr in ("controls", "content", "actions", "title", "leading", "trailing", "tabs"):
        v = getattr(c, attr, None)
        if isinstance(v, (list, tuple)):
            for x in v:
                yield from walk(x, seen)
        elif v is not None and "flet" in str(type(v)):
            yield from walk(v, seen)


def click_matching(tree, *subs):
    subs = [s.lower() for s in subs]
    for c in walk(tree):
        label = ""
        if isinstance(c, ft.Container) and getattr(c, "on_click", None):
            for t in walk(c):
                if isinstance(t, ft.Text) and t.value:
                    label += " " + t.value.lower()
        elif isinstance(c, (ft.ElevatedButton, ft.TextButton, ft.FilledButton)) and getattr(c, "text", None):
            label = str(c.text).lower()
        if label and any(s in label for s in subs) and getattr(c, "on_click", None):
            c.on_click(None); return True
    return False


DARK_BG = "#0d1117"   # Colors.DARK bg_primary — must never appear in a light-only app


def test_wizard_no_dark_and_scrolls():
    from theme.colors import Colors
    # 1) source-level: the wizard must not reach for the dark palette at all
    src = open(os.path.join("flet_app", "views", "setup_wizard_view.py")).read()
    check("wizard source does not use Colors.DARK", "Colors.DARK" not in src)

    from views.setup_wizard_view import build_setup_wizard
    page = FakePage()
    tree = build_setup_wizard(page, lambda *a, **k: None)

    def dark_containers(root):
        return [c for c in walk(root) if getattr(c, "bgcolor", None) == DARK_BG]

    check("welcome step: no dark-on-dark containers", len(dark_containers(tree)) == 0)

    # 2) drive Next -> the Configure Paths step, then assert light + scrollable
    check("Next advances to Configure Paths", click_matching(tree, "next"))
    dark = dark_containers(tree)
    check("paths step: no dark #0d1117 containers", len(dark) == 0, f"{len(dark)} dark containers")
    # the light palette bg must actually be light (sanity on the palette itself)
    check("light palette bg is light", Colors.get_palette("light")["bg_primary"].lower() != DARK_BG)
    # a Column in the tree must be scrollable so long steps can be reached
    scrollables = [c for c in walk(tree) if isinstance(c, ft.Column) and getattr(c, "scroll", None)]
    check("some step content is scrollable", len(scrollables) >= 1, "no scrollable Column found")


if __name__ == "__main__":
    test_wizard_no_dark_and_scrolls()
    print(f"\n{'ALL PASS' if _fail == 0 else str(_fail)+' FAILED'}")
    sys.exit(1 if _fail else 0)
