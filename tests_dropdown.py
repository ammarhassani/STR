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


if __name__ == "__main__":
    test_filter()
    test_surface()
    test_pick_fires_on_change_and_typing_does_not()
    print(f"\n{'ALL PASS' if _fail == 0 else str(_fail)+' FAILED'}")
    sys.exit(1 if _fail else 0)
