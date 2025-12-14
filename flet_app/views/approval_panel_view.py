"""
Approval Panel View for FIU Report Management System.
Admin-only view for managing report approval requests.
"""
import flet as ft
import asyncio
from typing import Any, Dict, List
from datetime import datetime

from theme.theme_manager import theme_manager
from components.toast import show_success, show_error


def build_approval_panel_view(page: ft.Page, app_state: Any) -> ft.Column:
    """
    Build the approval panel view.

    Args:
        page: Flet page object
        app_state: Application state

    Returns:
        Approval panel column
    """
    colors = theme_manager.get_colors()

    # State
    pending_approvals = []
    is_loading = True

    # Refs
    loading_ref = ft.Ref[ft.Container]()
    table_ref = ft.Ref[ft.Container]()
    stats_ref = ft.Ref[ft.Text]()
    empty_ref = ft.Ref[ft.Container]()

    async def load_approvals():
        """Load pending approvals asynchronously."""
        nonlocal pending_approvals, is_loading

        is_loading = True
        if loading_ref.current:
            loading_ref.current.visible = True
        if table_ref.current:
            table_ref.current.visible = False
        if empty_ref.current:
            empty_ref.current.visible = False
        page.update()

        try:
            loop = asyncio.get_event_loop()

            def fetch_approvals():
                if app_state.approval_service:
                    return app_state.approval_service.get_pending_approvals()
                return []

            pending_approvals = await loop.run_in_executor(None, fetch_approvals)
            update_table_ui()

        except Exception as e:
            print(f"Error loading approvals: {e}")
            show_error(page, f"Error loading approvals: {str(e)}")

        finally:
            is_loading = False
            if loading_ref.current:
                loading_ref.current.visible = False
            page.update()

    def update_table_ui():
        """Update table with current data."""
        # Update stats
        if stats_ref.current:
            if pending_approvals:
                stats_ref.current.value = f"Showing {len(pending_approvals)} pending approval request(s)"
            else:
                stats_ref.current.value = "No pending approval requests at this time."

        # Show empty state or table
        if not pending_approvals:
            if table_ref.current:
                table_ref.current.visible = False
            if empty_ref.current:
                empty_ref.current.visible = True
        else:
            if table_ref.current:
                table_ref.current.visible = True
                table_ref.current.content = build_table()
            if empty_ref.current:
                empty_ref.current.visible = False

        page.update()

    def build_table() -> ft.Control:
        """Build the approvals data table."""
        if not pending_approvals:
            return ft.Container()

        # Build data rows
        rows = []
        for idx, approval in enumerate(pending_approvals):
            # Format requested_at
            requested_at = approval.get('requested_at', '')
            try:
                dt = datetime.fromisoformat(requested_at.replace('Z', '+00:00'))
                formatted_date = dt.strftime('%Y-%m-%d %H:%M')
            except:
                formatted_date = str(requested_at)[:16] if requested_at else ''

            # Truncate comment
            comment = approval.get('comment', '')
            comment_display = (comment[:50] + '...') if len(comment) > 50 else comment

            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(approval.get('report_number', '')), size=12, color=colors["text_primary"])),
                        ft.DataCell(ft.Text(approval.get('reported_entity_name', ''), size=12, color=colors["text_primary"])),
                        ft.DataCell(ft.Text(approval.get('requested_by', ''), size=12, color=colors["text_primary"])),
                        ft.DataCell(ft.Text(formatted_date, size=12, color=colors["text_secondary"])),
                        ft.DataCell(
                            ft.Container(
                                content=ft.Text(
                                    "Pending",
                                    size=11,
                                    color=ft.Colors.WHITE,
                                ),
                                bgcolor=colors["warning"],
                                border_radius=10,
                                padding=ft.padding.symmetric(horizontal=8, vertical=2),
                            )
                        ),
                        ft.DataCell(
                            ft.Text(
                                comment_display or "-",
                                size=12,
                                color=colors["text_secondary"],
                                tooltip=comment if comment else "No comment",
                            )
                        ),
                        ft.DataCell(
                            ft.ElevatedButton(
                                "Review",
                                icon=ft.Icons.RATE_REVIEW,
                                bgcolor=colors["primary"],
                                color=ft.Colors.WHITE,
                                on_click=lambda e, a=approval, i=idx: handle_review(a, i),
                            )
                        ),
                    ],
                )
            )

        columns = [
            ft.DataColumn(ft.Text("Report #", weight=ft.FontWeight.BOLD, size=12, color=colors["text_primary"])),
            ft.DataColumn(ft.Text("Entity Name", weight=ft.FontWeight.BOLD, size=12, color=colors["text_primary"])),
            ft.DataColumn(ft.Text("Requested By", weight=ft.FontWeight.BOLD, size=12, color=colors["text_primary"])),
            ft.DataColumn(ft.Text("Requested At", weight=ft.FontWeight.BOLD, size=12, color=colors["text_primary"])),
            ft.DataColumn(ft.Text("Status", weight=ft.FontWeight.BOLD, size=12, color=colors["text_primary"])),
            ft.DataColumn(ft.Text("Comment", weight=ft.FontWeight.BOLD, size=12, color=colors["text_primary"])),
            ft.DataColumn(ft.Text("Actions", weight=ft.FontWeight.BOLD, size=12, color=colors["text_primary"])),
        ]

        return ft.DataTable(
            columns=columns,
            rows=rows,
            column_spacing=16,
            horizontal_lines=ft.BorderSide(1, colors["border"]),
            heading_row_color=colors["bg_tertiary"],
            data_row_color={
                ft.ControlState.HOVERED: colors["hover"],
            },
            border_radius=8,
        )

    def handle_review(approval: Dict, idx: int):
        """Handle review button click."""
        show_approval_decision_dialog(approval)

    def show_approval_decision_dialog(approval: Dict):
        """Show the approval decision dialog."""
        decision_ref = {"value": "approve"}
        comment_ref = ft.Ref[ft.TextField]()

        def submit_decision(e):
            comment = comment_ref.current.value.strip() if comment_ref.current else ""
            decision = decision_ref["value"]

            # Validate comment for reject/rework
            if decision in ["reject", "rework"] and not comment:
                show_error(page, "Please provide feedback for rejection or rework request.")
                return

            decision_dialog.open = False
            page.update()

            process_decision(approval, decision, comment)

        def cancel_decision(e):
            decision_dialog.open = False
            page.update()

        def on_decision_change(e):
            decision_ref["value"] = e.control.value

        decision_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Review Approval Request"),
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        # Report details
                        ft.Container(
                            content=ft.Column(
                                controls=[
                                    ft.Text(f"Report Number: {approval.get('report_number', '')}", size=13),
                                    ft.Text(f"Entity: {approval.get('reported_entity_name', '')}", size=13),
                                    ft.Text(f"Requested By: {approval.get('requested_by', '')}", size=13),
                                    ft.Text(f"Requested At: {approval.get('requested_at', '')}", size=13),
                                    ft.Text(
                                        f"Request Comment: {approval.get('comment', 'None')}",
                                        size=13,
                                        color=colors["text_secondary"],
                                    ) if approval.get('comment') else ft.Container(),
                                ],
                                spacing=4,
                            ),
                            bgcolor=colors["bg_tertiary"],
                            border_radius=8,
                            padding=16,
                        ),

                        ft.Container(height=16),

                        # Decision options
                        ft.Text("Your Decision:", size=14, weight=ft.FontWeight.BOLD, color=colors["text_primary"]),
                        ft.RadioGroup(
                            value="approve",
                            on_change=on_decision_change,
                            content=ft.Column(
                                controls=[
                                    ft.Radio(value="approve", label="Approve - Report is accurate and complete"),
                                    ft.Radio(value="rework", label="Request Rework - Report needs corrections"),
                                    ft.Radio(value="reject", label="Reject - Report is invalid"),
                                ],
                                spacing=8,
                            ),
                        ),

                        ft.Container(height=16),

                        # Comment field
                        ft.Text("Comment (optional but recommended):", size=14, weight=ft.FontWeight.BOLD, color=colors["text_primary"]),
                        ft.TextField(
                            ref=comment_ref,
                            hint_text="Enter your feedback, suggestions, or reasons for this decision...",
                            multiline=True,
                            min_lines=3,
                            max_lines=5,
                            text_size=13,
                            border_radius=8,
                        ),
                    ],
                    spacing=8,
                ),
                width=500,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=cancel_decision),
                ft.ElevatedButton(
                    "Submit Decision",
                    bgcolor=colors["primary"],
                    color=ft.Colors.WHITE,
                    on_click=submit_decision,
                ),
            ],
        )

        page.overlay.append(decision_dialog)
        decision_dialog.open = True
        page.update()

    def process_decision(approval: Dict, decision: str, comment: str):
        """Process the approval decision."""
        try:
            approval_id = approval['approval_id']
            approval_service = app_state.approval_service

            if not approval_service:
                show_error(page, "Approval service not available")
                return

            if decision == 'approve':
                success, message = approval_service.approve_report(approval_id, comment)
            else:
                request_rework = (decision == 'rework')
                success, message = approval_service.reject_report(
                    approval_id, comment, request_rework
                )

            if success:
                show_success(page, message)
                page.run_task(load_approvals)
            else:
                show_error(page, message)

        except Exception as ex:
            show_error(page, f"Failed to process approval: {str(ex)}")

    def handle_refresh(e):
        """Refresh approvals."""
        page.run_task(load_approvals)

    # Header row
    header_row = ft.Row(
        controls=[
            ft.Text(
                "Approval Management",
                size=18,
                weight=ft.FontWeight.BOLD,
                color=colors["text_primary"],
            ),
            ft.Container(expand=True),
            ft.ElevatedButton(
                "Refresh",
                icon=ft.Icons.REFRESH,
                on_click=handle_refresh,
                bgcolor=colors["primary"],
                color=ft.Colors.WHITE,
            ),
        ],
        spacing=12,
    )

    # Stats row
    stats_row = ft.Row(
        controls=[
            ft.Text(
                ref=stats_ref,
                value="Loading...",
                size=13,
                color=colors["text_secondary"],
            ),
        ],
    )

    # Loading indicator
    loading_container = ft.Container(
        ref=loading_ref,
        content=ft.Column(
            controls=[
                ft.ProgressRing(width=32, height=32, color=colors["primary"]),
                ft.Text("Loading approvals...", color=colors["text_secondary"]),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=8,
        ),
        expand=True,
        alignment=ft.alignment.center,
        visible=True,
    )

    # Empty state
    empty_container = ft.Container(
        ref=empty_ref,
        content=ft.Column(
            controls=[
                ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, size=64, color=colors["success"]),
                ft.Text("No pending approval requests", size=16, color=colors["text_muted"]),
                ft.Text("All caught up!", size=13, color=colors["text_secondary"]),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=8,
        ),
        expand=True,
        alignment=ft.alignment.center,
        visible=False,
    )

    # Table container
    table_container = ft.Container(
        ref=table_ref,
        content=ft.Text("Loading...", color=colors["text_muted"]),
        expand=True,
        visible=False,
    )

    # Trigger initial load
    page.run_task(load_approvals)

    return ft.Column(
        controls=[
            header_row,
            ft.Container(height=16),
            stats_row,
            ft.Container(height=8),
            ft.Container(
                content=ft.Stack(
                    controls=[
                        loading_container,
                        empty_container,
                        ft.Container(
                            content=ft.Column(
                                controls=[table_container],
                                scroll=ft.ScrollMode.ALWAYS,
                                expand=True,
                            ),
                            expand=True,
                        ),
                    ],
                ),
                expand=True,
                border=ft.border.all(1, colors["border"]),
                border_radius=8,
                bgcolor=colors["card_bg"],
            ),
        ],
        spacing=0,
        expand=True,
    )
