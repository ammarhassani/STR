"""
Mini Window Framework
Lightweight, compact dialogs for quick CRUD operations and record comparison.
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QFrame, QScrollArea, QWidget,
                             QGridLayout, QMessageBox, QSizePolicy)
from PyQt6.QtCore import Qt, QSettings, QRect, pyqtSignal
from PyQt6.QtGui import QFont, QIcon, QScreen
from typing import Dict, List, Optional, Callable


class MiniWindow(QDialog):
    """
    Base class for mini windows - compact, lightweight dialogs.
    Features:
    - Compact size (40% of screen)
    - Always on top option
    - Remembers position
    - Quick close (Escape key)
    - Minimal chrome
    """

    # Signals
    closed = pyqtSignal()
    data_changed = pyqtSignal()

    def __init__(self, title: str, parent=None, stay_on_top: bool = False):
        """
        Initialize mini window.

        Args:
            title: Window title
            parent: Parent widget
            stay_on_top: Keep window on top of other windows
        """
        flags = Qt.WindowType.Window | Qt.WindowType.WindowCloseButtonHint
        if stay_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint

        super().__init__(parent, flags)

        self.setWindowTitle(title)
        self.window_key = self.__class__.__name__  # For saving geometry

        # Set compact size (40% of screen)
        screen = QScreen.availableGeometry(self.screen())
        width = int(screen.width() * 0.4)
        height = int(screen.height() * 0.6)
        self.resize(width, height)

        # Setup UI
        self.setup_base_ui()

        # Restore saved position if available
        self.restore_geometry()

    def setup_base_ui(self):
        """Setup base UI structure."""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)

        # Header (title bar replacement for minimal chrome)
        self.header_frame = QFrame()
        self.header_frame.setObjectName("miniWindowHeader")
        self.header_frame.setFrameShape(QFrame.Shape.StyledPanel)
        header_layout = QHBoxLayout(self.header_frame)
        header_layout.setContentsMargins(10, 5, 10, 5)

        self.title_label = QLabel(self.windowTitle())
        self.title_label.setObjectName("miniWindowTitle")
        title_font = QFont()
        title_font.setPointSize(10)
        title_font.setWeight(QFont.Weight.Bold)
        self.title_label.setFont(title_font)
        header_layout.addWidget(self.title_label)

        header_layout.addStretch()

        # Pin button (toggle stay on top)
        self.pin_button = QPushButton("📌")
        self.pin_button.setObjectName("miniButton")
        self.pin_button.setFixedSize(25, 25)
        self.pin_button.setToolTip("Pin window on top")
        self.pin_button.clicked.connect(self.toggle_pin)
        header_layout.addWidget(self.pin_button)

        # Close button
        close_button = QPushButton("✕")
        close_button.setObjectName("miniButton")
        close_button.setFixedSize(25, 25)
        close_button.setToolTip("Close (Esc)")
        close_button.clicked.connect(self.close)
        header_layout.addWidget(close_button)

        self.main_layout.addWidget(self.header_frame)

        # Content area (to be filled by subclasses)
        self.content_scroll = QScrollArea()
        self.content_scroll.setWidgetResizable(True)
        self.content_scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(5, 5, 5, 5)
        self.content_layout.setSpacing(8)

        self.content_scroll.setWidget(self.content_widget)
        self.main_layout.addWidget(self.content_scroll)

        # Button bar (optional, can be hidden by subclasses)
        self.button_bar = QFrame()
        button_bar_layout = QHBoxLayout(self.button_bar)
        button_bar_layout.setContentsMargins(0, 5, 0, 0)

        button_bar_layout.addStretch()

        self.close_btn = QPushButton("Close")
        self.close_btn.setObjectName("secondaryButton")
        self.close_btn.setMinimumWidth(80)
        self.close_btn.clicked.connect(self.close)
        button_bar_layout.addWidget(self.close_btn)

        self.main_layout.addWidget(self.button_bar)

    def toggle_pin(self):
        """Toggle stay-on-top behavior."""
        current_flags = self.windowFlags()

        if current_flags & Qt.WindowType.WindowStaysOnTopHint:
            # Remove stay on top
            new_flags = current_flags & ~Qt.WindowType.WindowStaysOnTopHint
            self.pin_button.setText("📌")
            self.pin_button.setToolTip("Pin window on top")
        else:
            # Add stay on top
            new_flags = current_flags | Qt.WindowType.WindowStaysOnTopHint
            self.pin_button.setText("📍")
            self.pin_button.setToolTip("Unpin window")

        # Save current geometry before changing flags
        current_geometry = self.geometry()

        # Apply new flags
        self.setWindowFlags(new_flags)

        # Restore geometry and show window
        self.setGeometry(current_geometry)
        self.show()

    def add_content_widget(self, widget: QWidget):
        """Add a widget to the content area."""
        self.content_layout.addWidget(widget)

    def add_content_stretch(self):
        """Add stretch to content area."""
        self.content_layout.addStretch()

    def hide_button_bar(self):
        """Hide the default button bar."""
        self.button_bar.hide()

    def save_geometry(self):
        """Save window geometry to settings."""
        settings = QSettings('FIU', 'ReportManagement')
        settings.setValue(f'mini_window/{self.window_key}/geometry', self.saveGeometry())
        settings.setValue(f'mini_window/{self.window_key}/position', self.pos())
        settings.setValue(f'mini_window/{self.window_key}/size', self.size())

    def restore_geometry(self):
        """Restore window geometry from settings."""
        settings = QSettings('FIU', 'ReportManagement')
        geometry = settings.value(f'mini_window/{self.window_key}/geometry', None)
        if geometry:
            self.restoreGeometry(geometry)

    def closeEvent(self, event):
        """Handle close event."""
        self.save_geometry()
        self.closed.emit()
        super().closeEvent(event)

    def keyPressEvent(self, event):
        """Handle key press - Escape to close."""
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)


class FieldDisplayWidget(QFrame):
    """Widget for displaying a field name and value in a compact format."""

    def __init__(self, label: str, value: str, parent=None):
        super().__init__(parent)
        self.setObjectName("fieldDisplay")
        self.setFrameShape(QFrame.Shape.StyledPanel)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 5, 8, 5)
        layout.setSpacing(2)

        # Label
        label_widget = QLabel(label)
        label_widget.setObjectName("fieldLabel")
        label_font = QFont()
        label_font.setPointSize(8)
        label_widget.setFont(label_font)
        label_widget.setStyleSheet("color: #666;")
        layout.addWidget(label_widget)

        # Value
        value_widget = QLabel(str(value) if value else "-")
        value_widget.setObjectName("fieldValue")
        value_widget.setWordWrap(True)
        value_font = QFont()
        value_font.setPointSize(9)
        value_widget.setFont(value_font)
        layout.addWidget(value_widget)


class DataGridWidget(QWidget):
    """Grid widget for displaying data fields in a compact 2-column layout."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.grid_layout = QGridLayout(self)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(8)
        self.grid_layout.setColumnStretch(0, 1)
        self.grid_layout.setColumnStretch(1, 1)

        self.row = 0

    def add_field(self, label: str, value: str, span_columns: bool = False):
        """
        Add a field to the grid.

        Args:
            label: Field label
            value: Field value
            span_columns: If True, field spans both columns (for long content)
        """
        field_widget = FieldDisplayWidget(label, value)

        if span_columns:
            self.grid_layout.addWidget(field_widget, self.row, 0, 1, 2)
            self.row += 1
        else:
            col = 0 if self.row % 2 == 0 or self.grid_layout.itemAtPosition(self.row, 0) is None else 1
            if col == 1 and self.grid_layout.itemAtPosition(self.row, 0) is None:
                # Fill empty left column with spacer
                col = 0

            self.grid_layout.addWidget(field_widget, self.row, col)

            if col == 1:
                self.row += 1

    def add_separator(self, text: str = ""):
        """Add a separator line with optional text."""
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)

        if text:
            container = QWidget()
            layout = QHBoxLayout(container)
            layout.setContentsMargins(0, 5, 0, 5)

            layout.addWidget(separator, 1)
            label = QLabel(text)
            label.setStyleSheet("color: #888; font-weight: bold; font-size: 10px;")
            layout.addWidget(label)
            layout.addWidget(QFrame(), 1)

            self.grid_layout.addWidget(container, self.row, 0, 1, 2)
        else:
            self.grid_layout.addWidget(separator, self.row, 0, 1, 2)

        self.row += 1


