# Flat-Enterprise UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the Material Design *look* from the STR Flet app — flat, minimal, light-only enterprise styling with the teal accent retained.

**Architecture:** Hybrid. A global flat `ft.Theme` (kills ripple/elevation/transitions app-wide) plus bespoke flat primitives (`AppButton`) swapped into high-visibility surfaces. Pure presentation — no service, DB, permission, or workflow change. Dark mode removed (light forced, toggle deleted).

**Tech Stack:** Flet 0.28.3 (run with `python3.14`), existing script-style test harnesses.

## Global Constraints

- **Run everything with `python3.14`** (has Flet 0.28.3 + bcrypt); plain `python3` lacks deps.
- **macOS has no `timeout` command** — never use it in Bash.
- **Light mode only.** No dark palette usage, no theme toggle.
- **Teal accent kept:** `primary = #0d7377`.
- **Corner radius = 4px** everywhere. **Depth = 1px hairline borders, never shadows.**
- **Keep every existing key** in `theme/colors.py` `LIGHT` map — views read `colors["…"]`; a dropped key breaks a view.
- **No logic changes.** Every control keeps its existing `on_click`/value/ref wiring.
- **Regression gate:** after every task, `python3.14 tests_ui_driver.py` prints `UI failures: 0/NN`. The logic suites (`tests_e2e_harness.py` 180/180, `tests_prosecutor.py` 0/35, `tests_conformance.py` 47/47) must stay green but only need re-running once at the end (no logic touched).
- Tests are **plain scripts** run with `python3.14 tests_X.py` (this repo has no pytest). Match that pattern.

---

### Task 1: Flat light design tokens

**Files:**
- Modify: `flet_app/theme/colors.py` (rewrite `LIGHT` dict values; add `radius`)
- Test: `tests_theme.py` (create)

**Interfaces:**
- Consumes: nothing.
- Produces: `Colors.get_palette("light")` returns a dict containing every key listed in `REQUIRED_KEYS` below plus `"radius": 4`.

- [ ] **Step 1: Write the failing test**

Create `tests_theme.py`:

```python
"""Flat-enterprise theme unit checks. Run: python3.14 tests_theme.py"""
import sys
sys.path.insert(0, '/Users/engammar/Scripts/STR')
sys.path.insert(0, '/Users/engammar/Scripts/STR/flet_app')

FAILS = []
def check(name, ok, detail=''):
    print(('  ok  ' if ok else '  FAIL') + f' {name}' + ('' if ok else f' — {detail}'))
    if not ok: FAILS.append(name)

REQUIRED_KEYS = [
    'bg_primary','bg_secondary','bg_tertiary','bg_elevated',
    'text_primary','text_secondary','text_muted',
    'primary','primary_light','accent',
    'success','success_bg','warning','warning_bg','danger','danger_bg','info','info_bg',
    'border','border_light','hover','active','disabled',
    'card_bg','card_border','sidebar_bg','sidebar_item_hover','sidebar_item_active',
]

def test_tokens():
    from theme.colors import Colors
    p = Colors.get_palette('light')
    missing = [k for k in REQUIRED_KEYS if k not in p]
    check('T1 all required keys present', not missing, f'missing {missing}')
    check('T1 radius token added', p.get('radius') == 4, p.get('radius'))
    check('T1 teal accent kept', p['primary'] == '#0d7377', p['primary'])
    check('T1 light background is light', p['bg_primary'].lower() in ('#ffffff', '#f7f8fa'), p['bg_primary'])
    check('T1 muted approved green', p['success'] == '#2f855a', p['success'])

if __name__ == '__main__':
    test_tokens()
    print(f"\nTHEME FAILURES: {len(FAILS)}")
    sys.exit(1 if FAILS else 0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/engammar/Scripts/STR && python3.14 tests_theme.py`
Expected: FAIL on `T1 radius token added` and `T1 muted approved green` (radius absent, success is old neon `#4caf50`).

- [ ] **Step 3: Rewrite the `LIGHT` dict**

In `flet_app/theme/colors.py`, replace the `LIGHT = { … }` block with the flat values (keep all keys, add `radius`):

