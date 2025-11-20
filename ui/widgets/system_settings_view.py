"""
System Settings View
Admin panel for configuring system-wide settings.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QFrame, QSpinBox, QMessageBox,
                             QFormLayout, QGroupBox, QLineEdit, QTextEdit)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from datetime import datetime


class SystemSettingsView(QWidget):
    """
    Admin view for managing system-wide settings.

    Features:
    - Month grace period configuration
    - Batch pool size configuration
    - Reservation expiry time
    - Other system parameters
    """

    settings_changed = pyqtSignal()

    def __init__(self, db_manager, logging_service, current_user):
        super().__init__()
        self.db_manager = db_manager
        self.logging_service = logging_service
        self.current_user = current_user

        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Header
        header_layout = QHBoxLayout()

        title_label = QLabel("System Settings")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setWeight(QFont.Weight.Bold)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        layout.addLayout(header_layout)

        # Info
        info_label = QLabel(
            "Configure system-wide settings. Changes take effect immediately."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666;")
        layout.addWidget(info_label)

        # Report Numbering Settings
        numbering_group = QGroupBox("📋 Report Numbering")
        numbering_layout = QFormLayout(numbering_group)
        numbering_layout.setSpacing(15)

        # Month grace period
        self.grace_period_input = QSpinBox()
        self.grace_period_input.setMinimum(0)
        self.grace_period_input.setMaximum(15)
        self.grace_period_input.setValue(3)
        self.grace_period_input.setSuffix(" days")
        self.grace_period_input.setToolTip(
            "Number of days into new month to continue using previous month number.\n"
            "Example: If set to 3, on Dec 1-3, reports still use 2025/11 instead of 2025/12"
        )

        grace_help = QLabel(
            "<i>Example: Set to 3 means Dec 1st-3rd still use November (2025/11)</i>"
        )
        grace_help.setStyleSheet("color: #888; font-size: 10px;")

        numbering_layout.addRow("Month Grace Period:", self.grace_period_input)
        numbering_layout.addRow("", grace_help)

        layout.addWidget(numbering_group)

        # Batch Reservation Settings
        batch_group = QGroupBox("🔄 Batch Reservation")
        batch_layout = QFormLayout(batch_group)
        batch_layout.setSpacing(15)

        # Batch pool size
        self.batch_size_input = QSpinBox()
        self.batch_size_input.setMinimum(5)
        self.batch_size_input.setMaximum(100)
        self.batch_size_input.setValue(20)
        self.batch_size_input.setSuffix(" numbers")
        self.batch_size_input.setToolTip(
            "Number of report numbers to pre-reserve in the batch pool.\n"
            "Higher numbers = faster for many concurrent users, but more potential waste."
        )

        batch_help = QLabel(
            "<i>Higher = faster for concurrent users. Recommended: 10-30</i>"
        )
        batch_help.setStyleSheet("color: #888; font-size: 10px;")

        batch_layout.addRow("Batch Pool Size:", self.batch_size_input)
        batch_layout.addRow("", batch_help)

        # Reservation expiry
        self.reservation_expiry_input = QSpinBox()
        self.reservation_expiry_input.setMinimum(1)
        self.reservation_expiry_input.setMaximum(60)
        self.reservation_expiry_input.setValue(5)
        self.reservation_expiry_input.setSuffix(" minutes")
        self.reservation_expiry_input.setToolTip(
            "How long a reserved report number is held before expiring.\n"
            "Longer = more flexibility, but slower number recycling."
        )

        expiry_help = QLabel(
            "<i>Time before reserved numbers expire. Recommended: 5-10 minutes</i>"
        )
        expiry_help.setStyleSheet("color: #888; font-size: 10px;")

        batch_layout.addRow("Reservation Expiry:", self.reservation_expiry_input)
        batch_layout.addRow("", expiry_help)

        layout.addWidget(batch_group)

        # General Settings
        general_group = QGroupBox("⚙️ General")
        general_layout = QFormLayout(general_group)
        general_layout.setSpacing(15)

        # Page size
        self.page_size_input = QSpinBox()
        self.page_size_input.setMinimum(10)
        self.page_size_input.setMaximum(200)
        self.page_size_input.setValue(50)
        self.page_size_input.setSuffix(" records")
        self.page_size_input.setToolTip("Number of records to show per page in tables")

        general_layout.addRow("Default Page Size:", self.page_size_input)

        layout.addWidget(general_group)

        layout.addStretch()

        # Save button
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.setObjectName("secondaryButton")
        reset_btn.setMinimumWidth(150)
        reset_btn.clicked.connect(self.reset_to_defaults)
        button_layout.addWidget(reset_btn)

        save_btn = QPushButton("Save Settings")
        save_btn.setObjectName("primaryButton")
        save_btn.setMinimumWidth(150)
        save_btn.clicked.connect(self.save_settings)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

    def load_settings(self):
        """Load current settings from database."""
        try:
            # Month grace period
            result = self.db_manager.execute_with_retry(
                "SELECT config_value FROM system_config WHERE config_key = 'month_grace_period' AND is_active = 1"
            )
            if result:
                self.grace_period_input.setValue(int(result[0][0]))

            # Batch pool size
            result = self.db_manager.execute_with_retry(
                "SELECT config_value FROM system_config WHERE config_key = 'batch_pool_size' AND is_active = 1"
            )
            if result:
                self.batch_size_input.setValue(int(result[0][0]))

            # Reservation expiry
            result = self.db_manager.execute_with_retry(
                "SELECT config_value FROM system_config WHERE config_key = 'reservation_expiry_minutes' AND is_active = 1"
            )
            if result:
                self.reservation_expiry_input.setValue(int(result[0][0]))

            # Page size
            result = self.db_manager.execute_with_retry(
                "SELECT config_value FROM system_config WHERE config_key = 'records_per_page' AND is_active = 1"
            )
            if result:
                self.page_size_input.setValue(int(result[0][0]))

        except Exception as e:
            self.logging_service.error(f"Error loading settings: {str(e)}", exc_info=True)
            QMessageBox.warning(self, "Error", f"Failed to load settings: {str(e)}")

    def save_settings(self):
        """Save settings to database."""
        try:
            now = datetime.now().isoformat()
            username = self.current_user['username']

            # Helper function to save/update a setting
            def save_setting(key: str, value: str, config_type: str = 'setting'):
                # Check if exists
                result = self.db_manager.execute_with_retry(
                    "SELECT config_id FROM system_config WHERE config_key = ?",
                    (key,)
                )

                if result:
                    # Update
                    self.db_manager.execute_with_retry(
                        """UPDATE system_config
                           SET config_value = ?, updated_at = ?, updated_by = ?
                           WHERE config_key = ?""",
                        (value, now, username, key)
                    )
                else:
                    # Insert
                    self.db_manager.execute_with_retry(
                        """INSERT INTO system_config
                           (config_key, config_value, config_type, config_category, updated_at, updated_by)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (key, value, config_type, 'system', now, username)
                    )

            # Save each setting
            save_setting('month_grace_period', str(self.grace_period_input.value()))
            save_setting('batch_pool_size', str(self.batch_size_input.value()))
            save_setting('reservation_expiry_minutes', str(self.reservation_expiry_input.value()))
            save_setting('records_per_page', str(self.page_size_input.value()))

            # Log the change
            self.logging_service.info(
                f"Admin {username} updated system settings: "
                f"grace_period={self.grace_period_input.value()}, "
                f"batch_size={self.batch_size_input.value()}, "
                f"expiry={self.reservation_expiry_input.value()}"
            )

            QMessageBox.information(
                self,
                "Success",
                "Settings saved successfully!\n\n"
                "Changes will take effect for new operations."
            )

            self.settings_changed.emit()

        except Exception as e:
            self.logging_service.error(f"Error saving settings: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to save settings: {str(e)}")

    def reset_to_defaults(self):
        """Reset all settings to default values."""
        reply = QMessageBox.question(
            self,
            "Reset to Defaults",
            "Are you sure you want to reset all settings to their default values?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.grace_period_input.setValue(3)
            self.batch_size_input.setValue(20)
            self.reservation_expiry_input.setValue(5)
            self.page_size_input.setValue(50)

            QMessageBox.information(
                self,
                "Reset",
                "Settings reset to defaults. Click 'Save Settings' to apply."
            )
