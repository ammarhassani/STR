"""
Delete Confirmation Dialog for FIU Report Management System.
Provides soft delete and hard delete options with appropriate warnings.
"""
import flet as ft
from typing import Optional, Any, Callable, Dict

from theme.theme_manager import theme_manager


def show_delete_confirmation_dialog(
    page: ft.Page,
    app_state: Any,
    item_type: str,
    item_id: int,
    item_description: str,
    impact: Optional[Dict[str, int]] = None,
    on_soft_delete: Optional[Callable[[], None]] = None,
    on_hard_delete: Optional[Callable[[], None]] = None,
):
    """
    Show delete confirmation dialog with soft/hard delete options.

    Args:
        page: Flet page object
        app_state: Application state with services
        item_type: Type of item ('report' or 'version')
        item_id: ID of the item to delete
        item_description: Human-readable description of the item
        impact: Dictionary with counts of affected items (versions, approvals, etc.)
        on_soft_delete: Callback when soft delete is confirmed
        on_hard_delete: Callback when hard delete is confirmed
    """
    colors = theme_manager.get_colors()

    def close_dialog(e=None):
        dialog.open = False
        page.update()

    def handle_soft_delete(e):
        close_dialog()
        if on_soft_delete:
            on_soft_delete()

    def handle_hard_delete(e):
        # Show additional confirmation for hard delete
        def confirm_hard_delete(e):
            confirm_dialog.open = False
            page.update()
            if on_hard_delete:
                on_hard_delete()

        def cancel_hard_delete(e):
            confirm_dialog.open = False
            page.update()

        confirm_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.WARNING_AMBER, color=colors["danger"], size=24),
                    ft.Text("Confirm Permanent Deletion", weight=ft.FontWeight.BOLD),
                ],
                spacing=8,
            ),
            content=ft.Column(
                controls=[
                    ft.Text(
                        "This action CANNOT be undone!",
                        color=colors["danger"],
                        weight=ft.FontWeight.BOLD,
                        size=14,
                    ),
                    ft.Container(height=8),
                    ft.Text(
                        f"You are about to permanently delete:\n{item_description}",
                        color=colors["text_primary"],
                        size=13,
                    ),
                    ft.Container(height=8),
                    ft.Text(
                        "Type 'DELETE' to confirm:",
                        color=colors["text_secondary"],
                        size=12,
                    ),
                    ft.TextField(
                        hint_text="Type DELETE",
                        border_color=colors["border"],
                        focused_border_color=colors["danger"],
                        on_change=lambda e: update_confirm_button(e.control.value),
                    ),
                ],
                spacing=4,
                tight=True,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=cancel_hard_delete),
                ft.ElevatedButton(
                    "Permanently Delete",
                    bgcolor=colors["danger"],
                    color=ft.Colors.WHITE,
                    disabled=True,
                    on_click=confirm_hard_delete,
                    data="confirm_btn",
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        confirm_btn = None
        for action in confirm_dialog.actions:
            if hasattr(action, 'data') and action.data == "confirm_btn":
                confirm_btn = action
                break

        def update_confirm_button(value):
            if confirm_btn:
                confirm_btn.disabled = value.upper() != "DELETE"
                page.update()

        page.overlay.append(confirm_dialog)
        confirm_dialog.open = True
        close_dialog()
        page.update()

    # Build impact warning if available
    impact_controls = []
    if impact:
        impact_controls.append(
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text(
                            "This action will affect:",
                            weight=ft.FontWeight.W_500,
                            color=colors["text_primary"],
                            size=13,
                        ),
                        ft.Row(
                            controls=[
                                ft.Container(
                                    content=ft.Column(
                                        controls=[
                                            ft.Text(
                                                str(impact.get('versions', 0)),
                                                size=20,
                                                weight=ft.FontWeight.BOLD,
                                                color=colors["primary"],
                                            ),
                                            ft.Text("Versions", size=11, color=colors["text_secondary"]),
                                        ],
                                        spacing=2,
                                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                    ),
                                    expand=True,
                                    alignment=ft.alignment.center,
                                ),
                                ft.Container(
                                    content=ft.Column(
                                        controls=[
                                            ft.Text(
                                                str(impact.get('approvals', 0)),
                                                size=20,
                                                weight=ft.FontWeight.BOLD,
                                                color=colors["warning"] if impact.get('pending_approvals', 0) > 0 else colors["primary"],
                                            ),
                                            ft.Text("Approvals", size=11, color=colors["text_secondary"]),
                                        ],
                                        spacing=2,
                                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                    ),
                                    expand=True,
                                    alignment=ft.alignment.center,
                                ),
                            ],
                            spacing=16,
                        ),
                    ],
                    spacing=8,
                ),
                padding=12,
                border_radius=8,
                bgcolor=colors["bg_tertiary"],
                border=ft.border.all(1, colors["border"]),
            )
        )

        if impact.get('pending_approvals', 0) > 0:
            impact_controls.append(
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.WARNING_AMBER, color=colors["warning"], size=16),
                            ft.Text(
                                f"{impact.get('pending_approvals')} pending approval(s) will be cancelled",
                                size=12,
                                color=colors["warning"],
                            ),
                        ],
                        spacing=8,
                    ),
                    padding=8,
                )
            )

    # Create dialog content
    dialog_content = ft.Container(
        content=ft.Column(
            controls=[
                # Header
                ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.DELETE_OUTLINE, color=colors["danger"], size=28),
                        ft.Text(
                            f"Delete {item_type.title()}?",
                            size=18,
                            weight=ft.FontWeight.BOLD,
                            color=colors["text_primary"],
                        ),
                    ],
                    spacing=12,
                ),
                ft.Divider(color=colors["border"]),
                # Description
                ft.Text(
                    item_description,
                    size=14,
                    color=colors["text_primary"],
                ),
                # Impact warning
                *impact_controls,
                ft.Container(height=8),
                # Delete options
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Text(
                                "Choose delete option:",
                                weight=ft.FontWeight.W_500,
                                color=colors["text_primary"],
                                size=13,
                            ),
                            # Soft delete option
                            ft.Container(
                                content=ft.Row(
                                    controls=[
                                        ft.Icon(ft.Icons.DELETE_OUTLINE, color=colors["warning"], size=20),
                                        ft.Column(
                                            controls=[
                                                ft.Text(
                                                    "Soft Delete",
                                                    weight=ft.FontWeight.W_500,
                                                    color=colors["text_primary"],
                                                    size=14,
                                                ),
                                                ft.Text(
                                                    "Can be restored later by an administrator",
                                                    color=colors["text_secondary"],
                                                    size=12,
                                                ),
                                            ],
                                            spacing=2,
                                            expand=True,
                                        ),
                                        ft.ElevatedButton(
                                            "Soft Delete",
                                            bgcolor=colors["warning"],
                                            color=ft.Colors.WHITE,
                                            on_click=handle_soft_delete,
                                        ),
                                    ],
                                    spacing=12,
                                ),
                                padding=12,
                                border_radius=8,
                                border=ft.border.all(1, colors["border"]),
                            ),
                            # Hard delete option
                            ft.Container(
                                content=ft.Row(
                                    controls=[
                                        ft.Icon(ft.Icons.DELETE_FOREVER, color=colors["danger"], size=20),
                                        ft.Column(
                                            controls=[
                                                ft.Text(
                                                    "Permanent Delete",
                                                    weight=ft.FontWeight.W_500,
                                                    color=colors["text_primary"],
                                                    size=14,
                                                ),
                                                ft.Text(
                                                    "Cannot be undone - all data will be permanently removed",
                                                    color=colors["danger"],
                                                    size=12,
                                                ),
                                            ],
                                            spacing=2,
                                            expand=True,
                                        ),
                                        ft.ElevatedButton(
                                            "Hard Delete",
                                            bgcolor=colors["danger"],
                                            color=ft.Colors.WHITE,
                                            on_click=handle_hard_delete,
                                        ),
                                    ],
                                    spacing=12,
                                ),
                                padding=12,
                                border_radius=8,
                                border=ft.border.all(1, colors["danger"]),
                            ),
                        ],
                        spacing=12,
                    ),
                ),
                ft.Container(height=8),
                # Cancel button
                ft.Row(
                    controls=[
                        ft.Container(expand=True),
                        ft.TextButton("Cancel", on_click=close_dialog),
                    ],
                ),
            ],
            spacing=12,
        ),
        width=500,
        padding=24,
    )

    # Create dialog
    dialog = ft.AlertDialog(
        modal=True,
        content=dialog_content,
        shape=ft.RoundedRectangleBorder(radius=12),
    )

    # Show dialog
    page.overlay.append(dialog)
    dialog.open = True
    page.update()


