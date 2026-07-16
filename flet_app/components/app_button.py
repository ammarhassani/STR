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
