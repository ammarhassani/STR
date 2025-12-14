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


# Column definitions for the reports table (all columns, no status)
REPORT_COLUMNS = [
    {'key': 'sn', 'header': 'SN', 'width': 60},
    {'key': 'report_number', 'header': 'Report #', 'width': 110},
    {'key': 'case_id', 'header': 'Case ID', 'width': 100},
    {'key': 'report_date', 'header': 'Date', 'width': 90},
    {'key': 'outgoing_letter_number', 'header': 'Letter #', 'width': 90},
    {'key': 'reported_entity_name', 'header': 'Entity Name', 'width': 160, 'max_length': 20},
    {'key': 'legal_entity_owner', 'header': 'Legal Owner', 'width': 90},
    {'key': 'gender', 'header': 'Gender', 'width': 70},
    {'key': 'nationality', 'header': 'Nationality', 'width': 100},
    {'key': 'id_type', 'header': 'ID Type', 'width': 70},
    {'key': 'id_cr', 'header': 'ID/CR', 'width': 100},
    {'key': 'relationship', 'header': 'Relation', 'width': 100},
    {'key': 'account_membership', 'header': 'Account', 'width': 100},
    {'key': 'branch_id', 'header': 'Branch', 'width': 70},
    {'key': 'cic', 'header': 'CIC', 'width': 130},
    {'key': 'first_reason_for_suspicion', 'header': '1st Reason', 'width': 120, 'max_length': 15},
    {'key': 'second_reason_for_suspicion', 'header': '2nd Reason', 'width': 120, 'max_length': 15},
    {'key': 'type_of_suspected_transaction', 'header': 'Trans Type', 'width': 100, 'max_length': 12},
    {'key': 'arb_staff', 'header': 'ARB Staff', 'width': 90},
    {'key': 'total_transaction', 'header': 'Total Trans', 'width': 100},
    {'key': 'report_classification', 'header': 'Class', 'width': 80},
    {'key': 'report_source', 'header': 'Source', 'width': 80},
    {'key': 'reporting_entity', 'header': 'Rep Entity', 'width': 90},
    {'key': 'reporter_initials', 'header': 'Initials', 'width': 70},
    {'key': 'sending_date', 'header': 'Sent', 'width': 90},
    {'key': 'original_copy_confirmation', 'header': 'Orig Copy', 'width': 80},
    {'key': 'fiu_number', 'header': 'FIU #', 'width': 80},
    {'key': 'fiu_letter_receive_date', 'header': 'FIU Recv', 'width': 90},
    {'key': 'fiu_feedback', 'header': 'FIU FB', 'width': 80},
    {'key': 'fiu_letter_number', 'header': 'FIU Letter', 'width': 90},
    {'key': 'fiu_date', 'header': 'FIU Date', 'width': 90},
    {'key': 'current_version', 'header': 'Ver', 'width': 50},
    {'key': 'approval_status', 'header': 'Approval', 'width': 100},
    {'key': 'created_by', 'header': 'Created By', 'width': 90},
    {'key': 'created_at', 'header': 'Created At', 'width': 130},
    {'key': 'updated_by', 'header': 'Updated By', 'width': 90},
    {'key': 'updated_at', 'header': 'Updated At', 'width': 130},
]

