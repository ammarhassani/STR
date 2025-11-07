"""
Reports view widget for managing financial crime reports.
Simplified placeholder implementation.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QLineEdit, QComboBox, QHeaderView, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from ui.workers import ReportLoadWorker


class ReportsView(QWidget):
    """
    Reports management view.

    Features:
    - View reports list
    - Search and filter
    - View/Edit reports
    """

    def __init__(self, report_service, logging_service):
        """
        Initialize reports view.

        Args:
            report_service: ReportService instance
            logging_service: LoggingService instance
        """
        super().__init__()
        self.report_service = report_service
        self.logging_service = logging_service
        self.current_reports = []
        self.worker = None

        self.setup_ui()
        self.load_reports()

    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header
        header_layout = QHBoxLayout()

        title_label = QLabel("Reports Management")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setWeight(QFont.Weight.Bold)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # Add Report button
        add_btn = QPushButton("Add New Report")
        add_btn.setObjectName("primaryButton")
        add_btn.clicked.connect(self.add_report)
        header_layout.addWidget(add_btn)

        layout.addLayout(header_layout)

        # Filters
        filters_layout = QHBoxLayout()

        # Search
        search_label = QLabel("Search:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by report number, entity name, or CIC...")
        self.search_input.textChanged.connect(self.on_search_changed)
        filters_layout.addWidget(search_label)
        filters_layout.addWidget(self.search_input, stretch=1)

        # Status filter
        status_label = QLabel("Status:")
        self.status_combo = QComboBox()
        self.status_combo.addItems([
            'All', 'Open', 'Case Review', 'Under Investigation',
            'Case Validation', 'Close Case', 'Closed with STR'
        ])
        self.status_combo.currentTextChanged.connect(self.on_filter_changed)
        filters_layout.addWidget(status_label)
        filters_layout.addWidget(self.status_combo)

        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.load_reports)
        filters_layout.addWidget(refresh_btn)

        layout.addLayout(filters_layout)

        # Stats
        self.stats_label = QLabel("0 reports")
        self.stats_label.setStyleSheet("color: #7f8c8d; font-weight: 500;")
        layout.addWidget(self.stats_label)

        # Reports table
        self.reports_table = QTableWidget()
        self.reports_table.setColumnCount(7)
        self.reports_table.setHorizontalHeaderLabels([
            'SN', 'Report Number', 'Date', 'Entity Name',
            'Status', 'Created By', 'Created At'
        ])

        # Configure table
        self.reports_table.setAlternatingRowColors(True)
        self.reports_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.reports_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.reports_table.doubleClicked.connect(self.view_report)

        # Set column widths
        header = self.reports_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # SN
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Report Number
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Date
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)  # Entity Name
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Status
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # Created By
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # Created At

        layout.addWidget(self.reports_table)

        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #7f8c8d;")
        layout.addWidget(self.status_label)

    def on_search_changed(self, text: str):
        """Handle search text change."""
        # Could implement debouncing here
        pass

    def on_filter_changed(self):
        """Handle filter change."""
        self.load_reports()

    def load_reports(self):
        """Load reports from database."""
        self.status_label.setText("Loading reports...")

        # Get filter values
        status = None if self.status_combo.currentText() == 'All' else self.status_combo.currentText()
        search_term = self.search_input.text().strip() or None

        # Load in worker thread
        self.worker = ReportLoadWorker(
            self.report_service,
            status=status,
            search_term=search_term,
            limit=100
        )
        self.worker.finished.connect(self.on_reports_loaded)
        self.worker.error.connect(self.on_load_error)
        self.worker.progress.connect(lambda v, m: self.status_label.setText(m))
        self.worker.start()

    def on_reports_loaded(self, reports: list, total_count: int):
        """
        Handle reports loaded.

        Args:
            reports: List of report dictionaries
            total_count: Total number of reports matching filter
        """
        self.current_reports = reports

        # Update table
        self.reports_table.setRowCount(0)
        self.reports_table.setRowCount(len(reports))

        for row, report in enumerate(reports):
            # SN
            sn_item = QTableWidgetItem(str(report.get('sn', '')))
            self.reports_table.setItem(row, 0, sn_item)

            # Report Number
            report_num_item = QTableWidgetItem(report.get('report_number', ''))
            self.reports_table.setItem(row, 1, report_num_item)

            # Date
            date_item = QTableWidgetItem(report.get('report_date', ''))
            self.reports_table.setItem(row, 2, date_item)

            # Entity Name
            entity_item = QTableWidgetItem(report.get('reported_entity_name', ''))
            self.reports_table.setItem(row, 3, entity_item)

            # Status
            status_item = QTableWidgetItem(report.get('status', ''))
            self.reports_table.setItem(row, 4, status_item)

            # Created By
            created_by_item = QTableWidgetItem(report.get('created_by', ''))
            self.reports_table.setItem(row, 5, created_by_item)

            # Created At
            created_at = report.get('created_at', '')
            if created_at:
                created_at = created_at[:19]  # Remove microseconds
            created_at_item = QTableWidgetItem(created_at)
            self.reports_table.setItem(row, 6, created_at_item)

        # Update stats
        self.stats_label.setText(f"{len(reports)} reports (Total: {total_count})")
        self.status_label.setText("Reports loaded")

    def on_load_error(self, error_message: str):
        """
        Handle load error.

        Args:
            error_message: Error message
        """
        self.status_label.setText(f"Error: {error_message}")
        QMessageBox.critical(self, "Error", f"Failed to load reports:\n{error_message}")

    def view_report(self):
        """View selected report."""
        selected_rows = self.reports_table.selectedRows()
        if not selected_rows:
            return

        row = selected_rows[0].row()
        if row < len(self.current_reports):
            report = self.current_reports[row]
            QMessageBox.information(
                self,
                "Report Details",
                f"Report Number: {report.get('report_number')}\n"
                f"Entity: {report.get('reported_entity_name')}\n"
                f"Status: {report.get('status')}\n\n"
                f"Full report view/edit dialog to be implemented."
            )

    def add_report(self):
        """Add new report."""
        QMessageBox.information(
            self,
            "Add Report",
            "Add report dialog to be implemented.\n\n"
            "This will open a comprehensive form for entering report details."
        )

    def refresh(self):
        """Refresh the view (called from main window)."""
        self.load_reports()
