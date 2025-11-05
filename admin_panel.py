"""
Admin Panel Module - Full User Management
Implements add, edit, delete, and manage users functionality
"""
import flet as ft
import logging
from datetime import datetime

logger = logging.getLogger('fiu_system')


class AdminPanel:
    """Complete admin panel with user management"""
    
    def __init__(self, page, db_manager, current_user, content_area):
        self.page = page
        self.db_manager = db_manager
        self.current_user = current_user
        self.content_area = content_area
        self.selected_tab = 0
        self.users_list = []
    
    def show(self):
        """Show admin panel"""
        logger.info("Showing admin panel")
        
        # Create tabs
        tabs = ft.Tabs(
            selected_index=self.selected_tab,
            animation_duration=300,
            tabs=[
                ft.Tab(
                    text="User Management",
                    icon=ft.Icons.PEOPLE,
                    content=self.build_user_management(),
                ),
                ft.Tab(
                    text="System Settings",
                    icon=ft.Icons.SETTINGS,
                    content=self.build_system_settings(),
                ),
                ft.Tab(
                    text="Database",
                    icon=ft.Icons.STORAGE,
                    content=self.build_database_management(),
                ),
            ],
            expand=1,
        )
        
        admin_content = ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(ft.Icons.ADMIN_PANEL_SETTINGS, size=32, color=ft.Colors.BLUE_700),
                        ft.Text("Administration Panel", size=28, weight=ft.FontWeight.BOLD),
                    ],
                ),
                ft.Divider(),
                tabs,
            ],
            expand=True,
        )
        
        self.content_area.content = admin_content
        self.page.update()
    
    def build_user_management(self):
        """Build user management tab"""
        logger.info("Building user management interface")
        
        # Load users
        self.load_users()
        
        # Create user list
        user_rows = []
        for user in self.users_list:
            user_rows.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Column(
                                [
                                    ft.Text(user['username'], weight=ft.FontWeight.BOLD, size=16),
                                    ft.Text(user['full_name'], size=14),
                                ],
                                spacing=2,
                            ),
                            ft.Container(
                                content=ft.Text(
                                    user['role'].title(),
                                    size=12,
                                    color=ft.Colors.WHITE,
                                ),
                                bgcolor=self.get_role_color(user['role']),
                                padding=5,
                                border_radius=5,
                            ),
                            ft.Container(
                                content=ft.Text(
                                    "Active" if user['is_active'] else "Inactive",
                                    size=12,
                                    color=ft.Colors.WHITE,
                                ),
                                bgcolor=ft.Colors.GREEN_700 if user['is_active'] else ft.Colors.RED_700,
                                padding=5,
                                border_radius=5,
                            ),
                            ft.Row(
                                [
                                    ft.IconButton(
                                        icon=ft.Icons.EDIT,
                                        tooltip="Edit User",
                                        on_click=lambda e, u=user: self.show_edit_user_dialog(u),
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.DELETE,
                                        tooltip="Delete User",
                                        on_click=lambda e, u=user: self.show_delete_user_dialog(u),
                                        icon_color=ft.Colors.RED_700,
                                        disabled=user['user_id'] == 1,  # Cannot delete default admin
                                    ),
                                ],
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    padding=15,
                    border=ft.border.all(1, ft.Colors.GREY_300),
                    border_radius=10,
                    bgcolor=ft.Colors.WHITE,
                )
            )
        
        user_management_content = ft.Column(
            [
                ft.Row(
                    [
                        ft.Text("User Management", size=20, weight=ft.FontWeight.BOLD),
                        ft.ElevatedButton(
                            text="Add New User",
                            icon=ft.Icons.PERSON_ADD,
                            on_click=lambda e: self.show_add_user_dialog(),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Divider(),
                
                ft.Container(
                    content=ft.Column(
                        user_rows,
                        spacing=10,
                        scroll=ft.ScrollMode.AUTO,
                    ),
                    expand=True,
                ),
            ],
            expand=True,
        )
        
        return ft.Container(content=user_management_content, padding=20)
    
    def build_system_settings(self):
        """Build system settings tab"""
        return ft.Container(
            content=ft.Column(
                [
                    ft.Text("System Settings", size=20, weight=ft.FontWeight.BOLD),
                    ft.Divider(),
                    ft.Text("System configuration options will be implemented here"),
                ],
            ),
            padding=20,
        )
    
    def build_database_management(self):
        """Build database management tab"""
        from config import Config
        
        def create_backup(e):
            try:
                from pathlib import Path
                backup_file = Path(Config.BACKUP_PATH) / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                
                if self.db_manager.backup_database(str(backup_file)):
                    self.show_success("Backup created successfully")
                    logger.info(f"Backup created: {backup_file}")
                else:
                    self.show_error("Failed to create backup")
            except Exception as ex:
                logger.error(f"Backup error: {ex}")
                self.show_error(f"Backup failed: {str(ex)}")
        
        return ft.Container(
            content=ft.Column(
                [
                    ft.Text("Database Management", size=20, weight=ft.FontWeight.BOLD),
                    ft.Divider(),
                    
                    ft.Card(
                        content=ft.Container(
                            content=ft.Column(
                                [
                                    ft.Text("Database Location", size=16, weight=ft.FontWeight.BOLD),
                                    ft.Text(Config.DATABASE_PATH, size=12, color=ft.Colors.GREY_700),
                                    ft.Container(height=10),
                                    ft.Text("Backup Directory", size=16, weight=ft.FontWeight.BOLD),
                                    ft.Text(Config.BACKUP_PATH, size=12, color=ft.Colors.GREY_700),
                                ],
                            ),
                            padding=20,
                        ),
                        elevation=2,
                    ),
                    
                    ft.Container(height=20),
                    
                    ft.Card(
                        content=ft.Container(
                            content=ft.Column(
                                [
                                    ft.Text("Backup Management", size=16, weight=ft.FontWeight.BOLD),
                                    ft.Divider(),
                                    ft.ElevatedButton(
                                        text="Create Backup Now",
                                        icon=ft.Icons.BACKUP,
                                        on_click=create_backup,
                                    ),
                                ],
                            ),
                            padding=20,
                        ),
                        elevation=2,
                    ),
                ],
            ),
            padding=20,
        )
    
    def load_users(self):
        """Load all users from database"""
        try:
            query = """
                SELECT user_id, username, full_name, role, is_active, last_login, created_at
                FROM users
                ORDER BY user_id
            """
            results = self.db_manager.execute_with_retry(query)
            self.users_list = [dict(row) for row in results]
            logger.info(f"Loaded {len(self.users_list)} users")
        except Exception as e:
            logger.error(f"Failed to load users: {e}")
            self.users_list = []
    
    def show_add_user_dialog(self):
        """Show add user dialog"""
        logger.info("Showing add user dialog")
        
        username_field = ft.TextField(
            label="Username",
            hint_text="Enter username",
            prefix_icon=ft.Icons.PERSON,
            autofocus=True,
        )
        
        password_field = ft.TextField(
            label="Password",
            hint_text="Enter password",
            prefix_icon=ft.Icons.LOCK,
            password=True,
            can_reveal_password=True,
        )
        
        full_name_field = ft.TextField(
            label="Full Name",
            hint_text="Enter full name",
            prefix_icon=ft.Icons.BADGE,
        )
        
        role_dropdown = ft.Dropdown(
            label="Role",
            hint_text="Select role",
            options=[
                ft.dropdown.Option("admin", "Administrator"),
                ft.dropdown.Option("agent", "Agent"),
                ft.dropdown.Option("reporter", "Reporter"),
            ],
            value="agent",
        )
        
        is_active_checkbox = ft.Checkbox(
            label="Active User",
            value=True,
        )
        
        error_text = ft.Text("", color=ft.Colors.RED_700, visible=False)
        
        def validate_and_add(e):
            # Validation
            if not username_field.value or not username_field.value.strip():
                error_text.value = "Username is required"
                error_text.visible = True
                self.page.update()
                return
            
            if not password_field.value or len(password_field.value) < 3:
                error_text.value = "Password must be at least 3 characters"
                error_text.visible = True
                self.page.update()
                return
            
            if not full_name_field.value or not full_name_field.value.strip():
                error_text.value = "Full name is required"
                error_text.visible = True
                self.page.update()
                return
            
            # Check if username exists
            check_query = "SELECT COUNT(*) as count FROM users WHERE username = ?"
            result = self.db_manager.execute_with_retry(check_query, (username_field.value.strip(),))
            if result[0]['count'] > 0:
                error_text.value = "Username already exists"
                error_text.visible = True
                self.page.update()
                return
            
            # Add user
            try:
                insert_query = """
                    INSERT INTO users (username, password, full_name, role, is_active, created_at, created_by)
                    VALUES (?, ?, ?, ?, ?, datetime('now'), ?)
                """
                self.db_manager.execute_with_retry(
                    insert_query,
                    (
                        username_field.value.strip(),
                        password_field.value,
                        full_name_field.value.strip(),
                        role_dropdown.value,
                        1 if is_active_checkbox.value else 0,
                        self.current_user['username'],
                    )
                )
                
                logger.info(f"User added: {username_field.value}")
                self.page.dialog.open = False
                self.page.update()
                
                # Refresh user list
                self.show()
                self.show_success(f"User '{username_field.value}' added successfully")
                
            except Exception as ex:
                logger.error(f"Failed to add user: {ex}")
                error_text.value = f"Failed to add user: {str(ex)}"
                error_text.visible = True
                self.page.update()
        
        def cancel(e):
            self.page.dialog.open = False
            self.page.update()
        
        dialog = ft.AlertDialog(
            title=ft.Text("Add New User"),
            content=ft.Container(
                content=ft.Column(
                    [
                        username_field,
                        ft.Container(height=10),
                        password_field,
                        ft.Container(height=10),
                        full_name_field,
                        ft.Container(height=10),
                        role_dropdown,
                        ft.Container(height=10),
                        is_active_checkbox,
                        ft.Container(height=10),
                        error_text,
                    ],
                    tight=True,
                    scroll=ft.ScrollMode.AUTO,
                ),
                width=400,
                height=400,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=cancel),
                ft.ElevatedButton("Add User", on_click=validate_and_add),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
    
    def show_edit_user_dialog(self, user):
        """Show edit user dialog"""
        logger.info(f"Showing edit dialog for user: {user['username']}")
        
        username_field = ft.TextField(
            label="Username",
            value=user['username'],
            read_only=True,
            prefix_icon=ft.Icons.PERSON,
        )
        
        password_field = ft.TextField(
            label="New Password (leave empty to keep current)",
            hint_text="Enter new password or leave empty",
            prefix_icon=ft.Icons.LOCK,
            password=True,
            can_reveal_password=True,
        )
        
        full_name_field = ft.TextField(
            label="Full Name",
            value=user['full_name'],
            prefix_icon=ft.Icons.BADGE,
        )
        
        role_dropdown = ft.Dropdown(
            label="Role",
            options=[
                ft.dropdown.Option("admin", "Administrator"),
                ft.dropdown.Option("agent", "Agent"),
                ft.dropdown.Option("reporter", "Reporter"),
            ],
            value=user['role'],
        )
        
        is_active_checkbox = ft.Checkbox(
            label="Active User",
            value=bool(user['is_active']),
        )
        
        error_text = ft.Text("", color=ft.Colors.RED_700, visible=False)
        
        def validate_and_update(e):
            # Validation
            if not full_name_field.value or not full_name_field.value.strip():
                error_text.value = "Full name is required"
                error_text.visible = True
                self.page.update()
                return
            
            if password_field.value and len(password_field.value) < 3:
                error_text.value = "Password must be at least 3 characters"
                error_text.visible = True
                self.page.update()
                return
            
            # Update user
            try:
                if password_field.value:
                    # Update with new password
                    update_query = """
                        UPDATE users 
                        SET password = ?, full_name = ?, role = ?, is_active = ?, 
                            updated_at = datetime('now'), updated_by = ?
                        WHERE user_id = ?
                    """
                    params = (
                        password_field.value,
                        full_name_field.value.strip(),
                        role_dropdown.value,
                        1 if is_active_checkbox.value else 0,
                        self.current_user['username'],
                        user['user_id'],
                    )
                else:
                    # Update without password change
                    update_query = """
                        UPDATE users 
                        SET full_name = ?, role = ?, is_active = ?, 
                            updated_at = datetime('now'), updated_by = ?
                        WHERE user_id = ?
                    """
                    params = (
                        full_name_field.value.strip(),
                        role_dropdown.value,
                        1 if is_active_checkbox.value else 0,
                        self.current_user['username'],
                        user['user_id'],
                    )
                
                self.db_manager.execute_with_retry(update_query, params)
                
                logger.info(f"User updated: {user['username']}")
                self.page.dialog.open = False
                self.page.update()
                
                # Refresh user list
                self.show()
                self.show_success(f"User '{user['username']}' updated successfully")
                
            except Exception as ex:
                logger.error(f"Failed to update user: {ex}")
                error_text.value = f"Failed to update user: {str(ex)}"
                error_text.visible = True
                self.page.update()
        
        def cancel(e):
            self.page.dialog.open = False
            self.page.update()
        
        dialog = ft.AlertDialog(
            title=ft.Text(f"Edit User: {user['username']}"),
            content=ft.Container(
                content=ft.Column(
                    [
                        username_field,
                        ft.Container(height=10),
                        password_field,
                        ft.Container(height=10),
                        full_name_field,
                        ft.Container(height=10),
                        role_dropdown,
                        ft.Container(height=10),
                        is_active_checkbox,
                        ft.Container(height=10),
                        error_text,
                    ],
                    tight=True,
                    scroll=ft.ScrollMode.AUTO,
                ),
                width=400,
                height=400,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=cancel),
                ft.ElevatedButton("Update User", on_click=validate_and_update),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
    
    def show_delete_user_dialog(self, user):
        """Show delete user confirmation dialog"""
        logger.info(f"Showing delete confirmation for user: {user['username']}")
        
        # Cannot delete default admin
        if user['user_id'] == 1:
            self.show_error("Cannot delete the default admin user")
            return
        
        def confirm_delete(e):
            try:
                # Soft delete - set is_active to 0
                delete_query = """
                    UPDATE users 
                    SET is_active = 0, updated_at = datetime('now'), updated_by = ?
                    WHERE user_id = ?
                """
                self.db_manager.execute_with_retry(
                    delete_query,
                    (self.current_user['username'], user['user_id'])
                )
                
                logger.info(f"User deleted: {user['username']}")
                self.page.dialog.open = False
                self.page.update()
                
                # Refresh user list
                self.show()
                self.show_success(f"User '{user['username']}' has been deactivated")
                
            except Exception as ex:
                logger.error(f"Failed to delete user: {ex}")
                self.show_error(f"Failed to delete user: {str(ex)}")
        
        def cancel(e):
            self.page.dialog.open = False
            self.page.update()
        
        dialog = ft.AlertDialog(
            title=ft.Text("Confirm Delete"),
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(ft.Icons.WARNING, size=48, color=ft.Colors.ORANGE_700),
                        ft.Container(height=10),
                        ft.Text(
                            f"Are you sure you want to delete user '{user['username']}'?",
                            size=14,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Container(height=10),
                        ft.Text(
                            "This action will deactivate the user account.",
                            size=12,
                            color=ft.Colors.GREY_700,
                            text_align=ft.TextAlign.CENTER,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    tight=True,
                ),
                width=350,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=cancel),
                ft.ElevatedButton(
                    "Delete User",
                    on_click=confirm_delete,
                    bgcolor=ft.Colors.RED_700,
                    color=ft.Colors.WHITE,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
    
    def get_role_color(self, role):
        """Get color for role badge"""
        colors = {
            'admin': ft.Colors.PURPLE_700,
            'agent': ft.Colors.BLUE_700,
            'reporter': ft.Colors.GREEN_700,
        }
        return colors.get(role, ft.Colors.GREY_700)
    
    def show_success(self, message):
        """Show success message"""
        self.page.snack_bar = ft.SnackBar(
            content=ft.Text(message),
            bgcolor=ft.Colors.GREEN_700,
        )
        self.page.snack_bar.open = True
        self.page.update()
    
    def show_error(self, message):
        """Show error message"""
        self.page.snack_bar = ft.SnackBar(
            content=ft.Text(message),
            bgcolor=ft.Colors.RED_700,
        )
        self.page.snack_bar.open = True
        self.page.update()
