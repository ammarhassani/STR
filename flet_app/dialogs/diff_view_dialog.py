"""
Diff View Dialog for FIU Report Management System.
Shows side-by-side and unified diff views for comparing report versions.
"""
import flet as ft
from typing import Optional, Any, Callable, Dict

from theme.theme_manager import theme_manager


# Field display names mapping
FIELD_LABELS = {
    'sn': 'Serial Number',
    'report_number': 'Report Number',
    'report_date': 'Report Date',
    'outgoing_letter_number': 'Outgoing Letter Number',
    'reported_entity_name': 'Reported Entity Name',
    'legal_entity_owner': 'Legal Entity Owner',
    'gender': 'Gender',
    'nationality': 'Nationality',
    'id_cr': 'ID/CR',
    'id_type': 'ID Type',
    'account_membership': 'Account/Membership',
    'relationship': 'Relationship',
    'branch_id': 'Branch ID',
    'cic': 'CIC',
    'first_reason_for_suspicion': 'First Reason for Suspicion',
    'second_reason_for_suspicion': 'Second Reason for Suspicion',
    'type_of_suspected_transaction': 'Type of Suspected Transaction',
    'arb_staff': 'ARB Staff',
    'total_transaction': 'Total Transaction',
    'report_classification': 'Report Classification',
    'report_source': 'Report Source',
    'reporting_entity': 'Reporting Entity',
    'reporter_initials': 'Reporter Initials',
    'sending_date': 'Sending Date',
    'original_copy_confirmation': 'Original Copy Confirmation',
    'fiu_number': 'FIU Number',
    'fiu_letter_receive_date': 'FIU Letter Receive Date',
    'fiu_feedback': 'FIU Feedback',
    'fiu_letter_number': 'FIU Letter Number',
    'fiu_date': 'FIU Date',
    'status': 'Status',
    'approval_status': 'Approval Status',
}

# Diff colors
DIFF_COLORS = {
    'added': '#00d084',      # Green
    'removed': '#f44336',    # Red
    'modified': '#ffa726',   # Orange/Yellow
}


