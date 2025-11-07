"""
Dashboard view widget showing summary statistics and charts.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QFrame, QGridLayout, QPushButton)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from ui.workers import DashboardDataWorker


class KPICard(QFrame):
    """
    KPI Card widget for displaying key metrics.
    """

    def __init__(self, title: str, value: str, card_type: str = "info"):
        """
        Initialize KPI card.

        Args:
            title: Card title
            value: Metric value
            card_type: Card type (info, success, warning, danger)
        """
        super().__init__()
        self.setObjectName("kpiCard")
        self.setProperty("type", card_type)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        # Title
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #7f8c8d; font-size: 10pt; font-weight: 500;")
        layout.addWidget(title_label)

        # Value
        self.value_label = QLabel(value)
        value_font = QFont()
        value_font.setPointSize(24)
        value_font.setWeight(QFont.Weight.Bold)
        self.value_label.setFont(value_font)
        self.value_label.setStyleSheet("color: #2c3e50;")
        layout.addWidget(self.value_label)

        layout.addStretch()

    def update_value(self, value: str):
        """Update the card value."""
        self.value_label.setText(value)


class DashboardView(QWidget):
    """
    Dashboard view showing system statistics and metrics.

    Signals:
        refresh_requested: Emitted when refresh is requested
    """

    refresh_requested = pyqtSignal()

    def __init__(self, dashboard_service, logging_service):
        """
        Initialize dashboard view.

        Args:
            dashboard_service: DashboardService instance
            logging_service: LoggingService instance
        """
        super().__init__()
        self.dashboard_service = dashboard_service
        self.logging_service = logging_service
        self.worker = None

        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(24)

        # Welcome message
        welcome_label = QLabel("Welcome to FIU Report Management System")
        welcome_font = QFont()
        welcome_font.setPointSize(14)
        welcome_label.setFont(welcome_font)
        layout.addWidget(welcome_label)

        # KPI Cards Grid
        kpi_grid = QGridLayout()
        kpi_grid.setSpacing(16)

        self.kpi_cards = {}

        # Total Reports
        self.kpi_cards['total'] = KPICard("Total Reports", "0", "info")
        kpi_grid.addWidget(self.kpi_cards['total'], 0, 0)

        # Open Reports
        self.kpi_cards['open'] = KPICard("Open Reports", "0", "success")
        kpi_grid.addWidget(self.kpi_cards['open'], 0, 1)

        # Under Investigation
        self.kpi_cards['investigation'] = KPICard("Under Investigation", "0", "warning")
        kpi_grid.addWidget(self.kpi_cards['investigation'], 0, 2)

        # Closed Cases
        self.kpi_cards['closed'] = KPICard("Closed Cases", "0", "danger")
        kpi_grid.addWidget(self.kpi_cards['closed'], 0, 3)

        layout.addLayout(kpi_grid)

        # Charts section
        charts_frame = QFrame()
        charts_frame.setObjectName("card")
        charts_layout = QVBoxLayout(charts_frame)
        charts_layout.setContentsMargins(16, 16, 16, 16)

        charts_title = QLabel("Reports Distribution")
        charts_title_font = QFont()
        charts_title_font.setPointSize(12)
        charts_title_font.setWeight(QFont.Weight.Bold)
        charts_title.setFont(charts_title_font)
        charts_layout.addWidget(charts_title)

        self.status_label = QLabel("Loading data...")
        self.status_label.setStyleSheet("color: #7f8c8d;")
        charts_layout.addWidget(self.status_label)

        layout.addWidget(charts_frame)

        # Refresh button
        refresh_btn = QPushButton("Refresh Dashboard")
        refresh_btn.clicked.connect(self.load_data)
        refresh_btn.setMaximumWidth(200)
        layout.addWidget(refresh_btn)

        layout.addStretch()

    def load_data(self):
        """Load dashboard data asynchronously."""
        # Cancel existing worker if running
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()

        # Create and start worker
        self.worker = DashboardDataWorker(self.dashboard_service)
        self.worker.finished.connect(self.on_data_loaded)
        self.worker.error.connect(self.on_data_error)
        self.worker.progress.connect(self.on_progress)
        self.worker.start()

        # Show loading state
        self.status_label.setText("Loading dashboard data...")

    def on_data_loaded(self, data: dict):
        """
        Handle dashboard data loaded.

        Args:
            data: Dashboard data dictionary
        """
        summary = data.get('summary', {})

        # Update KPI cards
        self.kpi_cards['total'].update_value(str(summary.get('total_reports', 0)))
        self.kpi_cards['open'].update_value(str(summary.get('open_reports', 0)))
        self.kpi_cards['investigation'].update_value(str(summary.get('under_investigation', 0)))
        self.kpi_cards['closed'].update_value(str(summary.get('closed_cases', 0)))

        # Update status
        by_status = data.get('by_status', [])
        status_text = "Reports by Status:\n"
        for item in by_status:
            status_text += f"  • {item['status']}: {item['count']}\n"

        self.status_label.setText(status_text if by_status else "No data available")

        self.logging_service.info("Dashboard data loaded successfully")

    def on_data_error(self, error_message: str):
        """
        Handle data loading error.

        Args:
            error_message: Error message
        """
        self.status_label.setText(f"Error loading data: {error_message}")
        self.logging_service.error(f"Dashboard data load error: {error_message}")

    def on_progress(self, value: int, message: str):
        """
        Handle progress updates.

        Args:
            value: Progress value (0-100)
            message: Progress message
        """
        self.status_label.setText(f"{message} ({value}%)")

    def refresh(self):
        """Refresh the dashboard (called from main window)."""
        self.load_data()
