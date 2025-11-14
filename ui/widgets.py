"""
Modern UI Widgets and Components
"""
from PyQt6.QtWidgets import (
    QWidget, QFrame, QLabel, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QColor, QFont


class StatCard(QFrame):
    """Beautiful animated statistics card"""

    def __init__(self, title, value, icon, color, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setFixedHeight(160)
        self.setMinimumWidth(220)

        # Add shadow effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(QColor(0, 0, 0, 30))
        self.setGraphicsEffect(shadow)

        self._value = 0
        self._target_value = value

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        # Icon and value row
        top_row = QHBoxLayout()

        # Icon
        icon_label = QLabel(icon)
        icon_label.setStyleSheet(f"""
            font-size: 48px;
            color: {color};
            background-color: {color}15;
            border-radius: 16px;
            padding: 12px;
        """)
        icon_label.setFixedSize(80, 80)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top_row.addWidget(icon_label)

        top_row.addStretch()

        # Value
        self.value_label = QLabel("0")
        self.value_label.setStyleSheet(f"""
            font-size: 42px;
            font-weight: bold;
            color: {color};
        """)
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        top_row.addWidget(self.value_label)

        layout.addLayout(top_row)

        # Title
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            font-size: 15px;
            color: #757575;
            font-weight: 600;
        """)
        title_label.setWordWrap(True)
        layout.addWidget(title_label)

        # Animate value
        self.animate_value(value)

    def animate_value(self, target):
        """Animate counter from 0 to target"""
        from PyQt6.QtCore import QTimer

        self._current = 0
        self._target = target
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_value)
        self._timer.start(20)  # Update every 20ms

    def _update_value(self):
        """Update animated value"""
        if self._current < self._target:
            increment = max(1, (self._target - self._current) // 10)
            self._current += increment
            if self._current > self._target:
                self._current = self._target
            self.value_label.setText(str(self._current))
        else:
            self._timer.stop()


class ModernButton(QPushButton):
    """Modern button with hover effects"""

    def __init__(self, text, style="primary", icon=None, parent=None):
        super().__init__(text, parent)
        self.setObjectName(style)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        if icon:
            self.setText(f"{icon}  {text}")

        # Add subtle shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(10)
        shadow.setXOffset(0)
        shadow.setYOffset(2)
        shadow.setColor(QColor(0, 0, 0, 40))
        self.setGraphicsEffect(shadow)


class SearchBar(QLineEdit):
    """Modern search bar with icon"""

    def __init__(self, placeholder="Search...", parent=None):
        super().__init__(parent)
        self.setPlaceholderText(f"🔍 {placeholder}")
        self.setMinimumHeight(48)
        self.setStyleSheet("""
            QLineEdit {
                border: 2px solid #E0E0E0;
                border-radius: 24px;
                padding: 12px 20px;
                font-size: 14px;
                background-color: white;
            }
            QLineEdit:focus {
                border: 2px solid #1976D2;
                background-color: white;
            }
        """)

        # Add shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setXOffset(0)
        shadow.setYOffset(2)
        shadow.setColor(QColor(0, 0, 0, 20))
        self.setGraphicsEffect(shadow)


class StatusBadge(QLabel):
    """Colored status badge"""

    STATUS_COLORS = {
        'Open': ('#4CAF50', '#E8F5E9'),
        'Under Investigation': ('#FF9800', '#FFF3E0'),
        'Case Review': ('#2196F3', '#E3F2FD'),
        'Case Validation': ('#9C27B0', '#F3E5F5'),
        'Close Case': ('#F44336', '#FFEBEE'),
        'Closed with STR': ('#F44336', '#FFEBEE'),
    }

    def __init__(self, status, parent=None):
        super().__init__(status, parent)

        color, bg_color = self.STATUS_COLORS.get(status, ('#757575', '#F5F5F5'))

        self.setStyleSheet(f"""
            QLabel {{
                background-color: {bg_color};
                color: {color};
                border-radius: 12px;
                padding: 6px 16px;
                font-size: 12px;
                font-weight: bold;
            }}
        """)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedHeight(28)


class ModernCard(QFrame):
    """Modern card container with shadow"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")

        # Add shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(QColor(0, 0, 0, 30))
        self.setGraphicsEffect(shadow)


class SectionHeader(QWidget):
    """Section header with divider"""

    def __init__(self, title, subtitle=None, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 16)
        layout.setSpacing(4)

        # Title
        title_label = QLabel(title)
        title_label.setObjectName("sectionTitle")
        layout.addWidget(title_label)

        # Subtitle
        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setObjectName("subtitle")
            layout.addWidget(subtitle_label)

        # Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFixedHeight(2)
        divider.setStyleSheet("background-color: #E0E0E0;")
        layout.addWidget(divider)


class AnimatedWidget(QWidget):
    """Widget with fade-in animation"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowOpacity(0)

    def showEvent(self, event):
        """Fade in on show"""
        super().showEvent(event)

        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(300)
        self.animation.setStartValue(0)
        self.animation.setEndValue(1)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.animation.start()


class FieldGroup(QFrame):
    """Grouped form fields with styling"""

    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 2px solid #E0E0E0;
                border-radius: 12px;
                padding: 20px;
            }
        """)

        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(16)

        # Group title
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #1976D2;
            padding-bottom: 8px;
            border-bottom: 2px solid #E0E0E0;
        """)
        self.layout.addWidget(title_label)

    def add_field(self, label, widget):
        """Add field to group"""
        label_widget = QLabel(label)
        label_widget.setObjectName("fieldLabel")
        self.layout.addWidget(label_widget)
        self.layout.addWidget(widget)
