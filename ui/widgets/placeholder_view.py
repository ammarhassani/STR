"""
Placeholder view widget for features under development.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class PlaceholderView(QWidget):
    """
    Placeholder widget for views not yet implemented.
    """

    def __init__(self, view_name: str, description: str = ""):
        """
        Initialize placeholder view.

        Args:
            view_name: Name of the view
            description: Optional description
        """
        super().__init__()
        self.view_name = view_name

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(16)

        # Title
        title_label = QLabel(f"{view_name}")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setWeight(QFont.Weight.Bold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # Description
        desc_label = QLabel(description or "This feature is under development.")
        desc_label.setStyleSheet("color: #7f8c8d; font-size: 11pt;")
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        # Status
        status_label = QLabel("Coming Soon")
        status_label.setStyleSheet("""
            background-color: #3498db;
            color: white;
            padding: 12px 24px;
            border-radius: 6px;
            font-size: 12pt;
            font-weight: 600;
        """)
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(status_label)

    def refresh(self):
        """Refresh method (required by MainWindow)."""
        pass
