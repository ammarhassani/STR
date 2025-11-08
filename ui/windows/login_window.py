"""
Login window for FIU Report Management System.
Modern PyQt6-based authentication interface.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QFrame, QMessageBox,
                             QApplication)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap
from ui.workers import AuthenticationWorker


class LoginWindow(QWidget):
    """
    Login window for user authentication.

    Signals:
        login_successful: Emitted when login is successful with user dict
    """

    login_successful = pyqtSignal(dict)

    def __init__(self, auth_service):
        """
        Initialize the login window.

        Args:
            auth_service: AuthService instance for authentication
        """
        super().__init__()
        self.auth_service = auth_service
        self.auth_worker = None

        self.setup_ui()
        self.apply_styles()

    def setup_ui(self):
        """Setup the user interface."""
        self.setWindowTitle("Financial Crime Investigation - Login")
        self.setMinimumSize(400, 500)
        self.resize(450, 550)  # Default size, but resizable

        # Center window on screen
        self.center_window()

        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Background container
        container = QFrame()
        container.setObjectName("loginContainer")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(40, 40, 40, 40)
        container_layout.setSpacing(20)

        # Logo/Title area
        title_layout = QVBoxLayout()
        title_layout.setSpacing(8)

        title_label = QLabel("FIU Report\nManagement System")
        title_label.setObjectName("titleLabel")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setWordWrap(True)
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setWeight(QFont.Weight.Bold)
        title_label.setFont(title_font)

        subtitle_label = QLabel("Financial Intelligence Unit")
        subtitle_label.setObjectName("subtitleLabel")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title_layout.addWidget(title_label)
        title_layout.addWidget(subtitle_label)
        container_layout.addLayout(title_layout)

        container_layout.addSpacing(30)

        # Form area
        form_layout = QVBoxLayout()
        form_layout.setSpacing(16)

        # Username field
        username_label = QLabel("Username")
        username_label.setStyleSheet("font-weight: 600; color: #2c3e50;")

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter your username")
        self.username_input.setMinimumHeight(40)
        self.username_input.returnPressed.connect(self.handle_login)

        form_layout.addWidget(username_label)
        form_layout.addWidget(self.username_input)

        # Password field
        password_label = QLabel("Password")
        password_label.setStyleSheet("font-weight: 600; color: #2c3e50;")

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setMinimumHeight(40)
        self.password_input.returnPressed.connect(self.handle_login)

        form_layout.addWidget(password_label)
        form_layout.addWidget(self.password_input)

        container_layout.addLayout(form_layout)

        # Error message label
        self.error_label = QLabel("")
        self.error_label.setObjectName("errorLabel")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.setWordWrap(True)
        self.error_label.setVisible(False)
        container_layout.addWidget(self.error_label)

        container_layout.addSpacing(10)

        # Login button
        self.login_button = QPushButton("Login")
        self.login_button.setObjectName("primaryButton")
        self.login_button.setMinimumHeight(45)
        self.login_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.login_button.clicked.connect(self.handle_login)
        container_layout.addWidget(self.login_button)

        # Version info at bottom
        container_layout.addStretch()
        version_label = QLabel("Version 2.0.0")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setStyleSheet("color: #95a5a6; font-size: 9pt;")
        container_layout.addWidget(version_label)

        main_layout.addWidget(container)
        self.setLayout(main_layout)

        # Set focus to username input
        self.username_input.setFocus()

    def apply_styles(self):
        """Apply custom styles to the window."""
        self.setStyleSheet("""
            QWidget {
                background-color: #0d1117;
            }
            QFrame#loginContainer {
                background-color: #161b22;
                border-radius: 12px;
                border: 1px solid #30363d;
            }
        """)

    def center_window(self):
        """Center the window on the screen."""
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def handle_login(self):
        """Handle login button click."""
        username = self.username_input.text().strip()
        password = self.password_input.text()

        # Validation
        if not username:
            self.show_error("Please enter your username")
            self.username_input.setFocus()
            return

        if not password:
            self.show_error("Please enter your password")
            self.password_input.setFocus()
            return

        # Disable inputs during authentication
        self.set_loading(True)

        # Create and start authentication worker
        self.auth_worker = AuthenticationWorker(
            self.auth_service,
            username,
            password
        )
        self.auth_worker.finished.connect(self.on_auth_finished)
        self.auth_worker.error.connect(self.on_auth_error)
        self.auth_worker.start()

    def on_auth_finished(self, success: bool, user: dict, message: str):
        """
        Handle authentication result.

        Args:
            success: Whether authentication was successful
            user: User dictionary if successful
            message: Result message
        """
        self.set_loading(False)

        if success:
            self.hide_error()
            self.login_successful.emit(user)
            self.close()
        else:
            self.show_error(message)
            self.password_input.clear()
            self.password_input.setFocus()

    def on_auth_error(self, error_message: str):
        """
        Handle authentication error.

        Args:
            error_message: Error message
        """
        self.set_loading(False)
        self.show_error(f"Authentication error: {error_message}")

    def show_error(self, message: str):
        """
        Show error message.

        Args:
            message: Error message to display
        """
        self.error_label.setText(message)
        self.error_label.setVisible(True)

    def hide_error(self):
        """Hide error message."""
        self.error_label.setVisible(False)
        self.error_label.setText("")

    def set_loading(self, loading: bool):
        """
        Set loading state for form.

        Args:
            loading: True to disable inputs, False to enable
        """
        self.username_input.setEnabled(not loading)
        self.password_input.setEnabled(not loading)
        self.login_button.setEnabled(not loading)

        if loading:
            self.login_button.setText("Logging in...")
        else:
            self.login_button.setText("Login")

    def closeEvent(self, event):
        """Handle window close event."""
        # Cancel authentication worker if running
        if self.auth_worker and self.auth_worker.isRunning():
            self.auth_worker.terminate()
            self.auth_worker.wait()
        event.accept()
