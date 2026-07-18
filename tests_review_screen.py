"""#9 — review screen: gender must always show its stored value, never blank,
never greyed-into-unreadable. Run: python3.14 tests_review_screen.py"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'flet_app'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_fail = 0
def check(label, cond, detail=""):
    global _fail
    ok = bool(cond)
    print(("PASS " if ok else "FAIL ") + label + ("" if ok else f"  -- {detail}"))
    if not ok:
        _fail += 1


def test_option_union_preserves_stored_value():
    from views.approval_panel_view import review_field_options
    # stored value in a DIFFERENT language than the active list (the real bug:
    # config seeded Arabic, review hardcoded English) — must still be an option.
    opts = review_field_options(['Male', 'Female'], 'ذكر')
    check("stored value survives even if not in active list", 'ذكر' in opts, opts)
    check("active values still present", 'Male' in opts and 'Female' in opts, opts)

    # normal case: stored value already active -> no duplicate
    opts2 = review_field_options(['Male', 'Female'], 'Male')
    check("no duplicate when stored value already active", opts2.count('Male') == 1, opts2)

    # empties dropped, order preserved
    opts3 = review_field_options(['Male', '', 'Female', None], '')
    check("empty/None option values dropped", '' not in opts3 and None not in opts3, opts3)
    check("order preserved", opts3 == ['Male', 'Female'], opts3)

    # no active values at all -> stored value alone (never blank)
    opts4 = review_field_options([], 'Female')
    check("stored value shown even with empty active list", opts4 == ['Female'], opts4)

    # no data anywhere -> empty (not [''] )
    check("empty in, empty out", review_field_options([], '') == [], review_field_options([], ''))


def test_structural_no_hardcoded_english_options():
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            'flet_app/views/approval_panel_view.py')).read()
    # the review dropdown must source from the live service, not a hardcoded list
    check("review dropdown uses live dropdown values",
          'get_active_dropdown_values' in src, "no service call")
    check("locked gender is a readable display field (not a disabled dropdown)",
          "field_info['display'].visible" in src, "no display/editor swap")
    check("edit reads the constrained editor value",
          "field_info['editor'].value" in src, "get_form_data not reading editor")


if __name__ == "__main__":
    test_option_union_preserves_stored_value()
    test_structural_no_hardcoded_english_options()
    print(f"\n{'ALL PASS' if _fail == 0 else str(_fail)+' FAILED'}")
    sys.exit(1 if _fail else 0)
