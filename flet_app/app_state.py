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
    intelligence_service: Any = None
    _gateway: Any = None  # RemoteGateway, set only in client mode
    host_status: Any = None  # HostStatus, set only in client mode

    # ==================== UI State ====================
    theme: str = "dark"
    current_route: str = "/login"

    # ==================== Event Listeners ====================
    _auth_listeners: List[Callable] = field(default_factory=list)
    _route_listeners: List[Callable] = field(default_factory=list)

    def initialize_services(self, db_path: str, mode: str = "local", bus_dir: str = None) -> bool:
        """
        Initialize all services with proper dependency injection.

        Args:
            db_path: Path to the SQLite database file (in client mode, this
                is the client's local copy of the replica)
            mode: "host" builds real services that write straight to db_path
                (today's behavior). "client" additionally wraps the
                write-capable services in a RemoteServiceProxy so writes go
                through the host queue while reads stay local.
            bus_dir: shared folder for the client/host command queue. Only
                used when mode == "client"; if not given, no proxying
                happens and this behaves exactly like a local single-machine
                install.

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

            # Initialize database manager. In client mode the db_path is the
            # client's local copy of the host replica: open it read-only (no
            # WAL sidecars) so the background refresher can swap the file
            # underneath us and the single-writer rule holds client-side.
            is_client = (mode == "client" and bool(bus_dir))
            self.db_manager = DatabaseManager(db_path, read_only=is_client)

            # Initialize logging service first (other services depend on it)
            log_dir = project_root / 'logs'
            self.logging_service = LoggingService(
                self.db_manager, log_dir,
                db_logging=(mode != "client" or not bus_dir))

            # Run migrations (skip on the read-only replica - the host
            # already migrated it, and this connection can't write anyway)
            if not is_client:
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
            self.dashboard_service = DashboardService(self.db_manager, self.logging_service, self.auth_service)
            self.dropdown_service = DropdownService(self.db_manager, self.logging_service, self.auth_service)
            self.validation_service = ValidationService(self.db_manager, self.logging_service)
            from services.intelligence_service import IntelligenceService
            self.intelligence_service = IntelligenceService(self.db_manager, self.logging_service)
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
            # Wire the number service so create_report enforces the reservation gate
            self.report_service.set_report_number_service(self.report_number_service)

            # Maintenance schedulers: auto-purge (R80) + weekly backup (R107).
            # Client mode reads a throwaway, read-only replica - a local
            # purge/backup would write to it (and now crash on the ro
            # handle). Only start these against a real writable DB.
            if not is_client:
                try:
                    from services.maintenance_service import MaintenanceService
                    from config import Config
                    self.maintenance_service = MaintenanceService(
                        self.db_manager, self.logging_service, self.report_service,
                        backup_dir=Config.BACKUP_PATH, settings_service=self.settings_service)
                    self.maintenance_service.start()
                except Exception as e:
                    self.logging_service.warning(f"Maintenance schedulers not started: {e}")

            if mode == "client" and bus_dir:
                from services.queue_transport import QueueTransport
                from services.remote_gateway import RemoteGateway, RemoteServiceProxy
                from services.outbox import Outbox
                from services.host_status import HostStatus
                from config import Config
                gw = RemoteGateway(QueueTransport(bus_dir), outbox=Outbox(Config.get_client_outbox_dir()))
                self._gateway = gw
                self.host_status = HostStatus(bus_dir)
                for attr in ("auth_service", "report_service", "approval_service",
                             "version_service", "report_number_service", "dropdown_service",
                             "validation_service", "settings_service"):
                    local = getattr(self, attr)
                    setattr(self, attr, RemoteServiceProxy(attr, local, gw))

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

        # Apply the user's UI language (#3 i18n)
        try:
            from i18n import set_language
            set_language(user.get('language', 'en'))
        except Exception:
            pass

        # In client mode auth_service is a proxy; set current_user on the real
        # local service so has_permission()/RBAC reads work against the replica.
        try:
            local_auth = getattr(self.auth_service, "_local", self.auth_service)
            local_auth.current_user = user
        except Exception:
            pass

        # Set user context in logging service
        if self.logging_service:
            self.logging_service.set_user_context(
                user.get('user_id'),
                user.get('username')
            )

        # A host restart (reboot, failover) invalidates every client's session
        # token, and queued writes carry that dead token — the host rejects them
        # with "Not authenticated (re-login)" and the outbox keeps them forever.
        # A fresh login is exactly when they become drainable, so drain here.
        try:
            self.drain_outbox()
        except Exception:
            pass  # never block a login on the outbox

        # Notify listeners
        self._notify_auth_listeners()

    def login_remote(self, username: str, password: str):
        """Authenticate against the host in client mode (bypasses the local
        auth_service proxy, which has no real password to check)."""
        if not self._gateway:
            return False, None, "Not in client mode (no gateway configured)"
        return self._gateway.login(username, password)

    def authenticate(self, username: str, password: str):
        """Unified login: host (client mode) or local auth_service."""
        if self._gateway:
            return self.login_remote(username, password)
        return self.auth_service.authenticate(username, password)

    def get_onboarding_status(self, username: str) -> str:
        """'pending' | 'active' | 'unknown' — read (local replica in client mode)."""
        return self.auth_service.get_onboarding_status(username)

    def complete_onboarding(self, username: str, full_name: str, password: str):
        """Two-way handshake (#1): the user self-registers name + password.
        Pre-auth write — routed to the host in client mode."""
        if self._gateway:
            return self._gateway.complete_onboarding(username, full_name, password)
        return self.auth_service.complete_onboarding(username, full_name, password)

    def pending_writes(self) -> int:
        """Outbox depth: writes queued while the host was unreachable."""
        gw = self._gateway
        if gw is not None and getattr(gw, "outbox", None) is not None:
            return len(gw.outbox.pending())
        return 0

    def drain_outbox(self):
        """Resubmit queued outbox writes to the host. Safe to call when the
        host is offline (drain no-ops/returns quickly in that case)."""
        gw = self._gateway
        if gw is not None and getattr(gw, "outbox", None) is not None:
            return gw.drain()
        return (0, 0)

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