def show_version_delete_dialog(
    page: ft.Page,
    app_state: Any,
    version_id: int,
    version_number: int,
    report_number: str,
    on_soft_delete: Optional[Callable[[], None]] = None,
    on_hard_delete: Optional[Callable[[], None]] = None,
):
    """
    Show delete confirmation dialog for a version.

    Args:
        page: Flet page object
        app_state: Application state
        version_id: Version ID to delete
        version_number: Version number for display
        report_number: Report number for display
        on_soft_delete: Callback when soft delete is confirmed
        on_hard_delete: Callback when hard delete is confirmed
    """
    show_delete_confirmation_dialog(
        page=page,
        app_state=app_state,
        item_type="version",
        item_id=version_id,
        item_description=f"Version {version_number} of Report #{report_number}",
        impact=None,  # Versions don't have sub-items
        on_soft_delete=on_soft_delete,
        on_hard_delete=on_hard_delete,
    )


def show_report_delete_dialog(
    page: ft.Page,
    app_state: Any,
    report_id: int,
    report_number: str,
    entity_name: str = "",
    on_soft_delete: Optional[Callable[[], None]] = None,
    on_hard_delete: Optional[Callable[[], None]] = None,
):
    """
    Show delete confirmation dialog for a report.

    Args:
        page: Flet page object
        app_state: Application state
        report_id: Report ID to delete
        report_number: Report number for display
        entity_name: Entity name for display
        on_soft_delete: Callback when soft delete is confirmed
        on_hard_delete: Callback when hard delete is confirmed
    """
    # Get impact counts
    impact = None
    if app_state.report_service:
        impact = app_state.report_service.get_report_impact(report_id)

    description = f"Report #{report_number}"
    if entity_name:
        description += f"\n{entity_name}"

    show_delete_confirmation_dialog(
        page=page,
        app_state=app_state,
        item_type="report",
        item_id=report_id,
        item_description=description,
        impact=impact,
        on_soft_delete=on_soft_delete,
        on_hard_delete=on_hard_delete,
    )
