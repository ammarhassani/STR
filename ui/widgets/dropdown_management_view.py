"""
Dropdown Management View
Admin panel for managing dropdown values (CRUD operations).
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QHeaderView, QMessageBox, QComboBox, QLineEdit,
                             QFrame, QDialog, QDialogButtonBox, QSpinBox,
                             QTextEdit, QSizePolicy)
from PyQt6.QtCore import Qt, QSettings, pyqtSignal
from PyQt6.QtGui import QFont, QColor
from datetime import datetime


class DropdownValueDialog(QDialog):
    """Dialog for adding/editing dropdown values."""

    def __init__(self, category: str, value: str = "", display_order: int = 0,
                 is_edit: bool = False, parent=None):
        super().__init__(parent)
        self.category = category
        self.value_text = value
        self.order = display_order
        self.is_edit = is_edit

        self.setWindowTitle(f"{'Edit' if is_edit else 'Add'} Dropdown Value - {category}")
        self.setMinimumWidth(400)

        self.setup_ui()

    def setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Category label
        category_label = QLabel(f"Category: <b>{self.category}</b>")
        layout.addWidget(category_label)

        # Value input
        value_label = QLabel("Value:")
        layout.addWidget(value_label)

        self.value_input = QLineEdit()
        self.value_input.setText(self.value_text)
        self.value_input.setPlaceholderText("Enter dropdown value...")
        layout.addWidget(self.value_input)

        # Display order
        order_label = QLabel("Display Order (lower numbers appear first):")
        layout.addWidget(order_label)

        self.order_input = QSpinBox()
        self.order_input.setMinimum(0)
        self.order_input.setMaximum(9999)
        self.order_input.setValue(self.order)
        layout.addWidget(self.order_input)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.validate_and_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def validate_and_accept(self):
        """Validate input and accept dialog."""
        value = self.value_input.text().strip()

        if not value:
            QMessageBox.warning(self, "Validation Error", "Value cannot be empty.")
            return

        self.accept()

    def get_data(self):
        """Get dialog data."""
        return {
            'value': self.value_input.text().strip(),
            'display_order': self.order_input.value()
        }


class DropdownManagementView(QWidget):
    """
    Admin view for managing dropdown values.

    Features:
    - View all dropdown categories
    - Add/Edit/Delete dropdown values
    - Reorder values
    - Soft delete (preserves data integrity)
    """

    data_changed = pyqtSignal()

    def __init__(self, dropdown_service, logging_service, current_user):
        super().__init__()
        self.dropdown_service = dropdown_service
        self.logging_service = logging_service
        self.current_user = current_user

        # Current state
        self.current_category = None
        self.dropdown_values = []

        self.setup_ui()
        self.load_categories()

    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header
        header_layout = QHBoxLayout()

        title_label = QLabel("Dropdown Management")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setWeight(QFont.Weight.Bold)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setObjectName("secondaryButton")
        refresh_btn.clicked.connect(self.load_values)
        header_layout.addWidget(refresh_btn)

        layout.addLayout(header_layout)

        # Info label
        info_label = QLabel("Manage dropdown values for various fields. Admin-manageable categories can be freely modified.")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666;")
        layout.addWidget(info_label)

        # Category selection
        category_frame = QFrame()
        category_frame.setObjectName("filterFrame")
        category_layout = QHBoxLayout(category_frame)

        category_label = QLabel("Category:")
        category_layout.addWidget(category_label)

        self.category_combo = QComboBox()
        self.category_combo.currentTextChanged.connect(self.on_category_changed)
        self.category_combo.setMinimumWidth(300)
        category_layout.addWidget(self.category_combo)

        category_layout.addStretch()

        # Add value button
        self.add_btn = QPushButton("Add Value")
        self.add_btn.setObjectName("primaryButton")
        self.add_btn.clicked.connect(self.add_value)
        self.add_btn.setEnabled(False)
        category_layout.addWidget(self.add_btn)

        layout.addWidget(category_frame)

        # Status label
        self.status_label = QLabel()
        layout.addWidget(self.status_label)

        # Table
        self.values_table = QTableWidget()
        self.values_table.setColumnCount(5)
        self.values_table.setHorizontalHeaderLabels([
            'Value', 'Display Order', 'Status', 'Updated By', 'Actions'
        ])

        self.values_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.values_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.values_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.values_table.setAlternatingRowColors(True)

        # Configure table - responsive column sizing
        header = self.values_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Value - takes remaining space
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Display Order
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Status
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Updated By
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Actions

        # Configure vertical header for responsive row heights
        vertical_header = self.values_table.verticalHeader()
        vertical_header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        vertical_header.setDefaultSectionSize(40)
        vertical_header.setMinimumSectionSize(35)

        layout.addWidget(self.values_table)

        # Notice about admin-manageable categories
        notice_label = QLabel(
            "ℹ️ <b>Admin-Manageable Categories:</b> " +
            ", ".join(self.dropdown_service.ADMIN_MANAGEABLE_CATEGORIES)
        )
        notice_label.setWordWrap(True)
        notice_label.setStyleSheet("background-color: #e3f2fd; padding: 10px; border-radius: 4px;")
        layout.addWidget(notice_label)

    def load_categories(self):
        """Load all dropdown categories."""
        try:
            categories = self.dropdown_service.get_all_categories()

            self.category_combo.clear()
            self.category_combo.addItem("-- Select Category --", None)

            for category in categories:
                # Show admin-manageable categories with a marker
                display_name = category
                if category in self.dropdown_service.ADMIN_MANAGEABLE_CATEGORIES:
                    display_name = f"✏️ {category}"

                self.category_combo.addItem(display_name, category)

        except Exception as e:
            self.logging_service.error(f"Error loading categories: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to load categories: {str(e)}")

    def on_category_changed(self, text):
        """Handle category selection change."""
        category = self.category_combo.currentData()

        if category:
            self.current_category = category
            self.load_values()

            # Enable add button only for admin-manageable categories
            is_admin_manageable = category in self.dropdown_service.ADMIN_MANAGEABLE_CATEGORIES
            self.add_btn.setEnabled(is_admin_manageable)
        else:
            self.current_category = None
            self.values_table.setRowCount(0)
            self.status_label.setText("")
            self.add_btn.setEnabled(False)

    def load_values(self):
        """Load values for current category."""
        if not self.current_category:
            return

        try:
            # Get all values including inactive ones
            all_values = self.dropdown_service.get_all_dropdown_values(self.current_category)

            self.dropdown_values = all_values
            self.values_table.setRowCount(len(all_values))

            for row, value_data in enumerate(all_values):
                # Value
                value_item = QTableWidgetItem(value_data['value'])
                self.values_table.setItem(row, 0, value_item)

                # Display Order
                order_item = QTableWidgetItem(str(value_data['display_order']))
                order_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.values_table.setItem(row, 1, order_item)

                # Status
                status = "Active" if value_data['is_active'] else "Inactive"
                status_item = QTableWidgetItem(status)
                status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                if value_data['is_active']:
                    status_item.setBackground(QColor(220, 252, 231))  # Light green
                else:
                    status_item.setBackground(QColor(254, 226, 226))  # Light red

                self.values_table.setItem(row, 2, status_item)

                # Updated By
                updated_by = value_data.get('updated_by', '-')
                updated_item = QTableWidgetItem(updated_by)
                self.values_table.setItem(row, 3, updated_item)

                # Actions
                self._add_action_buttons(row, value_data)

            # Update status label
            active_count = sum(1 for v in all_values if v['is_active'])
            inactive_count = len(all_values) - active_count

            is_admin_manageable = self.current_category in self.dropdown_service.ADMIN_MANAGEABLE_CATEGORIES
            manageable_text = "✏️ Admin-Manageable" if is_admin_manageable else "🔒 Fixed (Read-Only)"

            self.status_label.setText(
                f"<b>{self.current_category}</b> - {manageable_text} | "
                f"Active: {active_count} | Inactive: {inactive_count}"
            )

        except Exception as e:
            self.logging_service.error(f"Error loading dropdown values: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to load values: {str(e)}")

    def _add_action_buttons(self, row: int, value_data: dict):
        """Add action buttons to table row."""
        actions_widget = QWidget()
        actions_layout = QHBoxLayout(actions_widget)
        actions_layout.setContentsMargins(10, 10, 10, 10)
        actions_layout.setSpacing(8)

        is_admin_manageable = self.current_category in self.dropdown_service.ADMIN_MANAGEABLE_CATEGORIES

        if is_admin_manageable:
            # Edit button
            edit_btn = QPushButton("Edit")
            edit_btn.setObjectName("secondaryButton")
            edit_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            edit_btn.clicked.connect(lambda: self.edit_value(value_data))
            actions_layout.addWidget(edit_btn)

            # Delete/Restore button
            if value_data['is_active']:
                delete_btn = QPushButton("Delete")
                delete_btn.setObjectName("dangerButton")
                delete_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                delete_btn.clicked.connect(lambda: self.delete_value(value_data))
                actions_layout.addWidget(delete_btn)
            else:
                restore_btn = QPushButton("Restore")
                restore_btn.setObjectName("primaryButton")
                restore_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                restore_btn.clicked.connect(lambda: self.restore_value(value_data))
                actions_layout.addWidget(restore_btn)
        else:
            info_label = QLabel("Read-Only")
            info_label.setStyleSheet("color: #999;")
            actions_layout.addWidget(info_label)

        actions_layout.addStretch()

        self.values_table.setCellWidget(row, 4, actions_widget)

    def add_value(self):
        """Add new dropdown value."""
        if not self.current_category:
            return

        # Get next display order
        next_order = len(self.dropdown_values)

        dialog = DropdownValueDialog(
            self.current_category,
            display_order=next_order,
            parent=self
        )

        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()

            success, message = self.dropdown_service.add_dropdown_value(
                self.current_category,
                data['value'],
                self.current_user['username'],
                data['display_order']
            )

            if success:
                QMessageBox.information(self, "Success", message)
                self.load_values()
                self.data_changed.emit()
            else:
                QMessageBox.warning(self, "Error", message)

    def edit_value(self, value_data: dict):
        """Edit dropdown value."""
        dialog = DropdownValueDialog(
            self.current_category,
            value=value_data['value'],
            display_order=value_data['display_order'],
            is_edit=True,
            parent=self
        )

        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()

            success, message = self.dropdown_service.update_dropdown_value(
                value_data['config_id'],
                data['value'],
                self.current_user['username'],
                data['display_order']
            )

            if success:
                QMessageBox.information(self, "Success", message)
                self.load_values()
                self.data_changed.emit()
            else:
                QMessageBox.warning(self, "Error", message)

    def delete_value(self, value_data: dict):
        """Soft delete dropdown value."""
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete the value '{value_data['value']}'?\n\n"
            "This will be a soft delete - the value will be hidden but existing data is preserved.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            success, message = self.dropdown_service.delete_dropdown_value(
                value_data['config_id'],
                self.current_user['username']
            )

            if success:
                QMessageBox.information(self, "Success", message)
                self.load_values()
                self.data_changed.emit()
            else:
                QMessageBox.warning(self, "Error", message)

    def restore_value(self, value_data: dict):
        """Restore soft-deleted dropdown value."""
        success, message = self.dropdown_service.restore_dropdown_value(
            value_data['config_id'],
            self.current_user['username']
        )

        if success:
            QMessageBox.information(self, "Success", message)
            self.load_values()
            self.data_changed.emit()
        else:
            QMessageBox.warning(self, "Error", message)