def show_diff_view_dialog(
    page: ft.Page,
    app_state: Any,
    version_id_1: int,
    version_id_2: int,
    on_close: Optional[Callable[[], None]] = None,
):
    """
    Show the diff view dialog comparing two versions.

    Args:
        page: Flet page object
        app_state: Application state with services
        version_id_1: First version ID (older)
        version_id_2: Second version ID (newer)
        on_close: Callback when dialog is closed
    """
    colors = theme_manager.get_colors()
    version_service = app_state.version_service

    # State
    state = {
        "view_mode": "side_by_side",  # "side_by_side" or "unified"
        "comparison_data": None,
        "is_loading": True,
    }

    def load_comparison():
        """Load version comparison data."""
        try:
            state["comparison_data"] = version_service.compare_versions_detailed(
                version_id_1, version_id_2
            )
            state["is_loading"] = False
            update_diff_view()
        except Exception as e:
            state["is_loading"] = False
            show_error(f"Failed to load comparison: {str(e)}")

    def update_diff_view():
        """Update the diff view based on current state."""
        diff_container.controls.clear()

        if state["is_loading"]:
            diff_container.controls.append(
                ft.Container(
                    content=ft.ProgressRing(width=32, height=32),
                    alignment=ft.alignment.center,
                    padding=40,
                )
            )
        elif not state["comparison_data"]:
            diff_container.controls.append(
                ft.Container(
                    content=ft.Text(
                        "Failed to load comparison data",
                        color=colors["text_secondary"],
                    ),
                    alignment=ft.alignment.center,
                    padding=40,
                )
            )
        else:
            if state["view_mode"] == "side_by_side":
                diff_container.controls.append(build_side_by_side_view())
            else:
                diff_container.controls.append(build_unified_view())

        # Update toggle buttons
        side_by_side_btn.bgcolor = colors["primary"] if state["view_mode"] == "side_by_side" else colors["bg_tertiary"]
        side_by_side_btn.color = ft.Colors.WHITE if state["view_mode"] == "side_by_side" else colors["text_primary"]
        unified_btn.bgcolor = colors["primary"] if state["view_mode"] == "unified" else colors["bg_tertiary"]
        unified_btn.color = ft.Colors.WHITE if state["view_mode"] == "unified" else colors["text_primary"]

        page.update()

    def build_side_by_side_view() -> ft.Container:
        """Build side-by-side diff view."""
        data = state["comparison_data"]
        v1 = data.get("version_1", {})
        v2 = data.get("version_2", {})
        differences = data.get("differences", {})

        # Header row
        header = ft.Row(
            controls=[
                ft.Container(
                    content=ft.Text(
                        f"Version {v1.get('version_number', '?')}",
                        weight=ft.FontWeight.BOLD,
                        color=colors["text_primary"],
                    ),
                    expand=True,
                    padding=8,
                    bgcolor=colors["bg_tertiary"],
                    border_radius=ft.border_radius.only(top_left=8),
                ),
                ft.Container(width=2, bgcolor=colors["border"]),
                ft.Container(
                    content=ft.Text(
                        f"Version {v2.get('version_number', '?')}",
                        weight=ft.FontWeight.BOLD,
                        color=colors["text_primary"],
                    ),
                    expand=True,
                    padding=8,
                    bgcolor=colors["bg_tertiary"],
                    border_radius=ft.border_radius.only(top_right=8),
                ),
            ],
            spacing=0,
        )

        # Build diff rows
        rows = [header]

        for field_name, diff in differences.items():
            label = FIELD_LABELS.get(field_name, field_name.replace('_', ' ').title())
            old_value = str(diff.get("old_value", "")) if diff.get("old_value") else ""
            new_value = str(diff.get("new_value", "")) if diff.get("new_value") else ""
            change_type = diff.get("change_type", "modified")

            color = DIFF_COLORS.get(change_type, colors["text_primary"])

            row = ft.Row(
                controls=[
                    # Left side (old value)
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Text(
                                    label,
                                    size=11,
                                    weight=ft.FontWeight.W_500,
                                    color=colors["text_secondary"],
                                ),
                                ft.Text(
                                    old_value or "(empty)",
                                    size=13,
                                    color=DIFF_COLORS["removed"] if change_type == "removed" else colors["text_primary"],
                                    italic=not old_value,
                                ),
                            ],
                            spacing=2,
                        ),
                        expand=True,
                        padding=8,
                        bgcolor=f"{DIFF_COLORS['removed']}15" if change_type in ["removed", "modified"] else "transparent",
                    ),
                    ft.Container(width=2, bgcolor=colors["border"]),
                    # Right side (new value)
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Text(
                                    label,
                                    size=11,
                                    weight=ft.FontWeight.W_500,
                                    color=colors["text_secondary"],
                                ),
                                ft.Text(
                                    new_value or "(empty)",
                                    size=13,
                                    color=DIFF_COLORS["added"] if change_type == "added" else (
                                        DIFF_COLORS["modified"] if change_type == "modified" else colors["text_primary"]
                                    ),
                                    italic=not new_value,
                                ),
                            ],
                            spacing=2,
                        ),
                        expand=True,
                        padding=8,
                        bgcolor=f"{DIFF_COLORS['added']}15" if change_type in ["added", "modified"] else "transparent",
                    ),
                ],
                spacing=0,
            )
            rows.append(row)

        if len(differences) == 0:
            rows.append(
                ft.Container(
                    content=ft.Text(
                        "No differences found",
                        color=colors["text_secondary"],
                        text_align=ft.TextAlign.CENTER,
                    ),
                    alignment=ft.alignment.center,
                    padding=20,
                )
            )

        return ft.Container(
            content=ft.Column(
                controls=rows,
                spacing=1,
                scroll=ft.ScrollMode.AUTO,
            ),
            border=ft.border.all(1, colors["border"]),
            border_radius=8,
            expand=True,
        )

    def build_unified_view() -> ft.Container:
        """Build unified diff view (like git diff)."""
        data = state["comparison_data"]
        v1 = data.get("version_1", {})
        v2 = data.get("version_2", {})
        differences = data.get("differences", {})

        rows = []

        # Header
        rows.append(
            ft.Container(
                content=ft.Text(
                    f"Comparing Version {v1.get('version_number', '?')} → Version {v2.get('version_number', '?')}",
                    weight=ft.FontWeight.BOLD,
                    color=colors["text_primary"],
                ),
                padding=12,
                bgcolor=colors["bg_tertiary"],
                border_radius=ft.border_radius.only(top_left=8, top_right=8),
            )
        )

        for field_name, diff in differences.items():
            label = FIELD_LABELS.get(field_name, field_name.replace('_', ' ').title())
            old_value = str(diff.get("old_value", "")) if diff.get("old_value") else ""
            new_value = str(diff.get("new_value", "")) if diff.get("new_value") else ""
            change_type = diff.get("change_type", "modified")

            # Field label
            rows.append(
                ft.Container(
                    content=ft.Text(
                        label,
                        size=12,
                        weight=ft.FontWeight.W_500,
                        color=colors["text_secondary"],
                    ),
                    padding=ft.padding.only(left=12, top=8, right=12),
                )
            )

            # Old value (removed line)
            if change_type in ["removed", "modified"]:
                rows.append(
                    ft.Container(
                        content=ft.Row(
                            controls=[
                                ft.Text("−", size=14, weight=ft.FontWeight.BOLD, color=DIFF_COLORS["removed"]),
                                ft.Text(
                                    old_value or "(empty)",
                                    size=13,
                                    color=DIFF_COLORS["removed"],
                                    expand=True,
                                ),
                            ],
                            spacing=8,
                        ),
                        padding=ft.padding.only(left=12, right=12, top=2, bottom=2),
                        bgcolor=f"{DIFF_COLORS['removed']}20",
                    )
                )

            # New value (added line)
            if change_type in ["added", "modified"]:
                rows.append(
                    ft.Container(
                        content=ft.Row(
                            controls=[
                                ft.Text("+", size=14, weight=ft.FontWeight.BOLD, color=DIFF_COLORS["added"]),
                                ft.Text(
                                    new_value or "(empty)",
                                    size=13,
                                    color=DIFF_COLORS["added"],
                                    expand=True,
                                ),
                            ],
                            spacing=8,
                        ),
                        padding=ft.padding.only(left=12, right=12, top=2, bottom=2),
                        bgcolor=f"{DIFF_COLORS['added']}20",
                    )
                )

        if len(differences) == 0:
            rows.append(
                ft.Container(
                    content=ft.Text(
                        "No differences found",
                        color=colors["text_secondary"],
                        text_align=ft.TextAlign.CENTER,
                    ),
                    alignment=ft.alignment.center,
                    padding=20,
                )
            )

        return ft.Container(
            content=ft.Column(
                controls=rows,
                spacing=0,
                scroll=ft.ScrollMode.AUTO,
            ),
            border=ft.border.all(1, colors["border"]),
            border_radius=8,
            expand=True,
        )

    def switch_to_side_by_side(e):
        state["view_mode"] = "side_by_side"
        update_diff_view()

    def switch_to_unified(e):
        state["view_mode"] = "unified"
        update_diff_view()

    def show_error(message: str):
        """Show error snackbar."""
        page.snack_bar = ft.SnackBar(
            content=ft.Text(message),
            bgcolor=colors["danger"],
        )
        page.snack_bar.open = True
        page.update()

    def close_dialog(e):
        """Close the dialog."""
        dialog.open = False
        page.update()
        if on_close:
            on_close()

    # Toggle buttons
    side_by_side_btn = ft.ElevatedButton(
        "Side by Side",
        icon=ft.Icons.VIEW_COLUMN,
        on_click=switch_to_side_by_side,
        bgcolor=colors["primary"],
        color=ft.Colors.WHITE,
    )

    unified_btn = ft.ElevatedButton(
        "Unified",
        icon=ft.Icons.VIEW_STREAM,
        on_click=switch_to_unified,
        bgcolor=colors["bg_tertiary"],
        color=colors["text_primary"],
    )

    # Diff container
    diff_container = ft.Column(
        controls=[
            ft.Container(
                content=ft.ProgressRing(width=32, height=32),
                alignment=ft.alignment.center,
                padding=40,
            )
        ],
        expand=True,
    )

    # Summary row
    summary_row = ft.Container(
        content=ft.Row(
            controls=[
                ft.Container(
                    content=ft.Icon(ft.Icons.ADD_CIRCLE, color=DIFF_COLORS["added"], size=16),
                    tooltip="Added",
                ),
                ft.Text("Added", size=12, color=colors["text_secondary"]),
                ft.Container(width=16),
                ft.Container(
                    content=ft.Icon(ft.Icons.REMOVE_CIRCLE, color=DIFF_COLORS["removed"], size=16),
                    tooltip="Removed",
                ),
                ft.Text("Removed", size=12, color=colors["text_secondary"]),
                ft.Container(width=16),
                ft.Container(
                    content=ft.Icon(ft.Icons.CHANGE_CIRCLE, color=DIFF_COLORS["modified"], size=16),
                    tooltip="Modified",
                ),
                ft.Text("Modified", size=12, color=colors["text_secondary"]),
            ],
            spacing=4,
        ),
        padding=ft.padding.only(bottom=8),
    )

    # Create dialog content
    dialog_content = ft.Container(
        content=ft.Column(
            controls=[
                # Header
                ft.Row(
                    controls=[
                        ft.Text(
                            "Compare Versions",
                            size=18,
                            weight=ft.FontWeight.BOLD,
                            color=colors["text_primary"],
                            expand=True,
                        ),
                        ft.IconButton(
                            icon=ft.Icons.CLOSE,
                            icon_color=colors["text_secondary"],
                            on_click=close_dialog,
                        ),
                    ],
                ),
                # Toggle buttons
                ft.Row(
                    controls=[side_by_side_btn, unified_btn],
                    spacing=8,
                ),
                # Summary legend
                summary_row,
                ft.Divider(color=colors["border"]),
                # Diff view
                ft.Container(
                    content=diff_container,
                    expand=True,
                ),
                # Close button
                ft.Row(
                    controls=[
                        ft.Container(expand=True),
                        ft.ElevatedButton(
                            "Close",
                            on_click=close_dialog,
                        ),
                    ],
                ),
            ],
            spacing=12,
        ),
        width=700,
        height=600,
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

    # Load comparison data
    load_comparison()
