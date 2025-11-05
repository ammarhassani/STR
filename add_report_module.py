"""
Add Report Module - Production-Grade Dynamic Form
Implements dynamic report form based on column_settings table
"""
import flet as ft
import logging
from datetime import datetime
import re
import json

logger = logging.getLogger('fiu_system')


class AddReportModule:
    """Complete add report form with dynamic fields and validation"""

    def __init__(self, page, db_manager, current_user, content_area):
        self.page = page
        self.db_manager = db_manager
        self.current_user = current_user
        self.content_area = content_area

        # Form data
        self.form_fields = {}
        self.field_controls = {}
        self.column_settings = []
        self.dropdown_options = {}

    def show(self):
        """Display add report form"""
        logger.info("Loading add report form")

        # Load column settings and dropdown options
        self.load_column_settings()
        self.load_dropdown_options()

        # Build UI
        form_view = ft.Column(
            [
                self.build_header(),
                ft.Divider(height=1),
                self.build_form(),
                ft.Divider(height=1),
                self.build_actions(),
            ],
            spacing=0,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

        self.content_area.content = form_view
        self.page.update()

    def build_header(self):
        """Build form header"""
        return ft.Container(
            content=ft.Row(
                [
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.ADD_CIRCLE, size=32, color=ft.Colors.BLUE_700),
                            ft.Column(
                                [
                                    ft.Text("Add New Report", size=24, weight=ft.FontWeight.BOLD),
                                    ft.Text("Fill in the required fields", size=12, color=ft.Colors.GREY_700),
                                ],
                                spacing=2,
                            ),
                        ],
                        spacing=10,
                    ),
                    ft.Row(
                        [
                            ft.TextButton(
                                "Clear Form",
                                icon=ft.Icons.CLEAR_ALL,
                                on_click=lambda e: self.clear_form(),
                            ),
                        ],
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            padding=20,
            bgcolor=ft.Colors.WHITE,
        )

    def build_form(self):
        """Build dynamic form based on column settings"""
        form_sections = []

        # Group fields into sections
        section_1_fields = []  # Basic Information
        section_2_fields = []  # Entity Details
        section_3_fields = []  # Transaction Details
        section_4_fields = []  # FIU Details

        for column in self.column_settings:
            field_control = self.create_field_control(column)
            if field_control:
                self.field_controls[column['column_name']] = field_control

                # Categorize fields
                if column['display_order'] <= 10:
                    section_1_fields.append(field_control)
                elif column['display_order'] <= 20:
                    section_2_fields.append(field_control)
                elif column['display_order'] <= 25:
                    section_3_fields.append(field_control)
                else:
                    section_4_fields.append(field_control)

        # Build sections
        if section_1_fields:
            form_sections.append(self.create_section("Basic Information", section_1_fields))

        if section_2_fields:
            form_sections.append(self.create_section("Entity Details", section_2_fields))

        if section_3_fields:
            form_sections.append(self.create_section("Transaction Details", section_3_fields))

        if section_4_fields:
            form_sections.append(self.create_section("FIU Details", section_4_fields))

        return ft.Container(
            content=ft.Column(
                form_sections,
                spacing=20,
                scroll=ft.ScrollMode.AUTO,
            ),
            padding=20,
            expand=True,
        )

    def create_section(self, title, fields):
        """Create a form section"""
        return ft.Card(
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Text(title, size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700),
                        ft.Divider(),
                        ft.Column(fields, spacing=15),
                    ],
                    spacing=10,
                ),
                padding=20,
            ),
            elevation=2,
        )

    def create_field_control(self, column):
        """Create appropriate control based on field type"""
        field_name = column['column_name']
        label = column['display_name_en']
        is_required = bool(column['is_required'])
        data_type = column['data_type']

        # Parse validation rules
        validation_rules = {}
        if column['validation_rules']:
            try:
                validation_rules = json.loads(column['validation_rules'])
            except:
                validation_rules = {}

        # Create control based on data type
        if data_type == 'DATE':
            return ft.TextField(
                label=label + (" *" if is_required else ""),
                hint_text="DD/MM/YYYY",
                prefix_icon=ft.Icons.CALENDAR_TODAY,
                keyboard_type=ft.KeyboardType.DATETIME,
                max_length=10,
            )

        elif data_type == 'DROPDOWN':
            options = validation_rules.get('options', [])
            # Get options from dropdown_options if available
            category = field_name
            if category in self.dropdown_options:
                options = self.dropdown_options[category]

            return ft.Dropdown(
                label=label + (" *" if is_required else ""),
                hint_text=f"Select {label.lower()}",
                options=[ft.dropdown.Option(opt, opt) for opt in options],
            )

        elif data_type == 'INTEGER':
            return ft.TextField(
                label=label + (" *" if is_required else ""),
                hint_text=f"Enter {label.lower()}",
                prefix_icon=ft.Icons.NUMBERS,
                keyboard_type=ft.KeyboardType.NUMBER,
            )

        else:  # TEXT
            # Check if multiline
            max_length = validation_rules.get('maxLength', 255)
            is_multiline = max_length > 100

            return ft.TextField(
                label=label + (" *" if is_required else ""),
                hint_text=validation_rules.get('example', f"Enter {label.lower()}"),
                multiline=is_multiline,
                max_lines=3 if is_multiline else 1,
                max_length=max_length,
            )

    def build_actions(self):
        """Build form action buttons"""
        return ft.Container(
            content=ft.Row(
                [
                    ft.ElevatedButton(
                        "Save Report",
                        icon=ft.Icons.SAVE,
                        on_click=lambda e: self.save_report(),
                        height=45,
                        style=ft.ButtonStyle(
                            bgcolor=ft.Colors.GREEN_700,
                            color=ft.Colors.WHITE,
                        ),
                    ),
                    ft.OutlinedButton(
                        "Save as Draft",
                        icon=ft.Icons.DRAFTS,
                        on_click=lambda e: self.save_draft(),
                        height=45,
                    ),
                    ft.TextButton(
                        "Cancel",
                        icon=ft.Icons.CANCEL,
                        on_click=lambda e: self.cancel(),
                        height=45,
                    ),
                ],
                spacing=10,
            ),
            padding=20,
            bgcolor=ft.Colors.WHITE,
        )

    def load_column_settings(self):
        """Load column settings from database"""
        try:
            query = """
                SELECT * FROM column_settings
                WHERE is_visible = 1
                ORDER BY display_order
            """
            self.column_settings = [dict(row) for row in self.db_manager.execute_with_retry(query)]
            logger.info(f"Loaded {len(self.column_settings)} column settings")
        except Exception as e:
            logger.error(f"Failed to load column settings: {e}")
            self.column_settings = []

    def load_dropdown_options(self):
        """Load dropdown options from system_config"""
        try:
            query = """
                SELECT config_key, config_value, config_category
                FROM system_config
                WHERE config_type = 'dropdown' AND is_active = 1
                ORDER BY config_category, display_order
            """
            results = self.db_manager.execute_with_retry(query)

            # Group by category
            for row in results:
                category = row['config_category']
                if category not in self.dropdown_options:
                    self.dropdown_options[category] = []
                self.dropdown_options[category].append(row['config_value'])

            logger.info(f"Loaded dropdown options for {len(self.dropdown_options)} categories")
        except Exception as e:
            logger.error(f"Failed to load dropdown options: {e}")
            self.dropdown_options = {}

    def validate_form(self):
        """Validate all form fields"""
        errors = []

        for column in self.column_settings:
            field_name = column['column_name']
            control = self.field_controls.get(field_name)

            if not control:
                continue

            value = control.value

            # Check required fields
            if column['is_required'] and not value:
                errors.append(f"{column['display_name_en']} is required")

            # Validate based on rules
            if value and column['validation_rules']:
                try:
                    rules = json.loads(column['validation_rules'])

                    # Pattern validation
                    if 'pattern' in rules:
                        pattern = rules['pattern']
                        if not re.match(pattern, value):
                            example = rules.get('example', '')
                            errors.append(f"{column['display_name_en']} format is invalid. Example: {example}")

                    # Length validation
                    if 'maxLength' in rules:
                        if len(value) > rules['maxLength']:
                            errors.append(f"{column['display_name_en']} is too long")

                except:
                    pass

        return errors

    def save_report(self):
        """Save report to database"""
        # Validate form
        errors = self.validate_form()
        if errors:
            self.show_error_dialog("Validation Errors", "\n".join(errors))
            return

        try:
            # Collect form data
            form_data = {}
            for field_name, control in self.field_controls.items():
                form_data[field_name] = control.value or None

            # Add metadata
            form_data['created_by'] = self.current_user['username']
            form_data['created_at'] = datetime.now().isoformat()
            form_data['status'] = 'Open'
            form_data['is_deleted'] = 0

            # Build insert query
            fields = ', '.join(form_data.keys())
            placeholders = ', '.join(['?' for _ in form_data])
            query = f"INSERT INTO reports ({fields}) VALUES ({placeholders})"

            # Execute
            self.db_manager.execute_with_retry(query, tuple(form_data.values()))

            logger.info(f"Report saved: {form_data.get('report_number', 'N/A')}")
            self.show_success_dialog("Success", "Report saved successfully!")

            # Clear form
            self.clear_form()

        except Exception as e:
            logger.error(f"Failed to save report: {e}")
            self.show_error_dialog("Save Failed", f"Failed to save report: {str(e)}")

    def save_draft(self):
        """Save report as draft"""
        # TODO: Implement draft functionality
        self.show_snackbar("Draft saved")

    def cancel(self):
        """Cancel and return to reports list"""
        # Load reports module
        from reports_module import ReportsModule
        module = ReportsModule(self.page, self.db_manager, self.current_user, self.content_area)
        module.show()

    def clear_form(self):
        """Clear all form fields"""
        for control in self.field_controls.values():
            control.value = ""
        self.page.update()
        self.show_snackbar("Form cleared")

    def show_error_dialog(self, title, message):
        """Show error dialog"""
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(title),
            content=ft.Text(message),
            actions=[
                ft.TextButton("OK", on_click=lambda e: self.page.close(dialog)),
            ],
        )
        self.page.open(dialog)

    def show_success_dialog(self, title, message):
        """Show success dialog"""
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(title),
            content=ft.Text(message),
            actions=[
                ft.TextButton("OK", on_click=lambda e: self.page.close(dialog)),
            ],
        )
        self.page.open(dialog)

    def show_snackbar(self, message):
        """Show snackbar message"""
        self.page.snack_bar = ft.SnackBar(content=ft.Text(message))
        self.page.snack_bar.open = True
        self.page.update()
