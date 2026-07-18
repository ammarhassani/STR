"""App logo. The PNG lives in the repo (flet_app/assets/logo.png) so it persists
and ships with every clone; we embed it as base64 at runtime so it renders in
desktop, web, and packaged builds without needing a Flet assets_dir configured.
"""
import base64
import os
import flet as ft

_LOGO_B64 = None


def logo_base64() -> str:
    global _LOGO_B64
    if _LOGO_B64 is None:
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "assets", "logo.png")
        try:
            with open(path, "rb") as f:
                _LOGO_B64 = base64.b64encode(f.read()).decode("ascii")
        except Exception:
            _LOGO_B64 = ""
    return _LOGO_B64


def logo_image(size: int = 32, fallback_color=None):
    """The app logo as an ft.Image, or a shield icon fallback if the file is missing."""
    b = logo_base64()
    if b:
        return ft.Image(src_base64=b, width=size, height=size, fit=ft.ImageFit.CONTAIN)
    return ft.Icon(ft.Icons.SHIELD, size=size, color=fallback_color)
