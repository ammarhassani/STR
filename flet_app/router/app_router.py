"""
Application Router for FIU Report Management System.
Handles navigation, route guards, and view management.
"""
import flet as ft
from typing import Dict, Callable, Optional, Any


class AppRouter:
    """
    Centralized routing with authentication and role-based guards.
    Manages navigation between views and handles access control.
    """

    # Route definitions
    ROUTES = {
        "/login": "login",
        "/setup": "setup",
        "/": "dashboard",
        "/dashboard": "dashboard",
        "/reports": "reports",
        "/export": "export",
        "/activity": "activity",
        "/approvals": "approvals",
        "/users": "users",
        "/logs": "logs",
        "/settings": "settings",
        "/dropdown-management": "dropdown_mgmt",
        "/field-management": "field_mgmt",
        "/system-settings": "system_settings",
    }

    # Routes that require admin role
    ADMIN_ROUTES = [
        "/approvals",
        "/users",
        "/logs",
        "/settings",
        "/dropdown-management",
        "/field-management",
        "/system-settings",
    ]

    # Routes that don't require authentication
    PUBLIC_ROUTES = ["/login", "/setup"]

    def __init__(self, page: ft.Page, app_state: Any):
        """
        Initialize the router.

        Args:
            page: Flet page object
            app_state: Application state object
        """
        self.page = page
        self.app_state = app_state
        self.view_builders: Dict[str, Callable] = {}
        self.current_route: str = "/login"
        self._on_route_change_callback: Optional[Callable] = None

    def register_view(self, route_name: str, builder: Callable):
        """
        Register a view builder function.

        Args:
            route_name: Name of the route (from ROUTES values)
            builder: Function that builds and returns a view/control
        """
        self.view_builders[route_name] = builder

    def register_views(self, views: Dict[str, Callable]):
        """
        Register multiple view builders at once.

        Args:
            views: Dictionary mapping route names to builder functions
        """
        self.view_builders.update(views)

    def navigate(self, route: str):
        """
        Navigate to a route with guards.

        Args:
            route: Route path to navigate to
        """
        # Authentication guard
        if route not in self.PUBLIC_ROUTES and not self.app_state.is_authenticated:
            self.page.go("/login")
            return

        # Admin guard
        if route in self.ADMIN_ROUTES:
            if not self.app_state.is_admin():
                self.show_access_denied()
                return

        # Update current route
        self.current_route = route
        self.app_state.set_route(route)

        # Navigate
        self.page.go(route)

    def handle_route_change(self, e: ft.RouteChangeEvent):
        """
        Handle route changes from Flet.

        Args:
            e: Route change event
        """
        route = e.route
        self.current_route = route

        # Apply guards
        if route not in self.PUBLIC_ROUTES and not self.app_state.is_authenticated:
            self.page.go("/login")
            return

        if route in self.ADMIN_ROUTES and not self.app_state.is_admin():
            self.show_access_denied()
            return

        # Get route name
        route_name = self.ROUTES.get(route, "dashboard")

        # Build and display view
        if route_name in self.view_builders:
            try:
                # Clear existing views
                self.page.views.clear()

                # Build new view
                view = self.view_builders[route_name]()

                # Add to page
                if isinstance(view, ft.View):
                    self.page.views.append(view)
                else:
                    # Wrap in a View if it's just a control
                    self.page.views.append(
                        ft.View(
                            route=route,
                            controls=[view],
                            padding=0,
                            spacing=0,
                        )
                    )

                self.page.update()

                # Notify callback if set
                if self._on_route_change_callback:
                    self._on_route_change_callback(route, route_name)

            except Exception as ex:
                print(f"Error building view for {route}: {ex}")
                import traceback
                traceback.print_exc()
                self.show_error(f"Error loading page: {str(ex)}")

    def handle_view_pop(self, e: ft.ViewPopEvent):
        """
        Handle view pop events (back navigation).

        Args:
            e: View pop event
        """
        if len(self.page.views) > 1:
            self.page.views.pop()
            top_view = self.page.views[-1]
            self.page.go(top_view.route)

    def set_on_route_change(self, callback: Callable[[str, str], None]):
        """
        Set callback for route changes.

        Args:
            callback: Function(route, route_name) called on route change
        """
        self._on_route_change_callback = callback

    def show_access_denied(self):
        """Show access denied dialog."""
        def close_dialog(e):
            dlg.open = False
            self.page.update()
            # Navigate back to dashboard
            self.navigate("/dashboard")

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Access Denied"),
            content=ft.Text("You don't have permission to access this page."),
            actions=[
                ft.TextButton("OK", on_click=close_dialog)
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()

    def show_error(self, message: str):
        """
        Show error dialog.

        Args:
            message: Error message to display
        """
        def close_dialog(e):
            dlg.open = False
            self.page.update()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Error"),
            content=ft.Text(message),
            actions=[
                ft.TextButton("OK", on_click=close_dialog)
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()

    def get_nav_items(self) -> list:
        """
        Get navigation items based on user role.

        Returns:
            List of navigation item dictionaries
        """
        items = [
            {"icon": ft.Icons.DASHBOARD, "label": "Dashboard", "route": "/dashboard"},
            {"icon": ft.Icons.DESCRIPTION, "label": "Reports", "route": "/reports"},
            {"icon": ft.Icons.HISTORY, "label": "Activity", "route": "/activity"},
            {"icon": ft.Icons.DOWNLOAD, "label": "Export", "route": "/export"},
        ]

        # Add admin-only items
        if self.app_state.is_admin():
            items.extend([
                {"icon": ft.Icons.CHECK_CIRCLE, "label": "Approvals", "route": "/approvals"},
                {"icon": ft.Icons.PEOPLE, "label": "Users", "route": "/users"},
                {"icon": ft.Icons.BUG_REPORT, "label": "System Logs", "route": "/logs"},
                {"icon": ft.Icons.SETTINGS, "label": "Settings", "route": "/settings"},
                {"icon": ft.Icons.LIST, "label": "Dropdowns", "route": "/dropdown-management"},
                {"icon": ft.Icons.TUNE, "label": "Fields", "route": "/field-management"},
            ])

        return items

    def get_current_route_index(self, nav_items: list) -> int:
        """
        Get the index of the current route in nav items.

        Args:
            nav_items: List of navigation items

        Returns:
            Index of current route, or 0 if not found
        """
        for i, item in enumerate(nav_items):
            if item["route"] == self.current_route:
                return i
        return 0

    def go_to_login(self):
        """Navigate to login page."""
        self.navigate("/login")

    def go_to_dashboard(self):
        """Navigate to dashboard."""
        self.navigate("/dashboard")

    def go_to_reports(self):
        """Navigate to reports."""
        self.navigate("/reports")
