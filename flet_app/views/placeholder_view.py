"""
Placeholder View for FIU Report Management System.
Used as a template for views that are not yet implemented.
"""
import flet as ft
from typing import Any

from theme.theme_manager import theme_manager


def build_placeholder_view(
    page: ft.Page,
    app_state: Any,
    title: str,
    description: str = "This feature is coming soon.",
    icon: str = ft.Icons.CONSTRUCTION,
) -> ft.Container:
    """
    Build a placeholder view.

    Args:
        page: Flet page object
        app_state: Application state
        title: View title
        description: Description text
        icon: Icon to display

    Returns:
        Placeholder container
    """
    colors = theme_manager.get_colors()

    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Icon(
                    icon,
                    size=64,
                    color=colors["text_muted"],
                ),
                ft.Container(height=16),
                ft.Text(
                    title,
                    size=24,
                    weight=ft.FontWeight.BOLD,
                    color=colors["text_primary"],
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Container(height=8),
                ft.Text(
                    description,
                    size=14,
                    color=colors["text_secondary"],
                    text_align=ft.TextAlign.CENTER,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        expand=True,
        alignment=ft.alignment.center,
    )


def build_reports_placeholder(page: ft.Page, app_state: Any) -> ft.Container:
    """Build reports view placeholder."""
    return build_placeholder_view(
        page, app_state,
        "Reports",
        "Report management is being implemented.",
        ft.Icons.DESCRIPTION
    )


def build_export_placeholder(page: ft.Page, app_state: Any) -> ft.Container:
    """Build export view placeholder."""
    return build_placeholder_view(
        page, app_state,
        "Export",
        "Export functionality is being implemented.",
        ft.Icons.DOWNLOAD
    )


def build_approvals_placeholder(page: ft.Page, app_state: Any) -> ft.Container:
    """Build approvals view placeholder."""
    return build_placeholder_view(
        page, app_state,
        "Approvals",
        "Approval management is being implemented.",
        ft.Icons.CHECK_CIRCLE
    )


def build_users_placeholder(page: ft.Page, app_state: Any) -> ft.Container:
    """Build users view placeholder."""
    return build_placeholder_view(
        page, app_state,
        "User Management",
        "User management is being implemented.",
        ft.Icons.PEOPLE
    )


def build_logs_placeholder(page: ft.Page, app_state: Any) -> ft.Container:
    """Build logs view placeholder."""
    return build_placeholder_view(
        page, app_state,
        "System Logs",
        "Log management is being implemented.",
        ft.Icons.HISTORY
    )


def build_settings_placeholder(page: ft.Page, app_state: Any) -> ft.Container:
    """Build settings view placeholder."""
    return build_placeholder_view(
        page, app_state,
        "Settings",
        "Settings management is being implemented.",
        ft.Icons.SETTINGS
    )


def build_dropdown_mgmt_placeholder(page: ft.Page, app_state: Any) -> ft.Container:
    """Build dropdown management view placeholder."""
    return build_placeholder_view(
        page, app_state,
        "Dropdown Management",
        "Dropdown management is being implemented.",
        ft.Icons.LIST
    )


def build_field_mgmt_placeholder(page: ft.Page, app_state: Any) -> ft.Container:
    """Build field management view placeholder."""
    return build_placeholder_view(
        page, app_state,
        "Field Management",
        "Field management is being implemented.",
        ft.Icons.TUNE
    )
