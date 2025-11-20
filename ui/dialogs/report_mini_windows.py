"""
Report Mini Windows
Quick view and comparison windows for reports.
"""

from PyQt6.QtWidgets import (QVBoxLayout, QHBoxLayout, QPushButton,
                             QMessageBox, QLabel, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from typing import Dict, Optional, List
from datetime import datetime

from .mini_window import MiniWindow, DataGridWidget, SideBySideComparisonWidget


class ReportQuickViewWindow(MiniWindow):
    """
    Quick view window for a single report.
    Lightweight, read-only display of report details.
    """

    edit_requested = pyqtSignal(int)  # Emits report_id when edit is requested
    delete_requested = pyqtSignal(int)  # Emits report_id when delete is requested

    def __init__(self, report_data: Dict, report_service, logging_service,
                 current_user: Dict, parent=None):
        """
        Initialize report quick view window.

        Args:
            report_data: Report dictionary
            report_service: ReportService instance
            logging_service: LoggingService instance
            current_user: Current user dictionary
            parent: Parent widget
        """
        self.report_data = report_data
        self.report_service = report_service
        self.logging_service = logging_service
        self.current_user = current_user

        report_number = report_data.get('report_number', 'Unknown')
        super().__init__(f"Quick View: {report_number}", parent)

        self.load_report_data()

    def load_report_data(self):
        """Load and display report data."""
        # Create data grid
        grid = DataGridWidget()

        # Basic Information Section
        grid.add_separator("📋 Basic Information")
        grid.add_field("Serial Number", str(self.report_data.get('sn', '-')))
        grid.add_field("Report Number", self.report_data.get('report_number', '-'))
        grid.add_field("Report Date", self.report_data.get('report_date', '-'))
        grid.add_field("Status", self.report_data.get('status', '-'))

        # Entity Information Section
        grid.add_separator("🏢 Entity Information")
        grid.add_field("Entity Name", self.report_data.get('reported_entity_name', '-'), span_columns=True)

        # Check if it's the new checkbox field or old text field
        legal_owner = self.report_data.get('legal_entity_owner_checkbox')
        if legal_owner is not None:
            legal_owner_display = "Yes" if legal_owner == 1 else "No"
        else:
            legal_owner_display = self.report_data.get('legal_entity_owner', '-')

        grid.add_field("Legal Entity Owner", legal_owner_display)
        grid.add_field("Gender", self.report_data.get('gender', '-'))
        grid.add_field("Nationality", self.report_data.get('nationality', '-'))
        grid.add_field("ID/CR", self.report_data.get('id_cr', '-'))

        # Account Information Section
        grid.add_separator("💳 Account Information")

        # Check for new checkbox field
        acc_membership_checkbox = self.report_data.get('acc_membership_checkbox')
        if acc_membership_checkbox is not None:
            membership_type = "International Membership" if acc_membership_checkbox == 1 else "Account Number"
            grid.add_field("Membership Type", membership_type)
            grid.add_field("Relationship", self.report_data.get('relationship', '-'))
        else:
            grid.add_field("Account/Membership", self.report_data.get('account_membership', '-'))

        grid.add_field("Branch ID", self.report_data.get('branch_id', '-'))
        grid.add_field("CIC", self.report_data.get('cic', '-'))

        # Suspicion Information Section
        grid.add_separator("🔍 Suspicion Information")
        grid.add_field("First Reason", self.report_data.get('first_reason_for_suspicion', '-'), span_columns=True)
        grid.add_field("Second Reason", self.report_data.get('second_reason_for_suspicion', '-'), span_columns=True)
        grid.add_field("Transaction Type", self.report_data.get('type_of_suspected_transaction', '-'), span_columns=True)
        grid.add_field("ARB Staff", self.report_data.get('arb_staff', '-'))
        grid.add_field("Total Transaction", self.report_data.get('total_transaction', '-'))

        # Classification Section
        grid.add_separator("📊 Classification")
        grid.add_field("Report Classification", self.report_data.get('report_classification', '-'))
        grid.add_field("Report Source", self.report_data.get('report_source', '-'))
        grid.add_field("Reporting Entity", self.report_data.get('reporting_entity', '-'))
        grid.add_field("Reporter Initials", self.report_data.get('reporter_initials', '-'))

        # FIU Information Section
        grid.add_separator("🏛️ FIU Information")
        grid.add_field("FIU Number", self.report_data.get('fiu_number', '-'))
        grid.add_field("FIU Letter Number", self.report_data.get('fiu_letter_number', '-'))
        grid.add_field("Sending Date", self.report_data.get('sending_date', '-'))
        grid.add_field("FIU Receive Date", self.report_data.get('fiu_letter_receive_date', '-'))
        grid.add_field("FIU Feedback", self.report_data.get('fiu_feedback', '-'), span_columns=True)

        # Metadata Section
        grid.add_separator("ℹ️ Metadata")
        grid.add_field("Created By", self.report_data.get('created_by', '-'))
        grid.add_field("Created At", self._format_datetime(self.report_data.get('created_at')))

        updated_by = self.report_data.get('updated_by')
        updated_at = self.report_data.get('updated_at')
        if updated_by and updated_at:
            grid.add_field("Updated By", updated_by)
            grid.add_field("Updated At", self._format_datetime(updated_at))

        self.add_content_widget(grid)
        self.add_content_stretch()

        # Add action buttons
        self._add_action_buttons()

    def _format_datetime(self, dt_string: Optional[str]) -> str:
        """Format datetime string for display."""
        if not dt_string:
            return "-"
        try:
            dt = datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M')
        except:
            return dt_string

    def _add_action_buttons(self):
        """Add action buttons to the window."""
        # Replace default close button with action buttons
        self.button_bar.setVisible(True)

        # Clear existing buttons
        for i in reversed(range(self.button_bar.layout().count())):
            widget = self.button_bar.layout().itemAt(i).widget()
            if widget:
                widget.setParent(None)

        button_layout = self.button_bar.layout()

        # Edit button (if user has permission)
        if self.current_user.get('role') in ['admin', 'agent']:
            edit_btn = QPushButton("✏️ Edit")
            edit_btn.setObjectName("primaryButton")
            edit_btn.setMinimumWidth(100)
            edit_btn.clicked.connect(self._handle_edit)
            button_layout.addWidget(edit_btn)

        # Delete button (admin only)
        if self.current_user.get('role') == 'admin':
            delete_btn = QPushButton("🗑️ Delete")
            delete_btn.setObjectName("dangerButton")
            delete_btn.setMinimumWidth(100)
            delete_btn.clicked.connect(self._handle_delete)
            button_layout.addWidget(delete_btn)

        button_layout.addStretch()

        # Close button
        close_btn = QPushButton("Close")
        close_btn.setObjectName("secondaryButton")
        close_btn.setMinimumWidth(80)
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)

    def _handle_edit(self):
        """Handle edit button click."""
        self.edit_requested.emit(self.report_data['report_id'])
        self.close()

    def _handle_delete(self):
        """Handle delete button click."""
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete report {self.report_data['report_number']}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.delete_requested.emit(self.report_data['report_id'])
            self.close()


