"""Flat, Material-free button. Container + on_click, no ripple/elevation.

`disabled` uses Flet's native Control.disabled, so it is LIVE: toggle
`btn.disabled` (and call `btn.update()`) after build and the button re-arms
correctly — native disabled blocks the click and greys the control. Use
`set_button_enabled(btn, enabled)` for the opacity + disabled toggle together.
"""
import flet as ft
from theme.theme_manager import theme_manager


def app_button(text, on_click=None, variant="primary", icon=None,
               disabled=False, expand=False):
    c = theme_manager.get_colors()
    r = c.get("radius", 4)
    if variant == "danger":
        bg, fg, border, hover = c["danger"], "#ffffff", c["danger"], c.get("danger_hover", c["danger"])
    elif variant == "secondary":
        bg, fg, border, hover = "transparent", c["text_primary"], c["border"], c["hover"]
    elif variant == "ghost":
        # fully floating: no fill, no border — just accent-colored icon+text.
        # hover shows a faint translucent tint so it still reads as clickable.
        bg, fg, border, hover = "transparent", c["primary"], None, ft.Colors.with_opacity(0.10, c["primary"])
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
        border=(ft.border.all(1, border) if border else None),
        border_radius=r,
        ink=False,
        alignment=ft.alignment.center,
        # Native disabled: blocks the click AND stays live-toggleable. on_click
        # is always wired; Flet gates it while disabled.
        disabled=disabled,
        opacity=0.45 if disabled else 1.0,
        on_click=on_click,
        expand=expand,
    )

    def _hover(e):
        if cont.disabled:
            return
        cont.bgcolor = hover if e.data == "true" else bg
        cont.update()

    cont.on_hover = _hover
    # remember base colors so a dynamic re-enable restores them
    cont.data = {"bg": bg, "hover": hover}
    return cont


def set_button_enabled(btn, enabled: bool):
    """Live-toggle an app_button's enabled state (disabled + opacity together)."""
    btn.disabled = not enabled
    btn.opacity = 1.0 if enabled else 0.45
    btn.update()