```python
    LIGHT = {
        # Backgrounds — flat neutrals
        "bg_primary": "#f7f8fa",
        "bg_secondary": "#ffffff",
        "bg_tertiary": "#eef0f3",
        "bg_elevated": "#ffffff",

        # Text
        "text_primary": "#1a1d21",
        "text_secondary": "#5b6470",
        "text_muted": "#8a929c",

        # Brand / Accent — teal kept, flattened
        "primary": "#0d7377",
        "primary_light": "#14919b",
        "accent": "#0d7377",

        # Status — muted (no neon)
        "success": "#2f855a",
        "success_bg": "#e8f3ec",
        "warning": "#b7791f",
        "warning_bg": "#f6efe1",
        "danger": "#c53030",
        "danger_bg": "#f7e8e8",
        "info": "#3b5bdb",
        "info_bg": "#e8ecfb",

        # Borders — hairline
        "border": "#e2e5e9",
        "border_light": "#eef0f3",

        # Interactive
        "hover": "#eef0f3",
        "active": "#0d7377",
        "disabled": "#c2c8d0",

        # Cards
        "card_bg": "#ffffff",
        "card_border": "#e2e5e9",

        # Sidebar
        "sidebar_bg": "#ffffff",
        "sidebar_item_hover": "#eef0f3",
        "sidebar_item_active": "#0d7377",

        # Design tokens
        "radius": 4,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/engammar/Scripts/STR && python3.14 tests_theme.py`
Expected: `THEME FAILURES: 0`

- [ ] **Step 5: Regression + commit**

Run: `python3.14 tests_ui_driver.py 2>/dev/null | grep "UI failures"`
Expected: `UI failures: 0/NN`

```bash
git add flet_app/theme/colors.py tests_theme.py
git commit -m "feat(ui): flat light design tokens + radius"
```

---

### Task 2: Global flat theme + force light

**Files:**
- Modify: `flet_app/theme/theme_manager.py` (`_apply_theme`, `set_theme`, `toggle_theme`)
- Test: `tests_theme.py` (extend)

**Interfaces:**
- Consumes: `Colors.get_palette("light")` (Task 1).
- Produces: after `theme_manager.initialize(page)` / `_apply_theme`, `page.theme_mode == ft.ThemeMode.LIGHT`, `page.theme.visual_density == ft.VisualDensity.COMPACT`, `page.theme.splash_color == ft.Colors.TRANSPARENT`, `page.theme.page_transitions` is set. `is_dark` always False.

- [ ] **Step 1: Write the failing test**

Add to `tests_theme.py` before the `__main__` block:

```python
class FakePage:
    def __init__(self):
        self.theme = None; self.dark_theme = None
        self.theme_mode = None
    def update(self): pass

def test_flat_theme():
    import flet as ft
    from theme.theme_manager import ThemeManager
    tm = ThemeManager(); tm._page = FakePage(); tm._current_theme = 'dark'  # even if 'dark' stored...
    tm._apply_theme()
    pg = tm._page
    check('T2 forced light mode', pg.theme_mode == ft.ThemeMode.LIGHT, pg.theme_mode)
    check('T2 compact density', pg.theme.visual_density == ft.VisualDensity.COMPACT)
    check('T2 no ripple splash', pg.theme.splash_color == ft.Colors.TRANSPARENT)
    check('T2 no page transitions', pg.theme.page_transitions is not None)
    check('T2 is_dark always False', tm.is_dark is False)
```

And call it in `__main__`: add `test_flat_theme()` after `test_tokens()`.

- [ ] **Step 2: Run to verify it fails**

Run: `cd /Users/engammar/Scripts/STR && python3.14 tests_theme.py`
Expected: FAIL on `T2 forced light mode` / `T2 compact density` (current code honors 'dark' and sets no visual_density).

- [ ] **Step 3: Rewrite `_apply_theme` and neutralize the togglers**

In `flet_app/theme/theme_manager.py`, replace the body of `_apply_theme` with a light-only flat theme:

