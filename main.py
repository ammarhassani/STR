"""
FIU Report Management System - Main Entry Point
Modern PyQt6-based application with modular architecture.

Version: 2.0.0
Technology: Python 3.9+ | PyQt6 | SQLite3
"""

import sys
import logging
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import configuration
from config import Config

# Import database components
from database.db_manager import DatabaseManager
from database.init_db import validate_database
from database.migrations import migrate_database

# Import services
from services.logging_service import LoggingService
from services.auth_service import AuthService
from services.report_service import ReportService
from services.version_service import VersionService
from services.approval_service import ApprovalService
from services.dashboard_service import DashboardService
from services.settings_service import SettingsService
from services.dropdown_service import DropdownService
from services.validation_service import ValidationService
from services.report_number_service import ReportNumberService

# Import UI windows
from ui.windows.login_window import LoginWindow
from ui.windows.main_window import MainWindow
from ui.windows.setup_wizard import SetupWizard
from ui.widgets.dashboard_view import DashboardView
from ui.widgets.log_management_view import LogManagementView
from ui.widgets.reports_view import ReportsView
from ui.widgets.export_view import ExportView
from ui.widgets.admin_panel import AdminPanel
from ui.widgets.approval_panel import ApprovalPanel
from ui.widgets.placeholder_view import PlaceholderView
from ui.widgets.settings_view import SettingsView
from ui.widgets.dropdown_management_view import DropdownManagementView
from ui.widgets.system_settings_view import SystemSettingsView
from ui.widgets.field_management_view import FieldManagementView


