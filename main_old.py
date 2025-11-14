"""
FIU Report Management System - PyQt6 Version
Main Application Entry Point
"""
import sys
import logging
from pathlib import Path
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QMessageBox, QStackedWidget,
    QFrame, QGridLayout, QScrollArea, QFileDialog, QProgressDialog
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QIcon, QColor, QPalette

from config import Config
from database.db_manager import DatabaseManager
from database.init_db import initialize_database, validate_database
from utils.permissions import has_permission

# Setup logging
log_dir = Path.home() / '.fiu_system'
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / 'app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('fiu_system')


class StyleSheet:
    """Application-wide stylesheet"""

    @staticmethod
    def get():
        return """
            QMainWindow {
                background-color: #F5F5F5;
            }

            QWidget#card {
                background-color: white;
                border-radius: 8px;
                border: 1px solid #E0E0E0;
            }

            QWidget#sidebar {
                background-color: #1976D2;
                border-right: 1px solid #1565C0;
            }

            QPushButton#primary {
                background-color: #1976D2;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: bold;
            }

            QPushButton#primary:hover {
                background-color: #1565C0;
            }

            QPushButton#primary:pressed {
                background-color: #0D47A1;
            }

            QPushButton#secondary {
                background-color: #757575;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 16px;
                font-size: 12px;
            }

            QPushButton#secondary:hover {
                background-color: #616161;
            }

            QPushButton#success {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: bold;
            }

            QPushButton#success:hover {
                background-color: #45A049;
            }

            QPushButton#navButton {
                background-color: transparent;
                color: white;
                border: none;
                text-align: left;
                padding: 12px 20px;
                font-size: 13px;
            }

            QPushButton#navButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }

            QPushButton#navButton:checked {
                background-color: rgba(255, 255, 255, 0.2);
                border-left: 4px solid white;
            }

            QLineEdit {
                border: 2px solid #E0E0E0;
                border-radius: 5px;
                padding: 10px;
                font-size: 13px;
                background-color: white;
            }

            QLineEdit:focus {
                border: 2px solid #1976D2;
            }

            QLabel#title {
                font-size: 24px;
                font-weight: bold;
                color: #212121;
            }

            QLabel#subtitle {
                font-size: 14px;
                color: #757575;
            }

            QLabel#statValue {
                font-size: 32px;
                font-weight: bold;
                color: #1976D2;
            }

            QLabel#statLabel {
                font-size: 13px;
                color: #757575;
            }
        """


