"""
Approval Panel View for FIU Report Management System.
Admin-only view for managing report approval requests.
"""
import flet as ft
from components.searchable_dropdown import searchable_dropdown
import asyncio
from typing import Any, Dict, List
from datetime import datetime

from theme.theme_manager import theme_manager
from components.toast import show_success, show_error

# Field definitions for the report form
REPORT_FIELDS = [
    {'key': 'report_number', 'label': 'Report Number', 'readonly': True},
    {'key': 'sn', 'label': 'Serial Number', 'readonly': True},
    {'key': 'report_date', 'label': 'Report Date'},
    {'key': 'outgoing_letter_number', 'label': 'Outgoing Letter Number'},
    {'key': 'reported_entity_name', 'label': 'Reported Entity Name'},
    {'key': 'legal_entity_owner', 'label': 'Legal Entity Owner'},
    {'key': 'gender', 'label': 'Gender', 'type': 'dropdown', 'options': ['Male', 'Female', 'Other', 'N/A']},
    {'key': 'nationality', 'label': 'Nationality'},
    {'key': 'id_type', 'label': 'ID Type'},
    {'key': 'id_cr', 'label': 'ID/CR'},
    {'key': 'case_id', 'label': 'Case ID'},
    {'key': 'relationship', 'label': 'Relationship'},
    {'key': 'account_membership', 'label': 'Account/Membership'},
    {'key': 'branch_id', 'label': 'Branch ID'},
    {'key': 'cic', 'label': 'CIC'},
    {'key': 'first_reason_for_suspicion', 'label': 'First Reason for Suspicion'},
    {'key': 'second_reason_for_suspicion', 'label': 'Second Reason for Suspicion'},
    {'key': 'type_of_suspected_transaction', 'label': 'Type of Suspected Transaction'},
    {'key': 'arb_staff', 'label': 'ARB Staff'},
    {'key': 'total_transaction', 'label': 'Total Transaction'},
    {'key': 'report_classification', 'label': 'Report Classification'},
    {'key': 'report_source', 'label': 'Report Source'},
    {'key': 'reporting_entity', 'label': 'Reporting Entity'},
    {'key': 'reporter_initials', 'label': 'Reporter Initials'},
    {'key': 'sending_date', 'label': 'Sending Date'},
    {'key': 'original_copy_confirmation', 'label': 'Original Copy Confirmation'},
    {'key': 'fiu_number', 'label': 'FIU Number'},
    {'key': 'fiu_letter_receive_date', 'label': 'FIU Letter Receive Date'},
    {'key': 'fiu_feedback', 'label': 'FIU Feedback'},
    {'key': 'fiu_letter_number', 'label': 'FIU Letter Number'},
    {'key': 'fiu_date', 'label': 'FIU Date'},
]


