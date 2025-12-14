"""
Application State Management for FIU Report Management System.
Handles global state, service initialization, and dependency injection.
"""
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Callable

# Add parent directory to path for imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


@dataclass
class AppState:
    """
    Global application state container.
    Manages authentication state, services, and UI state.
    """

    # ==================== Authentication State ====================
    is_authenticated: bool = False
    current_user: Optional[Dict[str, Any]] = None
    current_session_id: Optional[int] = None

    # ==================== Services ====================
    db_manager: Any = None
    logging_service: Any = None
    auth_service: Any = None
    report_service: Any = None
    dashboard_service: Any = None
    approval_service: Any = None
    version_service: Any = None
    dropdown_service: Any = None
    validation_service: Any = None
    settings_service: Any = None
    report_number_service: Any = None
    activity_service: Any = None

    # ==================== UI State ====================
    theme: str = "dark"
    current_route: str = "/login"

    # ==================== Event Listeners ====================
    _auth_listeners: List[Callable] = field(default_factory=list)
    _route_listeners: List[Callable] = field(default_factory=list)

    def initialize_services(self, db_path: str) -> bool:
        """
        Initialize all services with proper dependency injection.

        Args:
            db_path: Path to the SQLite database file

        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            # Import services from parent directory
            from database.db_manager import DatabaseManager
            from database.init_db import validate_database
            from database.migrations import migrate_database
            from services.logging_service import LoggingService
            from services.auth_service import AuthService
            from services.report_service import ReportService
            from services.dashboard_service import DashboardService
            from services.approval_service import ApprovalService
            from services.version_service import VersionService
            from services.dropdown_service import DropdownService
            from services.validation_service import ValidationService
            from services.settings_service import SettingsService
            from services.report_number_service import ReportNumberService
            from services.activity_service import ActivityService

            # Validate database
            is_valid, message = validate_database(db_path)
            if not is_valid:
                print(f"Database validation failed: {message}")
                return False

            # Initialize database manager
            self.db_manager = DatabaseManager(db_path)

            # Initialize logging service first (other services depend on it)
            log_dir = project_root / 'logs'
            self.logging_service = LoggingService(self.db_manager, log_dir)

            # Run migrations
            success, migration_msg = migrate_database(db_path)
            if not success:
                self.logging_service.warning(f"Migration warning: {migration_msg}")
            elif "No migrations needed" not in migration_msg:
                self.logging_service.info(f"Database migration: {migration_msg}")

            self.logging_service.info("=" * 60)
            self.logging_service.info("FIU Report Management System Starting (Flet Edition)")
            self.logging_service.info("Version 2.0.0")
            self.logging_service.info("=" * 60)

            # Initialize core services
            self.auth_service = AuthService(self.db_manager, self.logging_service)
            self.settings_service = SettingsService(self.db_manager, self.auth_service)
            self.report_service = ReportService(
                self.db_manager, self.logging_service, self.auth_service
            )
            self.dashboard_service = DashboardService(self.db_manager, self.logging_service)
            self.dropdown_service = DropdownService(self.db_manager, self.logging_service)
            self.validation_service = ValidationService(self.db_manager, self.logging_service)
            self.report_number_service = ReportNumberService(
                self.db_manager, self.logging_service
            )

            # Initialize activity service (GitHub-style changelog)
            self.activity_service = ActivityService(
                self.db_manager,
                self.logging_service,
                self.auth_service
            )

            # Initialize services with complex dependencies
            self.version_service = VersionService(
                self.db_manager,
                self.logging_service,
                self.auth_service,
                self.report_service,
                self.activity_service
            )
            self.approval_service = ApprovalService(
                self.db_manager,
                self.logging_service,
                self.auth_service,
                self.version_service,
                self.report_service,
                self.activity_service
            )

            # Wire up activity service to other services for late binding
            self.report_service.set_activity_service(self.activity_service)
            self.version_service.set_activity_service(self.activity_service)

            self.logging_service.info("All services initialized successfully")
            return True

        except Exception as e:
            error_msg = f"Service initialization error: {str(e)}"
            print(error_msg)
            import traceback
            traceback.print_exc()
            if self.logging_service:
                self.logging_service.error(error_msg, exc_info=True)
            return False

    def login(self, user: Dict[str, Any], session_id: Optional[int] = None):
        """
        Set authenticated state after successful login.

        Args:
            user: User dictionary with user information
            session_id: Optional session ID
        """
        self.is_authenticated = True
        self.current_user = user
        self.current_session_id = session_id

        # Set user context in logging service
        if self.logging_service:
            self.logging_service.set_user_context(
                user.get('user_id'),
                user.get('username')
            )

        # Notify listeners
        self._notify_auth_listeners()

    def logout(self):
        """Clear authenticated state and perform cleanup."""
        if self.auth_service and self.is_authenticated:
            self.auth_service.logout()

        # Clear logging context
        if self.logging_service:
            self.logging_service.clear_user_context()

        self.is_authenticated = False
        self.current_user = None
        self.current_session_id = None

        # Notify listeners
        self._notify_auth_listeners()

    def is_admin(self) -> bool:
        """Check if current user is an admin."""
        if not self.current_user:
            return False
        return self.current_user.get('role') == 'admin'

    def has_permission(self, permission: str, resource_owner: str = None) -> bool:
        """
        Check if current user has a specific permission.

        Args:
            permission: Permission name to check
            resource_owner: Optional resource owner username

        Returns:
            bool: True if user has permission
        """
        if not self.auth_service:
            return False
        return self.auth_service.has_permission(permission, resource_owner)

    def get_user_display_name(self) -> str:
        """Get display name for current user."""
        if not self.current_user:
            return "Guest"
        return self.current_user.get('full_name', self.current_user.get('username', 'User'))

    def get_user_role(self) -> str:
        """Get role of current user."""
        if not self.current_user:
            return ""
        return self.current_user.get('role', '')

    # ==================== Event Handling ====================

    def add_auth_listener(self, callback: Callable):
        """Add listener for authentication state changes."""
        if callback not in self._auth_listeners:
            self._auth_listeners.append(callback)

    def remove_auth_listener(self, callback: Callable):
        """Remove authentication state listener."""
        if callback in self._auth_listeners:
            self._auth_listeners.remove(callback)

    def _notify_auth_listeners(self):
        """Notify all authentication listeners."""
        for callback in self._auth_listeners:
            try:
                callback(self.is_authenticated, self.current_user)
            except Exception as e:
                print(f"Error notifying auth listener: {e}")

    def add_route_listener(self, callback: Callable):
        """Add listener for route changes."""
        if callback not in self._route_listeners:
            self._route_listeners.append(callback)

    def remove_route_listener(self, callback: Callable):
        """Remove route change listener."""
        if callback in self._route_listeners:
            self._route_listeners.remove(callback)

    def set_route(self, route: str):
        """Set current route and notify listeners."""
        self.current_route = route
        for callback in self._route_listeners:
            try:
                callback(route)
            except Exception as e:
                print(f"Error notifying route listener: {e}")


# Global application state instance
app_state = AppState()
