"""
Version History Dialog for viewing and managing report versions.
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QTextEdit, QSplitter, QMessageBox, QHeaderView,
                             QWidget, QFrame, QScrollArea)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from datetime import datetime


class VersionHistoryDialog(QDialog):
    """
    Dialog for viewing version history of a report.

    Signals:
        version_restored: Emitted when a version is restored
    """

    version_restored = pyqtSignal(int)  # version_id

    def __init__(self, report_service, report_id, current_user, parent=None):
        """
        Initialize the version history dialog.

        Args:
            report_service: ReportService instance
            report_id: Report ID to show history for
            current_user: Current user dictionary
            parent: Parent widget
        """
        super().__init__(parent)
        self.report_service = report_service
        self.report_id = report_id
        self.current_user = current_user
        self.versions = []
        self.selected_version_id = None

        self.setup_ui()
        self.load_versions()

    def setup_ui(self):
        """Setup the user interface."""
        self.setWindowTitle(f"Version History - Report #{self.report_id}")
        self.setMinimumSize(900, 600)
        self.resize(1000, 700)

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        header_label = QLabel(f"Version History - Report #{self.report_id}")
        header_label.setObjectName("titleLabel")
        header_font = QFont()
        header_font.setPointSize(16)
        header_font.setWeight(QFont.Weight.Bold)
        header_label.setFont(header_font)
        layout.addWidget(header_label)

        # Info label
        info_label = QLabel("View and manage all versions of this report. Admins can restore previous versions.")
        info_label.setObjectName("subtitleLabel")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Splitter for versions list and details
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left side - Versions list
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        versions_label = QLabel("Versions")
        versions_label.setObjectName("subtitleLabel")
        versions_font = QFont()
        versions_font.setPointSize(12)
        versions_font.setWeight(QFont.Weight.Bold)
        versions_label.setFont(versions_font)
        left_layout.addWidget(versions_label)

        # Versions table
        self.versions_table = QTableWidget()
        self.versions_table.setColumnCount(4)
        self.versions_table.setHorizontalHeaderLabels(['Version', 'Created By', 'Created At', 'Summary'])
        self.versions_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.versions_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.versions_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.versions_table.verticalHeader().setVisible(True)
        self.versions_table.itemSelectionChanged.connect(self.on_version_selected)

        # Configure responsive column sizing
        header = self.versions_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Version
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Created By
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Created At
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)  # Summary - takes remaining space

        # Configure vertical header for responsive row heights
        vertical_header = self.versions_table.verticalHeader()
        vertical_header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        vertical_header.setDefaultSectionSize(35)
        vertical_header.setMinimumSectionSize(30)

        left_layout.addWidget(self.versions_table)

        # Right side - Version details
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        details_label = QLabel("Version Details")
        details_label.setObjectName("subtitleLabel")
        details_label.setFont(versions_font)
        right_layout.addWidget(details_label)

        # Details text area
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setPlaceholderText("Select a version to view details")
        right_layout.addWidget(self.details_text)

        # Action buttons for selected version
        action_layout = QHBoxLayout()

        self.compare_button = QPushButton("Compare with Current")
        self.compare_button.setObjectName("primaryButton")
        self.compare_button.setEnabled(False)
        self.compare_button.clicked.connect(self.compare_with_current)
        action_layout.addWidget(self.compare_button)

        self.restore_button = QPushButton("Restore This Version")
        self.restore_button.setObjectName("dangerButton")
        self.restore_button.setEnabled(False)
        self.restore_button.clicked.connect(self.restore_version)
        # Only admins can restore
        if self.current_user.get('role') != 'admin':
            self.restore_button.setVisible(False)
        action_layout.addWidget(self.restore_button)

        action_layout.addStretch()
        right_layout.addLayout(action_layout)

        # Add to splitter
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)

        layout.addWidget(splitter)

        # Bottom buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        close_button = QPushButton("Close")
        close_button.setObjectName("secondaryButton")
        close_button.setMinimumWidth(100)
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

    def load_versions(self):
        """Load version history from database."""
        try:
            self.versions = self.report_service.get_report_versions(self.report_id)

            self.versions_table.setRowCount(len(self.versions))

            for row, version in enumerate(self.versions):
                # Version number
                version_item = QTableWidgetItem(f"v{version['version_number']}")
                version_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.versions_table.setItem(row, 0, version_item)

                # Created by
                creator_item = QTableWidgetItem(version['created_by'])
                self.versions_table.setItem(row, 1, creator_item)

                # Created at
                created_at = version['created_at']
                try:
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    formatted_date = dt.strftime('%Y-%m-%d %H:%M')
                except:
                    formatted_date = created_at
                date_item = QTableWidgetItem(formatted_date)
                self.versions_table.setItem(row, 2, date_item)

                # Summary
                summary = version.get('change_summary', 'No summary provided')
                summary_item = QTableWidgetItem(summary)
                self.versions_table.setItem(row, 3, summary_item)

            if not self.versions:
                self.details_text.setPlainText("No version history available for this report.")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load version history: {str(e)}")

    def on_version_selected(self):
        """Handle version selection."""
        selected_rows = self.versions_table.selectedIndexes()
        if not selected_rows:
            self.selected_version_id = None
            self.compare_button.setEnabled(False)
            self.restore_button.setEnabled(False)
            return

        row = selected_rows[0].row()
        if row < len(self.versions):
            version = self.versions[row]
            self.selected_version_id = version['version_id']

            # Load and display snapshot details
            snapshot = self.report_service.get_version_snapshot(self.selected_version_id)
            if snapshot:
                self.display_version_details(version, snapshot)

            self.compare_button.setEnabled(True)
            if self.current_user.get('role') == 'admin':
                self.restore_button.setEnabled(True)

    def display_version_details(self, version, snapshot):
        """
        Display version details in the text area.

        Args:
            version: Version metadata dictionary
            snapshot: Full report snapshot dictionary
        """
        details = []
        details.append(f"=== Version {version['version_number']} ===\n")
        details.append(f"Created By: {version['created_by']}")
        details.append(f"Created At: {version['created_at']}")
        details.append(f"Summary: {version.get('change_summary', 'No summary')}\n")
        details.append("=" * 50)
        details.append("\nReport Data:\n")

        # Display key fields from snapshot
        important_fields = [
            'report_number', 'reported_entity_name', 'cic', 'account_number',
            'status', 'approval_status', 'reported_amount', 'reporting_institution'
        ]

        for field in important_fields:
            if field in snapshot:
                field_name = field.replace('_', ' ').title()
                value = snapshot[field] or 'N/A'
                details.append(f"{field_name}: {value}")

        self.details_text.setPlainText('\n'.join(details))

    def compare_with_current(self):
        """Compare selected version with current report state."""
        if not self.selected_version_id:
            return

        try:
            # Get current report
            current_report = self.report_service.get_report(self.report_id)
            if not current_report:
                QMessageBox.warning(self, "Error", "Could not load current report")
                return

            # Get selected version snapshot
            selected_snapshot = self.report_service.get_version_snapshot(self.selected_version_id)
            if not selected_snapshot:
                QMessageBox.warning(self, "Error", "Could not load version snapshot")
                return

            # Find differences
            differences = []
            all_keys = set(current_report.keys()) | set(selected_snapshot.keys())

            # Exclude system fields from comparison
            exclude_fields = {'updated_at', 'updated_by', 'current_version', 'created_at'}

            for key in sorted(all_keys - exclude_fields):
                current_val = current_report.get(key, 'N/A')
                snapshot_val = selected_snapshot.get(key, 'N/A')

                if current_val != snapshot_val:
                    field_name = key.replace('_', ' ').title()
                    differences.append(f"\n{field_name}:")
                    differences.append(f"  Version: {snapshot_val}")
                    differences.append(f"  Current: {current_val}")

            if differences:
                comparison_text = "=== Comparison with Current Version ===\n"
                comparison_text += f"\nShowing {len(differences) // 3} field(s) that differ:\n"
                comparison_text += '\n'.join(differences)
            else:
                comparison_text = "No differences found between selected version and current version."

            # Show in a message box or dialog
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Version Comparison")
            msg_box.setText("Comparison Results")
            msg_box.setDetailedText(comparison_text)
            msg_box.setIcon(QMessageBox.Icon.Information)
            msg_box.exec()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to compare versions: {str(e)}")

    def restore_version(self):
        """Restore the selected version (admin only)."""
        if not self.selected_version_id:
            return

        if self.current_user.get('role') != 'admin':
            QMessageBox.warning(self, "Permission Denied",
                              "Only administrators can restore previous versions.")
            return

        # Confirmation dialog
        reply = QMessageBox.question(
            self,
            "Confirm Restore",
            "Are you sure you want to restore this version?\n\n"
            "This will replace the current report data with the selected version. "
            "A backup of the current state will be created automatically.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            success, message = self.report_service.restore_version(
                self.selected_version_id,
                f"Restored by {self.current_user['username']} via version history dialog"
            )

            if success:
                QMessageBox.information(self, "Success", message)
                self.version_restored.emit(self.selected_version_id)
                self.load_versions()  # Reload to show new backup version
            else:
                QMessageBox.warning(self, "Restore Failed", message)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to restore version: {str(e)}")
