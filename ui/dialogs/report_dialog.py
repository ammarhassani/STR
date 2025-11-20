"""
Report dialog for creating and editing financial crime reports.
Comprehensive form with validation for all report fields.
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QTextEdit, QComboBox, QDateEdit,
                             QTabWidget, QWidget, QPushButton, QMessageBox,
                             QGroupBox, QFormLayout, QScrollArea, QFrame,
                             QCheckBox, QSizePolicy)
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

    def __init__(self, report_service, logging_service, current_user, auth_service=None, approval_service=None, report_number_service=None, report_data=None, parent=None):
        """
        Initialize report dialog.

        Args:
            report_service: ReportService instance
            logging_service: LoggingService instance
            current_user: Current user dictionary
            auth_service: AuthService instance (optional, needed for version snapshots)
            approval_service: ApprovalService instance (optional, needed for approval requests)
            report_number_service: ReportNumberService instance (optional, will create if not provided)
            report_data: Existing report data for editing (None for new report)
            parent: Parent widget
        """
        super().__init__(parent)
        self.report_service = report_service
        self.logging_service = logging_service
        self.current_user = current_user
        self.auth_service = auth_service
        self.approval_service = approval_service
        self.report_data = report_data
        self.is_edit_mode = report_data is not None

        # Initialize dropdown service for managing dropdowns
        from services.dropdown_service import DropdownService
        self.dropdown_service = DropdownService(report_service.db_manager, logging_service)

        # Use provided report number service or create new one for backward compatibility
        if report_number_service:
            self.report_number_service = report_number_service
        else:
            from services.report_number_service import ReportNumberService
            self.report_number_service = ReportNumberService(report_service.db_manager, logging_service)

        # Initialize validation service for field validation
        from services.validation_service import ValidationService
        self.validation_service = ValidationService(report_service.db_manager, logging_service)

        # Initialize version service for version snapshots (only if auth_service provided)
        self.version_service = None
        if auth_service:
            from services.version_service import VersionService
            self.version_service = VersionService(report_service.db_manager, logging_service, auth_service, report_service)

        # Store reservation info (for new reports only)
        self.reservation_info = None

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

        # Note: outgoing_letter_number and status fields removed per requirements #1, #2

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

        # Legal Entity Owner - CHANGED TO CHECKBOX (Req #3)
        self.legal_owner_checkbox = QCheckBox("Is Legal Entity Owner")
        layout.addRow("Legal Entity Owner:", self.legal_owner_checkbox)

        # Gender - CHANGED TO USE DROPDOWN SERVICE
        self.gender_combo = QComboBox()
        self.gender_combo.setEditable(True)  # Allow custom values
        self.gender_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)  # Accept custom input
        genders = self.dropdown_service.get_active_dropdown_values('gender')
        self.gender_combo.addItem('')  # Empty option
        self.gender_combo.addItems(genders)
        layout.addRow("Gender:", self.gender_combo)

        # Nationality - CHANGED TO DROPDOWN (Req #4)
        self.nationality_combo = QComboBox()
        self.nationality_combo.setEditable(True)  # Allow filtering/searching
        self.nationality_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        # Load nationalities from dropdown service
        nationalities = self.dropdown_service.get_active_dropdown_values('nationality')
        self.nationality_combo.addItem('')  # Empty option
        self.nationality_combo.addItems(nationalities)
        self.nationality_combo.currentTextChanged.connect(self.validate_id_cr)
        layout.addRow("Nationality:", self.nationality_combo)

        # ID/CR
        self.id_cr_input = QLineEdit()
        self.id_cr_input.setPlaceholderText("Enter ID or Commercial Registration number")
        self.id_cr_input.textChanged.connect(self.validate_id_cr)
        layout.addRow("ID/CR:", self.id_cr_input)

        # ID/CR Type Checkbox
        self.id_type_checkbox = QCheckBox("Is Commercial Registration (CR)")
        self.id_type_checkbox.setToolTip("Check if this is a CR for corporation/establishment, uncheck for individual ID")
        self.id_type_checkbox.stateChanged.connect(self.update_id_type_field)
        self.id_type_checkbox.stateChanged.connect(self.validate_id_cr)
        layout.addRow("ID Type:", self.id_type_checkbox)

        # ID Type Display - AUTO-GENERATED READ-ONLY
        self.id_type_display = QLineEdit()
        self.id_type_display.setReadOnly(True)
        self.id_type_display.setText("ID")  # Default
        self.id_type_display.setObjectName("readOnlyField")
        layout.addRow("ID/CR Type:", self.id_type_display)

        # Account/Membership
        self.account_input = QLineEdit()
        self.account_input.setPlaceholderText("Enter account or membership number")
        self.account_input.textChanged.connect(self.validate_account_membership)
        layout.addRow("Account/Membership:", self.account_input)

        # Account Membership Checkbox - NEW (Req #5)
        self.acc_membership_checkbox = QCheckBox("Is Membership?")
        self.acc_membership_checkbox.setToolTip("Check if this is a membership account, uncheck for current account")
        self.acc_membership_checkbox.stateChanged.connect(self.update_relationship_field)
        self.acc_membership_checkbox.stateChanged.connect(self.validate_account_membership)
        layout.addRow("Account Type:", self.acc_membership_checkbox)

        # Relationship - AUTO-GENERATED READ-ONLY (Req #5)
        self.relationship_display = QLineEdit()
        self.relationship_display.setReadOnly(True)
        self.relationship_display.setText("Current Account")  # Default
        self.relationship_display.setObjectName("readOnlyField")
        layout.addRow("Relationship:", self.relationship_display)

        # Branch ID
        self.branch_input = QLineEdit()
        self.branch_input.setPlaceholderText("Enter branch ID")
        layout.addRow("Branch ID:", self.branch_input)

        # CIC - WITH AUTO-PADDING TO 16 DIGITS (Req #6)
        self.cic_input = QLineEdit()
        self.cic_input.setPlaceholderText("Enter CIC number (will auto-pad to 16 digits)")
        self.cic_input.setMaxLength(16)
        self.cic_input.textChanged.connect(self.format_cic)
        self.cic_input.editingFinished.connect(self.finalize_cic_format)
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
        self.first_reason_input.setMinimumHeight(80)
        self.first_reason_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addRow("First Reason for Suspicion:", self.first_reason_input)

        # Second Reason for Suspicion - CHANGED TO DROPDOWN (Req #7)
        self.second_reason_combo = QComboBox()
        self.second_reason_combo.setEditable(True)  # Allow custom values
        second_reasons = self.dropdown_service.get_active_dropdown_values('second_reason_for_suspicion')
        self.second_reason_combo.addItem('')  # Empty option
        self.second_reason_combo.addItems(second_reasons)
        layout.addRow("Second Reason for Suspicion:", self.second_reason_combo)

        # Type of Suspected Transaction - CHANGED TO DROPDOWN (Req #8)
        self.transaction_type_combo = QComboBox()
        self.transaction_type_combo.setEditable(True)  # Allow custom values
        transaction_types = self.dropdown_service.get_active_dropdown_values('type_of_suspected_transaction')
        self.transaction_type_combo.addItem('')  # Empty option
        self.transaction_type_combo.addItems(transaction_types)
        layout.addRow("Type of Suspected Transaction:", self.transaction_type_combo)

        # ARB Staff - CHANGED TO USE DROPDOWN SERVICE
        self.arb_staff_combo = QComboBox()
        self.arb_staff_combo.setEditable(True)  # Allow custom values
        self.arb_staff_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)  # Accept custom input
        arb_staff_values = self.dropdown_service.get_active_dropdown_values('arb_staff')
        self.arb_staff_combo.addItem('')  # Empty option
        self.arb_staff_combo.addItems(arb_staff_values)
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

        # Report Classification - CHANGED TO DROPDOWN (Req #11)
        self.classification_combo = QComboBox()
        self.classification_combo.setEditable(True)  # Allow custom values
        classifications = self.dropdown_service.get_active_dropdown_values('report_classification')
        self.classification_combo.addItem('')  # Empty option
        self.classification_combo.addItems(classifications)
        layout.addRow("Report Classification:", self.classification_combo)

        # Report Source - CHANGED TO DROPDOWN (Req #12)
        self.report_source_combo = QComboBox()
        self.report_source_combo.setEditable(True)  # Allow custom values
        self.report_source_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)  # Accept custom input
        report_sources = self.dropdown_service.get_active_dropdown_values('report_source')
        self.report_source_combo.addItem('')  # Empty option
        self.report_source_combo.addItems(report_sources)
        layout.addRow("Report Source:", self.report_source_combo)

        # Reporting Entity - CHANGED TO DROPDOWN (Req #13)
        self.reporting_entity_combo = QComboBox()
        self.reporting_entity_combo.setEditable(True)  # Allow custom values
        self.reporting_entity_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)  # Accept custom input
        reporting_entities = self.dropdown_service.get_active_dropdown_values('reporting_entity')
        self.reporting_entity_combo.addItem('')  # Empty option
        self.reporting_entity_combo.addItems(reporting_entities)
        layout.addRow("Reporting Entity:", self.reporting_entity_combo)

        # Note: paper_or_automated removed (Req #14)

        # Reporter Initials
        self.reporter_initials_input = QLineEdit()
        self.reporter_initials_input.setPlaceholderText("Enter 2 uppercase letters (e.g., ZM)")
        self.reporter_initials_input.setMaxLength(2)
        layout.addRow("Reporter Initials:", self.reporter_initials_input)

        # Sending Date - NULLABLE (Req #15)
        self.sending_date_input = QDateEdit()
        self.sending_date_input.setCalendarPopup(True)
        self.sending_date_input.setDate(QDate.currentDate())
        self.sending_date_input.setDisplayFormat("dd/MM/yyyy")
        self.sending_date_input.setSpecialValueText(" ")  # Allow empty/null
        self.sending_date_input.setMinimumDate(QDate(1900, 1, 1))  # Allow clearing
        layout.addRow("Sending Date:", self.sending_date_input)

        # Note: original_copy_confirmation removed (Req #16)

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

        # FIU Letter Receive Date - NULLABLE (Req #17)
        self.fiu_receive_date_input = QDateEdit()
        self.fiu_receive_date_input.setCalendarPopup(True)
        self.fiu_receive_date_input.setDate(QDate.currentDate())
        self.fiu_receive_date_input.setDisplayFormat("dd/MM/yyyy")
        self.fiu_receive_date_input.setSpecialValueText(" ")  # Allow empty/null
        self.fiu_receive_date_input.setMinimumDate(QDate(1900, 1, 1))  # Allow clearing
        layout.addRow("FIU Letter Receive Date:", self.fiu_receive_date_input)

        # FIU Feedback - CHANGED TO DROPDOWN (Req #18)
        self.fiu_feedback_combo = QComboBox()
        self.fiu_feedback_combo.setEditable(True)  # Allow custom values
        fiu_feedbacks = self.dropdown_service.get_active_dropdown_values('fiu_feedback')
        self.fiu_feedback_combo.addItem('')  # Empty option
        self.fiu_feedback_combo.addItems(fiu_feedbacks)
        layout.addRow("FIU Feedback:", self.fiu_feedback_combo)

        # FIU Letter Number
        self.fiu_letter_number_input = QLineEdit()
        self.fiu_letter_number_input.setPlaceholderText("Enter FIU letter number")
        layout.addRow("FIU Letter Number:", self.fiu_letter_number_input)

        # Note: FIU Date removed (Req #19)

        scroll.setWidget(container)

        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll)

        return tab

    def format_cic(self):
        """Auto-format CIC to 16 digits with leading zeros (Req #6)."""
        cic_text = self.cic_input.text().replace(' ', '').replace('-', '')
        if cic_text and cic_text.isdigit():
            # Pad to 16 digits only if user is done typing (on focus out this finalizes)
            # For now, just ensure it doesn't exceed 16
            if len(cic_text) > 16:
                self.cic_input.setText(cic_text[:16])

    def finalize_cic_format(self):
        """Finalize CIC formatting when user leaves the field."""
        cic_text = self.cic_input.text().replace(' ', '').replace('-', '')
        if cic_text and cic_text.isdigit():
            # Pad to 16 digits with leading zeros
            formatted_cic = cic_text.zfill(16)
            self.cic_input.setText(formatted_cic)

    def update_relationship_field(self):
        """Auto-update relationship field based on acc_membership_checkbox."""
        if self.acc_membership_checkbox.isChecked():
            self.relationship_display.setText("Membership")
        else:
            self.relationship_display.setText("Current Account")

    def update_id_type_field(self):
        """Auto-update ID type field based on id_type_checkbox."""
        if self.id_type_checkbox.isChecked():
            self.id_type_display.setText("CR")
        else:
            self.id_type_display.setText("ID")

    def load_data(self):
        """Load existing report data if in edit mode or reserve numbers for new reports."""
        # Reserve report number and serial number for new reports (5-minute reservation)
        if not self.is_edit_mode:
            try:
                # Reserve next available numbers using concurrent-safe service
                success, reservation, message = self.report_number_service.reserve_next_numbers(
                    self.current_user['username']
                )

                if success and reservation:
                    self.reservation_info = reservation

                    # Set the reserved numbers
                    self.sn_input.setText(str(reservation['serial_number']))
                    self.report_number_input.setText(reservation['report_number'])

                    # Make them read-only
                    self.sn_input.setReadOnly(True)
                    self.report_number_input.setReadOnly(True)

                    # Show gap notification if there's a gap being reused
                    if reservation.get('has_gap') and reservation.get('gap_info'):
                        gap_info = reservation['gap_info']
                        QMessageBox.information(
                            self,
                            "Gap Detected",
                            f"📋 Gap Notice:\n\n{gap_info['message']}\n\n"
                            f"The system is reusing this number to fill the gap in the sequence.\n\n"
                            f"Deleted on: {gap_info.get('deleted_at', 'Unknown')}\n"
                            f"Deleted by: {gap_info.get('deleted_by', 'Unknown')}"
                        )

                    self.logging_service.info(
                        f"Reserved numbers for {self.current_user['username']}: "
                        f"Report# {reservation['report_number']}, SN {reservation['serial_number']}"
                    )
                else:
                    # Fallback to old method if reservation fails
                    QMessageBox.warning(
                        self,
                        "Reservation Failed",
                        f"Could not reserve report number: {message}\n\n"
                        "Falling back to manual entry."
                    )
                    self.sn_input.setPlaceholderText("Enter serial number")
                    self.report_number_input.setPlaceholderText("Enter report number")

            except Exception as e:
                self.logging_service.error(f"Error reserving numbers: {str(e)}")
                QMessageBox.warning(
                    self,
                    "Error",
                    f"Failed to reserve numbers: {str(e)}\n\nPlease enter manually."
                )
                self.sn_input.setPlaceholderText("Enter serial number")
                self.report_number_input.setPlaceholderText("Enter report number")
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

        # Note: outgoing_letter_number and status removed

        # Entity Details
        self.entity_name_input.setText(self.report_data.get('reported_entity_name', ''))

        # Legal Entity Owner - CHECKBOX (Req #3)
        legal_owner_checked = self.report_data.get('legal_entity_owner_checkbox', 0)
        self.legal_owner_checkbox.setChecked(bool(legal_owner_checked))

        gender = self.report_data.get('gender', '')
        index = self.gender_combo.findText(gender)
        if index >= 0:
            self.gender_combo.setCurrentIndex(index)

        # Nationality - DROPDOWN (Req #4)
        nationality = self.report_data.get('nationality', '')
        if nationality:
            index = self.nationality_combo.findText(nationality)
            if index >= 0:
                self.nationality_combo.setCurrentIndex(index)
            else:
                # If not in list, add it as custom value
                self.nationality_combo.setEditText(nationality)

        self.id_cr_input.setText(self.report_data.get('id_cr', ''))

        # ID Type - Set checkbox based on saved value
        id_type = self.report_data.get('id_type', 'ID')
        self.id_type_checkbox.setChecked(id_type == 'CR')
        self.update_id_type_field()  # Update ID type display

        self.account_input.setText(self.report_data.get('account_membership', ''))

        # Account Membership Checkbox (Req #5)
        acc_membership_checked = self.report_data.get('acc_membership_checkbox', 0)
        self.acc_membership_checkbox.setChecked(bool(acc_membership_checked))
        self.update_relationship_field()  # Update relationship display

        self.branch_input.setText(self.report_data.get('branch_id', ''))

        # CIC - Format to 16 digits (Req #6)
        cic = self.report_data.get('cic', '')
        if cic:
            # Ensure it's formatted to 16 digits
            cic_formatted = cic.replace(' ', '').replace('-', '')
            if cic_formatted.isdigit():
                cic_formatted = cic_formatted.zfill(16)
            self.cic_input.setText(cic_formatted)

        # Suspicion Details
        self.first_reason_input.setPlainText(self.report_data.get('first_reason_for_suspicion', ''))

        # Second Reason - DROPDOWN (Req #7)
        second_reason = self.report_data.get('second_reason_for_suspicion', '')
        if second_reason:
            index = self.second_reason_combo.findText(second_reason)
            if index >= 0:
                self.second_reason_combo.setCurrentIndex(index)
            else:
                self.second_reason_combo.setEditText(second_reason)

        # Transaction Type - DROPDOWN (Req #8)
        transaction_type = self.report_data.get('type_of_suspected_transaction', '')
        if transaction_type:
            index = self.transaction_type_combo.findText(transaction_type)
            if index >= 0:
                self.transaction_type_combo.setCurrentIndex(index)
            else:
                self.transaction_type_combo.setEditText(transaction_type)

        arb_staff = self.report_data.get('arb_staff', '')
        index = self.arb_staff_combo.findText(arb_staff)
        if index >= 0:
            self.arb_staff_combo.setCurrentIndex(index)

        self.total_transaction_input.setText(self.report_data.get('total_transaction', ''))

        # Classification
        # Report Classification - DROPDOWN (Req #11)
        classification = self.report_data.get('report_classification', '')
        if classification:
            index = self.classification_combo.findText(classification)
            if index >= 0:
                self.classification_combo.setCurrentIndex(index)
            else:
                self.classification_combo.setEditText(classification)

        # Report Source - DROPDOWN (Req #12)
        report_source = self.report_data.get('report_source', '')
        if report_source:
            index = self.report_source_combo.findText(report_source)
            if index >= 0:
                self.report_source_combo.setCurrentIndex(index)

        # Reporting Entity - DROPDOWN (Req #13)
        reporting_entity = self.report_data.get('reporting_entity', '')
        if reporting_entity:
            index = self.reporting_entity_combo.findText(reporting_entity)
            if index >= 0:
                self.reporting_entity_combo.setCurrentIndex(index)

        # Note: paper_or_automated removed (Req #14)

        self.reporter_initials_input.setText(self.report_data.get('reporter_initials', ''))

        # Sending Date - NULLABLE (Req #15)
        sending_date_str = self.report_data.get('sending_date', '')
        if sending_date_str:
            date = self.parse_date(sending_date_str)
            if date:
                self.sending_date_input.setDate(date)
        else:
            # Clear the date if empty
            self.sending_date_input.setDate(QDate(1900, 1, 1))

        # Note: original_copy_confirmation removed (Req #16)

        # FIU Details
        self.fiu_number_input.setText(self.report_data.get('fiu_number', ''))

        # FIU Receive Date - NULLABLE (Req #17)
        fiu_receive_date_str = self.report_data.get('fiu_letter_receive_date', '')
        if fiu_receive_date_str:
            date = self.parse_date(fiu_receive_date_str)
            if date:
                self.fiu_receive_date_input.setDate(date)
        else:
            # Clear the date if empty
            self.fiu_receive_date_input.setDate(QDate(1900, 1, 1))

        # FIU Feedback - DROPDOWN (Req #18)
        fiu_feedback = self.report_data.get('fiu_feedback', '')
        if fiu_feedback:
            index = self.fiu_feedback_combo.findText(fiu_feedback)
            if index >= 0:
                self.fiu_feedback_combo.setCurrentIndex(index)
            else:
                self.fiu_feedback_combo.setEditText(fiu_feedback)

        self.fiu_letter_number_input.setText(self.report_data.get('fiu_letter_number', ''))

        # Note: fiu_date removed (Req #19)

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

        # Validate CIC if provided - MUST BE 16 DIGITS (Req #6)
        cic = self.cic_input.text().strip()
        if cic:
            cic_cleaned = cic.replace(' ', '').replace('-', '')
            if not cic_cleaned.isdigit():
                errors.append("CIC must contain only digits")
            elif len(cic_cleaned) != 16:
                errors.append("CIC must be exactly 16 digits")

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
        # Helper function to check if date is valid and not the minimum date (cleared)
        def get_date_value(date_input):
            date = date_input.date()
            if date.isValid() and date != QDate(1900, 1, 1):
                return date.toString("dd/MM/yyyy")
            return None

        data = {
            'sn': int(self.sn_input.text().strip()),
            'report_number': self.report_number_input.text().strip(),
            'report_date': self.report_date_input.date().toString("dd/MM/yyyy"),
            # REMOVED: 'outgoing_letter_number' (Req #1)
            'reported_entity_name': self.entity_name_input.text().strip(),
            # CHANGED: Legal Entity Owner to checkbox (Req #3)
            'legal_entity_owner_checkbox': 1 if self.legal_owner_checkbox.isChecked() else 0,
            'gender': self.gender_combo.currentText() or None,
            # CHANGED: Nationality to dropdown (Req #4)
            'nationality': self.nationality_combo.currentText().strip() or None,
            'id_cr': self.id_cr_input.text().strip() or None,
            # NEW: ID Type (ID or CR)
            'id_type': self.id_type_display.text(),
            'account_membership': self.account_input.text().strip() or None,
            # NEW: Account Membership Checkbox (Req #5)
            'acc_membership_checkbox': 1 if self.acc_membership_checkbox.isChecked() else 0,
            # NEW: Auto-generated Relationship field (Req #5)
            'relationship': self.relationship_display.text(),
            'branch_id': self.branch_input.text().strip() or None,
            # CHANGED: CIC with 16-digit formatting (Req #6)
            'cic': self.cic_input.text().strip() or None,
            'first_reason_for_suspicion': self.first_reason_input.toPlainText().strip() or None,
            # CHANGED: Second reason to dropdown (Req #7)
            'second_reason_for_suspicion': self.second_reason_combo.currentText().strip() or None,
            # CHANGED: Transaction type to dropdown (Req #8)
            'type_of_suspected_transaction': self.transaction_type_combo.currentText().strip() or None,
            'arb_staff': self.arb_staff_combo.currentText() or None,
            'total_transaction': self.total_transaction_input.text().strip() or None,
            # CHANGED: Report classification to dropdown (Req #11)
            'report_classification': self.classification_combo.currentText().strip() or None,
            # CHANGED: Report source to dropdown (Req #12)
            'report_source': self.report_source_combo.currentText().strip() or None,
            # CHANGED: Reporting entity to dropdown (Req #13)
            'reporting_entity': self.reporting_entity_combo.currentText().strip() or None,
            # REMOVED: 'paper_or_automated' (Req #14)
            'reporter_initials': self.reporter_initials_input.text().strip() or None,
            # CHANGED: Sending date to nullable (Req #15)
            'sending_date': get_date_value(self.sending_date_input),
            # REMOVED: 'original_copy_confirmation' (Req #16)
            'fiu_number': self.fiu_number_input.text().strip() or None,
            # CHANGED: FIU receive date to nullable (Req #17)
            'fiu_letter_receive_date': get_date_value(self.fiu_receive_date_input),
            # CHANGED: FIU feedback to dropdown (Req #18)
            'fiu_feedback': self.fiu_feedback_combo.currentText().strip() or None,
            'fiu_letter_number': self.fiu_letter_number_input.text().strip() or None,
            # REMOVED: 'fiu_date' (Req #19)
            # REMOVED: 'status' (Req #2)
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

                # Create version snapshot before updating (if version service available)
                if self.version_service:
                    snapshot_success, version_id, snapshot_msg = self.version_service.create_version_snapshot(
                        report_id,
                        f"Modified by {self.current_user['username']}"
                    )

                success, message = self.report_service.update_report(report_id, form_data)
            else:
                # Create new report
                success, report_id, message = self.report_service.create_report(form_data)

            if success:
                # Mark reservation as used (for new reports only)
                if not self.is_edit_mode and self.reservation_info:
                    try:
                        self.report_number_service.mark_reservation_used(
                            self.reservation_info['report_number'],
                            self.current_user['username']
                        )
                        self.logging_service.info(
                            f"Marked reservation {self.reservation_info['report_number']} as used"
                        )
                        # Clear reservation so closeEvent doesn't cancel it
                        self.reservation_info = None
                    except Exception as e:
                        self.logging_service.error(f"Error marking reservation as used: {str(e)}")

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
            if not self.approval_service:
                QMessageBox.warning(
                    self,
                    "Approval Service Unavailable",
                    "Cannot submit for approval - approval service not initialized."
                )
                return

            success, approval_id, message = self.approval_service.request_approval(
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

    def validate_id_cr(self):
        """Validate ID/CR field in real-time."""
        value = self.id_cr_input.text()

        # Skip validation if empty
        if not value:
            self.id_cr_input.setStyleSheet("")
            return

        # Get nationality and CR checkbox state
        nationality = self.nationality_combo.currentText()
        is_cr = self.id_type_checkbox.isChecked()

        # Validate using ValidationService
        is_valid, error_msg = self.validation_service.validate_field_from_db(
            'id_cr',
            value,
            nationality=nationality,
            is_cr=is_cr
        )

        # Apply visual feedback
        if is_valid:
            self.id_cr_input.setStyleSheet("")
            self.id_cr_input.setToolTip("")
        else:
            self.id_cr_input.setStyleSheet("border: 2px solid #e74c3c;")
            self.id_cr_input.setToolTip(error_msg)

    def validate_account_membership(self):
        """Validate Account/Membership field in real-time."""
        value = self.account_input.text()

        # Skip validation if empty
        if not value:
            self.account_input.setStyleSheet("")
            return

        # Get membership checkbox state
        is_membership = self.acc_membership_checkbox.isChecked()

        # Validate using ValidationService
        is_valid, error_msg = self.validation_service.validate_field_from_db(
            'account_membership',
            value,
            is_membership=is_membership
        )

        # Apply visual feedback
        if is_valid:
            self.account_input.setStyleSheet("")
            self.account_input.setToolTip("")
        else:
            self.account_input.setStyleSheet("border: 2px solid #e74c3c;")
            self.account_input.setToolTip(error_msg)

    def closeEvent(self, event):
        """Handle dialog close event - cancel reservation if not used."""
        # Cancel reservation if dialog closed without saving (new reports only)
        if not self.is_edit_mode and self.reservation_info:
            try:
                success, message = self.report_number_service.cancel_reservation(
                    self.reservation_info['report_number'],
                    self.current_user['username']
                )
                if success:
                    self.logging_service.info(
                        f"Cancelled reservation {self.reservation_info['report_number']} "
                        f"for {self.current_user['username']} (dialog closed)"
                    )
                else:
                    self.logging_service.warning(
                        f"Failed to cancel reservation: {message}"
                    )
            except Exception as e:
                self.logging_service.error(f"Error cancelling reservation on close: {str(e)}")

        # Call parent closeEvent
        super().closeEvent(event)
