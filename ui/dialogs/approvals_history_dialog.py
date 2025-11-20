"""
Approvals History Dialog
Displays complete approval history with filtering and search capabilities (Admin-only).
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QHeaderView, QComboBox, QLineEdit, QFrame,
                             QMessageBox, QFileDialog, QWidget, QSizePolicy)
from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtGui import QFont, QColor
from datetime import datetime
import csv


class ApprovalsHistoryDialog(QDialog):
    """
    Dialog for viewing complete approval history.
    Admin-only access to all approval requests across all statuses.
    """

    def __init__(self, report_service, logging_service, parent=None):
        """
        Initialize the approvals history dialog.

        Args:
            report_service: ReportService instance
            logging_service: LoggingService instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.report_service = report_service
        self.logging_service = logging_service

        # Pagination state
        self.current_page = 0
        self.page_size = 50
        self.total_count = 0
        self.current_filter = None  # None = All

        self.setup_ui()
        self.load_approvals()

    def setup_ui(self):
        """Setup the user interface."""
        self.setWindowTitle("Approval History")
        self.setMinimumSize(1200, 700)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header section
        header_layout = QHBoxLayout()

        title_label = QLabel("Approval History")
        title_label.setObjectName("titleLabel")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setWeight(QFont.Weight.Bold)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # Export button
        export_button = QPushButton("Export to CSV")
        export_button.setObjectName("secondaryButton")
        export_button.setMinimumWidth(120)
        export_button.clicked.connect(self.export_to_csv)
        header_layout.addWidget(export_button)

        # Refresh button
        refresh_button = QPushButton("Refresh")
        refresh_button.setObjectName("primaryButton")
        refresh_button.setMinimumWidth(100)
        refresh_button.clicked.connect(self.refresh_data)
        header_layout.addWidget(refresh_button)

        layout.addLayout(header_layout)

        # Filter section
        filter_frame = QFrame()
        filter_frame.setObjectName("filterFrame")
        filter_frame.setFrameShape(QFrame.Shape.StyledPanel)
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(10, 10, 10, 10)

        # Status filter
        filter_label = QLabel("Filter by Status:")
        filter_label.setObjectName("filterLabel")
        filter_layout.addWidget(filter_label)

        self.status_filter = QComboBox()
        self.status_filter.addItem("All", None)
        self.status_filter.addItem("Pending", "pending")
        self.status_filter.addItem("Approved", "approved")
        self.status_filter.addItem("Rejected", "rejected")
        self.status_filter.addItem("Rework Requested", "rework")
        self.status_filter.currentIndexChanged.connect(self.apply_filter)
        self.status_filter.setMinimumWidth(150)
        filter_layout.addWidget(self.status_filter)

        filter_layout.addSpacing(20)

        # Search box (future enhancement)
        search_label = QLabel("Search:")
        search_label.setObjectName("filterLabel")
        filter_layout.addWidget(search_label)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by report number or entity...")
        self.search_input.setMinimumWidth(300)
        self.search_input.returnPressed.connect(self.apply_search)
        filter_layout.addWidget(self.search_input)

        search_button = QPushButton("Search")
        search_button.setObjectName("secondaryButton")
        search_button.clicked.connect(self.apply_search)
        filter_layout.addWidget(search_button)

        clear_search_button = QPushButton("Clear")
        clear_search_button.setObjectName("secondaryButton")
        clear_search_button.clicked.connect(self.clear_search)
        filter_layout.addWidget(clear_search_button)

        filter_layout.addStretch()

        layout.addWidget(filter_frame)

        # Info label
        self.info_label = QLabel()
        self.info_label.setObjectName("subtitleLabel")
        layout.addWidget(self.info_label)

        # Table for approvals
        self.approvals_table = QTableWidget()
        self.approvals_table.setColumnCount(10)
        self.approvals_table.setHorizontalHeaderLabels([
            'Approval ID', 'Report #', 'Entity Name', 'Status',
            'Requested By', 'Requested At', 'Reviewed By',
            'Reviewed At', 'Report Status', 'Comment'
        ])
        self.approvals_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.approvals_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.approvals_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.approvals_table.verticalHeader().setVisible(True)
        self.approvals_table.setAlternatingRowColors(True)

        # Configure responsive column sizing
        header = self.approvals_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Approval ID
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Report #
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)  # Entity Name - takes space
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Status
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Requested By
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # Requested At
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # Reviewed By
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)  # Reviewed At
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.ResizeToContents)  # Report Status
        header.setSectionResizeMode(9, QHeaderView.ResizeMode.ResizeToContents)  # Comment

        # Configure vertical header for responsive row heights
        vertical_header = self.approvals_table.verticalHeader()
        vertical_header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        vertical_header.setDefaultSectionSize(45)
        vertical_header.setMinimumSectionSize(35)

        # Connect signals for saving geometry
        header.sectionResized.connect(self.save_table_geometry)
        self.approvals_table.verticalHeader().sectionResized.connect(self.save_table_geometry)

        # Double-click to view details
        self.approvals_table.doubleClicked.connect(self.view_approval_details)

        layout.addWidget(self.approvals_table)

        # Restore saved geometry
        self.restore_table_geometry()

        # Pagination controls
        pagination_layout = QHBoxLayout()

        self.page_info_label = QLabel()
        pagination_layout.addWidget(self.page_info_label)

        pagination_layout.addStretch()

        self.prev_button = QPushButton("Previous")
        self.prev_button.setObjectName("secondaryButton")
        self.prev_button.setMinimumWidth(100)
        self.prev_button.clicked.connect(self.previous_page)
        pagination_layout.addWidget(self.prev_button)

        self.next_button = QPushButton("Next")
        self.next_button.setObjectName("secondaryButton")
        self.next_button.setMinimumWidth(100)
        self.next_button.clicked.connect(self.next_page)
        pagination_layout.addWidget(self.next_button)

        layout.addLayout(pagination_layout)

        # Close button
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        close_button = QPushButton("Close")
        close_button.setObjectName("primaryButton")
        close_button.setMinimumWidth(100)
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

    def load_approvals(self):
        """Load approvals from database with current filter and pagination."""
        try:
            offset = self.current_page * self.page_size
            approvals, total_count = self.report_service.get_all_approvals(
                status_filter=self.current_filter,
                limit=self.page_size,
                offset=offset
            )

            self.total_count = total_count

            # Update info label
            if self.current_filter:
                filter_text = self.status_filter.currentText()
                self.info_label.setText(
                    f"Showing {len(approvals)} of {total_count} approval(s) "
                    f"(Filter: {filter_text})"
                )
            else:
                self.info_label.setText(f"Showing {len(approvals)} of {total_count} total approval(s)")

            # Update pagination info
            start_idx = offset + 1 if approvals else 0
            end_idx = offset + len(approvals)
            total_pages = (total_count + self.page_size - 1) // self.page_size if total_count > 0 else 1
            current_page_num = self.current_page + 1
            self.page_info_label.setText(
                f"Page {current_page_num} of {total_pages} | "
                f"Showing {start_idx}-{end_idx} of {total_count}"
            )

            # Enable/disable pagination buttons
            self.prev_button.setEnabled(self.current_page > 0)
            self.next_button.setEnabled(end_idx < total_count)

            # Populate table
            self.approvals_table.setRowCount(len(approvals))

            for row, approval in enumerate(approvals):
                # Approval ID
                id_item = QTableWidgetItem(str(approval['approval_id']))
                id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.approvals_table.setItem(row, 0, id_item)

                # Report number
                report_item = QTableWidgetItem(str(approval['report_number']))
                self.approvals_table.setItem(row, 1, report_item)

                # Entity name
                entity_item = QTableWidgetItem(approval['reported_entity_name'])
                self.approvals_table.setItem(row, 2, entity_item)

                # Status - with color coding
                status = approval['approval_status']
                status_item = QTableWidgetItem(status.capitalize())
                status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                # Color code the status
                if status == 'approved':
                    status_item.setBackground(QColor(220, 252, 231))  # Light green
                    status_item.setForeground(QColor(22, 101, 52))    # Dark green
                elif status == 'rejected':
                    status_item.setBackground(QColor(254, 226, 226))  # Light red
                    status_item.setForeground(QColor(153, 27, 27))    # Dark red
                elif status == 'rework':
                    status_item.setBackground(QColor(254, 243, 199))  # Light yellow
                    status_item.setForeground(QColor(120, 53, 15))    # Dark orange
                else:  # pending
                    status_item.setBackground(QColor(224, 242, 254))  # Light blue
                    status_item.setForeground(QColor(30, 64, 175))    # Dark blue

                self.approvals_table.setItem(row, 3, status_item)

                # Requested by
                requester_item = QTableWidgetItem(approval['requested_by'])
                self.approvals_table.setItem(row, 4, requester_item)

                # Requested at
                requested_at = approval['requested_at']
                try:
                    dt = datetime.fromisoformat(requested_at.replace('Z', '+00:00'))
                    formatted_date = dt.strftime('%Y-%m-%d %H:%M')
                except:
                    formatted_date = requested_at
                req_date_item = QTableWidgetItem(formatted_date)
                self.approvals_table.setItem(row, 5, req_date_item)

                # Reviewed by
                reviewer = approval.get('approver_full_name') or approval.get('approver_name') or '-'
                reviewer_item = QTableWidgetItem(reviewer)
                self.approvals_table.setItem(row, 6, reviewer_item)

                # Reviewed at
                reviewed_at = approval.get('reviewed_at') or '-'
                if reviewed_at and reviewed_at != '-':
                    try:
                        dt = datetime.fromisoformat(reviewed_at.replace('Z', '+00:00'))
                        reviewed_at = dt.strftime('%Y-%m-%d %H:%M')
                    except:
                        pass
                rev_date_item = QTableWidgetItem(reviewed_at)
                self.approvals_table.setItem(row, 7, rev_date_item)

                # Report status
                report_status_item = QTableWidgetItem(approval.get('report_status', '-'))
                self.approvals_table.setItem(row, 8, report_status_item)

                # Comment
                comment = approval.get('comment', '')
                comment_preview = comment[:50] + '...' if len(comment) > 50 else comment
                comment_item = QTableWidgetItem(comment_preview)
                comment_item.setToolTip(comment)  # Full comment on hover
                self.approvals_table.setItem(row, 9, comment_item)

        except Exception as e:
            self.logging_service.error(f"Error loading approvals history: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to load approvals: {str(e)}")

    def apply_filter(self):
        """Apply status filter and reload data."""
        self.current_filter = self.status_filter.currentData()
        self.current_page = 0  # Reset to first page
        self.load_approvals()

    def apply_search(self):
        """Apply search filter (future enhancement)."""
        search_term = self.search_input.text().strip()
        if search_term:
            # TODO: Implement search functionality
            # For now, show a message
            QMessageBox.information(
                self,
                "Search",
                f"Search functionality for '{search_term}' will be implemented in a future update."
            )
        else:
            self.load_approvals()

    def clear_search(self):
        """Clear search input and reload."""
        self.search_input.clear()
        self.load_approvals()

    def refresh_data(self):
        """Refresh the approvals data."""
        self.load_approvals()
        self.logging_service.info("Approvals history refreshed")

    def previous_page(self):
        """Go to previous page."""
        if self.current_page > 0:
            self.current_page -= 1
            self.load_approvals()

    def next_page(self):
        """Go to next page."""
        total_pages = (self.total_count + self.page_size - 1) // self.page_size
        if self.current_page < total_pages - 1:
            self.current_page += 1
            self.load_approvals()

    def view_approval_details(self, index):
        """View detailed information about an approval request."""
        row = index.row()
        if row < 0 or row >= self.approvals_table.rowCount():
            return

        # Get all details from the table
        approval_id = self.approvals_table.item(row, 0).text()
        report_number = self.approvals_table.item(row, 1).text()
        entity_name = self.approvals_table.item(row, 2).text()
        status = self.approvals_table.item(row, 3).text()
        requested_by = self.approvals_table.item(row, 4).text()
        requested_at = self.approvals_table.item(row, 5).text()
        reviewed_by = self.approvals_table.item(row, 6).text()
        reviewed_at = self.approvals_table.item(row, 7).text()
        report_status = self.approvals_table.item(row, 8).text()
        comment = self.approvals_table.item(row, 9).toolTip() or self.approvals_table.item(row, 9).text()

        # Show detailed info dialog
        details = f"""
Approval Details
{'=' * 50}

Approval ID: {approval_id}
Report Number: {report_number}
Entity Name: {entity_name}

Status: {status}
Report Status: {report_status}

Requested By: {requested_by}
Requested At: {requested_at}

Reviewed By: {reviewed_by}
Reviewed At: {reviewed_at}

Comment:
{comment if comment else '(No comment)'}
"""
        QMessageBox.information(self, "Approval Details", details)

    def export_to_csv(self):
        """Export current approvals view to CSV file."""
        try:
            # Ask user for file location
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Export Approvals to CSV",
                f"approvals_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "CSV Files (*.csv)"
            )

            if not file_path:
                return

            # Get all data (not just current page) with same filter
            all_approvals, _ = self.report_service.get_all_approvals(
                status_filter=self.current_filter,
                limit=10000,  # Large limit to get all
                offset=0
            )

            # Write to CSV
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)

                # Header
                writer.writerow([
                    'Approval ID', 'Report Number', 'Entity Name', 'Status',
                    'Requested By', 'Requested At', 'Reviewed By', 'Reviewed At',
                    'Report Status', 'Comment'
                ])

                # Data rows
                for approval in all_approvals:
                    writer.writerow([
                        approval['approval_id'],
                        approval['report_number'],
                        approval['reported_entity_name'],
                        approval['approval_status'],
                        approval['requested_by'],
                        approval['requested_at'],
                        approval.get('approver_full_name') or approval.get('approver_name') or '-',
                        approval.get('reviewed_at') or '-',
                        approval.get('report_status', '-'),
                        approval.get('comment', '')
                    ])

            QMessageBox.information(
                self,
                "Export Successful",
                f"Exported {len(all_approvals)} approval(s) to:\n{file_path}"
            )
            self.logging_service.info(f"Exported {len(all_approvals)} approvals to CSV: {file_path}")

        except Exception as e:
            self.logging_service.error(f"Error exporting approvals to CSV: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Export Error", f"Failed to export: {str(e)}")

    def save_table_geometry(self):
        """Save column widths and row heights to settings."""
        settings = QSettings('FIU', 'ReportManagement')

        # Save column widths
        column_widths = []
        for i in range(self.approvals_table.columnCount()):
            column_widths.append(self.approvals_table.columnWidth(i))
        settings.setValue('approvals_history/column_widths', column_widths)

        # Save default row height
        if self.approvals_table.rowCount() > 0:
            default_height = self.approvals_table.rowHeight(0)
            settings.setValue('approvals_history/default_row_height', default_height)

    def restore_table_geometry(self):
        """Restore column widths and row heights from settings."""
        settings = QSettings('FIU', 'ReportManagement')

        # Restore column widths
        column_widths = settings.value('approvals_history/column_widths', None)
        if column_widths:
            for i, width in enumerate(column_widths):
                if i < self.approvals_table.columnCount():
                    self.approvals_table.setColumnWidth(i, int(width))

        # Restore default row height
        default_height = settings.value('approvals_history/default_row_height', None)
        if default_height:
            self.approvals_table.verticalHeader().setDefaultSectionSize(int(default_height))
