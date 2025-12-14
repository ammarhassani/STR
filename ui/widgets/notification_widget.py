"""
Notification Widget for displaying user notifications.
Shows a bell icon with unread count and dropdown with recent notifications.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QFrame, QScrollArea, QMenu,
                             QToolButton, QApplication)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QCursor
from datetime import datetime
from ui.utils.responsive_sizing import ResponsiveSize


class NotificationItem(QFrame):
    """Individual notification item widget."""

    clicked = pyqtSignal(dict)  # Emits notification data

    def __init__(self, notification, parent=None):
        """
        Initialize notification item.

        Args:
            notification: Notification dictionary
            parent: Parent widget
        """
        super().__init__(parent)
        self.notification = notification
        self.setup_ui()

    def setup_ui(self):
        """Setup the user interface."""
        self.setObjectName("notificationItem")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        # Header with title and timestamp
        header_layout = QHBoxLayout()

        # Title
        title_label = QLabel(self.notification['title'])
        title_font = QFont()
        title_font.setWeight(QFont.Weight.Bold)
        title_label.setFont(title_font)

        # Mark unread with different styling
        if not self.notification.get('is_read', False):
            title_label.setStyleSheet("color: #58a6ff;")

        header_layout.addWidget(title_label)
        header_layout.addStretch()

        # Timestamp
        created_at = self.notification.get('created_at', '')
        try:
            dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            time_ago = self.get_time_ago(dt)
        except:
            time_ago = created_at

        time_label = QLabel(time_ago)
        time_label.setObjectName("hintLabel")
        time_font = QFont()
        time_font.setPointSize(9)
        time_label.setFont(time_font)
        header_layout.addWidget(time_label)

        layout.addLayout(header_layout)

        # Message
        message_label = QLabel(self.notification['message'])
        message_label.setWordWrap(True)
        message_label.setObjectName("subtitleLabel")
        layout.addWidget(message_label)

        # Type indicator
        notif_type = self.notification.get('notification_type', 'info')
        type_colors = {
            'info': '#58a6ff',
            'warning': '#d29922',
            'approval_request': '#1f6feb',
            'approval_result': '#2ea043'
        }

        self.setStyleSheet(f"""
            QFrame#notificationItem {{
                border-left: 3px solid {type_colors.get(notif_type, '#58a6ff')};
                background-color: #0d1117;
                border-radius: 4px;
                margin-bottom: 4px;
            }}
            QFrame#notificationItem:hover {{
                background-color: #161b22;
            }}
        """)

    def get_time_ago(self, dt):
        """
        Get human-readable time ago string.

        Args:
            dt: datetime object

        Returns:
            Time ago string
        """
        now = datetime.now()
        diff = now - dt

        if diff.days > 7:
            return dt.strftime('%b %d')
        elif diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds >= 3600:
            hours = diff.seconds // 3600
            return f"{hours}h ago"
        elif diff.seconds >= 60:
            minutes = diff.seconds // 60
            return f"{minutes}m ago"
        else:
            return "Just now"

    def mousePressEvent(self, event):
        """Handle mouse press to emit clicked signal."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.notification)
        super().mousePressEvent(event)


