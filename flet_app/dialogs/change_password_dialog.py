"""
Change Password Dialog for FIU Report Management System.
Allows users to change their password.
"""
import flet as ft
from typing import Any

from theme.theme_manager import theme_manager
from components.toast import show_success, show_error


def show_change_password_dialog(page: ft.Page, app_state: Any):
    """
    Show the change password dialog.

    Args:
        page: Flet page object
        app_state: Application state
    """
    colors = theme_manager.get_colors()
    current_user = app_state.auth_service.get_current_user()

    if not current_user:
        show_error(page, "No user is logged in")
        return

    # Input fields
    current_password = ft.TextField(
        label="Current Password",
        password=True,
        can_reveal_password=True,
        autofocus=True,
    )

    new_password = ft.TextField(
        label="New Password",
        password=True,
        can_reveal_password=True,
    )

    confirm_password = ft.TextField(
        label="Confirm New Password",
        password=True,
        can_reveal_password=True,
    )

    strength_text = ft.Text("", size=11)

    def check_strength(e):
        """Check password strength."""
        pwd = new_password.value or ""
        if not pwd:
            strength_text.value = ""
            strength_text.color = colors["text_muted"]
            page.update()
            return

        strength = 0
        feedback = []

        if len(pwd) >= 8:
            strength += 1
        else:
            feedback.append("too short")

        if any(c.isupper() for c in pwd):
            strength += 1
        else:
            feedback.append("add uppercase")

        if any(c.islower() for c in pwd):
            strength += 1
        else:
            feedback.append("add lowercase")

        if any(c.isdigit() for c in pwd):
            strength += 1
        else:
            feedback.append("add number")

        if strength == 4:
            strength_text.value = "Strong password"
            strength_text.color = colors["success"]
        elif strength >= 2:
            strength_text.value = f"Weak: {', '.join(feedback)}"
            strength_text.color = colors["warning"]
        else:
            strength_text.value = f"Too weak: {', '.join(feedback)}"
            strength_text.color = colors["danger"]

        page.update()

    new_password.on_change = check_strength

    def validate() -> tuple:
        """Validate inputs."""
        cur = current_password.value.strip() if current_password.value else ""
        new = new_password.value.strip() if new_password.value else ""
        confirm = confirm_password.value.strip() if confirm_password.value else ""

        if not cur:
            return False, "Please enter your current password."
        if not new:
            return False, "Please enter a new password."
        if not confirm:
            return False, "Please confirm your new password."
        if len(new) < 8:
            return False, "Password must be at least 8 characters."
        if not any(c.isupper() for c in new):
            return False, "Password must contain at least one uppercase letter."
        if not any(c.islower() for c in new):
            return False, "Password must contain at least one lowercase letter."
        if not any(c.isdigit() for c in new):
            return False, "Password must contain at least one number."
        if new != confirm:
            return False, "New passwords do not match."
        if cur == new:
            return False, "New password must be different from current password."

        return True, ""

    def handle_change(e):
        """Handle password change."""
        is_valid, error_msg = validate()
        if not is_valid:
            show_error(page, error_msg)
            return

        try:
            # Verify current password
            if not app_state.auth_service.verify_password(
                current_user['username'],
                current_password.value.strip()
            ):
                show_error(page, "Current password is incorrect.")
                current_password.value = ""
                page.update()
                return

            # Change password
            success = app_state.auth_service.change_password(
                current_user['user_id'],
                new_password.value.strip()
            )

            if success:
                dialog.open = False
                page.update()
                show_success(page, "Password changed successfully!")
            else:
                show_error(page, "Failed to change password. Please try again.")

        except Exception as ex:
            show_error(page, f"Error: {str(ex)}")

    def close_dialog(e):
        dialog.open = False
        page.update()

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Change Password"),
        content=ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(
                        "Please enter your current password and choose a new password.",
                        size=12,
                        color=colors["text_secondary"],
                    ),
                    ft.Container(height=12),
                    current_password,
                    ft.Container(height=8),
                    new_password,
                    strength_text,
                    ft.Container(height=8),
                    confirm_password,
                    ft.Container(height=12),
                    ft.Container(
                        content=ft.Text(
                            "Password requirements:\n"
                            "- Minimum 8 characters\n"
                            "- At least one uppercase letter\n"
                            "- At least one lowercase letter\n"
                            "- At least one number",
                            size=11,
                            color=colors["text_muted"],
                        ),
                        bgcolor=colors["bg_tertiary"],
                        padding=10,
                        border_radius=4,
                    ),
                ],
                tight=True,
                spacing=4,
            ),
            width=400,
        ),
        actions=[
            ft.TextButton("Cancel", on_click=close_dialog),
            ft.ElevatedButton(
                "Change Password",
                icon=ft.Icons.KEY,
                bgcolor=colors["primary"],
                color=ft.Colors.WHITE,
                on_click=handle_change,
            ),
        ],
    )

    page.overlay.append(dialog)
    dialog.open = True
    page.update()
