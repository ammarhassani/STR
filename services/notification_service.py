"""
Notification Service
Global service for managing toast notifications.
"""

from typing import List, Optional
from PyQt6.QtCore import QObject, QPoint
from PyQt6.QtWidgets import QApplication


class NotificationService(QObject):
    """
    Service for managing toast notifications globally.

    Features:
    - Queue management for multiple notifications
    - Automatic positioning
    - Stack notifications vertically
    """

    def __init__(self):
        """Initialize notification service."""
        super().__init__()
        self.active_toasts: List = []
        self.toast_spacing = 12  # Pixels between toasts
        self.margin = 24  # Margin from screen edge

    def show_success(self, message: str, duration: int = 3000):
        """Show success notification."""
        from ui.components.toast_notification import ToastNotification
        self._show_toast(message, ToastNotification.SUCCESS, duration)

    def show_error(self, message: str, duration: int = 5000):
        """Show error notification (longer duration by default)."""
        from ui.components.toast_notification import ToastNotification
        self._show_toast(message, ToastNotification.ERROR, duration)

    def show_warning(self, message: str, duration: int = 4000):
        """Show warning notification."""
        from ui.components.toast_notification import ToastNotification
        self._show_toast(message, ToastNotification.WARNING, duration)

    def show_info(self, message: str, duration: int = 3000):
        """Show info notification."""
        from ui.components.toast_notification import ToastNotification
        self._show_toast(message, ToastNotification.INFO, duration)

    def _show_toast(self, message: str, toast_type: str, duration: int):
        """
        Create and show a toast notification.

        Args:
            message: Message to display
            toast_type: Type of toast
            duration: Display duration in milliseconds
        """
        from ui.components.toast_notification import ToastNotification

        # Get the main window or active window
        parent = QApplication.activeWindow()
        if not parent:
            parent = QApplication.instance().topLevelWidgets()[0] if QApplication.instance().topLevelWidgets() else None

        # Create toast
        toast = ToastNotification(message, toast_type, duration, parent)

        # Connect close signal to cleanup
        toast.destroyed.connect(lambda: self._remove_toast(toast))

        # Add to active toasts
        self.active_toasts.append(toast)

        # Position and show
        position = self._calculate_position(toast)
        toast.show_animated(position)

    def _calculate_position(self, toast) -> QPoint:
        """
        Calculate position for new toast.

        Args:
            toast: Toast widget to position

        Returns:
            QPoint for toast position
        """
        # Get screen geometry
        screen = QApplication.primaryScreen().geometry()

        # Start position (top-right corner)
        x = screen.width() - toast.width() - self.margin
        y = self.margin

        # Stack below existing toasts
        for existing_toast in self.active_toasts[:-1]:  # Exclude the current toast
            if existing_toast.isVisible():
                y += existing_toast.height() + self.toast_spacing

        return QPoint(x, y)

    def _remove_toast(self, toast):
        """
        Remove toast from active list and reposition remaining toasts.

        Args:
            toast: Toast widget to remove
        """
        if toast in self.active_toasts:
            self.active_toasts.remove(toast)

            # Reposition remaining toasts
            self._reposition_toasts()

    def _reposition_toasts(self):
        """Reposition all active toasts."""
        y = self.margin

        for toast in self.active_toasts:
            if toast.isVisible():
                # Animate to new position
                from PyQt6.QtCore import QPropertyAnimation, QEasingCurve

                animation = QPropertyAnimation(toast, b"pos")
                animation.setDuration(200)
                animation.setStartValue(toast.pos())
                animation.setEndValue(QPoint(toast.x(), y))
                animation.setEasingCurve(QEasingCurve.Type.OutCubic)
                animation.start()

                y += toast.height() + self.toast_spacing

    def clear_all(self):
        """Clear all active notifications."""
        for toast in self.active_toasts[:]:  # Copy list to avoid modification during iteration
            toast.fade_out()

        self.active_toasts.clear()


# Global notification service instance
_notification_service = None


def get_notification_service() -> NotificationService:
    """
    Get the global notification service instance.

    Returns:
        NotificationService instance
    """
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service
