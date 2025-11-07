"""
Export view widget for exporting reports to CSV.
Modern interface with filtering and customization options.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QComboBox, QLineEdit, QDateEdit,
                             QCheckBox, QFrame, QGroupBox, QMessageBox,
                             QFileDialog, QProgressBar)
from PyQt6.QtCore import Qt, QDate, pyqtSignal, QThread
from PyQt6.QtGui import QFont
from pathlib import Path
from datetime import datetime
from utils.export import export_reports
from services.icon_service import get_icon


class ExportWorker(QThread):
    """Worker thread for exporting reports."""

    finished = pyqtSignal(bool, str, str)  # success, message, file_path
    progress = pyqtSignal(int, str)

    def __init__(self, db_manager, filters, output_path):
        super().__init__()
        self.db_manager = db_manager
        self.filters = filters
        self.output_path = output_path

    def run(self):
        """Export reports in background."""
        try:
            self.progress.emit(20, "Preparing export...")

            # Export reports
            file_path = export_reports(
                self.db_manager,
                filters=self.filters,
                output_dir=str(Path(self.output_path).parent)
            )

            self.progress.emit(90, "Finalizing...")
            self.progress.emit(100, "Export completed!")

            self.finished.emit(True, f"Successfully exported to {file_path}", str(file_path))

        except Exception as e:
            self.finished.emit(False, f"Export failed: {str(e)}", "")


class ExportView(QWidget):
    """
    Export view for exporting reports to CSV.

    Features:
    - Filter by status, date range, search term
    - Choose output location
    - Progress indication
    """

    def __init__(self, db_manager, logging_service):
        """
        Initialize export view.

        Args:
            db_manager: DatabaseManager instance
            logging_service: LoggingService instance
        """
        super().__init__()
        self.db_manager = db_manager
        self.logging_service = logging_service
        self.worker = None

        self.setup_ui()

    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(24)

        # Header
        header_layout = QHBoxLayout()

        title = QLabel("Export Reports to CSV")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setWeight(QFont.Weight.Bold)
        title.setFont(title_font)
        header_layout.addWidget(title)

        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Description
        desc = QLabel(
            "Export your reports to CSV format for analysis in Excel or other tools. "
            "Apply filters to export only specific reports."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #7f8c8d; font-size: 10pt;")
        layout.addWidget(desc)

        # Filters section
        filters_group = QGroupBox("Export Filters")
        filters_layout = QVBoxLayout(filters_group)
        filters_layout.setSpacing(16)

        # Status filter
        status_layout = QHBoxLayout()
        status_label = QLabel("Status:")
        status_label.setMinimumWidth(120)
        self.status_combo = QComboBox()
        self.status_combo.addItems([
            'All Statuses',
            'Open',
            'Case Review',
            'Under Investigation',
            'Case Validation',
            'Close Case',
            'Closed with STR'
        ])
        status_layout.addWidget(status_label)
        status_layout.addWidget(self.status_combo, stretch=1)
        filters_layout.addLayout(status_layout)

        # Date range
        date_range_layout = QHBoxLayout()
        date_label = QLabel("Date Range:")
        date_label.setMinimumWidth(120)

        self.date_from_input = QDateEdit()
        self.date_from_input.setCalendarPopup(True)
        self.date_from_input.setDisplayFormat("dd/MM/yyyy")
        self.date_from_input.setDate(QDate.currentDate().addMonths(-6))
        self.date_from_input.setSpecialValueText("From Date")

        date_to_label = QLabel("to")

        self.date_to_input = QDateEdit()
        self.date_to_input.setCalendarPopup(True)
        self.date_to_input.setDisplayFormat("dd/MM/yyyy")
        self.date_to_input.setDate(QDate.currentDate())
        self.date_to_input.setSpecialValueText("To Date")

        self.date_filter_enabled = QCheckBox("Enable Date Filter")

        date_range_layout.addWidget(date_label)
        date_range_layout.addWidget(self.date_from_input)
        date_range_layout.addWidget(date_to_label)
        date_range_layout.addWidget(self.date_to_input)
        date_range_layout.addWidget(self.date_filter_enabled)
        date_range_layout.addStretch()
        filters_layout.addLayout(date_range_layout)

        # Search term
        search_layout = QHBoxLayout()
        search_label = QLabel("Search Term:")
        search_label.setMinimumWidth(120)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by report number, entity name, or CIC...")
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input, stretch=1)
        filters_layout.addLayout(search_layout)

        layout.addWidget(filters_group)

        # Output location section
        output_group = QGroupBox("Output Location")
        output_layout = QVBoxLayout(output_group)

        output_path_layout = QHBoxLayout()
        output_label = QLabel("Save to:")
        output_label.setMinimumWidth(120)

        self.output_path_input = QLineEdit()
        default_path = str(Path.home() / "Downloads")
        self.output_path_input.setText(default_path)
        self.output_path_input.setReadOnly(True)

        browse_btn = QPushButton("Browse...")
        browse_btn.setIcon(get_icon('folder-open'))
        browse_btn.clicked.connect(self.browse_output_location)
        browse_btn.setMaximumWidth(100)

        output_path_layout.addWidget(output_label)
        output_path_layout.addWidget(self.output_path_input)
        output_path_layout.addWidget(browse_btn)

        output_layout.addLayout(output_path_layout)

        # File naming info
        filename_info = QLabel(
            "File will be automatically named: fiu_reports_YYYYMMDD_HHMMSS.csv"
        )
        filename_info.setStyleSheet("color: #7f8c8d; font-size: 9pt; font-style: italic;")
        output_layout.addWidget(filename_info)

        layout.addWidget(output_group)

        # Progress section
        self.progress_frame = QFrame()
        self.progress_frame.setObjectName("card")
        self.progress_frame.setVisible(False)
        progress_layout = QVBoxLayout(self.progress_frame)
        progress_layout.setContentsMargins(16, 16, 16, 16)

        self.progress_label = QLabel("Exporting...")
        progress_layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimumHeight(6)
        self.progress_bar.setTextVisible(False)
        progress_layout.addWidget(self.progress_bar)

        layout.addWidget(self.progress_frame)

        # Stats
        self.stats_label = QLabel("")
        self.stats_label.setStyleSheet("color: #7f8c8d; font-size: 10pt;")
        self.stats_label.setVisible(False)
        layout.addWidget(self.stats_label)

        # Buttons
        button_layout = QHBoxLayout()

        self.preview_btn = QPushButton("Preview Count")
        self.preview_btn.setIcon(get_icon('search'))
        self.preview_btn.setObjectName("secondaryButton")
        self.preview_btn.clicked.connect(self.preview_export)
        button_layout.addWidget(self.preview_btn)

        button_layout.addStretch()

        self.export_btn = QPushButton("Export to CSV")
        self.export_btn.setIcon(get_icon('file-export'))
        self.export_btn.setObjectName("primaryButton")
        self.export_btn.setMinimumWidth(150)
        self.export_btn.clicked.connect(self.start_export)
        button_layout.addWidget(self.export_btn)

        layout.addLayout(button_layout)
        layout.addStretch()

    def browse_output_location(self):
        """Browse for output directory."""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory",
            self.output_path_input.text()
        )
        if dir_path:
            self.output_path_input.setText(dir_path)

    def get_filters(self):
        """Get current filter values."""
        filters = {}

        # Status filter
        status = self.status_combo.currentText()
        if status != 'All Statuses':
            filters['status'] = status

        # Date range filter
        if self.date_filter_enabled.isChecked():
            filters['date_from'] = self.date_from_input.date().toString("dd/MM/yyyy")
            filters['date_to'] = self.date_to_input.date().toString("dd/MM/yyyy")

        # Search term
        search_term = self.search_input.text().strip()
        if search_term:
            filters['search_term'] = search_term

        return filters

    def preview_export(self):
        """Preview how many reports will be exported."""
        try:
            filters = self.get_filters()

            # Build count query
            query = "SELECT COUNT(*) FROM reports WHERE is_deleted = 0"
            params = []

            if 'status' in filters:
                query += " AND status = ?"
                params.append(filters['status'])

            if 'date_from' in filters:
                query += " AND report_date >= ?"
                params.append(filters['date_from'])

            if 'date_to' in filters:
                query += " AND report_date <= ?"
                params.append(filters['date_to'])

            if 'search_term' in filters:
                query += """ AND (
                    report_number LIKE ? OR
                    reported_entity_name LIKE ? OR
                    cic LIKE ?
                )"""
                search_pattern = f"%{filters['search_term']}%"
                params.extend([search_pattern] * 3)

            # Execute query
            result = self.db_manager.execute_with_retry(query, tuple(params))
            count = result[0][0] if result else 0

            # Show result
            filter_desc = []
            if 'status' in filters:
                filter_desc.append(f"Status: {filters['status']}")
            if 'date_from' in filters:
                filter_desc.append(f"From: {filters['date_from']}")
            if 'date_to' in filters:
                filter_desc.append(f"To: {filters['date_to']}")
            if 'search_term' in filters:
                filter_desc.append(f"Search: {filters['search_term']}")

            filter_text = "\n".join(filter_desc) if filter_desc else "No filters applied"

            self.stats_label.setText(
                f"📊 {count} report(s) will be exported\n\nApplied filters:\n{filter_text}"
            )
            self.stats_label.setVisible(True)

            self.logging_service.info(f"Export preview: {count} reports")

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to preview export: {str(e)}"
            )
            self.logging_service.error(f"Export preview error: {str(e)}", exc_info=True)

    def start_export(self):
        """Start export process."""
        output_path = self.output_path_input.text()

        if not output_path:
            QMessageBox.warning(
                self,
                "No Output Location",
                "Please select an output location."
            )
            return

        # Verify directory exists
        if not Path(output_path).exists():
            QMessageBox.warning(
                self,
                "Invalid Path",
                "The selected output directory does not exist."
            )
            return

        # Get filters
        filters = self.get_filters()

        # Disable buttons
        self.export_btn.setEnabled(False)
        self.preview_btn.setEnabled(False)

        # Show progress
        self.progress_frame.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_label.setText("Starting export...")

        # Start worker
        self.worker = ExportWorker(self.db_manager, filters, output_path)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_export_finished)
        self.worker.start()

        self.logging_service.log_user_action("EXPORT_STARTED", {"filters": filters})

    def on_progress(self, value, message):
        """Handle progress updates."""
        self.progress_bar.setValue(value)
        self.progress_label.setText(message)

    def on_export_finished(self, success, message, file_path):
        """Handle export completion."""
        # Re-enable buttons
        self.export_btn.setEnabled(True)
        self.preview_btn.setEnabled(True)

        if success:
            # Show success message with option to open folder
            reply = QMessageBox.information(
                self,
                "Export Successful",
                f"{message}\n\nWould you like to open the folder?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                import os
                import subprocess
                folder_path = str(Path(file_path).parent)

                # Open folder based on OS
                if os.name == 'nt':  # Windows
                    os.startfile(folder_path)
                elif os.name == 'posix':  # macOS and Linux
                    subprocess.Popen(['xdg-open', folder_path])

            self.logging_service.log_user_action("EXPORT_COMPLETED", {"file_path": file_path})

        else:
            QMessageBox.critical(
                self,
                "Export Failed",
                message
            )
            self.logging_service.error(f"Export failed: {message}")

        # Hide progress
        self.progress_frame.setVisible(False)

    def refresh(self):
        """Refresh the view (called from main window)."""
        # Clear stats
        self.stats_label.setVisible(False)