class FIUApplication:
    """
    Main application class that orchestrates the entire system.
    Handles initialization, dependency injection, and window management.
    """

    def __init__(self):
        """Initialize the application."""
        self.app = None
        self.db_manager = None
        self.logging_service = None
        self.auth_service = None
        self.report_service = None
        self.version_service = None
        self.approval_service = None
        self.dashboard_service = None
        self.settings_service = None
        self.dropdown_service = None
        self.validation_service = None

        self.setup_wizard = None
        self.login_window = None
        self.main_window = None

    def run(self):
        """Run the application."""
        # Create QApplication
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("finan")
        self.app.setApplicationVersion("2.0.0")
        self.app.setOrganizationName("FIU")

        # Store reference to this FIU app for theme changes
        self.app._fiu_app = self

        # Set application font
        font = QFont("Segoe UI", 10)
        self.app.setFont(font)

        # Load configuration
        Config.load()

        # Check if system is configured
        if not Config.is_configured():
            # First run - show setup wizard
            self.show_setup_wizard()
        else:
            # System configured - initialize and show login
            try:
                if not self.initialize_application():
                    QMessageBox.critical(
                        None,
                        "Initialization Error",
                        "Failed to initialize application. Please check the logs."
                    )
                    return 1

                # Load theme
                self.load_theme()

                # Show login window
                self.show_login()

            except Exception as e:
                QMessageBox.critical(
                    None,
                    "Fatal Error",
                    f"An unexpected error occurred:\n{str(e)}"
                )
                return 1

        # Run event loop
        return self.app.exec()

    def show_setup_wizard(self):
        """Show setup wizard for first-time configuration."""
        self.setup_wizard = SetupWizard()
        self.setup_wizard.setup_completed.connect(self.on_setup_completed)
        self.setup_wizard.show()

    def on_setup_completed(self, db_path, backup_path):
        """
        Handle setup wizard completion.

        Args:
            db_path: Database file path
            backup_path: Backup directory path
        """
        # Save configuration
        Config.DATABASE_PATH = db_path
        Config.BACKUP_PATH = backup_path
        Config.save()

        # Close setup wizard
        if self.setup_wizard:
            self.setup_wizard.close()
            self.setup_wizard = None

        # Initialize application
        try:
            if not self.initialize_application():
                QMessageBox.critical(
                    None,
                    "Initialization Error",
                    "Failed to initialize application after setup."
                )
                sys.exit(1)

            # Load theme
            self.load_theme()

            # Show login window
            self.show_login()

        except Exception as e:
            QMessageBox.critical(
                None,
                "Initialization Error",
                f"Failed to initialize application:\n{str(e)}"
            )
            sys.exit(1)

    def initialize_application(self):
        """
        Initialize application components.

        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            # Validate paths
            is_valid, message = Config.validate_paths()
            if not is_valid:
                QMessageBox.warning(
                    None,
                    "Configuration Error",
                    f"Invalid configuration:\n{message}"
                )
                return False

            # Initialize database manager
            db_path = Path(Config.DATABASE_PATH)
            self.db_manager = DatabaseManager(str(db_path))

            # Validate database
            is_valid, message = validate_database(str(db_path))
            if not is_valid:
                QMessageBox.critical(
                    None,
                    "Database Error",
                    f"Database validation failed:\n{message}"
                )
                return False

            # Initialize logging service first
            log_dir = Path.home() / '.fiu_system'
            self.logging_service = LoggingService(self.db_manager, log_dir)

            # Run migrations
            success, migration_msg = migrate_database(str(db_path))
            if not success:
                QMessageBox.warning(
                    None,
                    "Migration Warning",
                    f"Database migration issue:\n{migration_msg}"
                )
            elif "No migrations needed" not in migration_msg:
                self.logging_service.info(f"Database migration: {migration_msg}")
            self.logging_service.info("=" * 60)
            self.logging_service.info("FIU Report Management System Starting")
            self.logging_service.info("Version 2.0.0 - PyQt6 Edition")
            self.logging_service.info("=" * 60)

            # Initialize services
            self.auth_service = AuthService(self.db_manager, self.logging_service)
            self.settings_service = SettingsService(self.db_manager, self.auth_service)
            self.report_service = ReportService(self.db_manager, self.logging_service, self.auth_service)
            self.dashboard_service = DashboardService(self.db_manager, self.logging_service)
            self.dropdown_service = DropdownService(self.db_manager, self.logging_service)
            self.validation_service = ValidationService(self.db_manager, self.logging_service)
            self.report_number_service = ReportNumberService(self.db_manager, self.logging_service)

            # Initialize version and approval services (depend on report_service)
            self.version_service = VersionService(self.db_manager, self.logging_service, self.auth_service, self.report_service)
            self.approval_service = ApprovalService(self.db_manager, self.logging_service, self.auth_service, self.version_service, self.report_service)

            self.logging_service.info("All services initialized successfully")
            return True

        except Exception as e:
            error_msg = f"Initialization error: {str(e)}"
            print(error_msg)
            if self.logging_service:
                self.logging_service.error(error_msg, exc_info=True)
            return False

    def load_theme(self):
        """Load and apply the dark theme."""
        try:
            self.apply_theme()
        except Exception as e:
            if self.logging_service:
                self.logging_service.error(f"Error loading theme: {str(e)}")

    def apply_theme(self):
        """Apply the dark theme."""
        try:
            stylesheet_path = project_root / "resources" / "style_dark.qss"

            if stylesheet_path.exists():
                with open(stylesheet_path, 'r', encoding='utf-8') as f:
                    stylesheet = f.read()
                    self.app.setStyleSheet(stylesheet)

                if self.logging_service:
                    self.logging_service.info("Dark theme applied")
            else:
                if self.logging_service:
                    self.logging_service.warning(f"Theme file not found: {stylesheet_path}")

        except Exception as e:
            if self.logging_service:
                self.logging_service.error(f"Error applying theme: {str(e)}")

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
            self.dashboard_service,
            approval_service=self.approval_service,
            db_manager=self.db_manager,
            report_number_service=self.report_number_service
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
            self.logging_service,
            self.auth_service,
            self.version_service,
            self.approval_service
        )
        self.main_window.add_view('reports', reports_view)

        # Export view
        if self.auth_service.has_permission('export'):
            export_view = ExportView(
                self.db_manager,
                self.logging_service
            )
            self.main_window.add_view('export', export_view)

        # Admin views (admin only)
        if self.auth_service.get_current_user()['role'] == 'admin':
            # Approval management
            current_user = self.auth_service.get_current_user()
            approvals_view = ApprovalPanel(
                self.report_service,
                current_user,
                self.approval_service,
                self.version_service
            )
            self.main_window.add_view('approvals', approvals_view)

            # Users management
            users_view = AdminPanel(
                self.db_manager,
                self.logging_service
            )
            self.main_window.add_view('users', users_view)

            # System logs view
            log_view = LogManagementView(self.logging_service)
            self.main_window.add_view('logs', log_view)

            # Settings view
            settings_view = SettingsView(
                self.settings_service,
                self.auth_service,
                self,
                self.db_manager,
                self.logging_service
            )
            self.main_window.add_view('settings', settings_view)

            # Dropdown Management view
            dropdown_mgmt_view = DropdownManagementView(
                self.dropdown_service,
                self.logging_service,
                current_user
            )
            self.main_window.add_view('dropdown_mgmt', dropdown_mgmt_view)

            # System Settings view
            system_settings_view = SystemSettingsView(
                self.db_manager,
                self.logging_service,
                current_user
            )
            self.main_window.add_view('system_settings', system_settings_view)

            # Field Management view
            field_management_view = FieldManagementView(
                self.validation_service,
                self.logging_service,
                current_user
            )
            self.main_window.add_view('field_management', field_management_view)

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
