"""
Header Component for FIU Report Management System.
Provides app bar with title, toolbar actions, theme toggle, and user menu.
"""
import flet as ft
from typing import Callable, Optional, Any

from theme.theme_manager import theme_manager
from theme.colors import Colors
from components.app_button import app_button


def create_header(
    page: ft.Page,
    app_state: Any,
    title: str = "Dashboard",
    on_logout: Callable[[], None] = None,
    on_profile: Callable[[], None] = None,
    on_new_report: Callable[[], None] = None,
    on_refresh: Callable[[], None] = None,
    on_help: Callable[[], None] = None,
    on_backup: Callable[[], None] = None,
    on_reservations: Callable[[], None] = None,
    on_language_change: Callable[[], None] = None,
) -> ft.Container:
    """
    Create the application header.

    Args:
        page: Flet page object
        app_state: Application state
        title: Page title to display
        on_logout: Callback for logout action
        on_profile: Callback for profile action
        on_new_report: Callback for new report action
        on_refresh: Callback for refresh action
        on_help: Callback for help action
        on_backup: Callback for backup/restore action (admin only)
        on_reservations: Callback for reservation management (admin only)

    Returns:
        Header container
    """
    colors = theme_manager.get_colors()
    from i18n import t as _t, set_language, is_rtl, get_language, available_languages

    def handle_logout(e):
        """Handle logout click."""
        if on_logout:
            on_logout()

    def handle_profile(e):
        """Handle profile click."""
        if on_profile:
            on_profile()

    def handle_new_report(e):
        """Handle new report click."""
        if on_new_report:
            on_new_report()

    def handle_refresh(e):
        """Handle refresh click."""
        if on_refresh:
            on_refresh()

    def handle_help(e):
        """Handle help click."""
        if on_help:
            on_help()

    def handle_backup(e):
        """Handle backup click."""
        if on_backup:
            on_backup()

    def handle_reservations(e):
        """Handle reservations click."""
        if on_reservations:
            on_reservations()

    # Check if user is admin
    is_admin = False
    if app_state.auth_service:
        current_user = app_state.auth_service.get_current_user()
        is_admin = current_user and current_user.get('role') == 'admin'

    # Toolbar buttons (quick actions)
    toolbar_buttons = []

    # New Report button (if user has permission)
    if app_state.auth_service and app_state.auth_service.has_permission('add_report'):
        toolbar_buttons.append(
            app_button(
                _t("header.new_report"),
                icon=ft.Icons.ADD,
                on_click=handle_new_report,
                variant="primary",
            )
        )

    # Refresh button
    toolbar_buttons.append(
        ft.IconButton(
            icon=ft.Icons.REFRESH,
            icon_color=colors["text_secondary"],
            tooltip=_t("header.refresh") + " (F5)",
            on_click=handle_refresh,
        )
    )

    # Help button
    toolbar_buttons.append(
        ft.IconButton(
            icon=ft.Icons.HELP_OUTLINE,
            icon_color=colors["text_secondary"],
            tooltip=_t("header.help") + " (F1)",
            on_click=handle_help,
        )
    )

    # Admin menu button (admin only)
    if is_admin:
        admin_menu = ft.PopupMenuButton(
            icon=ft.Icons.ADMIN_PANEL_SETTINGS,
            icon_color=colors["text_secondary"],
            tooltip=_t("header.admin_tools"),
            items=[
                ft.PopupMenuItem(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.BACKUP, size=18, color=colors["text_secondary"]),
                            ft.Text(_t("header.backup"), color=colors["text_primary"]),
                            ft.Text("Ctrl+B", size=10, color=colors["text_muted"]),
                        ],
                        spacing=10,
                    ),
                    on_click=handle_backup,
                ),
                ft.PopupMenuItem(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.NUMBERS, size=18, color=colors["text_secondary"]),
                            ft.Text(_t("header.reservation_mgmt"), color=colors["text_primary"]),
                            ft.Text("Ctrl+R", size=10, color=colors["text_muted"]),
                        ],
                        spacing=10,
                    ),
                    on_click=handle_reservations,
                ),
            ],
        )
        toolbar_buttons.append(admin_menu)

    # Language toggle (#3): per-user, available to everyone from the header.
    def _change_language(code):
        try:
            if code == get_language():
                return
            if app_state.auth_service:
                app_state.auth_service.set_user_language(code)
            set_language(code)
            page.rtl = is_rtl()
            # live re-render of the whole shell in the new language
            if on_language_change:
                on_language_change()
            else:
                page.update()
        except Exception:
            pass

    language_menu = ft.PopupMenuButton(
        icon=ft.Icons.LANGUAGE,
        tooltip=_t("settings.language"),
        items=[
            ft.PopupMenuItem(
                text=("● " if get_language() == code else "   ") + name,
                on_click=lambda e, c=code: _change_language(c),
            )
            for code, name in available_languages()
        ],
    )

    # Notification button (placeholder)
    notification_button = ft.IconButton(
        icon=ft.Icons.NOTIFICATIONS_OUTLINED,
        icon_color=colors["text_secondary"],
        tooltip=_t("header.notifications"),
        on_click=lambda e: None,  # TODO: Implement notifications
    )

    # User menu
    user_menu = ft.PopupMenuButton(
        content=ft.Container(
            content=ft.Row(
                controls=[
                    ft.Container(
                        content=ft.Text(
                            app_state.get_user_display_name()[0].upper() if app_state.current_user else "?",
                            color=ft.Colors.WHITE,
                            size=12,
                            weight=ft.FontWeight.BOLD,
                        ),
                        width=32,
                        height=32,
                        border_radius=16,
                        bgcolor=colors["primary"],
                        alignment=ft.alignment.center,
                    ),
                    ft.Icon(ft.Icons.ARROW_DROP_DOWN, color=colors["text_secondary"], size=20),
                ],
                spacing=4,
            ),
            padding=ft.padding.symmetric(horizontal=8, vertical=4),
            border_radius=4,
        ),
        items=[
            ft.PopupMenuItem(
                content=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.PERSON, size=18, color=colors["text_secondary"]),
                        ft.Text(_t("header.profile"), color=colors["text_primary"]),
                    ],
                    spacing=10,
                ),
                on_click=handle_profile,
            ),
            ft.PopupMenuItem(),  # Divider
            ft.PopupMenuItem(
                content=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.LOGOUT, size=18, color=colors["danger"]),
                        ft.Text(_t("header.logout"), color=colors["danger"]),
                    ],
                    spacing=10,
                ),
                on_click=handle_logout,
            ),
        ],
    )

    return ft.Container(
        content=ft.Row(
            controls=[
                # Page title
                ft.Text(
                    title,
                    size=20,
                    weight=ft.FontWeight.BOLD,
                    color=colors["text_primary"],
                ),

                # Toolbar buttons
                ft.Row(
                    controls=toolbar_buttons,
                    spacing=4,
                ),

                # Spacer
                ft.Container(expand=True),

                # Actions
                ft.Row(
                    controls=[
                        language_menu,
                        notification_button,
                        ft.VerticalDivider(width=1, color=colors["border"]),
                        user_menu,
                    ],
                    spacing=8,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(horizontal=24, vertical=12),
        bgcolor=colors["bg_secondary"],
        border=ft.border.only(bottom=ft.BorderSide(1, colors["border"])),
    )


# Note: UserControl was removed in Flet 0.21+
# Use function-based component (create_header) instead
