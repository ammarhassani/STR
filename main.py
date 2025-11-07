"""
FIU Report Management System - Main Entry Point
Modern PyQt6-based application with modular architecture.

Version: 2.0.0
Technology: Python 3.9+ | PyQt6 | SQLite3
"""

import sys
import logging
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMessageBox, QSplashScreen
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QFont

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import configuration
from config import Config

# Import database components
from database.db_manager import DatabaseManager
from database.init_db import initialize_database, validate_database

# Import services
from services.logging_service import LoggingService
from services.auth_service import AuthService
from services.report_service import ReportService
from services.dashboard_service import DashboardService

# Import UI windows
from ui.windows.login_window import LoginWindow
from ui.windows.main_window import MainWindow
from ui.widgets.dashboard_view import DashboardView
from ui.widgets.log_management_view import LogManagementView
from ui.widgets.reports_view import ReportsView
from ui.widgets.placeholder_view import PlaceholderView


class FIUApplication:
    """
    Main application class that orchestrates the entire system.
    Handles initialization, dependency injection, and window management.
    """

    def __init__(self):
        """Initialize the application."""
        self.app = None
        self.config = None
        self.db_manager = None
        self.logging_service = None
        self.auth_service = None
        self.report_service = None
        self.dashboard_service = None

        self.login_window = None
        self.main_window = None

    def run(self):
        """Run the application."""
        # Create QApplication
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("FIU Report Management System")
        self.app.setApplicationVersion("2.0.0")
        self.app.setOrganizationName("FIU")

        # Set application font
        font = QFont("Segoe UI", 10)
        self.app.setFont(font)

        # Initialize application
        try:
            if not self.initialize_application():
                QMessageBox.critical(
                    None,
                    "Initialization Error",
                    "Failed to initialize application. Please check the logs."
                )
                return 1

            # Load stylesheet
            self.load_stylesheet()

            # Show login window
            self.show_login()

            # Run event loop
            return self.app.exec()

        except Exception as e:
            QMessageBox.critical(
                None,
                "Fatal Error",
                f"An unexpected error occurred:\n{str(e)}"
            )
            if self.logging_service:
                self.logging_service.critical(f"Fatal application error: {str(e)}", exc_info=True)
            return 1

    def initialize_application(self):
        """
        Initialize application components.

        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            # Load configuration
            self.config = Config.load()

            if not self.config.is_configured():
                # First run - setup required
                QMessageBox.information(
                    None,
                    "First Run Setup",
                    "Welcome to FIU Report Management System!\n\n"
                    "This appears to be your first run. Please configure the system.\n\n"
                    "For now, we'll use default settings:\n"
                    "Database: ~/FIU_System/database/fiu_reports.db\n"
                    "Backup: ~/FIU_System/backups/"
                )

                # Set default paths
                default_base = Path.home() / "FIU_System"
                default_base.mkdir(parents=True, exist_ok=True)

                db_dir = default_base / "database"
                db_dir.mkdir(parents=True, exist_ok=True)

                backup_dir = default_base / "backups"
                backup_dir.mkdir(parents=True, exist_ok=True)

                self.config.database_path = str(db_dir / "fiu_reports.db")
                self.config.backup_path = str(backup_dir)
                self.config.save()

            # Initialize database
            db_path = Path(self.config.database_path)

            # Ensure database directory exists
            db_path.parent.mkdir(parents=True, exist_ok=True)

            # Check if database needs initialization
            if not db_path.exists():
                print("Database not found. Creating new database...")
                schema_path = project_root / "database" / "schema.sql"

                if not schema_path.exists():
                    raise FileNotFoundError(f"Database schema not found: {schema_path}")

                initialize_database(str(db_path), str(schema_path))
                print("Database created successfully")

            # Initialize database manager
            self.db_manager = DatabaseManager(str(db_path))

            # Validate database
            is_valid, errors = validate_database(self.db_manager)
            if not is_valid:
                error_msg = "Database validation failed:\n" + "\n".join(errors)
                QMessageBox.critical(None, "Database Error", error_msg)
                return False

            # Initialize logging service
            log_dir = Path.home() / '.fiu_system'
            self.logging_service = LoggingService(self.db_manager, log_dir)
            self.logging_service.info("=" * 60)
            self.logging_service.info("FIU Report Management System Starting")
            self.logging_service.info("Version 2.0.0 - PyQt6 Edition")
            self.logging_service.info("=" * 60)

            # Initialize services
            self.auth_service = AuthService(self.db_manager, self.logging_service)
            self.report_service = ReportService(self.db_manager, self.logging_service, self.auth_service)
            self.dashboard_service = DashboardService(self.db_manager, self.logging_service)

            self.logging_service.info("All services initialized successfully")
            return True

        except Exception as e:
            error_msg = f"Initialization error: {str(e)}"
            print(error_msg)
            if self.logging_service:
                self.logging_service.error(error_msg, exc_info=True)
            return False

    def load_stylesheet(self):
        """Load and apply the QSS stylesheet."""
        try:
            stylesheet_path = project_root / "resources" / "style.qss"
            if stylesheet_path.exists():
                with open(stylesheet_path, 'r', encoding='utf-8') as f:
                    stylesheet = f.read()
                    self.app.setStyleSheet(stylesheet)
                    self.logging_service.info("Stylesheet loaded successfully")
            else:
                self.logging_service.warning(f"Stylesheet not found: {stylesheet_path}")
        except Exception as e:
            self.logging_service.error(f"Error loading stylesheet: {str(e)}")

    def show_login(self):
        """Show the login window."""
        self.login_window = LoginWindow(self.auth_service)
        self.login_window.login_successful.connect(self.on_login_successful)
        self.login_window.show()

    def on_login_successful(self, user: dict):
        """
        Handle successful login.

        Args:
            user: User dictionary with user information
        """
        self.logging_service.info(f"User logged in: {user['username']}")

        # Create and show main window
        self.show_main_window()

    def show_main_window(self):
        """Show the main application window."""
        self.main_window = MainWindow(
            self.auth_service,
            self.logging_service,
            self.report_service,
            self.dashboard_service
        )

        # Add views to main window
        self.setup_views()

        # Connect logout signal
        self.main_window.logout_requested.connect(self.on_logout)

        # Show main window
        self.main_window.show()

    def setup_views(self):
        """Setup and add views to the main window."""
        # Dashboard view
        dashboard_view = DashboardView(
            self.dashboard_service,
            self.logging_service
        )
        self.main_window.add_view('dashboard', dashboard_view)

        # Reports view
        reports_view = ReportsView(
            self.report_service,
            self.logging_service
        )
        self.main_window.add_view('reports', reports_view)

        # Add Report view (placeholder)
        if self.auth_service.has_permission('add_report'):
            add_report_view = PlaceholderView(
                "Add Report",
                "Comprehensive report entry form with validation and field management."
            )
            self.main_window.add_view('add_report', add_report_view)

        # Export view (placeholder)
        if self.auth_service.has_permission('export'):
            export_view = PlaceholderView(
                "Export Data",
                "Export reports to CSV with filtering and customization options."
            )
            self.main_window.add_view('export', export_view)

        # Admin views
        if self.auth_service.get_current_user()['role'] == 'admin':
            # Users management (placeholder)
            users_view = PlaceholderView(
                "User Management",
                "Create, edit, and manage user accounts with role-based permissions."
            )
            self.main_window.add_view('users', users_view)

            # System logs view
            log_view = LogManagementView(self.logging_service)
            self.main_window.add_view('logs', log_view)

            # Settings view (placeholder)
            settings_view = PlaceholderView(
                "System Settings",
                "Configure system parameters, backup schedules, and application preferences."
            )
            self.main_window.add_view('settings', settings_view)

        # Switch to dashboard
        self.main_window.switch_view('dashboard')

    def on_logout(self):
        """Handle logout."""
        self.logging_service.info("User logged out")

        # Close main window if open
        if self.main_window:
            self.main_window.close()
            self.main_window = None

        # Show login window again
        self.show_login()


def main():
    """Main entry point."""
    app = FIUApplication()
    sys.exit(app.run())


if __name__ == "__main__":
    main()
