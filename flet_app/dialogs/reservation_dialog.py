"""
Report Number Reservation Management Dialog for Admin.
Allows admins to monitor and manage report number reservations.
"""
import flet as ft
import asyncio
from typing import Any
from datetime import datetime

from theme.theme_manager import theme_manager
from components.toast import show_success, show_error, show_warning


def show_reservation_dialog(page: ft.Page, app_state: Any):
    """
    Show the reservation management dialog.

    Args:
        page: Flet page object
        app_state: Application state
    """
    colors = theme_manager.get_colors()

    # State
    reservations_data = []
    activity_data = []
    selected_reservation = None

    # Controls
    reservations_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Report Number", weight=ft.FontWeight.BOLD, size=12)),
            ft.DataColumn(ft.Text("Serial #", weight=ft.FontWeight.BOLD, size=12)),
            ft.DataColumn(ft.Text("Reserved By", weight=ft.FontWeight.BOLD, size=12)),
            ft.DataColumn(ft.Text("Reserved At", weight=ft.FontWeight.BOLD, size=12)),
            ft.DataColumn(ft.Text("Expires At", weight=ft.FontWeight.BOLD, size=12)),
            ft.DataColumn(ft.Text("Status", weight=ft.FontWeight.BOLD, size=12)),
        ],
        rows=[],
        border=ft.border.all(1, colors["border"]),
        border_radius=6,
        horizontal_lines=ft.BorderSide(1, colors["border"]),
        heading_row_color=colors["bg_tertiary"],
        column_spacing=20,
    )

    activity_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Report Number", weight=ft.FontWeight.BOLD, size=12)),
            ft.DataColumn(ft.Text("User", weight=ft.FontWeight.BOLD, size=12)),
            ft.DataColumn(ft.Text("Action", weight=ft.FontWeight.BOLD, size=12)),
            ft.DataColumn(ft.Text("Timestamp", weight=ft.FontWeight.BOLD, size=12)),
        ],
        rows=[],
        border=ft.border.all(1, colors["border"]),
        border_radius=6,
        horizontal_lines=ft.BorderSide(1, colors["border"]),
        heading_row_color=colors["bg_tertiary"],
        column_spacing=20,
    )

    stats_text = ft.Text("Loading statistics...", size=12, color=colors["text_secondary"])

    # Settings controls
    max_concurrent_input = ft.TextField(
        label="Max Concurrent Reservations (System-Wide)",
        value="10",
        keyboard_type=ft.KeyboardType.NUMBER,
        width=200,
    )

    max_per_user_input = ft.TextField(
        label="Max Reservations Per User",
        value="1",
        keyboard_type=ft.KeyboardType.NUMBER,
        width=200,
    )

    timeout_input = ft.TextField(
        label="Reservation Timeout (minutes)",
        value="5",
        keyboard_type=ft.KeyboardType.NUMBER,
        width=200,
    )

    # Action buttons
    release_btn = ft.ElevatedButton(
        "Release Selected",
        icon=ft.Icons.CANCEL,
        disabled=True,
        bgcolor=colors["warning"],
        color=ft.Colors.WHITE,
    )

    release_user_btn = ft.ElevatedButton(
        "Release All for User",
        icon=ft.Icons.PERSON_REMOVE,
        disabled=True,
    )

    async def load_data():
        """Load all data."""
        await asyncio.gather(
            load_reservations(),
            load_statistics(),
            load_activity(),
            load_settings(),
        )

    async def load_reservations():
        """Load active reservations."""
        nonlocal reservations_data
        try:
            def fetch():
                query = """
                    SELECT report_number, serial_number, reserved_by,
                           reserved_at, expires_at, is_used
                    FROM report_number_reservations
                    WHERE is_used = 0
                    ORDER BY reserved_at DESC
                """
                return app_state.db_manager.execute_with_retry(query)

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, fetch)

            reservations_data = result or []
            now = datetime.now()

            reservations_table.rows.clear()

            for row in reservations_data:
                report_number = str(row[0])
                serial_number = str(row[1])
                reserved_by = str(row[2])

                try:
                    reserved_at = datetime.fromisoformat(row[3]).strftime("%Y-%m-%d %H:%M")
                except:
                    reserved_at = str(row[3])

                try:
                    expires_at_dt = datetime.fromisoformat(row[4])
                    expires_at = expires_at_dt.strftime("%Y-%m-%d %H:%M")

                    if expires_at_dt < now:
                        status = "EXPIRED"
                        status_color = colors["danger"]
                    else:
                        minutes_left = int((expires_at_dt - now).total_seconds() / 60)
                        status = f"Active ({minutes_left} min left)"
                        status_color = colors["success"]
                except:
                    expires_at = str(row[4])
                    status = "Unknown"
                    status_color = colors["text_muted"]

                def create_row_click(rn):
                    def handler(e):
                        nonlocal selected_reservation
                        selected_reservation = rn
                        release_btn.disabled = False
                        release_user_btn.disabled = False
                        page.update()
                    return handler

                reservations_table.rows.append(
                    ft.DataRow(
                        cells=[
                            ft.DataCell(ft.Text(report_number, size=12)),
                            ft.DataCell(ft.Text(serial_number, size=12)),
                            ft.DataCell(ft.Text(reserved_by, size=12)),
                            ft.DataCell(ft.Text(reserved_at, size=12)),
                            ft.DataCell(ft.Text(expires_at, size=12)),
                            ft.DataCell(ft.Text(status, size=12, color=status_color)),
                        ],
                        data={'report_number': report_number, 'reserved_by': reserved_by},
                        on_select_changed=create_row_click({'report_number': report_number, 'reserved_by': reserved_by}),
                    )
                )

            page.update()

        except Exception as e:
            print(f"Error loading reservations: {e}")

    async def load_statistics():
        """Load reservation statistics."""
        try:
            def fetch():
                stats = []

                # Total active
                result = app_state.db_manager.execute_with_retry(
                    "SELECT COUNT(*) FROM report_number_reservations WHERE is_used = 0"
                )
                total_active = result[0][0] if result else 0
                stats.append(f"Active Reservations: {total_active}")

                # Expired
                result = app_state.db_manager.execute_with_retry(
                    "SELECT COUNT(*) FROM report_number_reservations WHERE is_used = 0 AND expires_at < datetime('now')"
                )
                expired = result[0][0] if result else 0
                stats.append(f"Expired Reservations: {expired}")

                # Total completed
                result = app_state.db_manager.execute_with_retry(
                    "SELECT COUNT(*) FROM report_number_reservations WHERE is_used = 1"
                )
                total_used = result[0][0] if result else 0
                stats.append(f"Reports Created (All Time): {total_used}")

                # Latest serial
                result = app_state.db_manager.execute_with_retry(
                    "SELECT MAX(serial_number) FROM report_number_reservations"
                )
                latest_sn = result[0][0] if result and result[0][0] else 0
                stats.append(f"Latest Serial Number: {latest_sn}")

                # By user
                result = app_state.db_manager.execute_with_retry(
                    """SELECT reserved_by, COUNT(*) as count
                       FROM report_number_reservations WHERE is_used = 0
                       GROUP BY reserved_by ORDER BY count DESC"""
                )
                if result:
                    stats.append("\nReservations by User:")
                    for row in result:
                        stats.append(f"  {row[0]}: {row[1]}")

                return "\n".join(stats)

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, fetch)
            stats_text.value = result
            page.update()

        except Exception as e:
            stats_text.value = f"Error: {str(e)}"
            page.update()

    async def load_activity():
        """Load recent activity."""
        try:
            def fetch():
                query = """
                    SELECT report_number, reserved_by, is_used, reserved_at
                    FROM report_number_reservations
                    ORDER BY reserved_at DESC LIMIT 50
                """
                return app_state.db_manager.execute_with_retry(query)

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, fetch)

            activity_table.rows.clear()

            for row in (result or []):
                report_number = str(row[0])
                user = str(row[1])
                action = "Created Report" if row[2] == 1 else "Reserved"

                try:
                    timestamp = datetime.fromisoformat(row[3]).strftime("%Y-%m-%d %H:%M")
                except:
                    timestamp = str(row[3])

                activity_table.rows.append(
                    ft.DataRow(
                        cells=[
                            ft.DataCell(ft.Text(report_number, size=12)),
                            ft.DataCell(ft.Text(user, size=12)),
                            ft.DataCell(ft.Text(action, size=12)),
                            ft.DataCell(ft.Text(timestamp, size=12)),
                        ],
                    )
                )

            page.update()

        except Exception as e:
            print(f"Error loading activity: {e}")

    async def load_settings():
        """Load current settings."""
        try:
            def fetch():
                settings = {}

                result = app_state.db_manager.execute_with_retry(
                    "SELECT setting_value FROM system_settings WHERE setting_key = 'max_concurrent_reservations'"
                )
                if result and result[0][0]:
                    settings['max_concurrent'] = result[0][0]

                result = app_state.db_manager.execute_with_retry(
                    "SELECT setting_value FROM system_settings WHERE setting_key = 'max_reservations_per_user'"
                )
                if result and result[0][0]:
                    settings['max_per_user'] = result[0][0]

                return settings

            loop = asyncio.get_event_loop()
            settings = await loop.run_in_executor(None, fetch)

            if settings.get('max_concurrent'):
                max_concurrent_input.value = settings['max_concurrent']
            if settings.get('max_per_user'):
                max_per_user_input.value = settings['max_per_user']

            page.update()

        except Exception as e:
            print(f"Error loading settings: {e}")

    async def release_selected(e):
        """Release selected reservation."""
        nonlocal selected_reservation
        if not selected_reservation:
            show_warning(page, "Please select a reservation first.")
            return

        report_number = selected_reservation.get('report_number')

        def on_confirm(e):
            confirm_dialog.open = False
            page.update()
            page.run_task(do_release)

        def on_cancel(e):
            confirm_dialog.open = False
            page.update()

        confirm_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Release Reservation"),
            content=ft.Text(f"Release reservation for {report_number}?"),
            actions=[
                ft.TextButton("Cancel", on_click=on_cancel),
                ft.ElevatedButton("Release", on_click=on_confirm),
            ],
        )
        page.overlay.append(confirm_dialog)
        confirm_dialog.open = True
        page.update()

    async def do_release():
        nonlocal selected_reservation
        try:
            report_number = selected_reservation.get('report_number')

            def execute():
                app_state.db_manager.execute_with_retry(
                    "DELETE FROM report_number_reservations WHERE report_number = ? AND is_used = 0",
                    (report_number,)
                )

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, execute)

            show_success(page, f"Released reservation for {report_number}")
            selected_reservation = None
            release_btn.disabled = True
            release_user_btn.disabled = True
            await load_data()

        except Exception as ex:
            show_error(page, f"Failed to release: {str(ex)}")

    async def release_user_reservations(e):
        """Release all reservations for selected user."""
        nonlocal selected_reservation
        if not selected_reservation:
            show_warning(page, "Please select a reservation first.")
            return

        username = selected_reservation.get('reserved_by')

        def on_confirm(e):
            confirm_dialog.open = False
            page.update()
            page.run_task(do_release_user)

        def on_cancel(e):
            confirm_dialog.open = False
            page.update()

        confirm_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Release All Reservations"),
            content=ft.Text(f"Release ALL reservations held by {username}?"),
            actions=[
                ft.TextButton("Cancel", on_click=on_cancel),
                ft.ElevatedButton("Release All", on_click=on_confirm, bgcolor=colors["warning"], color=ft.Colors.WHITE),
            ],
        )
        page.overlay.append(confirm_dialog)
        confirm_dialog.open = True
        page.update()

    async def do_release_user():
        nonlocal selected_reservation
        try:
            username = selected_reservation.get('reserved_by')

            def execute():
                app_state.db_manager.execute_with_retry(
                    "DELETE FROM report_number_reservations WHERE reserved_by = ? AND is_used = 0",
                    (username,)
                )

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, execute)

            show_success(page, f"Released all reservations for {username}")
            selected_reservation = None
            release_btn.disabled = True
            release_user_btn.disabled = True
            await load_data()

        except Exception as ex:
            show_error(page, f"Failed to release: {str(ex)}")

    async def run_cleanup(e):
        """Run reservation cleanup."""
        try:
            def execute():
                if hasattr(app_state, 'report_number_service') and app_state.report_number_service:
                    app_state.report_number_service.cleanup_expired_reservations_public()
                else:
                    app_state.db_manager.execute_with_retry(
                        "DELETE FROM report_number_reservations WHERE is_used = 0 AND expires_at < datetime('now')"
                    )

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, execute)

            show_success(page, "Cleanup completed. Expired reservations released.")
            await load_data()

        except Exception as ex:
            show_error(page, f"Cleanup failed: {str(ex)}")

    async def save_settings(e):
        """Save reservation settings."""
        try:
            max_concurrent = int(max_concurrent_input.value or "10")
            max_per_user = int(max_per_user_input.value or "1")

            def execute():
                app_state.db_manager.execute_with_retry(
                    "UPDATE system_settings SET setting_value = ? WHERE setting_key = 'max_concurrent_reservations'",
                    (str(max_concurrent),)
                )
                app_state.db_manager.execute_with_retry(
                    "UPDATE system_settings SET setting_value = ? WHERE setting_key = 'max_reservations_per_user'",
                    (str(max_per_user),)
                )

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, execute)

            show_success(page, f"Settings saved: Max concurrent={max_concurrent}, Per user={max_per_user}")

        except ValueError:
            show_error(page, "Please enter valid numbers.")
        except Exception as ex:
            show_error(page, f"Failed to save settings: {str(ex)}")

    # Connect handlers
    release_btn.on_click = release_selected
    release_user_btn.on_click = release_user_reservations

    def close_dialog(e):
        dialog.open = False
        page.update()

    # Tabs
    tabs = ft.Tabs(
        selected_index=0,
        animation_duration=200,
        tabs=[
            # Active Reservations Tab
            ft.Tab(
                text="Active Reservations",
                icon=ft.Icons.LIST_ALT,
                content=ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Text(
                                "Active report number reservations. These are numbers currently held by users.",
                                size=12,
                                color=colors["text_secondary"],
                            ),
                            ft.Container(
                                content=ft.Column(
                                    controls=[reservations_table],
                                    scroll=ft.ScrollMode.AUTO,
                                ),
                                height=250,
                            ),
                            ft.Row(
                                controls=[release_btn, release_user_btn],
                                spacing=8,
                            ),
                        ],
                        spacing=12,
                    ),
                    padding=16,
                ),
            ),

            # Statistics Tab
            ft.Tab(
                text="Statistics",
                icon=ft.Icons.ANALYTICS,
                content=ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Text("Reservation Pool Statistics", weight=ft.FontWeight.BOLD, size=14),
                            ft.Container(
                                content=stats_text,
                                bgcolor=colors["bg_tertiary"],
                                padding=16,
                                border_radius=6,
                            ),
                            ft.Container(height=12),
                            ft.Text("Recent Activity", weight=ft.FontWeight.BOLD, size=14),
                            ft.Container(
                                content=ft.Column(
                                    controls=[activity_table],
                                    scroll=ft.ScrollMode.AUTO,
                                ),
                                height=200,
                            ),
                        ],
                        spacing=8,
                        scroll=ft.ScrollMode.AUTO,
                    ),
                    padding=16,
                ),
            ),

            # Settings Tab
            ft.Tab(
                text="Settings",
                icon=ft.Icons.SETTINGS,
                content=ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Text("Concurrent Reservation Limits", weight=ft.FontWeight.BOLD, size=14),
                            ft.Container(height=8),
                            max_concurrent_input,
                            ft.Text(
                                "Controls how many report numbers can be reserved simultaneously across all users.",
                                size=11,
                                color=colors["text_muted"],
                            ),
                            ft.Container(height=12),
                            max_per_user_input,
                            ft.Text(
                                "Controls how many report numbers each user can reserve at once. Typically set to 1.",
                                size=11,
                                color=colors["text_muted"],
                            ),
                            ft.Container(height=16),
                            ft.ElevatedButton(
                                "Save Reservation Limits",
                                icon=ft.Icons.SAVE,
                                bgcolor=colors["primary"],
                                color=ft.Colors.WHITE,
                                on_click=save_settings,
                            ),
                            ft.Container(height=24),
                            ft.Text("Reservation Timeout", weight=ft.FontWeight.BOLD, size=14),
                            ft.Container(height=8),
                            timeout_input,
                            ft.Text(
                                "How long a user can hold a reserved report number before it expires.",
                                size=11,
                                color=colors["text_muted"],
                            ),
                            ft.Container(height=24),
                            ft.Text("Cleanup", weight=ft.FontWeight.BOLD, size=14),
                            ft.Text(
                                "Automatic cleanup runs every 2 minutes. Use the button below for manual cleanup.",
                                size=11,
                                color=colors["text_muted"],
                            ),
                            ft.Container(height=8),
                            ft.ElevatedButton(
                                "Run Manual Cleanup",
                                icon=ft.Icons.CLEANING_SERVICES,
                                on_click=run_cleanup,
                            ),
                        ],
                        spacing=4,
                        scroll=ft.ScrollMode.AUTO,
                    ),
                    padding=16,
                ),
            ),
        ],
    )

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Row(
            controls=[
                ft.Icon(ft.Icons.NUMBERS, color=colors["primary"]),
                ft.Text("Report Number Reservation Management", weight=ft.FontWeight.BOLD),
            ],
            spacing=12,
        ),
        content=ft.Container(
            content=tabs,
            width=700,
            height=450,
        ),
        actions=[
            ft.ElevatedButton(
                "Refresh Now",
                icon=ft.Icons.REFRESH,
                on_click=lambda e: page.run_task(load_data),
            ),
            ft.ElevatedButton(
                "Run Cleanup",
                icon=ft.Icons.CLEANING_SERVICES,
                on_click=run_cleanup,
            ),
            ft.TextButton("Close", on_click=close_dialog),
        ],
    )

    page.overlay.append(dialog)
    dialog.open = True
    page.update()

    # Load data
    page.run_task(load_data)
