"""
User Profile Dialog for FIU Report Management System.
View and edit current user profile information.
"""
import flet as ft
import asyncio
from typing import Any
from datetime import datetime

from theme.theme_manager import theme_manager
from components.toast import show_success, show_error
from dialogs.change_password_dialog import show_change_password_dialog


def show_user_profile_dialog(page: ft.Page, app_state: Any):
    """
    Show the user profile dialog.

    Args:
        page: Flet page object
        app_state: Application state
    """
    colors = theme_manager.get_colors()
    current_user = app_state.auth_service.get_current_user()

    if not current_user:
        show_error(page, "No user is logged in")
        return

    # State for stats
    stats = {
        'login_count': 0,
        'reports_created': 0,
        'reports_edited': 0,
        'last_action': 'N/A',
        'recent_activity': [],
    }

    # Input fields
    full_name_input = ft.TextField(
        label="Full Name",
        value=current_user.get('full_name', ''),
    )

    username_display = ft.TextField(
        label="Username",
        value=current_user.get('username', ''),
        read_only=True,
        bgcolor=colors["bg_tertiary"],
    )

    role_display = ft.TextField(
        label="Role",
        value=current_user.get('role', '').title(),
        read_only=True,
        bgcolor=colors["bg_tertiary"],
    )

    # Stats labels
    created_at_text = ft.Text("Loading...", size=12, color=colors["text_secondary"])
    last_login_text = ft.Text("Loading...", size=12, color=colors["text_secondary"])
    login_count_text = ft.Text("Loading...", size=12, color=colors["text_secondary"])
    reports_created_text = ft.Text("Loading...", size=12, color=colors["text_secondary"])
    reports_edited_text = ft.Text("Loading...", size=12, color=colors["text_secondary"])
    last_action_text = ft.Text("Loading...", size=12, color=colors["text_secondary"])
    recent_activity_text = ft.Text("Loading recent activity...", size=11, color=colors["text_muted"])
    password_changed_text = ft.Text("Last changed: Loading...", size=11, color=colors["text_muted"])

    async def load_stats():
        """Load user statistics."""
        try:
            loop = asyncio.get_event_loop()
            user_id = current_user['user_id']
            username = current_user['username']

            def fetch_stats():
                result = {}

                # Account created
                created_at = current_user.get('created_at', 'Unknown')
                if created_at and created_at != 'Unknown':
                    try:
                        created_dt = datetime.fromisoformat(created_at)
                        result['created_at'] = created_dt.strftime('%Y-%m-%d %H:%M')
                    except:
                        result['created_at'] = created_at
                else:
                    result['created_at'] = 'Unknown'

                # Last login
                last_login = current_user.get('last_login', 'Never')
                if last_login and last_login != 'Never':
                    try:
                        login_dt = datetime.fromisoformat(last_login)
                        result['last_login'] = login_dt.strftime('%Y-%m-%d %H:%M')
                    except:
                        result['last_login'] = last_login
                else:
                    result['last_login'] = 'Never'

                # Login count
                try:
                    login_results = app_state.db_manager.execute_with_retry(
                        "SELECT COUNT(*) FROM session_log WHERE user_id = ?",
                        (user_id,)
                    )
                    result['login_count'] = login_results[0][0] if login_results else 0
                except:
                    result['login_count'] = 0

                # Reports created
                try:
                    reports_results = app_state.db_manager.execute_with_retry(
                        "SELECT COUNT(*) FROM reports WHERE created_by = ? AND is_deleted = 0",
                        (username,)
                    )
                    result['reports_created'] = reports_results[0][0] if reports_results else 0
                except:
                    result['reports_created'] = 0

                # Reports edited
                try:
                    edits_results = app_state.db_manager.execute_with_retry(
                        """SELECT COUNT(DISTINCT report_id) FROM reports
                           WHERE updated_by = ? AND updated_by != created_by AND is_deleted = 0""",
                        (username,)
                    )
                    result['reports_edited'] = edits_results[0][0] if edits_results else 0
                except:
                    result['reports_edited'] = 0

                # Recent activity
                try:
                    recent_results = app_state.db_manager.execute_with_retry(
                        """SELECT action_type, created_at FROM audit_log
                           WHERE user_id = ? ORDER BY created_at DESC LIMIT 10""",
                        (user_id,)
                    )
                    if recent_results:
                        activities = []
                        for action, timestamp in recent_results:
                            try:
                                ts_dt = datetime.fromisoformat(timestamp)
                                ts_str = ts_dt.strftime('%Y-%m-%d %H:%M')
                            except:
                                ts_str = timestamp
                            activities.append(f"[{ts_str}] {action}")
                        result['recent_activity'] = activities
                        result['last_action'] = recent_results[0][1] if recent_results else 'N/A'
                    else:
                        result['recent_activity'] = ["No recent activity"]
                        result['last_action'] = 'N/A'
                except:
                    result['recent_activity'] = ["Error loading activity"]
                    result['last_action'] = 'N/A'

                # Password last changed
                updated_at = current_user.get('updated_at', 'Unknown')
                if updated_at and updated_at != 'Unknown':
                    try:
                        updated_dt = datetime.fromisoformat(updated_at)
                        result['password_changed'] = updated_dt.strftime('%Y-%m-%d %H:%M')
                    except:
                        result['password_changed'] = updated_at
                else:
                    result['password_changed'] = 'Unknown'

                return result

            data = await loop.run_in_executor(None, fetch_stats)

            # Update UI
            created_at_text.value = data.get('created_at', 'Unknown')
            last_login_text.value = data.get('last_login', 'Never')
            login_count_text.value = str(data.get('login_count', 0))
            reports_created_text.value = str(data.get('reports_created', 0))
            reports_edited_text.value = str(data.get('reports_edited', 0))

            last_action = data.get('last_action', 'N/A')
            if last_action != 'N/A':
                try:
                    la_dt = datetime.fromisoformat(last_action)
                    last_action_text.value = la_dt.strftime('%Y-%m-%d %H:%M')
                except:
                    last_action_text.value = last_action
            else:
                last_action_text.value = 'N/A'

            activities = data.get('recent_activity', [])
            recent_activity_text.value = '\n'.join(activities)

            password_changed_text.value = f"Last changed: {data.get('password_changed', 'Unknown')}"

            page.update()

        except Exception as e:
            print(f"Error loading stats: {e}")

    def create_stat_row(label: str, value_widget: ft.Control) -> ft.Row:
        """Create a statistics row."""
        return ft.Row(
            controls=[
                ft.Text(label, size=12, color=colors["text_secondary"], width=120),
                value_widget,
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    # Profile Tab
    profile_tab = ft.Tab(
        text="Profile",
        icon=ft.Icons.PERSON,
        content=ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("Basic Information", weight=ft.FontWeight.BOLD, size=14, color=colors["text_primary"]),
                    ft.Container(height=8),
                    full_name_input,
                    ft.Container(height=8),
                    username_display,
                    ft.Container(height=8),
                    role_display,
                ],
                scroll=ft.ScrollMode.AUTO,
            ),
            padding=20,
        ),
    )

    # Activity Tab
    activity_tab = ft.Tab(
        text="Activity",
        icon=ft.Icons.HISTORY,
        content=ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("Account Information", weight=ft.FontWeight.BOLD, size=14, color=colors["text_primary"]),
                    ft.Container(height=8),
                    create_stat_row("Account Created:", created_at_text),
                    create_stat_row("Last Login:", last_login_text),
                    create_stat_row("Total Logins:", login_count_text),
                    ft.Container(height=16),
                    ft.Text("Activity Statistics", weight=ft.FontWeight.BOLD, size=14, color=colors["text_primary"]),
                    ft.Container(height=8),
                    create_stat_row("Reports Created:", reports_created_text),
                    create_stat_row("Reports Edited:", reports_edited_text),
                    create_stat_row("Last Activity:", last_action_text),
                    ft.Container(height=16),
                    ft.Text("Recent Activity", weight=ft.FontWeight.BOLD, size=14, color=colors["text_primary"]),
                    ft.Container(height=8),
                    ft.Container(
                        content=recent_activity_text,
                        bgcolor=colors["bg_tertiary"],
                        padding=10,
                        border_radius=4,
                        height=150,
                    ),
                ],
                scroll=ft.ScrollMode.AUTO,
            ),
            padding=20,
        ),
    )

    # Security Tab
    def handle_change_password(e):
        show_change_password_dialog(page, app_state)

    security_tab = ft.Tab(
        text="Security",
        icon=ft.Icons.SECURITY,
        content=ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("Password & Authentication", weight=ft.FontWeight.BOLD, size=14, color=colors["text_primary"]),
                    ft.Container(height=8),
                    ft.Text(
                        "Keep your account secure by using a strong password and changing it regularly.",
                        size=12,
                        color=colors["text_secondary"],
                    ),
                    ft.Container(height=12),
                    ft.ElevatedButton(
                        "Change Password",
                        icon=ft.Icons.KEY,
                        on_click=handle_change_password,
                    ),
                    ft.Container(height=4),
                    password_changed_text,
                    ft.Container(height=24),
                    ft.Text("Session Information", weight=ft.FontWeight.BOLD, size=14, color=colors["text_primary"]),
                    ft.Container(height=8),
                    ft.Text(
                        f"Logged in as: {current_user['username']}\n"
                        f"Role: {current_user['role'].title()}\n"
                        f"Session started: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                        size=12,
                        color=colors["text_secondary"],
                    ),
                ],
                scroll=ft.ScrollMode.AUTO,
            ),
            padding=20,
        ),
    )

    def handle_save(e):
        """Save profile changes."""
        new_name = full_name_input.value.strip() if full_name_input.value else ""

        if not new_name:
            show_error(page, "Full name is required.")
            return

        try:
            app_state.db_manager.execute_with_retry(
                """UPDATE users SET full_name = ?, updated_at = ?, updated_by = ?
                   WHERE user_id = ?""",
                (new_name, datetime.now().isoformat(), current_user['username'], current_user['user_id'])
            )

            # Update current user object
            current_user['full_name'] = new_name

            if app_state.logging_service:
                app_state.logging_service.log_user_action("PROFILE_UPDATED", {'user_id': current_user['user_id']})

            dialog.open = False
            page.update()
            show_success(page, "Profile updated successfully!")

        except Exception as ex:
            show_error(page, f"Error saving profile: {str(ex)}")

    def close_dialog(e):
        dialog.open = False
        page.update()

    # Avatar
    initial = current_user['full_name'][0].upper() if current_user.get('full_name') else "U"

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Row(
            controls=[
                ft.Container(
                    content=ft.Text(initial, color=ft.Colors.WHITE, size=24, weight=ft.FontWeight.BOLD),
                    width=50,
                    height=50,
                    border_radius=25,
                    bgcolor=colors["primary"],
                    alignment=ft.alignment.center,
                ),
                ft.Container(width=12),
                ft.Column(
                    controls=[
                        ft.Text(current_user.get('full_name', 'User'), size=16, weight=ft.FontWeight.BOLD),
                        ft.Text(f"@{current_user.get('username', '')} - {current_user.get('role', '').title()}", size=12, color=colors["text_secondary"]),
                    ],
                    spacing=2,
                ),
            ],
        ),
        content=ft.Container(
            content=ft.Tabs(
                tabs=[profile_tab, activity_tab, security_tab],
                selected_index=0,
                animation_duration=200,
            ),
            width=500,
            height=400,
        ),
        actions=[
            ft.TextButton("Cancel", on_click=close_dialog),
            ft.ElevatedButton(
                "Save Changes",
                icon=ft.Icons.SAVE,
                bgcolor=colors["primary"],
                color=ft.Colors.WHITE,
                on_click=handle_save,
            ),
        ],
    )

    page.overlay.append(dialog)
    dialog.open = True
    page.update()

    # Load stats asynchronously
    page.run_task(load_stats)