class NotificationDropdown(QFrame):
    """Dropdown panel showing recent notifications."""

    notification_clicked = pyqtSignal(dict)
    mark_all_read = pyqtSignal()

    def __init__(self, notifications, parent=None):
        """
        Initialize notification dropdown.

        Args:
            notifications: List of notification dictionaries
            parent: Parent widget
        """
        super().__init__(parent)
        self.notifications = notifications
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setup_ui()

    def setup_ui(self):
        """Setup the user interface."""
        self.setObjectName("notificationDropdown")

        # Responsive dropdown sizing
        screen_width = QApplication.primaryScreen().geometry().width()
        dropdown_width = min(int(screen_width * 0.25), ResponsiveSize.get_scaled_size(400))
        dropdown_width = max(dropdown_width, ResponsiveSize.get_scaled_size(300))
        self.setMaximumWidth(dropdown_width)

        dropdown_height = ResponsiveSize.get_scaled_size(500)
        self.setMaximumHeight(dropdown_height)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Container frame
        container = QFrame()
        container.setObjectName("dropdownContainer")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # Header
        header = QFrame()
        header.setObjectName("dropdownHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 10, 12, 10)

        header_label = QLabel("Notifications")
        header_font = QFont()
        header_font.setWeight(QFont.Weight.Bold)
        header_label.setFont(header_font)
        header_layout.addWidget(header_label)

        header_layout.addStretch()

        # Mark all read button
        if any(not n.get('is_read', False) for n in self.notifications):
            mark_read_btn = QPushButton("Mark all read")
            mark_read_btn.setObjectName("linkButton")
            mark_read_btn.clicked.connect(self.mark_all_read.emit)
            header_layout.addWidget(mark_read_btn)

        container_layout.addWidget(header)

        # Scroll area for notifications
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setObjectName("notificationScroll")

        # Notifications container
        notif_widget = QWidget()
        notif_layout = QVBoxLayout(notif_widget)
        notif_layout.setContentsMargins(8, 8, 8, 8)
        notif_layout.setSpacing(4)

        if self.notifications:
            for notification in self.notifications:
                item = NotificationItem(notification)
                item.clicked.connect(self.notification_clicked.emit)
                notif_layout.addWidget(item)
        else:
            empty_label = QLabel("No notifications")
            empty_label.setObjectName("hintLabel")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            notif_layout.addWidget(empty_label)

        notif_layout.addStretch()

        scroll.setWidget(notif_widget)
        container_layout.addWidget(scroll)

        layout.addWidget(container)

        # Apply styling
        self.setStyleSheet("""
            QFrame#notificationDropdown {
                background-color: transparent;
            }
            QFrame#dropdownContainer {
                background-color: #0d1117;
                border: 1px solid #30363d;
                border-radius: 6px;
            }
            QFrame#dropdownHeader {
                background-color: #161b22;
                border-bottom: 1px solid #30363d;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }
            QScrollArea#notificationScroll {
                background-color: #0d1117;
                border: none;
            }
            QPushButton#linkButton {
                background-color: transparent;
                border: none;
                color: #58a6ff;
                text-decoration: underline;
                padding: 2px 4px;
            }
            QPushButton#linkButton:hover {
                color: #79c0ff;
            }
        """)


class NotificationWidget(QWidget):
    """
    Notification widget showing bell icon with unread count.

    Signals:
        notification_clicked: Emitted when a notification is clicked
    """

    notification_clicked = pyqtSignal(dict)

    def __init__(self, approval_service, current_user, parent=None):
        """
        Initialize notification widget.

        Args:
            approval_service: ApprovalService instance (has notification methods)
            current_user: Current user dictionary
            parent: Parent widget
        """
        super().__init__(parent)
        self.approval_service = approval_service
        self.current_user = current_user
        self.notifications = []
        self.unread_count = 0
        self.dropdown = None

        self.setup_ui()
        self.start_auto_refresh()

    def setup_ui(self):
        """Setup the user interface."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # Notification button
        self.notif_button = QToolButton()
        self.notif_button.setText("🔔")
        self.notif_button.setObjectName("notificationButton")
        self.notif_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.notif_button.clicked.connect(self.toggle_dropdown)
        layout.addWidget(self.notif_button)

        # Unread count badge
        self.count_label = QLabel()
        self.count_label.setObjectName("notificationBadge")
        self.count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.count_label.setVisible(False)
        self.count_label.setFixedSize(20, 20)
        layout.addWidget(self.count_label)

        # Styling
        self.setStyleSheet("""
            QToolButton#notificationButton {
                background-color: transparent;
                border: none;
                font-size: 18px;
                padding: 5px;
                border-radius: 4px;
            }
            QToolButton#notificationButton:hover {
                background-color: #161b22;
            }
            QLabel#notificationBadge {
                background-color: #f85149;
                color: #ffffff;
                border-radius: 10px;
                font-size: 10px;
                font-weight: bold;
            }
        """)

        # Initial load
        self.refresh_notifications()

    def start_auto_refresh(self):
        """Start auto-refresh timer for notifications."""
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_notifications)
        self.refresh_timer.start(30000)  # Refresh every 30 seconds

    def refresh_notifications(self):
        """Refresh notifications from database."""
        try:
            self.notifications = self.approval_service.get_user_notifications()
            self.unread_count = len([n for n in self.notifications if not n.get('is_read', False)])

            # Update badge
            if self.unread_count > 0:
                count_text = str(self.unread_count) if self.unread_count < 100 else "99+"
                self.count_label.setText(count_text)
                self.count_label.setVisible(True)
            else:
                self.count_label.setVisible(False)

        except Exception as e:
            print(f"Error refreshing notifications: {e}")

    def toggle_dropdown(self):
        """Toggle notification dropdown visibility."""
        if self.dropdown and self.dropdown.isVisible():
            self.dropdown.close()
            self.dropdown = None
        else:
            self.show_dropdown()

    def show_dropdown(self):
        """Show notification dropdown with smart positioning to prevent overflow."""
        if self.dropdown:
            self.dropdown.close()

        self.dropdown = NotificationDropdown(self.notifications, self)
        self.dropdown.notification_clicked.connect(self.on_notification_clicked)
        self.dropdown.mark_all_read.connect(self.mark_all_read)

        # Get button geometry in global coordinates
        button_rect = self.notif_button.geometry()
        button_global_pos = self.notif_button.mapToGlobal(button_rect.topLeft())

        # Get screen geometry
        screen = QApplication.primaryScreen().availableGeometry()

        # Calculate initial position (right-align dropdown with button)
        dropdown_x = button_global_pos.x() + button_rect.width() - self.dropdown.width()
        dropdown_y = button_global_pos.y() + button_rect.height() + ResponsiveSize.get_scaled_size(5)

        # Prevent right edge overflow
        if dropdown_x + self.dropdown.width() > screen.right():
            dropdown_x = screen.right() - self.dropdown.width() - 10

        # Prevent left edge overflow
        if dropdown_x < screen.left():
            dropdown_x = screen.left() + 10

        # Prevent bottom overflow
        if dropdown_y + self.dropdown.height() > screen.bottom():
            # Show above button instead
            dropdown_y = button_global_pos.y() - self.dropdown.height() - ResponsiveSize.get_scaled_size(5)

        # Position and show
        self.dropdown.move(dropdown_x, dropdown_y)
        self.dropdown.show()
        self.dropdown.raise_()

    def on_notification_clicked(self, notification):
        """
        Handle notification click.

        Args:
            notification: Notification dictionary
        """
        # Mark as read
        if not notification.get('is_read', False):
            self.report_service.mark_notification_read(notification['notification_id'])
            self.refresh_notifications()

        # Emit signal for parent to handle navigation
        self.notification_clicked.emit(notification)

        # Close dropdown
        if self.dropdown:
            self.dropdown.close()
            self.dropdown = None

    def mark_all_read(self):
        """Mark all notifications as read."""
        try:
            for notification in self.notifications:
                if not notification.get('is_read', False):
                    self.report_service.mark_notification_read(notification['notification_id'])

            self.refresh_notifications()

            if self.dropdown:
                self.dropdown.close()
                self.dropdown = None

        except Exception as e:
            print(f"Error marking all as read: {e}")
