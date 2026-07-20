"""Flat-enterprise theme unit checks. Run: python3.14 tests_theme.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'flet_app'))

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
    check('T2 no shadows', pg.theme.shadow_color == ft.Colors.TRANSPARENT)
    check('T2 no page transitions', pg.theme.page_transitions is not None)
    check('T2 is_dark always False', tm.is_dark is False)

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
    # ghost variant floats: no fill, no border
    g = app_button("Save", on_click=lambda e: None, variant="ghost")
    check('T4 ghost has no bg', g.bgcolor == "transparent", g.bgcolor)
    check('T4 ghost has no border', g.border is None)
    # native disabled: on_click stays wired but the control is disabled + dimmed
    dis = app_button("X", on_click=lambda e: None, disabled=True)
    check('T4 disabled sets native disabled', dis.disabled is True)
    check('T4 disabled is dimmed', dis.opacity == 0.45)
    # live re-enable works (the dynamic-button fix)
    from components.app_button import set_button_enabled
    dis.update = lambda: None  # no page attached in test
    set_button_enabled(dis, True)
    check('T4 set_button_enabled re-arms', dis.disabled is False and dis.opacity == 1.0)


def test_no_fake_alpha_colours():
    """A colour string with two hex digits stuck on the end is not a tint.

    The code wrote f"{colors['danger']}20" meaning "danger at 12% opacity".
    Flutter parses #AARRGGBB -- alpha FIRST -- so #c53030 + "20" became
    alpha=0xc5 (77% opaque), red=0x30, green=0x30, blue=0x20: a dark, nearly
    solid block. The "0 deleted" badge rendered as unreadable dark-on-dark.
    ft.Colors.with_opacity() is the API that means what this intended.
    """
    import re, pathlib
    # the tail of  f"{colors['danger']}20"  -- a colour with hex glued on
    pat = re.compile(r"\]\}[0-9A-Fa-f]{2}[\"']")
    offenders = []
    repo = pathlib.Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    for f in sorted((repo / "flet_app").rglob("*.py")):
        if "__pycache__" in str(f):
            continue
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if pat.search(line) and "colors[" in line:
                offenders.append(f"{f.name}:{i}")
    check("no colour is built by appending hex digits to another colour",
          not offenders, offenders)


def test_opacity_helper_produces_a_real_tint():
    import flet as ft
    from theme.theme_manager import theme_manager
    colors = theme_manager.get_colors()
    tint = ft.Colors.with_opacity(0.13, colors["danger"])
    check("a tint is not the same string as the solid colour",
          str(tint) != str(colors["danger"]), tint)
    check("and it records the opacity", "0.13" in str(tint), tint)


if __name__ == '__main__':
    test_tokens()
    test_flat_theme()
    test_app_button()
    test_no_fake_alpha_colours()
    test_opacity_helper_produces_a_real_tint()
    print(f"\nTHEME FAILURES: {len(FAILS)}")
    sys.exit(1 if FAILS else 0)