def review_field_options(live_values, stored_value):
    """Option set for a constrained field on the review screen: the currently
    active values, plus the stored value if it isn't among them — so a review
    can NEVER drop or blank recorded data, even when the option set changed (or
    was seeded in a different language) after the report was written. Order
    preserved, duplicates and empties removed."""
    return list(dict.fromkeys(
        [v for v in (live_values or []) if v] + ([stored_value] if stored_value else [])))


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
    from i18n import t, get_language
    from i18n.fields import field_label
    _lang = get_language()
    _db = app_state.db_manager

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
                stats_ref.current.value = t("appr.showing", n=len(pending_approvals))
            else:
                stats_ref.current.value = t("appr.none")

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
                                    t("appr.pending"),
                                    size=11,
                                    color=ft.Colors.WHITE,
                                ),
                                bgcolor=colors["warning"],
                                border_radius=4,
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
                                t("appr.review"),
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
            ft.DataColumn(ft.Text(t("appr.col.report"), weight=ft.FontWeight.BOLD, size=12, color=colors["text_primary"])),
            ft.DataColumn(ft.Text(t("appr.col.entity"), weight=ft.FontWeight.BOLD, size=12, color=colors["text_primary"])),
            ft.DataColumn(ft.Text(t("appr.col.requested_by"), weight=ft.FontWeight.BOLD, size=12, color=colors["text_primary"])),
            ft.DataColumn(ft.Text(t("appr.col.requested_at"), weight=ft.FontWeight.BOLD, size=12, color=colors["text_primary"])),
            ft.DataColumn(ft.Text(t("appr.col.status"), weight=ft.FontWeight.BOLD, size=12, color=colors["text_primary"])),
            ft.DataColumn(ft.Text(t("appr.col.comment"), weight=ft.FontWeight.BOLD, size=12, color=colors["text_primary"])),
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
            border_radius=4,
        )

    def handle_review(approval: Dict, idx: int):
        """Handle review button click."""
        show_full_report_review_dialog(approval)

    def show_full_report_review_dialog(approval: Dict):
        """Show full report form with review options. Fields locked by default, unlocked only with Edit."""
        report_id = approval.get('report_id')
        report_data = {}
        field_refs = {}
        decision_ref = {"value": "approve"}
        is_edit_mode = {"value": False}
        comment_ref = ft.Ref[ft.TextField]()
        reassign_ref = ft.Ref[ft.Dropdown]()
        form_container_ref = ft.Ref[ft.Container]()
        loading_ref = ft.Ref[ft.Container]()
        save_btn_ref = ft.Ref[ft.ElevatedButton]()
        approve_btn_ref = ft.Ref[ft.ElevatedButton]()
        edit_mode_label_ref = ft.Ref[ft.Container]()
        pre_edit_snapshot_created = {"value": False}  # Track if we captured state before edit

        def load_report_data():
            """Load full report data."""
            nonlocal report_data
            try:
                if app_state.report_service:
                    report_data = app_state.report_service.get_report(report_id) or {}
                    build_form()
            except Exception as e:
                show_error(page, f"Failed to load report: {str(e)}")

        def build_form():
            """Build the form fields (all locked by default)."""
            if loading_ref.current:
                loading_ref.current.visible = False

            form_fields = []

            # Two-column layout for fields
            row_fields = []
            for field in REPORT_FIELDS:
                key = field['key']
                label = field_label(_db, field['key'], _lang, default=field['label'])
                always_readonly = field.get('readonly', False)  # SN and Report Number
                field_type = field.get('type', 'text')
                value = str(report_data.get(key, '') or '')

                # All fields start as readonly (locked)
                if field_type == 'dropdown':
                    # #9: a locked review must READ like every other field — a plain,
                    # readable value, never greyed-out or blank. So locked = a
                    # read-only text field showing the stored value; edit mode swaps
                    # to a constrained dropdown. Options come from the SAME source the
                    # form uses (not a hardcoded English list that silently blanks any
                    # value stored in another language/config), unioned with the stored
                    # value so a review can never drop recorded data.
                    live = (app_state.dropdown_service.get_active_dropdown_values(key)
                            if app_state.dropdown_service else [])
                    opts = review_field_options(live, value)
                    display = ft.TextField(
                        label=label, value=value, read_only=True, text_size=12,
                        width=300, bgcolor=colors["bg_tertiary"],
                    )
                    editor = searchable_dropdown(
                        label=label,
                        value=value if value in opts else '',
                        options=[ft.dropdown.Option(o) for o in opts],
                        text_size=12, width=300,
                    )
                    editor.visible = False   # locked by default; shown in edit mode
                    control = ft.Column(controls=[display, editor], spacing=0, tight=True, width=300)
                    field_refs[key] = {'control': control, 'display': display, 'editor': editor,
                                       'always_readonly': always_readonly, 'type': 'dropdown'}
                else:
                    control = ft.TextField(
                        label=label,
                        value=value,
                        read_only=True,  # Start readonly
                        text_size=12,
                        width=300,
                        bgcolor=colors["bg_tertiary"],
                    )
                    field_refs[key] = {'control': control, 'always_readonly': always_readonly, 'type': field_type}

                row_fields.append(control)

                # Create row every 2 fields
                if len(row_fields) == 2:
                    form_fields.append(
                        ft.Row(controls=row_fields, spacing=16)
                    )
                    row_fields = []

            # Add remaining field if odd number
            if row_fields:
                form_fields.append(
                    ft.Row(controls=row_fields, spacing=16)
                )

            if form_container_ref.current:
                form_container_ref.current.content = ft.Column(
                    controls=form_fields,
                    spacing=12,
                    scroll=ft.ScrollMode.AUTO,
                )
                page.update()

        def toggle_edit_mode(enable: bool):
            """Enable or disable edit mode for form fields."""
            is_edit_mode["value"] = enable

            # Create version snapshot BEFORE editing (to capture the pre-edit state for diff)
            if enable and not pre_edit_snapshot_created["value"] and app_state.version_service:
                app_state.version_service.create_version_snapshot(
                    report_id,
                    f"State before admin review edit"
                )
                pre_edit_snapshot_created["value"] = True

            for key, field_info in field_refs.items():
                control = field_info['control']
                always_readonly = field_info['always_readonly']
                field_type = field_info['type']

                if always_readonly:
                    # SN and Report Number always stay readonly
                    continue

                if field_type == 'dropdown':
                    # swap readable display <-> constrained editor
                    field_info['display'].visible = not enable
                    field_info['editor'].visible = enable
                else:
                    control.read_only = not enable
                    control.bgcolor = None if enable else colors["bg_tertiary"]

            # Show/hide save button, approve button, and edit mode indicator
            if save_btn_ref.current:
                save_btn_ref.current.visible = enable
            if approve_btn_ref.current:
                approve_btn_ref.current.visible = enable
            if edit_mode_label_ref.current:
                edit_mode_label_ref.current.visible = enable

            page.update()

        def get_form_data() -> Dict:
            """Get current form data."""
            data = {}
            for key, field_info in field_refs.items():
                if field_info['type'] == 'dropdown':
                    # the editor holds the (constrained) value; the display is read-only
                    data[key] = field_info['editor'].value or ''
                else:
                    data[key] = field_info['control'].value or ''
            return data

        def save_changes(e):
            """Save any edits made to the report."""
            if not is_edit_mode["value"]:
                return

            form_data = get_form_data()
            try:
                success, message = app_state.report_service.update_report(report_id, form_data)
                if success:
                    show_success(page, "Report updated successfully")
                    # Create version snapshot
                    if app_state.version_service:
                        app_state.version_service.create_version_snapshot(
                            report_id,
                            f"Modified by admin during approval review"
                        )
                else:
                    show_error(page, message)
            except Exception as ex:
                show_error(page, f"Failed to save changes: {str(ex)}")

        def approve_after_edit(e):
            """Approve the report after editing."""
            # First save any pending changes
            if is_edit_mode["value"]:
                form_data = get_form_data()
                try:
                    success, message = app_state.report_service.update_report(report_id, form_data)
                    if success:
                        # Create version snapshot
                        if app_state.version_service:
                            app_state.version_service.create_version_snapshot(
                                report_id,
                                f"Modified by admin during approval review"
                            )
                    else:
                        show_error(page, f"Failed to save changes: {message}")
                        return
                except Exception as ex:
                    show_error(page, f"Failed to save changes: {str(ex)}")
                    return

            # Now approve the report
            review_dialog.open = False
            page.update()
            comment = comment_ref.current.value.strip() if comment_ref.current else ""
            process_decision(approval, "approve", comment or "Approved after admin edit")

        def submit_decision(e):
            """Submit the approval decision."""
            comment = comment_ref.current.value.strip() if comment_ref.current else ""
            decision = decision_ref["value"]

            # Handle Edit action - just enable edit mode, don't close dialog
            if decision == "edit":
                toggle_edit_mode(True)
                show_success(page, t("appr.edit_enabled"))
                return

            # Validate comment for reject/rework
            if decision in ["reject", "rework"] and not comment:
                show_error(page, "Please provide feedback for rejection or rework request.")
                return

            reassign_to = None
            if decision == "rework" and reassign_ref.current and reassign_ref.current.value:
                reassign_to = reassign_ref.current.value

            review_dialog.open = False
            page.update()
            process_decision(approval, decision, comment, reassign_to)

        def cancel_review(e):
            review_dialog.open = False
            page.update()

        def on_decision_change(e):
            decision_ref["value"] = e.control.value

        # Build the dialog content
        review_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.RATE_REVIEW, color=colors["primary"]),
                    ft.Text(f"Review Report #{approval.get('report_number', '')}", weight=ft.FontWeight.BOLD),
                ],
                spacing=8,
            ),
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        # Request info banner
                        ft.Container(
                            content=ft.Row(
                                controls=[
                                    ft.Icon(ft.Icons.INFO_OUTLINE, color=colors["info"], size=20),
                                    ft.Text(
                                        f"Requested by {approval.get('requested_by', '')} on {approval.get('requested_at', '')[:16] if approval.get('requested_at') else ''}",
                                        size=12,
                                        color=colors["text_secondary"],
                                    ),
                                    ft.Container(expand=True),
                                    ft.Container(
                                        content=ft.Text("Pending Review", size=11, color=ft.Colors.WHITE),
                                        bgcolor=colors["warning"],
                                        border_radius=4,
                                        padding=ft.padding.symmetric(horizontal=8, vertical=2),
                                    ),
                                ],
                                spacing=8,
                            ),
                            bgcolor=colors["bg_tertiary"],
                            border_radius=4,
                            padding=12,
                        ),

                        # Request comment if any
                        ft.Container(
                            content=ft.Row(
                                controls=[
                                    ft.Icon(ft.Icons.COMMENT, color=colors["text_secondary"], size=16),
                                    ft.Text(
                                        f"Request Comment: {approval.get('comment', 'No comment provided')}",
                                        size=12,
                                        color=colors["text_secondary"],
                                        italic=True,
                                    ),
                                ],
                                spacing=8,
                            ),
                            padding=ft.padding.only(top=8, bottom=8),
                        ) if approval.get('comment') else ft.Container(),

                        ft.Divider(height=1, color=colors["border"]),

                        # Form section header
                        ft.Row(
                            controls=[
                                ft.Text("Report Details", size=14, weight=ft.FontWeight.BOLD, color=colors["text_primary"]),
                                ft.Text("(Read-only - select 'Edit' below to modify)", size=11, color=colors["text_secondary"]),
                                ft.Container(expand=True),
                                # Edit mode indicator (hidden by default)
                                ft.Container(
                                    ref=edit_mode_label_ref,
                                    content=ft.Row(
                                        controls=[
                                            ft.Icon(ft.Icons.EDIT, color=colors["warning"], size=16),
                                            ft.Text("EDIT MODE", size=11, color=colors["warning"], weight=ft.FontWeight.BOLD),
                                        ],
                                        spacing=4,
                                    ),
                                    visible=False,
                                ),
                                # Save button (hidden by default, shown in edit mode)
                                ft.ElevatedButton(
                                    ref=save_btn_ref,
                                    text=t("appr.save_changes"),
                                    icon=ft.Icons.SAVE,
                                    bgcolor=colors["primary"],
                                    color=ft.Colors.WHITE,
                                    on_click=save_changes,
                                    visible=False,
                                ),
                                # Approve button (hidden by default, shown in edit mode)
                                ft.ElevatedButton(
                                    ref=approve_btn_ref,
                                    text=t("appr.approve_report"),
                                    icon=ft.Icons.CHECK_CIRCLE,
                                    bgcolor=colors["success"],
                                    color=ft.Colors.WHITE,
                                    on_click=approve_after_edit,
                                    visible=False,
                                ),
                            ],
                            spacing=8,
                        ),

                        # Loading indicator
                        ft.Container(
                            ref=loading_ref,
                            content=ft.Row(
                                controls=[
                                    ft.ProgressRing(width=20, height=20),
                                    ft.Text(t("appr.loading"), size=12),
                                ],
                                spacing=8,
                            ),
                            padding=20,
                            visible=True,
                        ),

                        # Form container (populated after load)
                        # #10: a review needs room — 31 fields in a 280px box is
                        # unreviewable; give it a tall viewport (form scrolls inside).
                        ft.Container(
                            ref=form_container_ref,
                            content=ft.Text("Loading..."),
                            height=480,
                        ),

                        ft.Divider(height=1, color=colors["border"]),

                        # Decision section
                        ft.Text(t("appr.your_decision"), size=14, weight=ft.FontWeight.BOLD, color=colors["text_primary"]),
                        ft.RadioGroup(
                            value="approve",
                            on_change=on_decision_change,
                            content=ft.Column(
                                controls=[
                                    ft.Radio(value="approve", label=t("appr.opt.approve")),
                                    ft.Radio(value="rework", label=t("appr.opt.rework")),
                                    ft.Radio(value="reject", label=t("appr.opt.reject")),
                                    ft.Radio(value="edit", label=t("appr.opt.edit")),
                                ],
                                spacing=4,
                            ),
                        ),

                        ft.TextField(
                            ref=comment_ref,
                            label=t("appr.comment"),
                            hint_text=t("appr.comment_hint"),
                            multiline=True,
                            min_lines=2,
                            max_lines=3,
                            text_size=12,
                        ),

                        # Rework reassignment (R36): optionally hand off to a
                        # different active agent. Only relevant for Rework.
                        searchable_dropdown(
                            ref=reassign_ref,
                            label=t("appr.reassign"),
                            hint_text=t("appr.keep_agent"),
                            options=[ft.dropdown.Option(key="", text=t("appr.keep_agent_opt"))] + [
                                ft.dropdown.Option(key=a['username'], text=a['full_name'] or a['username'])
                                for a in (app_state.approval_service.get_active_agents()
                                          if app_state.approval_service else [])
                            ],
                            value="",
                            text_size=12,
                        ),
                    ],
                    spacing=10,
                    scroll=ft.ScrollMode.AUTO,
                ),
                width=920,
                height=760,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=cancel_review),
                ft.ElevatedButton(
                    "Submit Decision",
                    icon=ft.Icons.GAVEL,
                    bgcolor=colors["success"],
                    color=ft.Colors.WHITE,
                    on_click=submit_decision,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        page.overlay.append(review_dialog)
        review_dialog.open = True
        page.update()

        # Load report data after dialog is shown
        load_report_data()

    def process_decision(approval: Dict, decision: str, comment: str, reassign_to: str = None):
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
                    approval_id, comment, request_rework, reassign_to=reassign_to
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
                border_radius=4,
                bgcolor=colors["card_bg"],
            ),
        ],
        spacing=0,
        expand=True,
    )
