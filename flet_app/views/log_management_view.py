"""
Log Management View for FIU Report Management System.
Admin view for viewing, filtering, and managing system logs.
"""
import flet as ft
import asyncio
from typing import Any, Dict, List
from datetime import datetime, timedelta

from theme.theme_manager import theme_manager
from components.toast import show_success, show_error


LOG_LEVELS = ['All', 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']


def build_log_management_view(page: ft.Page, app_state: Any) -> ft.Column:
    """
    Build the log management view.

    Args:
        page: Flet page object
        app_state: Application state

    Returns:
        Log management column
    """
    colors = theme_manager.get_colors()

    # State
    logs_data = []
    is_loading = True

    # Default date range: last 7 days
    default_start = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    default_end = datetime.now().strftime('%Y-%m-%d')

    # Refs
    loading_ref = ft.Ref[ft.Container]()
    table_ref = ft.Ref[ft.Container]()
    stats_ref = ft.Ref[ft.Text]()
    level_ref = ft.Ref[ft.Dropdown]()
    module_ref = ft.Ref[ft.TextField]()
    start_date_ref = ft.Ref[ft.TextField]()
    end_date_ref = ft.Ref[ft.TextField]()

    async def load_logs():
        """Load logs asynchronously."""
        nonlocal logs_data, is_loading

        is_loading = True
        if loading_ref.current:
            loading_ref.current.visible = True
        if table_ref.current:
            table_ref.current.visible = False
        page.update()

        try:
            loop = asyncio.get_event_loop()

            def fetch_logs():
                level = level_ref.current.value if level_ref.current and level_ref.current.value != 'All' else None
                module = module_ref.current.value.strip() if module_ref.current and module_ref.current.value else None
                start_date = start_date_ref.current.value if start_date_ref.current else default_start
                end_date_raw = end_date_ref.current.value if end_date_ref.current else default_end

                # Add 1 day to end_date to make it inclusive (include logs from the entire end date)
                try:
                    end_date_dt = datetime.strptime(end_date_raw, '%Y-%m-%d') + timedelta(days=1)
                    end_date = end_date_dt.strftime('%Y-%m-%d')
                except:
                    end_date = end_date_raw

                if app_state.logging_service:
                    return app_state.logging_service.get_logs(
                        level=level,
                        module=module,
                        start_date=start_date,
                        end_date=end_date,
                        limit=500
                    )
                return []

            logs_data = await loop.run_in_executor(None, fetch_logs)
            update_table_ui()

        except Exception as e:
            print(f"Error loading logs: {e}")
            show_error(page, f"Error loading logs: {str(e)}")

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
            stats_ref.current.value = f"{len(logs_data)} logs loaded"

        # Rebuild table
        if table_ref.current:
            table_ref.current.content = build_table()

        page.update()

    def build_table() -> ft.Control:
        """Build the logs data table."""
        if not logs_data:
            return ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Icon(ft.Icons.HISTORY, size=48, color=colors["text_muted"]),
                        ft.Text("No logs found", color=colors["text_muted"]),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                expand=True,
                alignment=ft.alignment.center,
            )

        # Level colors
        level_colors = {
            'DEBUG': colors["text_secondary"],
            'INFO': colors["info"],
            'WARNING': colors["warning"],
            'ERROR': colors["danger"],
            'CRITICAL': colors["danger"],
        }

        # Build data rows
        rows = []
        for log in logs_data:
            level = log.get('level', 'INFO')
            level_color = level_colors.get(level, colors["text_primary"])

            # Format timestamp
            timestamp = log.get('timestamp', '')
            if timestamp:
                timestamp = str(timestamp)[:19]

            # Truncate message
            message = log.get('message', '')
            message_display = (message[:80] + '...') if len(message) > 80 else message

            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(timestamp, size=11, color=colors["text_secondary"])),
                        ft.DataCell(
                            ft.Container(
                                content=ft.Text(level, size=10, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
                                bgcolor=level_color,
                                border_radius=4,
                                padding=ft.padding.symmetric(horizontal=6, vertical=2),
                            )
                        ),
                        ft.DataCell(ft.Text(log.get('module', ''), size=11, color=colors["text_primary"])),
                        ft.DataCell(ft.Text(log.get('function', ''), size=11, color=colors["text_secondary"])),
                        ft.DataCell(ft.Text(log.get('user', '-'), size=11, color=colors["text_secondary"])),
                        ft.DataCell(
                            ft.Text(message_display, size=11, color=colors["text_primary"], tooltip=message)
                        ),
                    ],
                )
            )

        columns = [
            ft.DataColumn(ft.Text("Timestamp", weight=ft.FontWeight.BOLD, size=11, color=colors["text_primary"])),
            ft.DataColumn(ft.Text("Level", weight=ft.FontWeight.BOLD, size=11, color=colors["text_primary"])),
            ft.DataColumn(ft.Text("Module", weight=ft.FontWeight.BOLD, size=11, color=colors["text_primary"])),
            ft.DataColumn(ft.Text("Function", weight=ft.FontWeight.BOLD, size=11, color=colors["text_primary"])),
            ft.DataColumn(ft.Text("User", weight=ft.FontWeight.BOLD, size=11, color=colors["text_primary"])),
            ft.DataColumn(ft.Text("Message", weight=ft.FontWeight.BOLD, size=11, color=colors["text_primary"])),
        ]

        return ft.DataTable(
            columns=columns,
            rows=rows,
            column_spacing=12,
            horizontal_lines=ft.BorderSide(1, colors["border"]),
            heading_row_color=colors["bg_tertiary"],
            data_row_color={
                ft.ControlState.HOVERED: colors["hover"],
            },
            border_radius=8,
        )

    def handle_refresh(e):
        """Refresh logs."""
        page.run_task(load_logs)

    def handle_export(e):
        """Export logs to file."""
        if not logs_data:
            show_error(page, "No logs to export")
            return

        # TODO: Implement file export with FilePicker
        show_success(page, f"Export functionality - {len(logs_data)} logs ready for export")

    def handle_clear_logs(e):
        """Clear all logs."""
        def confirm_clear(e):
            confirm_dialog.open = False
            page.update()

            try:
                if app_state.logging_service:
                    # Get date range
                    start = start_date_ref.current.value if start_date_ref.current else None
                    end = end_date_ref.current.value if end_date_ref.current else None

                    success = app_state.logging_service.clear_logs(
                        before_date=end
                    )

                    if success:
                        show_success(page, "Logs cleared successfully")
                        page.run_task(load_logs)
                    else:
                        show_error(page, "Failed to clear logs")
                else:
                    show_error(page, "Logging service not available")

            except Exception as ex:
                show_error(page, f"Error clearing logs: {str(ex)}")

        def cancel_clear(e):
            confirm_dialog.open = False
            page.update()

        confirm_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Clear Logs"),
            content=ft.Text(
                "Are you sure you want to clear the system logs?\n\n"
                "This action cannot be undone."
            ),
            actions=[
                ft.TextButton("Cancel", on_click=cancel_clear),
                ft.ElevatedButton(
                    "Clear Logs",
                    bgcolor=colors["danger"],
                    color=ft.Colors.WHITE,
                    on_click=confirm_clear,
                ),
            ],
        )
        page.overlay.append(confirm_dialog)
        confirm_dialog.open = True
        page.update()

    # Header row
    header_row = ft.Row(
        controls=[
            ft.Text(
                "System Logs Management",
                size=18,
                weight=ft.FontWeight.BOLD,
                color=colors["text_primary"],
            ),
        ],
        spacing=12,
    )

    # Filter row
    filter_row = ft.Container(
        content=ft.Row(
            controls=[
                ft.Text("Level:", color=colors["text_secondary"]),
                ft.Dropdown(
                    ref=level_ref,
                    value="All",
                    options=[ft.dropdown.Option(key=lvl, text=lvl) for lvl in LOG_LEVELS],
                    width=120,
                    text_size=13,
                ),
                ft.Text("Module:", color=colors["text_secondary"]),
                ft.TextField(
                    ref=module_ref,
                    hint_text="Filter by module...",
                    width=150,
                    height=40,
                    text_size=13,
                ),
                ft.Text("From:", color=colors["text_secondary"]),
                ft.TextField(
                    ref=start_date_ref,
                    value=default_start,
                    hint_text="YYYY-MM-DD",
                    width=120,
                    height=40,
                    text_size=13,
                ),
                ft.Text("To:", color=colors["text_secondary"]),
                ft.TextField(
                    ref=end_date_ref,
                    value=default_end,
                    hint_text="YYYY-MM-DD",
                    width=120,
                    height=40,
                    text_size=13,
                ),
                ft.IconButton(
                    icon=ft.Icons.SEARCH,
                    icon_color=colors["primary"],
                    tooltip="Apply filters",
                    on_click=handle_refresh,
                ),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            wrap=True,
        ),
        padding=ft.padding.all(12),
        bgcolor=colors["bg_tertiary"],
        border_radius=8,
    )

    # Actions row
    actions_row = ft.Row(
        controls=[
            ft.Text(
                ref=stats_ref,
                value="0 logs loaded",
                size=13,
                color=colors["text_secondary"],
            ),
            ft.Container(expand=True),
            ft.ElevatedButton(
                "Export to File",
                icon=ft.Icons.DOWNLOAD,
                bgcolor=colors["primary"],
                color=ft.Colors.WHITE,
                on_click=handle_export,
            ),
            ft.ElevatedButton(
                "Clear Logs",
                icon=ft.Icons.DELETE,
                bgcolor=colors["danger"],
                color=ft.Colors.WHITE,
                on_click=handle_clear_logs,
            ),
        ],
        spacing=12,
    )

    # Loading indicator
    loading_container = ft.Container(
        ref=loading_ref,
        content=ft.Column(
            controls=[
                ft.ProgressRing(width=32, height=32, color=colors["primary"]),
                ft.Text("Loading logs...", color=colors["text_secondary"]),
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
    page.run_task(load_logs)

    return ft.Column(
        controls=[
            header_row,
            ft.Container(height=16),
            filter_row,
            ft.Container(height=8),
            actions_row,
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
