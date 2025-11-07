"""
Dashboard Module - PyQt6
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QGridLayout, QPushButton, QScrollArea
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class StatCard(QFrame):
    """Statistics card widget"""

    def __init__(self, title, value, color, icon):
        super().__init__()
        self.setObjectName("card")
        self.setFixedSize(220, 140)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Icon
        icon_label = QLabel(icon)
        icon_label.setStyleSheet(f"font-size: 40px; color: {color};")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)

        # Value
        value_label = QLabel(str(value))
        value_label.setObjectName("statValue")
        value_label.setStyleSheet(f"color: {color};")
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(value_label)

        # Title
        title_label = QLabel(title)
        title_label.setObjectName("statLabel")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setWordWrap(True)
        layout.addWidget(title_label)


class DashboardModule(QWidget):
    """Dashboard with statistics"""

    def __init__(self, db_manager, current_user, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.current_user = current_user
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Title
        title = QLabel("Dashboard")
        title.setObjectName("title")
        layout.addWidget(title)

        # Stats cards
        stats = self.get_statistics()

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(15)

        cards_layout.addWidget(StatCard(
            "Total Reports", stats['total'], "#1976D2", "📊"
        ))
        cards_layout.addWidget(StatCard(
            "Open Reports", stats['open'], "#4CAF50", "📂"
        ))
        cards_layout.addWidget(StatCard(
            "Under Investigation", stats['investigating'], "#FF9800", "🔍"
        ))
        cards_layout.addWidget(StatCard(
            "Closed Cases", stats['closed'], "#F44336", "✓"
        ))

        cards_layout.addStretch()

        layout.addLayout(cards_layout)

        layout.addSpacing(20)

        # Quick actions card
        actions_card = QFrame()
        actions_card.setObjectName("card")
        actions_card.setMaximumWidth(800)

        actions_layout = QVBoxLayout(actions_card)
        actions_layout.setContentsMargins(30, 30, 30, 30)
        actions_layout.setSpacing(15)

        actions_title = QLabel("Quick Actions")
        actions_title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        actions_layout.addWidget(actions_title)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        view_reports_btn = QPushButton("📋 View All Reports")
        view_reports_btn.setObjectName("primary")
        view_reports_btn.clicked.connect(lambda: self.parent().load_module("reports"))
        btn_layout.addWidget(view_reports_btn)

        from utils.permissions import has_permission

        if has_permission(self.current_user['role'], 'add_report'):
            add_report_btn = QPushButton("➕ Add New Report")
            add_report_btn.setObjectName("success")
            add_report_btn.clicked.connect(lambda: self.parent().load_module("add_report"))
            btn_layout.addWidget(add_report_btn)

        if has_permission(self.current_user['role'], 'export'):
            export_btn = QPushButton("💾 Export Data")
            export_btn.setObjectName("secondary")
            export_btn.clicked.connect(lambda: self.parent().load_module("export"))
            btn_layout.addWidget(export_btn)

        btn_layout.addStretch()

        actions_layout.addLayout(btn_layout)

        layout.addWidget(actions_card)

        layout.addStretch()

    def get_statistics(self):
        """Get dashboard statistics"""
        try:
            total = self.db_manager.execute_with_retry(
                "SELECT COUNT(*) as count FROM reports WHERE is_deleted = 0"
            )[0]['count']

            open_count = self.db_manager.execute_with_retry(
                "SELECT COUNT(*) as count FROM reports WHERE status = 'Open' AND is_deleted = 0"
            )[0]['count']

            investigating = self.db_manager.execute_with_retry(
                "SELECT COUNT(*) as count FROM reports WHERE status = 'Under Investigation' AND is_deleted = 0"
            )[0]['count']

            closed = self.db_manager.execute_with_retry(
                "SELECT COUNT(*) as count FROM reports WHERE status IN ('Close Case', 'Closed with STR') AND is_deleted = 0"
            )[0]['count']

            return {
                'total': total,
                'open': open_count,
                'investigating': investigating,
                'closed': closed
            }

        except Exception as e:
            return {
                'total': 0,
                'open': 0,
                'investigating': 0,
                'closed': 0
            }
