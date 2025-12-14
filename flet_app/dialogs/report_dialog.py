"""
Report Dialog for FIU Report Management System.
Comprehensive 35-field tabbed form for creating and editing reports.
"""
import flet as ft
from typing import Optional, Any, Callable
from datetime import datetime
import re
import asyncio

from theme.theme_manager import theme_manager
from components.form_fields import (
    create_text_field,
    create_dropdown,
    create_date_picker,
    create_checkbox,
    create_form_section,
)


def show_report_dialog(
    page: ft.Page,
    app_state: Any,
    report_data: Optional[dict] = None,
    on_save: Optional[Callable[[], None]] = None,
):
    """
    Show the report dialog.

    Args:
        page: Flet page object
        app_state: Application state with services
        report_data: Existing report data for editing (None for new report)
        on_save: Callback when report is saved
    """
    colors = theme_manager.get_colors()
    is_edit_mode = report_data is not None

    # Services
    report_service = app_state.report_service
    dropdown_service = app_state.dropdown_service
    validation_service = app_state.validation_service
    report_number_service = app_state.report_number_service
    logging_service = app_state.logging_service
    approval_service = app_state.approval_service
    version_service = app_state.version_service
    current_user = app_state.current_user

    # State
    reservation_info = {"value": None}

    # Load dropdown values
    genders = dropdown_service.get_active_dropdown_values('gender') if dropdown_service else []
    nationalities = dropdown_service.get_active_dropdown_values('nationality') if dropdown_service else []
    second_reasons = dropdown_service.get_active_dropdown_values('second_reason_for_suspicion') if dropdown_service else []
    transaction_types = dropdown_service.get_active_dropdown_values('type_of_suspected_transaction') if dropdown_service else []
    arb_staff_values = dropdown_service.get_active_dropdown_values('arb_staff') if dropdown_service else []
    classifications = dropdown_service.get_active_dropdown_values('report_classification') if dropdown_service else []
    report_sources = dropdown_service.get_active_dropdown_values('report_source') if dropdown_service else []
    reporting_entities = dropdown_service.get_active_dropdown_values('reporting_entity') if dropdown_service else []
    fiu_feedbacks = dropdown_service.get_active_dropdown_values('fiu_feedback') if dropdown_service else []

    # Form field references
    sn_ref = ft.Ref[ft.TextField]()
    report_number_ref = ft.Ref[ft.TextField]()
    report_date_ref = ft.Ref[ft.TextField]()
    entity_name_ref = ft.Ref[ft.TextField]()
    legal_owner_ref = ft.Ref[ft.Checkbox]()
    gender_ref = ft.Ref[ft.Dropdown]()
    nationality_ref = ft.Ref[ft.Dropdown]()
    id_cr_ref = ft.Ref[ft.TextField]()
    id_type_checkbox_ref = ft.Ref[ft.Checkbox]()
    id_type_display_ref = ft.Ref[ft.TextField]()
    account_ref = ft.Ref[ft.TextField]()
    acc_membership_ref = ft.Ref[ft.Checkbox]()
    relationship_ref = ft.Ref[ft.TextField]()
    branch_ref = ft.Ref[ft.TextField]()
    cic_ref = ft.Ref[ft.TextField]()
    first_reason_ref = ft.Ref[ft.TextField]()
    second_reason_ref = ft.Ref[ft.Dropdown]()
    transaction_type_ref = ft.Ref[ft.Dropdown]()
    arb_staff_ref = ft.Ref[ft.Dropdown]()
    total_transaction_ref = ft.Ref[ft.TextField]()
    classification_ref = ft.Ref[ft.Dropdown]()
    report_source_ref = ft.Ref[ft.Dropdown]()
    reporting_entity_ref = ft.Ref[ft.Dropdown]()
    reporter_initials_ref = ft.Ref[ft.TextField]()
    sending_date_ref = ft.Ref[ft.TextField]()
    fiu_number_ref = ft.Ref[ft.TextField]()
    fiu_receive_date_ref = ft.Ref[ft.TextField]()
    fiu_feedback_ref = ft.Ref[ft.Dropdown]()
    fiu_letter_number_ref = ft.Ref[ft.TextField]()

    def update_id_type_display(e):
        """Update ID type display based on checkbox."""
        if id_type_display_ref.current:
            id_type_display_ref.current.value = "CR" if id_type_checkbox_ref.current.value else "ID"
            page.update()

    def update_relationship_display(e):
        """Update relationship display based on checkbox."""
        if relationship_ref.current:
            relationship_ref.current.value = "Membership" if acc_membership_ref.current.value else "Current Account"
            page.update()

    def format_cic(e):
        """Format CIC to 16 digits."""
        if cic_ref.current:
            cic_text = cic_ref.current.value.replace(' ', '').replace('-', '')
            if cic_text and cic_text.isdigit() and len(cic_text) > 16:
                cic_ref.current.value = cic_text[:16]
                page.update()

    def finalize_cic(e):
        """Finalize CIC formatting on blur."""
        if cic_ref.current:
            cic_text = cic_ref.current.value.replace(' ', '').replace('-', '')
            if cic_text and cic_text.isdigit():
                cic_ref.current.value = cic_text.zfill(16)
                page.update()

    # Live validation functions
    def validate_sn_live(e):
        """Live validation for Serial Number."""
        if sn_ref.current:
            value = sn_ref.current.value.strip() if sn_ref.current.value else ""
            if value and not value.isdigit():
                sn_ref.current.error_text = "Must be numeric"
            else:
                sn_ref.current.error_text = None
            page.update()

    def validate_report_number_live(e):
        """Live validation for Report Number."""
        if report_number_ref.current:
            value = report_number_ref.current.value.strip() if report_number_ref.current.value else ""
            if value:
                if not re.match(r'^\d{4}/\d{2}/\d{3}$', value):
                    report_number_ref.current.error_text = "Format: YYYY/MM/NNN"
                else:
                    report_number_ref.current.error_text = None
            else:
                report_number_ref.current.error_text = None
            page.update()

    def validate_entity_name_live(e):
        """Live validation for Reported Entity Name."""
        if entity_name_ref.current:
            value = entity_name_ref.current.value.strip() if entity_name_ref.current.value else ""
            # Don't show error while empty (will be checked on submit)
            entity_name_ref.current.error_text = None
            page.update()

    def validate_cic_live(e):
        """Live validation for CIC (after format_cic)."""
        format_cic(e)  # Apply formatting first
        if cic_ref.current:
            cic_text = cic_ref.current.value.replace(' ', '').replace('-', '') if cic_ref.current.value else ""
            if cic_text:
                if not cic_text.isdigit():
                    cic_ref.current.error_text = "Must contain only digits"
                elif len(cic_text) > 16:
                    cic_ref.current.error_text = "Must be exactly 16 digits"
                else:
                    cic_ref.current.error_text = None
            else:
                cic_ref.current.error_text = None
            page.update()

    def validate_initials_live(e):
        """Live validation for Reporter Initials."""
        if reporter_initials_ref.current:
            value = reporter_initials_ref.current.value.strip() if reporter_initials_ref.current.value else ""
            if value:
                # Auto-uppercase
                if value != value.upper():
                    reporter_initials_ref.current.value = value.upper()
                    value = value.upper()
                if not re.match(r'^[A-Z]{0,2}$', value):
                    reporter_initials_ref.current.error_text = "Must be 2 uppercase letters"
                elif len(value) == 2 and not re.match(r'^[A-Z]{2}$', value):
                    reporter_initials_ref.current.error_text = "Must be 2 uppercase letters"
                else:
                    reporter_initials_ref.current.error_text = None
            else:
                reporter_initials_ref.current.error_text = None
            page.update()

    def validate_form() -> tuple[bool, list]:
        """Validate form data. Returns (is_valid, errors)."""
        errors = []

        # Required fields
        sn = sn_ref.current.value.strip() if sn_ref.current else ""
        if not sn:
            errors.append("Serial Number is required")
        elif not sn.isdigit():
            errors.append("Serial Number must be a number")

        report_num = report_number_ref.current.value.strip() if report_number_ref.current else ""
        if not report_num:
            errors.append("Report Number is required")
        elif not re.match(r'^\d{4}/\d{2}/\d{3}$', report_num):
            errors.append("Report Number must be in format YYYY/MM/NNN (e.g., 2025/11/001)")

        entity = entity_name_ref.current.value.strip() if entity_name_ref.current else ""
        if not entity:
            errors.append("Reported Entity Name is required")

        # CIC validation
        cic = cic_ref.current.value.strip() if cic_ref.current else ""
        if cic:
            cic_cleaned = cic.replace(' ', '').replace('-', '')
            if not cic_cleaned.isdigit():
                errors.append("CIC must contain only digits")
            elif len(cic_cleaned) != 16:
                errors.append("CIC must be exactly 16 digits")

        # Reporter initials validation
        initials = reporter_initials_ref.current.value.strip() if reporter_initials_ref.current else ""
        if initials and not re.match(r'^[A-Z]{2}$', initials):
            errors.append("Reporter Initials must be 2 uppercase letters")

        return len(errors) == 0, errors

    def get_form_data() -> dict:
        """Get form data as dictionary."""
        def get_value(ref, default=""):
            return ref.current.value.strip() if ref.current and ref.current.value else default

        def get_dropdown_value(ref):
            return ref.current.value if ref.current and ref.current.value else None

        def get_checkbox_value(ref):
            return 1 if ref.current and ref.current.value else 0

        return {
            'sn': int(get_value(sn_ref, "0")),
            'report_number': get_value(report_number_ref),
            'report_date': get_value(report_date_ref),
            'reported_entity_name': get_value(entity_name_ref),
            'legal_entity_owner_checkbox': get_checkbox_value(legal_owner_ref),
            'gender': get_dropdown_value(gender_ref),
            'nationality': get_dropdown_value(nationality_ref),
            'id_cr': get_value(id_cr_ref) or None,
            'id_type': get_value(id_type_display_ref, "ID"),
            'account_membership': get_value(account_ref) or None,
            'acc_membership_checkbox': get_checkbox_value(acc_membership_ref),
            'relationship': get_value(relationship_ref, "Current Account"),
            'branch_id': get_value(branch_ref) or None,
            'cic': get_value(cic_ref) or None,
            'first_reason_for_suspicion': get_value(first_reason_ref) or None,
            'second_reason_for_suspicion': get_dropdown_value(second_reason_ref),
            'type_of_suspected_transaction': get_dropdown_value(transaction_type_ref),
            'arb_staff': get_dropdown_value(arb_staff_ref),
            'total_transaction': get_value(total_transaction_ref) or None,
            'report_classification': get_dropdown_value(classification_ref),
            'report_source': get_dropdown_value(report_source_ref),
            'reporting_entity': get_dropdown_value(reporting_entity_ref),
            'reporter_initials': get_value(reporter_initials_ref) or None,
            'sending_date': get_value(sending_date_ref) or None,
            'fiu_number': get_value(fiu_number_ref) or None,
            'fiu_letter_receive_date': get_value(fiu_receive_date_ref) or None,
            'fiu_feedback': get_dropdown_value(fiu_feedback_ref),
            'fiu_letter_number': get_value(fiu_letter_number_ref) or None,
        }

    def save_report(e):
        """Save the report."""
        is_valid, errors = validate_form()
        if not is_valid:
            show_error_dialog("\n".join(f"• {err}" for err in errors))
            return

        form_data = get_form_data()

        try:
            if is_edit_mode:
                report_id = report_data.get('report_id') or report_data.get('id')
                if not report_id:
                    show_error_dialog("Report ID not found")
                    return

                # Create version snapshot before updating
                if version_service:
                    version_service.create_version_snapshot(
                        report_id,
                        f"Modified by {current_user['username']}"
                    )

                success, message = report_service.update_report(report_id, form_data)
            else:
                success, report_id, message = report_service.create_report(form_data)

            if success:
                # Mark reservation as used
                if not is_edit_mode and reservation_info["value"] and report_number_service:
                    try:
                        report_number_service.mark_reservation_used(
                            reservation_info["value"]['report_number'],
                            current_user['username']
                        )
                        reservation_info["value"] = None
                    except Exception as ex:
                        logging_service.error(f"Error marking reservation as used: {ex}")

                show_success_dialog(message)
                dialog.open = False
                page.update()
                if on_save:
                    on_save()
            else:
                show_error_dialog(message)

        except Exception as ex:
            show_error_dialog(f"Failed to save report: {str(ex)}")
            logging_service.error(f"Report save error: {ex}", exc_info=True)

    def submit_for_approval(e):
        """Submit report for approval."""
        if not is_edit_mode or not report_data:
            return

        report_id = report_data.get('report_id') or report_data.get('id')
        if not report_id:
            show_error_dialog("Report ID not found")
            return

        def confirm_submit(e):
            confirm_dialog.open = False
            page.update()

            try:
                if not approval_service:
                    show_error_dialog("Approval service not available")
                    return

                success, approval_id, message = approval_service.request_approval(
                    report_id,
                    f"Submitted by {current_user['username']}"
                )

                if success:
                    show_success_dialog(message)
                    dialog.open = False
                    page.update()
                    if on_save:
                        on_save()
                else:
                    show_error_dialog(message)

            except Exception as ex:
                show_error_dialog(f"Failed to submit for approval: {str(ex)}")

        def cancel_submit(e):
            confirm_dialog.open = False
            page.update()

        confirm_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Submit for Approval"),
            content=ft.Text(
                "Are you sure you want to submit this report for admin approval?\n\n"
                "Once submitted, you won't be able to edit it until an admin reviews it."
            ),
            actions=[
                ft.TextButton("Cancel", on_click=cancel_submit),
                ft.ElevatedButton("Submit", on_click=confirm_submit),
            ],
        )
        page.overlay.append(confirm_dialog)
        confirm_dialog.open = True
        page.update()

    def show_error_dialog(message: str):
        """Show error dialog."""
        error_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Validation Error", color=colors["danger"]),
            content=ft.Text(message),
            actions=[
                ft.TextButton("OK", on_click=lambda e: close_error_dialog()),
            ],
        )

        def close_error_dialog():
            error_dialog.open = False
            page.update()

        page.overlay.append(error_dialog)
        error_dialog.open = True
        page.update()

    def show_success_dialog(message: str):
        """Show success dialog."""
        success_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Success", color=colors["success"]),
            content=ft.Text(message),
            actions=[
                ft.TextButton("OK", on_click=lambda e: close_success_dialog()),
            ],
        )

        def close_success_dialog():
            success_dialog.open = False
            page.update()

        page.overlay.append(success_dialog)
        success_dialog.open = True
        page.update()

    def close_dialog(e):
        """Close dialog and cancel reservation if needed."""
        if not is_edit_mode and reservation_info["value"] and report_number_service:
            try:
                report_number_service.cancel_reservation(
                    reservation_info["value"]['report_number'],
                    current_user['username']
                )
            except Exception as ex:
                logging_service.error(f"Error cancelling reservation: {ex}")

        dialog.open = False
        page.update()

    def view_history(e):
        """View version history."""
        if not is_edit_mode or not report_data:
            return

        report_id = report_data.get('report_id') or report_data.get('id')
        if not report_id:
            show_error_dialog("Report ID not found")
            return

        # Import and show version history dialog
        from dialogs.version_history_dialog import show_version_history_dialog
        show_version_history_dialog(page, app_state, report_id, on_restore=lambda: load_report_data())

    def load_report_data():
        """Load existing report data into form fields."""
        if not report_data:
            return

        # Basic Info
        if sn_ref.current:
            sn_ref.current.value = str(report_data.get('sn', ''))
            sn_ref.current.read_only = True
        if report_number_ref.current:
            report_number_ref.current.value = report_data.get('report_number', '')
            report_number_ref.current.read_only = True
        if report_date_ref.current:
            report_date_ref.current.value = report_data.get('report_date', '')

        # Entity Details
        if entity_name_ref.current:
            entity_name_ref.current.value = report_data.get('reported_entity_name', '')
        if legal_owner_ref.current:
            legal_owner_ref.current.value = bool(report_data.get('legal_entity_owner_checkbox', 0))
        if gender_ref.current:
            gender_ref.current.value = report_data.get('gender', '')
        if nationality_ref.current:
            nationality_ref.current.value = report_data.get('nationality', '')
        if id_cr_ref.current:
            id_cr_ref.current.value = report_data.get('id_cr', '')
        if id_type_checkbox_ref.current:
            id_type_checkbox_ref.current.value = report_data.get('id_type', 'ID') == 'CR'
        if id_type_display_ref.current:
            id_type_display_ref.current.value = report_data.get('id_type', 'ID')
        if account_ref.current:
            account_ref.current.value = report_data.get('account_membership', '')
        if acc_membership_ref.current:
            acc_membership_ref.current.value = bool(report_data.get('acc_membership_checkbox', 0))
        if relationship_ref.current:
            relationship_ref.current.value = report_data.get('relationship', 'Current Account')
        if branch_ref.current:
            branch_ref.current.value = report_data.get('branch_id', '')
        if cic_ref.current:
            cic = report_data.get('cic', '')
            if cic:
                cic = cic.replace(' ', '').replace('-', '').zfill(16)
            cic_ref.current.value = cic

        # Suspicion Details
        if first_reason_ref.current:
            first_reason_ref.current.value = report_data.get('first_reason_for_suspicion', '')
        if second_reason_ref.current:
            second_reason_ref.current.value = report_data.get('second_reason_for_suspicion', '')
        if transaction_type_ref.current:
            transaction_type_ref.current.value = report_data.get('type_of_suspected_transaction', '')
        if arb_staff_ref.current:
            arb_staff_ref.current.value = report_data.get('arb_staff', '')
        if total_transaction_ref.current:
            total_transaction_ref.current.value = report_data.get('total_transaction', '')

        # Classification & Source
        if classification_ref.current:
            classification_ref.current.value = report_data.get('report_classification', '')
        if report_source_ref.current:
            report_source_ref.current.value = report_data.get('report_source', '')
        if reporting_entity_ref.current:
            reporting_entity_ref.current.value = report_data.get('reporting_entity', '')
        if reporter_initials_ref.current:
            reporter_initials_ref.current.value = report_data.get('reporter_initials', '')
        if sending_date_ref.current:
            sending_date_ref.current.value = report_data.get('sending_date', '')

        # FIU Details
        if fiu_number_ref.current:
            fiu_number_ref.current.value = report_data.get('fiu_number', '')
        if fiu_receive_date_ref.current:
            fiu_receive_date_ref.current.value = report_data.get('fiu_letter_receive_date', '')
        if fiu_feedback_ref.current:
            fiu_feedback_ref.current.value = report_data.get('fiu_feedback', '')
        if fiu_letter_number_ref.current:
            fiu_letter_number_ref.current.value = report_data.get('fiu_letter_number', '')

        page.update()

    def reserve_numbers():
        """Reserve report numbers for new reports."""
        if is_edit_mode or not report_number_service:
            return

        try:
            success, reservation, message = report_number_service.reserve_next_numbers(
                current_user['username']
            )

            if success and reservation:
                reservation_info["value"] = reservation

                if sn_ref.current:
                    sn_ref.current.value = str(reservation['serial_number'])
                    sn_ref.current.read_only = True
                if report_number_ref.current:
                    report_number_ref.current.value = reservation['report_number']
                    report_number_ref.current.read_only = True

                page.update()

                if reservation.get('has_gap') and reservation.get('gap_info'):
                    gap_info = reservation['gap_info']
                    show_gap_notice(gap_info)

                logging_service.info(
                    f"Reserved numbers for {current_user['username']}: "
                    f"Report# {reservation['report_number']}, SN {reservation['serial_number']}"
                )
            else:
                logging_service.warning(f"Could not reserve report number: {message}")

        except Exception as ex:
            logging_service.error(f"Error reserving numbers: {ex}")

    def show_gap_notice(gap_info):
        """Show gap notice dialog."""
        gap_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Gap Detected"),
            content=ft.Text(
                f"📋 Gap Notice:\n\n{gap_info['message']}\n\n"
                f"The system is reusing this number to fill the gap in the sequence.\n\n"
                f"Deleted on: {gap_info.get('deleted_at', 'Unknown')}\n"
                f"Deleted by: {gap_info.get('deleted_by', 'Unknown')}"
            ),
            actions=[
                ft.TextButton("OK", on_click=lambda e: close_gap_dialog()),
            ],
        )

        def close_gap_dialog():
            gap_dialog.open = False
            page.update()

        page.overlay.append(gap_dialog)
        gap_dialog.open = True
        page.update()

    # Build tabs
    def build_basic_info_tab():
        """Build Basic Information tab."""
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Column(
                        controls=[
                            ft.Text("Serial Number *", size=12, weight=ft.FontWeight.W_500, color=colors["text_secondary"]),
                            ft.TextField(
                                ref=sn_ref,
                                hint_text="Enter serial number (e.g., 1)",
                                text_size=13,
                                border_radius=8,
                                on_change=validate_sn_live,
                            ),
                        ],
                        spacing=4,
                    ),
                    ft.Column(
                        controls=[
                            ft.Text("Report Number *", size=12, weight=ft.FontWeight.W_500, color=colors["text_secondary"]),
                            ft.TextField(
                                ref=report_number_ref,
                                hint_text="Format: YYYY/MM/NNN (e.g., 2025/11/001)",
                                text_size=13,
                                border_radius=8,
                                on_change=validate_report_number_live,
                            ),
                        ],
                        spacing=4,
                    ),
                    ft.Column(
                        controls=[
                            ft.Text("Report Date *", size=12, weight=ft.FontWeight.W_500, color=colors["text_secondary"]),
                            ft.TextField(
                                ref=report_date_ref,
                                hint_text="DD/MM/YYYY",
                                value=datetime.now().strftime("%d/%m/%Y"),
                                text_size=13,
                                border_radius=8,
                            ),
                        ],
                        spacing=4,
                    ),
                ],
                spacing=16,
                scroll=ft.ScrollMode.AUTO,
            ),
            padding=20,
        )

    def build_entity_details_tab():
        """Build Entity Details tab."""
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Column(
                        controls=[
                            ft.Text("Reported Entity Name *", size=12, weight=ft.FontWeight.W_500, color=colors["text_secondary"]),
                            ft.TextField(
                                ref=entity_name_ref,
                                hint_text="Enter entity name",
                                text_size=13,
                                border_radius=8,
                                on_change=validate_entity_name_live,
                            ),
                        ],
                        spacing=4,
                    ),
                    ft.Checkbox(
                        ref=legal_owner_ref,
                        label="Is Legal Entity Owner",
                        value=False,
                    ),
                    ft.Column(
                        controls=[
                            ft.Text("Gender", size=12, weight=ft.FontWeight.W_500, color=colors["text_secondary"]),
                            ft.Dropdown(
                                ref=gender_ref,
                                options=[ft.dropdown.Option("")] + [ft.dropdown.Option(g) for g in genders],
                                text_size=13,
                                border_radius=8,
                            ),
                        ],
                        spacing=4,
                    ),
                    ft.Column(
                        controls=[
                            ft.Text("Nationality", size=12, weight=ft.FontWeight.W_500, color=colors["text_secondary"]),
                            ft.Dropdown(
                                ref=nationality_ref,
                                options=[ft.dropdown.Option("")] + [ft.dropdown.Option(n) for n in nationalities],
                                text_size=13,
                                border_radius=8,
                            ),
                        ],
                        spacing=4,
                    ),
                    ft.Column(
                        controls=[
                            ft.Text("ID/CR", size=12, weight=ft.FontWeight.W_500, color=colors["text_secondary"]),
                            ft.TextField(
                                ref=id_cr_ref,
                                hint_text="Enter ID or Commercial Registration number",
                                text_size=13,
                                border_radius=8,
                            ),
                        ],
                        spacing=4,
                    ),
                    ft.Checkbox(
                        ref=id_type_checkbox_ref,
                        label="Is Commercial Registration (CR)",
                        value=False,
                        on_change=update_id_type_display,
                    ),
                    ft.Column(
                        controls=[
                            ft.Text("ID/CR Type", size=12, weight=ft.FontWeight.W_500, color=colors["text_secondary"]),
                            ft.TextField(
                                ref=id_type_display_ref,
                                value="ID",
                                read_only=True,
                                text_size=13,
                                border_radius=8,
                            ),
                        ],
                        spacing=4,
                    ),
                    ft.Column(
                        controls=[
                            ft.Text("Account/Membership", size=12, weight=ft.FontWeight.W_500, color=colors["text_secondary"]),
                            ft.TextField(
                                ref=account_ref,
                                hint_text="Enter account or membership number",
                                text_size=13,
                                border_radius=8,
                            ),
                        ],
                        spacing=4,
                    ),
                    ft.Checkbox(
                        ref=acc_membership_ref,
                        label="Is Membership?",
                        value=False,
                        on_change=update_relationship_display,
                    ),
                    ft.Column(
                        controls=[
                            ft.Text("Relationship", size=12, weight=ft.FontWeight.W_500, color=colors["text_secondary"]),
                            ft.TextField(
                                ref=relationship_ref,
                                value="Current Account",
                                read_only=True,
                                text_size=13,
                                border_radius=8,
                            ),
                        ],
                        spacing=4,
                    ),
                    ft.Column(
                        controls=[
                            ft.Text("Branch ID", size=12, weight=ft.FontWeight.W_500, color=colors["text_secondary"]),
                            ft.TextField(
                                ref=branch_ref,
                                hint_text="Enter branch ID",
                                text_size=13,
                                border_radius=8,
                            ),
                        ],
                        spacing=4,
                    ),
                    ft.Column(
                        controls=[
                            ft.Text("CIC", size=12, weight=ft.FontWeight.W_500, color=colors["text_secondary"]),
                            ft.TextField(
                                ref=cic_ref,
                                hint_text="Enter CIC number (will auto-pad to 16 digits)",
                                max_length=16,
                                text_size=13,
                                border_radius=8,
                                on_change=validate_cic_live,
                                on_blur=finalize_cic,
                            ),
                        ],
                        spacing=4,
                    ),
                ],
                spacing=12,
                scroll=ft.ScrollMode.AUTO,
            ),
            padding=20,
        )

    def build_suspicion_details_tab():
        """Build Suspicion Details tab."""
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Column(
                        controls=[
                            ft.Text("First Reason for Suspicion", size=12, weight=ft.FontWeight.W_500, color=colors["text_secondary"]),
                            ft.TextField(
                                ref=first_reason_ref,
                                hint_text="Describe the first reason for suspicion",
                                multiline=True,
                                min_lines=3,
                                max_lines=5,
                                text_size=13,
                                border_radius=8,
                            ),
                        ],
                        spacing=4,
                    ),
                    ft.Column(
                        controls=[
                            ft.Text("Second Reason for Suspicion", size=12, weight=ft.FontWeight.W_500, color=colors["text_secondary"]),
                            ft.Dropdown(
                                ref=second_reason_ref,
                                options=[ft.dropdown.Option("")] + [ft.dropdown.Option(r) for r in second_reasons],
                                text_size=13,
                                border_radius=8,
                            ),
                        ],
                        spacing=4,
                    ),
                    ft.Column(
                        controls=[
                            ft.Text("Type of Suspected Transaction", size=12, weight=ft.FontWeight.W_500, color=colors["text_secondary"]),
                            ft.Dropdown(
                                ref=transaction_type_ref,
                                options=[ft.dropdown.Option("")] + [ft.dropdown.Option(t) for t in transaction_types],
                                text_size=13,
                                border_radius=8,
                            ),
                        ],
                        spacing=4,
                    ),
                    ft.Column(
                        controls=[
                            ft.Text("ARB Staff", size=12, weight=ft.FontWeight.W_500, color=colors["text_secondary"]),
                            ft.Dropdown(
                                ref=arb_staff_ref,
                                options=[ft.dropdown.Option("")] + [ft.dropdown.Option(a) for a in arb_staff_values],
                                text_size=13,
                                border_radius=8,
                            ),
                        ],
                        spacing=4,
                    ),
                    ft.Column(
                        controls=[
                            ft.Text("Total Transaction", size=12, weight=ft.FontWeight.W_500, color=colors["text_secondary"]),
                            ft.TextField(
                                ref=total_transaction_ref,
                                hint_text="Enter amount with SAR (e.g., 605040 SAR)",
                                text_size=13,
                                border_radius=8,
                            ),
                        ],
                        spacing=4,
                    ),
                ],
                spacing=16,
                scroll=ft.ScrollMode.AUTO,
            ),
            padding=20,
        )

    def build_classification_tab():
        """Build Classification & Source tab."""
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Column(
                        controls=[
                            ft.Text("Report Classification", size=12, weight=ft.FontWeight.W_500, color=colors["text_secondary"]),
                            ft.Dropdown(
                                ref=classification_ref,
                                options=[ft.dropdown.Option("")] + [ft.dropdown.Option(c) for c in classifications],
                                text_size=13,
                                border_radius=8,
                            ),
                        ],
                        spacing=4,
                    ),
                    ft.Column(
                        controls=[
                            ft.Text("Report Source", size=12, weight=ft.FontWeight.W_500, color=colors["text_secondary"]),
                            ft.Dropdown(
                                ref=report_source_ref,
                                options=[ft.dropdown.Option("")] + [ft.dropdown.Option(s) for s in report_sources],
                                text_size=13,
                                border_radius=8,
                            ),
                        ],
                        spacing=4,
                    ),
                    ft.Column(
                        controls=[
                            ft.Text("Reporting Entity", size=12, weight=ft.FontWeight.W_500, color=colors["text_secondary"]),
                            ft.Dropdown(
                                ref=reporting_entity_ref,
                                options=[ft.dropdown.Option("")] + [ft.dropdown.Option(e) for e in reporting_entities],
                                text_size=13,
                                border_radius=8,
                            ),
                        ],
                        spacing=4,
                    ),
                    ft.Column(
                        controls=[
                            ft.Text("Reporter Initials", size=12, weight=ft.FontWeight.W_500, color=colors["text_secondary"]),
                            ft.TextField(
                                ref=reporter_initials_ref,
                                hint_text="Enter 2 uppercase letters (e.g., ZM)",
                                max_length=2,
                                text_size=13,
                                border_radius=8,
                                on_change=validate_initials_live,
                            ),
                        ],
                        spacing=4,
                    ),
                    ft.Column(
                        controls=[
                            ft.Text("Sending Date", size=12, weight=ft.FontWeight.W_500, color=colors["text_secondary"]),
                            ft.TextField(
                                ref=sending_date_ref,
                                hint_text="DD/MM/YYYY (optional)",
                                text_size=13,
                                border_radius=8,
                            ),
                        ],
                        spacing=4,
                    ),
                ],
                spacing=16,
                scroll=ft.ScrollMode.AUTO,
            ),
            padding=20,
        )

    def build_fiu_details_tab():
        """Build FIU Details tab."""
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Column(
                        controls=[
                            ft.Text("FIU Number", size=12, weight=ft.FontWeight.W_500, color=colors["text_secondary"]),
                            ft.TextField(
                                ref=fiu_number_ref,
                                hint_text="Enter FIU number",
                                text_size=13,
                                border_radius=8,
                            ),
                        ],
                        spacing=4,
                    ),
                    ft.Column(
                        controls=[
                            ft.Text("FIU Letter Receive Date", size=12, weight=ft.FontWeight.W_500, color=colors["text_secondary"]),
                            ft.TextField(
                                ref=fiu_receive_date_ref,
                                hint_text="DD/MM/YYYY (optional)",
                                text_size=13,
                                border_radius=8,
                            ),
                        ],
                        spacing=4,
                    ),
                    ft.Column(
                        controls=[
                            ft.Text("FIU Feedback", size=12, weight=ft.FontWeight.W_500, color=colors["text_secondary"]),
                            ft.Dropdown(
                                ref=fiu_feedback_ref,
                                options=[ft.dropdown.Option("")] + [ft.dropdown.Option(f) for f in fiu_feedbacks],
                                text_size=13,
                                border_radius=8,
                            ),
                        ],
                        spacing=4,
                    ),
                    ft.Column(
                        controls=[
                            ft.Text("FIU Letter Number", size=12, weight=ft.FontWeight.W_500, color=colors["text_secondary"]),
                            ft.TextField(
                                ref=fiu_letter_number_ref,
                                hint_text="Enter FIU letter number",
                                text_size=13,
                                border_radius=8,
                            ),
                        ],
                        spacing=4,
                    ),
                ],
                spacing=16,
                scroll=ft.ScrollMode.AUTO,
            ),
            padding=20,
        )

    # Header with badges
    header_controls = [
        ft.Text(
            "Edit Report" if is_edit_mode else "Add New Report",
            size=18,
            weight=ft.FontWeight.BOLD,
            color=colors["text_primary"],
        ),
    ]

    if is_edit_mode and report_data:
        current_version = report_data.get('current_version', 1)
        approval_status = report_data.get('approval_status', 'draft')

        # Version badge
        header_controls.append(
            ft.Container(
                content=ft.Text(f"v{current_version}", size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                bgcolor=colors["primary"],
                border_radius=10,
                padding=ft.padding.symmetric(horizontal=12, vertical=4),
            )
        )

        # Approval status badge
        status_colors = {
            'draft': colors["text_secondary"],
            'pending_approval': colors["warning"],
            'approved': colors["success"],
            'rejected': colors["danger"],
            'rework': colors["warning"],
        }
        status_labels = {
            'draft': 'Draft',
            'pending_approval': 'Pending Approval',
            'approved': 'Approved',
            'rejected': 'Rejected',
            'rework': 'Needs Rework',
        }

        header_controls.append(
            ft.Container(
                content=ft.Text(
                    status_labels.get(approval_status, approval_status),
                    size=11,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.WHITE,
                ),
                bgcolor=status_colors.get(approval_status, colors["text_secondary"]),
                border_radius=10,
                padding=ft.padding.symmetric(horizontal=12, vertical=4),
            )
        )

    # Build tabs content
    tabs = ft.Tabs(
        selected_index=0,
        animation_duration=300,
        tabs=[
            ft.Tab(text="Basic Information", content=build_basic_info_tab()),
            ft.Tab(text="Entity Details", content=build_entity_details_tab()),
            ft.Tab(text="Suspicion Details", content=build_suspicion_details_tab()),
            ft.Tab(text="Classification & Source", content=build_classification_tab()),
            ft.Tab(text="FIU Details", content=build_fiu_details_tab()),
        ],
        expand=True,
    )

    # Build action buttons
    action_buttons = []

    # Left side buttons
    if is_edit_mode and report_data:
        action_buttons.append(
            ft.TextButton(
                "View History",
                icon=ft.Icons.HISTORY,
                on_click=view_history,
            )
        )

    action_buttons.append(ft.Container(expand=True))

    # Right side buttons
    action_buttons.append(
        ft.TextButton(
            "Cancel",
            icon=ft.Icons.CLOSE,
            on_click=close_dialog,
        )
    )

    action_buttons.append(
        ft.ElevatedButton(
            "Save Report",
            icon=ft.Icons.SAVE,
            bgcolor=colors["primary"],
            color=ft.Colors.WHITE,
            on_click=save_report,
        )
    )

    # Submit for approval button
    if is_edit_mode and report_data:
        approval_status = report_data.get('approval_status', 'draft')
        if approval_status not in ['pending_approval', 'approved']:
            action_buttons.append(
                ft.ElevatedButton(
                    "Submit for Approval",
                    icon=ft.Icons.CHECK_CIRCLE,
                    bgcolor=colors["success"],
                    color=ft.Colors.WHITE,
                    on_click=submit_for_approval,
                )
            )

    # Create dialog content
    dialog_content = ft.Container(
        content=ft.Column(
            controls=[
                # Header
                ft.Row(controls=header_controls, spacing=12),
                ft.Divider(color=colors["border"]),
                # Tabs
                tabs,
                # Buttons
                ft.Row(controls=action_buttons, spacing=8),
            ],
            spacing=16,
        ),
        width=900,
        height=650,
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

    # Load data or reserve numbers
    if is_edit_mode:
        load_report_data()
    else:
        reserve_numbers()