class SideBySideComparisonWidget(QWidget):
    """Widget for displaying two records side-by-side for comparison."""

    def __init__(self, title_left: str = "Record A", title_right: str = "Record B", parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Left panel
        left_panel = QFrame()
        left_panel.setObjectName("comparisonPanel")
        left_panel.setFrameShape(QFrame.Shape.StyledPanel)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)

        left_title = QLabel(title_left)
        left_title.setObjectName("comparisonTitle")
        left_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_title_font = QFont()
        left_title_font.setWeight(QFont.Weight.Bold)
        left_title.setFont(left_title_font)
        left_layout.addWidget(left_title)

        self.left_grid = DataGridWidget()
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setWidget(self.left_grid)
        left_layout.addWidget(left_scroll)

        layout.addWidget(left_panel)

        # Right panel
        right_panel = QFrame()
        right_panel.setObjectName("comparisonPanel")
        right_panel.setFrameShape(QFrame.Shape.StyledPanel)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 10, 10, 10)

        right_title = QLabel(title_right)
        right_title.setObjectName("comparisonTitle")
        right_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_title_font = QFont()
        right_title_font.setWeight(QFont.Weight.Bold)
        right_title.setFont(right_title_font)
        right_layout.addWidget(right_title)

        self.right_grid = DataGridWidget()
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setWidget(self.right_grid)
        right_layout.addWidget(right_scroll)

        layout.addWidget(right_panel)

    def add_field_pair(self, label: str, value_left: str, value_right: str, span_columns: bool = False):
        """
        Add a field to both panels for comparison.

        Args:
            label: Field label
            value_left: Value in left panel
            value_right: Value in right panel
            span_columns: If True, field spans both columns
        """
        self.left_grid.add_field(label, value_left, span_columns)
        self.right_grid.add_field(label, value_right, span_columns)

    def add_separator(self, text: str = ""):
        """Add separator to both panels."""
        self.left_grid.add_separator(text)
        self.right_grid.add_separator(text)
