"""
FIU Report Management System - Main Application
Version 2.1.0 - Enhanced Stability & Error Handling
"""
import flet as ft
import sys
import traceback
import logging
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Path.home() / '.fiu_system' / 'app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('fiu_system')

try:
    from config import Config
    from database.db_manager import DatabaseManager
    from database.queue_manager import WriteQueue
    from database.init_db import initialize_database, validate_database
    from utils.permissions import has_permission
except ImportError as e:
    logger.error(f"Import error: {e}")
    # Continue - we'll handle this gracefully


class FIUApplication:
    """Main application class with enhanced error handling"""
    
    def __init__(self, page: ft.Page):
        self.page = page
        self.db_manager = None
        self.write_queue = None
        self.current_user = None
        self.content_area = ft.Container(expand=True)
        self.is_initialized = False
        
        logger.info("Initializing FIU Application v2.1.0")
        
        # Safe page configuration
        try:
            self.page.title = "FIU Report Management System v2.1.0"
            self.page.window.width = 1400
            self.page.window.height = 800
            self.page.theme_mode = ft.ThemeMode.LIGHT
            self.page.padding = 0
            self.page.fonts = {
                "default": "Arial"
            }
        except Exception as e:
            logger.error(f"Page configuration failed: {e}")
        
        # Initialize application state
        self.initialize_application()
    
    def initialize_application(self):
        """Initialize application with comprehensive error handling"""
        try:
            # Load configuration
            if not self.safe_load_config():
                return
            
            # Check configuration state
            if not Config.is_configured():
                self.show_first_time_setup()
                return
            
            # Validate paths
            is_valid, message = Config.validate_paths()
            if not is_valid:
                self.show_config_error(message)
                return
            
            # Initialize database system
            if not self.initialize_database_system():
                return
            
            # Application is ready
            self.is_initialized = True
            self.show_login_screen()
            
        except Exception as e:
            logger.error(f"Application initialization failed: {e}")
            self.show_fatal_error(f"Application failed to start: {str(e)}")
    
    def safe_load_config(self) -> bool:
        """Safely load configuration with fallbacks"""
        try:
            if not Config.load():
                logger.warning("Configuration file not found or invalid")
                return True  # Continue to first-time setup
            return True
        except Exception as e:
            logger.error(f"Config loading failed: {e}")
            self.show_error_dialog(
                "Configuration Error", 
                f"Failed to load configuration: {str(e)}"
            )
            return False
    
    def initialize_database_system(self) -> bool:
        """Initialize database with comprehensive error handling"""
        try:
            db_path = Path(Config.DATABASE_PATH)
            
            # Check if database exists
            if not db_path.exists():
                return self.handle_missing_database()
            
            # Initialize database manager
            self.db_manager = DatabaseManager(Config.DATABASE_PATH)
            self.write_queue = WriteQueue(self.db_manager)
            
            # Validate database
            is_valid, message = validate_database(Config.DATABASE_PATH)
            if not is_valid:
                return self.handle_database_validation_failed(message)
            
            logger.info("Database system initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            self.show_error_dialog(
                "Database Error",
                f"Failed to initialize database: {str(e)}"
            )
            return False
    
    def handle_missing_database(self) -> bool:
        """Handle missing database file"""
        logger.warning(f"Database file not found: {Config.DATABASE_PATH}")
        
        # Ask user if they want to create the database
        def create_database(e):
            if self.create_new_database():
                self.page.dialog.open = False
                self.page.clean()
                self.initialize_application()
            else:
                self.show_fatal_error("Failed to create database. Application cannot continue.")
        
        def exit_app(e):
            self.page.window_destroy()
        
        dialog = ft.AlertDialog(
            title=ft.Text("Database Not Found"),
            content=ft.Column([
                ft.Text(f"Database file not found at:", size=14),
                ft.Text(Config.DATABASE_PATH, size=12, color=ft.Colors.BLUE_700),
                ft.Container(height=10),
                ft.Text("Would you like to create a new database?", size=16),
            ], tight=True),
            actions=[
                ft.TextButton("Exit", on_click=exit_app),
                ft.ElevatedButton("Create Database", on_click=create_database),
            ]
        )
        
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
        return False
    
    def handle_database_validation_failed(self, error_message: str) -> bool:
        """Handle database validation failures"""
        logger.error(f"Database validation failed: {error_message}")
        
        def repair_database(e):
            if self.repair_database():
                self.page.dialog.open = False
                self.page.clean()
                self.initialize_application()
        
        def exit_app(e):
            self.page.window_destroy()
        
        dialog = ft.AlertDialog(
            title=ft.Text("Database Error"),
            content=ft.Column([
                ft.Text("Database validation failed:", size=14),
                ft.Text(error_message, size=12, color=ft.Colors.ORANGE_700),
                ft.Container(height=10),
                ft.Text("Attempt automatic repair?", size=16),
                ft.Text("Note: This may result in data loss", size=12, color=ft.Colors.RED_700),
            ], tight=True),
            actions=[
                ft.TextButton("Exit", on_click=exit_app),
                ft.ElevatedButton("Repair Database", on_click=repair_database),
            ]
        )
        
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
        return False
    
    def create_new_database(self) -> bool:
        """Create a new database with admin credentials"""
        try:
            # Create parent directories
            db_path = Path(Config.DATABASE_PATH)
            db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Initialize database
            success, message = initialize_database(Config.DATABASE_PATH)
            if not success:
                logger.error(f"Database creation failed: {message}")
                return False
            
            # Ensure backup directory exists
            Path(Config.BACKUP_PATH).mkdir(parents=True, exist_ok=True)
            
            logger.info("New database created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Database creation error: {e}")
            return False
    
    def repair_database(self) -> bool:
        """Attempt to repair corrupted database"""
        try:
            # Close existing connections
            self.db_manager = None
            self.write_queue = None
            
            # Backup existing database
            db_path = Path(Config.DATABASE_PATH)
            if db_path.exists():
                backup_path = Path(Config.BACKUP_PATH) / f"corrupted_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                db_path.rename(backup_path)
                logger.info(f"Backed up corrupted database to: {backup_path}")
            
            # Create new database
            return self.create_new_database()
            
        except Exception as e:
            logger.error(f"Database repair failed: {e}")
            return False
    
    def show_first_time_setup(self):
        """Show first-time setup wizard"""
        try:
            # Default paths
            default_db_path = str(Path.home() / "fiu_system" / "database.db")
            default_backup_path = str(Path.home() / "fiu_system" / "backups")
            
            db_path_field = ft.TextField(
                label="Database File Path",
                value=default_db_path,
                width=500,
                prefix_icon=ft.icons.STORAGE,
            )
            
            backup_path_field = ft.TextField(
                label="Backup Directory",
                value=default_backup_path,
                width=500,
                prefix_icon=ft.icons.BACKUP,
            )
            
            status_text = ft.Text("", color=ft.Colors.GREY_600, size=12)
            
            def validate_paths():
                db_path = db_path_field.value.strip()
                backup_path = backup_path_field.value.strip()
                
                if not db_path or not backup_path:
                    return False, "Both paths are required"
                
                try:
                    # Check if we can create directories
                    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
                    Path(backup_path).mkdir(parents=True, exist_ok=True)
                    return True, "Paths are valid"
                except Exception as e:
                    return False, f"Invalid path: {str(e)}"
            
            def on_path_change(e):
                is_valid, message = validate_paths()
                status_text.value = message
                status_text.color = ft.Colors.GREEN if is_valid else ft.Colors.RED
                self.page.update()
            
            def complete_setup(e):
                is_valid, message = validate_paths()
                if not is_valid:
                    self.show_error_dialog("Invalid Paths", message)
                    return
                
                # Save configuration
                Config.DATABASE_PATH = db_path_field.value.strip()
                Config.BACKUP_PATH = backup_path_field.value.strip()
                
                if not Config.save():
                    self.show_error_dialog("Setup Failed", "Failed to save configuration")
                    return
                
                # Create database
                if self.create_new_database():
                    self.show_success_message("Setup completed successfully!")
                    self.page.clean()
                    self.initialize_application()
                else:
                    self.show_error_dialog("Setup Failed", "Failed to create database")
            
            # Setup form
            setup_form = ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(ft.icons.SETTINGS, size=80, color=ft.Colors.BLUE_700),
                        ft.Text("First Time Setup", size=32, weight=ft.FontWeight.BOLD),
                        ft.Text("Configure your database and backup locations", 
                               size=16, color=ft.Colors.GREY_700),
                        ft.Container(height=30),
                        
                        ft.Card(
                            content=ft.Container(
                                content=ft.Column([
                                    ft.Text("Database Configuration", size=20, 
                                           weight=ft.FontWeight.BOLD),
                                    ft.Container(height=10),
                                    db_path_field,
                                    ft.Container(height=10),
                                    backup_path_field,
                                    ft.Container(height=10),
                                    status_text,
                                ], spacing=0),
                                padding=20,
                            ),
                            elevation=5,
                        ),
                        
                        ft.Container(height=20),
                        ft.Row([
                            ft.ElevatedButton(
                                text="Complete Setup",
                                icon=ft.icons.CHECK_CIRCLE,
                                on_click=complete_setup,
                                width=200,
                            ),
                            ft.TextButton(
                                text="Exit",
                                icon=ft.icons.EXIT_TO_APP,
                                on_click=lambda e: self.page.window_destroy(),
                            ),
                        ], alignment=ft.MainAxisAlignment.CENTER),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    scroll=ft.ScrollMode.ADAPTIVE,
                ),
                padding=40,
                alignment=ft.Alignment.center,
                expand=True,
            )
            
            # Register change listeners
            db_path_field.on_change = on_path_change
            backup_path_field.on_change = on_path_change
            
            self.page.clean()
            self.page.add(setup_form)
            self.page.update()
            
        except Exception as e:
            logger.error(f"First-time setup failed: {e}")
            self.show_fatal_error(f"Setup failed: {str(e)}")
    
    def show_login_screen(self):
        """Show login screen with enhanced validation"""
        try:
            username_field = ft.TextField(
                label="Username",
                width=350,
                autofocus=True,
                prefix_icon=ft.icons.PERSON,
                text_size=14,
            )
            
            password_field = ft.TextField(
                label="Password",
                width=350,
                password=True,
                can_reveal_password=True,
                prefix_icon=ft.icons.LOCK,
                text_size=14,
                on_submit=lambda e: attempt_login(),
            )
            
            error_text = ft.Text("", color=ft.Colors.RED_700, visible=False)
            loading_indicator = ft.ProgressRing(visible=False, width=20, height=20)
            
            def attempt_login():
                username = username_field.value.strip()
                password = password_field.value
                
                if not username or not password:
                    error_text.value = "Please enter both username and password"
                    error_text.visible = True
                    self.page.update()
                    return
                
                # Show loading
                loading_indicator.visible = True
                error_text.visible = False
                self.page.update()
                
                # Authenticate (simulate some delay for better UX)
                def login_task():
                    user = self.authenticate_user(username, password)
                    if user:
                        self.current_user = user
                        self.log_session(user['user_id'], user['username'])
                        self.page.clean()
                        self.show_main_application()
                    else:
                        error_text.value = "Invalid username or password"
                        error_text.visible = True
                        loading_indicator.visible = False
                        self.page.update()
                
                # Use timer to avoid blocking UI
                self.page.run_task(login_task)
            
            login_card = ft.Card(
                content=ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(ft.icons.SECURITY, size=80, color=ft.Colors.BLUE_700),
                            ft.Container(height=10),
                            ft.Text("FIU Report System", size=28, weight=ft.FontWeight.BOLD),
                            ft.Text("v2.1.0 - Secure Access", size=14, color=ft.Colors.GREY_700),
                            ft.Container(height=30),
                            
                            username_field,
                            ft.Container(height=15),
                            password_field,
                            ft.Container(height=10),
                            
                            ft.Row([
                                loading_indicator,
                                error_text,
                            ], alignment=ft.MainAxisAlignment.CENTER),
                            
                            ft.Container(height=20),
                            ft.ElevatedButton(
                                text="Sign In",
                                icon=ft.icons.LOGIN,
                                width=350,
                                on_click=lambda e: attempt_login(),
                            ),
                            
                            ft.Container(height=10),
                            ft.Text(
                                "Default: admin / admin123",
                                size=12,
                                color=ft.Colors.GREY_600,
                                italic=True,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=40,
                    width=500,
                ),
                elevation=10,
            )
            
            login_view = ft.Container(
                content=ft.Row([login_card], alignment=ft.MainAxisAlignment.CENTER),
                padding=20,
                alignment=ft.Alignment.center,
                expand=True,
                gradient=ft.LinearGradient(
                    begin=ft.alignment.top_left,
                    end=ft.alignment.bottom_right,
                    colors=[ft.Colors.BLUE_50, ft.Colors.WHITE],
                ),
            )
            
            self.page.clean()
            self.page.add(login_view)
            self.page.update()
            
        except Exception as e:
            logger.error(f"Login screen failed: {e}")
            self.show_fatal_error(f"Login screen error: {str(e)}")
    
    def authenticate_user(self, username: str, password: str):
        """Authenticate user with enhanced error handling"""
        try:
            if not self.db_manager:
                logger.error("Database manager not initialized")
                return None
            
            query = """
                SELECT user_id, username, password, full_name, role, is_active, last_login
                FROM users 
                WHERE username = ? AND password = ? AND is_active = 1
            """
            results = self.db_manager.execute_with_retry(query, (username, password))
            
            if results:
                user = dict(results[0])
                logger.info(f"User authenticated: {username}")
                
                # Update last login
                update_query = """
                    UPDATE users 
                    SET last_login = datetime('now'), failed_login_attempts = 0
                    WHERE user_id = ?
                """
                self.db_manager.execute_with_retry(update_query, (user['user_id'],))
                
                return user
            else:
                # Log failed attempt
                logger.warning(f"Failed login attempt for user: {username}")
                return None
                
        except Exception as e:
            logger.error(f"Authentication error for {username}: {e}")
            return None
    
    def log_session(self, user_id: int, username: str):
        """Log user session with error handling"""
        try:
            query = """
                INSERT INTO session_log (user_id, username, login_time, ip_address)
                VALUES (?, ?, datetime('now'), 'local')
            """
            self.db_manager.execute_with_retry(query, (user_id, username))
        except Exception as e:
            logger.error(f"Session logging failed: {e}")
    
    def show_main_application(self):
        """Show main application interface"""
        try:
            # Create navigation rail
            nav_rail = self.create_navigation_rail()
            
            # Header with user info
            header = ft.Container(
                content=ft.Row([
                    ft.Column([
                        ft.Text(f"Welcome, {self.current_user['full_name']}", 
                               size=20, weight=ft.FontWeight.BOLD),
                        ft.Text(f"Role: {self.current_user['role'].title()} | "
                               f"Last Login: {self.current_user.get('last_login', 'Never')}",
                               size=12, color=ft.Colors.GREY_700),
                    ], expand=True),
                    ft.IconButton(
                        icon=ft.icons.LOGOUT,
                        tooltip="Logout",
                        on_click=lambda e: self.logout(),
                    ),
                ]),
                padding=15,
                bgcolor=ft.Colors.BLUE_50,
                border_radius=ft.border_radius.only(top_left=10, top_right=10),
            )
            
            # Main content area
            main_content = ft.Column([
                header,
                ft.Divider(height=1),
                ft.Container(
                    content=self.content_area,
                    expand=True,
                    padding=0,
                ),
            ], spacing=0, expand=True)
            
            # Main layout
            main_layout = ft.Row(
                [
                    nav_rail,
                    ft.VerticalDivider(width=1),
                    main_content,
                ],
                expand=True,
            )
            
            self.page.clean()
            self.page.add(main_layout)
            
            # Load default view
            self.load_dashboard()
            
        except Exception as e:
            logger.error(f"Main application failed: {e}")
            self.show_error_dialog("Interface Error", f"Failed to load main application: {str(e)}")
    
    def create_navigation_rail(self):
        """Create navigation rail based on user permissions"""
        try:
            role = self.current_user['role']
            destinations = []
            
            # Dashboard - available to all
            destinations.append(
                ft.NavigationRailDestination(
                    icon=ft.icons.DASHBOARD_OUTLINED,
                    selected_icon=ft.icons.DASHBOARD,
                    label="Dashboard",
                )
            )
            
            # Reports - available to all
            destinations.append(
                ft.NavigationRailDestination(
                    icon=ft.icons.LIST_ALT_OUTLINED,
                    selected_icon=ft.icons.LIST_ALT,
                    label="Reports",
                )
            )
            
            # Add Report - for agents and admins
            if has_permission(role, 'add_report'):
                destinations.append(
                    ft.NavigationRailDestination(
                        icon=ft.icons.ADD_CIRCLE_OUTLINE,
                        selected_icon=ft.icons.ADD_CIRCLE,
                        label="Add Report",
                    )
                )
            
            # Admin Panel - for admins only
            if has_permission(role, 'access_admin_panel'):
                destinations.append(
                    ft.NavigationRailDestination(
                        icon=ft.icons.ADMIN_PANEL_SETTINGS_OUTLINED,
                        selected_icon=ft.icons.ADMIN_PANEL_SETTINGS,
                        label="Admin",
                    )
                )
            
            # Export - for all roles
            if has_permission(role, 'export'):
                destinations.append(
                    ft.NavigationRailDestination(
                        icon=ft.icons.DOWNLOAD_OUTLINED,
                        selected_icon=ft.icons.DOWNLOAD,
                        label="Export",
                    )
                )
            
            rail = ft.NavigationRail(
                selected_index=0,
                label_type=ft.NavigationRailLabelType.ALL,
                min_width=100,
                min_extended_width=200,
                destinations=destinations,
                on_change=self.handle_navigation,
            )
            
            return rail
            
        except Exception as e:
            logger.error(f"Navigation creation failed: {e}")
            # Return basic navigation as fallback
            return ft.NavigationRail(
                selected_index=0,
                destinations=[
                    ft.NavigationRailDestination(icon=ft.icons.DASHBOARD, label="Dashboard"),
                ],
                on_change=self.handle_navigation,
            )
    
    def handle_navigation(self, e):
        """Handle navigation events"""
        try:
            index = e.control.selected_index
            navigation_map = {
                0: self.load_dashboard,
                1: self.load_reports_list,
                2: self.load_add_report,
                3: self.load_admin_panel,
                4: self.load_export_view,
            }
            
            if index in navigation_map:
                navigation_map[index]()
            else:
                logger.warning(f"Invalid navigation index: {index}")
                
        except Exception as ex:
            logger.error(f"Navigation failed: {ex}")
            self.show_error_dialog("Navigation Error", f"Failed to load view: {str(ex)}")
    
    def load_dashboard(self):
        """Load dashboard view"""
        try:
            # Simple dashboard with basic widgets
            welcome_card = ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("Dashboard", size=24, weight=ft.FontWeight.BOLD),
                        ft.Divider(),
                        ft.Text(f"Welcome back, {self.current_user['full_name']}!", size=16),
                        ft.Text(f"System Status: Operational", size=14, color=ft.Colors.GREEN_700),
                        ft.Container(height=10),
                        ft.Text("Quick Actions:", size=16, weight=ft.FontWeight.W_500),
                        ft.Row([
                            ft.FilledButton("View Reports", on_click=lambda e: self.load_reports_list()),
                            ft.OutlinedButton("Add Report", on_click=lambda e: self.load_add_report()),
                        ]),
                    ]),
                    padding=20,
                ),
                elevation=3,
            )
            
            dashboard_content = ft.Column(
                [
                    welcome_card,
                    ft.Container(height=20),
                    ft.Text("System Overview", size=20, weight=ft.FontWeight.BOLD),
                    ft.GridView(
                        [
                            ft.Container(
                                content=ft.Column([
                                    ft.Icon(ft.icons.STORAGE, size=40, color=ft.Colors.BLUE_700),
                                    ft.Text("Database", size=16),
                                    ft.Text("Operational", size=14, color=ft.Colors.GREEN_700),
                                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                                padding=20,
                                border_radius=10,
                                bgcolor=ft.Colors.BLUE_50,
                            ),
                            ft.Container(
                                content=ft.Column([
                                    ft.Icon(ft.icons.SECURITY, size=40, color=ft.Colors.GREEN_700),
                                    ft.Text("Security", size=16),
                                    ft.Text("Active", size=14, color=ft.Colors.GREEN_700),
                                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                                padding=20,
                                border_radius=10,
                                bgcolor=ft.Colors.GREEN_50,
                            ),
                        ],
                        runs_count=2,
                        max_extent=200,
                        spacing=10,
                        run_spacing=10,
                    ),
                ],
                scroll=ft.ScrollMode.ADAPTIVE,
            )
            
            self.content_area.content = ft.Container(
                content=dashboard_content,
                padding=30,
                expand=True,
            )
            self.page.update()
            
        except Exception as e:
            logger.error(f"Dashboard load failed: {e}")
            self.show_error_dialog("Dashboard Error", f"Failed to load dashboard: {str(e)}")
    
    def load_reports_list(self):
        """Load reports list view"""
        try:
            # Simple reports list
            reports_content = ft.Column([
                ft.Text("Reports", size=24, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.Text("Reports functionality will be implemented here.", size=16),
                ft.Container(height=20),
                ft.FilledButton(
                    "View Sample Report", 
                    on_click=lambda e: self.show_info_dialog(
                        "Sample Report", 
                        "This is a sample report dialog. Full implementation coming soon."
                    )
                ),
            ])
            
            self.content_area.content = ft.Container(
                content=reports_content,
                padding=30,
                expand=True,
            )
            self.page.update()
            
        except Exception as e:
            logger.error(f"Reports list load failed: {e}")
            self.show_error_dialog("Reports Error", f"Failed to load reports: {str(e)}")
    
    def load_add_report(self):
        """Load add report form"""
        self.show_info_dialog(
            "Add Report", 
            "Report creation form will be implemented here with full validation."
        )
    
    def load_admin_panel(self):
        """Load admin panel"""
        self.show_info_dialog(
            "Admin Panel", 
            "Administrative functions for user management and system configuration."
        )
    
    def load_export_view(self):
        """Load export view"""
        self.show_info_dialog(
            "Export Data", 
            "Data export functionality with CSV and Excel formats."
        )
    
    def logout(self):
        """Logout user and return to login screen"""
        try:
            self.current_user = None
            self.db_manager = None
            self.write_queue = None
            self.page.clean()
            self.show_login_screen()
        except Exception as e:
            logger.error(f"Logout failed: {e}")
            self.page.restart()  # Force restart if logout fails
    
    # UI Helper Methods
    def show_error_dialog(self, title: str, message: str):
        """Show error dialog"""
        try:
            dialog = ft.AlertDialog(
                title=ft.Text(title),
                content=ft.Text(message),
                actions=[ft.TextButton("OK", on_click=lambda e: self.close_dialog())],
            )
            self.page.dialog = dialog
            dialog.open = True
            self.page.update()
        except Exception as e:
            logger.error(f"Error dialog failed: {e}")
    
    def show_info_dialog(self, title: str, message: str):
        """Show info dialog"""
        try:
            dialog = ft.AlertDialog(
                title=ft.Text(title),
                content=ft.Text(message),
                actions=[ft.TextButton("OK", on_click=lambda e: self.close_dialog())],
            )
            self.page.dialog = dialog
            dialog.open = True
            self.page.update()
        except Exception as e:
            logger.error(f"Info dialog failed: {e}")
    
    def show_success_message(self, message: str):
        """Show success snackbar"""
        try:
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(message),
                bgcolor=ft.Colors.GREEN_700,
            )
            self.page.snack_bar.open = True
            self.page.update()
        except Exception as e:
            logger.error(f"Success message failed: {e}")
    
    def show_config_error(self, message: str):
        """Show configuration error screen"""
        error_view = ft.Container(
            content=ft.Column([
                ft.Icon(ft.icons.ERROR_OUTLINE, size=64, color=ft.Colors.ORANGE_700),
                ft.Text("Configuration Error", size=24, weight=ft.FontWeight.BOLD),
                ft.Text(message, size=16, text_align=ft.TextAlign.CENTER),
                ft.Container(height=20),
                ft.Row([
                    ft.ElevatedButton(
                        "Reconfigure", 
                        icon=ft.icons.SETTINGS,
                        on_click=lambda e: self.show_first_time_setup()
                    ),
                    ft.TextButton(
                        "Exit", 
                        icon=ft.icons.EXIT_TO_APP,
                        on_click=lambda e: self.page.window_destroy()
                    ),
                ], alignment=ft.MainAxisAlignment.CENTER),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=40,
            alignment=ft.Alignment.center,
            expand=True,
        )
        self.page.clean()
        self.page.add(error_view)
        self.page.update()
    
    def show_fatal_error(self, message: str):
        """Show fatal error screen"""
        error_view = ft.Container(
            content=ft.Column([
                ft.Icon(ft.icons.ERROR, size=80, color=ft.Colors.RED_700),
                ft.Text("Fatal Error", size=28, weight=ft.FontWeight.BOLD),
                ft.Text(message, size=16, text_align=ft.TextAlign.CENTER),
                ft.Container(height=10),
                ft.Text("Please check the application logs for details.", 
                       size=14, color=ft.Colors.GREY_700),
                ft.Container(height=30),
                ft.Row([
                    ft.ElevatedButton(
                        "Restart Application", 
                        icon=ft.icons.REFRESH,
                        on_click=lambda e: self.page.restart()
                    ),
                    ft.TextButton(
                        "Exit", 
                        icon=ft.icons.EXIT_TO_APP,
                        on_click=lambda e: self.page.window_destroy()
                    ),
                ], alignment=ft.MainAxisAlignment.CENTER),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=40,
            alignment=ft.Alignment.center,
            expand=True,
        )
        self.page.clean()
        self.page.add(error_view)
        self.page.update()
    
    def close_dialog(self):
        """Close current dialog"""
        try:
            if self.page.dialog:
                self.page.dialog.open = False
                self.page.update()
        except Exception as e:
            logger.error(f"Dialog close failed: {e}")


def main(page: ft.Page):
    """Application entry point with global error handling"""
    try:
        # Set window properties
        page.window.center()
        page.window.min_width = 1000
        page.window.min_height = 600
        
        # Initialize application
        FIUApplication(page)
        
    except Exception as e:
        # Ultimate fallback - show basic error
        logger.critical(f"Fatal application error: {e}")
        traceback.print_exc()
        
        page.clean()
        page.add(
            ft.Container(
                content=ft.Column([
                    ft.Text("FIU System - Critical Error", size=24, weight=ft.FontWeight.BOLD),
                    ft.Text(str(e), size=14),
                    ft.Container(height=20),
                    ft.ElevatedButton("Restart", on_click=lambda e: page.restart()),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                alignment=ft.Alignment.center,
                expand=True,
                padding=40
            )
        )
        page.update()


if __name__ == "__main__":
    # Launch application
    ft.app(
        target=main,
        view=ft.AppView.FLET_APP,
        assets_dir="assets"
    )