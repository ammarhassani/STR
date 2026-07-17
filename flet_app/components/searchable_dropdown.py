"""Custom type-to-filter dropdown — a drop-in replacement for ft.Dropdown.

Flet 0.27+ made ft.Dropdown filterable via editable/enable_filter, but that does
NOT render a search field on the desktop client (verified on 0.28.3), so we build
our own: a TextField you type into + a filtered list of options underneath. It
exposes the same surface the app already uses (`.value`, `.options`, `on_change`,
`ref`, `label`, `hint_text`, `width`, `disabled`, plus the common styling kwargs),
so every existing `searchable_dropdown(...)` call site works unchanged.

Two behaviours baked in:
  - Only CLICKING an option sets the value; free-typed text just filters and, on
    close, snaps back to the current selection. Users can't commit junk.
  - Any empty-key placeholder option (the old "-- Select --") is dropped — the
    unselected state shows hint text instead. This is fix #12: no selectable
    placeholder that the app then reads as a bad value.
"""
import flet as ft


def _display_text(opt):
    """The label shown for an option (Flet Option: .text or falls back to .key)."""
    t = getattr(opt, "text", None)
    return t if t not in (None, "") else str(getattr(opt, "key", ""))


def filter_options(options, query):
    """Pure: options whose display text (or key) contains query, case-insensitive.
    Empty query -> all. Placeholder options (empty key) are never included."""
    real = [o for o in options if str(getattr(o, "key", "")) != ""]
    q = (query or "").strip().lower()
    if not q:
        return real
    return [o for o in real if q in _display_text(o).lower() or q in str(getattr(o, "key", "")).lower()]


class _Evt:
    """Minimal on_change event: handlers read e.control.value / e.data."""
    def __init__(self, control):
        self.control = control
        self.data = control.value
        self.page = getattr(control, "page", None)


class SearchableDropdown(ft.Column):
    def __init__(self, options=None, value=None, on_change=None, label=None,
                 hint_text=None, width=None, disabled=False, ref=None,
                 text_size=None, border_color=None, focused_border_color=None,
                 border_radius=None, content_padding=None, **_ignore):
        super().__init__(spacing=2, tight=True, ref=ref, width=width)
        self._options = [o for o in (options or []) if str(getattr(o, "key", "")) != ""]
        self._value = value if value not in ("",) else None
        self._on_change = on_change
        self._hint = hint_text or "Type to search…"

        self._field = ft.TextField(
            label=label,
            hint_text=self._hint,
            width=width,
            dense=True,
            text_size=text_size,
            border_color=border_color,
            focused_border_color=focused_border_color,
            border_radius=border_radius,
            content_padding=content_padding,
            suffix=ft.IconButton(
                icon=ft.Icons.ARROW_DROP_DOWN, icon_size=20,
                on_click=self._toggle, style=ft.ButtonStyle(padding=0),
            ),
            on_change=self._on_type,
            on_focus=self._open_menu,
            on_blur=self._on_blur,
        )
        self._list = ft.Column(spacing=0, scroll=ft.ScrollMode.AUTO, tight=True)
        self._menu = ft.Container(
            content=self._list, visible=False, width=width,
            border=ft.border.all(1, "#e2e5e9"), border_radius=6,
            bgcolor="#ffffff", padding=4, height=220,
        )
        self.controls = [self._field, self._menu]
        self.disabled = disabled
        self._render_selection()

    # ---- ft.Dropdown-compatible surface ----------------------------------
    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, v):
        self._value = v if v not in ("",) else None
        self._render_selection()

    @property
    def options(self):
        return self._options

    @options.setter
    def options(self, opts):
        self._options = [o for o in (opts or []) if str(getattr(o, "key", "")) != ""]
        self._render_selection()
        if self._menu.visible:
            self._rebuild_list(self._field.value or "")

    # ---- internals -------------------------------------------------------
    def _selected_option(self):
        for o in self._options:
            if str(getattr(o, "key", "")) == str(self._value):
                return o
        return None

    def _render_selection(self):
        """Show the selected option's display text in the field (or blank -> hint)."""
        opt = self._selected_option()
        self._field.value = _display_text(opt) if opt else ""
        self._safe_update(self._field)

    def _rebuild_list(self, query):
        rows = []
        for o in filter_options(self._options, query):
            disp = _display_text(o)

            def pick(e, opt=o, text=disp):
                self._value = getattr(opt, "key", None)
                self._field.value = text
                self._close_menu()
                if self._on_change:
                    self._on_change(_Evt(self))
                self._safe_update(self._field)

            rows.append(
                ft.Container(
                    content=ft.Text(disp, size=13),
                    padding=ft.padding.symmetric(8, 10),
                    on_click=pick, ink=True, border_radius=4,
                )
            )
        if not rows:
            rows = [ft.Container(content=ft.Text("No matches", size=12, italic=True),
                                 padding=ft.padding.symmetric(8, 10))]
        self._list.controls = rows
        self._safe_update(self._list)

    def _open_menu(self, e=None):
        if self.disabled:
            return
        self._rebuild_list(self._field.value or "")
        self._menu.visible = True
        self._safe_update(self._menu)

    def _close_menu(self):
        self._menu.visible = False
        self._safe_update(self._menu)

    def _toggle(self, e=None):
        if self._menu.visible:
            self._close_menu()
        else:
            self._open_menu()

    def _on_type(self, e):
        # typing filters only; it never sets the value
        self._rebuild_list(self._field.value or "")
        self._menu.visible = True
        self._safe_update(self._menu)

    def _on_blur(self, e):
        # snap the text back to the current selection so free-typed text can't
        # linger and be mistaken for a value
        self._render_selection()

    def _safe_update(self, ctrl):
        try:
            if getattr(ctrl, "page", None) is not None:
                ctrl.update()
        except Exception:
            pass


def searchable_dropdown(*args, **kwargs):
    """Drop-in for ft.Dropdown, now backed by the custom SearchableDropdown."""
    return SearchableDropdown(**kwargs)