```python
    def _apply_theme(self):
        """Apply the flat, light-only enterprise theme."""
        if not self._page:
            return
        import flet as ft
        self._current_theme = "light"
        self._page.theme_mode = ft.ThemeMode.LIGHT
        colors = Colors.get_palette("light")
        r = colors.get("radius", 4)
        none_tx = ft.PageTransitionsTheme(
            android=ft.PageTransitionTheme.NONE, ios=ft.PageTransitionTheme.NONE,
            macos=ft.PageTransitionTheme.NONE, windows=ft.PageTransitionTheme.NONE,
            linux=ft.PageTransitionTheme.NONE,
        )
        self._page.theme = ft.Theme(
            use_material3=True,
            visual_density=ft.VisualDensity.COMPACT,
            splash_color=ft.Colors.TRANSPARENT,
            highlight_color=ft.Colors.TRANSPARENT,
            hover_color=colors["hover"],
            page_transitions=none_tx,
            color_scheme=ft.ColorScheme(
                primary=colors["primary"],
                secondary=colors["accent"],
                surface=colors["bg_secondary"],
                background=colors["bg_primary"],
                error=colors["danger"],
                on_primary=ft.Colors.WHITE,
                on_secondary=ft.Colors.WHITE,
                on_surface=colors["text_primary"],
                on_background=colors["text_primary"],
                surface_variant=colors["bg_tertiary"],
                outline=colors["border"],
            ),
            divider_theme=ft.DividerTheme(thickness=1, color=colors["border"]),
            dialog_theme=ft.DialogTheme(
                elevation=0, shadow_color=ft.Colors.TRANSPARENT,
                shape=ft.RoundedRectangleBorder(radius=r)),
            card_theme=ft.CardTheme(
                elevation=0, shadow_color=ft.Colors.TRANSPARENT,
                shape=ft.RoundedRectangleBorder(radius=r)),
            data_table_theme=ft.DataTableTheme(
                divider_thickness=1, heading_row_height=40,
                data_row_min_height=34, data_row_max_height=44),
        )
        self._page.dark_theme = self._page.theme
        self._page.update()
```

Then make the togglers no-ops that keep light. Replace the bodies of `set_theme` and `toggle_theme`:

```python
    def toggle_theme(self):
        """Dark mode removed — always light."""
        self.set_theme("light")

    def set_theme(self, theme_name: str):
        """Dark mode removed — force light regardless of the request."""
        self._current_theme = "light"
        self._apply_theme()
        for cb in self._listeners:
            try:
                cb("light")
            except Exception:
                pass
```

(If `_listeners` has a different attribute name in the file, use the existing one — check the class before editing.) Ensure the `is_dark` property returns `self._current_theme == "dark"` (already the case) so it is always False.

- [ ] **Step 4: Run to verify it passes**

Run: `cd /Users/engammar/Scripts/STR && python3.14 tests_theme.py`
Expected: `THEME FAILURES: 0`

- [ ] **Step 5: Regression + commit**

Run: `python3.14 tests_ui_driver.py 2>/dev/null | grep "UI failures"` → `UI failures: 0/NN`

```bash
git add flet_app/theme/theme_manager.py tests_theme.py
git commit -m "feat(ui): global flat theme, light-only (no ripple/elevation/transitions)"
```

---

### Task 3: Remove the theme toggle from the header

**Files:**
- Modify: `flet_app/components/header.py` (remove `toggle_theme` handler ~lines 44-46, `theme_button` def ~160-165, and its append ~248)
- Test: `tests_ui_driver.py` (extend the "UI Feature wiring" block)

**Interfaces:**
- Consumes: nothing.
- Produces: header builds without a theme toggle; source contains no `toggle_theme`.

- [ ] **Step 1: Write the failing check**

In `tests_ui_driver.py`, inside the `E = 'UI Feature wiring'` section, add:

```python
    hdr_src = open(os.path.join(REPO, 'flet_app/components/header.py')).read()
    finding(E, 'header still has a theme toggle (dark mode removed)',
            'toggle_theme' in hdr_src or 'theme_button' in hdr_src)
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd /Users/engammar/Scripts/STR && python3.14 tests_ui_driver.py 2>/dev/null | grep -E "✗|UI failures"`
Expected: a `✗ … header still has a theme toggle` line; failure count > 0.

- [ ] **Step 3: Remove the toggle**

In `flet_app/components/header.py`:
1. Delete the `toggle_theme` handler:
```python
    def toggle_theme(e):
        """Toggle between light and dark theme."""
        theme_manager.toggle_theme()
        # (delete the whole function, including any page.update()/rebuild lines it contains — read the file to catch them all)
```
2. Delete the `theme_button = ft.IconButton( … )` definition (the `LIGHT_MODE if theme_manager.is_dark else DARK_MODE` button).
3. Delete the `theme_button,` line from the toolbar controls list (~line 248).

