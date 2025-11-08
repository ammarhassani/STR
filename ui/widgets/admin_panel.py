"""
Admin Panel view for user management.
Modern interface for creating, editing, and managing users.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QLineEdit, QComboBox, QHeaderView, QMessageBox,
                             QDialog, QFormLayout, QDialogButtonBox, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from datetime import datetime


class UserDialog(QDialog):
    """Dialog for creating or editing users."""

    def __init__(self, db_manager, user_data=None, parent=None):
        """
        Initialize user dialog.

        Args:
            db_manager: DatabaseManager instance
            user_data: Existing user data for editing (None for new user)
            parent: Parent widget
        """
        super().__init__(parent)
        self.db_manager = db_manager
        self.user_data = user_data
        self.is_edit_mode = user_data is not None

        self.setup_ui()

    def setup_ui(self):
        """Setup the user interface."""
        title = "Edit User" if self.is_edit_mode else "Add New User"
        self.setWindowTitle(title)
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Header
        header = QLabel(title)
        header_font = QFont()
        header_font.setPointSize(14)
        header_font.setWeight(QFont.Weight.Bold)
        header.setFont(header_font)
        layout.addWidget(header)

        # Form
        form_frame = QFrame()
        form_frame.setObjectName("card")
        form_layout = QFormLayout(form_frame)
        form_layout.setSpacing(12)
        form_layout.setContentsMargins(20, 20, 20, 20)

        # Username
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter username")
        if self.is_edit_mode:
            self.username_input.setText(self.user_data.get('username', ''))
            self.username_input.setReadOnly(True)  # Username cannot be changed
        form_layout.addRow("Username: *", self.username_input)

        # Password
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter password" if not self.is_edit_mode else "Leave blank to keep current password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addRow("Password:" + (" *" if not self.is_edit_mode else ""), self.password_input)

        # Full Name
        self.fullname_input = QLineEdit()
        self.fullname_input.setPlaceholderText("Enter full name")
        if self.is_edit_mode:
            self.fullname_input.setText(self.user_data.get('full_name', ''))
        form_layout.addRow("Full Name: *", self.fullname_input)

        # Role
        self.role_combo = QComboBox()
        self.role_combo.addItems(['admin', 'agent', 'reporter'])
        if self.is_edit_mode:
            role = self.user_data.get('role', 'reporter')
            index = self.role_combo.findText(role)
            if index >= 0:
                self.role_combo.setCurrentIndex(index)
        form_layout.addRow("Role: *", self.role_combo)

        # Active Status
        self.is_active_combo = QComboBox()
        self.is_active_combo.addItems(['Active', 'Inactive'])
        if self.is_edit_mode:
            is_active = self.user_data.get('is_active', 1)
            self.is_active_combo.setCurrentIndex(0 if is_active else 1)
        form_layout.addRow("Status:", self.is_active_combo)

        layout.addWidget(form_frame)

        # Info text
        info_label = QLabel("* Required fields")
        info_label.setObjectName("hintLabel")
        layout.addWidget(info_label)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.save_user)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def validate_form(self):
        """Validate form data."""
        username = self.username_input.text().strip()
        password = self.password_input.text()
        full_name = self.fullname_input.text().strip()

        if not username:
            QMessageBox.warning(self, "Validation Error", "Username is required")
            return False

        if not self.is_edit_mode and not password:
            QMessageBox.warning(self, "Validation Error", "Password is required for new users")
            return False

        if not full_name:
            QMessageBox.warning(self, "Validation Error", "Full name is required")
            return False

        # Check if username already exists (for new users)
        if not self.is_edit_mode:
            check_query = "SELECT COUNT(*) FROM users WHERE username = ?"
            result = self.db_manager.execute_with_retry(check_query, (username,))
            if result and result[0][0] > 0:
                QMessageBox.warning(self, "Validation Error", f"Username '{username}' already exists")
                return False

        return True

    def save_user(self):
        """Save user data."""
        if not self.validate_form():
            return

        username = self.username_input.text().strip()
        password = self.password_input.text()
        full_name = self.fullname_input.text().strip()
        role = self.role_combo.currentText()
        is_active = 1 if self.is_active_combo.currentText() == 'Active' else 0

        try:
            if self.is_edit_mode:
                # Update existing user
                user_id = self.user_data['user_id']

                if password:
                    # Update with new password
                    query = """
                        UPDATE users
                        SET password = ?, full_name = ?, role = ?, is_active = ?,
                            updated_at = datetime('now'), updated_by = 'admin'
                        WHERE user_id = ?
                    """
                    self.db_manager.execute_with_retry(query, (password, full_name, role, is_active, user_id))
                else:
                    # Update without changing password
                    query = """
                        UPDATE users
                        SET full_name = ?, role = ?, is_active = ?,
                            updated_at = datetime('now'), updated_by = 'admin'
                        WHERE user_id = ?
                    """
                    self.db_manager.execute_with_retry(query, (full_name, role, is_active, user_id))

                QMessageBox.information(self, "Success", "User updated successfully")

            else:
                # Create new user
                query = """
                    INSERT INTO users (username, password, full_name, role, is_active,
                                     created_at, created_by)
                    VALUES (?, ?, ?, ?, ?, datetime('now'), 'admin')
                """
                self.db_manager.execute_with_retry(query, (username, password, full_name, role, is_active))

                QMessageBox.information(self, "Success", "User created successfully")

            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save user: {str(e)}")


class AdminPanel(QWidget):
    """
    Admin Panel view for user management.

    Features:
    - View all users
    - Create new users
    - Edit existing users
    - Delete users (soft delete)
    - Filter by role and status
    """

    def __init__(self, db_manager, logging_service):
        """
        Initialize admin panel.

        Args:
            db_manager: DatabaseManager instance
            logging_service: LoggingService instance
        """
        super().__init__()
        self.db_manager = db_manager
        self.logging_service = logging_service
        self.current_users = []

        self.setup_ui()
        self.load_users()

    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header
        header_layout = QHBoxLayout()

        title = QLabel("User Management")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setWeight(QFont.Weight.Bold)
        title.setFont(title_font)
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Add User button
        add_btn = QPushButton("Add New User")
        add_btn.setObjectName("primaryButton")
        add_btn.clicked.connect(self.add_user)
        header_layout.addWidget(add_btn)

        layout.addLayout(header_layout)

        # Filters
        filters_layout = QHBoxLayout()

        # Role filter
        role_label = QLabel("Role:")
        self.role_filter = QComboBox()
        self.role_filter.addItems(['All Roles', 'admin', 'agent', 'reporter'])
        self.role_filter.currentTextChanged.connect(self.load_users)
        filters_layout.addWidget(role_label)
        filters_layout.addWidget(self.role_filter)

        # Status filter
        status_label = QLabel("Status:")
        self.status_filter = QComboBox()
        self.status_filter.addItems(['All', 'Active', 'Inactive'])
        self.status_filter.currentTextChanged.connect(self.load_users)
        filters_layout.addWidget(status_label)
        filters_layout.addWidget(self.status_filter)

        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.load_users)
        filters_layout.addWidget(refresh_btn)

        filters_layout.addStretch()

        layout.addLayout(filters_layout)

        # Stats
        self.stats_label = QLabel("0 users")
        self.stats_label.setObjectName("subtitleLabel")
        layout.addWidget(self.stats_label)

        # Users table
        self.users_table = QTableWidget()
        self.users_table.setColumnCount(7)
        self.users_table.setHorizontalHeaderLabels([
            'ID', 'Username', 'Full Name', 'Role', 'Status', 'Last Login', 'Actions'
        ])

        # Configure table
        self.users_table.setAlternatingRowColors(True)
        self.users_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.users_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        # Set column widths
        header = self.users_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # ID
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Username
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)  # Full Name
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Role
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Status
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # Last Login
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # Actions

        # Set row height to accommodate action buttons properly
        self.users_table.verticalHeader().setDefaultSectionSize(50)
        self.users_table.verticalHeader().setMinimumSectionSize(50)

        layout.addWidget(self.users_table)

    def load_users(self):
        """Load users from database."""
        try:
            # Build query
            query = "SELECT user_id, username, full_name, role, is_active, last_login FROM users WHERE 1=1"
            params = []

            # Role filter
            role = self.role_filter.currentText()
            if role != 'All Roles':
                query += " AND role = ?"
                params.append(role)

            # Status filter
            status = self.status_filter.currentText()
            if status == 'Active':
                query += " AND is_active = 1"
            elif status == 'Inactive':
                query += " AND is_active = 0"

            query += " ORDER BY user_id DESC"

            # Execute query
            results = self.db_manager.execute_with_retry(query, tuple(params))

            # Convert to list of dicts
            self.current_users = []
            for row in results:
                self.current_users.append({
                    'user_id': row[0],
                    'username': row[1],
                    'full_name': row[2],
                    'role': row[3],
                    'is_active': row[4],
                    'last_login': row[5]
                })

            # Update table
            self.users_table.setRowCount(0)
            self.users_table.setRowCount(len(self.current_users))

            for row, user in enumerate(self.current_users):
                # Set row height to ensure buttons are visible
                self.users_table.setRowHeight(row, 50)

                # ID
                id_item = QTableWidgetItem(str(user['user_id']))
                self.users_table.setItem(row, 0, id_item)

                # Username
                username_item = QTableWidgetItem(user['username'])
                self.users_table.setItem(row, 1, username_item)

                # Full Name
                fullname_item = QTableWidgetItem(user['full_name'])
                self.users_table.setItem(row, 2, fullname_item)

                # Role
                role_item = QTableWidgetItem(user['role'].capitalize())
                self.users_table.setItem(row, 3, role_item)

                # Status
                status_text = 'Active' if user['is_active'] else 'Inactive'
                status_item = QTableWidgetItem(status_text)
                if user['is_active']:
                    status_item.setForeground(Qt.GlobalColor.darkGreen)
                else:
                    status_item.setForeground(Qt.GlobalColor.red)
                self.users_table.setItem(row, 4, status_item)

                # Last Login
                last_login = user.get('last_login', '')
                if last_login:
                    last_login = last_login[:19]  # Remove microseconds
                last_login_item = QTableWidgetItem(last_login if last_login else 'Never')
                self.users_table.setItem(row, 5, last_login_item)

                # Actions (create widget with buttons)
                actions_widget = QWidget()
                actions_layout = QHBoxLayout(actions_widget)
                actions_layout.setContentsMargins(4, 2, 4, 2)
                actions_layout.setSpacing(4)

                edit_btn = QPushButton("Edit")
                edit_btn.setMaximumWidth(60)
                edit_btn.setMinimumHeight(36)  # Ensure button is tall enough to see
                edit_btn.clicked.connect(lambda checked, u=user: self.edit_user(u))
                actions_layout.addWidget(edit_btn)

                # Don't allow deleting admin user (user_id = 1)
                if user['user_id'] != 1:
                    delete_btn = QPushButton("Delete")
                    delete_btn.setObjectName("dangerButton")
                    delete_btn.setMaximumWidth(60)
                    delete_btn.setMinimumHeight(36)  # Ensure button is tall enough to see
                    delete_btn.clicked.connect(lambda checked, u=user: self.delete_user(u))
                    actions_layout.addWidget(delete_btn)

                actions_layout.addStretch()

                self.users_table.setCellWidget(row, 6, actions_widget)

            # Update stats
            self.stats_label.setText(f"{len(self.current_users)} user(s)")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load users: {str(e)}")
            self.logging_service.error(f"User load error: {str(e)}", exc_info=True)

    def add_user(self):
        """Add new user."""
        dialog = UserDialog(self.db_manager, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_users()
            self.logging_service.log_user_action("USER_CREATED")

    def edit_user(self, user):
        """Edit existing user."""
        dialog = UserDialog(self.db_manager, user_data=user, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_users()
            self.logging_service.log_user_action("USER_UPDATED", {"user_id": user['user_id']})

    def delete_user(self, user):
        """Delete user."""
        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete user '{user['username']}'?\n\n"
            "This will permanently remove the user from the system.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                query = "DELETE FROM users WHERE user_id = ?"
                self.db_manager.execute_with_retry(query, (user['user_id'],))

                QMessageBox.information(self, "Success", "User deleted successfully")
                self.load_users()
                self.logging_service.log_user_action("USER_DELETED", {"user_id": user['user_id']})

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete user: {str(e)}")
                self.logging_service.error(f"User deletion error: {str(e)}", exc_info=True)

    def refresh(self):
        """Refresh the view (called from main window)."""
        self.load_users()