# All columns for export (same as display, no status)
ALL_COLUMNS = [
    {'key': 'sn', 'header': 'SN'},
    {'key': 'report_number', 'header': 'Report Number'},
    {'key': 'case_id', 'header': 'Case ID'},
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
    {'key': 'current_version', 'header': 'Version'},
    {'key': 'approval_status', 'header': 'Approval'},
    {'key': 'created_by', 'header': 'Created By'},
    {'key': 'created_at', 'header': 'Created At'},
    {'key': 'updated_by', 'header': 'Updated By'},
    {'key': 'updated_at', 'header': 'Updated At'},
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
        "date_filter_enabled": False,
        "date_from": datetime.now() - timedelta(days=180),
        "date_to": datetime.now(),
        # Bulk selection
        "selected_ids": set(),
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
    show_deleted_switch_ref = ft.Ref[ft.Switch]()
    deleted_count_ref = ft.Ref[ft.Text]()
    bulk_actions_ref = ft.Ref[ft.Container]()
    select_all_ref = ft.Ref[ft.Checkbox]()
    selection_count_ref = ft.Ref[ft.Text]()

    async def load_reports():
        """Load reports asynchronously."""
        state["is_loading"] = True
        state["selected_ids"] = set()  # Clear selection on reload
        if loading_ref.current:
            loading_ref.current.visible = True
        if table_ref.current:
            table_ref.current.visible = False
        if bulk_actions_ref.current:
            bulk_actions_ref.current.visible = False
        page.update()

        try:
            loop = asyncio.get_event_loop()

            # Build filters
            created_by = app_state.current_user.get('username') if state["my_reports_only"] else None

            # Get date range if enabled
            df = state["date_from"].strftime('%Y-%m-%d') if state["date_filter_enabled"] else None
            dt = state["date_to"].strftime('%Y-%m-%d') if state["date_filter_enabled"] else None

            offset = (state["current_page"] - 1) * state["page_size"]

            # Fetch reports
            result = await loop.run_in_executor(
                None,
                lambda: app_state.report_service.get_reports(
                    status=None,
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

    def update_bulk_actions_ui():
        """Update bulk actions bar visibility and selection count."""
        selected_count = len(state["selected_ids"])
        has_selection = selected_count > 0

        if bulk_actions_ref.current:
            bulk_actions_ref.current.visible = has_selection

        if selection_count_ref.current:
            selection_count_ref.current.value = f"{selected_count} selected"

        # Update select all checkbox state
        if select_all_ref.current and state["reports_data"]:
            all_ids = {r.get('report_id', r.get('id')) for r in state["reports_data"]}
            if state["selected_ids"] == all_ids and all_ids:
                select_all_ref.current.value = True
            elif state["selected_ids"] & all_ids:  # Some selected
                select_all_ref.current.value = None  # Indeterminate
            else:
                select_all_ref.current.value = False

        page.update()

    def toggle_select_all(e):
        """Toggle select all reports on current page."""
        # Get all report IDs on current page
        all_ids = {r.get('report_id', r.get('id')) for r in state["reports_data"]}

        # Check if all are currently selected
        all_currently_selected = state["selected_ids"] >= all_ids and len(all_ids) > 0

        if all_currently_selected:
            # Deselect all
            state["selected_ids"].clear()
        else:
            # Select all on current page
            for report in state["reports_data"]:
                report_id = report.get('report_id', report.get('id'))
                state["selected_ids"].add(report_id)

        # Update bulk actions bar
        selected_count = len(state["selected_ids"])
        if bulk_actions_ref.current:
            bulk_actions_ref.current.visible = selected_count > 0
        if selection_count_ref.current:
            selection_count_ref.current.value = f"{selected_count} selected"

        # Rebuild table to update checkboxes
        if table_ref.current:
            table_ref.current.content = build_table()
        page.update()

    def toggle_select_report(report_id: int, selected: bool):
        """Toggle selection of a single report."""
        if selected:
            state["selected_ids"].add(report_id)
        else:
            state["selected_ids"].discard(report_id)
        update_bulk_actions_ui()

    def clear_selection():
        """Clear all selections."""
        state["selected_ids"].clear()
        update_bulk_actions_ui()
        if table_ref.current:
            table_ref.current.content = build_table()
        page.update()

    def build_table() -> ft.Control:
        """Build the data table with checkbox selection and action popup menu."""
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
            report_id = report.get('report_id', report.get('id'))
            is_selected = report_id in state["selected_ids"]

            cells = []

            # Checkbox cell FIRST (for selection) - admin only
            if is_admin:
                cells.append(
                    ft.DataCell(
                        ft.Checkbox(
                            value=is_selected,
                            on_change=lambda e, rid=report_id: toggle_select_report(rid, e.control.value),
                        )
                    )
                )

            # Action cell (popup menu)
            if is_deleted:
                # For deleted reports: Restore and Permanent Delete options (admin only)
                if is_admin:
                    action_cell = ft.DataCell(
                        ft.PopupMenuButton(
                            icon=ft.Icons.MORE_VERT,
                            icon_color=colors["text_muted"],
                            icon_size=20,
                            tooltip="Actions",
                            items=[
                                ft.PopupMenuItem(
                                    icon=ft.Icons.RESTORE,
                                    text="Restore",
                                    on_click=lambda e, r=report: handle_restore_report(r),
                                ),
                                ft.PopupMenuItem(
                                    icon=ft.Icons.DELETE_FOREVER,
                                    text="Delete Permanently",
                                    on_click=lambda e, r=report: handle_hard_delete_report(r),
                                ),
                            ],
                        )
                    )
                else:
                    action_cell = ft.DataCell(ft.Container(width=40))
            else:
                # For active reports: Edit, History, Delete options
                # Check if current user can edit this report
                current_username = app_state.current_user.get('username', '')
                report_creator = report.get('created_by', '')
                can_edit = is_admin or (current_username == report_creator)

                menu_items = []

                # Only show Edit if user can edit (admin or own report)
                if can_edit:
                    menu_items.append(
                        ft.PopupMenuItem(
                            icon=ft.Icons.EDIT,
                            text="Edit",
                            on_click=lambda e, r=report: handle_row_click(r),
                        )
                    )

                # History is always visible
                menu_items.append(
                    ft.PopupMenuItem(
                        icon=ft.Icons.HISTORY,
                        text="History",
                        on_click=lambda e, r=report: handle_version_history(r),
                    )
                )

                # Delete is admin only
                if is_admin:
                    menu_items.append(
                        ft.PopupMenuItem(
                            icon=ft.Icons.DELETE_OUTLINE,
                            text="Delete",
                            on_click=lambda e, r=report: handle_delete_report(r),
                        )
                    )

                action_cell = ft.DataCell(
                    ft.PopupMenuButton(
                        icon=ft.Icons.MORE_VERT,
                        icon_color=colors["primary"] if can_edit else colors["text_secondary"],
                        icon_size=20,
                        tooltip="Actions",
                        items=menu_items,
                    )
                )

            cells.append(action_cell)

            # Data cells
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
                            size=11,
                            color=cell_color,
                            overflow=ft.TextOverflow.ELLIPSIS,
                            style=ft.TextStyle(decoration=ft.TextDecoration.LINE_THROUGH) if is_deleted else None,
                        ),
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

        # Build columns
        columns = []

        # Select All checkbox column (admin only)
        if is_admin:
            all_ids = {r.get('report_id', r.get('id')) for r in state["reports_data"]}
            all_selected = state["selected_ids"] == all_ids and all_ids
            some_selected = bool(state["selected_ids"] & all_ids) and not all_selected

            columns.append(
                ft.DataColumn(
                    ft.Checkbox(
                        ref=select_all_ref,
                        value=all_selected,
                        tristate=True if some_selected else False,
                        on_change=toggle_select_all,
                    ),
                )
            )

        # Actions column
        columns.append(
            ft.DataColumn(
                ft.Text(
                    "",
                    weight=ft.FontWeight.BOLD,
                    size=11,
                    color=colors["text_primary"],
                ),
            )
        )

        # Data columns
        columns.extend([
            ft.DataColumn(
                ft.Text(
                    col['header'],
                    weight=ft.FontWeight.BOLD,
                    size=11,
                    color=colors["text_primary"],
                ),
            )
            for col in REPORT_COLUMNS
        ])

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
                    report_id
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
                    report_id
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

    def handle_bulk_soft_delete(e):
        """Handle bulk soft delete of selected reports."""
        selected_count = len(state["selected_ids"])
        if selected_count == 0:
            return

        def confirm_bulk_delete(e):
            bulk_delete_dialog.open = False
            page.update()

            success_count = 0
            fail_count = 0

            for report_id in state["selected_ids"]:
                try:
                    success, _ = app_state.report_service.delete_report(report_id)
                    if success:
                        success_count += 1
                    else:
                        fail_count += 1
                except:
                    fail_count += 1

            if success_count > 0:
                show_success(page, f"Successfully deleted {success_count} report(s)")
            if fail_count > 0:
                show_error(page, f"Failed to delete {fail_count} report(s)")

            state["selected_ids"].clear()
            page.run_task(load_reports)

        def cancel_bulk_delete(e):
            bulk_delete_dialog.open = False
            page.update()

        bulk_delete_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.DELETE_OUTLINE, color=colors["warning"], size=24),
                    ft.Text("Bulk Delete Reports", weight=ft.FontWeight.BOLD),
                ],
                spacing=8,
            ),
            content=ft.Column(
                controls=[
                    ft.Text(
                        f"Are you sure you want to delete {selected_count} selected report(s)?",
                        size=14,
                    ),
                    ft.Text(
                        "This is a soft delete - reports can be restored later.",
                        size=12,
                        color=colors["text_secondary"],
                        italic=True,
                    ),
                ],
                spacing=8,
                tight=True,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=cancel_bulk_delete),
                ft.ElevatedButton(
                    "Delete Selected",
                    icon=ft.Icons.DELETE_OUTLINE,
                    bgcolor=colors["warning"],
                    color=ft.Colors.WHITE,
                    on_click=confirm_bulk_delete,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.overlay.append(bulk_delete_dialog)
        bulk_delete_dialog.open = True
        page.update()

    def handle_bulk_hard_delete(e):
        """Handle bulk permanent delete of selected reports."""
        selected_count = len(state["selected_ids"])
        if selected_count == 0:
            return

        confirm_text_ref = ft.Ref[ft.TextField]()

        def confirm_bulk_hard_delete(e):
            # Require typing "DELETE" to confirm
            if confirm_text_ref.current.value != "DELETE":
                show_error(page, "Please type DELETE to confirm permanent deletion")
                return

            bulk_hard_delete_dialog.open = False
            page.update()

            success_count = 0
            fail_count = 0

            for report_id in state["selected_ids"]:
                try:
                    success, _ = app_state.report_service.hard_delete_report(
                        report_id,
                        "Bulk permanent deletion"
                    )
                    if success:
                        success_count += 1
                    else:
                        fail_count += 1
                except:
                    fail_count += 1

            if success_count > 0:
                show_success(page, f"Permanently deleted {success_count} report(s)")
            if fail_count > 0:
                show_error(page, f"Failed to permanently delete {fail_count} report(s)")

            state["selected_ids"].clear()
            page.run_task(load_reports)

        def cancel_bulk_hard_delete(e):
            bulk_hard_delete_dialog.open = False
            page.update()

        bulk_hard_delete_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.DELETE_FOREVER, color=colors["danger"], size=24),
                    ft.Text("Permanently Delete Reports", weight=ft.FontWeight.BOLD, color=colors["danger"]),
                ],
                spacing=8,
            ),
            content=ft.Column(
                controls=[
                    ft.Container(
                        content=ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.WARNING, color=colors["danger"], size=20),
                                ft.Text(
                                    "WARNING: This action cannot be undone!",
                                    size=14,
                                    color=colors["danger"],
                                    weight=ft.FontWeight.BOLD,
                                ),
                            ],
                            spacing=8,
                        ),
                        bgcolor=f"{colors['danger']}20",
                        padding=12,
                        border_radius=8,
                    ),
                    ft.Text(
                        f"You are about to permanently delete {selected_count} report(s).",
                        size=14,
                    ),
                    ft.Text(
                        "All associated data including version history will be lost forever.",
                        size=12,
                        color=colors["text_secondary"],
                    ),
                    ft.Container(height=8),
                    ft.Text(
                        "Type DELETE to confirm:",
                        size=12,
                        color=colors["text_secondary"],
                    ),
                    ft.TextField(
                        ref=confirm_text_ref,
                        hint_text="Type DELETE to confirm",
                        text_size=14,
                        border_color=colors["danger"],
                    ),
                ],
                spacing=8,
                tight=True,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=cancel_bulk_hard_delete),
                ft.ElevatedButton(
                    "Permanently Delete",
                    icon=ft.Icons.DELETE_FOREVER,
                    bgcolor=colors["danger"],
                    color=ft.Colors.WHITE,
                    on_click=confirm_bulk_hard_delete,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.overlay.append(bulk_hard_delete_dialog)
        bulk_hard_delete_dialog.open = True
        page.update()

    def handle_bulk_restore(e):
        """Handle bulk restore of selected deleted reports."""
        selected_count = len(state["selected_ids"])
        if selected_count == 0:
            return

        def confirm_bulk_restore(e):
            bulk_restore_dialog.open = False
            page.update()

            success_count = 0
            fail_count = 0

            for report_id in state["selected_ids"]:
                try:
                    success, _ = app_state.report_service.restore_report(report_id)
                    if success:
                        success_count += 1
                    else:
                        fail_count += 1
                except:
                    fail_count += 1

            if success_count > 0:
                show_success(page, f"Successfully restored {success_count} report(s)")
            if fail_count > 0:
                show_error(page, f"Failed to restore {fail_count} report(s)")

            state["selected_ids"].clear()
            page.run_task(load_reports)

        def cancel_bulk_restore(e):
            bulk_restore_dialog.open = False
            page.update()

        bulk_restore_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.RESTORE, color=colors["success"], size=24),
                    ft.Text("Restore Reports", weight=ft.FontWeight.BOLD),
                ],
                spacing=8,
            ),
            content=ft.Text(
                f"Are you sure you want to restore {selected_count} selected report(s)?\n\n"
                "This will make them visible and editable again."
            ),
            actions=[
                ft.TextButton("Cancel", on_click=cancel_bulk_restore),
                ft.ElevatedButton(
                    "Restore Selected",
                    icon=ft.Icons.RESTORE,
                    bgcolor=colors["success"],
                    color=ft.Colors.WHITE,
                    on_click=confirm_bulk_restore,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.overlay.append(bulk_restore_dialog)
        bulk_restore_dialog.open = True
        page.update()

    def handle_search(e):
        """Handle search."""
        state["search_term"] = search_ref.current.value if search_ref.current else ""
        state["current_page"] = 1
        page.run_task(load_reports)

    def handle_clear_filters(e):
        """Clear all filters."""
        state["search_term"] = ""
        state["current_page"] = 1
        state["show_deleted"] = False
        if search_ref.current:
            search_ref.current.value = ""
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
            width=350,
            height=40,
            text_size=13,
            content_padding=ft.padding.symmetric(horizontal=12, vertical=0),
            on_submit=handle_search,
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

    # Bulk actions bar (admin only, visible when items selected)
    bulk_actions_bar = ft.Container(
        ref=bulk_actions_ref,
        content=ft.Row(
            controls=[
                ft.Icon(ft.Icons.CHECK_BOX, color=colors["primary"], size=20),
                ft.Text(
                    ref=selection_count_ref,
                    value="0 selected",
                    size=13,
                    weight=ft.FontWeight.W_500,
                    color=colors["text_primary"],
                ),
                ft.Container(width=16),
                ft.ElevatedButton(
                    "Delete Selected",
                    icon=ft.Icons.DELETE_OUTLINE,
                    bgcolor=colors["warning"],
                    color=ft.Colors.WHITE,
                    on_click=handle_bulk_soft_delete,
                ),
                ft.ElevatedButton(
                    "Permanently Delete",
                    icon=ft.Icons.DELETE_FOREVER,
                    bgcolor=colors["danger"],
                    color=ft.Colors.WHITE,
                    on_click=handle_bulk_hard_delete,
                ),
                ft.ElevatedButton(
                    "Restore Selected",
                    icon=ft.Icons.RESTORE,
                    bgcolor=colors["success"],
                    color=ft.Colors.WHITE,
                    on_click=handle_bulk_restore,
                    visible=state["show_deleted"],  # Only show when viewing deleted
                ),
                ft.Container(expand=True),
                ft.TextButton(
                    "Clear Selection",
                    icon=ft.Icons.CLEAR,
                    on_click=lambda e: clear_selection(),
                ),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(horizontal=16, vertical=8),
        bgcolor=f"{colors['primary']}15",
        border_radius=8,
        visible=False,  # Hidden by default
    ) if is_admin else ft.Container()

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
            bulk_actions_bar,
            stats_row,
            ft.Container(height=8),
            ft.Container(
                content=ft.Stack(
                    controls=[
                        loading_container,
                        ft.Container(
                            content=ft.Column(
                                controls=[
                                    ft.Row(
                                        controls=[table_container],
                                        scroll=ft.ScrollMode.ALWAYS,
                                        expand=True,
                                    ),
                                ],
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
