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
from views.my_work_view import build_my_work_view
from views.admin_panel_view import build_admin_panel_view
from views.approval_panel_view import build_approval_panel_view
from views.log_management_view import build_log_management_view
from views.settings_view import build_settings_view
from views.dropdown_management_view import build_dropdown_management_view
from views.field_management_view import build_field_management_view
from views.dashboard_widgets_view import build_dashboard_widgets_view
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
        # Open windowed-fullscreen (maximized), not a small off-centre window
        self.page.window.width = 1400
        self.page.window.height = 900
        self.page.window.min_width = 1024
        self.page.window.min_height = 600
        self.page.window.center()
        self.page.window.maximized = True
        self.page.padding = 0
        self.page.spacing = 0
        # light-only theme background
        self.page.bgcolor = theme_manager.get_colors()["bg_primary"]

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

        # Ctrl+N - New Report (only if the role may add reports)
        elif ctrl and key.lower() == "n":
            if app_state.auth_service and app_state.auth_service.has_permission('add_report'):
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
            if Config.MODE == "client":
                from services.replica_sync import bootstrap_replica, ReplicaRefresher
                bus_dir = Config.get_bus_dir()
                local_replica = Config.get_client_replica_path()
                if not bootstrap_replica(bus_dir, local_replica, timeout=30.0):
                    self._show_error("Cannot reach the host replica on the shared folder.\n"
                                     "Make sure a host PC is running and the share is available.")
                    return False
                ok = app_state.initialize_services(local_replica, mode="client", bus_dir=bus_dir)
                if not ok:
                    return False
                # keep the local read replica fresh; drain queued writes and
                # refresh the host-down banner each time the replica updates
                # (the host republishes right after processing an outbox
                # write, so this is when a drain is most likely to succeed)
                def _on_replica_update():
                    try:
                        app_state.drain_outbox()
                    except Exception:
                        pass
                    if getattr(self, "_host_banner", None) is not None:
                        self._host_banner.refresh()
                        try:
                            self.page.update()
                        except Exception:
                            pass
                if not getattr(self, "_refresher", None):
                    self._refresher = ReplicaRefresher(
                        bus_dir, local_replica, poll=2.0,
                        on_update=_on_replica_update)
                    self._refresher.start()
                theme_manager.initialize(self.page, app_state.settings_service, app_state.auth_service)
                return True

            # local / host (unchanged)
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
            import traceback; traceback.print_exc()
            return False

    def _show_setup_wizard(self):
        """Show the setup wizard for first-time configuration."""
        def on_setup_complete(db_path: str, backup_path: str, mode: str = "local", share_path: str = None):
            """Handle setup completion."""
            Config.DATABASE_PATH = db_path
            Config.BACKUP_PATH = backup_path
            Config.MODE = mode
            Config.SHARE_PATH = share_path
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
        # Force the default/reset account to set a new password immediately.
        if user.get('must_change_password'):
            try:
                from dialogs.change_password_dialog import show_change_password_dialog
                from components.toast import show_error
                show_error(self.page, "You are using a default password — please set a new one now.")
                show_change_password_dialog(self.page, app_state)
            except Exception as e:
                app_state.logging_service.warning(f"Could not open forced password change: {e}")

    def _show_main_app(self):
        """Show the main application with navigation."""
        self.page.controls.clear()

        # Initialize content area
        self.content_area = ft.Container(
            content=build_dashboard_content(self.page, app_state, self._handle_navigate),
            expand=True,
            padding=24,
        )

        # Build the main layout
        self._build_main_layout()
        self.page.update()

    def _handle_navigate(self, route: str):
        """Handle navigation to a route."""
        self.current_route = route
        self._update_content(route)
        self._rebuild_sidebar()

    def _build_main_layout(self):
        """Build the main application layout with sidebar and content."""
        colors = theme_manager.get_colors()

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
            self._handle_navigate,
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

        # Host-down banner (client mode only; local/host installs have no
        # host_status and never show it)
        main_column_controls = []
        if app_state.host_status:
            from flet_app.components.host_banner import build_host_banner
            self._host_banner = build_host_banner(app_state)
            main_column_controls.append(self._host_banner)

        # Main content column
        main_column_controls += [
            self.header,
            ft.Container(
                content=self.content_area,
                expand=True,
                bgcolor=colors["bg_primary"],
            ),
        ]
        main_column = ft.Column(
            controls=main_column_controls,
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
            "/dashboard": lambda: build_dashboard_content(self.page, app_state, self._handle_navigate),
            "/reports": lambda: build_reports_view(self.page, app_state),
            "/my-work": lambda: build_my_work_view(self.page, app_state),
            "/activity": lambda: build_activity_view(self.page, app_state),
            "/export": lambda: build_export_view(self.page, app_state),
            "/approvals": lambda: build_approval_panel_view(self.page, app_state),
            "/users": lambda: build_admin_panel_view(self.page, app_state),
            "/logs": lambda: build_log_management_view(self.page, app_state),
            "/settings": lambda: build_settings_view(self.page, app_state),
            "/dropdown-management": lambda: build_dropdown_management_view(self.page, app_state),
            "/field-management": lambda: build_field_management_view(self.page, app_state),
            "/dashboard-widgets": lambda: build_dashboard_widgets_view(self.page, app_state),
        }

        builder = route_content.get(route, route_content["/dashboard"])
        return builder()

    def _get_page_title(self, route: str) -> str:
        """Get page title for a route."""
        titles = {
            "/dashboard": "Dashboard",
            "/reports": "Reports",
            "/my-work": "My Work",
            "/activity": "Activity Log",
            "/export": "Export",
            "/approvals": "Approvals",
            "/users": "User Management",
            "/logs": "System Logs",
            "/settings": "Settings",
            "/dropdown-management": "Dropdown Management",
            "/field-management": "Field Management",
            "/dashboard-widgets": "Dashboard Widgets",
        }
        return titles.get(route, "Dashboard")

    def _show_error(self, message: str):
        """Show error dialog."""
        from theme.colors import Colors
        colors = Colors.get_palette("light")   # app is light-only

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
    if "--host" in sys.argv:
        # Host mode: no UI. Build services against the local DB and serve
        # the command queue for clients until killed.
        from services.queue_transport import QueueTransport
        from host.host_service import HostService

        Config.load()
        app_state.initialize_services(Config.DATABASE_PATH, mode="host")
        host_services = {a: getattr(app_state, a) for a in (
            "auth_service", "settings_service", "report_service", "dashboard_service",
            "dropdown_service", "validation_service", "report_number_service",
            "activity_service", "version_service", "approval_service")}
        bus_dir = Config.get_bus_dir()
        HostService(host_services, app_state.db_manager, QueueTransport(bus_dir),
                    bus_dir, host_id=Config.ensure_host_id()).serve_forever()
        sys.exit(0)

    if "--panel" in sys.argv:
        from panel.control_panel import main as panel_main
        panel_main()
        sys.exit(0)

    # View selection. Default is the NATIVE desktop window (shortcuts work, no
    # browser refresh). On the locked-down Windows workstation the flet desktop
    # client can't be downloaded (org proxy 403s the CDN), so we ship it in the
    # repo (vendor/flet-client/) and seed it into flet's cache here. If anything
    # about desktop fails, fall back to the web-browser view (always works).
    # Force either explicitly with STR_VIEW=desktop | web.
    import os

    def _ensure_desktop_client():
        """Windows only: extract the vendored flet client into ~/.flet/bin so the
        native window launches offline (no CDN download)."""
        if not sys.platform.startswith("win"):
            return  # mac/linux download their own client (dev machines have net)
        import zipfile
        try:
            import flet_desktop.version
            ver = flet_desktop.version.version
        except Exception:
            ver = "0.28.3"
        dest = Path.home() / ".flet" / "bin" / f"flet-{ver}"
        if (dest / "flet" / "flet.exe").exists():
            return  # already seeded
        vendored = project_root / "vendor" / "flet-client" / f"flet-windows-{ver}.zip"
        if not vendored.exists():
            vendored = project_root / "vendor" / "flet-client" / "flet-windows-0.28.3.zip"
        if not vendored.exists():
            raise FileNotFoundError("vendored flet windows client not found")
        dest.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(vendored) as z:
            z.extractall(dest)

    forced = os.environ.get("STR_VIEW", "").lower()
    use_web = forced in ("web", "browser")
    if not use_web:
        try:
            _ensure_desktop_client()
        except Exception as e:
            print(f"[VIEW] desktop client unavailable ({e}); falling back to web")
            use_web = True

    if use_web:
        ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=int(os.environ.get("STR_PORT", "8550")))
    else:
        ft.app(target=main)  # native desktop window
