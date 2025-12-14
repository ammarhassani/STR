"""
FIU Report Management System - Flet Application Entry Point
Modern Flet-based application with light/dark theming.

Version: 2.0.0
Technology: Python 3.9+ | Flet | SQLite3 | Plotly
"""
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import flet as ft

# Import configuration
from config import Config

# Import app state
from app_state import app_state

# Import theme
from theme.theme_manager import theme_manager

# Import router
from router.app_router import AppRouter

# Import views
from views.login_view import LoginView
from views.dashboard_view import build_dashboard_content
from views.reports_view import build_reports_view
from views.admin_panel_view import build_admin_panel_view
from views.approval_panel_view import build_approval_panel_view
from views.log_management_view import build_log_management_view
from views.settings_view import build_settings_view
from views.dropdown_management_view import build_dropdown_management_view
from views.field_management_view import build_field_management_view
from views.export_view import build_export_view
from views.activity_view import build_activity_view

# Import components
from components.sidebar import create_sidebar
from components.header import create_header
from components.toast import Toast

# Import dialogs
from dialogs.report_dialog import show_report_dialog
from dialogs.user_profile_dialog import show_user_profile_dialog
from dialogs.help_dialog import show_help_dialog
from dialogs.backup_restore_dialog import show_backup_restore_dialog
from dialogs.reservation_dialog import show_reservation_dialog

# Import setup wizard
from views.setup_wizard_view import build_setup_wizard


