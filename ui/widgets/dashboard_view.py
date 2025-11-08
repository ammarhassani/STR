"""
Dashboard view widget showing summary statistics and charts.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QFrame, QGridLayout, QPushButton, QTabWidget, QApplication)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from ui.workers import DashboardDataWorker
from services.icon_service import get_icon, IconService
from ui.widgets.chart_widget import (PieChartWidget, BarChartWidget,
                                     LineChartWidget, HorizontalBarChartWidget)


class KPICard(QFrame):
    """
    KPI Card widget for displaying key metrics.
    """

    def __init__(self, title: str, value: str, card_type: str = "info", icon_name: str = None):
        """
        Initialize KPI card.

        Args:
            title: Card title
            value: Metric value
            card_type: Card type (info, success, warning, danger)
            icon_name: Icon name for the card
        """
        super().__init__()
        self.setObjectName("kpiCard")
        self.setProperty("type", card_type)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        # Header with icon and title
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        # Icon
        if icon_name:
            icon_label = QLabel()
            icon_color = {'info': '#3498db', 'success': '#27ae60', 'warning': '#f39c12', 'danger': '#e74c3c'}.get(card_type, '#3498db')
            icon = get_icon(icon_name, color=icon_color, size=IconService.LARGE)
            icon_label.setPixmap(icon.pixmap(32, 32))
            header_layout.addWidget(icon_label)

        # Title
        title_label = QLabel(title)
        title_label.setObjectName("subtitleLabel")
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        # Value
        self.value_label = QLabel(value)
        value_font = QFont()
        value_font.setPointSize(24)
        value_font.setWeight(QFont.Weight.Bold)
        self.value_label.setFont(value_font)
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
        self.kpi_cards['total'] = KPICard("Total Reports", "0", "info", "clipboard-list")
        kpi_grid.addWidget(self.kpi_cards['total'], 0, 0)

        # Open Reports
        self.kpi_cards['open'] = KPICard("Open Reports", "0", "success", "file-alt")
        kpi_grid.addWidget(self.kpi_cards['open'], 0, 1)

        # Under Investigation
        self.kpi_cards['investigation'] = KPICard("Under Investigation", "0", "warning", "search")
        kpi_grid.addWidget(self.kpi_cards['investigation'], 0, 2)

        # Closed Cases
        self.kpi_cards['closed'] = KPICard("Closed Cases", "0", "danger", "check-circle")
        kpi_grid.addWidget(self.kpi_cards['closed'], 0, 3)

        layout.addLayout(kpi_grid)

        # Charts section with tabs
        charts_frame = QFrame()
        charts_frame.setObjectName("card")
        charts_layout = QVBoxLayout(charts_frame)
        charts_layout.setContentsMargins(16, 16, 16, 16)

        charts_title = QLabel("Data Visualization")
        charts_title_font = QFont()
        charts_title_font.setPointSize(12)
        charts_title_font.setWeight(QFont.Weight.Bold)
        charts_title.setFont(charts_title_font)
        charts_layout.addWidget(charts_title)

        # Create tabs for different charts
        self.chart_tabs = QTabWidget()
        self.chart_tabs.setMinimumHeight(400)

        # Determine theme for charts
        # Try to detect current theme from application stylesheet
        # Always use dark theme
        current_theme = 'dark'

        # Pie chart tab
        self.pie_chart = PieChartWidget(theme=current_theme)
        self.chart_tabs.addTab(self.pie_chart, "Status Distribution")

        # Line chart tab
        self.line_chart = LineChartWidget(theme=current_theme)
        self.chart_tabs.addTab(self.line_chart, "Trend Over Time")

        # Bar chart tab
        self.bar_chart = HorizontalBarChartWidget(theme=current_theme)
        self.chart_tabs.addTab(self.bar_chart, "Top Contributors")

        charts_layout.addWidget(self.chart_tabs)

        # Status label for chart loading
        self.status_label = QLabel("Loading charts...")
        self.status_label.setObjectName("hintLabel")
        charts_layout.addWidget(self.status_label)

        layout.addWidget(charts_frame)

        # Refresh button
        refresh_btn = QPushButton("Refresh Dashboard")
        refresh_btn.setIcon(get_icon('refresh'))
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

        # Update charts
        self.update_charts(data)

        # Update status
        self.status_label.setText("Charts updated successfully")

        self.logging_service.info("Dashboard data loaded successfully")

    def update_charts(self, data: dict):
        """
        Update all dashboard charts with data.

        Args:
            data: Dashboard data dictionary
        """
        try:
            # Pie Chart - Status Distribution
            by_status = data.get('by_status', [])
            if by_status:
                labels = [item['status'] for item in by_status]
                values = [item['count'] for item in by_status]
                self.pie_chart.plot_data(values, labels, "Reports by Status")
            else:
                self.pie_chart.plot_data([], [], "Reports by Status")

            # Line Chart - Trend Over Time
            by_month = data.get('by_month', [])
            if by_month:
                months = [item['month'] for item in by_month]
                counts = [item['count'] for item in by_month]

                # Format month labels for better display
                formatted_months = []
                for month in months:
                    try:
                        from datetime import datetime
                        dt = datetime.strptime(month, '%Y-%m')
                        formatted_months.append(dt.strftime('%b %Y'))
                    except:
                        formatted_months.append(month)

                self.line_chart.plot_data(
                    formatted_months,
                    {'Reports': counts},
                    "Reports Trend (Last 12 Months)",
                    "Month",
                    "Number of Reports"
                )
            else:
                self.line_chart.plot_data([], {}, "Reports Trend (Last 12 Months)")

            # Bar Chart - Top Contributors
            top_reporters = data.get('top_reporters', [])
            if top_reporters:
                usernames = [item['username'] for item in top_reporters]
                counts = [item['count'] for item in top_reporters]
                self.bar_chart.plot_data(
                    usernames,
                    counts,
                    "Top 5 Report Contributors",
                    "Number of Reports"
                )
            else:
                self.bar_chart.plot_data([], [], "Top 5 Report Contributors")

        except Exception as e:
            self.logging_service.error(f"Error updating charts: {str(e)}")
            self.status_label.setText(f"Error updating charts: {str(e)}")

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
