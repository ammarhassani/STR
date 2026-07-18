"""
User Dialog for FIU Report Management System.

Two-way handshake (#1): an admin creates a user by USER ID + role only. The
user sets their own full name + password at first login, so the admin never
knows an FIU reporter's password. Admins here manage the ID, role, and active
status — and can "Reset password" (re-arm the handshake) but never set one.
"""
import flet as ft
from components.searchable_dropdown import searchable_dropdown
from typing import Optional, Any, Callable

from theme.theme_manager import theme_manager
from components.app_button import app_button


def show_user_dialog(
    page: ft.Page,
    app_state: Any,
    user_data: Optional[dict] = None,
    on_save: Optional[Callable[[], None]] = None,
):
    colors = theme_manager.get_colors()
    is_edit_mode = user_data is not None

    db_manager = app_state.db_manager
    logging_service = app_state.logging_service
    auth_service = app_state.auth_service

    username_ref = ft.Ref[ft.TextField]()
    role_ref = ft.Ref[ft.Dropdown]()
    status_ref = ft.Ref[ft.Dropdown]()

    is_pending = bool(user_data.get('onboarding_pending')) if is_edit_mode else False

    def show_error(message: str):
        page.snack_bar = ft.SnackBar(content=ft.Text(message), bgcolor=colors["danger"])
        page.snack_bar.open = True
        page.update()

    def show_success(message: str):
        page.snack_bar = ft.SnackBar(content=ft.Text(message), bgcolor=colors["success"])
        page.snack_bar.open = True
        page.update()

    def close_dialog(e):
        dialog.open = False
        page.update()

    def save_user(e):
        role = role_ref.current.value if role_ref.current else "reporter"
        is_active = 1 if (status_ref.current and status_ref.current.value == "Active") else 0
        try:
            if is_edit_mode:
                ok, msg = auth_service.update_user(
                    user_data['user_id'], role=role, is_active=is_active)
            else:
                username = username_ref.current.value.strip() if username_ref.current else ""
                if not username:
                    show_error("User ID is required"); return
                # ID + role only — the user self-registers name + password
                ok, msg = auth_service.create_pending_user(username, role)
                if ok and not is_active:
                    row = db_manager.execute_with_retry(
                        "SELECT user_id FROM users WHERE username = ? COLLATE NOCASE", (username,))
                    if row:
                        auth_service.update_user(row[0][0], is_active=0)
            if not ok:
                show_error(msg); return
            show_success(msg)
            dialog.open = False
            page.update()
            if on_save:
                on_save()
        except Exception as ex:
            show_error(f"Failed to save user: {str(ex)}")
            logging_service.error(f"User save error: {ex}", exc_info=True)

    def reset_password(e):
        """Re-arm the handshake so the user re-registers a new password."""
        try:
            ok, msg = auth_service.reset_onboarding(user_data['username'])
            if not ok:
                show_error(msg); return
            show_success(msg)
            dialog.open = False
            page.update()
            if on_save:
                on_save()
        except Exception as ex:
            show_error(f"Reset failed: {str(ex)}")

    # ---- form fields ----
    fields = [
        ft.Text("Edit User" if is_edit_mode else "Add New User",
                size=18, weight=ft.FontWeight.BOLD, color=colors["text_primary"]),
        ft.Divider(color=colors["border"]),
        ft.Column(
            controls=[
                ft.Text("User ID *", size=12, weight=ft.FontWeight.W_500, color=colors["text_secondary"]),
                ft.TextField(
                    ref=username_ref,
                    value=user_data.get('username', '') if is_edit_mode else "",
                    hint_text="e.g. reporter7 (the user logs in with this)",
                    read_only=is_edit_mode,
                    text_size=13, border_radius=4,
                ),
            ],
            spacing=4,
        ),
    ]

    # In edit mode, show the user-owned full name (read-only) + registration state.
    if is_edit_mode:
        fields.append(
            ft.Column(
                controls=[
                    ft.Text("Full Name (set by the user)", size=12, weight=ft.FontWeight.W_500,
                            color=colors["text_secondary"]),
                    ft.TextField(value=user_data.get('full_name') or "—", read_only=True,
                                 text_size=13, border_radius=4, bgcolor=colors.get("bg_tertiary")),
                ],
                spacing=4,
            )
        )
        fields.append(
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.INFO_OUTLINE, size=14,
                            color=colors["warning"] if is_pending else colors["success"]),
                    ft.Text("Awaiting first-login registration" if is_pending
                            else "Registered — password is set by the user",
                            size=12, color=colors["text_secondary"]),
                ], spacing=6),
                padding=ft.padding.symmetric(6, 8), border_radius=4,
                bgcolor=ft.Colors.with_opacity(0.06, colors["warning"] if is_pending else colors["success"]),
            )
        )

    fields.append(
        ft.Column(
            controls=[
                ft.Text("Role *", size=12, weight=ft.FontWeight.W_500, color=colors["text_secondary"]),
                searchable_dropdown(
                    ref=role_ref,
                    value=user_data.get('role', 'reporter') if is_edit_mode else "reporter",
                    options=[
                        ft.dropdown.Option(key="admin", text="admin"),
                        ft.dropdown.Option(key="supervisor", text="supervisor"),
                        ft.dropdown.Option(key="agent", text="agent"),
                        ft.dropdown.Option(key="reporter", text="reporter"),
                    ],
                    text_size=13, border_radius=4,
                ),
            ],
            spacing=4,
        )
    )
    fields.append(
        ft.Column(
            controls=[
                ft.Text("Status", size=12, weight=ft.FontWeight.W_500, color=colors["text_secondary"]),
                searchable_dropdown(
                    ref=status_ref,
                    value="Active" if (not is_edit_mode or user_data.get('is_active', 1)) else "Inactive",
                    options=[
                        ft.dropdown.Option(key="Active", text="Active"),
                        ft.dropdown.Option(key="Inactive", text="Inactive"),
                    ],
                    text_size=13, border_radius=4,
                ),
            ],
            spacing=4,
        )
    )

    if not is_edit_mode:
        fields.append(
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.HANDSHAKE, size=16, color=colors["primary"]),
                    ft.Text("The user sets their own name and password at first login.",
                            size=12, color=colors["text_secondary"], expand=True),
                ], spacing=8),
                padding=ft.padding.symmetric(8, 10), border_radius=4,
                bgcolor=ft.Colors.with_opacity(0.06, colors["primary"]),
            )
        )

    # buttons — edit mode gets a "Reset password" (re-onboard) action
    button_row = [ft.Container(expand=True)]
    if is_edit_mode and not is_pending:
        button_row.append(
            ft.TextButton("Reset password", icon=ft.Icons.LOCK_RESET, on_click=reset_password))
    button_row += [
        ft.TextButton("Cancel", on_click=close_dialog),
        app_button("Save", icon=ft.Icons.SAVE, on_click=save_user, variant="primary"),
    ]
    fields.append(ft.Row(controls=button_row, spacing=8))

    dialog_content = ft.Container(
        content=ft.Column(controls=fields, spacing=16, scroll=ft.ScrollMode.AUTO),
        width=450, padding=24,
    )
    dialog = ft.AlertDialog(
        modal=True, content=dialog_content, shape=ft.RoundedRectangleBorder(radius=12))
    page.overlay.append(dialog)
    dialog.open = True
    page.update()