class FletApp:
    """
    Main Flet application class.
    Handles initialization, navigation, and view management.
    """

    def __init__(self, page: ft.Page):
        """Initialize the application."""
        self.page = page
        self.router = None
        self.toast = Toast(page)
        self.current_route = "/login"
        self.sidebar = None
        self.header = None
        self.content_area = None

        # Configure page
        self._configure_page()

        # Load configuration
        Config.load()

        # Initialize theme
        theme_manager.initialize(page)

        # Start the application flow
        self._start()

    def _configure_page(self):
        """Configure the Flet page."""
        self.page.title = "FIU Report Management System"
        self.page.window.width = 1400
        self.page.window.height = 900
        self.page.window.min_width = 1024
        self.page.window.min_height = 600
        self.page.padding = 0
        self.page.spacing = 0
        self.page.bgcolor = "#0d1117"

        # Setup keyboard shortcuts
        self.page.on_keyboard_event = self._handle_keyboard_event

    def _handle_keyboard_event(self, e: ft.KeyboardEvent):
        """Handle keyboard shortcuts."""
        # Only process when logged in (main app showing)
        if not app_state.auth_service or not app_state.auth_service.get_current_user():
            return

        key = e.key
        ctrl = e.ctrl
        shift = e.shift

        # F1 - Help
        if key == "F1":
            show_help_dialog(self.page, app_state)

        # F5 - Refresh
        elif key == "F5":
            self._update_content(self.current_route)

        # Ctrl+N - New Report
        elif ctrl and key.lower() == "n":
            current_user = app_state.auth_service.get_current_user()
            if current_user and current_user.get('role') in ['admin', 'creator']:
                show_report_dialog(self.page, app_state, on_save=lambda: self._update_content(self.current_route))

        # Ctrl+B - Backup/Restore (Admin only)
        elif ctrl and key.lower() == "b":
            current_user = app_state.auth_service.get_current_user()
            if current_user and current_user.get('role') == 'admin':
                show_backup_restore_dialog(self.page, app_state)

        # Ctrl+R - Reservation Management (Admin only)
        elif ctrl and key.lower() == "r":
            current_user = app_state.auth_service.get_current_user()
            if current_user and current_user.get('role') == 'admin':
                show_reservation_dialog(self.page, app_state)

        # Ctrl+P - User Profile
        elif ctrl and key.lower() == "p":
            show_user_profile_dialog(self.page, app_state)

        # Escape - Close any open dialogs
        elif key == "Escape":
            # Close any open overlay dialogs
            for overlay in self.page.overlay[:]:
                if isinstance(overlay, ft.AlertDialog) and overlay.open:
                    overlay.open = False
            self.page.update()

    def _start(self):
        """Start the application flow."""
        # Check if system is configured
        if not Config.is_configured():
            # First run - show setup wizard
            self._show_setup_wizard()
        else:
            # Initialize services
            if self._initialize_services():
                # Show login
                self._show_login()
            else:
                self._show_error("Failed to initialize application. Please check the configuration.")

    def _initialize_services(self) -> bool:
        """Initialize application services."""
        try:
            db_path = Config.DATABASE_PATH
            if not db_path:
                return False

            success = app_state.initialize_services(db_path)
            if success:
                # Initialize theme with services
                theme_manager.initialize(
                    self.page,
                    app_state.settings_service,
                    app_state.auth_service
                )
            return success

        except Exception as e:
            print(f"Error initializing services: {e}")
            return False

    def _show_setup_wizard(self):
        """Show the setup wizard for first-time configuration."""
        def on_setup_complete(db_path: str, backup_path: str):
            """Handle setup completion."""
            Config.DATABASE_PATH = db_path
            Config.BACKUP_PATH = backup_path
            Config.save()

            if self._initialize_services():
                self._show_login()
            else:
                self._show_error("Failed to initialize after setup.")

        # Use the full setup wizard view
        setup_content = build_setup_wizard(self.page, on_setup_complete)

        self.page.controls.clear()
        self.page.add(setup_content)
        self.page.update()

    def _show_login(self):
        """Show the login view."""
        self.page.controls.clear()

        login_view = LoginView(
            self.page,
            app_state,
            self._on_login_success
        )

        self.page.add(login_view.build().controls[0])
        self.page.update()

    def _on_login_success(self, user: dict):
        """Handle successful login."""
        app_state.logging_service.info(f"User logged in: {user['username']}")
        self._show_main_app()

    def _show_main_app(self):
        """Show the main application with navigation."""
        self.page.controls.clear()

        # Initialize content area
        self.content_area = ft.Container(
            content=build_dashboard_content(self.page, app_state),
            expand=True,
            padding=24,
        )

        # Build the main layout
        self._build_main_layout()
        self.page.update()

    def _build_main_layout(self):
        """Build the main application layout with sidebar and content."""
        colors = theme_manager.get_colors()

        # Navigation handler
        def handle_navigate(route: str):
            self.current_route = route
            self._update_content(route)
            self._rebuild_sidebar()

        # Logout handler
        def handle_logout():
            app_state.logout()
            self._show_login()

        # New Report handler
        def handle_new_report():
            show_report_dialog(self.page, app_state, on_save=lambda: self._update_content(self.current_route))

        # Refresh handler
        def handle_refresh():
            self._update_content(self.current_route)

        # Help handler
        def handle_help():
            show_help_dialog(self.page, app_state)

        # Profile handler
        def handle_profile():
            show_user_profile_dialog(self.page, app_state)

        # Backup handler (Admin only)
        def handle_backup():
            show_backup_restore_dialog(self.page, app_state)

        # Reservations handler (Admin only)
        def handle_reservations():
            show_reservation_dialog(self.page, app_state)

        # Create sidebar
        self.sidebar = create_sidebar(
            app_state,
            handle_navigate,
            self.current_route
        )

        # Create header
        self.header = create_header(
            self.page,
            app_state,
            self._get_page_title(self.current_route),
            on_logout=handle_logout,
            on_profile=handle_profile,
            on_new_report=handle_new_report,
            on_refresh=handle_refresh,
            on_help=handle_help,
            on_backup=handle_backup,
            on_reservations=handle_reservations,
        )

        # Main content column
        main_column = ft.Column(
            controls=[
                self.header,
                ft.Container(
                    content=self.content_area,
                    expand=True,
                    bgcolor=colors["bg_primary"],
                ),
            ],
            spacing=0,
            expand=True,
        )

        # Full layout
        main_row = ft.Row(
            controls=[
                self.sidebar,
                main_column,
            ],
            spacing=0,
            expand=True,
        )

        self.page.add(main_row)

    def _rebuild_sidebar(self):
        """Rebuild sidebar with updated route."""
        # This will be called when navigation changes
        pass

    def _update_content(self, route: str):
        """Update the content area based on route."""
        # Get content for route
        content = self._get_content_for_route(route)

        # Update content area
        self.content_area.content = content

        # Rebuild layout (this will recreate header with proper callbacks)
        self.page.controls.clear()
        self._build_main_layout()
        self.page.update()

    def _get_content_for_route(self, route: str) -> ft.Control:
        """Get content control for a route."""
        route_content = {
            "/dashboard": lambda: build_dashboard_content(self.page, app_state),
            "/reports": lambda: build_reports_view(self.page, app_state),
            "/activity": lambda: build_activity_view(self.page, app_state),
            "/export": lambda: build_export_view(self.page, app_state),
            "/approvals": lambda: build_approval_panel_view(self.page, app_state),
            "/users": lambda: build_admin_panel_view(self.page, app_state),
            "/logs": lambda: build_log_management_view(self.page, app_state),
            "/settings": lambda: build_settings_view(self.page, app_state),
            "/dropdown-management": lambda: build_dropdown_management_view(self.page, app_state),
            "/field-management": lambda: build_field_management_view(self.page, app_state),
        }

        builder = route_content.get(route, route_content["/dashboard"])
        return builder()

    def _get_page_title(self, route: str) -> str:
        """Get page title for a route."""
        titles = {
            "/dashboard": "Dashboard",
            "/reports": "Reports",
            "/activity": "Activity Log",
            "/export": "Export",
            "/approvals": "Approvals",
            "/users": "User Management",
            "/logs": "System Logs",
            "/settings": "Settings",
            "/dropdown-management": "Dropdown Management",
            "/field-management": "Field Management",
        }
        return titles.get(route, "Dashboard")

    def _show_error(self, message: str):
        """Show error dialog."""
        from theme.colors import Colors
        colors = Colors.DARK

        error_content = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Icon(ft.Icons.ERROR, size=64, color=colors["danger"]),
                    ft.Container(height=16),
                    ft.Text(
                        "Error",
                        size=24,
                        weight=ft.FontWeight.BOLD,
                        color=colors["text_primary"],
                    ),
                    ft.Container(height=8),
                    ft.Text(
                        message,
                        size=14,
                        color=colors["text_secondary"],
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Container(height=24),
                    ft.ElevatedButton(
                        "Retry",
                        on_click=lambda e: self._start(),
                        style=ft.ButtonStyle(
                            bgcolor=colors["primary"],
                            color=ft.Colors.WHITE,
                        ),
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            expand=True,
            alignment=ft.alignment.center,
            bgcolor=colors["bg_primary"],
        )

        self.page.controls.clear()
        self.page.add(error_content)
        self.page.update()


def main(page: ft.Page):
    """Main entry point for Flet application."""
    FletApp(page)


if __name__ == "__main__":
    ft.app(target=main)