Read the file first to confirm exact current line numbers before deleting.

- [ ] **Step 4: Run to verify it passes**

Run: `cd /Users/engammar/Scripts/STR && python3.14 tests_ui_driver.py 2>/dev/null | grep -E "✗|UI failures"`
Expected: no toggle finding; `UI failures: 0/NN`.

- [ ] **Step 5: Commit**

```bash
git add flet_app/components/header.py tests_ui_driver.py
git commit -m "feat(ui): remove theme toggle (light-only)"
```

---

### Task 4: Flat AppButton primitive

**Files:**
- Create: `flet_app/components/app_button.py`
- Test: `tests_theme.py` (extend)

**Interfaces:**
- Consumes: `theme_manager.get_colors()` (returns the light palette dict).
- Produces: `app_button(text: str, on_click=None, variant: str = "primary", icon=None, disabled: bool = False, expand: bool = False) -> ft.Container`. Variants: `"primary"` (filled teal), `"secondary"` (hairline border, transparent), `"danger"` (filled red). No ripple (`ink=False`).

- [ ] **Step 1: Write the failing test**

Add to `tests_theme.py` before `__main__`:

```python
def test_app_button():
    import flet as ft
    from components.app_button import app_button
    clicked = {'n': 0}
    for variant in ('primary', 'secondary', 'danger'):
        b = app_button("Go", on_click=lambda e: clicked.__setitem__('n', clicked['n']+1),
                       variant=variant)
        check(f'T4 {variant} builds a Container', isinstance(b, ft.Container))
        check(f'T4 {variant} no ripple (ink False)', b.ink is False)
        check(f'T4 {variant} radius 4', b.border_radius == 4)
        if b.on_click:
            b.on_click(None)
    check('T4 on_click fires', clicked['n'] == 3, clicked['n'])
    dis = app_button("X", on_click=lambda e: None, disabled=True)
    check('T4 disabled has no on_click', dis.on_click is None)
```

Call `test_app_button()` in `__main__` after `test_flat_theme()`.

- [ ] **Step 2: Run to verify it fails**

Run: `cd /Users/engammar/Scripts/STR && python3.14 tests_theme.py`
Expected: FAIL — `No module named 'components.app_button'`.

- [ ] **Step 3: Implement `app_button`**

Create `flet_app/components/app_button.py`:

```python
"""Flat, Material-free button. Container + on_click, no ripple/elevation."""
import flet as ft
from theme.theme_manager import theme_manager


def app_button(text, on_click=None, variant="primary", icon=None,
               disabled=False, expand=False):
    c = theme_manager.get_colors()
    r = c.get("radius", 4)
    if variant == "danger":
        bg, fg, border, hover = c["danger"], "#ffffff", c["danger"], "#a52626"
    elif variant == "secondary":
        bg, fg, border, hover = "#ffffff", c["text_primary"], c["border"], c["hover"]
    else:  # primary
        bg, fg, border, hover = c["primary"], "#ffffff", c["primary"], c["primary_light"]

    row_controls = []
    if icon:
        row_controls.append(ft.Icon(icon, size=16, color=fg))
    row_controls.append(ft.Text(text, size=13, weight=ft.FontWeight.W_500, color=fg))

    cont = ft.Container(
        content=ft.Row(row_controls, spacing=8, tight=True,
                       alignment=ft.MainAxisAlignment.CENTER),
        bgcolor=bg,
        padding=ft.padding.symmetric(vertical=9, horizontal=16),
        border=ft.border.all(1, border),
        border_radius=r,
        ink=False,
        alignment=ft.alignment.center,
        opacity=0.45 if disabled else 1.0,
        on_click=(None if disabled else on_click),
        expand=expand,
    )

    def _hover(e):
        cont.bgcolor = hover if e.data == "true" else bg
        cont.update()

    if not disabled:
        cont.on_hover = _hover
    return cont
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd /Users/engammar/Scripts/STR && python3.14 tests_theme.py`
Expected: `THEME FAILURES: 0`

- [ ] **Step 5: Commit**

