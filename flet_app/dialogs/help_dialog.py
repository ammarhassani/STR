"""
Help Dialog for FIU Report Management System.
Comprehensive help system with documentation and shortcuts.
"""
import flet as ft
from components.overlay import (mount as _overlay_mount,
                                dismiss as _overlay_dismiss)
from i18n import t
from typing import Any

from theme.theme_manager import theme_manager
from components.branding import logo_image


def show_help_dialog(page: ft.Page, app_state: Any = None):
    """
    Show the help dialog.

    Args:
        page: Flet page object
        app_state: Application state (optional)
    """
    colors = theme_manager.get_colors()

    # Tab prose lives in the i18n catalogs so it switches with the UI language.
    getting_started_content = t("help.body.getting_started")
    shortcuts_content = t("help.body.shortcuts")
    faq_content = t("help.body.faq")

    # About content
    about_content = ft.Column(
        controls=[
            logo_image(64, fallback_color=colors["primary"]),
            ft.Container(height=16),
            ft.Text(
                t("help.about.name"),
                size=20,
                weight=ft.FontWeight.BOLD,
                color=colors["text_primary"],
                text_align=ft.TextAlign.CENTER,
            ),
            ft.Container(height=8),
            ft.Text(
                t("help.about.version"),
                size=14,
                color=colors["text_secondary"],
                text_align=ft.TextAlign.CENTER,
            ),
            ft.Container(height=24),
            ft.Text(
                "A comprehensive system for managing Financial Intelligence Unit reports.\n"
                "Built with Python and Flet for cross-platform desktop applications.",
                size=12,
                color=colors["text_secondary"],
                text_align=ft.TextAlign.CENTER,
            ),
            ft.Container(height=24),
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text(t("help.about.stack"), weight=ft.FontWeight.BOLD, size=12),
                        ft.Text("Python 3.9+", size=11, color=colors["text_muted"]),
                        ft.Text("Flet 0.21+", size=11, color=colors["text_muted"]),
                        ft.Text("SQLite3", size=11, color=colors["text_muted"]),
                        ft.Text("Plotly Charts", size=11, color=colors["text_muted"]),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=4,
                ),
                padding=16,
                bgcolor=colors["bg_tertiary"],
                border_radius=4,
            ),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        alignment=ft.MainAxisAlignment.CENTER,
    )

    # #18: each tab must scroll — content routinely exceeds the fixed 450px
    # dialog height, and without a scroll wrapper the overflow is unreachable.
    def scroll_pane(inner, center=False):
        return ft.Container(
            content=ft.Column(
                controls=[inner],
                scroll=ft.ScrollMode.AUTO,
                expand=True,
                horizontal_alignment=(ft.CrossAxisAlignment.CENTER if center
                                      else ft.CrossAxisAlignment.START),
            ),
            padding=20,
            expand=True,
        )

    def md(text):
        return ft.Markdown(text, selectable=True,
                           extension_set=ft.MarkdownExtensionSet.GITHUB_WEB)

    # Tabs
    tabs = ft.Tabs(
        selected_index=0,
        animation_duration=200,
        tabs=[
            ft.Tab(text=t("help.tab.getting_started"), icon=ft.Icons.ROCKET_LAUNCH,
                   content=scroll_pane(md(getting_started_content))),
            ft.Tab(text=t("help.tab.shortcuts"), icon=ft.Icons.KEYBOARD,
                   content=scroll_pane(md(shortcuts_content))),
            ft.Tab(text=t("help.tab.faq"), icon=ft.Icons.HELP_OUTLINE,
                   content=scroll_pane(md(faq_content))),
            ft.Tab(text=t("help.tab.about"), icon=ft.Icons.INFO_OUTLINE,
                   content=scroll_pane(about_content, center=True)),
        ],
    )

    def close_dialog(e):
        dialog.open = False
        _overlay_dismiss(page, dialog)
        page.update()

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Row(
            controls=[
                ft.Icon(ft.Icons.HELP, color=colors["primary"]),
                ft.Container(width=8),
                ft.Text(t("help.title")),
                ft.Container(expand=True),
                ft.Text("v2.0.0", size=11, color=colors["text_muted"]),
            ],
        ),
        content=ft.Container(
            content=tabs,
            width=600,
            height=450,
        ),
        actions=[
            ft.TextButton(t("common.close"), on_click=close_dialog),
        ],
    )

    _overlay_mount(page, dialog, update=False)
    page.update()
