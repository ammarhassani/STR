"""
Reports View for FIU Report Management System.
Displays reports list with filtering, pagination, delete, and CRUD operations.
GitHub-style report management.
"""
import flet as ft
import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from theme.theme_manager import theme_manager
from components.data_table import create_data_table
from components.toast import show_success, show_error
from dialogs.report_dialog import show_report_dialog


# Column definitions for the reports table
REPORT_COLUMNS = [
    {'key': 'sn', 'header': 'SN', 'width': 70},
    {'key': 'report_number', 'header': 'Report Number', 'width': 130},
    {'key': 'report_date', 'header': 'Report Date', 'width': 110},
    {'key': 'reported_entity_name', 'header': 'Reported Entity', 'width': 200, 'max_length': 30},
    {'key': 'nationality', 'header': 'Nationality', 'width': 120},
    {'key': 'id_type', 'header': 'ID Type', 'width': 80},
    {'key': 'id_cr', 'header': 'ID/CR', 'width': 120},
    {'key': 'cic', 'header': 'CIC', 'width': 100},
    {'key': 'type_of_suspected_transaction', 'header': 'Transaction Type', 'width': 150, 'max_length': 25},
    {'key': 'report_classification', 'header': 'Classification', 'width': 120},
    {'key': 'status', 'header': 'Status', 'width': 120},
    {'key': 'approval_status', 'header': 'Approval', 'width': 100},
    {'key': 'created_by', 'header': 'Created By', 'width': 100},
    {'key': 'created_at', 'header': 'Created At', 'width': 150},
]

# All columns for export
ALL_COLUMNS = [
    {'key': 'sn', 'header': 'SN'},
    {'key': 'report_number', 'header': 'Report Number'},
    {'key': 'report_date', 'header': 'Report Date'},
    {'key': 'outgoing_letter_number', 'header': 'Outgoing Letter #'},
    {'key': 'reported_entity_name', 'header': 'Reported Entity'},
    {'key': 'legal_entity_owner', 'header': 'Legal Entity Owner'},
    {'key': 'gender', 'header': 'Gender'},
    {'key': 'nationality', 'header': 'Nationality'},
    {'key': 'id_type', 'header': 'ID Type'},
    {'key': 'id_cr', 'header': 'ID/CR'},
    {'key': 'relationship', 'header': 'Relationship'},
    {'key': 'account_membership', 'header': 'Account/Membership'},
    {'key': 'branch_id', 'header': 'Branch ID'},
    {'key': 'cic', 'header': 'CIC'},
    {'key': 'first_reason_for_suspicion', 'header': '1st Reason for Suspicion'},
    {'key': 'second_reason_for_suspicion', 'header': '2nd Reason for Suspicion'},
    {'key': 'type_of_suspected_transaction', 'header': 'Transaction Type'},
    {'key': 'arb_staff', 'header': 'ARB Staff'},
    {'key': 'total_transaction', 'header': 'Total Transaction'},
    {'key': 'report_classification', 'header': 'Classification'},
    {'key': 'report_source', 'header': 'Source'},
    {'key': 'reporting_entity', 'header': 'Reporting Entity'},
    {'key': 'reporter_initials', 'header': 'Reporter Initials'},
    {'key': 'sending_date', 'header': 'Sending Date'},
    {'key': 'original_copy_confirmation', 'header': 'Original Copy Confirmation'},
    {'key': 'fiu_number', 'header': 'FIU Number'},
    {'key': 'fiu_letter_receive_date', 'header': 'FIU Letter Receive Date'},
    {'key': 'fiu_feedback', 'header': 'FIU Feedback'},
    {'key': 'fiu_letter_number', 'header': 'FIU Letter Number'},
    {'key': 'fiu_date', 'header': 'FIU Date'},
    {'key': 'status', 'header': 'Status'},
    {'key': 'current_version', 'header': 'Version'},
    {'key': 'approval_status', 'header': 'Approval'},
    {'key': 'created_by', 'header': 'Created By'},
    {'key': 'created_at', 'header': 'Created At'},
    {'key': 'updated_by', 'header': 'Updated By'},
    {'key': 'updated_at', 'header': 'Updated At'},
]