```bash
git add flet_app/components/app_button.py tests_theme.py
git commit -m "feat(ui): flat AppButton primitive (no ripple)"
```

---

### Task 5: Swap buttons in high-visibility surfaces + full regression

**Files:**
- Modify: `flet_app/components/header.py`, `flet_app/dialogs/report_dialog.py`, `flet_app/dialogs/delete_confirmation_dialog.py`, `flet_app/dialogs/user_dialog.py`, `flet_app/views/login_view.py`, `flet_app/views/settings_view.py` (swap the primary `ElevatedButton`s → `app_button`)
- Test: `tests_ui_driver.py` (already builds all views/dialogs)

**Interfaces:**
- Consumes: `app_button` (Task 4).
- Produces: the same actions, flat-styled. No behavior change.

- [ ] **Step 1: Establish the regression baseline**

Run: `cd /Users/engammar/Scripts/STR && python3.14 tests_ui_driver.py 2>/dev/null | grep "UI failures"`
Expected: `UI failures: 0/NN` (record NN).

- [ ] **Step 2: Swap the header's primary action**

In `flet_app/components/header.py`, replace the "add report" `ElevatedButton` (the New Report action) with:

```python
from components.app_button import app_button
# ...
new_report_btn = app_button("New Report", icon=ft.Icons.ADD,
                            on_click=on_add_report, variant="primary")
```

Keep its existing visibility/permission guard (`app_state.auth_service.has_permission('add_report')`) and the same `on_add_report` callback. Preserve where it is appended to the toolbar.

- [ ] **Step 3: Swap dialog primary/danger buttons**

In each of `report_dialog.py` (Save / Submit), `delete_confirmation_dialog.py` (Permanently Delete → `variant="danger"`; keep the type-DELETE `disabled` gating by setting `disabled=` from the same condition), `user_dialog.py` (Save), `login_view.py` (Sign In), `settings_view.py` (Save Settings, Close Month): replace the primary `ft.ElevatedButton(...)` with `app_button(<same text>, on_click=<same handler>, variant="primary" or "danger")`. Keep every `ref`, `on_click`, and enable/disable condition identical. Leave `TextButton("Cancel", …)` as-is (secondary, low visibility — inherits the flat theme).

Do these one file at a time; after each file run Step 4.

- [ ] **Step 4: Regression after each file**

Run: `python3.14 tests_ui_driver.py 2>/dev/null | grep -E "✗|UI failures"`
Expected: `UI failures: 0/NN` (no new `✗`). If a `✗ … view build CRASHED` appears, the swap broke a build — fix before continuing.

- [ ] **Step 5: Full suite + manual eyeball**

Run all logic suites (unchanged, must stay green):
```bash
python3.14 tests_e2e_harness.py 2>/dev/null | grep TOTAL         # 180/180
python3.14 tests_prosecutor.py 2>/dev/null | grep TOTAL          # 0 / 35
python3.14 tests_conformance.py 2>/dev/null | grep Conformance   # 47/47
python3.14 tests_ui_driver.py 2>/dev/null | grep "UI failures"   # 0/NN
```
Then drive the app and eyeball light-only flat look on login, reports list, report dialog, dashboard, approval panel (use the `/run` skill or `python3.14 flet_app/main.py`).

- [ ] **Step 6: Commit**

```bash
git add flet_app/components/header.py flet_app/dialogs/report_dialog.py \
  flet_app/dialogs/delete_confirmation_dialog.py flet_app/dialogs/user_dialog.py \
  flet_app/views/login_view.py flet_app/views/settings_view.py tests_ui_driver.py
git commit -m "feat(ui): swap primary actions to flat AppButton across key surfaces"
```

---

## Notes for the implementer

- `theme_manager.get_colors()` returns the light palette dict (has `radius`, all keys). Never read `Colors.DARK`.
- Flet 0.28.3 has **no** `InputDecorationTheme`; style text fields per-field (`border`, `filled=False`, `bgcolor`, `border_radius`, `focused_border_color`) if a field still looks Material — but only if the manual eyeball flags it (YAGNI otherwise).
- The `data_table` component inherits `data_table_theme` from Task 2. Only rebuild it if the eyeball still reads Material after Task 2.
- If any `tests_ui_driver.py` build crashes after a swap, the cause is almost always a missing `import` of `app_button` at the top of that file — add it.
