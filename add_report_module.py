"""
Add Report Module - Production-Grade Dynamic Form (Enhanced)
Implements dynamic report form with date pickers, auto-generation, and validation
"""
import flet as ft
import logging
from datetime import datetime
import re
import json

logger = logging.getLogger('fiu_system')

# Comprehensive nationality list
NATIONALITIES = [
    "Afghan", "Albanian", "Algerian", "American", "Andorran", "Angolan", "Antiguans", "Argentinean", "Armenian",
    "Australian", "Austrian", "Azerbaijani", "Bahamian", "Bahraini", "Bangladeshi", "Barbadian", "Barbudans",
    "Batswana", "Belarusian", "Belgian", "Belizean", "Beninese", "Bhutanese", "Bolivian", "Bosnian", "Brazilian",
    "British", "Bruneian", "Bulgarian", "Burkinabe", "Burmese", "Burundian", "Cambodian", "Cameroonian", "Canadian",
    "Cape Verdean", "Central African", "Chadian", "Chilean", "Chinese", "Colombian", "Comoran", "Congolese",
    "Costa Rican", "Croatian", "Cuban", "Cypriot", "Czech", "Danish", "Djibouti", "Dominican", "Dutch", "East Timorese",
    "Ecuadorean", "Egyptian", "Emirian", "Equatorial Guinean", "Eritrean", "Estonian", "Ethiopian", "Fijian", "Filipino",
    "Finnish", "French", "Gabonese", "Gambian", "Georgian", "German", "Ghanaian", "Greek", "Grenadian", "Guatemalan",
    "Guinea-Bissauan", "Guinean", "Guyanese", "Haitian", "Herzegovinian", "Honduran", "Hungarian", "I-Kiribati",
    "Icelander", "Indian", "Indonesian", "Iranian", "Iraqi", "Irish", "Israeli", "Italian", "Ivorian", "Jamaican",
    "Japanese", "Jordanian", "Kazakhstani", "Kenyan", "Kittian and Nevisian", "Kuwaiti", "Kyrgyz", "Laotian", "Latvian",
    "Lebanese", "Liberian", "Libyan", "Liechtensteiner", "Lithuanian", "Luxembourger", "Macedonian", "Malagasy",
    "Malawian", "Malaysian", "Maldivian", "Malian", "Maltese", "Marshallese", "Mauritanian", "Mauritian", "Mexican",
    "Micronesian", "Moldovan", "Monacan", "Mongolian", "Moroccan", "Mosotho", "Motswana", "Mozambican", "Namibian",
    "Nauruan", "Nepalese", "New Zealander", "Nicaraguan", "Nigerian", "Nigerien", "North Korean", "Northern Irish",
    "Norwegian", "Omani", "Pakistani", "Palauan", "Panamanian", "Papua New Guinean", "Paraguayan", "Peruvian", "Polish",
    "Portuguese", "Qatari", "Romanian", "Russian", "Rwandan", "Saint Lucian", "Salvadoran", "Samoan", "San Marinese",
    "Sao Tomean", "Saudi", "Saudi Arabian", "Scottish", "Senegalese", "Serbian", "Seychellois", "Sierra Leonean",
    "Singaporean", "Slovakian", "Slovenian", "Solomon Islander", "Somali", "South African", "South Korean", "Spanish",
    "Sri Lankan", "Sudanese", "Surinamer", "Swazi", "Swedish", "Swiss", "Syrian", "Taiwanese", "Tajik", "Tanzanian",
    "Thai", "Togolese", "Tongan", "Trinidadian or Tobagonian", "Tunisian", "Turkish", "Tuvaluan", "Ugandan", "Ukrainian",
    "Uruguayan", "Uzbekistani", "Venezuelan", "Vietnamese", "Welsh", "Yemenite", "Zambian", "Zimbabwean"
]


