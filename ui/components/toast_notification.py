"""
Toast Notification Widget
Modern non-blocking notification system with animations.
"""

from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout, QGraphicsOpacityEffect
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint, pyqtProperty
from PyQt6.QtGui import QFont


class ToastNotification(QWidget):
    """
    Modern toast notification widget.

    Features:
    - Auto-dismiss with configurable duration
    - Slide-in/fade-out animations
    - Multiple types (success, error, warning, info)
    - Non-blocking
    - Stackable
    """

    # Toast types
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

    def __init__(self, message: str, toast_type: str = INFO, duration: int = 3000, parent=None):
        """
        Initialize toast notification.

        Args:
            message: Message to display
            toast_type: Type of toast (SUCCESS, ERROR, WARNING, INFO)
            duration: Display duration in milliseconds (0 = manual dismiss)
            parent: Parent widget
        """
        super().__init__(parent)
        self.message = message
        self.toast_type = toast_type
        self.duration = duration

        self.setup_ui()
        self.apply_styling()

        # Animation setup
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)

        # Auto-dismiss timer
        if duration > 0:
            QTimer.singleShot(duration, self.fade_out)

    def setup_ui(self):
        """Setup the UI."""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        # Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        # Icon label
        self.icon_label = QLabel(self.get_icon())
        self.icon_label.setStyleSheet(f"font-size: 18pt; color: {self.get_icon_color()};")
        layout.addWidget(self.icon_label)

        # Message label
        self.message_label = QLabel(self.message)
        self.message_label.setWordWrap(True)
        self.message_label.setMaximumWidth(400)
        message_font = QFont()
        message_font.setPointSize(10)
        message_font.setWeight(QFont.Weight.Medium)
        self.message_label.setFont(message_font)
        layout.addWidget(self.message_label, 1)

        # Close button (only for non-auto-dismiss)
        if self.duration == 0:
            close_label = QLabel("✕")
            close_label.setStyleSheet("color: #9ca3af; font-size: 14pt; font-weight: bold;")
            close_label.setCursor(Qt.CursorShape.PointingHandCursor)
            close_label.mousePressEvent = lambda e: self.fade_out()
            layout.addWidget(close_label)

        # Set minimum size
        self.setMinimumWidth(300)
        self.setMaximumWidth(500)
        self.adjustSize()

    def apply_styling(self):
        """Apply styling based on toast type."""
        colors = {
            self.SUCCESS: {
                'bg': '#d1fae5',
                'border': '#10b981',
                'text': '#065f46'
            },
            self.ERROR: {
                'bg': '#fee2e2',
                'border': '#ef4444',
                'text': '#991b1b'
            },
            self.WARNING: {
                'bg': '#fed7aa',
                'border': '#f97316',
                'text': '#9a3412'
            },
            self.INFO: {
                'bg': '#dbeafe',
                'border': '#3b82f6',
                'text': '#1e40af'
            }
        }

        color_scheme = colors.get(self.toast_type, colors[self.INFO])

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {color_scheme['bg']};
                border-left: 4px solid {color_scheme['border']};
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            }}
            QLabel {{
                color: {color_scheme['text']};
                background-color: transparent;
                border: none;
            }}
        """)

    def get_icon(self) -> str:
        """Get icon for toast type."""
        icons = {
            self.SUCCESS: "✓",
            self.ERROR: "✕",
            self.WARNING: "⚠",
            self.INFO: "ℹ"
        }
        return icons.get(self.toast_type, icons[self.INFO])

    def get_icon_color(self) -> str:
        """Get icon color for toast type."""
        colors = {
            self.SUCCESS: "#10b981",
            self.ERROR: "#ef4444",
            self.WARNING: "#f97316",
            self.INFO: "#3b82f6"
        }
        return colors.get(self.toast_type, colors[self.INFO])

    def show_animated(self, position: QPoint = None):
        """
        Show toast with slide-in animation.

        Args:
            position: Position to show toast (if None, will be set by NotificationManager)
        """
        if position:
            self.move(position)

        self.show()

        # Slide in from right
        self.slide_in_animation = QPropertyAnimation(self, b"pos")
        self.slide_in_animation.setDuration(300)
        self.slide_in_animation.setStartValue(QPoint(self.x() + 20, self.y()))
        self.slide_in_animation.setEndValue(QPoint(self.x(), self.y()))
        self.slide_in_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Fade in
        self.fade_in_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_in_animation.setDuration(300)
        self.fade_in_animation.setStartValue(0.0)
        self.fade_in_animation.setEndValue(1.0)
        self.fade_in_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.slide_in_animation.start()
        self.fade_in_animation.start()

    def fade_out(self):
        """Fade out and close toast."""
        self.fade_out_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_out_animation.setDuration(300)
        self.fade_out_animation.setStartValue(1.0)
        self.fade_out_animation.setEndValue(0.0)
        self.fade_out_animation.setEasingCurve(QEasingCurve.Type.InCubic)
        self.fade_out_animation.finished.connect(self.close)
        self.fade_out_animation.start()

    def mousePressEvent(self, event):
        """Dismiss on click."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.fade_out()
