"""
Admin Panel View for FIU Report Management System.
User management interface for administrators.
"""
import flet as ft
import asyncio
from typing import Any, Dict, List

from theme.theme_manager import theme_manager
from components.toast import show_success, show_error
from dialogs.user_dialog import show_user_dialog


ROLE_OPTIONS = ['All Roles', 'admin', 'agent', 'reporter']
STATUS_OPTIONS = ['All', 'Active', 'Inactive']


def build_admin_panel_view(page: ft.Page, app_state: Any) -> ft.Column:
    """
    Build the admin panel view for user management.

    Args:
        page: Flet page object
        app_state: Application state

    Returns:
        Admin panel column
    """
    colors = theme_manager.get_colors()

    # State
    users_data = []
    is_loading = True
    role_filter = "All Roles"
    status_filter = "All"

    # Refs
    loading_ref = ft.Ref[ft.Container]()
    table_ref = ft.Ref[ft.Container]()
    stats_ref = ft.Ref[ft.Text]()
    role_filter_ref = ft.Ref[ft.Dropdown]()
    status_filter_ref = ft.Ref[ft.Dropdown]()

    async def load_users():
        """Load users asynchronously."""
        nonlocal users_data, is_loading

        is_loading = True
        if loading_ref.current:
            loading_ref.current.visible = True
        if table_ref.current:
            table_ref.current.visible = False
        page.update()

        try:
            loop = asyncio.get_event_loop()

            def fetch_users():
                # Build query
                query = "SELECT user_id, username, full_name, role, is_active, last_login FROM users WHERE 1=1"
                params = []

                # Role filter
                if role_filter != "All Roles":
                    query += " AND role = ?"
                    params.append(role_filter)

                # Status filter
                if status_filter == "Active":
                    query += " AND is_active = 1"
                elif status_filter == "Inactive":
                    query += " AND is_active = 0"

                query += " ORDER BY user_id DESC"

                results = app_state.db_manager.execute_with_retry(query, tuple(params))

                users = []
                for row in results:
                    users.append({
                        'user_id': row[0],
                        'username': row[1],
                        'full_name': row[2],
                        'role': row[3],
                        'is_active': row[4],
                        'last_login': row[5]
                    })
                return users

            users_data = await loop.run_in_executor(None, fetch_users)
            update_table_ui()

        except Exception as e:
            print(f"Error loading users: {e}")
            show_error(page, f"Error loading users: {str(e)}")

        finally:
            is_loading = False
            if loading_ref.current:
                loading_ref.current.visible = False
            if table_ref.current:
                table_ref.current.visible = True
            page.update()

    def update_table_ui():
        """Update table with current data."""
        # Update stats
        if stats_ref.current:
            stats_ref.current.value = f"{len(users_data)} user(s)"

        # Rebuild table
        if table_ref.current:
            table_ref.current.content = build_table()

        page.update()

    def build_table() -> ft.Control:
        """Build the users data table."""
        if not users_data:
            return ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Icon(ft.Icons.PEOPLE, size=48, color=colors["text_muted"]),
                        ft.Text("No users found", color=colors["text_muted"]),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                expand=True,
                alignment=ft.alignment.center,
            )

        # Build data rows
        rows = []
        for user in users_data:
            # Status color
            status_color = colors["success"] if user['is_active'] else colors["danger"]
            status_text = "Active" if user['is_active'] else "Inactive"

            # Last login
            last_login = user.get('last_login', '')
            if last_login:
                last_login = str(last_login)[:19]  # Remove microseconds
            else:
                last_login = "Never"

            # Build action buttons
            action_buttons = [
                ft.IconButton(
                    icon=ft.Icons.EDIT,
                    icon_color=colors["primary"],
                    tooltip="Edit user",
                    on_click=lambda e, u=user: handle_edit_user(u),
                ),
            ]

            # Don't allow deleting admin user (user_id = 1)
            if user['user_id'] != 1:
                action_buttons.append(
                    ft.IconButton(
                        icon=ft.Icons.DELETE,
                        icon_color=colors["danger"],
                        tooltip="Delete user",
                        on_click=lambda e, u=user: handle_delete_user(u),
                    )
                )

            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(user['user_id']), size=12, color=colors["text_primary"])),
                        ft.DataCell(ft.Text(user['username'], size=12, color=colors["text_primary"])),
                        ft.DataCell(ft.Text(user['full_name'], size=12, color=colors["text_primary"])),
                        ft.DataCell(
                            ft.Container(
                                content=ft.Text(
                                    user['role'].capitalize(),
                                    size=11,
                                    color=ft.Colors.WHITE,
                                ),
                                bgcolor=colors["primary"],
                                border_radius=10,
                                padding=ft.padding.symmetric(horizontal=8, vertical=2),
                            )
                        ),
                        ft.DataCell(ft.Text(status_text, size=12, color=status_color)),
                        ft.DataCell(ft.Text(last_login, size=12, color=colors["text_secondary"])),
                        ft.DataCell(ft.Row(controls=action_buttons, spacing=0)),
                    ],
                )
            )

        columns = [
            ft.DataColumn(ft.Text("ID", weight=ft.FontWeight.BOLD, size=12, color=colors["text_primary"])),
            ft.DataColumn(ft.Text("Username", weight=ft.FontWeight.BOLD, size=12, color=colors["text_primary"])),
            ft.DataColumn(ft.Text("Full Name", weight=ft.FontWeight.BOLD, size=12, color=colors["text_primary"])),
            ft.DataColumn(ft.Text("Role", weight=ft.FontWeight.BOLD, size=12, color=colors["text_primary"])),
            ft.DataColumn(ft.Text("Status", weight=ft.FontWeight.BOLD, size=12, color=colors["text_primary"])),
            ft.DataColumn(ft.Text("Last Login", weight=ft.FontWeight.BOLD, size=12, color=colors["text_primary"])),
            ft.DataColumn(ft.Text("Actions", weight=ft.FontWeight.BOLD, size=12, color=colors["text_primary"])),
        ]

        return ft.DataTable(
            columns=columns,
            rows=rows,
            column_spacing=20,
            horizontal_lines=ft.BorderSide(1, colors["border"]),
            heading_row_color=colors["bg_tertiary"],
            data_row_color={
                ft.ControlState.HOVERED: colors["hover"],
            },
            border_radius=8,
        )

    def handle_role_filter_change(e):
        """Handle role filter change."""
        nonlocal role_filter
        role_filter = role_filter_ref.current.value if role_filter_ref.current else "All Roles"
        page.run_task(load_users)

    def handle_status_filter_change(e):
        """Handle status filter change."""
        nonlocal status_filter
        status_filter = status_filter_ref.current.value if status_filter_ref.current else "All"
        page.run_task(load_users)

    def handle_add_user(e):
        """Handle add user button."""
        show_user_dialog(
            page,
            app_state,
            user_data=None,
            on_save=lambda: page.run_task(load_users),
        )

    def handle_edit_user(user: Dict):
        """Handle edit user."""
        show_user_dialog(
            page,
            app_state,
            user_data=user,
            on_save=lambda: page.run_task(load_users),
        )

    def handle_delete_user(user: Dict):
        """Handle delete user."""
        def confirm_delete(e):
            confirm_dialog.open = False
            page.update()

            try:
                query = "DELETE FROM users WHERE user_id = ?"
                app_state.db_manager.execute_with_retry(query, (user['user_id'],))

                show_success(page, "User deleted successfully")
                app_state.logging_service.log_user_action("USER_DELETED", {"user_id": user['user_id']})
                page.run_task(load_users)

            except Exception as ex:
                show_error(page, f"Failed to delete user: {str(ex)}")
                app_state.logging_service.error(f"User deletion error: {ex}", exc_info=True)

        def cancel_delete(e):
            confirm_dialog.open = False
            page.update()

        confirm_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirm Deletion"),
            content=ft.Text(
                f"Are you sure you want to delete user '{user['username']}'?\n\n"
                "This will permanently remove the user from the system."
            ),
            actions=[
                ft.TextButton("Cancel", on_click=cancel_delete),
                ft.ElevatedButton(
                    "Delete",
                    bgcolor=colors["danger"],
                    color=ft.Colors.WHITE,
                    on_click=confirm_delete,
                ),
            ],
        )
        page.overlay.append(confirm_dialog)
        confirm_dialog.open = True
        page.update()

    def handle_refresh(e):
        """Refresh users."""
        page.run_task(load_users)

    # Header row
    header_row = ft.Row(
        controls=[
            ft.Text(
                "User Management",
                size=18,
                weight=ft.FontWeight.BOLD,
                color=colors["text_primary"],
            ),
            ft.Container(expand=True),
            ft.ElevatedButton(
                "Add New User",
                icon=ft.Icons.PERSON_ADD,
                on_click=handle_add_user,
                bgcolor=colors["primary"],
                color=ft.Colors.WHITE,
            ),
        ],
        spacing=12,
    )

    # Filter row
    filter_row = ft.Row(
        controls=[
            ft.Text("Role:", color=colors["text_secondary"]),
            ft.Dropdown(
                ref=role_filter_ref,
                value="All Roles",
                options=[ft.dropdown.Option(key=r, text=r) for r in ROLE_OPTIONS],
                width=150,
                text_size=13,
                on_change=handle_role_filter_change,
            ),
            ft.Text("Status:", color=colors["text_secondary"]),
            ft.Dropdown(
                ref=status_filter_ref,
                value="All",
                options=[ft.dropdown.Option(key=s, text=s) for s in STATUS_OPTIONS],
                width=120,
                text_size=13,
                on_change=handle_status_filter_change,
            ),
            ft.IconButton(
                icon=ft.Icons.REFRESH,
                icon_color=colors["text_secondary"],
                tooltip="Refresh",
                on_click=handle_refresh,
            ),
        ],
        spacing=12,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # Stats row
    stats_row = ft.Row(
        controls=[
            ft.Text(
                ref=stats_ref,
                value="0 user(s)",
                size=13,
                color=colors["text_secondary"],
            ),
        ],
    )

    # Loading indicator
    loading_container = ft.Container(
        ref=loading_ref,
        content=ft.Column(
            controls=[
                ft.ProgressRing(width=32, height=32, color=colors["primary"]),
                ft.Text("Loading users...", color=colors["text_secondary"]),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=8,
        ),
        expand=True,
        alignment=ft.alignment.center,
        visible=True,
    )

    # Table container
    table_container = ft.Container(
        ref=table_ref,
        content=ft.Text("Loading...", color=colors["text_muted"]),
        expand=True,
        visible=False,
    )

    # Trigger initial load
    page.run_task(load_users)

    return ft.Column(
        controls=[
            header_row,
            ft.Container(height=16),
            filter_row,
            ft.Container(height=8),
            stats_row,
            ft.Container(height=8),
            ft.Container(
                content=ft.Stack(
                    controls=[
                        loading_container,
                        ft.Container(
                            content=ft.Column(
                                controls=[table_container],
                                scroll=ft.ScrollMode.ALWAYS,
                                expand=True,
                            ),
                            expand=True,
                        ),
                    ],
                ),
                expand=True,
                border=ft.border.all(1, colors["border"]),
                border_radius=8,
                bgcolor=colors["card_bg"],
            ),
        ],
        spacing=0,
        expand=True,
    )
