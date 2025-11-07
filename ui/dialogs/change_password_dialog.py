"""
Change Password Dialog
Allows users to change their password.
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QLineEdit, QMessageBox, QFormLayout)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from services.icon_service import get_icon


class ChangePasswordDialog(QDialog):
    """
    Dialog for changing user password.

    Features:
    - Current password verification
    - Password strength validation
    - Confirmation matching
    """

    def __init__(self, auth_service, parent=None):
        """
        Initialize change password dialog.

        Args:
            auth_service: AuthService instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.auth_service = auth_service
        self.current_user = auth_service.get_current_user()

        self.setup_ui()

    def setup_ui(self):
        """Setup the user interface."""
        self.setWindowTitle("Change Password")
        self.setMinimumWidth(450)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Header
        header = QLabel("Change Password")
        header_font = QFont()
        header_font.setPointSize(14)
        header_font.setWeight(QFont.Weight.Bold)
        header.setFont(header_font)
        layout.addWidget(header)

        # Info
        info_label = QLabel("Please enter your current password and choose a new password.")
        info_label.setStyleSheet("color: #7f8c8d;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Form
        form_layout = QFormLayout()
        form_layout.setSpacing(12)

        # Current password
        self.current_password_input = QLineEdit()
        self.current_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.current_password_input.setPlaceholderText("Enter current password")
        form_layout.addRow("Current Password:", self.current_password_input)

        # New password
        self.new_password_input = QLineEdit()
        self.new_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_password_input.setPlaceholderText("Enter new password")
        self.new_password_input.textChanged.connect(self.check_password_strength)
        form_layout.addRow("New Password:", self.new_password_input)

        # Password strength indicator
        self.strength_label = QLabel("")
        self.strength_label.setStyleSheet("font-size: 9pt;")
        form_layout.addRow("", self.strength_label)

        # Confirm password
        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_password_input.setPlaceholderText("Confirm new password")
        form_layout.addRow("Confirm Password:", self.confirm_password_input)

        layout.addLayout(form_layout)

        # Requirements
        requirements_label = QLabel(
            "Password requirements:\n"
            "• Minimum 8 characters\n"
            "• At least one uppercase letter\n"
            "• At least one lowercase letter\n"
            "• At least one number"
        )
        requirements_label.setStyleSheet("color: #7f8c8d; font-size: 9pt;")
        layout.addWidget(requirements_label)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setIcon(get_icon('times'))
        cancel_btn.setObjectName("secondaryButton")
        cancel_btn.setMinimumWidth(100)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        change_btn = QPushButton("Change Password")
        change_btn.setIcon(get_icon('key'))
        change_btn.setObjectName("primaryButton")
        change_btn.setMinimumWidth(150)
        change_btn.clicked.connect(self.change_password)
        button_layout.addWidget(change_btn)

        layout.addLayout(button_layout)

    def check_password_strength(self, password: str):
        """
        Check password strength and update indicator.

        Args:
            password: Password to check
        """
        if not password:
            self.strength_label.setText("")
            return

        strength = 0
        feedback = []

        # Length check
        if len(password) >= 8:
            strength += 1
        else:
            feedback.append("Too short")

        # Uppercase check
        if any(c.isupper() for c in password):
            strength += 1
        else:
            feedback.append("Add uppercase")

        # Lowercase check
        if any(c.islower() for c in password):
            strength += 1
        else:
            feedback.append("Add lowercase")

        # Number check
        if any(c.isdigit() for c in password):
            strength += 1
        else:
            feedback.append("Add number")

        # Update label
        if strength == 4:
            self.strength_label.setText("✓ Strong password")
            self.strength_label.setStyleSheet("color: #27ae60; font-weight: 600;")
        elif strength >= 2:
            self.strength_label.setText(f"⚠ Weak: {', '.join(feedback)}")
            self.strength_label.setStyleSheet("color: #f39c12; font-weight: 600;")
        else:
            self.strength_label.setText(f"✗ Too weak: {', '.join(feedback)}")
            self.strength_label.setStyleSheet("color: #e74c3c; font-weight: 600;")

    def validate_inputs(self) -> tuple[bool, str]:
        """
        Validate all inputs.

        Returns:
            Tuple of (is_valid, error_message)
        """
        current_password = self.current_password_input.text().strip()
        new_password = self.new_password_input.text().strip()
        confirm_password = self.confirm_password_input.text().strip()

        # Check all fields filled
        if not current_password:
            return False, "Please enter your current password."

        if not new_password:
            return False, "Please enter a new password."

        if not confirm_password:
            return False, "Please confirm your new password."

        # Check password length
        if len(new_password) < 8:
            return False, "Password must be at least 8 characters long."

        # Check password requirements
        if not any(c.isupper() for c in new_password):
            return False, "Password must contain at least one uppercase letter."

        if not any(c.islower() for c in new_password):
            return False, "Password must contain at least one lowercase letter."

        if not any(c.isdigit() for c in new_password):
            return False, "Password must contain at least one number."

        # Check passwords match
        if new_password != confirm_password:
            return False, "New passwords do not match."

        # Check new password different from current
        if current_password == new_password:
            return False, "New password must be different from current password."

        return True, ""

    def change_password(self):
        """Change the user password."""
        # Validate inputs
        is_valid, error_message = self.validate_inputs()
        if not is_valid:
            QMessageBox.warning(self, "Validation Error", error_message)
            return

        current_password = self.current_password_input.text().strip()
        new_password = self.new_password_input.text().strip()

        try:
            # Verify current password
            if not self.auth_service.verify_password(
                self.current_user['username'],
                current_password
            ):
                QMessageBox.warning(
                    self,
                    "Authentication Failed",
                    "Current password is incorrect."
                )
                self.current_password_input.clear()
                self.current_password_input.setFocus()
                return

            # Change password
            success = self.auth_service.change_password(
                self.current_user['id'],
                new_password
            )

            if success:
                QMessageBox.information(
                    self,
                    "Password Changed",
                    "Your password has been changed successfully."
                )
                self.accept()
            else:
                QMessageBox.critical(
                    self,
                    "Error",
                    "Failed to change password. Please try again."
                )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"An error occurred: {str(e)}"
            )