class AddReportModule:
    """Complete add report form with dynamic fields and validation"""

    def __init__(self, page, db_manager, current_user, content_area, edit_mode=False, report_data=None):
        self.page = page
        self.db_manager = db_manager
        self.current_user = current_user
        self.content_area = content_area

        # Edit mode
        self.edit_mode = edit_mode
        self.report_data = report_data or {}

        # Form data
        self.form_fields = {}
        self.field_controls = {}
        self.column_settings = []
        self.dropdown_options = {}

        # Special fields
        self.id_type_checkbox = None
        self.account_type_checkbox = None

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

        # Pre-fill form if in edit mode
        if self.edit_mode and self.report_data:
            self.prefill_form()

        self.content_area.content = form_view
        self.page.update()

    def build_header(self):
        """Build form header"""
        if self.edit_mode:
            icon = ft.Icons.EDIT
            title = f"Edit Report: {self.report_data.get('report_number', 'N/A')}"
            subtitle = "Modify report details below"
        else:
            icon = ft.Icons.ADD_CIRCLE
            title = "Add New Report"
            subtitle = "Report number and serial number will be auto-generated"

        return ft.Container(
            content=ft.Row(
                [
                    ft.Row(
                        [
                            ft.Icon(icon, size=32, color=ft.Colors.BLUE_700),
                            ft.Column(
                                [
                                    ft.Text(title, size=24, weight=ft.FontWeight.BOLD),
                                    ft.Text(subtitle, size=12, color=ft.Colors.GREY_700),
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
            # bgcolor removed for theme compatibility
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
            # Skip auto-generated fields
            if column['column_name'] in ['sn', 'report_number']:
                continue

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

        # Special handling for specific fields
        if field_name == 'nationality':
            return self.create_nationality_field(label, is_required)
        elif field_name == 'id_cr':
            return self.create_id_cr_field(label, is_required)
        elif field_name == 'account_membership':
            return self.create_account_membership_field(label, is_required)

        # Create control based on data type
        if data_type == 'DATE':
            return self.create_date_field(label, is_required, field_name)

        elif data_type == 'DROPDOWN':
            options = self.get_dropdown_options(field_name, validation_rules)
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
            max_length = validation_rules.get('maxLength', 255)
            is_multiline = max_length > 100

            return ft.TextField(
                label=label + (" *" if is_required else ""),
                hint_text=validation_rules.get('example', f"Enter {label.lower()}"),
                multiline=is_multiline,
                max_lines=3 if is_multiline else 1,
                max_length=max_length,
            )

    def create_date_field(self, label, is_required, field_name):
        """Create date field with date picker and TODAY button"""
        date_field = ft.TextField(
            label=label + (" *" if is_required else ""),
            hint_text="DD/MM/YYYY",
            prefix_icon=ft.Icons.CALENDAR_TODAY,
            read_only=True,
            value="",
        )

        def open_date_picker(e):
            def on_date_change(e):
                if e.control.value:
                    date_field.value = e.control.value.strftime("%d/%m/%Y")
                    self.page.update()

            def set_today(e):
                date_field.value = datetime.now().strftime("%d/%m/%Y")
                self.page.close(dialog)
                self.page.update()

            def open_calendar(e):
                date_picker = ft.DatePicker(
                    on_change=on_date_change,
                    on_dismiss=lambda e: None,
                    first_date=datetime(2000, 1, 1),
                    last_date=datetime(2100, 12, 31),
                )
                self.page.overlay.append(date_picker)
                self.page.update()
                date_picker.pick_date()

            def close_dialog(e):
                self.page.close(dialog)

            dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text(f"Select {label}"),
                content=ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("Choose an option:", size=14),
                            ft.Container(height=10),
                            ft.ElevatedButton(
                                "Open Calendar Picker",
                                icon=ft.Icons.CALENDAR_MONTH,
                                on_click=open_calendar,
                                width=200,
                            ),
                            ft.Container(height=10),
                            ft.ElevatedButton(
                                "Use TODAY",
                                icon=ft.Icons.TODAY,
                                on_click=set_today,
                                width=200,
                                style=ft.ButtonStyle(
                                    bgcolor=ft.Colors.GREEN_700,
                                    color=ft.Colors.WHITE,
                                ),
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        tight=True,
                    ),
                    width=300,
                ),
                actions=[
                    ft.TextButton("Cancel", on_click=close_dialog),
                ],
            )

            self.page.open(dialog)

        date_field.on_click = open_date_picker

        return date_field

    def create_nationality_field(self, label, is_required):
        """Create searchable nationality dropdown"""
        return ft.Dropdown(
            label=label + (" *" if is_required else ""),
            hint_text="Select or search nationality",
            options=[ft.dropdown.Option(nat, nat) for nat in sorted(NATIONALITIES)],
        )

    def create_id_cr_field(self, label, is_required):
        """Create ID/CR field with type selector"""
        self.id_type_checkbox = ft.Checkbox(
            label="Commercial Registration (CR)",
            value=False,
        )

        id_field = ft.TextField(
            label=label + (" *" if is_required else ""),
            hint_text="Enter ID or CR number",
            prefix_icon=ft.Icons.BADGE,
        )

        return ft.Column(
            [
                self.id_type_checkbox,
                id_field,
            ],
            spacing=10,
        )

    def create_account_membership_field(self, label, is_required):
        """Create Account/Membership field with type selector"""
        self.account_type_checkbox = ft.Checkbox(
            label="Membership (not Account)",
            value=False,
        )

        account_field = ft.TextField(
            label=label + (" *" if is_required else ""),
            hint_text="Enter account or membership number",
            prefix_icon=ft.Icons.ACCOUNT_CIRCLE,
        )

        return ft.Column(
            [
                self.account_type_checkbox,
                account_field,
            ],
            spacing=10,
        )

    def get_dropdown_options(self, field_name, validation_rules):
        """Get dropdown options from database or validation rules"""
        options = validation_rules.get('options', [])

        # Try to get from dropdown_options (loaded from system_config)
        if field_name in self.dropdown_options:
            options = self.dropdown_options[field_name]

        return options

    def build_actions(self):
        """Build form action buttons"""
        button_text = "Update Report" if self.edit_mode else "Save Report"

        return ft.Container(
            content=ft.Row(
                [
                    ft.ElevatedButton(
                        button_text,
                        icon=ft.Icons.SAVE,
                        on_click=lambda e: self.save_report(),
                        height=45,
                        style=ft.ButtonStyle(
                            bgcolor=ft.Colors.GREEN_700,
                            color=ft.Colors.WHITE,
                        ),
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
            # bgcolor removed for theme compatibility
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

    def generate_next_sn(self):
        """Generate next serial number"""
        try:
            query = "SELECT MAX(sn) as max_sn FROM reports"
            result = self.db_manager.execute_with_retry(query)
            max_sn = result[0]['max_sn'] if result[0]['max_sn'] else 0
            return max_sn + 1
        except Exception as e:
            logger.error(f"Failed to generate SN: {e}")
            return 1

    def generate_report_number(self):
        """Generate unique report number in format YYYY/MM/NNN"""
        try:
            now = datetime.now()
            year = now.strftime("%Y")
            month = now.strftime("%m")

            # Get count of reports this month
            query = "SELECT COUNT(*) as count FROM reports WHERE report_number LIKE ?"
            pattern = f"{year}/{month}/%"
            result = self.db_manager.execute_with_retry(query, (pattern,))
            count = result[0]['count'] + 1

            return f"{year}/{month}/{count:03d}"
        except Exception as e:
            logger.error(f"Failed to generate report number: {e}")
            return f"{datetime.now().strftime('%Y/%m')}/001"

    def validate_form(self):
        """Validate all form fields"""
        errors = []

        for column in self.column_settings:
            # Skip auto-generated fields
            if column['column_name'] in ['sn', 'report_number']:
                continue

            field_name = column['column_name']
            control = self.field_controls.get(field_name)

            if not control:
                continue

            # Handle special fields
            if isinstance(control, ft.Column):
                # Get the text field from column (for ID/CR and Account/Membership)
                text_control = control.controls[1] if len(control.controls) > 1 else None
                value = text_control.value if text_control else None
            else:
                value = control.value

            # Check required fields
            if column['is_required'] and not value:
                errors.append(f"{column['display_name_en']} is required")

        return errors

    def save_report(self):
        """Save report to database (INSERT or UPDATE based on edit_mode)"""
        # Validate form
        errors = self.validate_form()
        if errors:
            self.show_error_dialog("Validation Errors", "\n".join(errors))
            return

        try:
            # Collect form data
            form_data = {}

            # Collect field values
            for field_name, control in self.field_controls.items():
                if isinstance(control, ft.Column):
                    # Handle special fields (ID/CR, Account/Membership)
                    text_control = control.controls[1] if len(control.controls) > 1 else None
                    form_data[field_name] = text_control.value if text_control else None
                else:
                    form_data[field_name] = control.value or None

            # Add ID type
            form_data['id_type'] = 'CR' if (self.id_type_checkbox and self.id_type_checkbox.value) else 'ID'

            # Add account type
            form_data['account_type'] = 'Membership' if (self.account_type_checkbox and self.account_type_checkbox.value) else 'Account'

            if self.edit_mode:
                # UPDATE existing report
                report_id = self.report_data.get('report_id')
                if not report_id:
                    raise ValueError("Cannot update report: missing report_id")

                # Track changes for audit trail
                self.log_changes(report_id, form_data)

                # Add update metadata
                form_data['updated_by'] = self.current_user['username']
                form_data['updated_at'] = datetime.now().isoformat()

                # Build UPDATE query
                set_clause = ', '.join([f"{k} = ?" for k in form_data.keys()])
                query = f"UPDATE reports SET {set_clause} WHERE report_id = ?"
                params = tuple(list(form_data.values()) + [report_id])

                # Execute
                self.db_manager.execute_with_retry(query, params)

                logger.info(f"Report updated: {self.report_data.get('report_number')}")
                self.show_success_dialog(
                    "Success",
                    f"Report updated successfully!\n\nReport Number: {self.report_data.get('report_number')}"
                )

                # Return to reports list
                self.cancel()

            else:
                # INSERT new report
                # Add auto-generated fields
                form_data['sn'] = self.generate_next_sn()
                form_data['report_number'] = self.generate_report_number()

                # Add metadata
                form_data['created_by'] = self.current_user['username']
                form_data['created_at'] = datetime.now().isoformat()
                form_data['status'] = 'Open'
                form_data['is_deleted'] = 0

                # Build INSERT query
                fields = ', '.join(form_data.keys())
                placeholders = ', '.join(['?' for _ in form_data])
                query = f"INSERT INTO reports ({fields}) VALUES ({placeholders})"

                # Execute
                self.db_manager.execute_with_retry(query, tuple(form_data.values()))

                # Get the inserted report_id
                report_id_query = "SELECT report_id FROM reports WHERE report_number = ?"
                result = self.db_manager.execute_with_retry(report_id_query, (form_data['report_number'],))
                if result:
                    new_report_id = result[0]['report_id']
                    # Log creation in audit trail
                    self.log_report_creation(new_report_id, form_data)

                logger.info(f"Report saved: {form_data['report_number']}, SN: {form_data['sn']}")
                self.show_success_dialog(
                    "Success",
                    f"Report saved successfully!\n\nReport Number: {form_data['report_number']}\nSerial Number: {form_data['sn']}"
                )

                # Clear form
                self.clear_form()

        except Exception as e:
            logger.error(f"Failed to save report: {e}")
            self.show_error_dialog("Save Failed", f"Failed to save report: {str(e)}")

    def log_report_creation(self, report_id, report_data):
        """Log report creation in audit trail"""
        try:
            timestamp = datetime.now().isoformat()

            # Log single INSERT entry
            insert_query = """
                INSERT INTO change_history (
                    table_name, record_id, field_name, old_value, new_value,
                    change_type, changed_by, changed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            self.db_manager.execute_with_retry(
                insert_query,
                (
                    'reports',
                    report_id,
                    'Report Created',
                    None,
                    f"Report {report_data.get('report_number')} created",
                    'INSERT',
                    self.current_user['username'],
                    timestamp
                )
            )
            logger.info(f"Report creation logged in audit trail: {report_data.get('report_number')}")

        except Exception as e:
            logger.error(f"Failed to log report creation: {e}")

    def log_changes(self, report_id, new_data):
        """Log all changes to change_history table for audit trail"""
        try:
            changes_logged = 0
            timestamp = datetime.now().isoformat()

            for field_name, new_value in new_data.items():
                # Get old value from report_data
                old_value = self.report_data.get(field_name)

                # Convert to strings for comparison (handle None values)
                old_value_str = str(old_value) if old_value is not None else ''
                new_value_str = str(new_value) if new_value is not None else ''

                # Skip if values are the same
                if old_value_str == new_value_str:
                    continue

                # Get display name for field
                display_name = field_name
                for col in self.column_settings:
                    if col['column_name'] == field_name:
                        display_name = col['display_name_en']
                        break

                # Insert change record
                insert_query = """
                    INSERT INTO change_history (
                        table_name, record_id, field_name, old_value, new_value,
                        change_type, changed_by, changed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """
                self.db_manager.execute_with_retry(
                    insert_query,
                    (
                        'reports',
                        report_id,
                        display_name,
                        old_value_str[:500] if old_value_str else None,  # Limit length
                        new_value_str[:500] if new_value_str else None,  # Limit length
                        'UPDATE',
                        self.current_user['username'],
                        timestamp
                    )
                )
                changes_logged += 1
                logger.info(f"Change logged: {field_name} changed from '{old_value_str}' to '{new_value_str}'")

            logger.info(f"Total changes logged: {changes_logged}")

        except Exception as e:
            logger.error(f"Failed to log changes: {e}")
            # Don't fail the update if logging fails, just log the error

    def cancel(self):
        """Cancel and return to reports list"""
        from reports_module import ReportsModule
        module = ReportsModule(self.page, self.db_manager, self.current_user, self.content_area)
        module.show()

    def clear_form(self):
        """Clear all form fields"""
        for control in self.field_controls.values():
            if isinstance(control, ft.Column):
                # Clear special fields
                if len(control.controls) > 1:
                    control.controls[1].value = ""
            else:
                control.value = ""

        if self.id_type_checkbox:
            self.id_type_checkbox.value = False
        if self.account_type_checkbox:
            self.account_type_checkbox.value = False

        self.page.update()
        self.show_snackbar("Form cleared")

    def prefill_form(self):
        """Pre-fill form fields with existing report data"""
        logger.info(f"Pre-filling form with report data: {self.report_data.get('report_number')}")

        for field_name, control in self.field_controls.items():
            # Get value from report data
            value = self.report_data.get(field_name)

            if value is None or value == '':
                continue

            try:
                # Handle different control types
                if isinstance(control, ft.Column):
                    # Special fields (id_cr, account_membership)
                    if field_name == 'id_cr':
                        # Set checkbox based on id_type
                        if self.id_type_checkbox and self.report_data.get('id_type') == 'CR':
                            self.id_type_checkbox.value = True
                        # Set the text field value
                        if len(control.controls) > 1 and isinstance(control.controls[1], ft.TextField):
                            control.controls[1].value = str(value)

                    elif field_name == 'account_membership':
                        # Set checkbox based on account_type
                        if self.account_type_checkbox and self.report_data.get('account_type') == 'Membership':
                            self.account_type_checkbox.value = True
                        # Set the text field value
                        if len(control.controls) > 1 and isinstance(control.controls[1], ft.TextField):
                            control.controls[1].value = str(value)

                elif isinstance(control, ft.TextField):
                    # Regular text fields and date fields
                    control.value = str(value)

                elif isinstance(control, ft.Dropdown):
                    # Dropdown fields
                    control.value = str(value)

                logger.info(f"Pre-filled field '{field_name}' with value: {value}")

            except Exception as e:
                logger.warning(f"Failed to pre-fill field '{field_name}': {e}")

        self.page.update()
        logger.info("Form pre-fill completed")

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
