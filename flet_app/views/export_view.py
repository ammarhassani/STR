"""
Export View for FIU Report Management System.
Export reports to CSV with filtering and customization options.
"""
import flet as ft
import asyncio
import threading
from typing import Any, Dict
from pathlib import Path
from datetime import datetime, timedelta

from theme.theme_manager import theme_manager
from components.toast import show_success, show_error
from utils.file_dialog import choose_directory


def build_export_view(page: ft.Page, app_state: Any) -> ft.Column:
    """
    Build the export view.

    Args:
        page: Flet page object
        app_state: Application state

    Returns:
        Export column
    """
    colors = theme_manager.get_colors()

    # State
    is_exporting = False
    export_count = 0

    # Default dates
    default_from = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
    default_to = datetime.now().strftime('%Y-%m-%d')
    default_path = str(Path.home() / "Downloads")

    # Refs
    status_ref = ft.Ref[ft.Dropdown]()
    date_from_ref = ft.Ref[ft.TextField]()
    date_to_ref = ft.Ref[ft.TextField]()
    date_filter_ref = ft.Ref[ft.Checkbox]()
    search_ref = ft.Ref[ft.TextField]()
    output_path_ref = ft.Ref[ft.TextField]()
    progress_ref = ft.Ref[ft.Container]()
    progress_bar_ref = ft.Ref[ft.ProgressBar]()
    progress_text_ref = ft.Ref[ft.Text]()
    stats_ref = ft.Ref[ft.Container]()
    stats_text_ref = ft.Ref[ft.Text]()
    export_btn_ref = ft.Ref[ft.ElevatedButton]()
    preview_btn_ref = ft.Ref[ft.ElevatedButton]()

    def get_filters() -> Dict:
        """Get current filter values."""
        filters = {}

        # Status filter
        status = status_ref.current.value if status_ref.current else ''
        if status and status != 'All Statuses':
            filters['status'] = status

        # Date range filter
        if date_filter_ref.current and date_filter_ref.current.value:
            date_from = date_from_ref.current.value if date_from_ref.current else ''
            date_to = date_to_ref.current.value if date_to_ref.current else ''
            if date_from:
                filters['date_from'] = date_from
            if date_to:
                filters['date_to'] = date_to

        # Search term
        search = search_ref.current.value.strip() if search_ref.current else ''
        if search:
            filters['search_term'] = search

        return filters

    async def preview_export(e=None):
        """Preview how many reports will be exported."""
        try:
            loop = asyncio.get_event_loop()
            filters = get_filters()

            def count_reports():
                # Build count query
                query = "SELECT COUNT(*) FROM reports WHERE is_deleted = 0"
                params = []

                if 'status' in filters:
                    query += " AND status = ?"
                    params.append(filters['status'])

                if 'date_from' in filters:
                    query += " AND report_date >= ?"
                    params.append(filters['date_from'])

                if 'date_to' in filters:
                    query += " AND report_date <= ?"
                    params.append(filters['date_to'])

                if 'search_term' in filters:
                    query += """ AND (
                        report_number LIKE ? OR
                        reported_entity_name LIKE ? OR
                        cic LIKE ?
                    )"""
                    search_pattern = f"%{filters['search_term']}%"
                    params.extend([search_pattern] * 3)

                result = app_state.db_manager.execute_with_retry(query, tuple(params))
                return result[0][0] if result else 0

            count = await loop.run_in_executor(None, count_reports)

            # Build filter description
            filter_desc = []
            if 'status' in filters:
                filter_desc.append(f"Status: {filters['status']}")
            if 'date_from' in filters:
                filter_desc.append(f"From: {filters['date_from']}")
            if 'date_to' in filters:
                filter_desc.append(f"To: {filters['date_to']}")
            if 'search_term' in filters:
                filter_desc.append(f"Search: {filters['search_term']}")

            filter_text = "\n".join(filter_desc) if filter_desc else "No filters applied"

            if stats_ref.current:
                stats_ref.current.visible = True
            if stats_text_ref.current:
                stats_text_ref.current.value = f"{count} report(s) will be exported\n\nApplied filters:\n{filter_text}"

            page.update()

            if app_state.logging_service:
                app_state.logging_service.info(f"Export preview: {count} reports")

        except Exception as ex:
            show_error(page, f"Failed to preview export: {str(ex)}")

    async def start_export(e=None):
        """Start export process."""
        nonlocal is_exporting

        output_path = output_path_ref.current.value if output_path_ref.current else ''

        if not output_path:
            show_error(page, "Please select an output location.")
            return

        # Verify directory exists
        if not Path(output_path).exists():
            show_error(page, "The selected output directory does not exist.")
            return

        is_exporting = True

        # Disable buttons
        if export_btn_ref.current:
            export_btn_ref.current.disabled = True
        if preview_btn_ref.current:
            preview_btn_ref.current.disabled = True

        # Show progress
        if progress_ref.current:
            progress_ref.current.visible = True
        if progress_bar_ref.current:
            progress_bar_ref.current.value = 0
        if progress_text_ref.current:
            progress_text_ref.current.value = "Starting export..."

        page.update()

        try:
            loop = asyncio.get_event_loop()
            filters = get_filters()

            def update_progress(value, message):
                if progress_bar_ref.current:
                    progress_bar_ref.current.value = value / 100
                if progress_text_ref.current:
                    progress_text_ref.current.value = message
                page.update()

            def do_export():
                from utils.export import export_reports

                update_progress(20, "Preparing export...")

                file_path = export_reports(
                    app_state.db_manager,
                    filters=filters,
                    output_dir=output_path
                )

                update_progress(90, "Finalizing...")
                update_progress(100, "Export completed!")

                return file_path

            file_path = await loop.run_in_executor(None, do_export)

            # Success
            if app_state.logging_service:
                app_state.logging_service.log_user_action("EXPORT_COMPLETED", {"file_path": str(file_path)})

            show_success(page, f"Successfully exported to {file_path}")

            # Ask to open folder
            def open_folder(e):
                import os
                import subprocess
                folder_path = str(Path(file_path).parent)

                dialog.open = False
                page.update()

                if os.name == 'nt':  # Windows
                    os.startfile(folder_path)
                elif os.name == 'posix':  # macOS and Linux
                    subprocess.Popen(['xdg-open', folder_path])

            def close_dialog(e):
                dialog.open = False
                page.update()

            dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("Export Successful"),
                content=ft.Text(f"File saved to:\n{file_path}\n\nWould you like to open the folder?"),
                actions=[
                    ft.TextButton("No", on_click=close_dialog),
                    ft.ElevatedButton(
                        "Open Folder",
                        bgcolor=colors["primary"],
                        color=ft.Colors.WHITE,
                        on_click=open_folder,
                    ),
                ],
            )
            page.overlay.append(dialog)
            dialog.open = True
            page.update()

        except Exception as ex:
            show_error(page, f"Export failed: {str(ex)}")
            if app_state.logging_service:
                app_state.logging_service.error(f"Export failed: {str(ex)}")

        finally:
            is_exporting = False

            # Re-enable buttons
            if export_btn_ref.current:
                export_btn_ref.current.disabled = False
            if preview_btn_ref.current:
                preview_btn_ref.current.disabled = False

            # Hide progress
            if progress_ref.current:
                progress_ref.current.visible = False

            page.update()

    def handle_browse(e):
        """Browse for output directory using native OS dialog."""
        def run_dialog():
            current_path = output_path_ref.current.value if output_path_ref.current else default_path
            result = choose_directory(
                prompt="Select Output Directory",
                default_path=current_path
            )
            if result:
                if output_path_ref.current:
                    output_path_ref.current.value = result
                page.update()

        # Run in background thread to avoid blocking UI
        threading.Thread(target=run_dialog, daemon=True).start()

    # Header
    header_row = ft.Row(
        controls=[
            ft.Text(
                "Export Reports to CSV",
                size=18,
                weight=ft.FontWeight.BOLD,
                color=colors["text_primary"],
            ),
        ],
    )

    # Description
    description = ft.Text(
        "Export your reports to CSV format for analysis in Excel or other tools. "
        "Apply filters to export only specific reports.",
        size=13,
        color=colors["text_secondary"],
    )

    # Filters section
    status_options = [
        'All Statuses',
        'Open',
        'Case Review',
        'Under Investigation',
        'Case Validation',
        'Close Case',
        'Closed with STR'
    ]

    filters_section = ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.FILTER_ALT, color=colors["primary"], size=20),
                        ft.Text("Export Filters", size=14, weight=ft.FontWeight.BOLD, color=colors["text_primary"]),
                    ],
                    spacing=8,
                ),
                ft.Container(height=12),
                # Status filter
                ft.Row(
                    controls=[
                        ft.Text("Status:", width=100, color=colors["text_secondary"]),
                        ft.Dropdown(
                            ref=status_ref,
                            value="All Statuses",
                            options=[ft.dropdown.Option(key=s, text=s) for s in status_options],
                            width=250,
                            text_size=13,
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Container(height=8),
                # Date range filter
                ft.Row(
                    controls=[
                        ft.Text("Date Range:", width=100, color=colors["text_secondary"]),
                        ft.TextField(
                            ref=date_from_ref,
                            value=default_from,
                            hint_text="From (YYYY-MM-DD)",
                            width=140,
                            text_size=13,
                        ),
                        ft.Text("to", color=colors["text_secondary"]),
                        ft.TextField(
                            ref=date_to_ref,
                            value=default_to,
                            hint_text="To (YYYY-MM-DD)",
                            width=140,
                            text_size=13,
                        ),
                        ft.Checkbox(
                            ref=date_filter_ref,
                            label="Enable Date Filter",
                            value=False,
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=8,
                    wrap=True,
                ),
                ft.Container(height=8),
                # Search term
                ft.Row(
                    controls=[
                        ft.Text("Search:", width=100, color=colors["text_secondary"]),
                        ft.TextField(
                            ref=search_ref,
                            hint_text="Search by report number, entity name, or CIC...",
                            expand=True,
                            text_size=13,
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
        ),
        padding=ft.padding.all(16),
        bgcolor=colors["card_bg"],
        border_radius=8,
        border=ft.border.all(1, colors["border"]),
    )

    # Output location section
    output_section = ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.FOLDER, color=colors["primary"], size=20),
                        ft.Text("Output Location", size=14, weight=ft.FontWeight.BOLD, color=colors["text_primary"]),
                    ],
                    spacing=8,
                ),
                ft.Container(height=12),
                ft.Row(
                    controls=[
                        ft.Text("Save to:", width=100, color=colors["text_secondary"]),
                        ft.TextField(
                            ref=output_path_ref,
                            value=default_path,
                            expand=True,
                            text_size=13,
                            read_only=True,
                        ),
                        ft.ElevatedButton(
                            "Browse...",
                            icon=ft.Icons.FOLDER_OPEN,
                            on_click=handle_browse,
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Container(height=4),
                ft.Text(
                    "File will be automatically named: fiu_reports_YYYYMMDD_HHMMSS.csv",
                    size=11,
                    color=colors["text_muted"],
                    italic=True,
                ),
            ],
        ),
        padding=ft.padding.all(16),
        bgcolor=colors["card_bg"],
        border_radius=8,
        border=ft.border.all(1, colors["border"]),
    )

    # Progress section
    progress_section = ft.Container(
        ref=progress_ref,
        content=ft.Column(
            controls=[
                ft.Text(
                    ref=progress_text_ref,
                    value="Exporting...",
                    color=colors["text_secondary"],
                ),
                ft.ProgressBar(
                    ref=progress_bar_ref,
                    value=0,
                    color=colors["primary"],
                    bgcolor=colors["bg_tertiary"],
                ),
            ],
            spacing=8,
        ),
        padding=ft.padding.all(16),
        bgcolor=colors["card_bg"],
        border_radius=8,
        border=ft.border.all(1, colors["border"]),
        visible=False,
    )

    # Stats section
    stats_section = ft.Container(
        ref=stats_ref,
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.INFO_OUTLINE, color=colors["info"], size=20),
                        ft.Text(
                            ref=stats_text_ref,
                            value="",
                            color=colors["text_secondary"],
                        ),
                    ],
                    spacing=8,
                ),
            ],
        ),
        padding=ft.padding.all(16),
        bgcolor=colors["bg_tertiary"],
        border_radius=8,
        visible=False,
    )

    # Buttons
    buttons_row = ft.Row(
        controls=[
            ft.ElevatedButton(
                ref=preview_btn_ref,
                text="Preview Count",
                icon=ft.Icons.SEARCH,
                on_click=lambda _: page.run_task(preview_export),
            ),
            ft.Container(expand=True),
            ft.ElevatedButton(
                ref=export_btn_ref,
                text="Export to CSV",
                icon=ft.Icons.DOWNLOAD,
                bgcolor=colors["primary"],
                color=ft.Colors.WHITE,
                on_click=lambda _: page.run_task(start_export),
            ),
        ],
    )

    return ft.Column(
        controls=[
            header_row,
            ft.Container(height=8),
            description,
            ft.Container(height=16),
            filters_section,
            ft.Container(height=12),
            output_section,
            ft.Container(height=12),
            progress_section,
            stats_section,
            ft.Container(height=16),
            buttons_row,
        ],
        spacing=0,
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )
