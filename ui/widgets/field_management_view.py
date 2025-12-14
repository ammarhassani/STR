"""
Field Validation Management View
Admin panel for managing field validation rules and required status.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QHeaderView, QMessageBox, QFrame, QDialog,
                             QDialogButtonBox, QSpinBox, QCheckBox, QGroupBox)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from services.icon_service import get_icon
from ui.theme_colors import ThemeColors


class FieldValidationDialog(QDialog):
    """Dialog for editing field validation rules."""

    def __init__(self, field_name: str, display_name: str, current_rules: dict,
                 is_required: bool, parent=None):
        super().__init__(parent)
        self.field_name = field_name
        self.display_name = display_name
        self.current_rules = current_rules or {}
        self.is_required_value = is_required

        self.setWindowTitle(f"Edit Validation Rules - {display_name}")
        self.setMinimumWidth(500)

        self.setup_ui()

    def setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Field name label
        field_label = QLabel(f"Field: <b>{self.display_name}</b> ({self.field_name})")
        layout.addWidget(field_label)

        # Required checkbox
        self.required_checkbox = QCheckBox("Mark this field as required")
        self.required_checkbox.setChecked(self.is_required_value)
        layout.addWidget(self.required_checkbox)

        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)

        # Validation rules based on field type
        if self.field_name == 'id_cr':
            self.setup_id_cr_rules(layout)
        elif self.field_name == 'account_membership':
            self.setup_account_membership_rules(layout)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.validate_and_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def setup_id_cr_rules(self, layout):
        """Setup ID/CR validation rules."""
        rules_group = QGroupBox("ID/CR Validation Rules")
        rules_layout = QVBoxLayout(rules_group)

        # Length input
        length_layout = QHBoxLayout()
        length_label = QLabel("Length (digits):")
        length_label.setMinimumWidth(150)
        self.length_input = QSpinBox()
        self.length_input.setMinimum(1)
        self.length_input.setMaximum(20)
        self.length_input.setValue(self.current_rules.get('length', 10))
        length_layout.addWidget(length_label)
        length_layout.addWidget(self.length_input)
        length_layout.addStretch()
        rules_layout.addLayout(length_layout)

        # Saudi ID starting digit
        saudi_layout = QHBoxLayout()
        saudi_label = QLabel("Saudi ID starts with:")
        saudi_label.setMinimumWidth(150)
        self.saudi_starts_input = QSpinBox()
        self.saudi_starts_input.setMinimum(0)
        self.saudi_starts_input.setMaximum(9)
        self.saudi_starts_input.setValue(int(self.current_rules.get('saudi_starts_with', '1')))
        saudi_layout.addWidget(saudi_label)
        saudi_layout.addWidget(self.saudi_starts_input)
        saudi_layout.addStretch()
        rules_layout.addLayout(saudi_layout)

        # CR starting digit
        cr_layout = QHBoxLayout()
        cr_label = QLabel("CR number starts with:")
        cr_label.setMinimumWidth(150)
        self.cr_starts_input = QSpinBox()
        self.cr_starts_input.setMinimum(0)
        self.cr_starts_input.setMaximum(9)
        self.cr_starts_input.setValue(int(self.current_rules.get('cr_starts_with', '7')))
        cr_layout.addWidget(cr_label)
        cr_layout.addWidget(self.cr_starts_input)
        cr_layout.addStretch()
        rules_layout.addLayout(cr_layout)

        # Info label
        info = QLabel(
            "• Length: Total digits for both ID and CR\n"
            "• Saudi ID: Starting digit for Saudi Arabian IDs\n"
            "• CR: Starting digit for Commercial Registration numbers"
        )
        info.setStyleSheet(f"color: {ThemeColors.TEXT_SECONDARY}; font-size: 11px;")
        info.setWordWrap(True)
        rules_layout.addWidget(info)

        layout.addWidget(rules_group)

    def setup_account_membership_rules(self, layout):
        """Setup Account/Membership validation rules."""
        rules_group = QGroupBox("Account/Membership Validation Rules")
        rules_layout = QVBoxLayout(rules_group)

        # Account length
        account_layout = QHBoxLayout()
        account_label = QLabel("Account number length:")
        account_label.setMinimumWidth(180)
        self.account_length_input = QSpinBox()
        self.account_length_input.setMinimum(1)
        self.account_length_input.setMaximum(30)
        self.account_length_input.setValue(self.current_rules.get('account_length', 21))
        account_layout.addWidget(account_label)
        account_layout.addWidget(self.account_length_input)
        account_layout.addStretch()
        rules_layout.addLayout(account_layout)

        # Membership length
        membership_layout = QHBoxLayout()
        membership_label = QLabel("Membership number length:")
        membership_label.setMinimumWidth(180)
        self.membership_length_input = QSpinBox()
        self.membership_length_input.setMinimum(1)
        self.membership_length_input.setMaximum(30)
        self.membership_length_input.setValue(self.current_rules.get('membership_length', 8))
        membership_layout.addWidget(membership_label)
        membership_layout.addWidget(self.membership_length_input)
        membership_layout.addStretch()
        rules_layout.addLayout(membership_layout)

        # Info label
        info = QLabel(
            "• Account: Number of digits for bank account numbers\n"
            "• Membership: Number of digits for membership numbers"
        )
        info.setStyleSheet(f"color: {ThemeColors.TEXT_SECONDARY}; font-size: 11px;")
        info.setWordWrap(True)
        rules_layout.addWidget(info)

        layout.addWidget(rules_group)

    def validate_and_accept(self):
        """Validate input and accept dialog."""
        # Basic validation
        if self.field_name == 'id_cr':
            if self.length_input.value() < 1:
                QMessageBox.warning(self, "Validation Error", "Length must be at least 1.")
                return
        elif self.field_name == 'account_membership':
            if self.account_length_input.value() < 1 or self.membership_length_input.value() < 1:
                QMessageBox.warning(self, "Validation Error", "Lengths must be at least 1.")
                return

        self.accept()

    def get_data(self):
        """Get dialog data."""
        if self.field_name == 'id_cr':
            rules = {
                'length': self.length_input.value(),
                'pattern': f"^[0-9]{{{self.length_input.value()}}}$",
                'saudi_starts_with': str(self.saudi_starts_input.value()),
                'cr_starts_with': str(self.cr_starts_input.value())
            }
        elif self.field_name == 'account_membership':
            rules = {
                'account_length': self.account_length_input.value(),
                'membership_length': self.membership_length_input.value()
            }
        else:
            rules = {}

        return {
            'rules': rules,
            'is_required': self.required_checkbox.isChecked()
        }


class FieldManagementView(QWidget):
    """
    Admin view for managing field validation rules.

    Features:
    - View all validatable fields
    - Edit validation rules
    - Toggle required status
    - Real-time updates
    """

    data_changed = pyqtSignal()

    def __init__(self, validation_service, logging_service, current_user):
        super().__init__()
        self.validation_service = validation_service
        self.logging_service = logging_service
        self.current_user = current_user

        # Current state
        self.field_settings = []

        self.setup_ui()
        self.load_fields()

    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header
        header_layout = QHBoxLayout()

        title_label = QLabel("Field Validation Management")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setWeight(QFont.Weight.Bold)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setIcon(get_icon('refresh', color=ThemeColors.ICON_DEFAULT))
        refresh_btn.setObjectName("secondaryButton")
        refresh_btn.clicked.connect(self.load_fields)
        header_layout.addWidget(refresh_btn)

        layout.addLayout(header_layout)

        # Info label
        info_label = QLabel(
            "Configure validation rules for ID/CR and Account/Membership fields. "
            "These rules will be applied when creating or editing reports."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet(f"color: {ThemeColors.TEXT_SECONDARY};")
        layout.addWidget(info_label)

        # Table
        self.fields_table = QTableWidget()
        self.fields_table.setColumnCount(5)
        self.fields_table.setHorizontalHeaderLabels([
            'Field Name', 'Required', 'Validation Rules', 'Updated By', 'Actions'
        ])

        self.fields_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.fields_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.fields_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.fields_table.setAlternatingRowColors(True)

        # Configure table - responsive column sizing
        header = self.fields_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Field Name
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Required
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)  # Validation Rules - takes remaining space
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Updated By
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Actions

        # Configure vertical header for responsive row heights
        vertical_header = self.fields_table.verticalHeader()
        vertical_header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        vertical_header.setDefaultSectionSize(40)
        vertical_header.setMinimumSectionSize(35)

        layout.addWidget(self.fields_table)

    def load_fields(self):
        """Load all field settings from database."""
        try:
            self.field_settings = self.validation_service.get_all_field_settings()
            self.populate_table()

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to load field settings: {str(e)}"
            )
            self.logging_service.error(f"Error loading field settings: {str(e)}", exc_info=True)

    def populate_table(self):
        """Populate the table with field settings."""
        self.fields_table.setRowCount(0)

        for field in self.field_settings:
            row = self.fields_table.rowCount()
            self.fields_table.insertRow(row)

            # Field name
            name_item = QTableWidgetItem(field['display_name_en'])
            name_item.setData(Qt.ItemDataRole.UserRole, field['column_name'])
            self.fields_table.setItem(row, 0, name_item)

            # Required status
            required_text = "Yes" if field['is_required'] else "No"
            required_item = QTableWidgetItem(required_text)
            self.fields_table.setItem(row, 1, required_item)

            # Validation rules (formatted)
            rules_text = self.format_rules(field['column_name'], field['validation_rules'])
            rules_item = QTableWidgetItem(rules_text)
            rules_item.setToolTip(rules_text)
            self.fields_table.setItem(row, 2, rules_item)

            # Updated by
            updated_by = field.get('updated_by', 'System')
            updated_item = QTableWidgetItem(updated_by or 'System')
            self.fields_table.setItem(row, 3, updated_item)

            # Actions
            self.add_action_buttons(row, field)

    def format_rules(self, field_name: str, rules: dict) -> str:
        """Format validation rules for display."""
        if not rules:
            return "No rules defined"

        if field_name == 'id_cr':
            return (
                f"Length: {rules.get('length', 'N/A')} digits | "
                f"Saudi ID starts: {rules.get('saudi_starts_with', 'N/A')} | "
                f"CR starts: {rules.get('cr_starts_with', 'N/A')}"
            )
        elif field_name == 'account_membership':
            return (
                f"Account: {rules.get('account_length', 'N/A')} digits | "
                f"Membership: {rules.get('membership_length', 'N/A')} digits"
            )
        else:
            return str(rules)

    def add_action_buttons(self, row: int, field: dict):
        """Add action buttons to table row."""
        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)
        button_layout.setContentsMargins(4, 4, 4, 4)
        button_layout.setSpacing(4)

        # Edit button
        edit_btn = QPushButton("Edit")
        edit_btn.setIcon(get_icon('edit', color=ThemeColors.ICON_DEFAULT))
        edit_btn.setObjectName("secondaryButton")
        edit_btn.setMaximumWidth(80)
        edit_btn.clicked.connect(lambda: self.edit_field(field))
        button_layout.addWidget(edit_btn)

        button_layout.addStretch()
        self.fields_table.setCellWidget(row, 4, button_widget)

    def edit_field(self, field: dict):
        """Edit field validation rules."""
        dialog = FieldValidationDialog(
            field['column_name'],
            field['display_name_en'],
            field['validation_rules'],
            field['is_required'],
            self
        )

        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()

            # Update validation rules
            success, message = self.validation_service.update_validation_rules(
                field['column_name'],
                data['rules'],
                self.current_user['username']
            )

            if not success:
                QMessageBox.warning(self, "Error", message)
                return

            # Update required status
            success, message = self.validation_service.update_required_status(
                field['column_name'],
                data['is_required'],
                self.current_user['username']
            )

            if not success:
                QMessageBox.warning(self, "Error", message)
                return

            # Success
            QMessageBox.information(
                self,
                "Success",
                f"Validation rules for '{field['display_name_en']}' updated successfully."
            )

            # Reload table
            self.load_fields()

            # Emit signal
            self.data_changed.emit()

    def refresh(self):
        """Refresh the view (called from main window)."""
        self.load_fields()
