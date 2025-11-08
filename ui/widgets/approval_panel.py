"""
Approval Panel for managing report approval requests.
Admin-only view for approving, rejecting, or requesting rework on reports.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QHeaderView, QFrame, QDialog, QTextEdit,
                             QMessageBox, QRadioButton, QButtonGroup, QLineEdit)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QIcon
from datetime import datetime


class ApprovalDecisionDialog(QDialog):
    """Dialog for approving or rejecting a report."""

    def __init__(self, approval_data, parent=None):
        """
        Initialize the approval decision dialog.

        Args:
            approval_data: Dictionary with approval request details
            parent: Parent widget
        """
        super().__init__(parent)
        self.approval_data = approval_data
        self.decision = None  # 'approve', 'reject', or 'rework'
        self.comment = ""

        self.setup_ui()

    def setup_ui(self):
        """Setup the user interface."""
        self.setWindowTitle("Review Approval Request")
        self.setMinimumSize(500, 400)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        header_label = QLabel(f"Review Approval Request")
        header_font = QFont()
        header_font.setPointSize(14)
        header_font.setWeight(QFont.Weight.Bold)
        header_label.setFont(header_font)
        layout.addWidget(header_label)

        # Report details
        details_frame = QFrame()
        details_frame.setObjectName("detailsFrame")
        details_layout = QVBoxLayout(details_frame)

        details_layout.addWidget(QLabel(f"Report Number: {self.approval_data['report_number']}"))
        details_layout.addWidget(QLabel(f"Entity: {self.approval_data['reported_entity_name']}"))
        details_layout.addWidget(QLabel(f"Requested By: {self.approval_data['requested_by']}"))
        details_layout.addWidget(QLabel(f"Requested At: {self.approval_data['requested_at']}"))

        if self.approval_data.get('comment'):
            request_comment = QLabel(f"Request Comment: {self.approval_data['comment']}")
            request_comment.setWordWrap(True)
            details_layout.addWidget(request_comment)

        layout.addWidget(details_frame)

        # Decision options
        decision_label = QLabel("Your Decision:")
        decision_label.setObjectName("subtitleLabel")
        decision_font = QFont()
        decision_font.setWeight(QFont.Weight.Bold)
        decision_label.setFont(decision_font)
        layout.addWidget(decision_label)

        self.decision_group = QButtonGroup()

        self.approve_radio = QRadioButton("Approve - Report is accurate and complete")
        self.approve_radio.setChecked(True)
        self.decision_group.addButton(self.approve_radio, 1)
        layout.addWidget(self.approve_radio)

        self.rework_radio = QRadioButton("Request Rework - Report needs corrections")
        self.decision_group.addButton(self.rework_radio, 2)
        layout.addWidget(self.rework_radio)

        self.reject_radio = QRadioButton("Reject - Report is invalid")
        self.decision_group.addButton(self.reject_radio, 3)
        layout.addWidget(self.reject_radio)

        # Comment field
        comment_label = QLabel("Comment (optional but recommended):")
        comment_label.setObjectName("subtitleLabel")
        comment_label.setFont(decision_font)
        layout.addWidget(comment_label)

        self.comment_edit = QTextEdit()
        self.comment_edit.setPlaceholderText("Enter your feedback, suggestions, or reasons for this decision...")
        self.comment_edit.setMaximumHeight(100)
        layout.addWidget(self.comment_edit)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_button = QPushButton("Cancel")
        cancel_button.setObjectName("secondaryButton")
        cancel_button.setMinimumWidth(100)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        submit_button = QPushButton("Submit Decision")
        submit_button.setObjectName("primaryButton")
        submit_button.setMinimumWidth(100)
        submit_button.clicked.connect(self.submit_decision)
        button_layout.addWidget(submit_button)

        layout.addLayout(button_layout)

    def submit_decision(self):
        """Submit the approval decision."""
        self.comment = self.comment_edit.toPlainText().strip()

        if self.approve_radio.isChecked():
            self.decision = 'approve'
        elif self.rework_radio.isChecked():
            self.decision = 'rework'
            if not self.comment:
                QMessageBox.warning(self, "Comment Required",
                                  "Please provide feedback on what needs to be reworked.")
                return
        elif self.reject_radio.isChecked():
            self.decision = 'reject'
            if not self.comment:
                QMessageBox.warning(self, "Comment Required",
                                  "Please provide a reason for rejection.")
                return

        self.accept()


class ApprovalPanel(QWidget):
    """
    Approval panel widget for managing report approval requests.

    Signals:
        approval_processed: Emitted when an approval is processed
    """

    approval_processed = pyqtSignal()

    def __init__(self, report_service, current_user):
        """
        Initialize the approval panel.

        Args:
            report_service: ReportService instance
            current_user: Current user dictionary
        """
        super().__init__()
        self.report_service = report_service
        self.current_user = current_user
        self.pending_approvals = []

        self.setup_ui()
        self.load_pending_approvals()

    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header section
        header_layout = QHBoxLayout()

        title_label = QLabel("Approval Management")
        title_label.setObjectName("titleLabel")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setWeight(QFont.Weight.Bold)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # Refresh button
        refresh_button = QPushButton("Refresh")
        refresh_button.setObjectName("primaryButton")
        refresh_button.setMinimumWidth(100)
        refresh_button.clicked.connect(self.load_pending_approvals)
        header_layout.addWidget(refresh_button)

        layout.addLayout(header_layout)

        # Info label
        self.info_label = QLabel()
        self.info_label.setObjectName("subtitleLabel")
        layout.addWidget(self.info_label)

        # Table for pending approvals
        self.approvals_table = QTableWidget()
        self.approvals_table.setColumnCount(7)
        self.approvals_table.setHorizontalHeaderLabels([
            'Report #', 'Entity Name', 'Requested By', 'Requested At',
            'Status', 'Comment', 'Actions'
        ])
        self.approvals_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.approvals_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.approvals_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.approvals_table.verticalHeader().setVisible(False)

        # Set column widths
        header = self.approvals_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(0, 100)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(2, 120)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(3, 150)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(4, 100)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(6, 150)

        # Set row height to accommodate buttons properly
        self.approvals_table.verticalHeader().setDefaultSectionSize(50)
        self.approvals_table.verticalHeader().setMinimumSectionSize(50)

        layout.addWidget(self.approvals_table)

        # Empty state label
        self.empty_label = QLabel("No pending approval requests")
        self.empty_label.setObjectName("hintLabel")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setVisible(False)
        layout.addWidget(self.empty_label)

    def load_pending_approvals(self):
        """Load pending approval requests from database."""
        try:
            self.pending_approvals = self.report_service.get_pending_approvals()

            if not self.pending_approvals:
                self.info_label.setText("No pending approval requests at this time.")
                self.approvals_table.setVisible(False)
                self.empty_label.setVisible(True)
                return

            self.info_label.setText(f"Showing {len(self.pending_approvals)} pending approval request(s)")
            self.approvals_table.setVisible(True)
            self.empty_label.setVisible(False)

            self.approvals_table.setRowCount(len(self.pending_approvals))

            for row, approval in enumerate(self.pending_approvals):
                # Set row height to ensure buttons are visible
                self.approvals_table.setRowHeight(row, 50)
                # Report number
                report_num_item = QTableWidgetItem(str(approval['report_number']))
                self.approvals_table.setItem(row, 0, report_num_item)

                # Entity name
                entity_item = QTableWidgetItem(approval['reported_entity_name'])
                self.approvals_table.setItem(row, 1, entity_item)

                # Requested by
                requester_item = QTableWidgetItem(approval['requested_by'])
                self.approvals_table.setItem(row, 2, requester_item)

                # Requested at
                requested_at = approval['requested_at']
                try:
                    dt = datetime.fromisoformat(requested_at.replace('Z', '+00:00'))
                    formatted_date = dt.strftime('%Y-%m-%d %H:%M')
                except:
                    formatted_date = requested_at
                date_item = QTableWidgetItem(formatted_date)
                self.approvals_table.setItem(row, 3, date_item)

                # Report status
                status_item = QTableWidgetItem(approval.get('report_status', 'N/A'))
                self.approvals_table.setItem(row, 4, status_item)

                # Comment
                comment = approval.get('comment', '')
                comment_item = QTableWidgetItem(comment[:50] + '...' if len(comment) > 50 else comment)
                comment_item.setToolTip(comment)
                self.approvals_table.setItem(row, 5, comment_item)

                # Actions - Review button
                actions_widget = QWidget()
                actions_layout = QHBoxLayout(actions_widget)
                actions_layout.setContentsMargins(8, 5, 8, 5)  # Better spacing

                review_button = QPushButton("Review")
                review_button.setObjectName("primaryButton")
                review_button.setMinimumHeight(32)  # Ensure button is clickable
                review_button.setMaximumWidth(90)
                review_button.clicked.connect(lambda checked, r=row: self.review_approval(r))
                actions_layout.addWidget(review_button)

                actions_layout.addStretch()

                self.approvals_table.setCellWidget(row, 6, actions_widget)

        except Exception as e:
            self.info_label.setText(f"Error loading approvals: {str(e)}")
            self.approvals_table.setVisible(False)
            self.empty_label.setVisible(True)

    def review_approval(self, row):
        """
        Review an approval request.

        Args:
            row: Table row index
        """
        if row >= len(self.pending_approvals):
            return

        approval_data = self.pending_approvals[row]

        # Show decision dialog
        dialog = ApprovalDecisionDialog(approval_data, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.process_decision(approval_data, dialog.decision, dialog.comment)

    def process_decision(self, approval_data, decision, comment):
        """
        Process the approval decision.

        Args:
            approval_data: Approval request data
            decision: 'approve', 'reject', or 'rework'
            comment: Admin's comment
        """
        try:
            approval_id = approval_data['approval_id']

            if decision == 'approve':
                success, message = self.report_service.approve_report(approval_id, comment)
            else:
                request_rework = (decision == 'rework')
                success, message = self.report_service.reject_report(
                    approval_id, comment, request_rework
                )

            if success:
                QMessageBox.information(self, "Success", message)
                self.approval_processed.emit()
                self.load_pending_approvals()  # Reload the list
            else:
                QMessageBox.warning(self, "Error", message)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to process approval: {str(e)}")

    def refresh(self):
        """Refresh the pending approvals list."""
        self.load_pending_approvals()
