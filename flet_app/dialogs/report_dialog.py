"""
Report Dialog for FIU Report Management System.
Comprehensive 35-field tabbed form for creating and editing reports.
"""
import flet as ft
from i18n import t
from components.searchable_dropdown import searchable_dropdown
from typing import Optional, Any, Callable
from datetime import datetime
import re
import asyncio

from theme.theme_manager import theme_manager
from services.remote_gateway import HostOfflineError
from components.app_button import app_button
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
    intelligence_service = app_state.intelligence_service
    current_user = app_state.current_user
    if not current_user:            # no session -> the form can't function
        from components.toast import show_error
        show_error(page, t("form.err.login_first"))
        return
    # #7: only users who may add reports can open the create form. Refuse cleanly
    # (a reporter, e.g.) instead of showing a misleading "reserve numbers" message.
    if not is_edit_mode and not app_state.auth_service.has_permission('add_report'):
        from components.toast import show_error
        show_error(page, t("form.err.no_create"))
        return

    # State
    reservation_info = {"value": None}

    # Error banner ref (for inline error display)
    error_banner_ref = ft.Ref[ft.Container]()

    # #5 / #14: non-blocking intelligence banners under CIC and Account.
    cic_intel_ref = ft.Ref[ft.Container]()
    account_intel_ref = ft.Ref[ft.Container]()
    _edit_report_id = (report_data.get('report_id') or report_data.get('id')) if is_edit_mode else None

    # Load dropdown values
    # #3: options are (english_value, localized_label) — store the English
    # canonical, show the label in the user's language.
    # NOTE: `t` is imported at module level. Re-importing it here would make it a
    # function-local name and every earlier t(...) call (the login/permission
    # guards above) would raise UnboundLocalError.
    from i18n import get_language
    from i18n.fields import field_label
    _lang = get_language()
    _db = app_state.db_manager
    def _flabel(col, required=False):
        # admin-managed column_settings wins; fall back to the static catalog,
        # then a humanized name. Append the required marker.
        lbl = field_label(_db, col, _lang, strict=True)
        if lbl is None:
            c = t(f"field.{col}")
            lbl = c if c != f"field.{col}" else col.replace('_', ' ').title()
        return lbl + (" *" if required else "")
    def _opts(cat):
        return dropdown_service.get_active_options(cat, _lang) if dropdown_service else []
    genders = _opts('gender')
    nationalities = _opts('nationality')
    second_reasons = _opts('second_reason_for_suspicion')
    transaction_types = _opts('type_of_suspected_transaction')
    arb_staff_values = _opts('arb_staff')
    classifications = _opts('report_classification')
    report_sources = _opts('report_source')
    reporting_entities = _opts('reporting_entity')
    fiu_feedbacks = _opts('fiu_feedback')

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
    fiu_date_ref = ft.Ref[ft.TextField]()
    case_id_ref = ft.Ref[ft.TextField]()

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

    def _fill_intel_banner(ref, icon, color, title, lines):
        """Render (or hide) a non-blocking info banner into `ref`'s container."""
        if not ref.current:
            return
        if not lines:
            ref.current.visible = False
            ref.current.content = None
        else:
            ref.current.visible = True
            ref.current.bgcolor = ft.Colors.with_opacity(0.08, color)
            ref.current.border = ft.border.all(1, ft.Colors.with_opacity(0.4, color))
            ref.current.content = ft.Column(
                controls=[
                    ft.Row([ft.Icon(icon, size=15, color=color),
                            ft.Text(title, size=12, weight=ft.FontWeight.BOLD, color=color)],
                           spacing=6),
                ] + [ft.Text(f"• {ln}", size=11, color=colors["text_secondary"], selectable=True)
                     for ln in lines],
                spacing=2, tight=True,
            )
        try:
            ref.current.update()
        except Exception:
            pass

    def _report_line(r):
        return (f"{r.get('report_number') or '—'} · {r.get('reported_entity_name') or '(no entity)'} "
                f"· {r.get('report_date') or ''} · {(r.get('approval_status') or '').replace('_',' ')}")

    def prefill_from_cic(e=None):
        """Fetch the customer's known entity details for this CIC and fill them in.

        The CIC is the customer code the analyst starts from: the bank has
        already recorded who this customer is on an earlier report, so retyping
        (and mistyping) name / ID / nationality / branch is pure risk. Only
        EMPTY fields are filled -- whatever the analyst typed always wins, and
        every filled value stays editable.
        """
        if not intelligence_service or not cic_ref.current:
            return []
        cic = (cic_ref.current.value or "").replace(' ', '').replace('-', '').strip()
        if len(cic) != 16 or not cic.isdigit():
            return []
        profile = intelligence_service.customer_profile(cic, exclude_report_id=_edit_report_id)
        if not profile:
            return []

        filled = []

        def fill_text(ref, key, label):
            value = profile.get(key)
            if not ref.current or not value:
                return
            if (ref.current.value or "").strip():
                return                      # analyst already typed something
            ref.current.value = str(value)
            filled.append(label)

        def fill_choice(ref, key, label):
            value = profile.get(key)
            if not ref.current or not value:
                return
            if (getattr(ref.current, "value", "") or ""):
                return
            ref.current.value = str(value)
            filled.append(label)

        def fill_check(ref, key, label):
            value = profile.get(key)
            if not ref.current or value in (None, ""):
                return
            new = bool(int(value)) if str(value).isdigit() else bool(value)
            if ref.current.value == new:
                return
            ref.current.value = new
            filled.append(label)

        fill_text(entity_name_ref, "reported_entity_name", "entity name")
        fill_choice(gender_ref, "gender", "gender")
        fill_choice(nationality_ref, "nationality", "nationality")
        fill_text(id_cr_ref, "id_cr", "ID/CR")
        fill_text(branch_ref, "branch_id", "branch")
        fill_check(legal_owner_ref, "legal_entity_owner_checkbox", "legal owner")
        fill_check(id_type_checkbox_ref, "id_type", "ID type")

        # keep the ID-type display in step with its checkbox. The
        # account/membership fields are intentionally left alone: the customer
        # may hold several accounts, or an account and a membership, so only the
        # analyst knows which one this report is about.
        if id_type_display_ref.current and id_type_checkbox_ref.current:
            id_type_display_ref.current.value = "CR" if id_type_checkbox_ref.current.value else "ID"

        if filled:
            try:
                page.update()
            except Exception:
                pass
        return filled

    def update_cic_intel(e=None):
        """#5: a duplicate CIC is INFORMATION, never a blocker — show the subject's
        prior filings so the analyst sees the fuller picture."""
        finalize_cic(e)
        if not intelligence_service or not cic_ref.current:
            return
        prefilled = prefill_from_cic(e)
        cic = (cic_ref.current.value or "").strip()
        empty = {"count": 0, "reports": [], "summary": {}}
        h = intelligence_service.cic_history(cic, exclude_report_id=_edit_report_id) if cic else empty
        if h["count"] == 0:
            _fill_intel_banner(cic_intel_ref, None, colors["info"], "", [])
            return
        lead = ([f"Filled from the last report for this customer: {', '.join(prefilled)}"]
                if prefilled else [])
        s = h.get("summary", {}) or {}
        lines = list(lead)
        if s.get("entities"):
            lines.append("Entities: " + ", ".join(s["entities"][:4])
                         + (" …" if len(s["entities"]) > 4 else ""))
        if s.get("amount_sum") is not None:
            lines.append(f"Total transactions: {s['amount_sum']:,.2f} "
                         f"(min {s['amount_min']:,.2f} – max {s['amount_max']:,.2f})")
        if s.get("days_since_last") is not None:
            lines.append(f"Days since last report: {s['days_since_last']}")
        if s.get("pending"):
            lines.append(f"{s['pending']} still pending approval")
        if s.get("classifications"):
            lines.append("Classifications: " + ", ".join(s["classifications"][:4]))
        # then the most recent reports themselves
        for r in h["reports"][:3]:
            lines.append(_report_line(r))
        if h["count"] > 3:
            lines.append(f"…and {h['count'] - 3} more report(s)")
        _fill_intel_banner(
            cic_intel_ref, ft.Icons.INFO_OUTLINE, colors["info"],
            f"This CIC already appears on {h['count']} report(s):", lines)

    def update_account_intel(e=None):
        """#14: multiple reports on one account within 0–2 days is a structuring
        signal — flag it (non-blocking)."""
        if not intelligence_service or not account_ref.current:
            return
        account = (account_ref.current.value or "").strip()
        rdate = report_date_ref.current.value if report_date_ref.current else ""
        r = intelligence_service.account_rapid_repeat(
            account, rdate, within_days=2, exclude_report_id=_edit_report_id) if account else {"count": 0, "reports": []}
        if r["count"] == 0:
            _fill_intel_banner(account_intel_ref, None, colors["warning"], "", [])
            return
        shown = r["reports"][:5]
        lines = [_report_line(x) for x in shown]
        if r["count"] > len(shown):
            lines.append(f"…and {r['count'] - len(shown)} more")
        _fill_intel_banner(
            account_intel_ref, ft.Icons.WARNING_AMBER, colors["warning"],
            f"Possible structuring: {r['count']} other report(s) on this account within 2 days:",
            lines)

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

    def validate_id_cr_live(e):
        """Live validation for ID/CR field using database rules."""
        if id_cr_ref.current:
            value = id_cr_ref.current.value.strip() if id_cr_ref.current.value else ""
            if not value:
                id_cr_ref.current.error_text = None
                page.update()
                return

            # Get context
            nationality = nationality_ref.current.value if nationality_ref.current else ""
            is_cr = id_type_checkbox_ref.current.value if id_type_checkbox_ref.current else False

            # Validate using service
            is_valid, error_msg = validation_service.validate_field_from_db(
                'id_cr', value, nationality=nationality, is_cr=is_cr
            )

            id_cr_ref.current.error_text = error_msg if not is_valid else None
            page.update()

    def validate_account_live(e):
        """Live validation for Account/Membership field using database rules."""
        if account_ref.current:
            value = account_ref.current.value.strip() if account_ref.current.value else ""
            if not value:
                account_ref.current.error_text = None
                page.update()
                return

            # Get context
            is_membership = acc_membership_ref.current.value if acc_membership_ref.current else False

            # Validate using service
            is_valid, error_msg = validation_service.validate_field_from_db(
                'account_membership', value, is_membership=is_membership
            )

            account_ref.current.error_text = error_msg if not is_valid else None
            page.update()

    def validate_form() -> tuple[bool, list]:
        """Validate form data using database-backed rules. Returns (is_valid, errors)."""
        errors = []
        form_data = get_form_data()

        # Field mapping: database column name -> (form_data key, display name)
        field_mappings = {
            'sn': ('sn', 'Serial Number'),
            'report_number': ('report_number', 'Report Number'),
            'report_date': ('report_date', 'Report Date'),
            'reported_entity_name': ('reported_entity_name', 'Reported Entity Name'),
            'id_cr': ('id_cr', 'ID/CR'),
            'account_membership': ('account_membership', 'Account/Membership'),
            'cic': ('cic', 'CIC'),
            'reporter_initials': ('reporter_initials', 'Reporter Initials'),
            'gender': ('gender', 'Gender'),
            'nationality': ('nationality', 'Nationality'),
            'branch_id': ('branch_id', 'Branch ID'),
            'first_reason_for_suspicion': ('first_reason_for_suspicion', 'First Reason for Suspicion'),
            'second_reason_for_suspicion': ('second_reason_for_suspicion', 'Second Reason for Suspicion'),
            'type_of_suspected_transaction': ('type_of_suspected_transaction', 'Type of Suspected Transaction'),
            'arb_staff': ('arb_staff', 'ARB Staff'),
            'total_transaction': ('total_transaction', 'Total Transaction'),
            'report_classification': ('report_classification', 'Report Classification'),
            'report_source': ('report_source', 'Report Source'),
            'reporting_entity': ('reporting_entity', 'Reporting Entity'),
            'sending_date': ('sending_date', 'Sending Date'),
            'fiu_number': ('fiu_number', 'FIU Number'),
            'fiu_letter_receive_date': ('fiu_letter_receive_date', 'FIU Letter Receive Date'),
            'fiu_feedback': ('fiu_feedback', 'FIU Feedback'),
            'fiu_letter_number': ('fiu_letter_number', 'FIU Letter Number'),
        }

        # Validate each field using database rules
        for field_name, (data_key, display_name) in field_mappings.items():
            value = form_data.get(data_key)
            if value is None:
                value = ''
            value = str(value).strip() if value else ''

            # Special handling for id_cr field (needs nationality context)
            if field_name == 'id_cr' and value:
                nationality = form_data.get('nationality', '')
                is_cr = form_data.get('id_type', 'ID') == 'CR'
                is_valid, error_msg = validation_service.validate_field_from_db(
                    'id_cr', value, nationality=nationality, is_cr=is_cr
                )
                if not is_valid:
                    errors.append(f"{display_name}: {error_msg}")
                continue

            # Special handling for account_membership field
            if field_name == 'account_membership' and value:
                is_membership = form_data.get('acc_membership_checkbox', 0) == 1
                is_valid, error_msg = validation_service.validate_field_from_db(
                    'account_membership', value, is_membership=is_membership
                )
                if not is_valid:
                    errors.append(f"{display_name}: {error_msg}")
                continue

            # Generic validation for all other fields
            is_valid, error_msg = validation_service.validate_field_generic(
                field_name, value, check_required=True
            )
            if not is_valid:
                # Avoid duplicate "is required" text
                if "is required" in error_msg:
                    errors.append(error_msg)
                else:
                    errors.append(f"{display_name}: {error_msg}")

        # Additional format validations (keep existing hardcoded rules for complex patterns)
        sn = form_data.get('sn', '')
        if sn and not str(sn).isdigit():
            if "Serial Number" not in str(errors):
                errors.append("Serial Number must be a number")

        report_num = form_data.get('report_number', '')
        if report_num and not re.match(r'^\d{4}/\d{2}/\d{3}$', str(report_num)):
            if "Report Number" not in str(errors):
                errors.append("Report Number must be in format YYYY/MM/NNN (e.g., 2025/11/001)")

        # CIC validation (16 digits)
        cic = form_data.get('cic', '')
        if cic:
            cic_cleaned = str(cic).replace(' ', '').replace('-', '')
            if not cic_cleaned.isdigit():
                if "CIC" not in str(errors):
                    errors.append("CIC must contain only digits")
            elif len(cic_cleaned) != 16:
                if "CIC" not in str(errors):
                    errors.append("CIC must be exactly 16 digits")

        # Reporter initials validation (2 uppercase letters)
        initials = form_data.get('reporter_initials', '')
        if initials and not re.match(r'^[A-Z]{2}$', str(initials)):
            if "Reporter Initials" not in str(errors):
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

        def get_int_value(ref, default=0):
            raw = get_value(ref, str(default))
            try:
                return int(raw)
            except (ValueError, TypeError):
                return default

        return {
            'sn': get_int_value(sn_ref, 0),
            'report_number': get_value(report_number_ref),
            'case_id': get_value(case_id_ref) or None,
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
            'fiu_date': get_value(fiu_date_ref) or None,
        }

    def save_report(e):
        """Save the report."""
        is_valid, errors = validate_form()
        if not is_valid:
            show_error_dialog("\n".join(f"• {err}" for err in errors))
            return

        try:
            form_data = get_form_data()
            if is_edit_mode:
                report_id = report_data.get('report_id') or report_data.get('id')
                if not report_id:
                    show_error_dialog("Report ID not found")
                    return

                success, message = report_service.update_report(report_id, form_data)

                # (update_report versions the change itself)
            else:
                form_data.pop('report_number', None)
                form_data.pop('sn', None)
                success, report_id, message = report_service.create_report(form_data)

            if success:
                show_success_dialog(message)
                dialog.open = False
                page.update()
                if on_save:
                    on_save()
            else:
                show_error_dialog(message)

        except HostOfflineError:
            # Host unreachable: the write was queued in the client outbox
            # (services.outbox) and will be replayed once the host comes
            # back. Close the dialog as if saved - it will apply exactly once.
            show_success_dialog(
                "Host offline — your entry is queued and will sync when the host returns."
            )
            dialog.open = False
            page.update()
            if on_save:
                on_save()

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
                # #3: auto-save the current form FIRST so Submit is one frictionless
                # action — no separate Save click, and the reviewer sees the edits.
                is_valid, errors = validate_form()
                if not is_valid:
                    show_error_dialog("\n".join(f"• {err}" for err in errors))
                    return
                ok_save, save_msg = report_service.update_report(report_id, get_form_data())
                if not ok_save:
                    show_error_dialog(f"Couldn't save before submitting: {save_msg}")
                    return
                # (update_report versions the change itself)

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
            title=ft.Text(t("form.submit")),
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
        """Show error as inline banner within the dialog (no separate overlay)."""
        if error_banner_ref.current:
            # Update error message and show banner
            error_banner_ref.current.content.controls[1].value = message
            error_banner_ref.current.visible = True
            page.update()

    def hide_error_banner():
        """Hide the error banner."""
        if error_banner_ref.current:
            error_banner_ref.current.visible = False
            page.update()

    def show_success_dialog(message: str):
        """Show success dialog."""
        success_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(t("form.success"), color=colors["success"]),
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
        """Close dialog and release any edit lock (R28)."""
        if is_edit_mode and report_data:
            rid = report_data.get('report_id') or report_data.get('id')
            if rid:
                try:
                    report_service.release_edit_lock(rid)
                except Exception:
                    pass

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
        if case_id_ref.current:
            case_id_ref.current.value = report_data.get('case_id', '') or ''
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
        if fiu_date_ref.current:
            fiu_date_ref.current.value = report_data.get('fiu_date', '')

        page.update()
        # surface intelligence for the already-populated CIC / account on open
        update_cic_intel()
        update_account_intel()

    def reserve_numbers():
        """Show (read-only) the reserved number this new report will consume."""
        if is_edit_mode or not report_number_service:
            return
        avail = report_number_service.get_available_numbers(current_user['username'])
        if avail:
            nxt = avail[0]
            reservation_info["value"] = nxt  # display only
            if sn_ref.current:
                sn_ref.current.value = str(nxt['serial_number']); sn_ref.current.read_only = True
            if report_number_ref.current:
                report_number_ref.current.value = nxt['report_number']; report_number_ref.current.read_only = True
            page.update()

    # Build tabs
    def build_basic_info_tab():
        """Build Basic Information tab."""
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Column(
                        controls=[
                            ft.Text(_flabel("sn", required=True), size=12, weight=ft.FontWeight.W_500, color=colors["text_secondary"]),
                            ft.TextField(
                                ref=sn_ref,
                                hint_text=t("form.hint.sn"),
                                text_size=13,
                                border_radius=4,
                                on_change=validate_sn_live,
                            ),
                        ],
                        spacing=4,
                    ),
                    ft.Column(
                        controls=[
                            ft.Text(_flabel("report_number", required=True), size=12, weight=ft.FontWeight.W_500, color=colors["text_secondary"]),
                            ft.TextField(
                                ref=report_number_ref,
                                hint_text=t("form.hint.report_number"),
                                text_size=13,
                                border_radius=4,
                                on_change=validate_report_number_live,
                            ),
                        ],
                        spacing=4,
                    ),
                    ft.Column(
                        controls=[
                            ft.Text(_flabel("case_id"), size=12, weight=ft.FontWeight.W_500, color=colors["text_secondary"]),
                            ft.TextField(
                                ref=case_id_ref,
                                hint_text=t("form.hint.case_id"),
                                text_size=13,
                                border_radius=4,
                            ),
                        ],
                        spacing=4,
                    ),
                    create_date_picker(
                        label=_flabel("report_date"),
                        value=datetime.now(),
                        required=True,
                        ref=report_date_ref,
                        page=page,
                        hint_text=t("form.hint.date"),
                    ),
                ],
                spacing=16,
                scroll=ft.ScrollMode.AUTO,
            ),
            padding=12,
        )

    def build_entity_details_tab():
        """Build Entity Details tab."""
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Column(
                        controls=[
                            ft.Text(_flabel("cic"), size=12, weight=ft.FontWeight.W_500, color=colors["text_secondary"]),
                            ft.TextField(
                                ref=cic_ref,
                                hint_text=t("form.hint.cic"),
                                max_length=16,
                                text_size=13,
                                border_radius=4,
                                on_change=validate_cic_live,
                                on_blur=update_cic_intel,
                            ),
                            ft.Container(ref=cic_intel_ref, visible=False,
                                         border_radius=4, padding=8),
                        ],
                        spacing=4,
                    ),
                    ft.Column(
                        controls=[
                            ft.Text(_flabel("reported_entity_name", required=True), size=12, weight=ft.FontWeight.W_500, color=colors["text_secondary"]),
                            ft.TextField(
                                ref=entity_name_ref,
                                hint_text=t("form.hint.entity"),
                                text_size=13,
                                border_radius=4,
                                on_change=validate_entity_name_live,
                            ),
                        ],
                        spacing=4,
                    ),
                    ft.Checkbox(
                        ref=legal_owner_ref,
                        label=t("form.chk.legal_owner"),
                        value=False,
                    ),
                    ft.Column(
                        controls=[
                            ft.Text(_flabel("gender"), size=12, weight=ft.FontWeight.W_500, color=colors["text_secondary"]),
                            searchable_dropdown(
                                ref=gender_ref,
                                options=[ft.dropdown.Option(key="", text="-- Select --")] + [ft.dropdown.Option(key=_v, text=_l) for _v, _l in genders],
                                text_size=13,
                                border_radius=4,
                            ),
                        ],
                        spacing=4,
                    ),
                    ft.Column(
                        controls=[
                            ft.Text(_flabel("nationality"), size=12, weight=ft.FontWeight.W_500, color=colors["text_secondary"]),
                            searchable_dropdown(
                                ref=nationality_ref,
                                options=[ft.dropdown.Option(key="", text="-- Select --")] + [ft.dropdown.Option(key=_v, text=_l) for _v, _l in nationalities],
                                text_size=13,
                                border_radius=4,
                            ),
                        ],
                        spacing=4,
                    ),
                    ft.Column(
                        controls=[
                            ft.Text(_flabel("id_cr"), size=12, weight=ft.FontWeight.W_500, color=colors["text_secondary"]),
                            ft.TextField(
                                ref=id_cr_ref,
                                hint_text=t("form.hint.id_cr"),
                                text_size=13,
                                border_radius=4,
                                on_change=validate_id_cr_live,
                            ),
                        ],
                        spacing=4,
                    ),
                    ft.Checkbox(
                        ref=id_type_checkbox_ref,
                        label=t("form.chk.is_cr"),
                        value=False,
                        on_change=update_id_type_display,
                    ),
                    ft.Column(
                        controls=[
                            ft.Text(_flabel("id_type"), size=12, weight=ft.FontWeight.W_500, color=colors["text_secondary"]),
                            ft.TextField(
                                ref=id_type_display_ref,
                                value="ID",
                                read_only=True,
                                text_size=13,
                                border_radius=4,
                            ),
                        ],
                        spacing=4,
                    ),
                    ft.Column(
                        controls=[
                            ft.Text(_flabel("account_membership"), size=12, weight=ft.FontWeight.W_500, color=colors["text_secondary"]),
                            ft.TextField(
                                ref=account_ref,
                                hint_text=t("form.hint.account"),
                                text_size=13,
                                border_radius=4,
                                on_change=validate_account_live,
                                on_blur=update_account_intel,
                            ),
                            ft.Container(ref=account_intel_ref, visible=False,
                                         border_radius=4, padding=8),
                        ],
                        spacing=4,
                    ),
                    ft.Checkbox(
                        ref=acc_membership_ref,
                        label=t("form.chk.is_membership"),
                        value=False,
                        on_change=update_relationship_display,
                    ),
                    ft.Column(
                        controls=[
                            ft.Text(_flabel("relationship"), size=12, weight=ft.FontWeight.W_500, color=colors["text_secondary"]),
                            ft.TextField(
                                ref=relationship_ref,
                                value="Current Account",
                                read_only=True,
                                text_size=13,
                                border_radius=4,
                            ),
                        ],
                        spacing=4,
                    ),
                    ft.Column(
                        controls=[
                            ft.Text(_flabel("branch_id"), size=12, weight=ft.FontWeight.W_500, color=colors["text_secondary"]),
                            ft.TextField(
                                ref=branch_ref,
                                hint_text=t("form.hint.branch"),
                                text_size=13,
                                border_radius=4,
                            ),
                        ],
                        spacing=4,
                    ),
                ],
                spacing=12,
                scroll=ft.ScrollMode.AUTO,
            ),
            padding=12,
        )

    def build_suspicion_details_tab():
        """Build Suspicion Details tab."""
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Column(
                        controls=[
                            ft.Text(_flabel("first_reason_for_suspicion"), size=12, weight=ft.FontWeight.W_500, color=colors["text_secondary"]),
                            ft.TextField(
                                ref=first_reason_ref,
                                hint_text=t("form.hint.first_reason"),
                                multiline=True,
                                min_lines=3,
                                max_lines=5,
                                text_size=13,
                                border_radius=4,
                            ),
                        ],
                        spacing=4,
                    ),
                    ft.Column(
                        controls=[
                            ft.Text(_flabel("second_reason_for_suspicion"), size=12, weight=ft.FontWeight.W_500, color=colors["text_secondary"]),
                            # Second reason is a PICK from the FIU's standard suspicion-
                            # reason list (searchable). First reason stays free-text.
                            searchable_dropdown(
                                ref=second_reason_ref,
                                options=[ft.dropdown.Option(key=_v, text=_l) for _v, _l in second_reasons],
                                text_size=13,
                                border_radius=4,
                            ),
                        ],
                        spacing=4,
                    ),
                    ft.Column(
                        controls=[
                            ft.Text(_flabel("type_of_suspected_transaction"), size=12, weight=ft.FontWeight.W_500, color=colors["text_secondary"]),
                            searchable_dropdown(
                                ref=transaction_type_ref,
                                options=[ft.dropdown.Option(key="", text="-- Select --")] + [ft.dropdown.Option(key=_v, text=_l) for _v, _l in transaction_types],
                                text_size=13,
                                border_radius=4,
                            ),
                        ],
                        spacing=4,
                    ),
                    ft.Column(
                        controls=[
                            ft.Text(_flabel("arb_staff"), size=12, weight=ft.FontWeight.W_500, color=colors["text_secondary"]),
                            searchable_dropdown(
                                ref=arb_staff_ref,
                                options=[ft.dropdown.Option(key=_v, text=_l) for _v, _l in arb_staff_values],
                                text_size=13,
                                border_radius=4,
                            ),
                        ],
                        spacing=4,
                    ),
                    ft.Column(
                        controls=[
                            ft.Text(_flabel("total_transaction"), size=12, weight=ft.FontWeight.W_500, color=colors["text_secondary"]),
                            ft.TextField(
                                ref=total_transaction_ref,
                                hint_text=t("form.hint.total"),
                                text_size=13,
                                border_radius=4,
                            ),
                        ],
                        spacing=4,
                    ),
                ],
                spacing=16,
                scroll=ft.ScrollMode.AUTO,
            ),
            padding=12,
        )

    def build_classification_tab():
        """Build Classification & Source tab."""
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Column(
                        controls=[
                            ft.Text(_flabel("report_classification"), size=12, weight=ft.FontWeight.W_500, color=colors["text_secondary"]),
                            searchable_dropdown(
                                ref=classification_ref,
                                options=[ft.dropdown.Option(key="", text="-- Select --")] + [ft.dropdown.Option(key=_v, text=_l) for _v, _l in classifications],
                                text_size=13,
                                border_radius=4,
                            ),
                        ],
                        spacing=4,
                    ),
                    ft.Column(
                        controls=[
                            ft.Text(_flabel("report_source"), size=12, weight=ft.FontWeight.W_500, color=colors["text_secondary"]),
                            searchable_dropdown(
                                ref=report_source_ref,
                                options=[ft.dropdown.Option(key="", text="-- Select --")] + [ft.dropdown.Option(key=_v, text=_l) for _v, _l in report_sources],
                                text_size=13,
                                border_radius=4,
                            ),
                        ],
                        spacing=4,
                    ),
                    ft.Column(
                        controls=[
                            ft.Text(_flabel("reporting_entity"), size=12, weight=ft.FontWeight.W_500, color=colors["text_secondary"]),
                            searchable_dropdown(
                                ref=reporting_entity_ref,
                                options=[ft.dropdown.Option(key="", text="-- Select --")] + [ft.dropdown.Option(key=_v, text=_l) for _v, _l in reporting_entities],
                                text_size=13,
                                border_radius=4,
                            ),
                        ],
                        spacing=4,
                    ),
                    ft.Column(
                        controls=[
                            ft.Text(_flabel("reporter_initials"), size=12, weight=ft.FontWeight.W_500, color=colors["text_secondary"]),
                            ft.TextField(
                                ref=reporter_initials_ref,
                                hint_text=t("form.hint.initials"),
                                max_length=2,
                                text_size=13,
                                border_radius=4,
                                on_change=validate_initials_live,
                            ),
                        ],
                        spacing=4,
                    ),
                    create_date_picker(
                        label=_flabel("sending_date"),
                        ref=sending_date_ref,
                        page=page,
                        hint_text=t("form.hint.date_optional"),
                    ),
                ],
                spacing=16,
                scroll=ft.ScrollMode.AUTO,
            ),
            padding=12,
        )

    def build_fiu_details_tab():
        """Build FIU Details tab."""
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Column(
                        controls=[
                            ft.Text(_flabel("fiu_number"), size=12, weight=ft.FontWeight.W_500, color=colors["text_secondary"]),
                            ft.TextField(
                                ref=fiu_number_ref,
                                hint_text=t("form.hint.fiu_number"),
                                text_size=13,
                                border_radius=4,
                            ),
                        ],
                        spacing=4,
                    ),
                    create_date_picker(
                        label=_flabel("fiu_date"),
                        ref=fiu_date_ref,
                        page=page,
                        hint_text=t("form.hint.date_optional"),
                    ),
                    create_date_picker(
                        label=_flabel("fiu_letter_receive_date"),
                        ref=fiu_receive_date_ref,
                        page=page,
                        hint_text=t("form.hint.date_optional"),
                    ),
                    ft.Column(
                        controls=[
                            ft.Text(_flabel("fiu_feedback"), size=12, weight=ft.FontWeight.W_500, color=colors["text_secondary"]),
                            searchable_dropdown(
                                ref=fiu_feedback_ref,
                                options=[ft.dropdown.Option(key="", text="-- Select --")] + [ft.dropdown.Option(key=_v, text=_l) for _v, _l in fiu_feedbacks],
                                text_size=13,
                                border_radius=4,
                            ),
                        ],
                        spacing=4,
                    ),
                    ft.Column(
                        controls=[
                            ft.Text(_flabel("fiu_letter_number"), size=12, weight=ft.FontWeight.W_500, color=colors["text_secondary"]),
                            ft.TextField(
                                ref=fiu_letter_number_ref,
                                hint_text=t("form.hint.fiu_letter"),
                                text_size=13,
                                border_radius=4,
                            ),
                        ],
                        spacing=4,
                    ),
                ],
                spacing=16,
                scroll=ft.ScrollMode.AUTO,
            ),
            padding=12,
        )

    # Header with badges
    header_controls = [
        ft.Text(
            t("form.edit_title") if is_edit_mode else t("form.new_title"),
            size=15,
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
                border_radius=4,
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
                border_radius=4,
                padding=ft.padding.symmetric(horizontal=12, vertical=4),
            )
        )

    # Build tabs content
    tabs = ft.Tabs(
        selected_index=0,
        animation_duration=300,
        tabs=[
            ft.Tab(text=t("form.tab.basic"), content=build_basic_info_tab()),
            ft.Tab(text=t("form.tab.entity"), content=build_entity_details_tab()),
            ft.Tab(text=t("form.tab.suspicion"), content=build_suspicion_details_tab()),
            ft.Tab(text=t("form.tab.classification"), content=build_classification_tab()),
            ft.Tab(text=t("form.tab.fiu"), content=build_fiu_details_tab()),
        ],
        expand=True,
    )

    # Action buttons FLOAT over the form (Stack) — no reserved footer band / no
    # island background behind them, so the form gets that vertical space back.
    left_buttons = []
    if is_edit_mode and report_data:
        left_buttons.append(
            ft.TextButton(t("form.view_history"), icon=ft.Icons.HISTORY, on_click=view_history)
        )

    right_buttons = [
        ft.TextButton("Cancel", icon=ft.Icons.CLOSE, on_click=close_dialog),
        app_button(t("form.save"), icon=ft.Icons.SAVE, on_click=save_report, variant="ghost"),
    ]
    # Submit for approval (non-admin, editable states only)
    if is_edit_mode and report_data:
        approval_status = report_data.get('approval_status', 'draft')
        is_admin = current_user and current_user.get('role') == 'admin'
        if not is_admin and approval_status not in ['pending_approval', 'approved']:
            right_buttons.append(
                app_button(t("form.submit"), icon=ft.Icons.CHECK_CIRCLE,
                           on_click=submit_for_approval, variant="ghost")
            )

    # Inline error message — no background box, just red text (shown on validation fail)
    error_banner = ft.Container(
        ref=error_banner_ref,
        content=ft.Row(
            controls=[
                ft.Icon(ft.Icons.ERROR_OUTLINE, color=colors["danger"], size=16),
                ft.Text("", color=colors["danger"], expand=True, size=12),
                ft.IconButton(
                    icon=ft.Icons.CLOSE,
                    icon_color=colors["danger"],
                    icon_size=14,
                    on_click=lambda e: hide_error_banner(),
                ),
            ],
            spacing=6,
        ),
        visible=False,
    )

    # #11: when a supervisor returns a report for rework, the agent must SEE why,
    # front-and-center, the moment they open it — not buried in an approvals log.
    rework_banner = None
    if is_edit_mode and report_data and report_data.get('approval_status') == 'rework':
        rc = app_state.approval_service.get_review_comment(
            report_data.get('report_id') or report_data.get('id'))
        if rc and rc.get('comment'):
            rework_banner = ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.ASSIGNMENT_RETURN, color=colors["danger"], size=20),
                        ft.Column(
                            controls=[
                                ft.Text(f"Returned for rework by {rc.get('reviewer') or 'reviewer'}",
                                        weight=ft.FontWeight.BOLD, size=13, color=colors["danger"]),
                                ft.Text(rc["comment"], size=13, color=colors["text_primary"],
                                        selectable=True),
                            ],
                            spacing=2, expand=True,
                        ),
                    ],
                    spacing=10, vertical_alignment=ft.CrossAxisAlignment.START,
                ),
                bgcolor=ft.Colors.with_opacity(0.10, colors["danger"]),
                border=ft.border.all(1, colors["danger"]),
                border_radius=6,
                padding=ft.padding.symmetric(10, 14),
            )

    # The form fills the whole surface; the bottom padding reserves a thin strip
    # so the last field never hides under the floating buttons.
    form_area = ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(controls=header_controls, spacing=8),
                *([rework_banner] if rework_banner else []),
                tabs,
                error_banner,
            ],
            spacing=14,
            expand=True,
        ),
        padding=ft.padding.only(left=28, right=28, top=24, bottom=58),
        expand=True,
    )

    stack_controls = [
        form_area,
        # right-aligned buttons floating at the bottom, transparent background
        ft.Container(
            content=ft.Row(controls=right_buttons, spacing=8, tight=True),
            right=24, bottom=14,
        ),
    ]
    if left_buttons:
        stack_controls.append(
            ft.Container(content=ft.Row(controls=left_buttons, spacing=8, tight=True),
                         left=24, bottom=14)
        )

    dialog_content = ft.Container(
        content=ft.Stack(controls=stack_controls, expand=True),
        width=1080,
        height=720,
        bgcolor=colors["bg_secondary"],
        border_radius=6,
    )

    # Opaque scrim so the app header/footer behind does NOT show through
    dialog = ft.AlertDialog(
        modal=True,
        content=dialog_content,
        content_padding=0,
        bgcolor=colors["bg_secondary"],
        barrier_color=ft.Colors.with_opacity(0.55, "#000000"),
        shape=ft.RoundedRectangleBorder(radius=6),
    )

    # Add-report gate (Task 5): a user must hold at least one reserved number
    # before the create form is allowed to open.
    if not is_edit_mode and report_number_service and current_user:
        if report_number_service.get_available_count(current_user['username']) < 1:
            # Dialog isn't mounted to page.overlay yet, so show_error_dialog
            # (which targets error_banner_ref.current) would silently no-op.
            # Use a toast instead — it works pre-mount.
            from components.toast import show_error
            show_error(page, t("form.err.no_reserved"))
            return

    # Record-edit lock (R28): one editor per report. Acquire before opening in
    # edit mode; if another user holds it, refuse and tell the user who.
    if is_edit_mode and report_data:
        _rid = report_data.get('report_id') or report_data.get('id')
        if _rid:
            acquired, holder, _msg = report_service.acquire_edit_lock(_rid)
            if not acquired:
                show_error_dialog(f"This report is currently being edited by {holder or 'another user'}")
                return

    # Show dialog
    page.overlay.append(dialog)
    dialog.open = True
    page.update()

    # Load data or reserve numbers
    if is_edit_mode:
        load_report_data()
    else:
        reserve_numbers()