class ReportComparisonWindow(MiniWindow):
    """
    Side-by-side comparison window for two reports.
    Allows visual comparison of all fields.
    """

    def __init__(self, report_a: Dict, report_b: Dict, parent=None):
        """
        Initialize report comparison window.

        Args:
            report_a: First report dictionary
            report_b: Second report dictionary
            parent: Parent widget
        """
        self.report_a = report_a
        self.report_b = report_b

        title = f"Compare: {report_a.get('report_number', '?')} vs {report_b.get('report_number', '?')}"
        super().__init__(title, parent)

        # Make window wider for side-by-side comparison
        screen = self.screen().availableGeometry()
        self.resize(int(screen.width() * 0.7), int(screen.height() * 0.7))

        self.load_comparison()

    def load_comparison(self):
        """Load and display side-by-side comparison."""
        comparison = SideBySideComparisonWidget(
            title_left=f"Report: {self.report_a.get('report_number', 'A')}",
            title_right=f"Report: {self.report_b.get('report_number', 'B')}"
        )

        # Helper function to get value with highlighting
        def get_value(report, key):
            val = report.get(key, '-')
            return str(val) if val else '-'

        # Basic Information
        comparison.add_separator("📋 Basic Information")
        comparison.add_field_pair("Serial Number",
                                  get_value(self.report_a, 'sn'),
                                  get_value(self.report_b, 'sn'))
        comparison.add_field_pair("Report Number",
                                  get_value(self.report_a, 'report_number'),
                                  get_value(self.report_b, 'report_number'))
        comparison.add_field_pair("Report Date",
                                  get_value(self.report_a, 'report_date'),
                                  get_value(self.report_b, 'report_date'))
        comparison.add_field_pair("Status",
                                  get_value(self.report_a, 'status'),
                                  get_value(self.report_b, 'status'))

        # Entity Information
        comparison.add_separator("🏢 Entity Information")
        comparison.add_field_pair("Entity Name",
                                  get_value(self.report_a, 'reported_entity_name'),
                                  get_value(self.report_b, 'reported_entity_name'),
                                  span_columns=True)

        comparison.add_field_pair("Legal Entity Owner",
                                  self._get_legal_owner(self.report_a),
                                  self._get_legal_owner(self.report_b))
        comparison.add_field_pair("Gender",
                                  get_value(self.report_a, 'gender'),
                                  get_value(self.report_b, 'gender'))
        comparison.add_field_pair("Nationality",
                                  get_value(self.report_a, 'nationality'),
                                  get_value(self.report_b, 'nationality'))
        comparison.add_field_pair("ID/CR",
                                  get_value(self.report_a, 'id_cr'),
                                  get_value(self.report_b, 'id_cr'))

        # Account Information
        comparison.add_separator("💳 Account Information")
        comparison.add_field_pair("Account/Membership",
                                  self._get_account_info(self.report_a),
                                  self._get_account_info(self.report_b))
        comparison.add_field_pair("Branch ID",
                                  get_value(self.report_a, 'branch_id'),
                                  get_value(self.report_b, 'branch_id'))
        comparison.add_field_pair("CIC",
                                  get_value(self.report_a, 'cic'),
                                  get_value(self.report_b, 'cic'))

        # Suspicion Information
        comparison.add_separator("🔍 Suspicion Information")
        comparison.add_field_pair("First Reason",
                                  get_value(self.report_a, 'first_reason_for_suspicion'),
                                  get_value(self.report_b, 'first_reason_for_suspicion'),
                                  span_columns=True)
        comparison.add_field_pair("Second Reason",
                                  get_value(self.report_a, 'second_reason_for_suspicion'),
                                  get_value(self.report_b, 'second_reason_for_suspicion'),
                                  span_columns=True)
        comparison.add_field_pair("Transaction Type",
                                  get_value(self.report_a, 'type_of_suspected_transaction'),
                                  get_value(self.report_b, 'type_of_suspected_transaction'),
                                  span_columns=True)
        comparison.add_field_pair("Total Transaction",
                                  get_value(self.report_a, 'total_transaction'),
                                  get_value(self.report_b, 'total_transaction'))

        # Classification
        comparison.add_separator("📊 Classification")
        comparison.add_field_pair("Report Classification",
                                  get_value(self.report_a, 'report_classification'),
                                  get_value(self.report_b, 'report_classification'))
        comparison.add_field_pair("Report Source",
                                  get_value(self.report_a, 'report_source'),
                                  get_value(self.report_b, 'report_source'))
        comparison.add_field_pair("Reporting Entity",
                                  get_value(self.report_a, 'reporting_entity'),
                                  get_value(self.report_b, 'reporting_entity'))

        # FIU Information
        comparison.add_separator("🏛️ FIU Information")
        comparison.add_field_pair("FIU Number",
                                  get_value(self.report_a, 'fiu_number'),
                                  get_value(self.report_b, 'fiu_number'))
        comparison.add_field_pair("Sending Date",
                                  get_value(self.report_a, 'sending_date'),
                                  get_value(self.report_b, 'sending_date'))
        comparison.add_field_pair("FIU Feedback",
                                  get_value(self.report_a, 'fiu_feedback'),
                                  get_value(self.report_b, 'fiu_feedback'),
                                  span_columns=True)

        # Metadata
        comparison.add_separator("ℹ️ Metadata")
        comparison.add_field_pair("Created By",
                                  get_value(self.report_a, 'created_by'),
                                  get_value(self.report_b, 'created_by'))
        comparison.add_field_pair("Created At",
                                  self._format_datetime(self.report_a.get('created_at')),
                                  self._format_datetime(self.report_b.get('created_at')))

        self.add_content_widget(comparison)

    def _get_legal_owner(self, report: Dict) -> str:
        """Get legal owner display value."""
        checkbox_val = report.get('legal_entity_owner_checkbox')
        if checkbox_val is not None:
            return "Yes" if checkbox_val == 1 else "No"
        return report.get('legal_entity_owner', '-')

    def _get_account_info(self, report: Dict) -> str:
        """Get account/membership info."""
        checkbox_val = report.get('acc_membership_checkbox')
        if checkbox_val is not None:
            membership_type = "International Membership" if checkbox_val == 1 else "Account Number"
            relationship = report.get('relationship', '-')
            return f"{membership_type}: {relationship}"
        return report.get('account_membership', '-')

    def _format_datetime(self, dt_string: Optional[str]) -> str:
        """Format datetime string for display."""
        if not dt_string:
            return "-"
        try:
            dt = datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M')
        except:
            return dt_string
