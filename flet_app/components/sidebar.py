"""
Sidebar Navigation Component for FIU Report Management System.
Provides navigation rail with role-based menu items.
"""
import flet as ft
from typing import Callable, Optional, Any, List

from theme.theme_manager import theme_manager
from theme.colors import Colors
from i18n import t
from components.branding import logo_image


# Note: UserControl was removed in Flet 0.21+
# Use function-based component (create_sidebar) instead


def create_sidebar(
    app_state: Any,
    on_navigate: Callable[[str], None],
    current_route: str = "/dashboard",
) -> ft.Container:
    """
    Create a sidebar navigation component.

    Args:
        app_state: Application state
        on_navigate: Navigation callback
        current_route: Current active route

    Returns:
        Sidebar container
    """
    colors = theme_manager.get_colors()

    def get_nav_items() -> List[dict]:
        """Get navigation items based on user role."""
        items = [
            {"icon": ft.Icons.DASHBOARD, "label": t("nav.dashboard"), "route": "/dashboard"},
            {"icon": ft.Icons.DESCRIPTION, "label": t("nav.reports"), "route": "/reports"},
            {"icon": ft.Icons.DOWNLOAD, "label": t("nav.export"), "route": "/export"},
        ]

        # My Work: a personal queue for anyone who creates reports (agent /
        # supervisor / admin) — drafts, returned-for-rework, pending, approved.
        if app_state.auth_service and app_state.auth_service.has_permission('add_report'):
            items.insert(2, {"icon": ft.Icons.INBOX, "label": t("nav.my_work"), "route": "/my-work"})

        auth = app_state.auth_service
        can_approve = bool(auth and auth.has_permission('approve_reports'))

        # Approvals: anyone with approval authority (supervisor OR admin)
        if can_approve:
            items.extend([
                {"type": "divider"},
                {"icon": ft.Icons.CHECK_CIRCLE, "label": t("nav.approvals"), "route": "/approvals"},
            ])

        # Admin tools: admins only
        if app_state.is_admin():
            items.extend([
                {"icon": ft.Icons.PEOPLE, "label": t("nav.users"), "route": "/users"},
                {"icon": ft.Icons.HISTORY, "label": t("nav.logs"), "route": "/logs"},
                {"type": "divider"},
                {"icon": ft.Icons.SETTINGS, "label": t("nav.settings"), "route": "/settings"},
                {"icon": ft.Icons.LIST, "label": t("nav.dropdowns"), "route": "/dropdown-management"},
                {"icon": ft.Icons.TUNE, "label": t("nav.fields"), "route": "/field-management"},
                {"icon": ft.Icons.DASHBOARD_CUSTOMIZE, "label": t("nav.widgets"), "route": "/dashboard-widgets"},
            ])

        return items

    def create_nav_item(item: dict, is_active: bool) -> ft.Control:
        """Create a navigation item."""
        if item.get("type") == "divider":
            return ft.Container(
                content=ft.Divider(color=colors["border"], height=1),
                margin=ft.margin.symmetric(vertical=8, horizontal=12),
            )

        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(
                        item["icon"],
                        color=ft.Colors.WHITE if is_active else colors["text_secondary"],
                        size=20,
                    ),
                    ft.Text(
                        item["label"],
                        color=ft.Colors.WHITE if is_active else colors["text_secondary"],
                        size=13,
                        weight=ft.FontWeight.W_500 if is_active else ft.FontWeight.NORMAL,
                    ),
                ],
                spacing=12,
            ),
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
            border_radius=4,
            bgcolor=colors["primary"] if is_active else "transparent",
            on_click=lambda e, r=item["route"]: on_navigate(r),
            ink=True,
        )

    nav_items = get_nav_items()
    nav_controls = [
        create_nav_item(item, item.get("route") == current_route)
        for item in nav_items
    ]

    # User info
    user_info = ft.Container(
        content=ft.Row(
            controls=[
                ft.Container(
                    content=ft.Text(
                        app_state.get_user_display_name()[0].upper() if app_state.current_user else "?",
                        color=ft.Colors.WHITE,
                        size=14,
                        weight=ft.FontWeight.BOLD,
                    ),
                    width=36,
                    height=36,
                    border_radius=18,
                    bgcolor=colors["primary"],
                    alignment=ft.alignment.center,
                ),
                ft.Column(
                    controls=[
                        ft.Text(
                            app_state.get_user_display_name(),
                            color=colors["text_primary"],
                            size=13,
                            weight=ft.FontWeight.W_500,
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                        ft.Text(
                            app_state.get_user_role().capitalize(),
                            color=colors["text_secondary"],
                            size=11,
                        ),
                    ],
                    spacing=2,
                ),
            ],
            spacing=12,
        ),
        padding=ft.padding.all(16),
        border=ft.border.only(top=ft.BorderSide(1, colors["border"])),
    )

    return ft.Container(
        content=ft.Column(
            controls=[
                # Logo
                ft.Container(
                    content=ft.Row(
                        controls=[
                            logo_image(28, fallback_color=colors["accent"]),
                            ft.Text(t("app.title"), color=colors["text_primary"], size=16, weight=ft.FontWeight.BOLD),
                        ],
                        spacing=10,
                    ),
                    padding=ft.padding.all(16),
                    margin=ft.margin.only(bottom=8),
                ),
                # Nav items
                ft.Container(
                    content=ft.Column(controls=nav_controls, spacing=4),
                    padding=ft.padding.symmetric(horizontal=8),
                    expand=True,
                ),
                # User info
                user_info,
            ],
            spacing=0,
        ),
        width=240,
        bgcolor=colors["sidebar_bg"],
        border=ft.border.only(right=ft.BorderSide(1, colors["border"])),
    )
