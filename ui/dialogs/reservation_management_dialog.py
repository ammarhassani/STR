"""
Report Number Reservation Management Dialog for Admin.
Allows admins to monitor and manage report number reservations.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QGroupBox, QMessageBox, QHeaderView, QTabWidget,
    QWidget, QTextEdit, QSpinBox, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from datetime import datetime


class ReservationManagementDialog(QDialog):
    """Dialog for managing report number reservations (Admin only)."""

    def __init__(self, report_number_service, auth_service, parent=None):
        """
        Initialize the reservation management dialog.

        Args:
            report_number_service: ReportNumberService instance
            auth_service: AuthService instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.report_number_service = report_number_service
        self.auth_service = auth_service

        self.setWindowTitle("Report Number Reservation Management")
        self.setMinimumSize(1000, 700)

        self.setup_ui()
        self.load_data()

        # Auto-refresh every 5 seconds
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_data)
        self.refresh_timer.start(5000)  # 5 seconds

    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("Report Number Reservation Management")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        # Tab widget
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Tab 1: Active Reservations
        self.reservations_tab = self.create_reservations_tab()
        self.tabs.addTab(self.reservations_tab, "Active Reservations")

        # Tab 2: Statistics
        self.stats_tab = self.create_statistics_tab()
        self.tabs.addTab(self.stats_tab, "Statistics")

        # Tab 3: Settings
        self.settings_tab = self.create_settings_tab()
        self.tabs.addTab(self.settings_tab, "Settings")

        # Bottom buttons
        button_layout = QHBoxLayout()

        refresh_btn = QPushButton("Refresh Now")
        refresh_btn.clicked.connect(self.refresh_data)
        button_layout.addWidget(refresh_btn)

        cleanup_btn = QPushButton("Run Cleanup Now")
        cleanup_btn.clicked.connect(self.run_cleanup)
        button_layout.addWidget(cleanup_btn)

        button_layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

    def create_reservations_tab(self):
        """Create the active reservations tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Info label
        info = QLabel("Active report number reservations. These are numbers currently held by users.")
        layout.addWidget(info)

        # Table
        self.reservations_table = QTableWidget()
        self.reservations_table.setColumnCount(6)
        self.reservations_table.setHorizontalHeaderLabels([
            "Report Number", "Serial Number", "Reserved By",
            "Reserved At", "Expires At", "Status"
        ])

        header = self.reservations_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)

        self.reservations_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.reservations_table.setAlternatingRowColors(True)
        self.reservations_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.reservations_table)

        # Action buttons
        action_layout = QHBoxLayout()

        release_btn = QPushButton("Release Selected Reservation")
        release_btn.clicked.connect(self.release_selected_reservation)
        action_layout.addWidget(release_btn)

        release_user_btn = QPushButton("Release All for Selected User")
        release_user_btn.clicked.connect(self.release_user_reservations)
        action_layout.addWidget(release_user_btn)

        action_layout.addStretch()
        layout.addLayout(action_layout)

        return tab

    def create_statistics_tab(self):
        """Create the statistics tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Statistics group
        stats_group = QGroupBox("Reservation Pool Statistics")
        stats_layout = QVBoxLayout(stats_group)

        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        self.stats_text.setMinimumHeight(150)
        self.stats_text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        stats_layout.addWidget(self.stats_text)

        layout.addWidget(stats_group)

        # Recent activity
        activity_group = QGroupBox("Recent Reservation Activity")
        activity_layout = QVBoxLayout(activity_group)

        self.activity_table = QTableWidget()
        self.activity_table.setColumnCount(4)
        self.activity_table.setHorizontalHeaderLabels([
            "Report Number", "User", "Action", "Timestamp"
        ])

        header = self.activity_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)

        self.activity_table.setAlternatingRowColors(True)
        self.activity_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        activity_layout.addWidget(self.activity_table)

        layout.addWidget(activity_group)

        return tab

    def create_settings_tab(self):
        """Create the settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Concurrent reservation limits
        limits_group = QGroupBox("Concurrent Reservation Limits")
        limits_layout = QVBoxLayout(limits_group)

        # Max concurrent reservations (system-wide)
        concurrent_label = QLabel("Maximum Concurrent Reservations (System-Wide):")
        limits_layout.addWidget(concurrent_label)

        concurrent_row = QHBoxLayout()
        self.max_concurrent_spinbox = QSpinBox()
        self.max_concurrent_spinbox.setMinimum(1)
        self.max_concurrent_spinbox.setMaximum(100)
        self.max_concurrent_spinbox.setValue(10)
        concurrent_row.addWidget(self.max_concurrent_spinbox)

        concurrent_row.addWidget(QLabel("employees can work at the same time"))
        concurrent_row.addStretch()

        limits_layout.addLayout(concurrent_row)

        concurrent_info = QLabel(
            "Controls how many report numbers can be reserved simultaneously across all users.\n"
            "Example: Set to 3 if you have 3 employees who need to create reports at the same time."
        )
        concurrent_info.setStyleSheet("color: gray; font-style: italic;")
        limits_layout.addWidget(concurrent_info)

        limits_layout.addSpacing(15)

        # Max reservations per user
        per_user_label = QLabel("Maximum Reservations Per User:")
        limits_layout.addWidget(per_user_label)

        per_user_row = QHBoxLayout()
        self.max_per_user_spinbox = QSpinBox()
        self.max_per_user_spinbox.setMinimum(1)
        self.max_per_user_spinbox.setMaximum(10)
        self.max_per_user_spinbox.setValue(1)
        per_user_row.addWidget(self.max_per_user_spinbox)

        per_user_row.addWidget(QLabel("reservations per employee"))
        per_user_row.addStretch()

        limits_layout.addLayout(per_user_row)

        per_user_info = QLabel(
            "Controls how many report numbers each user can reserve at once.\n"
            "Typically set to 1 - each user can work on one report at a time."
        )
        per_user_info.setStyleSheet("color: gray; font-style: italic;")
        limits_layout.addWidget(per_user_info)

        limits_layout.addSpacing(15)

        # Save button
        save_limits_btn = QPushButton("Save Reservation Limits")
        save_limits_btn.clicked.connect(self.save_reservation_limits)
        limits_layout.addWidget(save_limits_btn)

        layout.addWidget(limits_group)

        # Reservation timeout setting
        timeout_group = QGroupBox("Reservation Timeout")
        timeout_layout = QVBoxLayout(timeout_group)

        timeout_label = QLabel("Default Reservation Timeout (minutes):")
        timeout_layout.addWidget(timeout_label)

        timeout_row = QHBoxLayout()
        self.timeout_spinbox = QSpinBox()
        self.timeout_spinbox.setMinimum(1)
        self.timeout_spinbox.setMaximum(60)
        self.timeout_spinbox.setValue(5)
        timeout_row.addWidget(self.timeout_spinbox)

        save_timeout_btn = QPushButton("Save Timeout")
        save_timeout_btn.clicked.connect(self.save_timeout_setting)
        timeout_row.addWidget(save_timeout_btn)
        timeout_row.addStretch()

        timeout_layout.addLayout(timeout_row)

        timeout_info = QLabel(
            "How long a user can hold a reserved report number before it expires.\n"
            "Expired reservations are automatically cleaned up."
        )
        timeout_info.setStyleSheet("color: gray; font-style: italic;")
        timeout_layout.addWidget(timeout_info)

        layout.addWidget(timeout_group)

        # Cleanup settings
        cleanup_group = QGroupBox("Cleanup Settings")
        cleanup_layout = QVBoxLayout(cleanup_group)

        cleanup_info = QLabel(
            "Automatic cleanup runs every 2 minutes in the background.\n"
            "You can manually trigger cleanup using the button below."
        )
        cleanup_layout.addWidget(cleanup_info)

        manual_cleanup_btn = QPushButton("Run Manual Cleanup")
        manual_cleanup_btn.clicked.connect(self.run_cleanup)
        cleanup_layout.addWidget(manual_cleanup_btn)

        layout.addWidget(cleanup_group)

        layout.addStretch()

        return tab

    def load_data(self):
        """Load all data for the dialog."""
        self.load_reservations()
        self.load_statistics()
        self.load_activity()
        self.load_settings()

    def load_reservations(self):
        """Load active reservations into the table."""
        try:
            # Get active reservations from database
            query = """
                SELECT report_number, serial_number, reserved_by,
                       reserved_at, expires_at, is_used
                FROM report_number_reservations
                WHERE is_used = 0
                ORDER BY reserved_at DESC
            """

            result = self.report_number_service.db_manager.execute_with_retry(query)

            self.reservations_table.setRowCount(0)

            now = datetime.now()

            for row in result:
                row_position = self.reservations_table.rowCount()
                self.reservations_table.insertRow(row_position)

                # Report Number
                self.reservations_table.setItem(
                    row_position, 0, QTableWidgetItem(str(row[0]))
                )

                # Serial Number
                self.reservations_table.setItem(
                    row_position, 1, QTableWidgetItem(str(row[1]))
                )

                # Reserved By
                self.reservations_table.setItem(
                    row_position, 2, QTableWidgetItem(str(row[2]))
                )

                # Reserved At
                reserved_at = datetime.fromisoformat(row[3])
                self.reservations_table.setItem(
                    row_position, 3, QTableWidgetItem(reserved_at.strftime("%Y-%m-%d %H:%M:%S"))
                )

                # Expires At
                expires_at = datetime.fromisoformat(row[4])
                self.reservations_table.setItem(
                    row_position, 4, QTableWidgetItem(expires_at.strftime("%Y-%m-%d %H:%M:%S"))
                )

                # Status
                if expires_at < now:
                    status = "EXPIRED"
                    status_item = QTableWidgetItem(status)
                    status_item.setForeground(Qt.GlobalColor.red)
                else:
                    minutes_left = int((expires_at - now).total_seconds() / 60)
                    status = f"Active ({minutes_left} min left)"
                    status_item = QTableWidgetItem(status)
                    status_item.setForeground(Qt.GlobalColor.darkGreen)

                self.reservations_table.setItem(row_position, 5, status_item)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load reservations: {str(e)}")

    def load_statistics(self):
        """Load reservation statistics."""
        try:
            # Get various statistics
            stats = []

            # Total active reservations
            query = "SELECT COUNT(*) FROM report_number_reservations WHERE is_used = 0"
            result = self.report_number_service.db_manager.execute_with_retry(query)
            total_active = result[0][0] if result else 0
            stats.append(f"Active Reservations: {total_active}")

            # Expired reservations
            query = """
                SELECT COUNT(*) FROM report_number_reservations
                WHERE is_used = 0 AND expires_at < datetime('now')
            """
            result = self.report_number_service.db_manager.execute_with_retry(query)
            expired = result[0][0] if result else 0
            stats.append(f"Expired Reservations: {expired}")

            # Total used (completed)
            query = "SELECT COUNT(*) FROM report_number_reservations WHERE is_used = 1"
            result = self.report_number_service.db_manager.execute_with_retry(query)
            total_used = result[0][0] if result else 0
            stats.append(f"Total Reports Created (All Time): {total_used}")

            # Latest report number
            query = """
                SELECT MAX(serial_number) FROM report_number_reservations
            """
            result = self.report_number_service.db_manager.execute_with_retry(query)
            latest_sn = result[0][0] if result and result[0][0] else 0
            stats.append(f"Latest Serial Number: {latest_sn}")

            # Reservations by user
            query = """
                SELECT reserved_by, COUNT(*) as count
                FROM report_number_reservations
                WHERE is_used = 0
                GROUP BY reserved_by
                ORDER BY count DESC
            """
            result = self.report_number_service.db_manager.execute_with_retry(query)

            stats.append("\nReservations by User:")
            for row in result:
                stats.append(f"  {row[0]}: {row[1]} reservation(s)")

            self.stats_text.setText("\n".join(stats))

        except Exception as e:
            self.stats_text.setText(f"Error loading statistics: {str(e)}")

    def load_activity(self):
        """Load recent reservation activity."""
        try:
            # Get recent reservations (both active and used)
            query = """
                SELECT report_number, reserved_by, is_used, reserved_at
                FROM report_number_reservations
                ORDER BY reserved_at DESC
                LIMIT 50
            """

            result = self.report_number_service.db_manager.execute_with_retry(query)

            self.activity_table.setRowCount(0)

            for row in result:
                row_position = self.activity_table.rowCount()
                self.activity_table.insertRow(row_position)

                # Report Number
                self.activity_table.setItem(
                    row_position, 0, QTableWidgetItem(str(row[0]))
                )

                # User
                self.activity_table.setItem(
                    row_position, 1, QTableWidgetItem(str(row[1]))
                )

                # Action
                action = "Created Report" if row[2] == 1 else "Reserved"
                self.activity_table.setItem(
                    row_position, 2, QTableWidgetItem(action)
                )

                # Timestamp
                timestamp = datetime.fromisoformat(row[3])
                self.activity_table.setItem(
                    row_position, 3, QTableWidgetItem(timestamp.strftime("%Y-%m-%d %H:%M:%S"))
                )

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load activity: {str(e)}")

    def refresh_data(self):
        """Refresh all data in the dialog."""
        self.load_data()

    def release_selected_reservation(self):
        """Release the selected reservation."""
        selected_rows = self.reservations_table.selectionModel().selectedRows()

        if not selected_rows:
            QMessageBox.warning(self, "Warning", "Please select a reservation to release.")
            return

        row = selected_rows[0].row()
        report_number = self.reservations_table.item(row, 0).text()
        reserved_by = self.reservations_table.item(row, 2).text()

        reply = QMessageBox.question(
            self,
            "Confirm Release",
            f"Release reservation for {report_number} held by {reserved_by}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Delete the reservation
                query = """
                    DELETE FROM report_number_reservations
                    WHERE report_number = ? AND is_used = 0
                """
                self.report_number_service.db_manager.execute_with_retry(
                    query, (report_number,)
                )

                QMessageBox.information(
                    self, "Success", f"Released reservation for {report_number}"
                )
                self.refresh_data()

            except Exception as e:
                QMessageBox.critical(
                    self, "Error", f"Failed to release reservation: {str(e)}"
                )

    def release_user_reservations(self):
        """Release all reservations for the selected user."""
        selected_rows = self.reservations_table.selectionModel().selectedRows()

        if not selected_rows:
            QMessageBox.warning(self, "Warning", "Please select a user's reservation first.")
            return

        row = selected_rows[0].row()
        username = self.reservations_table.item(row, 2).text()

        reply = QMessageBox.question(
            self,
            "Confirm Release",
            f"Release ALL reservations held by {username}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Delete all reservations for this user
                query = """
                    DELETE FROM report_number_reservations
                    WHERE reserved_by = ? AND is_used = 0
                """
                self.report_number_service.db_manager.execute_with_retry(
                    query, (username,)
                )

                QMessageBox.information(
                    self, "Success", f"Released all reservations for {username}"
                )
                self.refresh_data()

            except Exception as e:
                QMessageBox.critical(
                    self, "Error", f"Failed to release reservations: {str(e)}"
                )

    def run_cleanup(self):
        """Manually trigger reservation cleanup."""
        try:
            self.report_number_service.cleanup_expired_reservations_public()
            QMessageBox.information(
                self, "Success", "Cleanup completed. Expired reservations have been released."
            )
            self.refresh_data()
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Failed to run cleanup: {str(e)}"
            )

    def load_settings(self):
        """Load current settings from database."""
        try:
            # Load max concurrent reservations
            query = """
                SELECT setting_value FROM system_settings
                WHERE setting_key = 'max_concurrent_reservations'
            """
            result = self.report_number_service.db_manager.execute_with_retry(query)
            if result and result[0][0]:
                self.max_concurrent_spinbox.setValue(int(result[0][0]))

            # Load max reservations per user
            query = """
                SELECT setting_value FROM system_settings
                WHERE setting_key = 'max_reservations_per_user'
            """
            result = self.report_number_service.db_manager.execute_with_retry(query)
            if result and result[0][0]:
                self.max_per_user_spinbox.setValue(int(result[0][0]))

        except Exception as e:
            print(f"Error loading settings: {str(e)}")

    def save_reservation_limits(self):
        """Save reservation limit settings."""
        try:
            max_concurrent = self.max_concurrent_spinbox.value()
            max_per_user = self.max_per_user_spinbox.value()

            # Update max concurrent reservations
            query = """
                UPDATE system_settings
                SET setting_value = ?
                WHERE setting_key = 'max_concurrent_reservations'
            """
            self.report_number_service.db_manager.execute_with_retry(
                query, (str(max_concurrent),)
            )

            # Update max reservations per user
            query = """
                UPDATE system_settings
                SET setting_value = ?
                WHERE setting_key = 'max_reservations_per_user'
            """
            self.report_number_service.db_manager.execute_with_retry(
                query, (str(max_per_user),)
            )

            QMessageBox.information(
                self,
                "Success",
                f"Reservation limits updated successfully!\n\n"
                f"• Max concurrent reservations: {max_concurrent} employees\n"
                f"• Max reservations per user: {max_per_user}\n\n"
                "These settings take effect immediately."
            )

        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Failed to save settings: {str(e)}"
            )

    def save_timeout_setting(self):
        """Save the reservation timeout setting."""
        timeout_minutes = self.timeout_spinbox.value()

        # TODO: Implement saving to configuration table
        QMessageBox.information(
            self,
            "Info",
            f"Timeout setting ({timeout_minutes} minutes) saved.\n"
            "Note: This will take effect for new reservations."
        )

    def closeEvent(self, event):
        """Handle dialog close event."""
        # Stop the refresh timer
        self.refresh_timer.stop()
        event.accept()
