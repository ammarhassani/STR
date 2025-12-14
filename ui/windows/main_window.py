"""
Main application window for FIU Report Management System.
Contains navigation and view management.
"""

from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QStackedWidget, QFrame,
                             QMenuBar, QMenu, QToolBar, QStatusBar, QMessageBox,
                             QSizePolicy, QApplication, QScrollArea)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QAction, QIcon, QFont
from pathlib import Path
from services.icon_service import get_icon
from services.keyboard_shortcuts_service import KeyboardShortcutsService
from ui.utils.responsive_sizing import ResponsiveSize
from ui.themes import ModernTheme
from ui.theme_colors import ThemeColors


class MainWindow(QMainWindow):
    """
    Main application window with navigation and view management.

    Signals:
        logout_requested: Emitted when user requests logout
    """

    logout_requested = pyqtSignal()

    def __init__(self, auth_service, logging_service, report_service, dashboard_service, approval_service=None, db_manager=None, report_number_service=None):
        """
        Initialize the main window.

        Args:
            auth_service: AuthService instance
            logging_service: LoggingService instance
            report_service: ReportService instance
            dashboard_service: DashboardService instance
            approval_service: ApprovalService instance (optional)
            db_manager: DatabaseManager instance (optional)
            report_number_service: ReportNumberService instance (optional)
        """
        super().__init__()
        self.auth_service = auth_service
        self.logging_service = logging_service
        self.report_service = report_service
        self.approval_service = approval_service
        self.report_number_service = report_number_service
        self.dashboard_service = dashboard_service
        self.db_manager = db_manager

        self.current_user = auth_service.get_current_user()

        # Initialize keyboard shortcuts service
        self.shortcuts_service = KeyboardShortcutsService()
        
        # Initialize resize timer for responsive behavior
        self.resize_timer = None
        self.resizing = False

        self.setup_ui()
        self.setup_menu_bar()
        self.setup_tool_bar()
        self.setup_status_bar()
        self.setup_shortcuts()
        self.load_initial_view()

    def setup_ui(self):
        """Setup the user interface."""
        self.setWindowTitle("FIU Report Management System")
        # Reduce minimum size to fit 15" laptop screens (1366x768)
        self.setMinimumSize(1024, 600)
        self.showMaximized()

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QHBoxLayout(central_widget)
        # Add proper margins and spacing for breathing room
        margin = ResponsiveSize.get_margin('normal')
        spacing = ResponsiveSize.get_spacing('normal')
        main_layout.setContentsMargins(margin, 0, margin, margin)  # Top stays 0 for header
        main_layout.setSpacing(spacing)

        # Left sidebar navigation
        self.sidebar = self.create_sidebar()
        main_layout.addWidget(self.sidebar)

        # Content area
        content_frame = QFrame()
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

        # Responsive sidebar width based on screen size
        screen_width = QApplication.primaryScreen().geometry().width()
        if screen_width >= 1920:
            sidebar.setMinimumWidth(ResponsiveSize.get_scaled_size(200))
            sidebar.setMaximumWidth(ResponsiveSize.get_scaled_size(320))
        elif screen_width >= 1400:
            sidebar.setMinimumWidth(ResponsiveSize.get_scaled_size(180))
            sidebar.setMaximumWidth(ResponsiveSize.get_scaled_size(250))
        else:
            sidebar.setMinimumWidth(ResponsiveSize.get_scaled_size(160))
            sidebar.setMaximumWidth(ResponsiveSize.get_scaled_size(200))

        sidebar.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

        # Dynamic stylesheet with responsive sizing
        padding_v = ResponsiveSize.get_scaled_size(12)
        padding_h = ResponsiveSize.get_scaled_size(16)
        font_size = ResponsiveSize.get_font_size('normal')
        border_radius = ResponsiveSize.get_scaled_size(4)

        sidebar.setStyleSheet(f"""
            QFrame#sidebar {{
                background-color: {ModernTheme.SIDEBAR_BG};
                border-right: 1px solid {ModernTheme.BORDER};
            }}
            QPushButton {{
                color: {ModernTheme.SIDEBAR_TEXT};
                background-color: transparent;
                border: none;
                text-align: left;
                padding: {padding_v}px {padding_h}px;
                font-size: {font_size}pt;
                border-radius: {border_radius}px;
            }}
            QPushButton:hover {{
                background-color: {ModernTheme.SIDEBAR_HOVER};
            }}
            QPushButton:checked {{
                background-color: {ModernTheme.PRIMARY};
                color: white;
                font-weight: 600;
            }}
        """)

        # Main sidebar layout (no margins here, will be on scroll content)
        main_sidebar_layout = QVBoxLayout(sidebar)
        main_sidebar_layout.setContentsMargins(0, 0, 0, 0)
        main_sidebar_layout.setSpacing(0)

        # App logo/title (fixed at top, not scrollable)
        title_label = QLabel("FIU System")
        title_label.setStyleSheet("""
            color: white;
            font-size: 16pt;
            font-weight: 600;
            padding: 12px;
        """)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_sidebar_layout.addWidget(title_label)

        # Create scroll area for nav buttons
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        # Content widget for scrollable buttons
        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)

        # Responsive margins and spacing
        margin_h = ResponsiveSize.get_margin('tight')
        margin_v = ResponsiveSize.get_margin('normal')
        spacing = ResponsiveSize.get_spacing('tight')
        layout.setContentsMargins(margin_h, margin_v, margin_h, margin_v)
        layout.setSpacing(spacing)

        # Navigation buttons
        self.nav_buttons = {}

        # Dashboard
        self.nav_buttons['dashboard'] = self.create_nav_button("Dashboard", "dashboard", "dashboard")
        layout.addWidget(self.nav_buttons['dashboard'])

        # Reports
        self.nav_buttons['reports'] = self.create_nav_button("Reports", "reports", "clipboard-list")
        layout.addWidget(self.nav_buttons['reports'])

        # Add Report (if has permission) - Opens dialog directly
        if self.auth_service.has_permission('add_report'):
            add_report_btn = QPushButton("Add Report")
            add_report_btn.setCheckable(False)
            add_report_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            add_report_btn.clicked.connect(self.quick_add_report)
            add_report_btn.setIcon(get_icon('plus', color='#ffffff'))
            layout.addWidget(add_report_btn)

        # Export
        if self.auth_service.has_permission('export'):
            self.nav_buttons['export'] = self.create_nav_button("Export", "export", "download")
            layout.addWidget(self.nav_buttons['export'])

        # Admin Panel (admin only)
        if self.current_user and self.current_user['role'] == 'admin':
            layout.addSpacing(20)

            admin_label = QLabel("ADMINISTRATION")
            admin_label.setStyleSheet(f"""
                color: {ThemeColors.TEXT_SECONDARY};
                font-size: 9pt;
                font-weight: 600;
                padding: 8px 16px;
            """)
            layout.addWidget(admin_label)

            self.nav_buttons['approvals'] = self.create_nav_button("Approvals", "approvals", "check-circle")
            layout.addWidget(self.nav_buttons['approvals'])

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
        user_role.setStyleSheet(f"color: {ThemeColors.TEXT_SECONDARY}; font-size: 9pt;")

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

        # Set scroll content and add to main sidebar layout
        scroll_area.setWidget(scroll_content)
        main_sidebar_layout.addWidget(scroll_area)

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
        header.setMinimumHeight(50)  # Reduced minimum height for smaller screens
        header.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        header.setStyleSheet("""
            QFrame {
                background-color: #0d1117;
                border-bottom: 1px solid #30363d;
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

        # Notification widget
        try:
            from ui.widgets.notification_widget import NotificationWidget
            self.notification_widget = NotificationWidget(
                self.approval_service,
                self.current_user,
                self
            )
            self.notification_widget.notification_clicked.connect(self.handle_notification_clicked)
            layout.addWidget(self.notification_widget)
        except Exception as e:
            self.logging_service.error(f"Error creating notification widget: {str(e)}")

        # Profile button in header for easy access
        self.profile_btn = QPushButton()
        self.profile_btn.setObjectName("profileButton")
        self.profile_btn.setIcon(get_icon('user', color='#ffffff'))
        self.profile_btn.setIconSize(ResponsiveSize.get_icon_size('medium'))
        self.profile_btn.setToolTip(f"Profile: {self.current_user['username'] if self.current_user else 'User'}")
        self.profile_btn.setCursor(Qt.CursorShape.PointingHandCursor)

        # Create profile menu
        profile_menu = QMenu(self)
        profile_menu.addAction("My Profile", self.show_profile)
        profile_menu.addSeparator()
        profile_menu.addAction("Logout", self.handle_logout)
        self.profile_btn.setMenu(profile_menu)

        # Style the profile button
        self.profile_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: 4px;
            }
        """)

        layout.addWidget(self.profile_btn)

        return header

    def setup_menu_bar(self):
        """Setup the menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        if self.auth_service.has_permission('export'):
            export_action = QAction(get_icon('file-export', color=ThemeColors.ICON_DEFAULT), "&Export Reports", self)
            export_action.triggered.connect(lambda: self.switch_view('export'))
            file_menu.addAction(export_action)

        file_menu.addSeparator()

        logout_action = QAction(get_icon('sign-out-alt', color=ThemeColors.ICON_DEFAULT), "&Logout", self)
        logout_action.triggered.connect(self.handle_logout)
        file_menu.addAction(logout_action)

        exit_action = QAction(get_icon('times-circle', color=ThemeColors.ICON_DEFAULT), "E&xit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # View menu
        view_menu = menubar.addMenu("&View")

        dashboard_action = QAction(get_icon('dashboard', color=ThemeColors.ICON_DEFAULT), "&Dashboard", self)
        dashboard_action.triggered.connect(lambda: self.switch_view('dashboard'))
        view_menu.addAction(dashboard_action)

        reports_action = QAction(get_icon('clipboard-list', color=ThemeColors.ICON_DEFAULT), "&Reports", self)
        reports_action.triggered.connect(lambda: self.switch_view('reports'))
        view_menu.addAction(reports_action)

        # Admin menu (admin only)
        if self.current_user and self.current_user['role'] == 'admin':
            admin_menu = menubar.addMenu("&Admin")

            users_action = QAction(get_icon('users', color=ThemeColors.ICON_DEFAULT), "&Users", self)
            users_action.triggered.connect(lambda: self.switch_view('users'))
            admin_menu.addAction(users_action)

            logs_action = QAction(get_icon('history', color=ThemeColors.ICON_DEFAULT), "System &Logs", self)
            logs_action.triggered.connect(lambda: self.switch_view('logs'))
            admin_menu.addAction(logs_action)

            settings_action = QAction(get_icon('cog', color=ThemeColors.ICON_DEFAULT), "&Settings", self)
            settings_action.triggered.connect(lambda: self.switch_view('settings'))
            admin_menu.addAction(settings_action)

            admin_menu.addSeparator()

            # Dropdown Management
            dropdown_mgmt_action = QAction(get_icon('list', color=ThemeColors.ICON_DEFAULT), "Dropdown &Management", self)
            dropdown_mgmt_action.triggered.connect(lambda: self.switch_view('dropdown_mgmt'))
            admin_menu.addAction(dropdown_mgmt_action)

            # System Settings
            system_settings_action = QAction(get_icon('sliders-h', color=ThemeColors.ICON_DEFAULT), "System Se&ttings", self)
            system_settings_action.triggered.connect(lambda: self.switch_view('system_settings'))
            admin_menu.addAction(system_settings_action)

            admin_menu.addSeparator()

            approvals_history_action = QAction(get_icon('history', color=ThemeColors.ICON_DEFAULT), "Approvals &History", self)
            approvals_history_action.triggered.connect(self.show_approvals_history)
            admin_menu.addAction(approvals_history_action)

            # Reservation Management
            reservation_mgmt_action = QAction(get_icon('database', color=ThemeColors.ICON_DEFAULT), "&Reservation Management", self)
            reservation_mgmt_action.triggered.connect(self.show_reservation_management)
            admin_menu.addAction(reservation_mgmt_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")

        help_action = QAction(get_icon('book', color=ThemeColors.ICON_DEFAULT), "&Help & Documentation", self)
        help_action.setShortcut("F1")
        help_action.triggered.connect(self.show_help)
        help_menu.addAction(help_action)

        help_menu.addSeparator()

        about_action = QAction(get_icon('info-circle', color=ThemeColors.ICON_DEFAULT), "&About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def setup_tool_bar(self):
        """Setup the toolbar."""
        self.toolbar = QToolBar("Main Toolbar")
        self.toolbar.setMovable(False)
        self.addToolBar(self.toolbar)

        # Add common actions
        if self.auth_service.has_permission('add_report'):
            add_report_action = QAction(get_icon('plus', color=ThemeColors.ICON_DEFAULT), "New Report", self)
            add_report_action.triggered.connect(self.quick_add_report)
            self.toolbar.addAction(add_report_action)

        self.toolbar.addSeparator()

        refresh_action = QAction(get_icon('refresh', color=ThemeColors.ICON_DEFAULT), "Refresh", self)
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
                self.current_user,
                auth_service=self.auth_service,
                approval_service=self.approval_service,
                report_number_service=self.report_number_service,
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
                'export': 'Export Data',
                'approvals': 'Approval Management',
                'users': 'User Management',
                'logs': 'System Logs',
                'settings': 'Settings',
                'dropdown_mgmt': 'Dropdown Management',
                'system_settings': 'System Settings'
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

    def show_approvals_history(self):
        """Show approvals history dialog (admin only)."""
        from ui.dialogs.approvals_history_dialog import ApprovalsHistoryDialog
        try:
            if not self.current_user or self.current_user.get('role') != 'admin':
                QMessageBox.warning(
                    self,
                    "Access Denied",
                    "Only administrators can view approvals history."
                )
                return

            if not self.report_service or not self.logging_service:
                QMessageBox.warning(
                    self,
                    "Not Available",
                    "Approvals history requires database access."
                )
                return

            dialog = ApprovalsHistoryDialog(
                self.report_service,
                self.logging_service,
                self
            )
            dialog.exec()
            self.logging_service.info(f"Admin {self.current_user['username']} viewed approvals history")

        except Exception as e:
            self.logging_service.error(f"Error showing approvals history: {str(e)}", exc_info=True)
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to open approvals history: {str(e)}"
            )

    def show_reservation_management(self):
        """Show reservation management dialog (admin only)."""
        from ui.dialogs.reservation_management_dialog import ReservationManagementDialog
        try:
            if not self.current_user or self.current_user.get('role') != 'admin':
                QMessageBox.warning(
                    self,
                    "Access Denied",
                    "Only administrators can access reservation management."
                )
                return

            if not self.report_number_service:
                QMessageBox.warning(
                    self,
                    "Not Available",
                    "Reservation management requires report number service."
                )
                return

            dialog = ReservationManagementDialog(
                self.report_number_service,
                self.auth_service,
                self
            )
            dialog.exec()
            self.logging_service.info(f"Admin {self.current_user['username']} opened reservation management")

        except Exception as e:
            self.logging_service.error(f"Error showing reservation management: {str(e)}", exc_info=True)
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to open reservation management: {str(e)}"
            )

    def handle_notification_clicked(self, notification):
        """
        Handle notification click.

        Args:
            notification: Notification dictionary
        """
        # Navigate to reports view if there's a related report
        related_report_id = notification.get('related_report_id')
        notification_type = notification.get('notification_type')

        if notification_type == 'approval_request' and self.current_user.get('role') == 'admin':
            # Navigate to approvals view
            self.switch_view('approvals')
        elif related_report_id:
            # Navigate to reports view
            self.switch_view('reports')

    def resizeEvent(self, event):
        """Handle window resize for responsive layout adjustments."""
        super().resizeEvent(event)
        
        # Debounce resize events to improve performance
        if self.resize_timer:
            self.resize_timer.stop()
        
        self.resize_timer = QTimer()
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self.handle_resize)
        self.resize_timer.start(100)
    
    def handle_resize(self):
        """Handle delayed resize operations with responsive sizing."""
        width = self.width()

        # Adjust sidebar width based on window size with DPI scaling
        if width < 1200:
            # Compact mode for smaller screens
            self.sidebar.setMaximumWidth(ResponsiveSize.get_scaled_size(160))
        elif width < 1600:
            # Normal mode
            self.sidebar.setMaximumWidth(ResponsiveSize.get_scaled_size(220))
        else:
            # Wide mode for larger screens
            self.sidebar.setMaximumWidth(ResponsiveSize.get_scaled_size(280))

        # Adjust header height based on window size
        header_height = ResponsiveSize.get_scaled_size(50 if width >= 1200 else 45)
        if hasattr(self, 'header'):
            self.header.setMinimumHeight(header_height)

        # Notify current view of resize if it supports it
        current_view = self.stacked_widget.currentWidget()
        if hasattr(current_view, 'handle_resize'):
            current_view.handle_resize(width, self.height())
    
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
