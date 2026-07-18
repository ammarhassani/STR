"""
Field Validation Management View for FIU Report Management System.
Admin panel for managing field validation rules and required status.
"""
import flet as ft
from components.overlay import (mount as _overlay_mount,
                                dismiss as _overlay_dismiss)
from components.searchable_dropdown import searchable_dropdown
import asyncio
from typing import Any, Dict, List

from theme.theme_manager import theme_manager
from i18n import t
from components.toast import show_success, show_error


def build_field_management_view(page: ft.Page, app_state: Any) -> ft.Column:
    """
    Build the field validation management view.

    Args:
        page: Flet page object
        app_state: Application state

    Returns:
        Field management column
    """
    colors = theme_manager.get_colors()

    # State
    field_settings = []
    is_loading = True

    # Refs
    loading_ref = ft.Ref[ft.Container]()
    table_ref = ft.Ref[ft.Container]()

    async def load_fields():
        """Load all field settings from database."""
        nonlocal field_settings, is_loading

        is_loading = True
        if loading_ref.current:
            loading_ref.current.visible = True
        if table_ref.current:
            table_ref.current.visible = False
        page.update()

        try:
            loop = asyncio.get_event_loop()

            def fetch_fields():
                if app_state.validation_service:
                    return app_state.validation_service.get_all_field_settings()
                return []

            field_settings = await loop.run_in_executor(None, fetch_fields)
            update_table_ui()

        except Exception as e:
            print(f"Error loading fields: {e}")
            show_error(page, f"Error loading fields: {str(e)}")

        finally:
            is_loading = False
            if loading_ref.current:
                loading_ref.current.visible = False
            if table_ref.current:
                table_ref.current.visible = True
            page.update()

    def update_table_ui():
        """Update table with current data."""
        if table_ref.current:
            table_ref.current.content = build_table()
        page.update()

    def format_rules(field_name: str, rules: Dict) -> str:
        """Format validation rules for display."""
        if not rules:
            return "No rules defined"

        parts = []

        # Handle special fields first
        if field_name == 'id_cr':
            if 'length' in rules:
                parts.append(f"Length: {rules['length']} digits")
            if 'saudi_starts_with' in rules:
                parts.append(f"Saudi ID starts: {rules['saudi_starts_with']}")
            if 'cr_starts_with' in rules:
                parts.append(f"CR starts: {rules['cr_starts_with']}")
            return " | ".join(parts) if parts else "Default ID/CR validation"

        elif field_name == 'account_membership':
            if 'account_length' in rules:
                parts.append(f"Account: {rules['account_length']} digits")
            if 'membership_length' in rules:
                parts.append(f"Membership: {rules['membership_length']} digits")
            return " | ".join(parts) if parts else "Default account validation"

        # Generic field rules
        if rules.get('required'):
            parts.append(t("fld.required"))
        if 'pattern' in rules:
            parts.append(f"Pattern: {rules.get('example', rules['pattern'][:20])}")
        if 'maxLength' in rules:
            parts.append(f"Max: {rules['maxLength']} chars")
        if 'minLength' in rules:
            parts.append(f"Min: {rules['minLength']} chars")
        if 'length' in rules:
            parts.append(f"Length: {rules['length']}")
        if rules.get('type') == 'numeric':
            parts.append("Numeric")
        elif rules.get('type') == 'integer':
            parts.append("Integer")
        if 'min' in rules:
            parts.append(f"Min value: {rules['min']}")
        if 'max' in rules:
            parts.append(f"Max value: {rules['max']}")

        return " | ".join(parts) if parts else "Default validation"

    def build_table() -> ft.Control:
        """Build the fields data table."""
        if not field_settings:
            return ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Icon(ft.Icons.TUNE, size=48, color=colors["text_muted"]),
                        ft.Text(t("fld.none"), color=colors["text_muted"]),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                expand=True,
                alignment=ft.alignment.center,
            )

        # Build data rows
        rows = []
        for field in field_settings:
            # Required status
            is_required = field.get('is_required', False)
            required_color = colors["success"] if is_required else colors["text_muted"]
            required_text = "Yes" if is_required else "No"

            # Format rules
            rules_text = format_rules(field.get('column_name', ''), field.get('validation_rules', {}))

            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(field.get('display_name_en', ''), size=12, color=colors["text_primary"])),
                        ft.DataCell(
                            ft.Text(required_text, size=12, color=required_color, weight=ft.FontWeight.BOLD)
                        ),
                        ft.DataCell(
                            ft.Text(
                                rules_text[:50] + '...' if len(rules_text) > 50 else rules_text,
                                size=11,
                                color=colors["text_secondary"],
                                tooltip=rules_text,
                            )
                        ),
                        ft.DataCell(ft.Text(field.get('updated_by', 'System') or 'System', size=12, color=colors["text_secondary"])),
                        ft.DataCell(
                            ft.IconButton(
                                icon=ft.Icons.EDIT,
                                icon_color=colors["primary"],
                                tooltip="Edit validation rules",
                                on_click=lambda e, f=field: show_edit_dialog(f),
                            )
                        ),
                    ],
                )
            )

        columns = [
            ft.DataColumn(ft.Text(t("fld.col.name"), weight=ft.FontWeight.BOLD, size=12, color=colors["text_primary"])),
            ft.DataColumn(ft.Text(t("fld.col.required"), weight=ft.FontWeight.BOLD, size=12, color=colors["text_primary"])),
            ft.DataColumn(ft.Text(t("fld.col.validation"), weight=ft.FontWeight.BOLD, size=12, color=colors["text_primary"])),
            ft.DataColumn(ft.Text(t("fld.col.updated_by"), weight=ft.FontWeight.BOLD, size=12, color=colors["text_primary"])),
            ft.DataColumn(ft.Text(t("common.actions"), weight=ft.FontWeight.BOLD, size=12, color=colors["text_primary"])),
        ]

        return ft.DataTable(
            columns=columns,
            rows=rows,
            column_spacing=20,
            horizontal_lines=ft.BorderSide(1, colors["border"]),
            heading_row_color=colors["bg_tertiary"],
            data_row_color={
                ft.ControlState.HOVERED: colors["hover"],
            },
            border_radius=4,
        )

    def show_edit_dialog(field: Dict):
        """Show dialog to edit field validation rules."""
        field_name = field.get('column_name', '')
        display_name = field.get('display_name_en', '')
        rules = field.get('validation_rules', {}) or {}
        is_required = field.get('is_required', False)

        # Required checkbox
        required_checkbox = ft.Checkbox(
            label=t("fld.mark_required"),
            value=is_required,
        )

        # Build rules inputs based on field type
        rules_controls = []

        if field_name == 'id_cr':
            length_input = ft.TextField(
                label=t("fld.length"),
                value=str(rules.get('length', 10)),
                keyboard_type=ft.KeyboardType.NUMBER,
                width=120,
            )
            saudi_input = ft.TextField(
                label=t("fld.id_starts"),
                value=str(rules.get('saudi_starts_with', '1')),
                keyboard_type=ft.KeyboardType.NUMBER,
                width=120,
            )
            cr_input = ft.TextField(
                label=t("fld.cr_starts"),
                value=str(rules.get('cr_starts_with', '7')),
                keyboard_type=ft.KeyboardType.NUMBER,
                width=120,
            )

            rules_controls = [
                ft.Text(t("fld.idcr_rules"), weight=ft.FontWeight.BOLD, size=13),
                ft.Container(height=8),
                ft.Row(controls=[length_input, saudi_input, cr_input], spacing=12, wrap=True),
                ft.Container(height=4),
                ft.Text(
                    "Length: Total digits for both ID and CR\n"
                    "Saudi ID: Starting digit for Saudi Arabian IDs\n"
                    "CR: Starting digit for Commercial Registration numbers",
                    size=11,
                    color=colors["text_muted"],
                ),
            ]

            def get_rules():
                return {
                    'length': int(length_input.value or 10),
                    'pattern': f"^[0-9]{{{length_input.value or 10}}}$",
                    'saudi_starts_with': saudi_input.value or '1',
                    'cr_starts_with': cr_input.value or '7',
                }

        elif field_name == 'account_membership':
            account_input = ft.TextField(
                label=t("fld.account_length"),
                value=str(rules.get('account_length', 21)),
                keyboard_type=ft.KeyboardType.NUMBER,
                width=150,
            )
            membership_input = ft.TextField(
                label=t("fld.membership_length"),
                value=str(rules.get('membership_length', 8)),
                keyboard_type=ft.KeyboardType.NUMBER,
                width=150,
            )

            rules_controls = [
                ft.Text(t("fld.acc_rules"), weight=ft.FontWeight.BOLD, size=13),
                ft.Container(height=8),
                ft.Row(controls=[account_input, membership_input], spacing=12),
                ft.Container(height=4),
                ft.Text(
                    "Account: Number of digits for bank account numbers\n"
                    "Membership: Number of digits for membership numbers",
                    size=11,
                    color=colors["text_muted"],
                ),
            ]

            def get_rules():
                return {
                    'account_length': int(account_input.value or 21),
                    'membership_length': int(membership_input.value or 8),
                }

        else:
            # Generic field validation - show common rule inputs
            pattern_input = ft.TextField(
                label="Pattern (regex)",
                value=str(rules.get('pattern', '')),
                hint_text="e.g., ^[A-Z]{2}[0-9]+$",
                width=300,
            )
            min_length_input = ft.TextField(
                label="Min Length",
                value=str(rules.get('minLength', '')) if rules.get('minLength') else '',
                keyboard_type=ft.KeyboardType.NUMBER,
                width=120,
            )
            max_length_input = ft.TextField(
                label="Max Length",
                value=str(rules.get('maxLength', '')) if rules.get('maxLength') else '',
                keyboard_type=ft.KeyboardType.NUMBER,
                width=120,
            )
            type_dropdown = searchable_dropdown(
                label="Type",
                value=rules.get('type', 'text'),
                options=[
                    ft.dropdown.Option("text", "Text"),
                    ft.dropdown.Option("numeric", "Numeric"),
                    ft.dropdown.Option("integer", "Integer"),
                ],
                width=120,
            )

            rules_controls = [
                ft.Text("Validation Rules", weight=ft.FontWeight.BOLD, size=13),
                ft.Container(height=8),
                ft.Row(controls=[type_dropdown, min_length_input, max_length_input], spacing=12, wrap=True),
                ft.Container(height=8),
                pattern_input,
                ft.Container(height=4),
                ft.Text(
                    "Pattern: Regular expression for value format\n"
                    "Min/Max Length: Character count constraints\n"
                    "Type: Data type (numeric fields only allow numbers)",
                    size=11,
                    color=colors["text_muted"],
                ),
            ]

            def get_rules():
                new_rules = {}
                if pattern_input.value and pattern_input.value.strip():
                    new_rules['pattern'] = pattern_input.value.strip()
                if min_length_input.value and min_length_input.value.strip():
                    try:
                        new_rules['minLength'] = int(min_length_input.value)
                    except ValueError:
                        pass
                if max_length_input.value and max_length_input.value.strip():
                    try:
                        new_rules['maxLength'] = int(max_length_input.value)
                    except ValueError:
                        pass
                if type_dropdown.value and type_dropdown.value != 'text':
                    new_rules['type'] = type_dropdown.value
                return new_rules

        def save_changes(e):
            current_user = app_state.auth_service.get_current_user()
            username = current_user['username'] if current_user else 'admin'

            try:
                # Update validation rules
                new_rules = get_rules()
                success, message = app_state.validation_service.update_validation_rules(
                    field_name,
                    new_rules,
                    username
                )

                if not success:
                    show_error(page, message)
                    return

                # Update required status
                success, message = app_state.validation_service.update_required_status(
                    field_name,
                    required_checkbox.value,
                    username
                )

                if not success:
                    show_error(page, message)
                    return

                dialog.open = False

                _overlay_dismiss(page, dialog)
                page.update()
                show_success(page, f"Validation rules for '{display_name}' updated successfully.")
                page.run_task(load_fields)

            except Exception as ex:
                show_error(page, f"Error saving: {str(ex)}")

        def close_dialog(e):
            dialog.open = False
            _overlay_dismiss(page, dialog)
            page.update()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Edit Validation Rules - {display_name}"),
            content=ft.Column(
                controls=[
                    ft.Text(f"Field: {display_name} ({field_name})", size=12, color=colors["text_secondary"]),
                    ft.Container(height=12),
                    required_checkbox,
                    ft.Divider(),
                    *rules_controls,
                ],
                spacing=4,
                tight=True,
                width=450,
            ),
            actions=[
                ft.TextButton(t("common.cancel"), on_click=close_dialog),
                ft.ElevatedButton(
                    t("common.save"),
                    bgcolor=colors["primary"],
                    color=ft.Colors.WHITE,
                    on_click=save_changes,
                ),
            ],
        )
        _overlay_mount(page, dialog, update=False)
        page.update()

    def handle_refresh(e):
        """Refresh field settings."""
        page.run_task(load_fields)

    # Header row
    header_row = ft.Row(
        controls=[
            ft.Text(
                "Field Validation Management",
                size=18,
                weight=ft.FontWeight.BOLD,
                color=colors["text_primary"],
            ),
            ft.Container(expand=True),
            ft.IconButton(
                icon=ft.Icons.REFRESH,
                icon_color=colors["text_secondary"],
                tooltip="Refresh",
                on_click=handle_refresh,
            ),
        ],
    )

    # Info text
    info_text = ft.Text(
        t("fld.info") + t("fld.info2"),
        size=13,
        color=colors["text_secondary"],
    )

    # Loading indicator
    loading_container = ft.Container(
        ref=loading_ref,
        content=ft.Column(
            controls=[
                ft.ProgressRing(width=32, height=32, color=colors["primary"]),
                ft.Text("Loading field settings...", color=colors["text_secondary"]),
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
    page.run_task(load_fields)

    return ft.Column(
        controls=[
            header_row,
            ft.Container(height=8),
            info_text,
            ft.Container(height=16),
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
                border_radius=4,
                bgcolor=colors["card_bg"],
            ),
        ],
        spacing=0,
        expand=True,
    )
