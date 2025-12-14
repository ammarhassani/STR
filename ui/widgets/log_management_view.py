"""
Log management view for system administrators.
Allows viewing, filtering, exporting, and clearing system logs.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QComboBox, QLineEdit, QMessageBox, QFileDialog,
                             QHeaderView, QFrame, QDateEdit, QGroupBox)
from PyQt6.QtCore import Qt, QDate, pyqtSignal
from PyQt6.QtGui import QFont
from ui.workers import Worker, LogExportWorker
from ui.theme_colors import ThemeColors
from datetime import datetime


class LogManagementView(QWidget):
    """
    Log management interface for administrators.

    Features:
    - View logs with filtering
    - Export logs to file
    - Clear logs with confirmation
    """

    def __init__(self, logging_service):
        """
        Initialize log management view.

        Args:
            logging_service: LoggingService instance
        """
        super().__init__()
        self.logging_service = logging_service
        self.current_logs = []
        self.worker = None

        self.setup_ui()
        self.load_logs()

    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header
        header_label = QLabel("System Logs Management")
        header_font = QFont()
        header_font.setPointSize(16)
        header_font.setWeight(QFont.Weight.Bold)
        header_label.setFont(header_font)
        layout.addWidget(header_label)

        # Filters
        filters_group = QGroupBox("Filters")
        filters_layout = QHBoxLayout()
        filters_layout.setSpacing(12)

        # Log level filter
        level_label = QLabel("Level:")
        self.level_combo = QComboBox()
        self.level_combo.addItems(['All', 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'])
        self.level_combo.currentTextChanged.connect(self.on_filter_changed)
        filters_layout.addWidget(level_label)
        filters_layout.addWidget(self.level_combo)

        # Module filter
        module_label = QLabel("Module:")
        self.module_input = QLineEdit()
        self.module_input.setPlaceholderText("Filter by module...")
        self.module_input.textChanged.connect(self.on_filter_changed)
        filters_layout.addWidget(module_label)
        filters_layout.addWidget(self.module_input)

        # Date range
        date_label = QLabel("From:")
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate().addDays(-7))
        self.start_date.dateChanged.connect(self.on_filter_changed)
        filters_layout.addWidget(date_label)
        filters_layout.addWidget(self.start_date)

        to_label = QLabel("To:")
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate())
        self.end_date.dateChanged.connect(self.on_filter_changed)
        filters_layout.addWidget(to_label)
        filters_layout.addWidget(self.end_date)

        filters_layout.addStretch()

        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.load_logs)
        filters_layout.addWidget(refresh_btn)

        filters_group.setLayout(filters_layout)
        layout.addWidget(filters_group)

        # Actions bar
        actions_layout = QHBoxLayout()

        self.stats_label = QLabel("0 logs loaded")
        self.stats_label.setStyleSheet(f"color: {ThemeColors.TEXT_SECONDARY}; font-weight: 500;")
        actions_layout.addWidget(self.stats_label)

        actions_layout.addStretch()

        # Export button
        export_btn = QPushButton("Export to File")
        export_btn.setObjectName("primaryButton")
        export_btn.clicked.connect(self.export_logs)
        actions_layout.addWidget(export_btn)

        # Clear logs button
        clear_btn = QPushButton("Clear Logs")
        clear_btn.setObjectName("dangerButton")
        clear_btn.clicked.connect(self.clear_logs)
        actions_layout.addWidget(clear_btn)

        layout.addLayout(actions_layout)

        # Logs table
        self.logs_table = QTableWidget()
        self.logs_table.setColumnCount(6)
        self.logs_table.setHorizontalHeaderLabels([
            'Timestamp', 'Level', 'Module', 'Function', 'User', 'Message'
        ])

        # Configure table
        self.logs_table.setAlternatingRowColors(True)
        self.logs_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.logs_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        # Set column widths
        header = self.logs_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Timestamp
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Level
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Module
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Function
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # User
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)  # Message

        # Configure vertical header for responsive row heights
        vertical_header = self.logs_table.verticalHeader()
        vertical_header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        vertical_header.setDefaultSectionSize(35)
        vertical_header.setMinimumSectionSize(30)

        layout.addWidget(self.logs_table)

        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet(f"color: {ThemeColors.TEXT_SECONDARY};")
        layout.addWidget(self.status_label)

    def on_filter_changed(self):
        """Handle filter change - reload logs."""
        # Auto-reload on filter change (could add debouncing here)
        pass

    def load_logs(self):
        """Load logs from database with current filters."""
        self.status_label.setText("Loading logs...")

        # Get filter values
        level = None if self.level_combo.currentText() == 'All' else self.level_combo.currentText()
        module = self.module_input.text().strip() or None
        start_date = self.start_date.date().toString("yyyy-MM-dd")
        end_date = self.end_date.date().toString("yyyy-MM-dd")

        # Load logs in worker thread
        def load_task():
            return self.logging_service.get_logs(
                level=level,
                module=module,
                start_date=start_date,
                end_date=end_date,
                limit=1000
            )

        self.worker = Worker(load_task)
        self.worker.finished.connect(self.on_logs_loaded)
        self.worker.error.connect(self.on_load_error)
        self.worker.start()

    def on_logs_loaded(self, logs: list):
        """
        Handle logs loaded.

        Args:
            logs: List of log dictionaries
        """
        self.current_logs = logs

        # Update table
        self.logs_table.setRowCount(0)
        self.logs_table.setRowCount(len(logs))

        for row, log in enumerate(logs):
            # Timestamp
            timestamp_item = QTableWidgetItem(log['timestamp'][:19])  # Remove microseconds
            self.logs_table.setItem(row, 0, timestamp_item)

            # Level with color coding
            level_item = QTableWidgetItem(log['log_level'])
            if log['log_level'] == 'ERROR' or log['log_level'] == 'CRITICAL':
                level_item.setForeground(Qt.GlobalColor.red)
            elif log['log_level'] == 'WARNING':
                level_item.setForeground(Qt.GlobalColor.darkYellow)
            elif log['log_level'] == 'DEBUG':
                level_item.setForeground(Qt.GlobalColor.gray)
            self.logs_table.setItem(row, 1, level_item)

            # Module
            module_item = QTableWidgetItem(log['module'] or '')
            self.logs_table.setItem(row, 2, module_item)

            # Function
            function_item = QTableWidgetItem(log['function_name'] or '')
            self.logs_table.setItem(row, 3, function_item)

            # User
            user_item = QTableWidgetItem(log['username'] or 'System')
            self.logs_table.setItem(row, 4, user_item)

            # Message
            message_item = QTableWidgetItem(log['message'] or '')
            self.logs_table.setItem(row, 5, message_item)

        # Update stats
        self.stats_label.setText(f"{len(logs)} logs loaded")
        self.status_label.setText(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    def on_load_error(self, error_message: str):
        """
        Handle log loading error.

        Args:
            error_message: Error message
        """
        self.status_label.setText(f"Error loading logs: {error_message}")
        QMessageBox.critical(self, "Error", f"Failed to load logs:\n{error_message}")

    def export_logs(self):
        """Export logs to text file."""
        # Get file path from user
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Logs",
            f"system_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "Text Files (*.txt);;All Files (*)"
        )

        if not file_path:
            return

        # Get filter values
        level = None if self.level_combo.currentText() == 'All' else self.level_combo.currentText()
        module = self.module_input.text().strip() or None
        start_date = self.start_date.date().toString("yyyy-MM-dd")
        end_date = self.end_date.date().toString("yyyy-MM-dd")

        # Export in worker thread
        self.status_label.setText("Exporting logs...")

        self.worker = LogExportWorker(
            self.logging_service,
            file_path,
            level=level,
            module=module,
            start_date=start_date,
            end_date=end_date
        )
        self.worker.finished.connect(self.on_export_finished)
        self.worker.error.connect(self.on_export_error)
        self.worker.progress.connect(lambda v, m: self.status_label.setText(m))
        self.worker.start()

    def on_export_finished(self, file_path: str, count: int):
        """
        Handle export finished.

        Args:
            file_path: Path to exported file
            count: Number of logs exported
        """
        self.status_label.setText(f"Exported {count} logs to {file_path}")
        QMessageBox.information(
            self,
            "Export Complete",
            f"Successfully exported {count} logs to:\n{file_path}"
        )

    def on_export_error(self, error_message: str):
        """
        Handle export error.

        Args:
            error_message: Error message
        """
        self.status_label.setText(f"Export failed: {error_message}")
        QMessageBox.critical(self, "Export Error", f"Failed to export logs:\n{error_message}")

    def clear_logs(self):
        """Clear logs from database with confirmation."""
        # Confirmation dialog
        reply = QMessageBox.question(
            self,
            "Confirm Clear Logs",
            "Are you sure you want to clear all system logs?\n\n"
            "This action cannot be undone. Consider exporting logs first.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # Ask if want to keep recent logs
        keep_reply = QMessageBox.question(
            self,
            "Keep Recent Logs",
            "Do you want to keep logs from the last 7 days?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        days_to_keep = 7 if keep_reply == QMessageBox.StandardButton.Yes else None

        # Clear logs in worker thread
        def clear_task():
            return self.logging_service.clear_logs(older_than_days=days_to_keep)

        self.status_label.setText("Clearing logs...")

        self.worker = Worker(clear_task)
        self.worker.finished.connect(self.on_clear_finished)
        self.worker.error.connect(self.on_clear_error)
        self.worker.start()

    def on_clear_finished(self, count: int):
        """
        Handle clear logs finished.

        Args:
            count: Number of logs cleared
        """
        self.status_label.setText(f"Cleared {count} logs")
        QMessageBox.information(
            self,
            "Clear Complete",
            f"Successfully cleared {count} logs from the database."
        )
        # Reload logs
        self.load_logs()

    def on_clear_error(self, error_message: str):
        """
        Handle clear error.

        Args:
            error_message: Error message
        """
        self.status_label.setText(f"Clear failed: {error_message}")
        QMessageBox.critical(self, "Clear Error", f"Failed to clear logs:\n{error_message}")

    def refresh(self):
        """Refresh the view (called from main window)."""
        self.load_logs()
