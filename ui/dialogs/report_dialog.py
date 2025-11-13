"""
Report dialog for creating and editing financial crime reports.
Comprehensive form with validation for all report fields.
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QTextEdit, QComboBox, QDateEdit,
                             QTabWidget, QWidget, QPushButton, QMessageBox,
                             QGroupBox, QFormLayout, QScrollArea, QFrame)
from PyQt6.QtCore import Qt, QDate, pyqtSignal
from PyQt6.QtGui import QFont
from datetime import datetime
import re
from services.icon_service import get_icon


class ReportDialog(QDialog):
    """
    Dialog for creating or editing reports.

    Signals:
        report_saved: Emitted when report is successfully saved
    """

    report_saved = pyqtSignal()

    def __init__(self, report_service, logging_service, current_user, report_data=None, parent=None):
        """
        Initialize report dialog.

        Args:
            report_service: ReportService instance
            logging_service: LoggingService instance
            current_user: Current user dictionary
            report_data: Existing report data for editing (None for new report)
            parent: Parent widget
        """
        super().__init__(parent)
        self.report_service = report_service
        self.logging_service = logging_service
        self.current_user = current_user
        self.report_data = report_data
        self.is_edit_mode = report_data is not None

        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        """Setup the user interface."""
        title = "Edit Report" if self.is_edit_mode else "Add New Report"
        self.setWindowTitle(title)
        self.setMinimumSize(900, 700)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Header with version and approval info
        header_layout = QHBoxLayout()

        header = QLabel(title)
        header_font = QFont()
        header_font.setPointSize(16)
        header_font.setWeight(QFont.Weight.Bold)
        header.setFont(header_font)
        header_layout.addWidget(header)

        # Version and approval status badges (only in edit mode)
        if self.is_edit_mode and self.report_data:
            current_version = self.report_data.get('current_version', 1)
            approval_status = self.report_data.get('approval_status', 'draft')

            # Version badge
            version_badge = QLabel(f"v{current_version}")
            version_badge.setObjectName("versionBadge")
            version_badge.setStyleSheet("""
                QLabel#versionBadge {
                    background-color: #0d7377;
                    color: #ffffff;
                    border-radius: 10px;
                    padding: 4px 12px;
                    font-size: 11px;
                    font-weight: bold;
                }
            """)
            header_layout.addWidget(version_badge)

            # Approval status badge
            status_colors = {
                'draft': '#6e7681',
                'pending_approval': '#d29922',
                'approved': '#2ea043',
                'rejected': '#f85149',
                'rework': '#d29922'
            }
            status_labels = {
                'draft': 'Draft',
                'pending_approval': 'Pending Approval',
                'approved': 'Approved',
                'rejected': 'Rejected',
                'rework': 'Needs Rework'
            }

            approval_badge = QLabel(status_labels.get(approval_status, approval_status))
            approval_badge.setObjectName("approvalBadge")
            approval_badge.setStyleSheet(f"""
                QLabel#approvalBadge {{
                    background-color: {status_colors.get(approval_status, '#6e7681')};
                    color: #ffffff;
                    border-radius: 10px;
                    padding: 4px 12px;
                    font-size: 11px;
                    font-weight: bold;
                }}
            """)
            header_layout.addWidget(approval_badge)

        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Tabs for organizing fields
        tabs = QTabWidget()
        tabs.addTab(self.create_basic_info_tab(), "Basic Information")
        tabs.addTab(self.create_entity_details_tab(), "Entity Details")
        tabs.addTab(self.create_suspicion_details_tab(), "Suspicion Details")
        tabs.addTab(self.create_classification_tab(), "Classification & Source")
        tabs.addTab(self.create_fiu_details_tab(), "FIU Details")
        layout.addWidget(tabs)

        # Buttons
        button_layout = QHBoxLayout()

        # Left side buttons (version history)
        if self.is_edit_mode and self.report_data:
            history_btn = QPushButton("View History")
            history_btn.setIcon(get_icon('history'))
            history_btn.setObjectName("secondaryButton")
            history_btn.setMinimumWidth(120)
            history_btn.clicked.connect(self.view_history)
            button_layout.addWidget(history_btn)

        button_layout.addStretch()

        # Right side buttons (actions)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setIcon(get_icon('times'))
        cancel_btn.setObjectName("secondaryButton")
        cancel_btn.setMinimumWidth(100)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save Report")
        save_btn.setIcon(get_icon('save'))
        save_btn.setObjectName("primaryButton")
        save_btn.setMinimumWidth(120)
        save_btn.clicked.connect(self.save_report)
        button_layout.addWidget(save_btn)

        # Submit for approval button (only if editing and not already approved)
        if self.is_edit_mode and self.report_data:
            approval_status = self.report_data.get('approval_status', 'draft')
            if approval_status not in ['pending_approval', 'approved']:
                submit_approval_btn = QPushButton("Submit for Approval")
                submit_approval_btn.setIcon(get_icon('check'))
                submit_approval_btn.setObjectName("successButton")
                submit_approval_btn.setMinimumWidth(150)
                submit_approval_btn.clicked.connect(self.submit_for_approval)
                button_layout.addWidget(submit_approval_btn)

        layout.addLayout(button_layout)

    def create_basic_info_tab(self):
        """Create basic information tab."""
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QFormLayout(container)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        # Serial Number
        self.sn_input = QLineEdit()
        self.sn_input.setPlaceholderText("Enter serial number (e.g., 1)")
        layout.addRow("Serial Number: *", self.sn_input)

        # Report Number
        self.report_number_input = QLineEdit()
        self.report_number_input.setPlaceholderText("Format: YYYY/MM/NNN (e.g., 2025/11/001)")
        layout.addRow("Report Number: *", self.report_number_input)

        # Report Date
        self.report_date_input = QDateEdit()
        self.report_date_input.setCalendarPopup(True)
        self.report_date_input.setDate(QDate.currentDate())
        self.report_date_input.setDisplayFormat("dd/MM/yyyy")
        layout.addRow("Report Date: *", self.report_date_input)

        # Outgoing Letter Number
        self.outgoing_letter_input = QLineEdit()
        self.outgoing_letter_input.setPlaceholderText("Enter outgoing letter number")
        layout.addRow("Outgoing Letter Number:", self.outgoing_letter_input)

        # Status
        self.status_combo = QComboBox()
        self.status_combo.addItems([
            'Open',
            'Case Review',
            'Under Investigation',
            'Case Validation',
            'Close Case',
            'Closed with STR'
        ])
        layout.addRow("Status: *", self.status_combo)

        scroll.setWidget(container)

        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll)

        return tab

    def create_entity_details_tab(self):
        """Create entity details tab."""
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QFormLayout(container)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        # Reported Entity Name
        self.entity_name_input = QLineEdit()
        self.entity_name_input.setPlaceholderText("Enter entity name")
        layout.addRow("Reported Entity Name: *", self.entity_name_input)

        # Legal Entity Owner
        self.legal_owner_input = QLineEdit()
        self.legal_owner_input.setPlaceholderText("Enter legal entity owner")
        layout.addRow("Legal Entity Owner:", self.legal_owner_input)

        # Gender
        self.gender_combo = QComboBox()
        self.gender_combo.addItems(['', 'ذكر', 'أنثى'])
        layout.addRow("Gender:", self.gender_combo)

        # Nationality
        self.nationality_input = QLineEdit()
        self.nationality_input.setPlaceholderText("Enter nationality")
        layout.addRow("Nationality:", self.nationality_input)

        # ID/CR
        self.id_cr_input = QLineEdit()
        self.id_cr_input.setPlaceholderText("Enter ID or Commercial Registration number")
        layout.addRow("ID/CR:", self.id_cr_input)

        # Account/Membership
        self.account_input = QLineEdit()
        self.account_input.setPlaceholderText("Enter account or membership number")
        layout.addRow("Account/Membership:", self.account_input)

        # Branch ID
        self.branch_input = QLineEdit()
        self.branch_input.setPlaceholderText("Enter branch ID")
        layout.addRow("Branch ID:", self.branch_input)

        # CIC
        self.cic_input = QLineEdit()
        self.cic_input.setPlaceholderText("Enter CIC number")
        layout.addRow("CIC:", self.cic_input)

        scroll.setWidget(container)

        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll)

        return tab

    def create_suspicion_details_tab(self):
        """Create suspicion details tab."""
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QFormLayout(container)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        # First Reason for Suspicion
        self.first_reason_input = QTextEdit()
        self.first_reason_input.setPlaceholderText("Describe the first reason for suspicion")
        self.first_reason_input.setMaximumHeight(100)
        layout.addRow("First Reason for Suspicion:", self.first_reason_input)

        # Second Reason for Suspicion
        self.second_reason_input = QTextEdit()
        self.second_reason_input.setPlaceholderText("Describe the second reason for suspicion")
        self.second_reason_input.setMaximumHeight(100)
        layout.addRow("Second Reason for Suspicion:", self.second_reason_input)

        # Type of Suspected Transaction
        self.transaction_type_input = QLineEdit()
        self.transaction_type_input.setPlaceholderText("Enter type of suspected transaction")
        layout.addRow("Type of Suspected Transaction:", self.transaction_type_input)

        # ARB Staff
        self.arb_staff_combo = QComboBox()
        self.arb_staff_combo.addItems(['', 'نعم', 'لا'])
        layout.addRow("ARB Staff:", self.arb_staff_combo)

        # Total Transaction
        self.total_transaction_input = QLineEdit()
        self.total_transaction_input.setPlaceholderText("Enter amount with SAR (e.g., 605040 SAR)")
        layout.addRow("Total Transaction:", self.total_transaction_input)

        scroll.setWidget(container)

        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll)

        return tab

    def create_classification_tab(self):
        """Create classification and source tab."""
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QFormLayout(container)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        # Report Classification
        self.classification_input = QLineEdit()
        self.classification_input.setPlaceholderText("Enter report classification")
        layout.addRow("Report Classification:", self.classification_input)

        # Report Source
        self.report_source_input = QLineEdit()
        self.report_source_input.setPlaceholderText("Enter report source")
        layout.addRow("Report Source:", self.report_source_input)

        # Reporting Entity
        self.reporting_entity_input = QLineEdit()
        self.reporting_entity_input.setPlaceholderText("Enter reporting entity")
        layout.addRow("Reporting Entity:", self.reporting_entity_input)

        # Paper or Automated
        self.paper_automated_combo = QComboBox()
        self.paper_automated_combo.addItems(['', 'ورقي', 'آلي'])
        layout.addRow("Paper or Automated:", self.paper_automated_combo)

        # Reporter Initials
        self.reporter_initials_input = QLineEdit()
        self.reporter_initials_input.setPlaceholderText("Enter 2 uppercase letters (e.g., ZM)")
        self.reporter_initials_input.setMaxLength(2)
        layout.addRow("Reporter Initials:", self.reporter_initials_input)

        # Sending Date
        self.sending_date_input = QDateEdit()
        self.sending_date_input.setCalendarPopup(True)
        self.sending_date_input.setDate(QDate.currentDate())
        self.sending_date_input.setDisplayFormat("dd/MM/yyyy")
        self.sending_date_input.setSpecialValueText(" ")
        layout.addRow("Sending Date:", self.sending_date_input)

        # Original Copy Confirmation
        self.original_copy_input = QLineEdit()
        self.original_copy_input.setPlaceholderText("Enter confirmation status")
        layout.addRow("Original Copy Confirmation:", self.original_copy_input)

        scroll.setWidget(container)

        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll)

        return tab

    def create_fiu_details_tab(self):
        """Create FIU details tab."""
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QFormLayout(container)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        # FIU Number
        self.fiu_number_input = QLineEdit()
        self.fiu_number_input.setPlaceholderText("Enter FIU number")
        layout.addRow("FIU Number:", self.fiu_number_input)

        # FIU Letter Receive Date
        self.fiu_receive_date_input = QDateEdit()
        self.fiu_receive_date_input.setCalendarPopup(True)
        self.fiu_receive_date_input.setDate(QDate.currentDate())
        self.fiu_receive_date_input.setDisplayFormat("dd/MM/yyyy")
        self.fiu_receive_date_input.setSpecialValueText(" ")
        layout.addRow("FIU Letter Receive Date:", self.fiu_receive_date_input)

        # FIU Feedback
        self.fiu_feedback_input = QTextEdit()
        self.fiu_feedback_input.setPlaceholderText("Enter FIU feedback")
        self.fiu_feedback_input.setMaximumHeight(100)
        layout.addRow("FIU Feedback:", self.fiu_feedback_input)

        # FIU Letter Number
        self.fiu_letter_number_input = QLineEdit()
        self.fiu_letter_number_input.setPlaceholderText("Enter FIU letter number")
        layout.addRow("FIU Letter Number:", self.fiu_letter_number_input)

        # FIU Date
        self.fiu_date_input = QDateEdit()
        self.fiu_date_input.setCalendarPopup(True)
        self.fiu_date_input.setDate(QDate.currentDate())
        self.fiu_date_input.setDisplayFormat("dd/MM/yyyy")
        self.fiu_date_input.setSpecialValueText(" ")
        layout.addRow("FIU Date:", self.fiu_date_input)

        scroll.setWidget(container)

        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll)

        return tab

    def load_data(self):
        """Load existing report data if in edit mode or auto-generate SN for new reports."""
        # Auto-generate serial number for new reports
        if not self.is_edit_mode:
            try:
                # Get next available SN
                query = "SELECT MAX(sn) FROM reports"
                result = self.report_service.db_manager.execute_with_retry(query)
                max_sn = result[0][0] if result and result[0][0] else 0
                next_sn = max_sn + 1

                self.sn_input.setText(str(next_sn))
                self.sn_input.setReadOnly(True)  # Prevent manual editing
            except Exception as e:
                self.logging_service.error(f"Error auto-generating SN: {str(e)}")
                # If error, leave it editable and show placeholder
                self.sn_input.setPlaceholderText("Auto-generated (1 if first report)")
            return

        if not self.report_data:
            return

        # Basic Info
        self.sn_input.setText(str(self.report_data.get('sn', '')))
        self.sn_input.setReadOnly(True)  # SN shouldn't be edited
        self.report_number_input.setText(self.report_data.get('report_number', ''))
        self.report_number_input.setReadOnly(True)  # Report number shouldn't be edited

        # Parse and set report date
        report_date_str = self.report_data.get('report_date', '')
        if report_date_str:
            date = self.parse_date(report_date_str)
            if date:
                self.report_date_input.setDate(date)

        self.outgoing_letter_input.setText(self.report_data.get('outgoing_letter_number', ''))

        status = self.report_data.get('status', 'Open')
        index = self.status_combo.findText(status)
        if index >= 0:
            self.status_combo.setCurrentIndex(index)

        # Entity Details
        self.entity_name_input.setText(self.report_data.get('reported_entity_name', ''))
        self.legal_owner_input.setText(self.report_data.get('legal_entity_owner', ''))

        gender = self.report_data.get('gender', '')
        index = self.gender_combo.findText(gender)
        if index >= 0:
            self.gender_combo.setCurrentIndex(index)

        self.nationality_input.setText(self.report_data.get('nationality', ''))
        self.id_cr_input.setText(self.report_data.get('id_cr', ''))
        self.account_input.setText(self.report_data.get('account_membership', ''))
        self.branch_input.setText(self.report_data.get('branch_id', ''))
        self.cic_input.setText(self.report_data.get('cic', ''))

        # Suspicion Details
        self.first_reason_input.setPlainText(self.report_data.get('first_reason_for_suspicion', ''))
        self.second_reason_input.setPlainText(self.report_data.get('second_reason_for_suspicion', ''))
        self.transaction_type_input.setText(self.report_data.get('type_of_suspected_transaction', ''))

        arb_staff = self.report_data.get('arb_staff', '')
        index = self.arb_staff_combo.findText(arb_staff)
        if index >= 0:
            self.arb_staff_combo.setCurrentIndex(index)

        self.total_transaction_input.setText(self.report_data.get('total_transaction', ''))

        # Classification
        self.classification_input.setText(self.report_data.get('report_classification', ''))
        self.report_source_input.setText(self.report_data.get('report_source', ''))
        self.reporting_entity_input.setText(self.report_data.get('reporting_entity', ''))

        paper_automated = self.report_data.get('paper_or_automated', '')
        index = self.paper_automated_combo.findText(paper_automated)
        if index >= 0:
            self.paper_automated_combo.setCurrentIndex(index)

        self.reporter_initials_input.setText(self.report_data.get('reporter_initials', ''))

        # Dates
        sending_date_str = self.report_data.get('sending_date', '')
        if sending_date_str:
            date = self.parse_date(sending_date_str)
            if date:
                self.sending_date_input.setDate(date)

        self.original_copy_input.setText(self.report_data.get('original_copy_confirmation', ''))

        # FIU Details
        self.fiu_number_input.setText(self.report_data.get('fiu_number', ''))

        fiu_receive_date_str = self.report_data.get('fiu_letter_receive_date', '')
        if fiu_receive_date_str:
            date = self.parse_date(fiu_receive_date_str)
            if date:
                self.fiu_receive_date_input.setDate(date)

        self.fiu_feedback_input.setPlainText(self.report_data.get('fiu_feedback', ''))
        self.fiu_letter_number_input.setText(self.report_data.get('fiu_letter_number', ''))

        fiu_date_str = self.report_data.get('fiu_date', '')
        if fiu_date_str:
            date = self.parse_date(fiu_date_str)
            if date:
                self.fiu_date_input.setDate(date)

    def parse_date(self, date_str):
        """Parse date string in DD/MM/YYYY format."""
        try:
            parts = date_str.split('/')
            if len(parts) == 3:
                day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
                return QDate(year, month, day)
        except:
            pass
        return None

    def validate_form(self):
        """Validate form data."""
        errors = []

        # Required fields
        if not self.sn_input.text().strip():
            errors.append("Serial Number is required")
        elif not self.sn_input.text().strip().isdigit():
            errors.append("Serial Number must be a number")

        if not self.report_number_input.text().strip():
            errors.append("Report Number is required")
        elif not re.match(r'^\d{4}/\d{2}/\d{3}$', self.report_number_input.text().strip()):
            errors.append("Report Number must be in format YYYY/MM/NNN (e.g., 2025/11/001)")

        if not self.entity_name_input.text().strip():
            errors.append("Reported Entity Name is required")

        # Validate reporter initials if provided
        initials = self.reporter_initials_input.text().strip()
        if initials and not re.match(r'^[A-Z]{2}$', initials):
            errors.append("Reporter Initials must be 2 uppercase letters")

        # Validate total transaction format if provided
        total_transaction = self.total_transaction_input.text().strip()
        if total_transaction and not re.match(r'^\d+\s*SAR$', total_transaction):
            errors.append("Total Transaction must be in format: amount SAR (e.g., 605040 SAR)")

        if errors:
            QMessageBox.warning(
                self,
                "Validation Error",
                "Please fix the following errors:\n\n" + "\n".join(f"• {e}" for e in errors)
            )
            return False

        return True

    def get_form_data(self):
        """Get form data as dictionary."""
        data = {
            'sn': int(self.sn_input.text().strip()),
            'report_number': self.report_number_input.text().strip(),
            'report_date': self.report_date_input.date().toString("dd/MM/yyyy"),
            'outgoing_letter_number': self.outgoing_letter_input.text().strip() or None,
            'reported_entity_name': self.entity_name_input.text().strip(),
            'legal_entity_owner': self.legal_owner_input.text().strip() or None,
            'gender': self.gender_combo.currentText() or None,
            'nationality': self.nationality_input.text().strip() or None,
            'id_cr': self.id_cr_input.text().strip() or None,
            'account_membership': self.account_input.text().strip() or None,
            'branch_id': self.branch_input.text().strip() or None,
            'cic': self.cic_input.text().strip() or None,
            'first_reason_for_suspicion': self.first_reason_input.toPlainText().strip() or None,
            'second_reason_for_suspicion': self.second_reason_input.toPlainText().strip() or None,
            'type_of_suspected_transaction': self.transaction_type_input.text().strip() or None,
            'arb_staff': self.arb_staff_combo.currentText() or None,
            'total_transaction': self.total_transaction_input.text().strip() or None,
            'report_classification': self.classification_input.text().strip() or None,
            'report_source': self.report_source_input.text().strip() or None,
            'reporting_entity': self.reporting_entity_input.text().strip() or None,
            'paper_or_automated': self.paper_automated_combo.currentText() or None,
            'reporter_initials': self.reporter_initials_input.text().strip() or None,
            'sending_date': self.sending_date_input.date().toString("dd/MM/yyyy") if self.sending_date_input.date().isValid() else None,
            'original_copy_confirmation': self.original_copy_input.text().strip() or None,
            'fiu_number': self.fiu_number_input.text().strip() or None,
            'fiu_letter_receive_date': self.fiu_receive_date_input.date().toString("dd/MM/yyyy") if self.fiu_receive_date_input.date().isValid() else None,
            'fiu_feedback': self.fiu_feedback_input.toPlainText().strip() or None,
            'fiu_letter_number': self.fiu_letter_number_input.text().strip() or None,
            'fiu_date': self.fiu_date_input.date().toString("dd/MM/yyyy") if self.fiu_date_input.date().isValid() else None,
            'status': self.status_combo.currentText()
        }

        return data

    def save_report(self):
        """Save the report."""
        if not self.validate_form():
            return

        form_data = self.get_form_data()

        try:
            if self.is_edit_mode:
                # Update existing report
                report_id = self.report_data.get('report_id') or self.report_data.get('id')
                if not report_id:
                    # Log available keys for debugging
                    available_keys = ', '.join(self.report_data.keys()) if self.report_data else 'None'
                    error_msg = f"Report ID not found in report data. Available keys: {available_keys}"
                    self.logging_service.error(error_msg)
                    raise ValueError(error_msg)

                # Create version snapshot before updating
                snapshot_success, version_id, snapshot_msg = self.report_service.create_version_snapshot(
                    report_id,
                    f"Modified by {self.current_user['username']}"
                )

                success, message = self.report_service.update_report(report_id, form_data)
            else:
                # Create new report
                success, report_id, message = self.report_service.create_report(form_data)

            if success:
                QMessageBox.information(
                    self,
                    "Success",
                    message
                )
                self.report_saved.emit()
                self.accept()
            else:
                QMessageBox.critical(
                    self,
                    "Error",
                    message
                )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to save report: {str(e)}"
            )
            self.logging_service.error(f"Report save error: {str(e)}", exc_info=True)

    def view_history(self):
        """View version history for this report."""
        if not self.is_edit_mode or not self.report_data:
            return

        report_id = self.report_data.get('report_id') or self.report_data.get('id')
        if not report_id:
            QMessageBox.warning(self, "Error", "Report ID not found")
            return

        try:
            from ui.dialogs.version_history_dialog import VersionHistoryDialog

            dialog = VersionHistoryDialog(
                self.report_service,
                report_id,
                self.current_user,
                self
            )
            dialog.version_restored.connect(self.on_version_restored)
            dialog.exec()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open version history: {str(e)}")

    def on_version_restored(self, version_id):
        """
        Handle version restoration.

        Args:
            version_id: Version ID that was restored
        """
        # Reload the report data
        try:
            report_id = self.report_data.get('report_id') or self.report_data.get('id')
            refreshed_report = self.report_service.get_report(report_id)
            if refreshed_report:
                self.report_data = refreshed_report
                self.load_data()
                QMessageBox.information(
                    self,
                    "Version Restored",
                    "The report has been restored to the selected version. Please review the changes."
                )
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to reload report data: {str(e)}")

    def submit_for_approval(self):
        """Submit the report for admin approval."""
        if not self.is_edit_mode or not self.report_data:
            return

        report_id = self.report_data.get('report_id') or self.report_data.get('id')
        if not report_id:
            QMessageBox.warning(self, "Error", "Report ID not found")
            return

        # Confirm submission
        reply = QMessageBox.question(
            self,
            "Submit for Approval",
            "Are you sure you want to submit this report for admin approval?\n\n"
            "Once submitted, you won't be able to edit it until an admin reviews it.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            success, approval_id, message = self.report_service.request_approval(
                report_id,
                f"Submitted by {self.current_user['username']}"
            )

            if success:
                QMessageBox.information(self, "Success", message)
                self.report_saved.emit()
                self.accept()
            else:
                QMessageBox.warning(self, "Error", message)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to submit for approval: {str(e)}")
