"""SearchableDropdown logic — run: python3.14 tests_dropdown.py"""
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


def opts(*pairs):
    return [ft.dropdown.Option(key=k, text=t) for k, t in pairs]


def test_filter():
    from components.searchable_dropdown import filter_options
    o = opts(("", "-- Select --"), ("sa", "Saudi Arabian"), ("eg", "Egyptian"), ("sy", "Syrian"))
    check("empty query returns all REAL options (placeholder dropped)",
          [x.key for x in filter_options(o, "")] == ["sa", "eg", "sy"])
    check("filter is case-insensitive substring on text",
          [x.key for x in filter_options(o, "sa")] == ["sa"])
    check("filter matches 'y' across text", set(x.key for x in filter_options(o, "y")) == {"eg", "sy"})
    check("filter matches on key too", [x.key for x in filter_options(o, "eg")] == ["eg"])
    check("no match -> empty", filter_options(o, "zzz") == [])


def test_surface():
    from components.searchable_dropdown import SearchableDropdown, _display_text
    o = opts(("", "-- Select --"), ("sa", "Saudi Arabian"), ("eg", "Egyptian"))
    sd = SearchableDropdown(options=o, label="Nationality", width=200)
    check("empty-key placeholder stripped from .options", [x.key for x in sd.options] == ["sa", "eg"])
    check("initial value None", sd.value is None)
    # set value -> field shows the option's display text
    sd.value = "eg"
    check("value setter works", sd.value == "eg")
    check("field text reflects selection", sd._field.value == "Egyptian", sd._field.value)
    # options setter also strips placeholder
    sd.options = opts(("", "x"), ("q", "Qatari"))
    check("options setter strips placeholder", [x.key for x in sd.options] == ["q"])


def test_pick_fires_on_change_and_typing_does_not():
    from components.searchable_dropdown import SearchableDropdown
    o = opts(("sa", "Saudi Arabian"), ("eg", "Egyptian"))
    fired = {"n": 0, "last": None}
    sd = SearchableDropdown(options=o, on_change=lambda e: (fired.__setitem__("n", fired["n"] + 1),
                                                            fired.__setitem__("last", e.control.value)))
    # simulate typing "egy" -> filters, must NOT set value or fire on_change
    sd._field.value = "egy"
    sd._on_type(type("E", (), {})())
    check("typing does not set value", sd.value is None)
    check("typing does not fire on_change", fired["n"] == 0)
    # the filtered list should now have exactly Egyptian; click its row
    rows = [c for c in sd._list.controls if getattr(c, "on_click", None)]
    check("filter narrowed to 1 row (Egyptian)", len(rows) == 1)
    rows[0].on_click(type("E", (), {})())
    check("clicking a row sets value", sd.value == "eg", sd.value)
    check("clicking fires on_change with the new value", fired["n"] == 1 and fired["last"] == "eg")
    check("field shows picked text", sd._field.value == "Egyptian", sd._field.value)




# ---------------------------------------------------------------------------
# Component-level interaction tests.
#
# These drive the dropdown the way a user does -- open, click a row, reopen,
# click another -- instead of assigning .value directly. Every earlier UI test
# set .value, so a bug that made re-selection impossible (the menu opened
# filtered by the CURRENT selection, leaving one row) passed everything.
# ---------------------------------------------------------------------------
def _sd(values):
    import flet as ft
    from components.searchable_dropdown import SearchableDropdown
    return SearchableDropdown(
        options=[ft.dropdown.Option(key=v, text=v) for v in values])


def _rows(d):
    return [c.content.value for c in d._list.controls
            if hasattr(c.content, "value") and c.content.value != "No matches"]


def _click(d, text):
    for c in d._list.controls:
        if getattr(c.content, "value", None) == text:
            c.on_click(None)
            return True
    return False


def test_dropdown_can_change_its_mind():
    d = _sd(["Male", "Female"])
    d._open_menu()
    check("menu opens with every option", _rows(d) == ["Male", "Female"], _rows(d))
    check("picking Female works", _click(d, "Female") and d.value == "Female", d.value)

    d._open_menu()
    check("reopening still shows every option (not just the chosen one)",
          _rows(d) == ["Male", "Female"], _rows(d))
    check("the choice can be changed back", _click(d, "Male") and d.value == "Male", d.value)

    # and again, several times over
    for want in ("Female", "Male", "Female"):
        d._open_menu()
        _click(d, want)
        check(f"switched to {want}", d.value == want, d.value)


def test_dropdown_typing_still_filters():
    d = _sd(["Saudi Arabian", "Egyptian", "Emirati"])
    d._open_menu()
    d._field.value = "emir"
    d._on_type(None)
    check("typing narrows the list", _rows(d) == ["Emirati"], _rows(d))
    check("a filtered pick sets the value", _click(d, "Emirati") and d.value == "Emirati", d.value)
    # after that pick, the next open must NOT still be filtered by 'Emirati'
    d._open_menu()
    check("the filter does not survive into the next open",
          len(_rows(d)) == 3, _rows(d))


def test_dropdown_blur_keeps_the_selection():
    d = _sd(["Male", "Female"])
    d._open_menu(); _click(d, "Female")
    d._field.value = "half typed nonsense"
    d._on_blur(None)
    check("free text is discarded on blur", d.value == "Female", d.value)
    check("the field shows the selection again", d._field.value == "Female", d._field.value)

if __name__ == "__main__":
    test_filter()
    test_surface()
    test_pick_fires_on_change_and_typing_does_not()
    test_dropdown_can_change_its_mind()
    test_dropdown_typing_still_filters()
    test_dropdown_blur_keeps_the_selection()
    print(f"\n{'ALL PASS' if _fail == 0 else str(_fail)+' FAILED'}")
    sys.exit(1 if _fail else 0)
