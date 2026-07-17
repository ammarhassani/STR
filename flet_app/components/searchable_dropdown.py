"""Drop-in replacement for ft.Dropdown that is type-to-filter searchable.

Flet 0.27+ moved Dropdown onto Material 3's DropdownMenu, which supports an
editable text field that filters the option list as you type. This wrapper just
turns that on by default, so every call site becomes searchable without changing
its arguments. It returns a real ft.Dropdown, so refs, isinstance checks, value,
options and on_change all behave exactly as before.

If type-to-filter ever misbehaves on a given Flet build, disabling search
app-wide is a one-line change here (drop the two setdefault lines) — no call
site needs to be touched.
"""
import flet as ft


def searchable_dropdown(*args, **kwargs):
    kwargs.setdefault("editable", True)       # show a text field
    kwargs.setdefault("enable_filter", True)  # filter options as you type
    return ft.Dropdown(*args, **kwargs)
