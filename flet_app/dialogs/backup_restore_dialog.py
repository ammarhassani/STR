"""
Backup & Restore Dialog for FIU Report Management System.
Comprehensive backup and restore functionality for database.
"""
import flet as ft
import asyncio
import shutil
import sqlite3
from typing import Any, Callable, Optional
from pathlib import Path
from datetime import datetime

from theme.theme_manager import theme_manager
from components.toast import show_success, show_error, show_warning
from config import Config


def show_backup_restore_dialog(
    page: ft.Page,
    app_state: Any,
    on_restore_complete: Optional[Callable[[], None]] = None,
):
    """
    Show the backup and restore dialog.

    Args:
        page: Flet page object
        app_state: Application state
        on_restore_complete: Callback when restore completes
    """
    colors = theme_manager.get_colors()

    # State
    backup_list_data = []
    selected_backup_path = None
    is_processing = False

    # Controls
    backup_list = ft.ListView(
        spacing=4,
        height=250,
        auto_scroll=False,
    )

    backup_info_text = ft.Text(
        "Select a backup to view details...",
        size=12,
        color=colors["text_secondary"],
    )

    progress_bar = ft.ProgressBar(visible=False)
    progress_label = ft.Text("", size=12, color=colors["text_secondary"], visible=False)

    # Action buttons (will be enabled/disabled based on selection)
    restore_btn = ft.ElevatedButton(
        "Restore Selected",
        icon=ft.Icons.RESTORE,
        disabled=True,
        bgcolor=colors["primary"],
        color=ft.Colors.WHITE,
    )

    export_btn = ft.ElevatedButton(
        "Export",
        icon=ft.Icons.FILE_DOWNLOAD,
        disabled=True,
    )

    delete_btn = ft.ElevatedButton(
        "Delete",
        icon=ft.Icons.DELETE,
        disabled=True,
        bgcolor=colors["danger"],
        color=ft.Colors.WHITE,
    )

    def get_backup_dir() -> Path:
        """Get backup directory path."""
        return Path(Config.BACKUP_PATH) if Config.BACKUP_PATH else Path.home() / "FIU_System" / "backups"

    def get_db_path() -> str:
        """Get database path."""
        return Config.DATABASE_PATH or ""

    async def refresh_backup_list():
        """Refresh the list of available backups."""
        nonlocal backup_list_data, selected_backup_path

        backup_list.controls.clear()
        backup_list_data.clear()
        selected_backup_path = None

        # Disable action buttons
        restore_btn.disabled = True
        export_btn.disabled = True
        delete_btn.disabled = True

        try:
            backup_dir = get_backup_dir()
            if not backup_dir.exists():
                backup_dir.mkdir(parents=True, exist_ok=True)

            def scan_backups():
                files = []
                for backup_file in backup_dir.glob("*.db"):
                    file_stat = backup_file.stat()
                    files.append({
                        'path': str(backup_file),
                        'name': backup_file.name,
                        'size': file_stat.st_size / (1024 * 1024),  # MB
                        'modified': datetime.fromtimestamp(file_stat.st_mtime),
                    })
                # Sort by modified time, newest first
                files.sort(key=lambda x: x['modified'], reverse=True)
                return files

            loop = asyncio.get_event_loop()
            backup_list_data = await loop.run_in_executor(None, scan_backups)

            if not backup_list_data:
                backup_list.controls.append(
                    ft.Container(
                        content=ft.Text(
                            "No backups found",
                            size=14,
                            color=colors["text_muted"],
                            text_align=ft.TextAlign.CENTER,
                        ),
                        padding=20,
                        alignment=ft.alignment.center,
                    )
                )
            else:
                for backup in backup_list_data:
                    backup_list.controls.append(
                        create_backup_item(backup)
                    )

            page.update()

        except Exception as e:
            show_error(page, f"Error loading backups: {str(e)}")

    def create_backup_item(backup: dict) -> ft.Container:
        """Create a backup list item."""
        def on_select(e):
            nonlocal selected_backup_path
            selected_backup_path = backup['path']

            # Update info
            backup_info_text.value = (
                f"File: {backup['name']}\n"
                f"Size: {backup['size']:.2f} MB\n"
                f"Modified: {backup['modified'].strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"Path: {backup['path']}"
            )

            # Enable action buttons
            restore_btn.disabled = False
            export_btn.disabled = False
            delete_btn.disabled = False

            # Update visual selection
            for control in backup_list.controls:
                if isinstance(control, ft.Container):
                    control.bgcolor = colors["bg_tertiary"] if control.data == backup['path'] else colors["bg_secondary"]

            page.update()

        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.STORAGE, size=20, color=colors["primary"]),
                    ft.Column(
                        controls=[
                            ft.Text(backup['name'], size=13, weight=ft.FontWeight.W_500),
                            ft.Text(
                                f"{backup['size']:.2f} MB • {backup['modified'].strftime('%Y-%m-%d %H:%M')}",
                                size=11,
                                color=colors["text_secondary"],
                            ),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                ],
                spacing=12,
            ),
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            bgcolor=colors["bg_secondary"],
            border_radius=6,
            data=backup['path'],
            on_click=on_select,
            ink=True,
        )

    async def create_backup(e):
        """Create a new database backup."""
        nonlocal is_processing
        if is_processing:
            return

        # Confirm dialog
        def on_confirm(e):
            confirm_dialog.open = False
            page.update()
            page.run_task(do_backup)

        def on_cancel(e):
            confirm_dialog.open = False
            page.update()

        confirm_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Create Backup"),
            content=ft.Text("Create a backup of the current database?"),
            actions=[
                ft.TextButton("Cancel", on_click=on_cancel),
                ft.ElevatedButton("Create Backup", on_click=on_confirm, bgcolor=colors["primary"], color=ft.Colors.WHITE),
            ],
        )
        page.overlay.append(confirm_dialog)
        confirm_dialog.open = True
        page.update()

    async def do_backup():
        nonlocal is_processing
        is_processing = True

        progress_bar.visible = True
        progress_label.visible = True
        progress_bar.value = 0
        progress_label.value = "Preparing backup..."
        page.update()

        try:
            def perform_backup():
                db_path = get_db_path()
                backup_dir = get_backup_dir()

                # Create backup directory
                backup_dir.mkdir(parents=True, exist_ok=True)

                # Generate backup filename
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_filename = f"fiu_backup_{timestamp}.db"
                backup_file_path = backup_dir / backup_filename

                # Copy database
                shutil.copy2(db_path, str(backup_file_path))

                # Verify backup
                conn = sqlite3.connect(str(backup_file_path))
                conn.execute("PRAGMA integrity_check")
                conn.close()

                return str(backup_file_path)

            loop = asyncio.get_event_loop()

            progress_bar.value = 0.3
            progress_label.value = "Creating backup..."
            page.update()

            backup_path = await loop.run_in_executor(None, perform_backup)

            progress_bar.value = 1.0
            progress_label.value = "Backup completed!"
            page.update()

            if app_state.logging_service:
                app_state.logging_service.log_user_action("BACKUP_CREATED", {'file_path': backup_path})

            show_success(page, f"Backup created: {Path(backup_path).name}")
            await refresh_backup_list()

        except Exception as ex:
            show_error(page, f"Backup failed: {str(ex)}")
        finally:
            is_processing = False
            progress_bar.visible = False
            progress_label.visible = False
            page.update()

    async def restore_backup(e):
        """Restore from selected backup."""
        nonlocal is_processing
        if is_processing or not selected_backup_path:
            return

        def on_confirm(e):
            confirm_dialog.open = False
            page.update()
            page.run_task(do_restore)

        def on_cancel(e):
            confirm_dialog.open = False
            page.update()

        confirm_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("⚠️ Restore Database"),
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text(
                            "WARNING: This will replace your current database!",
                            size=14,
                            weight=ft.FontWeight.BOLD,
                            color=colors["warning"],
                        ),
                        ft.Text(
                            "All changes made since this backup will be lost.\n"
                            "A backup of your current database will be created first.",
                            size=12,
                            color=colors["text_secondary"],
                        ),
                        ft.Text(
                            "Are you absolutely sure you want to continue?",
                            size=12,
                        ),
                    ],
                    spacing=12,
                    tight=True,
                ),
                width=400,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=on_cancel),
                ft.ElevatedButton("Restore", on_click=on_confirm, bgcolor=colors["danger"], color=ft.Colors.WHITE),
            ],
        )
        page.overlay.append(confirm_dialog)
        confirm_dialog.open = True
        page.update()

    async def do_restore():
        nonlocal is_processing
        is_processing = True

        progress_bar.visible = True
        progress_label.visible = True
        progress_bar.value = 0
        progress_label.value = "Verifying backup..."
        page.update()

        try:
            def perform_restore():
                target_db_path = get_db_path()

                # Verify backup
                conn = sqlite3.connect(selected_backup_path)
                conn.execute("PRAGMA integrity_check")
                conn.close()

                # Create backup of current database
                current_db = Path(target_db_path)
                if current_db.exists():
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    pre_restore_backup = current_db.parent / f"pre_restore_backup_{timestamp}.db"
                    shutil.copy2(str(current_db), str(pre_restore_backup))

                # Restore
                shutil.copy2(selected_backup_path, target_db_path)

            loop = asyncio.get_event_loop()

            progress_bar.value = 0.4
            progress_label.value = "Backing up current database..."
            page.update()

            await loop.run_in_executor(None, perform_restore)

            progress_bar.value = 1.0
            progress_label.value = "Restore completed!"
            page.update()

            if app_state.logging_service:
                app_state.logging_service.log_user_action("DATABASE_RESTORED", {})

            show_success(page, "Database restored! Please restart the application.")

            if on_restore_complete:
                on_restore_complete()

        except Exception as ex:
            show_error(page, f"Restore failed: {str(ex)}")
        finally:
            is_processing = False
            progress_bar.visible = False
            progress_label.visible = False
            page.update()

    async def export_backup(e):
        """Export selected backup."""
        if not selected_backup_path:
            return

        # Use FilePicker for save
        def on_save_result(e: ft.FilePickerResultEvent):
            if e.path:
                try:
                    shutil.copy2(selected_backup_path, e.path)
                    show_success(page, f"Backup exported to: {Path(e.path).name}")
                    if app_state.logging_service:
                        app_state.logging_service.log_user_action("BACKUP_EXPORTED", {'file_path': e.path})
                except Exception as ex:
                    show_error(page, f"Export failed: {str(ex)}")

        file_picker = ft.FilePicker(on_result=on_save_result)
        page.overlay.append(file_picker)
        page.update()

        file_picker.save_file(
            dialog_title="Export Backup",
            file_name=Path(selected_backup_path).name,
            allowed_extensions=["db"],
        )

    async def import_backup(e):
        """Import a backup file."""
        def on_file_result(e: ft.FilePickerResultEvent):
            if e.files and len(e.files) > 0:
                file_path = e.files[0].path
                page.run_task(lambda: do_import(file_path))

        file_picker = ft.FilePicker(on_result=on_file_result)
        page.overlay.append(file_picker)
        page.update()

        file_picker.pick_files(
            dialog_title="Import Backup",
            allowed_extensions=["db"],
            allow_multiple=False,
        )

    async def do_import(file_path: str):
        try:
            backup_dir = get_backup_dir()
            backup_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_filename = f"imported_backup_{timestamp}.db"
            new_path = backup_dir / new_filename

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: shutil.copy2(file_path, str(new_path)))

            show_success(page, f"Backup imported as: {new_filename}")
            if app_state.logging_service:
                app_state.logging_service.log_user_action("BACKUP_IMPORTED", {'file_path': str(new_path)})

            await refresh_backup_list()

        except Exception as ex:
            show_error(page, f"Import failed: {str(ex)}")

    async def delete_backup(e):
        """Delete selected backup."""
        if not selected_backup_path:
            return

        def on_confirm(e):
            confirm_dialog.open = False
            page.update()
            page.run_task(do_delete)

        def on_cancel(e):
            confirm_dialog.open = False
            page.update()

        confirm_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Delete Backup"),
            content=ft.Text(f"Delete backup: {Path(selected_backup_path).name}?\n\nThis cannot be undone."),
            actions=[
                ft.TextButton("Cancel", on_click=on_cancel),
                ft.ElevatedButton("Delete", on_click=on_confirm, bgcolor=colors["danger"], color=ft.Colors.WHITE),
            ],
        )
        page.overlay.append(confirm_dialog)
        confirm_dialog.open = True
        page.update()

    async def do_delete():
        nonlocal selected_backup_path
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: Path(selected_backup_path).unlink())

            if app_state.logging_service:
                app_state.logging_service.log_user_action("BACKUP_DELETED", {'file_path': selected_backup_path})

            show_success(page, "Backup deleted.")
            selected_backup_path = None
            await refresh_backup_list()

        except Exception as ex:
            show_error(page, f"Delete failed: {str(ex)}")

    def open_backup_folder(e):
        """Open backup folder in file explorer."""
        import subprocess
        import platform

        try:
            backup_dir = get_backup_dir()
            backup_dir.mkdir(parents=True, exist_ok=True)

            if platform.system() == 'Windows':
                subprocess.Popen(['explorer', str(backup_dir)])
            elif platform.system() == 'Darwin':
                subprocess.Popen(['open', str(backup_dir)])
            else:
                subprocess.Popen(['xdg-open', str(backup_dir)])
        except Exception as ex:
            show_error(page, f"Could not open folder: {str(ex)}")

    # Connect button handlers
    restore_btn.on_click = restore_backup
    export_btn.on_click = export_backup
    delete_btn.on_click = delete_backup

    def close_dialog(e):
        dialog.open = False
        page.update()

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Row(
            controls=[
                ft.Icon(ft.Icons.BACKUP, color=colors["primary"]),
                ft.Text("Database Backup & Restore", weight=ft.FontWeight.BOLD),
            ],
            spacing=12,
        ),
        content=ft.Container(
            content=ft.Column(
                controls=[
                    # Info
                    ft.Text(
                        "Create backups to protect against data loss. Restore from any backup to revert to a previous state.",
                        size=12,
                        color=colors["text_secondary"],
                    ),
                    ft.Container(height=8),

                    # Backup actions
                    ft.Text("Backup Actions", weight=ft.FontWeight.BOLD, size=13),
                    ft.Row(
                        controls=[
                            ft.ElevatedButton(
                                "Create Backup Now",
                                icon=ft.Icons.SAVE,
                                bgcolor=colors["primary"],
                                color=ft.Colors.WHITE,
                                on_click=create_backup,
                            ),
                            ft.ElevatedButton(
                                "Import Backup",
                                icon=ft.Icons.FILE_UPLOAD,
                                on_click=import_backup,
                            ),
                            ft.ElevatedButton(
                                "Open Folder",
                                icon=ft.Icons.FOLDER_OPEN,
                                on_click=open_backup_folder,
                            ),
                        ],
                        spacing=8,
                    ),
                    ft.Container(height=12),

                    # Progress
                    progress_label,
                    progress_bar,

                    # Existing backups
                    ft.Text("Existing Backups", weight=ft.FontWeight.BOLD, size=13),
                    ft.Container(
                        content=backup_list,
                        border=ft.border.all(1, colors["border"]),
                        border_radius=6,
                        bgcolor=colors["bg_secondary"],
                    ),

                    # Backup info
                    ft.Container(
                        content=backup_info_text,
                        bgcolor=colors["bg_tertiary"],
                        padding=12,
                        border_radius=6,
                    ),

                    # Actions for selected backup
                    ft.Row(
                        controls=[restore_btn, export_btn, delete_btn],
                        spacing=8,
                    ),
                ],
                spacing=8,
                scroll=ft.ScrollMode.AUTO,
            ),
            width=600,
            height=550,
        ),
        actions=[
            ft.ElevatedButton(
                "Refresh List",
                icon=ft.Icons.REFRESH,
                on_click=lambda e: page.run_task(refresh_backup_list),
            ),
            ft.TextButton("Close", on_click=close_dialog),
        ],
    )

    page.overlay.append(dialog)
    dialog.open = True
    page.update()

    # Load backups
    page.run_task(refresh_backup_list)