STATUS_OPTIONS = [
    'All', 'Open', 'Case Review', 'Under Investigation',
    'Case Validation', 'Close Case', 'Closed with STR'
]


def build_reports_view(
    page: ft.Page,
    app_state: Any,
    on_add_report: Optional[callable] = None,
    on_edit_report: Optional[callable] = None,
) -> ft.Column:
    """
    Build the reports view with GitHub-style management.

    Args:
        page: Flet page object
        app_state: Application state
        on_add_report: Callback for adding new report
        on_edit_report: Callback for editing a report

    Returns:
        Reports view column
    """
    colors = theme_manager.get_colors()
    is_admin = app_state.is_admin()

    # State
    state = {
        "reports_data": [],
        "total_count": 0,
        "current_page": 1,
        "page_size": 50,
        "is_loading": True,
        "my_reports_only": False,
        "show_deleted": False,
        "deleted_count": 0,
        # Filters
        "search_term": "",
        "status_filter": "All",
        "date_filter_enabled": False,
        "date_from": datetime.now() - timedelta(days=180),
        "date_to": datetime.now(),
    }

    # Refs
    loading_ref = ft.Ref[ft.Container]()
    content_ref = ft.Ref[ft.Container]()
    table_ref = ft.Ref[ft.Container]()
    stats_ref = ft.Ref[ft.Text]()
    page_ref = ft.Ref[ft.Text]()
    prev_btn_ref = ft.Ref[ft.IconButton]()
    next_btn_ref = ft.Ref[ft.IconButton]()
    search_ref = ft.Ref[ft.TextField]()
    status_ref = ft.Ref[ft.Dropdown]()
    show_deleted_switch_ref = ft.Ref[ft.Switch]()
    deleted_count_ref = ft.Ref[ft.Text]()

    async def load_reports():
        """Load reports asynchronously."""
        state["is_loading"] = True
        if loading_ref.current:
            loading_ref.current.visible = True
        if table_ref.current:
            table_ref.current.visible = False
        page.update()

        try:
            loop = asyncio.get_event_loop()

            # Build filters
            status = None if state["status_filter"] == "All" else state["status_filter"]
            created_by = app_state.current_user.get('username') if state["my_reports_only"] else None

            # Get date range if enabled
            df = state["date_from"].strftime('%Y-%m-%d') if state["date_filter_enabled"] else None
            dt = state["date_to"].strftime('%Y-%m-%d') if state["date_filter_enabled"] else None

            offset = (state["current_page"] - 1) * state["page_size"]

            # Fetch reports
            result = await loop.run_in_executor(
                None,
                lambda: app_state.report_service.get_reports(
                    status=status,
                    search_term=state["search_term"] if state["search_term"] else None,
                    date_from=df,
                    date_to=dt,
                    created_by=created_by,
                    limit=state["page_size"],
                    offset=offset,
                    include_deleted=state["show_deleted"],
                )
            )

            state["reports_data"], state["total_count"] = result

            # Also get deleted count if admin
            if is_admin:
                deleted_count = await loop.run_in_executor(
                    None,
                    lambda: app_state.report_service.get_deleted_reports_count() if hasattr(app_state.report_service, 'get_deleted_reports_count') else 0
                )
                state["deleted_count"] = deleted_count

            # Update UI
            update_table_ui()

        except Exception as e:
            print(f"Error loading reports: {e}")
            show_error(page, f"Error loading reports: {str(e)}")

        finally:
            state["is_loading"] = False
            if loading_ref.current:
                loading_ref.current.visible = False
            if table_ref.current:
                table_ref.current.visible = True
            page.update()

    def update_table_ui():
        """Update table with current data."""
        # Update stats
        if stats_ref.current:
            stats_text = f"{state['total_count']} reports"
            if state["show_deleted"]:
                stats_text += f" (including {state['deleted_count']} deleted)"
            stats_ref.current.value = stats_text

        # Update deleted count badge
        if deleted_count_ref.current:
            deleted_count_ref.current.value = f"{state['deleted_count']} deleted"
            deleted_count_ref.current.visible = state["deleted_count"] > 0 and not state["show_deleted"]

        # Update pagination
        total_pages = max(1, (state["total_count"] + state["page_size"] - 1) // state["page_size"])
        if page_ref.current:
            page_ref.current.value = f"Page {state['current_page']} of {total_pages}"
        if prev_btn_ref.current:
            prev_btn_ref.current.disabled = state["current_page"] <= 1
        if next_btn_ref.current:
            next_btn_ref.current.disabled = state["current_page"] >= total_pages

        # Rebuild table
        if table_ref.current:
            table_ref.current.content = build_table()

        page.update()

    def build_table() -> ft.Control:
        """Build the data table with action buttons."""
        if not state["reports_data"]:
            return ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Icon(ft.Icons.DESCRIPTION, size=48, color=colors["text_muted"]),
                        ft.Text("No reports found", color=colors["text_muted"]),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                expand=True,
                alignment=ft.alignment.center,
            )

        # Build data rows
        rows = []
        for report in state["reports_data"]:
            is_deleted = report.get('is_deleted', 0) == 1

            cells = []
            for col in REPORT_COLUMNS:
                value = report.get(col['key'], '')
                if value is None:
                    value = ''

                # Format approval status with color
                cell_color = colors["text_muted"] if is_deleted else colors["text_primary"]
                if col['key'] == 'approval_status' and not is_deleted:
                    if value == 'approved':
                        cell_color = colors["success"]
                    elif value == 'pending_approval':
                        cell_color = colors["warning"]
                    elif value == 'rejected':
                        cell_color = colors["danger"]
                    elif value == 'rework':
                        cell_color = colors["info"]

                # Truncate
                max_len = col.get('max_length', 40)
                text_value = str(value)
                if len(text_value) > max_len:
                    text_value = text_value[:max_len] + '...'

                cells.append(
                    ft.DataCell(
                        ft.Text(
                            text_value,
                            size=12,
                            color=cell_color,
                            overflow=ft.TextOverflow.ELLIPSIS,
                            text_decoration=ft.TextDecoration.LINE_THROUGH if is_deleted else None,
                        ),
                    )
                )

            # Add action cell
            action_buttons = []

            if is_deleted:
                # Restore button for deleted reports (admin only)
                if is_admin:
                    action_buttons.append(
                        ft.IconButton(
                            icon=ft.Icons.RESTORE,
                            icon_color=colors["success"],
                            icon_size=18,
                            tooltip="Restore report",
                            on_click=lambda e, r=report: handle_restore_report(r),
                        )
                    )
                    action_buttons.append(
                        ft.IconButton(
                            icon=ft.Icons.DELETE_FOREVER,
                            icon_color=colors["danger"],
                            icon_size=18,
                            tooltip="Permanently delete",
                            on_click=lambda e, r=report: handle_hard_delete_report(r),
                        )
                    )
            else:
                # Edit button
                action_buttons.append(
                    ft.IconButton(
                        icon=ft.Icons.EDIT,
                        icon_color=colors["primary"],
                        icon_size=18,
                        tooltip="Edit report",
                        on_click=lambda e, r=report: handle_row_click(r),
                    )
                )
                # Version history button
                action_buttons.append(
                    ft.IconButton(
                        icon=ft.Icons.HISTORY,
                        icon_color=colors["text_secondary"],
                        icon_size=18,
                        tooltip="Version history",
                        on_click=lambda e, r=report: handle_version_history(r),
                    )
                )
                # Delete button (admin only)
                if is_admin:
                    action_buttons.append(
                        ft.IconButton(
                            icon=ft.Icons.DELETE_OUTLINE,
                            icon_color=colors["danger"],
                            icon_size=18,
                            tooltip="Delete report",
                            on_click=lambda e, r=report: handle_delete_report(r),
                        )
                    )

            cells.append(
                ft.DataCell(
                    ft.Row(
                        controls=action_buttons,
                        spacing=0,
                    )
                )
            )

            # Row styling for deleted
            row_color = f"{colors['danger']}10" if is_deleted else None

            rows.append(
                ft.DataRow(
                    cells=cells,
                    color=row_color,
                )
            )

        # Build columns (add Actions column)
        columns = [
            ft.DataColumn(
                ft.Text(
                    col['header'],
                    weight=ft.FontWeight.BOLD,
                    size=12,
                    color=colors["text_primary"],
                ),
            )
            for col in REPORT_COLUMNS
        ]
        columns.append(
            ft.DataColumn(
                ft.Text(
                    "Actions",
                    weight=ft.FontWeight.BOLD,
                    size=12,
                    color=colors["text_primary"],
                ),
            )
        )

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

    def handle_row_click(report: Dict):
        """Handle report row click."""
        if report.get('is_deleted', 0) == 1:
            return  # Don't open deleted reports for editing

        if on_edit_report:
            on_edit_report(report)
        else:
            # Open report dialog for editing
            show_report_dialog(
                page,
                app_state,
                report_data=report,
                on_save=lambda: page.run_task(load_reports),
            )

    def handle_version_history(report: Dict):
        """Open version history dialog."""
        from dialogs.version_history_dialog import show_version_history_dialog

        report_id = report.get('report_id', report.get('id'))
        show_version_history_dialog(
            page=page,
            app_state=app_state,
            report_id=report_id,
            on_restore=lambda: page.run_task(load_reports),
            on_change=lambda: page.run_task(load_reports),
        )

    def handle_delete_report(report: Dict):
        """Handle delete report."""
        from dialogs.delete_confirmation_dialog import show_report_delete_dialog

        report_id = report.get('report_id', report.get('id'))
        report_number = report.get('report_number', str(report_id))
        entity_name = report.get('reported_entity_name', '')

        def on_soft_delete():
            try:
                success, message = app_state.report_service.delete_report(
                    report_id,
                    app_state.current_user['username']
                )
                if success:
                    show_success(page, message)
                    page.run_task(load_reports)
                else:
                    show_error(page, message)
            except Exception as e:
                show_error(page, f"Failed to delete report: {str(e)}")

        def on_hard_delete():
            try:
                success, message = app_state.report_service.hard_delete_report(
                    report_id,
                    app_state.current_user['username'],
                    "User requested permanent deletion"
                )
                if success:
                    show_success(page, message)
                    page.run_task(load_reports)
                else:
                    show_error(page, message)
            except Exception as e:
                show_error(page, f"Failed to permanently delete report: {str(e)}")

        show_report_delete_dialog(
            page=page,
            app_state=app_state,
            report_id=report_id,
            report_number=report_number,
            entity_name=entity_name,
            on_soft_delete=on_soft_delete,
            on_hard_delete=on_hard_delete,
        )

    def handle_restore_report(report: Dict):
        """Handle restore deleted report."""
        report_id = report.get('report_id', report.get('id'))
        report_number = report.get('report_number', str(report_id))

        def confirm_restore(e):
            confirm_dialog.open = False
            page.update()

            try:
                success, message = app_state.report_service.restore_report(
                    report_id,
                    app_state.current_user['username']
                )
                if success:
                    show_success(page, message)
                    page.run_task(load_reports)
                else:
                    show_error(page, message)
            except Exception as e:
                show_error(page, f"Failed to restore report: {str(e)}")

        def cancel_restore(e):
            confirm_dialog.open = False
            page.update()

        confirm_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.RESTORE, color=colors["success"], size=24),
                    ft.Text("Restore Report", weight=ft.FontWeight.BOLD),
                ],
                spacing=8,
            ),
            content=ft.Text(
                f"Are you sure you want to restore Report #{report_number}?\n\n"
                "This will make the report visible and editable again."
            ),
            actions=[
                ft.TextButton("Cancel", on_click=cancel_restore),
                ft.ElevatedButton(
                    "Restore",
                    icon=ft.Icons.RESTORE,
                    bgcolor=colors["success"],
                    color=ft.Colors.WHITE,
                    on_click=confirm_restore,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.overlay.append(confirm_dialog)
        confirm_dialog.open = True
        page.update()

    def handle_hard_delete_report(report: Dict):
        """Handle permanent delete for already soft-deleted report."""
        from dialogs.delete_confirmation_dialog import show_delete_confirmation_dialog

        report_id = report.get('report_id', report.get('id'))
        report_number = report.get('report_number', str(report_id))
        entity_name = report.get('reported_entity_name', '')

        description = f"Report #{report_number}"
        if entity_name:
            description += f"\n{entity_name}"

        def on_hard_delete():
            try:
                success, message = app_state.report_service.hard_delete_report(
                    report_id,
                    app_state.current_user['username'],
                    "User requested permanent deletion"
                )
                if success:
                    show_success(page, message)
                    page.run_task(load_reports)
                else:
                    show_error(page, message)
            except Exception as e:
                show_error(page, f"Failed to permanently delete report: {str(e)}")

        show_delete_confirmation_dialog(
            page=page,
            app_state=app_state,
            item_type="report",
            item_id=report_id,
            item_description=description,
            impact=app_state.report_service.get_report_impact(report_id) if hasattr(app_state.report_service, 'get_report_impact') else None,
            on_soft_delete=None,  # Already soft deleted
            on_hard_delete=on_hard_delete,
        )

    def handle_search(e):
        """Handle search."""
        state["search_term"] = search_ref.current.value if search_ref.current else ""
        state["current_page"] = 1
        page.run_task(load_reports)

    def handle_status_change(e):
        """Handle status filter change."""
        state["status_filter"] = status_ref.current.value if status_ref.current else "All"
        state["current_page"] = 1
        page.run_task(load_reports)

    def handle_clear_filters(e):
        """Clear all filters."""
        state["search_term"] = ""
        state["status_filter"] = "All"
        state["current_page"] = 1
        state["show_deleted"] = False
        if search_ref.current:
            search_ref.current.value = ""
        if status_ref.current:
            status_ref.current.value = "All"
        if show_deleted_switch_ref.current:
            show_deleted_switch_ref.current.value = False
        page.run_task(load_reports)

    def handle_prev_page(e):
        """Go to previous page."""
        if state["current_page"] > 1:
            state["current_page"] -= 1
            page.run_task(load_reports)

    def handle_next_page(e):
        """Go to next page."""
        total_pages = max(1, (state["total_count"] + state["page_size"] - 1) // state["page_size"])
        if state["current_page"] < total_pages:
            state["current_page"] += 1
            page.run_task(load_reports)

    def handle_add_report(e):
        """Handle add report button."""
        if on_add_report:
            on_add_report()
        else:
            # Open report dialog for new report
            show_report_dialog(
                page,
                app_state,
                report_data=None,
                on_save=lambda: page.run_task(load_reports),
            )

    def handle_refresh(e):
        """Refresh reports."""
        page.run_task(load_reports)

    def toggle_my_reports(e):
        """Toggle my reports filter."""
        state["my_reports_only"] = not state["my_reports_only"]
        state["current_page"] = 1
        page.run_task(load_reports)

    def toggle_show_deleted(e):
        """Toggle showing deleted reports."""
        state["show_deleted"] = e.control.value
        state["current_page"] = 1
        page.run_task(load_reports)

    # Header row
    header_row = ft.Row(
        controls=[
            ft.Text(
                "Reports Management",
                size=18,
                weight=ft.FontWeight.BOLD,
                color=colors["text_primary"],
            ),
            ft.Container(expand=True),
            # Deleted count badge (admin only)
            ft.Container(
                ref=deleted_count_ref,
                content=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.DELETE_OUTLINE, color=colors["danger"], size=16),
                        ft.Text(
                            "0 deleted",
                            size=12,
                            color=colors["danger"],
                        ),
                    ],
                    spacing=4,
                ),
                padding=ft.padding.symmetric(horizontal=8, vertical=4),
                border_radius=4,
                bgcolor=f"{colors['danger']}20",
                visible=False,
            ) if is_admin else ft.Container(),
            # My Reports button (for non-admins)
            ft.ElevatedButton(
                "My Reports",
                icon=ft.Icons.PERSON,
                on_click=toggle_my_reports,
                style=ft.ButtonStyle(
                    bgcolor=colors["primary"] if state["my_reports_only"] else colors["bg_secondary"],
                    color=ft.Colors.WHITE if state["my_reports_only"] else colors["text_primary"],
                ),
            ) if not is_admin else ft.Container(),
            ft.ElevatedButton(
                "Add New Report",
                icon=ft.Icons.ADD,
                on_click=handle_add_report,
                style=ft.ButtonStyle(
                    bgcolor=colors["primary"],
                    color=ft.Colors.WHITE,
                ),
            ),
        ],
        spacing=12,
    )

    # Filter row
    filter_controls = [
        ft.Text("Search:", color=colors["text_secondary"]),
        ft.TextField(
            ref=search_ref,
            hint_text="Search by report number, entity, or CIC...",
            width=300,
            height=40,
            text_size=13,
            content_padding=ft.padding.symmetric(horizontal=12, vertical=0),
            on_submit=handle_search,
        ),
        ft.Text("Status:", color=colors["text_secondary"]),
        ft.Dropdown(
            ref=status_ref,
            value="All",
            options=[ft.dropdown.Option(s) for s in STATUS_OPTIONS],
            width=180,
            text_size=13,
            on_change=handle_status_change,
        ),
    ]

    # Add "Show Deleted" toggle for admins
    if is_admin:
        filter_controls.extend([
            ft.VerticalDivider(width=16, color=colors["border"]),
            ft.Switch(
                ref=show_deleted_switch_ref,
                label="Show Deleted",
                value=False,
                on_change=toggle_show_deleted,
                active_color=colors["danger"],
            ),
        ])

    filter_controls.extend([
        ft.IconButton(
            icon=ft.Icons.SEARCH,
            icon_color=colors["text_primary"],
            tooltip="Search",
            on_click=handle_search,
        ),
        ft.IconButton(
            icon=ft.Icons.CLEAR,
            icon_color=colors["text_secondary"],
            tooltip="Clear filters",
            on_click=handle_clear_filters,
        ),
        ft.IconButton(
            icon=ft.Icons.REFRESH,
            icon_color=colors["text_secondary"],
            tooltip="Refresh",
            on_click=handle_refresh,
        ),
    ])

    filter_row = ft.Row(
        controls=filter_controls,
        spacing=12,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # Stats and pagination row
    stats_row = ft.Row(
        controls=[
            ft.Text(
                ref=stats_ref,
                value="0 reports",
                size=13,
                color=colors["text_secondary"],
            ),
            ft.Container(expand=True),
            ft.IconButton(
                ref=prev_btn_ref,
                icon=ft.Icons.CHEVRON_LEFT,
                icon_color=colors["text_primary"],
                tooltip="Previous page",
                disabled=True,
                on_click=handle_prev_page,
            ),
            ft.Text(
                ref=page_ref,
                value="Page 1 of 1",
                size=13,
                color=colors["text_primary"],
            ),
            ft.IconButton(
                ref=next_btn_ref,
                icon=ft.Icons.CHEVRON_RIGHT,
                icon_color=colors["text_primary"],
                tooltip="Next page",
                disabled=True,
                on_click=handle_next_page,
            ),
        ],
    )

    # Loading indicator
    loading_container = ft.Container(
        ref=loading_ref,
        content=ft.Column(
            controls=[
                ft.ProgressRing(width=32, height=32, color=colors["primary"]),
                ft.Text("Loading reports...", color=colors["text_secondary"]),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=8,
        ),
        expand=True,
        alignment=ft.alignment.center,
        visible=True,
    )

    # Table container
    table_container = ft.Container(
        ref=table_ref,
        content=ft.Text("Loading...", color=colors["text_muted"]),
        expand=True,
        visible=False,
    )

    # Trigger initial load
    page.run_task(load_reports)

    return ft.Column(
        controls=[
            header_row,
            ft.Container(height=16),
            filter_row,
            ft.Container(height=8),
            stats_row,
            ft.Container(height=8),
            ft.Container(
                content=ft.Stack(
                    controls=[
                        loading_container,
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
