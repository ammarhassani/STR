# Flat-Enterprise UI Redesign — Design

**Date:** 2026-07-16
**Status:** Approved for planning

## Goal

Eliminate the Material Design *look* from the STR Flet app. Reads as a bespoke,
flat, minimal enterprise compliance tool — not "a Material app."

## Constraint (why "look", not "MaterialApp")

Flet's runtime is a Flutter `MaterialApp`; every control (`ElevatedButton`,
`TextField`, `DataTable`, `AlertDialog`, the sidebar `NavigationRail`) is a
Material widget. The `MaterialApp` shell cannot be removed. We remove the
Material *visual signatures* instead — ripple, elevation shadows, pill/rounded
defaults, page-slide transitions, the seeded color scheme — via a global flat
theme plus a few bespoke primitives where Material still leaks through.

## Approach: Hybrid

1. Global flat theme as the base (app-wide, no per-view edits).
2. Bespoke flat primitives only where Material still shows (buttons, inputs).
3. Table restyled via theme; rebuilt only if it still reads Material.

Chosen over theme-only (buttons/inputs still look Material) and full-rebuild
(rewrites every view — cost not justified since the palette is already close).

## Aesthetic: Flat / minimal enterprise, teal accent retained

- Depth via **1px hairline borders**, never shadows.
- Corner radius **4px** everywhere (crisp, not pill; down from current 8–12).
- **Teal accent kept** (`primary #0d7377`) for primary actions + focus rings,
  flattened (no gradient, no glow).
- **Muted semantic status** colors (current neon values toned down):
  approved/success `#2f855a`, pending/warning `#b7791f`, rejected/danger
  `#c53030`, rework `#c05621`, info `#3b5bdb`. Draft/open = neutral gray.
- Denser layout (compact visual density).
- Both light and dark modes retained.
- System font retained (no bundled font files); sizes/weights retuned for a
  clear 20 / 16 / 13 / 11 hierarchy.

## Components / units

### Unit A — Design tokens (`theme/colors.py`)
Rewrite the `DARK` / `LIGHT` value maps. **Keep every existing key** (`card_bg`,
`sidebar_*`, `hover`, `border`, `*_bg`, etc.) so all `colors["…"]` consumers
keep working — only the values change (flatter neutrals, muted status, teal
kept). Add one token: `radius` = 4 (consumed by primitives/theme).

- *Does:* single source of truth for palette + radius.
- *Depends on:* nothing.
- *Consumers unchanged:* every view reads the same keys.

### Unit B — Global flat theme (`theme/theme_manager.py::_apply_theme`)
Extend the `ft.Theme` construction to strip Material signatures app-wide:
- `visual_density = ft.VisualDensity.COMPACT`
- transparent splash + highlight (no ripple)
- `page_transitions = ft.PageTransitionsTheme(...)` set to no-transition on all
  platforms (no Material slide)
- `input_decoration_theme`: box border, no fill, hairline, teal focus border
- dialog/card/divider sub-themes: 0 elevation, hairline border
- drop `color_scheme_seed` reliance (keep explicit `color_scheme` values)

Verify each `ft.Theme` field name against installed Flet (0.28.3) before use;
skip any not supported by that version rather than guessing.

- *Does:* makes all inherited Material widgets render flat.
- *Depends on:* Unit A.

### Unit C — Flat primitives (`components/app_button.py`, `components/app_input.py`)
- `AppButton(text, on_click, variant="primary|secondary|danger", icon=None,
  disabled=False)` — `GestureDetector` + `Container`, 4px radius, flat fill or
  hairline border, hover/press = color shift, no ripple. Returns an `ft.Control`.
- `AppInput(...)` — thin wrapper standardizing `ft.TextField` to flat box border,
  no fill, teal focus (used where a full custom field isn't needed).
- Status badge + KPI cards: recolor via Unit A only (already `Container`-based).

- *Does:* Material-free interactive controls.
- *Depends on:* Unit A. Isolated, unit-testable by building + inspecting the tree.

### Unit D — Rollout swaps
Swap `ElevatedButton`/`TextButton` → `AppButton` in the highest-visibility
surfaces first: header, report dialog, delete/user/approval dialogs, login,
settings. Leave lower-traffic spots to inherit the theme until visually checked.
Table (`components/data_table.py`) restyled by theme; custom rebuild only if it
still reads Material after B.

## Data flow / behavior

Pure presentation. No service, DB, permission, or workflow change. No control's
`on_click`/value semantics change — only how they look. All existing callbacks,
refs, and handlers stay wired.

## Testing / verification

- `tests_ui_driver.py` builds all 15 views/dialogs — MUST stay **0 failures**
  after each unit (A→B→C→D). This is the regression gate.
- The other three suites (e2e 180, prosecutor 0/35, conformance 47) are
  logic-only and must remain green (no logic touched).
- Add to `tests_ui_driver.py`: assert `AppButton` builds for each variant and
  exposes an `on_click`; assert `colors.py` still defines every key the views
  reference (guards against a dropped token).
- Manual: drive the running app (`/run`) and eyeball light + dark on the main
  screens (login, reports list, report dialog, dashboard, approval panel).

## Out of scope (YAGNI)

Icon-set replacement, bundled web fonts, animation library, Cupertino widgets,
new screens, layout/IA changes. Colors, borders, radius, density, ripple,
elevation, transitions, and button/input chrome only.

## Rollback

Each unit is a separate commit; `theme/colors.py` + `_apply_theme` revert
restores the old look without touching view logic.
