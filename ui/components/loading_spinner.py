"""
Loading Spinner Widget
Modern circular animated loading indicator.
"""

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, QRectF, pyqtProperty
from PyQt6.QtGui import QPainter, QPen, QColor, QPaintEvent


class LoadingSpinner(QWidget):
    """
    Modern circular loading spinner widget.

    Features:
    - Smooth rotation animation
    - Customizable size and color
    - Determinate and indeterminate modes
    """

    def __init__(self, size: int = 40, color: str = "#0d7377", parent=None):
        """
        Initialize loading spinner.

        Args:
            size: Size of the spinner in pixels
            size: Size of the spinner in pixels
            color: Color of the spinner (hex string)
            parent: Parent widget
        """
        super().__init__(parent)
        self._size = size
        self._color = QColor(color)
        self._angle = 0
        self._indeterminate = True
        self._value = 0

        self.setFixedSize(size, size)

        # Animation timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._rotate)
        self._timer.setInterval(16)  # ~60 FPS

    @pyqtProperty(int)
    def angle(self):
        """Get current rotation angle."""
        return self._angle

    @angle.setter
    def angle(self, value):
        """Set rotation angle."""
        self._angle = value
        self.update()

    def start(self):
        """Start spinner animation."""
        self._timer.start()

    def stop(self):
        """Stop spinner animation."""
        self._timer.stop()

    def set_indeterminate(self, indeterminate: bool):
        """
        Set determinate or indeterminate mode.

        Args:
            indeterminate: True for indeterminate (spinning), False for determinate (progress)
        """
        self._indeterminate = indeterminate
        self.update()

    def set_value(self, value: int):
        """
        Set progress value (0-100) for determinate mode.

        Args:
            value: Progress value (0-100)
        """
        self._value = max(0, min(100, value))
        self.update()

    def _rotate(self):
        """Rotate spinner for animation."""
        self._angle = (self._angle + 8) % 360
        self.update()

    def paintEvent(self, event: QPaintEvent):
        """Paint the spinner."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Calculate dimensions
        width = self.width()
        height = self.height()
        side = min(width, height)

        # Center the spinner
        painter.translate(width / 2, height / 2)

        if self._indeterminate:
            self._paint_indeterminate(painter, side)
        else:
            self._paint_determinate(painter, side)

    def _paint_indeterminate(self, painter: QPainter, side: int):
        """Paint indeterminate spinner (rotating arc)."""
        # Rotate
        painter.rotate(self._angle)

        # Draw arc
        pen_width = max(2, side // 10)
        pen = QPen(self._color)
        pen.setWidth(pen_width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)

        rect = QRectF(-side / 2 + pen_width, -side / 2 + pen_width,
                      side - pen_width * 2, side - pen_width * 2)

        # Draw arc (270 degrees)
        painter.drawArc(rect, 0, 270 * 16)

    def _paint_determinate(self, painter: QPainter, side: int):
        """Paint determinate spinner (progress circle)."""
        pen_width = max(2, side // 10)

        # Background circle
        bg_pen = QPen(QColor(self._color.red(), self._color.green(), self._color.blue(), 50))
        bg_pen.setWidth(pen_width)
        bg_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(bg_pen)

        rect = QRectF(-side / 2 + pen_width, -side / 2 + pen_width,
                      side - pen_width * 2, side - pen_width * 2)

        # Draw background circle
        painter.drawEllipse(rect)

        # Progress arc
        pen = QPen(self._color)
        pen.setWidth(pen_width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)

        # Rotate to start at top
        painter.rotate(-90)

        # Draw progress arc
        span_angle = int((self._value / 100) * 360 * 16)
        painter.drawArc(rect, 0, span_angle)

    def sizeHint(self):
        """Return preferred size."""
        from PyQt6.QtCore import QSize
        return QSize(self._size, self._size)

    def minimumSizeHint(self):
        """Return minimum size."""
        from PyQt6.QtCore import QSize
        return QSize(self._size, self._size)
