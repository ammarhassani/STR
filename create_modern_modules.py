"""
Script to create all modern UI modules
Run this to generate beautiful, professional modules
"""

# Dashboard module content
DASHBOARD_MODULE = '''"""
Beautiful Dashboard with Charts and Stats
"""
import logging
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout, QPushButton, QScrollArea
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from ui.widgets import StatCard, ModernButton, SectionHeader

logger = logging.getLogger('fiu_system')


class DashboardModule(QWidget):
    """Modern dashboard with animated stats"""

    def __init__(self, db_manager, current_user, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.current_user = current_user
        self.setup_ui()

    def setup_ui(self):
        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(30)

        # Header
        layout.addWidget(SectionHeader("Dashboard", "Overview of your FIU reports"))

        # Stats
        stats = self.get_statistics()

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(20)

        cards_layout.addWidget(StatCard("Total Reports", stats['total'], "📊", "#1976D2"))
        cards_layout.addWidget(StatCard("Open Reports", stats['open'], "📂", "#4CAF50"))
        cards_layout.addWidget(StatCard("Under Investigation", stats['investigating'], "🔍", "#FF9800"))
        cards_layout.addWidget(StatCard("Closed Cases", stats['closed'], "✓", "#F44336"))

        cards_layout.addStretch()
        layout.addLayout(cards_layout)

        # Quick actions
        actions = QFrame()
        actions.setObjectName("card")
        actions.setMaximumWidth(900)

        actions_layout = QVBoxLayout(actions)
        actions_layout.setContentsMargins(30, 30, 30, 30)
        actions_layout.setSpacing(20)

        actions_title = QLabel("Quick Actions")
        actions_title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        actions_layout.addWidget(actions_title)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)

        view_btn = ModernButton("📋  View All Reports", "primary")
        view_btn.clicked.connect(lambda: self.parent().load_module("reports"))
        btn_layout.addWidget(view_btn)

        from utils.permissions import has_permission

        if has_permission(self.current_user['role'], 'add_report'):
            add_btn = ModernButton("➕  Add New Report", "success")
            add_btn.clicked.connect(lambda: self.parent().load_module("add_report"))
            btn_layout.addWidget(add_btn)

        if has_permission(self.current_user['role'], 'export'):
            export_btn = ModernButton("💾  Export Data", "secondary")
            export_btn.clicked.connect(lambda: self.parent().load_module("export"))
            btn_layout.addWidget(export_btn)

        btn_layout.addStretch()
        actions_layout.addLayout(btn_layout)

        layout.addWidget(actions)

        layout.addStretch()

        scroll.setWidget(content)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

    def get_statistics(self):
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

            return {'total': total, 'open': open_count, 'investigating': investigating, 'closed': closed}

        except Exception as e:
            return {'total': 0, 'open': 0, 'investigating': 0, 'closed': 0}
'''

# Write files
import os

modules_dir = r"C:\Users\A\Desktop\STR\V2"

# Write dashboard
with open(os.path.join(modules_dir, "dashboard_module.py"), "w", encoding="utf-8") as f:
    f.write(DASHBOARD_MODULE)

print("✅ Dashboard module created!")
print("✅ All modules will continue in the next step...")
