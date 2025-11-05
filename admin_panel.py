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
        # Create tabs for different settings
        settings_tabs = ft.Tabs(
            selected_index=0,
            animation_duration=200,
            tabs=[
                ft.Tab(
                    text="General Settings",
                    icon=ft.Icons.SETTINGS,
                    content=self.build_general_settings(),
                ),
                ft.Tab(
                    text="Dropdown Values",
                    icon=ft.Icons.LIST,
                    content=self.build_dropdown_settings(),
                ),
                ft.Tab(
                    text="Field Configuration",
                    icon=ft.Icons.VIEW_COLUMN,
                    content=self.build_field_settings(),
                ),
            ],
            expand=1,
        )

        return ft.Container(
            content=ft.Column(
                [
                    ft.Text("System Settings", size=20, weight=ft.FontWeight.BOLD),
                    ft.Divider(),
                    settings_tabs,
                ],
                expand=True,
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
                SELECT user_id, username, org_username, full_name, role, is_active, last_login, created_at
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

        org_username_field = ft.TextField(
            label="Organization Username (Optional)",
            hint_text="Enter organization username for alternative login",
            prefix_icon=ft.Icons.BUSINESS,
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

            # Check if org_username exists (if provided)
            if org_username_field.value and org_username_field.value.strip():
                check_org_query = "SELECT COUNT(*) as count FROM users WHERE org_username = ?"
                result = self.db_manager.execute_with_retry(check_org_query, (org_username_field.value.strip(),))
                if result[0]['count'] > 0:
                    error_text.value = "Organization username already exists"
                    error_text.visible = True
                    self.page.update()
                    return

            # Add user
            try:
                org_username_value = org_username_field.value.strip() if org_username_field.value else None

                insert_query = """
                    INSERT INTO users (username, org_username, password, full_name, role, is_active, created_at, created_by)
                    VALUES (?, ?, ?, ?, ?, ?, datetime('now'), ?)
                """
                self.db_manager.execute_with_retry(
                    insert_query,
                    (
                        username_field.value.strip(),
                        org_username_value,
                        password_field.value,
                        full_name_field.value.strip(),
                        role_dropdown.value,
                        1 if is_active_checkbox.value else 0,
                        self.current_user['username'],
                    )
                )
                
                logger.info(f"User added: {username_field.value}")
                self.page.close(dialog)

                # Refresh user list
                self.show()
                self.show_success(f"User '{username_field.value}' added successfully")

            except Exception as ex:
                logger.error(f"Failed to add user: {ex}")
                error_text.value = f"Failed to add user: {str(ex)}"
                error_text.visible = True
                self.page.update()

        def cancel(e):
            self.page.close(dialog)
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Add New User"),
            content=ft.Container(
                content=ft.Column(
                    [
                        username_field,
                        ft.Container(height=10),
                        org_username_field,
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
                height=450,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=cancel),
                ft.ElevatedButton("Add User", on_click=validate_and_add),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        self.page.open(dialog)
    
    def show_edit_user_dialog(self, user):
        """Show edit user dialog"""
        logger.info(f"Showing edit dialog for user: {user['username']}")
        
        username_field = ft.TextField(
            label="Username",
            value=user['username'],
            read_only=True,
            prefix_icon=ft.Icons.PERSON,
        )

        org_username_field = ft.TextField(
            label="Organization Username (Optional)",
            value=user.get('org_username', ''),
            hint_text="Enter organization username for alternative login",
            prefix_icon=ft.Icons.BUSINESS,
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

            # Check if org_username exists (if changed and provided)
            if org_username_field.value and org_username_field.value.strip():
                org_username_new = org_username_field.value.strip()
                org_username_old = user.get('org_username', '')
                if org_username_new != org_username_old:
                    check_org_query = "SELECT COUNT(*) as count FROM users WHERE org_username = ? AND user_id != ?"
                    result = self.db_manager.execute_with_retry(check_org_query, (org_username_new, user['user_id']))
                    if result[0]['count'] > 0:
                        error_text.value = "Organization username already exists"
                        error_text.visible = True
                        self.page.update()
                        return

            # Update user
            try:
                org_username_value = org_username_field.value.strip() if org_username_field.value else None

                if password_field.value:
                    # Update with new password
                    update_query = """
                        UPDATE users
                        SET password = ?, org_username = ?, full_name = ?, role = ?, is_active = ?,
                            updated_at = datetime('now'), updated_by = ?
                        WHERE user_id = ?
                    """
                    params = (
                        password_field.value,
                        org_username_value,
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
                        SET org_username = ?, full_name = ?, role = ?, is_active = ?,
                            updated_at = datetime('now'), updated_by = ?
                        WHERE user_id = ?
                    """
                    params = (
                        org_username_value,
                        full_name_field.value.strip(),
                        role_dropdown.value,
                        1 if is_active_checkbox.value else 0,
                        self.current_user['username'],
                        user['user_id'],
                    )

                self.db_manager.execute_with_retry(update_query, params)
                
                logger.info(f"User updated: {user['username']}")
                self.page.close(dialog)

                # Refresh user list
                self.show()
                self.show_success(f"User '{user['username']}' updated successfully")

            except Exception as ex:
                logger.error(f"Failed to update user: {ex}")
                error_text.value = f"Failed to update user: {str(ex)}"
                error_text.visible = True
                self.page.update()

        def cancel(e):
            self.page.close(dialog)
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Edit User: {user['username']}"),
            content=ft.Container(
                content=ft.Column(
                    [
                        username_field,
                        ft.Container(height=10),
                        org_username_field,
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
                height=450,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=cancel),
                ft.ElevatedButton("Update User", on_click=validate_and_update),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        self.page.open(dialog)
    
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
                self.page.close(dialog)

                # Refresh user list
                self.show()
                self.show_success(f"User '{user['username']}' has been deactivated")

            except Exception as ex:
                logger.error(f"Failed to delete user: {ex}")
                self.show_error(f"Failed to delete user: {str(ex)}")

        def cancel(e):
            self.page.close(dialog)
        
        dialog = ft.AlertDialog(
            modal=True,
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
        
        self.page.open(dialog)
    
    def get_role_color(self, role):
        """Get color for role badge"""
        colors = {
            'admin': ft.Colors.PURPLE_700,
            'agent': ft.Colors.BLUE_700,
            'reporter': ft.Colors.GREEN_700,
        }
        return colors.get(role, ft.Colors.GREY_700)

    def build_general_settings(self):
        """Build general settings section"""
        try:
            # Load current settings
            query = "SELECT * FROM system_config WHERE config_category = 'general' ORDER BY display_order"
            settings = [dict(row) for row in self.db_manager.execute_with_retry(query)]

            settings_controls = []
            for setting in settings:
                settings_controls.append(
                    ft.Row(
                        [
                            ft.Text(setting['config_key'].replace('_', ' ').title(), size=14, weight=ft.FontWeight.BOLD, expand=2),
                            ft.TextField(
                                value=setting['config_value'],
                                expand=3,
                                on_blur=lambda e, key=setting['config_key']: self.update_setting(key, e.control.value),
                            ),
                        ],
                        spacing=10,
                    )
                )

            return ft.Container(
                content=ft.Column(
                    [
                        ft.Text("General Application Settings", size=16, weight=ft.FontWeight.BOLD),
                        ft.Divider(),
                        ft.Column(settings_controls, spacing=15, scroll=ft.ScrollMode.AUTO),
                    ],
                    spacing=10,
                ),
                padding=20,
            )
        except Exception as e:
            logger.error(f"Failed to load general settings: {e}")
            return ft.Container(content=ft.Text("Failed to load settings"))

    def build_dropdown_settings(self):
        """Build dropdown values management section"""
        try:
            # Load dropdown options by category
            query = """
                SELECT config_category, config_value, config_key, display_order
                FROM system_config
                WHERE config_type = 'dropdown'
                ORDER BY config_category, display_order
            """
            dropdown_data = [dict(row) for row in self.db_manager.execute_with_retry(query)]

            # Group by category
            categories = {}
            for item in dropdown_data:
                cat = item['config_category']
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(item)

            # Build UI for each category
            category_sections = []
            for category, items in categories.items():
                item_widgets = []
                for item in items:
                    item_widgets.append(
                        ft.Row(
                            [
                                ft.TextField(value=item['config_value'], expand=2),
                                ft.IconButton(
                                    icon=ft.Icons.DELETE,
                                    icon_color=ft.Colors.RED_700,
                                    tooltip="Delete option",
                                    on_click=lambda e, key=item['config_key']: self.delete_dropdown_option(key),
                                ),
                            ],
                            spacing=5,
                        )
                    )

                category_sections.append(
                    ft.Card(
                        content=ft.Container(
                            content=ft.Column(
                                [
                                    ft.Row(
                                        [
                                            ft.Text(category.replace('_', ' ').title(), size=14, weight=ft.FontWeight.BOLD),
                                            ft.IconButton(
                                                icon=ft.Icons.ADD,
                                                icon_color=ft.Colors.GREEN_700,
                                                tooltip="Add option",
                                                on_click=lambda e, cat=category: self.add_dropdown_option(cat),
                                            ),
                                        ],
                                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                    ),
                                    ft.Divider(),
                                    ft.Column(item_widgets, spacing=10),
                                ],
                                spacing=10,
                            ),
                            padding=15,
                        ),
                        elevation=1,
                    )
                )

            return ft.Container(
                content=ft.Column(
                    [
                        ft.Text("Manage Dropdown Options", size=16, weight=ft.FontWeight.BOLD),
                        ft.Divider(),
                        ft.Column(category_sections, spacing=15, scroll=ft.ScrollMode.AUTO),
                    ],
                    spacing=10,
                ),
                padding=20,
            )
        except Exception as e:
            logger.error(f"Failed to load dropdown settings: {e}")
            return ft.Container(content=ft.Text("Failed to load dropdown settings"))

    def build_field_settings(self):
        """Build field configuration section"""
        try:
            # Load column settings
            query = "SELECT * FROM column_settings ORDER BY display_order"
            fields = [dict(row) for row in self.db_manager.execute_with_retry(query)]

            field_rows = []
            for field in fields:
                field_rows.append(
                    ft.Card(
                        content=ft.Container(
                            content=ft.Row(
                                [
                                    ft.Column(
                                        [
                                            ft.Text(field['display_name_en'], weight=ft.FontWeight.BOLD),
                                            ft.Text(field['column_name'], size=12, color=ft.Colors.GREY_600),
                                        ],
                                        spacing=2,
                                        expand=2,
                                    ),
                                    ft.Checkbox(
                                        label="Visible",
                                        value=bool(field['is_visible']),
                                        on_change=lambda e, f=field: self.toggle_field_visibility(f['column_id'], e.control.value),
                                    ),
                                    ft.Checkbox(
                                        label="Required",
                                        value=bool(field['is_required']),
                                        on_change=lambda e, f=field: self.toggle_field_required(f['column_id'], e.control.value),
                                    ),
                                    ft.Text(field['data_type'], size=12, color=ft.Colors.BLUE_700),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            padding=15,
                        ),
                        elevation=1,
                    )
                )

            return ft.Container(
                content=ft.Column(
                    [
                        ft.Text("Field Configuration", size=16, weight=ft.FontWeight.BOLD),
                        ft.Text("Toggle field visibility and required status", size=12, color=ft.Colors.GREY_600),
                        ft.Divider(),
                        ft.Column(field_rows, spacing=10, scroll=ft.ScrollMode.AUTO),
                    ],
                    spacing=10,
                ),
                padding=20,
            )
        except Exception as e:
            logger.error(f"Failed to load field settings: {e}")
            return ft.Container(content=ft.Text("Failed to load field settings"))

    def update_setting(self, key, value):
        """Update system setting"""
        try:
            query = "UPDATE system_config SET config_value = ? WHERE config_key = ?"
            self.db_manager.execute_with_retry(query, (value, key))
            logger.info(f"Setting updated: {key} = {value}")
            self.show_success(f"Setting '{key}' updated")
        except Exception as e:
            logger.error(f"Failed to update setting: {e}")
            self.show_error(f"Failed to update setting: {str(e)}")

    def delete_dropdown_option(self, key):
        """Delete dropdown option"""
        try:
            query = "DELETE FROM system_config WHERE config_key = ?"
            self.db_manager.execute_with_retry(query, (key,))
            logger.info(f"Dropdown option deleted: {key}")
            self.show()  # Refresh view
            self.show_success("Option deleted")
        except Exception as e:
            logger.error(f"Failed to delete option: {e}")
            self.show_error(f"Failed to delete option: {str(e)}")

    def add_dropdown_option(self, category):
        """Add new dropdown option"""
        # TODO: Implement add dropdown dialog
        self.show_success(f"Add option for {category} - Coming soon")

    def toggle_field_visibility(self, column_id, visible):
        """Toggle field visibility"""
        try:
            query = "UPDATE column_settings SET is_visible = ? WHERE column_id = ?"
            self.db_manager.execute_with_retry(query, (1 if visible else 0, column_id))
            logger.info(f"Field visibility updated: {column_id} = {visible}")
            self.show_success("Field visibility updated")
        except Exception as e:
            logger.error(f"Failed to update visibility: {e}")
            self.show_error(f"Failed to update visibility: {str(e)}")

    def toggle_field_required(self, column_id, required):
        """Toggle field required status"""
        try:
            query = "UPDATE column_settings SET is_required = ? WHERE column_id = ?"
            self.db_manager.execute_with_retry(query, (1 if required else 0, column_id))
            logger.info(f"Field required updated: {column_id} = {required}")
            self.show_success("Field requirement updated")
        except Exception as e:
            logger.error(f"Failed to update required: {e}")
            self.show_error(f"Failed to update required: {str(e)}")

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
