"""
FIU Report Management System - Main Application
Version 2.1.0 - Complete Rewrite with Enhanced Workflow
"""
import flet as ft
import sys
import logging
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Ensure log directory exists
log_dir = Path.home() / '.fiu_system'
log_dir.mkdir(parents=True, exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / 'app.log'),
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
    logger.info("All modules imported successfully")
except ImportError as e:
    logger.error(f"Import error: {e}")
    logger.error("Please ensure all required files are present")


class FIUApplication:
    """Main application class"""
    
    def __init__(self, page: ft.Page):
        self.page = page
        self.db_manager = None
        self.write_queue = None
        self.current_user = None
        self.setup_step = 0
        self.temp_db_path = None
        self.temp_backup_path = None
        self.current_dialog = None
        
        logger.info("=== FIU Application Starting ===")
        
        # Configure page
        try:
            self.page.title = "FIU Report Management System"
            self.page.window_width = 1400
            self.page.window_height = 800
            self.page.window_min_width = 1000
            self.page.window_min_height = 600
            self.page.theme_mode = ft.ThemeMode.LIGHT
            self.page.padding = 0
            self.page.bgcolor = ft.Colors.BLUE_GREY_50
            logger.info("Page configured successfully")
        except Exception as e:
            logger.error(f"Page configuration error: {e}")
        
        # Start application flow
        self.start_application()
    
    def start_application(self):
        """Start application with proper workflow"""
        try:
            logger.info("Starting application workflow")
            
            # Try to load existing configuration
            if Config.load():
                logger.info("Configuration loaded successfully")
                
                # Check if configuration is complete
                if Config.is_configured():
                    logger.info("Configuration is complete")
                    
                    # Validate paths
                    is_valid, message = Config.validate_paths()
                    if is_valid:
                        logger.info("Paths validated successfully")
                        
                        # Initialize database
                        if self.init_database():
                            logger.info("Database initialized successfully")
                            # Go directly to login
                            self.show_login_screen()
                            return
                        else:
                            logger.warning("Database initialization failed, showing setup")
                    else:
                        logger.warning(f"Path validation failed: {message}")
            
            # If we get here, show welcome screen
            logger.info("Showing welcome screen")
            self.show_welcome_screen()
            
        except Exception as e:
            logger.error(f"Application start error: {e}")
            self.show_error_screen("Application failed to start", str(e))
    
    def show_welcome_screen(self):
        """Step 1: Welcome Screen"""
        logger.info("=== Showing Welcome Screen ===")
        
        def start_setup(e):
            logger.info("User clicked Start Setup")
            self.show_setup_wizard_step1()
        
        welcome_view = ft.Container(
            content=ft.Column(
                [
                    ft.Icon(ft.Icons.SECURITY, size=100, color=ft.Colors.BLUE_700),
                    ft.Container(height=20),
                    ft.Text(
                        "FIU Report Management System",
                        size=36,
                        weight=ft.FontWeight.BOLD,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Container(height=10),
                    ft.Text(
                        "Financial Intelligence Unit",
                        size=20,
                        color=ft.Colors.GREY_700,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        "Enterprise Report Management Solution",
                        size=16,
                        color=ft.Colors.GREY_600,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Container(height=40),
                    ft.ElevatedButton(
                        text="Start Setup",
                        icon=ft.Icons.ARROW_FORWARD,
                        on_click=start_setup,
                        height=50,
                        width=200,
                        style=ft.ButtonStyle(
                            text_style=ft.TextStyle(size=18, weight=ft.FontWeight.BOLD)
                        ),
                    ),
                    ft.Container(height=20),
                    ft.Text(
                        "Version 2.1.0",
                        size=12,
                        color=ft.Colors.GREY_500,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            expand=True,
            alignment=ft.alignment.center,
            gradient=ft.LinearGradient(
                begin=ft.alignment.top_left,
                end=ft.alignment.bottom_right,
                colors=[ft.Colors.BLUE_50, ft.Colors.WHITE],
            ),
        )
        
        self.page.clean()
        self.page.add(welcome_view)
        self.page.update()
    
    def show_setup_wizard_step1(self):
        """Step 2: Setup Wizard - Choose Paths"""
        logger.info("=== Setup Wizard Step 1: Choose Paths ===")
        
        # Default paths
        default_db_dir = str(Path.home() / "FIU_System")
        default_db_path = str(Path(default_db_dir) / "database" / "fiu_reports.db")
        default_backup_path = str(Path(default_db_dir) / "backups")
        
        db_path_field = ft.TextField(
            label="Database File Path",
            value=default_db_path,
            hint_text="Full path to database file",
            prefix_icon=ft.Icons.STORAGE,
            expand=True,
        )
        
        backup_path_field = ft.TextField(
            label="Backup Directory",
            value=default_backup_path,
            hint_text="Directory for backup files",
            prefix_icon=ft.Icons.BACKUP,
            expand=True,
        )
        
        status_text = ft.Text("", size=12)
        
        def validate_and_continue(e):
            db_path = db_path_field.value.strip()
            backup_path = backup_path_field.value.strip()
            
            if not db_path or not backup_path:
                status_text.value = "⚠ Both paths are required"
                status_text.color = ft.Colors.RED_700
                self.page.update()
                return
            
            # Store paths temporarily
            self.temp_db_path = db_path
            self.temp_backup_path = backup_path
            
            logger.info(f"Paths selected - DB: {db_path}, Backup: {backup_path}")

            # Check if database FILE exists (not just the directory)
            db_file = Path(db_path)
            if db_file.is_file():
                logger.info("Database file exists, asking user")
                self.show_database_found_dialog()
            else:
                logger.info("Database file doesn't exist, prompting for admin credentials")
                self.show_admin_credentials_prompt()
        
        def go_back(e):
            self.show_welcome_screen()
        
        setup_view = ft.Container(
            content=ft.Column(
                [
                    # Header
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.IconButton(
                                    icon=ft.Icons.ARROW_BACK,
                                    on_click=go_back,
                                    tooltip="Back",
                                ),
                                ft.Text(
                                    "Setup Wizard - Step 1 of 2",
                                    size=24,
                                    weight=ft.FontWeight.BOLD,
                                ),
                            ],
                        ),
                        padding=20,
                    ),
                    
                    ft.Divider(height=1),
                    
                    # Content
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Icon(ft.Icons.FOLDER_SPECIAL, size=60, color=ft.Colors.BLUE_700),
                                ft.Text(
                                    "Choose Database and Backup Locations",
                                    size=20,
                                    weight=ft.FontWeight.BOLD,
                                    text_align=ft.TextAlign.CENTER,
                                ),
                                ft.Text(
                                    "Select where to store your database and backups",
                                    size=14,
                                    color=ft.Colors.GREY_700,
                                    text_align=ft.TextAlign.CENTER,
                                ),
                                ft.Container(height=30),
                                
                                # Database path
                                ft.Card(
                                    content=ft.Container(
                                        content=ft.Column(
                                            [
                                                ft.Text("Database File Location", size=16, weight=ft.FontWeight.BOLD),
                                                ft.Text(
                                                    "This file will store all your reports and system data",
                                                    size=12,
                                                    color=ft.Colors.GREY_600,
                                                ),
                                                ft.Container(height=10),
                                                db_path_field,
                                            ],
                                        ),
                                        padding=20,
                                    ),
                                    elevation=2,
                                ),
                                
                                ft.Container(height=15),
                                
                                # Backup path
                                ft.Card(
                                    content=ft.Container(
                                        content=ft.Column(
                                            [
                                                ft.Text("Backup Directory", size=16, weight=ft.FontWeight.BOLD),
                                                ft.Text(
                                                    "Automatic backups will be stored here",
                                                    size=12,
                                                    color=ft.Colors.GREY_600,
                                                ),
                                                ft.Container(height=10),
                                                backup_path_field,
                                            ],
                                        ),
                                        padding=20,
                                    ),
                                    elevation=2,
                                ),
                                
                                ft.Container(height=10),
                                status_text,
                                ft.Container(height=20),
                                
                                ft.ElevatedButton(
                                    text="Continue",
                                    icon=ft.Icons.ARROW_FORWARD,
                                    on_click=validate_and_continue,
                                    height=45,
                                    width=200,
                                ),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            scroll=ft.ScrollMode.AUTO,
                        ),
                        padding=40,
                        expand=True,
                    ),
                ],
                spacing=0,
            ),
            expand=True,
            bgcolor=ft.Colors.WHITE,
        )
        
        self.page.clean()
        self.page.add(setup_view)
        self.page.update()
    
    def show_database_found_dialog(self):
        """Step 3: Database exists - ask to use it"""
        logger.info("=== Showing Database Found Dialog ===")

        def use_existing(e):
            logger.info("User chose to use existing database")
            self.page.close(dialog)

            # Save configuration
            Config.DATABASE_PATH = self.temp_db_path
            Config.BACKUP_PATH = self.temp_backup_path
            Config.save()

            # Initialize database
            if self.init_database():
                self.show_login_screen()
            else:
                self.show_error_dialog("Database Error", "Failed to initialize existing database")

        def create_new(e):
            logger.info("User chose to create new database")
            self.page.close(dialog)
            self.show_admin_credentials_prompt()

        def cancel(e):
            logger.info("User cancelled")
            self.page.close(dialog)
            self.show_setup_wizard_step1()
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Database Found"),
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(ft.Icons.INFO_OUTLINE, size=48, color=ft.Colors.BLUE_700),
                        ft.Container(height=10),
                        ft.Text(
                            "An existing database was found at:",
                            size=14,
                        ),
                        ft.Container(
                            content=ft.Text(
                                self.temp_db_path,
                                size=12,
                                color=ft.Colors.BLUE_700,
                                weight=ft.FontWeight.BOLD,
                            ),
                            padding=10,
                            bgcolor=ft.Colors.BLUE_50,
                            border_radius=5,
                        ),
                        ft.Container(height=15),
                        ft.Text(
                            "Would you like to use this existing database or create a new one?",
                            size=14,
                            text_align=ft.TextAlign.CENTER,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    tight=True,
                ),
                width=400,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=cancel),
                ft.OutlinedButton("Create New", on_click=create_new),
                ft.ElevatedButton("Use Existing", on_click=use_existing),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        self.page.open(dialog)
    
    def show_admin_credentials_prompt(self):
        """Step 4: Admin Verification - Must enter admin/admin123"""
        logger.info("=== Showing Admin Credentials Prompt ===")
        
        username_field = ft.TextField(
            label="Admin Username",
            hint_text="Enter: admin",
            prefix_icon=ft.Icons.ADMIN_PANEL_SETTINGS,
            autofocus=True,
        )
        
        password_field = ft.TextField(
            label="Admin Password",
            hint_text="Enter: admin123",
            prefix_icon=ft.Icons.LOCK,
            password=True,
            can_reveal_password=True,
        )
        
        error_text = ft.Text("", color=ft.Colors.RED_700, size=12)
        
        def verify_and_create(e):
            username = username_field.value.strip()
            password = password_field.value

            if username != "admin" or password != "admin123":
                error_text.value = "⚠ Invalid credentials. Use: admin / admin123"
                logger.warning("Invalid admin credentials entered")
                self.page.update()
                return

            logger.info("Admin credentials verified")
            self.page.close(dialog)

            # Create new database
            self.create_new_database()

        def cancel(e):
            self.page.close(dialog)
            self.show_setup_wizard_step1()
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Admin Verification Required"),
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(ft.Icons.VERIFIED_USER, size=48, color=ft.Colors.AMBER_700),
                        ft.Container(height=10),
                        ft.Text(
                            "To create a new database, please verify admin credentials:",
                            size=14,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Container(height=15),
                        username_field,
                        ft.Container(height=10),
                        password_field,
                        ft.Container(height=5),
                        error_text,
                        ft.Container(height=10),
                        ft.Container(
                            content=ft.Text(
                                "Default credentials:\nUsername: admin\nPassword: admin123",
                                size=12,
                                color=ft.Colors.GREY_600,
                                text_align=ft.TextAlign.CENTER,
                            ),
                            padding=10,
                            bgcolor=ft.Colors.GREY_100,
                            border_radius=5,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    tight=True,
                ),
                width=400,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=cancel),
                ft.ElevatedButton("Verify & Create", on_click=verify_and_create),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        self.page.open(dialog)
    
    def create_new_database(self):
        """Create new database with progress indicator"""
        logger.info("=== Creating New Database ===")
        
        # Show progress dialog
        progress = ft.ProgressRing()
        status_text = ft.Text("Creating database...", size=14)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Setting Up Database"),
            content=ft.Container(
                content=ft.Column(
                    [
                        progress,
                        ft.Container(height=15),
                        status_text,
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    tight=True,
                ),
                width=300,
            ),
            modal=True,
        )
        
        self.page.open(dialog)
        
        try:
            # Validate and create directories
            db_path = Path(self.temp_db_path)

            # Ensure the path ends with .db extension
            if not str(db_path).lower().endswith('.db'):
                db_path = Path(str(db_path) + '.db')
                self.temp_db_path = str(db_path)
                logger.info(f"Added .db extension to path: {self.temp_db_path}")

            # Create parent directory
            logger.info(f"Creating directory: {db_path.parent}")
            db_path.parent.mkdir(parents=True, exist_ok=True)

            # Create backup directory
            logger.info(f"Creating backup directory: {self.temp_backup_path}")
            Path(self.temp_backup_path).mkdir(parents=True, exist_ok=True)

            status_text.value = "Initializing database schema..."
            self.page.update()

            # Initialize database
            logger.info(f"Initializing database at: {self.temp_db_path}")
            success, message = initialize_database(self.temp_db_path)
            
            if not success:
                logger.error(f"Database creation failed: {message}")
                self.page.close(dialog)
                self.show_error_dialog("Database Creation Failed", message)
                return

            status_text.value = "Saving configuration..."
            self.page.update()

            # Save configuration
            Config.DATABASE_PATH = self.temp_db_path
            Config.BACKUP_PATH = self.temp_backup_path
            if not Config.save():
                logger.error("Failed to save configuration")
                self.page.close(dialog)
                self.show_error_dialog("Setup Failed", "Failed to save configuration")
                return

            status_text.value = "Database created successfully!"
            self.page.update()

            logger.info("Database created successfully")

            # Close dialog and show auto-login
            import time
            time.sleep(1)
            self.page.close(dialog)
            
            # Initialize database connection
            if self.init_database():
                self.show_auto_login()
            else:
                self.show_error_dialog("Initialization Error", "Failed to initialize database connection")
            
        except Exception as e:
            logger.error(f"Database creation error: {e}")
            self.page.close(dialog)
            self.show_error_dialog("Setup Error", f"Failed to create database: {str(e)}")
    
    def show_auto_login(self):
        """Step 5: Auto-login with pre-filled credentials"""
        logger.info("=== Showing Auto-Login Screen ===")
        
        username_field = ft.TextField(
            label="Username",
            value="admin",
            prefix_icon=ft.Icons.PERSON,
            read_only=True,
        )
        
        password_field = ft.TextField(
            label="Password",
            value="admin123",
            prefix_icon=ft.Icons.LOCK,
            password=True,
            can_reveal_password=True,
            read_only=True,
        )
        
        def proceed_to_login(e):
            logger.info("Proceeding to main login")
            self.show_login_screen()
        
        auto_login_view = ft.Container(
            content=ft.Column(
                [
                    ft.Icon(ft.Icons.CHECK_CIRCLE, size=80, color=ft.Colors.GREEN_700),
                    ft.Container(height=20),
                    ft.Text(
                        "Setup Complete!",
                        size=32,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.GREEN_700,
                    ),
                    ft.Container(height=10),
                    ft.Text(
                        "Your database has been created successfully",
                        size=16,
                        color=ft.Colors.GREY_700,
                    ),
                    ft.Container(height=30),
                    
                    ft.Card(
                        content=ft.Container(
                            content=ft.Column(
                                [
                                    ft.Text("Default Admin Credentials", size=18, weight=ft.FontWeight.BOLD),
                                    ft.Divider(),
                                    username_field,
                                    ft.Container(height=10),
                                    password_field,
                                    ft.Container(height=15),
                                    ft.Container(
                                        content=ft.Text(
                                            "⚠ Please change these credentials after first login",
                                            size=12,
                                            color=ft.Colors.ORANGE_700,
                                            text_align=ft.TextAlign.CENTER,
                                        ),
                                        padding=10,
                                        bgcolor=ft.Colors.ORANGE_50,
                                        border_radius=5,
                                    ),
                                ],
                            ),
                            padding=30,
                            width=400,
                        ),
                        elevation=5,
                    ),
                    
                    ft.Container(height=30),
                    ft.ElevatedButton(
                        text="Proceed to Login",
                        icon=ft.Icons.LOGIN,
                        on_click=proceed_to_login,
                        height=50,
                        width=200,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            expand=True,
            alignment=ft.alignment.center,
            gradient=ft.LinearGradient(
                begin=ft.alignment.top_left,
                end=ft.alignment.bottom_right,
                colors=[ft.Colors.GREEN_50, ft.Colors.WHITE],
            ),
        )
        
        self.page.clean()
        self.page.add(auto_login_view)
        self.page.update()
    
    def show_login_screen(self):
        """Step 6: Main Login Screen"""
        logger.info("=== Showing Login Screen ===")
        
        username_field = ft.TextField(
            label="Username",
            prefix_icon=ft.Icons.PERSON,
            autofocus=True,
            width=350,
        )
        
        password_field = ft.TextField(
            label="Password",
            prefix_icon=ft.Icons.LOCK,
            password=True,
            can_reveal_password=True,
            width=350,
            on_submit=lambda e: attempt_login(),
        )
        
        error_text = ft.Text("", color=ft.Colors.RED_700, visible=False)
        loading = ft.ProgressRing(visible=False, width=20, height=20)
        
        def attempt_login():
            username = username_field.value.strip()
            password = password_field.value
            
            if not username or not password:
                error_text.value = "Please enter username and password"
                error_text.visible = True
                self.page.update()
                return
            
            loading.visible = True
            error_text.visible = False
            self.page.update()
            
            # Authenticate
            user = self.authenticate_user(username, password)
            
            if user:
                logger.info(f"User logged in: {username}")
                self.current_user = user
                self.show_main_application()
            else:
                logger.warning(f"Login failed for: {username}")
                error_text.value = "Invalid username or password"
                error_text.visible = True
                loading.visible = False
                self.page.update()
        
        login_card = ft.Card(
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(ft.Icons.SECURITY, size=70, color=ft.Colors.BLUE_700),
                        ft.Container(height=15),
                        ft.Text("FIU Report System", size=26, weight=ft.FontWeight.BOLD),
                        ft.Text("Secure Login", size=14, color=ft.Colors.GREY_600),
                        ft.Container(height=25),
                        username_field,
                        ft.Container(height=15),
                        password_field,
                        ft.Container(height=10),
                        ft.Row(
                            [loading, error_text],
                            alignment=ft.MainAxisAlignment.CENTER,
                        ),
                        ft.Container(height=20),
                        ft.ElevatedButton(
                            text="Sign In",
                            icon=ft.Icons.LOGIN,
                            on_click=lambda e: attempt_login(),
                            width=350,
                            height=45,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=40,
            ),
            elevation=8,
        )
        
        login_view = ft.Container(
            content=ft.Column(
                [login_card],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            expand=True,
            alignment=ft.alignment.center,
            gradient=ft.LinearGradient(
                begin=ft.alignment.top_left,
                end=ft.alignment.bottom_right,
                colors=[ft.Colors.BLUE_50, ft.Colors.WHITE],
            ),
        )
        
        self.page.clean()
        self.page.add(login_view)
        self.page.update()
    
    def init_database(self):
        """Initialize database manager"""
        try:
            logger.info("Initializing database manager")
            
            # Validate database
            is_valid, message = validate_database(Config.DATABASE_PATH)
            if not is_valid:
                logger.error(f"Database validation failed: {message}")
                self.show_error_dialog("Database Error", message)
                return False
            
            # Create database manager
            self.db_manager = DatabaseManager(Config.DATABASE_PATH)
            self.write_queue = WriteQueue(self.db_manager)
            
            logger.info("Database manager initialized")
            return True
            
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
            return False
    
    def authenticate_user(self, username: str, password: str):
        """Authenticate user"""
        try:
            query = """
                SELECT user_id, username, full_name, role, is_active
                FROM users 
                WHERE username = ? AND password = ? AND is_active = 1
            """
            results = self.db_manager.execute_with_retry(query, (username, password))
            
            if results:
                user = dict(results[0])
                
                # Update last login
                update_query = """
                    UPDATE users 
                    SET last_login = datetime('now'), failed_login_attempts = 0
                    WHERE user_id = ?
                """
                self.db_manager.execute_with_retry(update_query, (user['user_id'],))
                
                return user
            
            return None
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None
    
    def show_main_application(self):
        """Main application interface"""
        logger.info("=== Loading Main Application ===")
        
        # Navigation
        nav_items = [
            ("Dashboard", ft.Icons.DASHBOARD_OUTLINED, ft.Icons.DASHBOARD),
            ("Reports", ft.Icons.LIST_ALT_OUTLINED, ft.Icons.LIST_ALT),
        ]
        
        # Add navigation items based on role
        if has_permission(self.current_user['role'], 'add_report'):
            nav_items.append(("Add Report", ft.Icons.ADD_CIRCLE_OUTLINE, ft.Icons.ADD_CIRCLE))
        
        if has_permission(self.current_user['role'], 'access_admin_panel'):
            nav_items.append(("Admin", ft.Icons.ADMIN_PANEL_SETTINGS_OUTLINED, ft.Icons.ADMIN_PANEL_SETTINGS))
        
        if has_permission(self.current_user['role'], 'export'):
            nav_items.append(("Export", ft.Icons.DOWNLOAD_OUTLINED, ft.Icons.DOWNLOAD))
        
        destinations = [
            ft.NavigationRailDestination(
                icon=icon_out,
                selected_icon=icon_sel,
                label=label,
            )
            for label, icon_out, icon_sel in nav_items
        ]
        
        nav_rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=100,
            min_extended_width=200,
            destinations=destinations,
            on_change=self.handle_navigation,
            bgcolor=ft.Colors.BLUE_GREY_50,
        )
        
        # Header
        header = ft.Container(
            content=ft.Row(
                [
                    ft.Column(
                        [
                            ft.Text(
                                f"Welcome, {self.current_user['full_name']}",
                                size=18,
                                weight=ft.FontWeight.BOLD,
                            ),
                            ft.Text(
                                f"Role: {self.current_user['role'].title()}",
                                size=12,
                                color=ft.Colors.GREY_700,
                            ),
                        ],
                        spacing=2,
                    ),
                    ft.Row(
                        [
                            ft.IconButton(
                                icon=ft.Icons.REFRESH,
                                tooltip="Refresh",
                                on_click=lambda e: self.refresh_current_view(),
                            ),
                            ft.IconButton(
                                icon=ft.Icons.LOGOUT,
                                tooltip="Logout",
                                on_click=lambda e: self.logout(),
                            ),
                        ],
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            padding=15,
            bgcolor=ft.Colors.BLUE_50,
        )
        
        # Content area
        self.content_area = ft.Container(expand=True, padding=20)
        
        # Main layout
        main_layout = ft.Row(
            [
                nav_rail,
                ft.VerticalDivider(width=1),
                ft.Column(
                    [
                        header,
                        ft.Divider(height=1),
                        self.content_area,
                    ],
                    spacing=0,
                    expand=True,
                ),
            ],
            spacing=0,
            expand=True,
        )
        
        self.page.clean()
        self.page.add(main_layout)
        
        # Load dashboard
        self.load_dashboard()
    
    def handle_navigation(self, e):
        """Handle navigation"""
        try:
            index = e.control.selected_index
            
            views = [
                self.load_dashboard,
                self.load_reports,
            ]
            
            # Add conditional views
            if has_permission(self.current_user['role'], 'add_report'):
                views.append(self.load_add_report)
            
            if has_permission(self.current_user['role'], 'access_admin_panel'):
                views.append(self.load_admin_panel)
            
            if has_permission(self.current_user['role'], 'export'):
                views.append(self.load_export)
            
            if index < len(views):
                views[index]()
            
        except Exception as e:
            logger.error(f"Navigation error: {e}")
            self.show_error_snackbar(f"Navigation failed: {str(e)}")
    
    def load_dashboard(self):
        """Load dashboard"""
        logger.info("Loading dashboard")
        
        try:
            # Get statistics
            total_reports = self.db_manager.execute_with_retry(
                "SELECT COUNT(*) as count FROM reports WHERE is_deleted = 0"
            )[0]['count']
            
            open_reports = self.db_manager.execute_with_retry(
                "SELECT COUNT(*) as count FROM reports WHERE status = 'Open' AND is_deleted = 0"
            )[0]['count']
            
            under_investigation = self.db_manager.execute_with_retry(
                "SELECT COUNT(*) as count FROM reports WHERE status = 'Under Investigation' AND is_deleted = 0"
            )[0]['count']
            
            closed_reports = self.db_manager.execute_with_retry(
                "SELECT COUNT(*) as count FROM reports WHERE status IN ('Close Case', 'Closed with STR') AND is_deleted = 0"
            )[0]['count']
            
            # Create stat cards
            def create_stat_card(title, value, color, icon):
                return ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(icon, size=40, color=color),
                            ft.Container(height=10),
                            ft.Text(str(value), size=32, weight=ft.FontWeight.BOLD),
                            ft.Text(title, size=14, color=ft.Colors.GREY_700),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=20,
                    bgcolor=ft.Colors.WHITE,
                    border_radius=10,
                    border=ft.border.all(2, color),
                    width=200,
                )
            
            dashboard_content = ft.Column(
                [
                    ft.Text("Dashboard", size=28, weight=ft.FontWeight.BOLD),
                    ft.Container(height=20),
                    
                    ft.Row(
                        [
                            create_stat_card("Total Reports", total_reports, ft.Colors.BLUE_700, ft.Icons.DESCRIPTION),
                            create_stat_card("Open Reports", open_reports, ft.Colors.GREEN_700, ft.Icons.FOLDER_OPEN),
                            create_stat_card("Under Investigation", under_investigation, ft.Colors.ORANGE_700, ft.Icons.SEARCH),
                            create_stat_card("Closed Cases", closed_reports, ft.Colors.RED_700, ft.Icons.CHECK_CIRCLE),
                        ],
                        wrap=True,
                        spacing=15,
                        run_spacing=15,
                    ),
                    
                    ft.Container(height=30),
                    
                    ft.Card(
                        content=ft.Container(
                            content=ft.Column(
                                [
                                    ft.Text("Quick Actions", size=20, weight=ft.FontWeight.BOLD),
                                    ft.Divider(),
                                    ft.Row(
                                        [
                                            ft.ElevatedButton(
                                                "View All Reports",
                                                icon=ft.Icons.LIST,
                                                on_click=lambda e: self.load_reports(),
                                            ),
                                            ft.ElevatedButton(
                                                "Add New Report",
                                                icon=ft.Icons.ADD,
                                                on_click=lambda e: self.load_add_report(),
                                            ) if has_permission(self.current_user['role'], 'add_report') else ft.Container(),
                                            ft.ElevatedButton(
                                                "Export Data",
                                                icon=ft.Icons.DOWNLOAD,
                                                on_click=lambda e: self.load_export(),
                                            ) if has_permission(self.current_user['role'], 'export') else ft.Container(),
                                        ],
                                        wrap=True,
                                        spacing=10,
                                    ),
                                ],
                            ),
                            padding=20,
                        ),
                        elevation=2,
                    ),
                ],
                scroll=ft.ScrollMode.AUTO,
            )
            
            self.content_area.content = dashboard_content
            self.page.update()
            
        except Exception as e:
            logger.error(f"Dashboard load error: {e}")
            self.show_error_snackbar("Failed to load dashboard")
    
    def load_reports(self):
        """Load reports list"""
        logger.info("Loading reports")

        from reports_module import ReportsModule
        module = ReportsModule(self.page, self.db_manager, self.current_user, self.content_area)
        module.show()
    
    def load_add_report(self):
        """Load add report form"""
        logger.info("Loading add report form")

        from add_report_module import AddReportModule
        module = AddReportModule(self.page, self.db_manager, self.current_user, self.content_area)
        module.show()
    
    def load_admin_panel(self):
        """Load admin panel with user management"""
        logger.info("Loading admin panel")
        
        from admin_panel import AdminPanel
        panel = AdminPanel(self.page, self.db_manager, self.current_user, self.content_area)
        panel.show()
    
    def load_export(self):
        """Load export view"""
        logger.info("Loading export view")

        from export_module import ExportModule
        module = ExportModule(self.page, self.db_manager, self.current_user, self.content_area)
        module.show()
    
    def refresh_current_view(self):
        """Refresh current view"""
        self.show_info_snackbar("Refreshed")
    
    def logout(self):
        """Logout user"""
        logger.info(f"User logging out: {self.current_user['username']}")
        self.current_user = None
        self.show_login_screen()
    
    # Helper methods
    def show_error_dialog(self, title, message):
        """Show error dialog"""
        self.current_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(title),
            content=ft.Text(message),
            actions=[ft.TextButton("OK", on_click=lambda e: self.close_dialog())],
        )
        self.page.open(self.current_dialog)

    def show_info_snackbar(self, message):
        """Show info snackbar"""
        self.page.snack_bar = ft.SnackBar(content=ft.Text(message))
        self.page.snack_bar.open = True
        self.page.update()

    def show_error_snackbar(self, message):
        """Show error snackbar"""
        self.page.snack_bar = ft.SnackBar(
            content=ft.Text(message),
            bgcolor=ft.Colors.RED_700,
        )
        self.page.snack_bar.open = True
        self.page.update()

    def close_dialog(self):
        """Close dialog"""
        if self.current_dialog:
            self.page.close(self.current_dialog)
            self.current_dialog = None
    
    def show_error_screen(self, title, message):
        """Show error screen"""
        error_view = ft.Container(
            content=ft.Column(
                [
                    ft.Icon(ft.Icons.ERROR, size=80, color=ft.Colors.RED_700),
                    ft.Text(title, size=24, weight=ft.FontWeight.BOLD),
                    ft.Text(message, size=16, text_align=ft.TextAlign.CENTER),
                    ft.Container(height=20),
                    ft.ElevatedButton(
                        "Restart",
                        icon=ft.Icons.REFRESH,
                        on_click=lambda e: self.page.window_destroy(),
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            expand=True,
            alignment=ft.alignment.center,
            padding=40,
        )
        self.page.clean()
        self.page.add(error_view)
        self.page.update()


def main(page: ft.Page):
    """Application entry point"""
    try:
        logger.info("=" * 50)
        logger.info("FIU Report Management System Starting")
        logger.info("=" * 50)

        # Create application
        FIUApplication(page)
        
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        logger.critical(f"Traceback: {__import__('traceback').format_exc()}")
        
        # Show basic error screen
        page.clean()
        page.add(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text("Critical Error", size=24, weight=ft.FontWeight.BOLD),
                        ft.Text(str(e), size=14),
                        ft.Container(height=20),
                        ft.ElevatedButton("Exit", on_click=lambda e: page.window_destroy()),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                alignment=ft.alignment.center,
                expand=True,
                padding=40,
            )
        )
        page.update()


if __name__ == "__main__":
    logger.info("Starting Flet application")
    ft.app(target=main, view=ft.AppView.FLET_APP)