class SetupWizard(QWidget):
    """First-time setup wizard"""

    setup_complete = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.temp_db_path = None
        self.temp_backup_path = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Card
        card = QWidget()
        card.setObjectName("card")
        card.setFixedWidth(600)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(40, 40, 40, 40)
        card_layout.setSpacing(15)

        # Title
        title = QLabel("Initial Setup - Choose Locations")
        title.setObjectName("title")
        card_layout.addWidget(title)

        subtitle = QLabel("Select where to store your database and backups")
        subtitle.setObjectName("subtitle")
        card_layout.addWidget(subtitle)

        card_layout.addSpacing(20)

        # Database path
        db_label = QLabel("Database File Path")
        card_layout.addWidget(db_label)

        db_layout = QHBoxLayout()
        default_db = str(Path.home() / "FIU_System" / "database" / "fiu_reports.db")
        self.db_path_input = QLineEdit(default_db)
        db_layout.addWidget(self.db_path_input)

        db_browse_btn = QPushButton("Browse")
        db_browse_btn.setObjectName("secondary")
        db_browse_btn.clicked.connect(self.browse_database)
        db_layout.addWidget(db_browse_btn)

        card_layout.addLayout(db_layout)

        card_layout.addSpacing(10)

        # Backup path
        backup_label = QLabel("Backup Directory")
        card_layout.addWidget(backup_label)

        backup_layout = QHBoxLayout()
        default_backup = str(Path.home() / "FIU_System" / "backups")
        self.backup_path_input = QLineEdit(default_backup)
        backup_layout.addWidget(self.backup_path_input)

        backup_browse_btn = QPushButton("Browse")
        backup_browse_btn.setObjectName("secondary")
        backup_browse_btn.clicked.connect(self.browse_backup)
        backup_layout.addWidget(backup_browse_btn)

        card_layout.addLayout(backup_layout)

        card_layout.addSpacing(20)

        # Continue button
        continue_btn = QPushButton("Continue")
        continue_btn.setObjectName("primary")
        continue_btn.clicked.connect(self.validate_and_continue)
        card_layout.addWidget(continue_btn)

        layout.addWidget(card)

    def browse_database(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Database Location",
            str(Path.home() / "FIU_System" / "database"),
            "Database Files (*.db)"
        )
        if path:
            self.db_path_input.setText(path)

    def browse_backup(self):
        path = QFileDialog.getExistingDirectory(
            self, "Backup Directory",
            str(Path.home() / "FIU_System")
        )
        if path:
            self.backup_path_input.setText(path)

    def validate_and_continue(self):
        db_path = self.db_path_input.text().strip()
        backup_path = self.backup_path_input.text().strip()

        if not db_path or not backup_path:
            QMessageBox.warning(self, "Error", "Both paths are required")
            return

        self.temp_db_path = db_path
        self.temp_backup_path = backup_path

        # Check if database exists
        db_file = Path(db_path)
        if db_file.is_file():
            reply = QMessageBox.question(
                self, "Database Found",
                f"An existing database was found:\n{db_path}\n\nUse this database?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.save_config_and_finish()
            else:
                self.create_new_database()
        else:
            self.create_new_database()

    def create_new_database(self):
        # Verify admin credentials
        username, ok = self.show_admin_dialog()
        if not ok:
            return

        if username != "admin":
            QMessageBox.warning(self, "Error", "Invalid admin credentials")
            return

        # Create database
        progress = QProgressDialog("Creating database...", None, 0, 0, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()
        QApplication.processEvents()

        try:
            # Create directories
            db_path = Path(self.temp_db_path)
            if not str(db_path).lower().endswith('.db'):
                db_path = Path(str(db_path) + '.db')
                self.temp_db_path = str(db_path)

            db_path.parent.mkdir(parents=True, exist_ok=True)
            Path(self.temp_backup_path).mkdir(parents=True, exist_ok=True)

            # Initialize database
            success, message = initialize_database(self.temp_db_path)
            progress.close()

            if not success:
                QMessageBox.critical(self, "Error", f"Failed to create database:\n{message}")
                return

            self.save_config_and_finish()

        except Exception as e:
            progress.close()
            QMessageBox.critical(self, "Error", f"Setup failed:\n{str(e)}")

    def show_admin_dialog(self):
        from PyQt6.QtWidgets import QDialog, QDialogButtonBox

        dialog = QDialog(self)
        dialog.setWindowTitle("Admin Verification")
        dialog.setFixedWidth(400)

        layout = QVBoxLayout(dialog)

        layout.addWidget(QLabel("Enter admin credentials to create database:"))
        layout.addSpacing(10)

        username_input = QLineEdit()
        username_input.setPlaceholderText("Username: admin")
        layout.addWidget(QLabel("Username"))
        layout.addWidget(username_input)

        password_input = QLineEdit()
        password_input.setPlaceholderText("Password: admin123")
        password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(QLabel("Password"))
        layout.addWidget(password_input)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        result = dialog.exec()

        if result == QDialog.DialogCode.Accepted:
            if username_input.text() == "admin" and password_input.text() == "admin123":
                return "admin", True

        return None, False

    def save_config_and_finish(self):
        Config.DATABASE_PATH = self.temp_db_path
        Config.BACKUP_PATH = self.temp_backup_path

        if Config.save():
            QMessageBox.information(
                self, "Success",
                "Setup complete!\n\nDefault login:\nUsername: admin\nPassword: admin123"
            )
            self.setup_complete.emit()
        else:
            QMessageBox.critical(self, "Error", "Failed to save configuration")


class LoginScreen(QWidget):
    """Login screen"""

    login_success = pyqtSignal(dict)

    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Login card
        card = QWidget()
        card.setObjectName("card")
        card.setFixedSize(400, 400)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(40, 40, 40, 40)
        card_layout.setSpacing(15)

        # Title
        title = QLabel("🔒 FIU Report System")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(title)

        subtitle = QLabel("Secure Login")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(subtitle)

        card_layout.addSpacing(20)

        # Username
        card_layout.addWidget(QLabel("Username"))
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter username")
        card_layout.addWidget(self.username_input)

        # Password
        card_layout.addWidget(QLabel("Password"))
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.returnPressed.connect(self.attempt_login)
        card_layout.addWidget(self.password_input)

        card_layout.addSpacing(10)

        # Login button
        login_btn = QPushButton("Sign In")
        login_btn.setObjectName("primary")
        login_btn.clicked.connect(self.attempt_login)
        card_layout.addWidget(login_btn)

        card_layout.addStretch()

        layout.addWidget(card)

    def attempt_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if not username or not password:
            QMessageBox.warning(self, "Error", "Enter username and password")
            return

        user = self.authenticate_user(username, password)

        if user:
            logger.info(f"User logged in: {username}")
            self.login_success.emit(user)
        else:
            QMessageBox.warning(self, "Login Failed", "Invalid username or password")

    def authenticate_user(self, username, password, is_org=False):
        try:
            if is_org:
                query = """
                    SELECT user_id, username, full_name, role, is_active, theme_preference
                    FROM users WHERE org_username = ? AND password = ? AND is_active = 1
                """
            else:
                query = """
                    SELECT user_id, username, full_name, role, is_active, theme_preference
                    FROM users WHERE username = ? AND password = ? AND is_active = 1
                """

            results = self.db_manager.execute_with_retry(query, (username, password))

            if results:
                user = dict(results[0])

                # Update last login
                self.db_manager.execute_with_retry(
                    "UPDATE users SET last_login = datetime('now'), failed_login_attempts = 0 WHERE user_id = ?",
                    (user['user_id'],)
                )

                return user

            if not is_org:
                return self.authenticate_user(username, password, is_org=True)

            return None

        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None


class MainApplication(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()
        self.db_manager = None
        self.current_user = None
        self.content_widgets = {}

        self.setWindowTitle("FIU Report Management System")
        self.setGeometry(100, 100, 1400, 800)
        self.setMinimumSize(1000, 600)

        self.setStyleSheet(StyleSheet.get())

        # Central stacked widget
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        self.start_application()

    def start_application(self):
        """Start application workflow"""
        logger.info("Starting application")

        if Config.load():
            if Config.is_configured():
                is_valid, message = Config.validate_paths()
                if is_valid:
                    if self.init_database():
                        self.show_login()
                        return

        # Show setup wizard
        self.show_setup()

    def show_setup(self):
        """Show setup wizard"""
        setup_widget = SetupWizard()
        setup_widget.setup_complete.connect(self.on_setup_complete)
        self.stacked_widget.addWidget(setup_widget)
        self.stacked_widget.setCurrentWidget(setup_widget)

    def on_setup_complete(self):
        """Handle setup completion"""
        if self.init_database():
            self.show_login()

    def init_database(self):
        """Initialize database"""
        try:
            is_valid, message = validate_database(Config.DATABASE_PATH)
            if not is_valid:
                QMessageBox.critical(self, "Database Error", message)
                return False

            self.db_manager = DatabaseManager(Config.DATABASE_PATH)
            logger.info("Database initialized")
            return True

        except Exception as e:
            logger.error(f"Database init error: {e}")
            return False

    def show_login(self):
        """Show login screen"""
        login_widget = LoginScreen(self.db_manager)
        login_widget.login_success.connect(self.on_login_success)
        self.stacked_widget.addWidget(login_widget)
        self.stacked_widget.setCurrentWidget(login_widget)

    def on_login_success(self, user):
        """Handle successful login"""
        self.current_user = user
        self.show_main_interface()

    def show_main_interface(self):
        """Show main application interface"""
        main_widget = QWidget()
        layout = QHBoxLayout(main_widget)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        # Sidebar
        sidebar = self.create_sidebar()
        layout.addWidget(sidebar)

        # Content area
        self.content_area = QStackedWidget()
        layout.addWidget(self.content_area, 1)

        self.stacked_widget.addWidget(main_widget)
        self.stacked_widget.setCurrentWidget(main_widget)

        # Load dashboard
        self.load_module("dashboard")

    def create_sidebar(self):
        """Create navigation sidebar"""
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(200)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 20, 0, 20)
        layout.setSpacing(5)

        # User info
        user_label = QLabel(f"👤 {self.current_user['full_name']}")
        user_label.setStyleSheet("color: white; padding: 10px 20px; font-size: 13px;")
        user_label.setWordWrap(True)
        layout.addWidget(user_label)

        role_label = QLabel(f"Role: {self.current_user['role'].title()}")
        role_label.setStyleSheet("color: rgba(255,255,255,0.7); padding: 0px 20px 10px 20px; font-size: 11px;")
        layout.addWidget(role_label)

        # Divider
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: rgba(255,255,255,0.2);")
        layout.addWidget(line)

        layout.addSpacing(10)

        # Navigation buttons
        nav_items = [
            ("📊 Dashboard", "dashboard"),
            ("📋 Reports", "reports"),
        ]

        if has_permission(self.current_user['role'], 'add_report'):
            nav_items.append(("➕ Add Report", "add_report"))

        if has_permission(self.current_user['role'], 'access_admin_panel'):
            nav_items.append(("⚙️ Admin", "admin"))

        if has_permission(self.current_user['role'], 'export'):
            nav_items.append(("💾 Export", "export"))

        self.nav_buttons = {}
        for label, module_name in nav_items:
            btn = QPushButton(label)
            btn.setObjectName("navButton")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, m=module_name: self.load_module(m))
            layout.addWidget(btn)
            self.nav_buttons[module_name] = btn

        layout.addStretch()

        # Logout button
        logout_btn = QPushButton("🚪 Logout")
        logout_btn.setObjectName("navButton")
        logout_btn.clicked.connect(self.logout)
        layout.addWidget(logout_btn)

        return sidebar

    def load_module(self, module_name):
        """Load application module"""
        # Uncheck all buttons
        for btn in self.nav_buttons.values():
            btn.setChecked(False)

        # Check current button
        if module_name in self.nav_buttons:
            self.nav_buttons[module_name].setChecked(True)

        # Load module
        if module_name == "dashboard":
            self.load_dashboard()
        elif module_name == "reports":
            self.load_reports()
        elif module_name == "add_report":
            self.load_add_report()
        elif module_name == "admin":
            self.load_admin()
        elif module_name == "export":
            self.load_export()

    def load_dashboard(self):
        """Load dashboard"""
        from dashboard_module import DashboardModule

        widget = DashboardModule(self.db_manager, self.current_user, self)
        self.content_area.addWidget(widget)
        self.content_area.setCurrentWidget(widget)

    def load_reports(self):
        """Load reports list"""
        from reports_module import ReportsModule

        widget = ReportsModule(self.db_manager, self.current_user, self)
        self.content_area.addWidget(widget)
        self.content_area.setCurrentWidget(widget)

    def load_add_report(self):
        """Load add report form"""
        from add_report_module import AddReportModule

        widget = AddReportModule(self.db_manager, self.current_user, self)
        self.content_area.addWidget(widget)
        self.content_area.setCurrentWidget(widget)

    def load_admin(self):
        """Load admin panel"""
        from admin_panel import AdminPanel

        widget = AdminPanel(self.db_manager, self.current_user, self)
        self.content_area.addWidget(widget)
        self.content_area.setCurrentWidget(widget)

    def load_export(self):
        """Load export module"""
        from export_module import ExportModule

        widget = ExportModule(self.db_manager, self.current_user, self)
        self.content_area.addWidget(widget)
        self.content_area.setCurrentWidget(widget)

    def logout(self):
        """Logout user"""
        logger.info(f"User logging out: {self.current_user['username']}")
        self.current_user = None

        # Clear content area
        while self.content_area.count() > 0:
            widget = self.content_area.widget(0)
            self.content_area.removeWidget(widget)
            widget.deleteLater()

        # Show login
        self.show_login()


def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))

    logger.info("=" * 50)
    logger.info("FIU Report Management System (PyQt6) Starting")
    logger.info("=" * 50)

    window = MainApplication()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
