"""
Main application window for FIU Report Management System.
Contains navigation and view management.
"""

from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QStackedWidget, QFrame,
                             QMenuBar, QMenu, QToolBar, QStatusBar, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QIcon, QFont
from pathlib import Path
from services.icon_service import get_icon
from services.keyboard_shortcuts_service import KeyboardShortcutsService


class MainWindow(QMainWindow):
    """
    Main application window with navigation and view management.

    Signals:
        logout_requested: Emitted when user requests logout
    """

    logout_requested = pyqtSignal()

    def __init__(self, auth_service, logging_service, report_service, dashboard_service, db_manager=None):
        """
        Initialize the main window.

        Args:
            auth_service: AuthService instance
            logging_service: LoggingService instance
            report_service: ReportService instance
            dashboard_service: DashboardService instance
            db_manager: DatabaseManager instance (optional)
        """
        super().__init__()
        self.auth_service = auth_service
        self.logging_service = logging_service
        self.report_service = report_service
        self.dashboard_service = dashboard_service
        self.db_manager = db_manager

        self.current_user = auth_service.get_current_user()

        # Initialize keyboard shortcuts service
        self.shortcuts_service = KeyboardShortcutsService()

        self.setup_ui()
        self.setup_menu_bar()
        self.setup_tool_bar()
        self.setup_status_bar()
        self.setup_shortcuts()
        self.load_initial_view()

    def setup_ui(self):
        """Setup the user interface."""
        self.setWindowTitle("FIU Report Management System")
        self.setMinimumSize(1200, 800)
        self.showMaximized()

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Left sidebar navigation
        self.sidebar = self.create_sidebar()
        main_layout.addWidget(self.sidebar)

        # Content area
        content_frame = QFrame()
        content_frame.setStyleSheet("background-color: #f5f7fa;")
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Header
        header = self.create_header()
        content_layout.addWidget(header)

        # Stacked widget for views
        self.stacked_widget = QStackedWidget()
        content_layout.addWidget(self.stacked_widget)

        main_layout.addWidget(content_frame, stretch=1)

        # Initialize views (will be created by subclasses or imported)
        self.views = {}

    def create_sidebar(self):
        """
        Create the left sidebar navigation.

        Returns:
            QFrame: Sidebar widget
        """
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)
        sidebar.setStyleSheet("""
            QFrame#sidebar {
                background-color: #34495e;
                border-right: 1px solid #2c3e50;
            }
            QPushButton {
                background-color: transparent;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 12px 16px;
                text-align: left;
                font-size: 11pt;
            }
            QPushButton:hover {
                background-color: #2c3e50;
            }
            QPushButton:checked {
                background-color: #3498db;
                font-weight: 600;
            }
        """)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(8, 16, 8, 16)
        layout.setSpacing(4)

        # App logo/title
        title_label = QLabel("FIU System")
        title_label.setStyleSheet("""
            color: white;
            font-size: 16pt;
            font-weight: 600;
            padding: 12px;
        """)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        layout.addSpacing(20)

        # Navigation buttons
        self.nav_buttons = {}

        # Dashboard
        self.nav_buttons['dashboard'] = self.create_nav_button("Dashboard", "dashboard", "dashboard")
        layout.addWidget(self.nav_buttons['dashboard'])

        # Reports
        self.nav_buttons['reports'] = self.create_nav_button("Reports", "reports", "clipboard-list")
        layout.addWidget(self.nav_buttons['reports'])

        # Add Report (if has permission)
        if self.auth_service.has_permission('add_report'):
            self.nav_buttons['add_report'] = self.create_nav_button("Add Report", "add_report", "plus")
            layout.addWidget(self.nav_buttons['add_report'])

        # Export
        if self.auth_service.has_permission('export'):
            self.nav_buttons['export'] = self.create_nav_button("Export", "export", "download")
            layout.addWidget(self.nav_buttons['export'])

        # Admin Panel (admin only)
        if self.current_user and self.current_user['role'] == 'admin':
            layout.addSpacing(20)

            admin_label = QLabel("ADMINISTRATION")
            admin_label.setStyleSheet("""
                color: #95a5a6;
                font-size: 9pt;
                font-weight: 600;
                padding: 8px 16px;
            """)
            layout.addWidget(admin_label)

            self.nav_buttons['users'] = self.create_nav_button("Users", "users", "users")
            layout.addWidget(self.nav_buttons['users'])

            self.nav_buttons['logs'] = self.create_nav_button("System Logs", "logs", "history")
            layout.addWidget(self.nav_buttons['logs'])

            self.nav_buttons['settings'] = self.create_nav_button("Settings", "settings", "cog")
            layout.addWidget(self.nav_buttons['settings'])

        layout.addStretch()

        # User info at bottom
        user_frame = QFrame()
        user_frame.setStyleSheet("""
            QFrame {
                background-color: #2c3e50;
                border-radius: 6px;
                padding: 8px;
            }
            QLabel {
                color: white;
            }
        """)
        user_layout = QVBoxLayout(user_frame)
        user_layout.setContentsMargins(12, 8, 12, 8)
        user_layout.setSpacing(4)

        user_name = QLabel(self.current_user['full_name'] if self.current_user else "User")
        user_name.setStyleSheet("font-weight: 600; font-size: 10pt;")

        user_role = QLabel(self.current_user['role'].capitalize() if self.current_user else "")
        user_role.setStyleSheet("color: #95a5a6; font-size: 9pt;")

        user_layout.addWidget(user_name)
        user_layout.addWidget(user_role)

        # My Profile button
        profile_btn = QPushButton("My Profile")
        profile_btn.setIcon(get_icon('user', color='#ffffff'))
        profile_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #0d7377;
                border: 1px solid #0d7377;
                padding: 6px;
                border-radius: 4px;
                margin-top: 8px;
            }
            QPushButton:hover {
                background-color: #0d7377;
                color: white;
            }
        """)
        profile_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        profile_btn.clicked.connect(self.show_profile)
        user_layout.addWidget(profile_btn)

        layout.addWidget(user_frame)

        # Logout button
        logout_btn = QPushButton("Logout")
        logout_btn.setIcon(get_icon('sign-out-alt', color='#ffffff'))
        logout_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                padding: 10px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        logout_btn.clicked.connect(self.handle_logout)
        layout.addWidget(logout_btn)

        return sidebar

    def create_nav_button(self, text: str, view_id: str, icon_name: str = None):
        """
        Create a navigation button.

        Args:
            text: Button text
            view_id: View identifier
            icon_name: Icon name for the button

        Returns:
            QPushButton: Navigation button
        """
        button = QPushButton(text)
        button.setCheckable(True)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.clicked.connect(lambda: self.switch_view(view_id))

        # Add icon if specified
        if icon_name:
            button.setIcon(get_icon(icon_name, color='#ffffff'))

        return button

    def create_header(self):
        """
        Create the header bar.

        Returns:
            QFrame: Header widget
        """
        header = QFrame()
        header.setFixedHeight(60)
        header.setStyleSheet("""
            QFrame {
                background-color: white;
                border-bottom: 1px solid #d0d7de;
            }
        """)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(24, 0, 24, 0)

        # Page title
        self.page_title = QLabel("Dashboard")
        self.page_title.setObjectName("titleLabel")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setWeight(QFont.Weight.Bold)
        self.page_title.setFont(title_font)

        layout.addWidget(self.page_title)
        layout.addStretch()

        # Quick actions could go here

        return header

    def setup_menu_bar(self):
        """Setup the menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        if self.auth_service.has_permission('export'):
            export_action = QAction(get_icon('file-export'), "&Export Reports", self)
            export_action.triggered.connect(lambda: self.switch_view('export'))
            file_menu.addAction(export_action)

        file_menu.addSeparator()

        logout_action = QAction(get_icon('sign-out-alt'), "&Logout", self)
        logout_action.triggered.connect(self.handle_logout)
        file_menu.addAction(logout_action)

        exit_action = QAction(get_icon('times-circle'), "E&xit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # View menu
        view_menu = menubar.addMenu("&View")

        dashboard_action = QAction(get_icon('dashboard'), "&Dashboard", self)
        dashboard_action.triggered.connect(lambda: self.switch_view('dashboard'))
        view_menu.addAction(dashboard_action)

        reports_action = QAction(get_icon('clipboard-list'), "&Reports", self)
        reports_action.triggered.connect(lambda: self.switch_view('reports'))
        view_menu.addAction(reports_action)

        # Admin menu (admin only)
        if self.current_user and self.current_user['role'] == 'admin':
            admin_menu = menubar.addMenu("&Admin")

            users_action = QAction(get_icon('users'), "&Users", self)
            users_action.triggered.connect(lambda: self.switch_view('users'))
            admin_menu.addAction(users_action)

            logs_action = QAction(get_icon('history'), "System &Logs", self)
            logs_action.triggered.connect(lambda: self.switch_view('logs'))
            admin_menu.addAction(logs_action)

            settings_action = QAction(get_icon('cog'), "&Settings", self)
            settings_action.triggered.connect(lambda: self.switch_view('settings'))
            admin_menu.addAction(settings_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")

        help_action = QAction(get_icon('book'), "&Help & Documentation", self)
        help_action.setShortcut("F1")
        help_action.triggered.connect(self.show_help)
        help_menu.addAction(help_action)

        help_menu.addSeparator()

        about_action = QAction(get_icon('info-circle'), "&About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def setup_tool_bar(self):
        """Setup the toolbar."""
        self.toolbar = QToolBar("Main Toolbar")
        self.toolbar.setMovable(False)
        self.addToolBar(self.toolbar)

        # Add common actions
        if self.auth_service.has_permission('add_report'):
            add_report_action = QAction(get_icon('plus'), "New Report", self)
            add_report_action.triggered.connect(lambda: self.switch_view('add_report'))
            self.toolbar.addAction(add_report_action)

        self.toolbar.addSeparator()

        refresh_action = QAction(get_icon('refresh'), "Refresh", self)
        refresh_action.triggered.connect(self.refresh_current_view)
        self.toolbar.addAction(refresh_action)

    def setup_status_bar(self):
        """Setup the status bar."""
        self.statusBar().showMessage("Ready")

    def setup_shortcuts(self):
        """Setup keyboard shortcuts for the application."""

        # Navigation shortcuts
        self.shortcuts_service.create_shortcut(
            self, "dashboard", lambda: self.switch_view('dashboard')
        )

        self.shortcuts_service.create_shortcut(
            self, "reports", lambda: self.switch_view('reports')
        )

        if 'export' in self.views:
            self.shortcuts_service.create_shortcut(
                self, "export", lambda: self.switch_view('export')
            )

        if 'settings' in self.views:
            self.shortcuts_service.create_shortcut(
                self, "settings", lambda: self.switch_view('settings')
            )

        # Actions
        if self.auth_service.has_permission('add_report'):
            self.shortcuts_service.create_shortcut(
                self, "new_report", self.quick_add_report
            )

        self.shortcuts_service.create_shortcut(
            self, "refresh", self.refresh_current_view
        )

        self.shortcuts_service.create_shortcut(
            self, "search", self.focus_search
        )

        # System shortcuts
        self.shortcuts_service.create_shortcut(
            self, "help", self.show_help
        )

        self.shortcuts_service.create_shortcut(
            self, "profile", self.show_profile
        )

        self.shortcuts_service.create_shortcut(
            self, "quit", self.close
        )

        self.logging_service.info("Keyboard shortcuts initialized")

    def quick_add_report(self):
        """Quick action to add a new report."""
        try:
            from ui.dialogs.report_dialog import ReportDialog

            dialog = ReportDialog(
                self.report_service,
                self.logging_service,
                parent=self
            )

            # Refresh reports view after saving
            current_widget = self.stacked_widget.currentWidget()
            if hasattr(current_widget, 'load_reports'):
                dialog.report_saved.connect(current_widget.load_reports)

            dialog.exec()
        except Exception as e:
            self.logging_service.error(f"Error opening report dialog: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to open report dialog:\n{str(e)}")

    def focus_search(self):
        """Focus the search box in the current view."""
        current_widget = self.stacked_widget.currentWidget()
        if hasattr(current_widget, 'search_input'):
            current_widget.search_input.setFocus()
            current_widget.search_input.selectAll()

    def add_view(self, view_id: str, widget: QWidget):
        """
        Add a view to the stacked widget.

        Args:
            view_id: Unique identifier for the view
            widget: Widget to add
        """
        self.views[view_id] = self.stacked_widget.addWidget(widget)

    def switch_view(self, view_id: str):
        """
        Switch to a specific view.

        Args:
            view_id: View identifier
        """
        if view_id in self.views:
            # Update navigation buttons
            for btn_id, button in self.nav_buttons.items():
                button.setChecked(btn_id == view_id)

            # Switch view
            self.stacked_widget.setCurrentIndex(self.views[view_id])

            # Update page title
            titles = {
                'dashboard': 'Dashboard',
                'reports': 'Reports',
                'add_report': 'Add Report',
                'export': 'Export Data',
                'users': 'User Management',
                'logs': 'System Logs',
                'settings': 'Settings'
            }
            self.page_title.setText(titles.get(view_id, view_id.title()))

            # Log view change
            self.logging_service.log_user_action(f"Switched to {view_id} view")
        else:
            self.statusBar().showMessage(f"View '{view_id}' not found", 3000)

    def load_initial_view(self):
        """Load the initial view (dashboard)."""
        if 'dashboard' in self.nav_buttons:
            self.nav_buttons['dashboard'].setChecked(True)

    def refresh_current_view(self):
        """Refresh the current view."""
        current_widget = self.stacked_widget.currentWidget()
        if hasattr(current_widget, 'refresh'):
            current_widget.refresh()
            self.statusBar().showMessage("View refreshed", 2000)

    def handle_logout(self):
        """Handle logout request."""
        reply = QMessageBox.question(
            self,
            "Confirm Logout",
            "Are you sure you want to logout?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.auth_service.logout()
            self.logout_requested.emit()
            self.close()

    def show_profile(self):
        """Show user profile dialog."""
        from ui.dialogs.user_profile_dialog import UserProfileDialog
        try:
            if not self.db_manager:
                QMessageBox.warning(
                    self,
                    "Not Available",
                    "User profile requires database access."
                )
                return

            profile_dialog = UserProfileDialog(
                self.auth_service,
                self.logging_service,
                self.db_manager,
                self
            )
            profile_dialog.exec()
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to open user profile: {str(e)}"
            )
            self.logging_service.error(f"Error opening user profile: {str(e)}")

    def show_help(self):
        """Show help dialog."""
        from ui.dialogs.help_dialog import HelpDialog
        help_dialog = HelpDialog(self, shortcuts_service=self.shortcuts_service)
        help_dialog.exec()

    def show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About FIU Report Management System",
            "<h3>FIU Report Management System</h3>"
            "<p>Version 2.0.0</p>"
            "<p>Financial Intelligence Unit Report Management</p>"
            "<p>Built with PyQt6 and modern architecture</p>"
        )

    def closeEvent(self, event):
        """Handle window close event."""
        reply = QMessageBox.question(
            self,
            "Confirm Exit",
            "Are you sure you want to exit the application?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.auth_service.logout()
            event.accept()
        else:
            event.ignore()
