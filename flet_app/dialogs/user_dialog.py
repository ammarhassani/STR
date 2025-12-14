"""
User Dialog for FIU Report Management System.
Dialog for creating and editing users.
"""
import flet as ft
from typing import Optional, Any, Callable

from theme.theme_manager import theme_manager


def show_user_dialog(
    page: ft.Page,
    app_state: Any,
    user_data: Optional[dict] = None,
    on_save: Optional[Callable[[], None]] = None,
):
    """
    Show the user dialog.

    Args:
        page: Flet page object
        app_state: Application state with services
        user_data: Existing user data for editing (None for new user)
        on_save: Callback when user is saved
    """
    colors = theme_manager.get_colors()
    is_edit_mode = user_data is not None

    db_manager = app_state.db_manager
    logging_service = app_state.logging_service
    auth_service = app_state.auth_service

    # Form refs
    username_ref = ft.Ref[ft.TextField]()
    password_ref = ft.Ref[ft.TextField]()
    fullname_ref = ft.Ref[ft.TextField]()
    role_ref = ft.Ref[ft.Dropdown]()
    status_ref = ft.Ref[ft.Dropdown]()

    def validate_form() -> tuple[bool, str]:
        """Validate form data."""
        username = username_ref.current.value.strip() if username_ref.current else ""
        password = password_ref.current.value if password_ref.current else ""
        fullname = fullname_ref.current.value.strip() if fullname_ref.current else ""

        if not username:
            return False, "Username is required"

        if not is_edit_mode and not password:
            return False, "Password is required for new users"

        if not fullname:
            return False, "Full name is required"

        # Check if username already exists (for new users)
        if not is_edit_mode:
            try:
                check_query = "SELECT COUNT(*) FROM users WHERE username = ?"
                result = db_manager.execute_with_retry(check_query, (username,))
                if result and result[0][0] > 0:
                    return False, f"Username '{username}' already exists"
            except Exception as e:
                return False, f"Error checking username: {str(e)}"

        return True, ""

    def save_user(e):
        """Save user data."""
        is_valid, error = validate_form()
        if not is_valid:
            show_error(error)
            return

        username = username_ref.current.value.strip()
        password = password_ref.current.value
        fullname = fullname_ref.current.value.strip()
        role = role_ref.current.value if role_ref.current else "reporter"
        is_active = 1 if status_ref.current.value == "Active" else 0

        try:
            if is_edit_mode:
                # Update existing user
                user_id = user_data['user_id']

                if password:
                    # Hash the new password
                    hashed_password = auth_service.hash_password(password) if auth_service else password
                    query = """
                        UPDATE users
                        SET password = ?, full_name = ?, role = ?, is_active = ?,
                            updated_at = datetime('now'), updated_by = 'admin'
                        WHERE user_id = ?
                    """
                    db_manager.execute_with_retry(query, (hashed_password, fullname, role, is_active, user_id))
                else:
                    # Update without changing password
                    query = """
                        UPDATE users
                        SET full_name = ?, role = ?, is_active = ?,
                            updated_at = datetime('now'), updated_by = 'admin'
                        WHERE user_id = ?
                    """
                    db_manager.execute_with_retry(query, (fullname, role, is_active, user_id))

                show_success("User updated successfully")
                logging_service.log_user_action("USER_UPDATED", {"user_id": user_id})

            else:
                # Create new user - hash password
                hashed_password = auth_service.hash_password(password) if auth_service else password
                query = """
                    INSERT INTO users (username, password, full_name, role, is_active,
                                     created_at, created_by)
                    VALUES (?, ?, ?, ?, ?, datetime('now'), 'admin')
                """
                db_manager.execute_with_retry(query, (username, hashed_password, fullname, role, is_active))

                show_success("User created successfully")
                logging_service.log_user_action("USER_CREATED")

            dialog.open = False
            page.update()
            if on_save:
                on_save()

        except Exception as ex:
            show_error(f"Failed to save user: {str(ex)}")
            logging_service.error(f"User save error: {ex}", exc_info=True)

    def show_error(message: str):
        """Show error snackbar."""
        page.snack_bar = ft.SnackBar(
            content=ft.Text(message),
            bgcolor=colors["danger"],
        )
        page.snack_bar.open = True
        page.update()

    def show_success(message: str):
        """Show success snackbar."""
        page.snack_bar = ft.SnackBar(
            content=ft.Text(message),
            bgcolor=colors["success"],
        )
        page.snack_bar.open = True
        page.update()

    def close_dialog(e):
        """Close the dialog."""
        dialog.open = False
        page.update()

    # Build form content
    dialog_content = ft.Container(
        content=ft.Column(
            controls=[
                # Header
                ft.Text(
                    "Edit User" if is_edit_mode else "Add New User",
                    size=18,
                    weight=ft.FontWeight.BOLD,
                    color=colors["text_primary"],
                ),
                ft.Divider(color=colors["border"]),

                # Form fields
                ft.Column(
                    controls=[
                        ft.Text("Username *", size=12, weight=ft.FontWeight.W_500, color=colors["text_secondary"]),
                        ft.TextField(
                            ref=username_ref,
                            value=user_data.get('username', '') if is_edit_mode else "",
                            hint_text="Enter username",
                            read_only=is_edit_mode,
                            text_size=13,
                            border_radius=8,
                        ),
                    ],
                    spacing=4,
                ),

                ft.Column(
                    controls=[
                        ft.Text(
                            "Password" + ("" if is_edit_mode else " *"),
                            size=12,
                            weight=ft.FontWeight.W_500,
                            color=colors["text_secondary"],
                        ),
                        ft.TextField(
                            ref=password_ref,
                            hint_text="Leave blank to keep current password" if is_edit_mode else "Enter password",
                            password=True,
                            can_reveal_password=True,
                            text_size=13,
                            border_radius=8,
                        ),
                    ],
                    spacing=4,
                ),

                ft.Column(
                    controls=[
                        ft.Text("Full Name *", size=12, weight=ft.FontWeight.W_500, color=colors["text_secondary"]),
                        ft.TextField(
                            ref=fullname_ref,
                            value=user_data.get('full_name', '') if is_edit_mode else "",
                            hint_text="Enter full name",
                            text_size=13,
                            border_radius=8,
                        ),
                    ],
                    spacing=4,
                ),

                ft.Column(
                    controls=[
                        ft.Text("Role *", size=12, weight=ft.FontWeight.W_500, color=colors["text_secondary"]),
                        ft.Dropdown(
                            ref=role_ref,
                            value=user_data.get('role', 'reporter') if is_edit_mode else "reporter",
                            options=[
                                ft.dropdown.Option("admin"),
                                ft.dropdown.Option("agent"),
                                ft.dropdown.Option("reporter"),
                            ],
                            text_size=13,
                            border_radius=8,
                        ),
                    ],
                    spacing=4,
                ),

                ft.Column(
                    controls=[
                        ft.Text("Status", size=12, weight=ft.FontWeight.W_500, color=colors["text_secondary"]),
                        ft.Dropdown(
                            ref=status_ref,
                            value="Active" if (not is_edit_mode or user_data.get('is_active', 1)) else "Inactive",
                            options=[
                                ft.dropdown.Option("Active"),
                                ft.dropdown.Option("Inactive"),
                            ],
                            text_size=13,
                            border_radius=8,
                        ),
                    ],
                    spacing=4,
                ),

                ft.Text("* Required fields", size=11, color=colors["text_muted"], italic=True),

                # Buttons
                ft.Row(
                    controls=[
                        ft.Container(expand=True),
                        ft.TextButton("Cancel", on_click=close_dialog),
                        ft.ElevatedButton(
                            "Save",
                            icon=ft.Icons.SAVE,
                            bgcolor=colors["primary"],
                            color=ft.Colors.WHITE,
                            on_click=save_user,
                        ),
                    ],
                    spacing=8,
                ),
            ],
            spacing=16,
        ),
        width=450,
        padding=24,
    )

    # Create dialog
    dialog = ft.AlertDialog(
        modal=True,
        content=dialog_content,
        shape=ft.RoundedRectangleBorder(radius=12),
    )

    # Show dialog
    page.overlay.append(dialog)
    dialog.open = True
    page.update()
