"""
Setup Wizard View for FIU Report Management System.
Multi-step wizard for first-time setup.
"""
import flet as ft
import asyncio
from typing import Any, Callable, Optional
from pathlib import Path

from theme.colors import Colors
from database.init_db import initialize_database


def build_setup_wizard(
    page: ft.Page,
    on_complete: Callable[[str, str], None],
) -> ft.Container:
    """
    Build the setup wizard view.

    Args:
        page: Flet page object
        on_complete: Callback when setup completes (db_path, backup_path)

    Returns:
        Container with setup wizard
    """
    colors = Colors.DARK  # Use dark theme for setup

    # State
    current_step = 0
    use_existing_db = False

    # Default paths
    default_base = Path.home() / "FIU_System"
    default_db_path = str(default_base / "database" / "fiu_reports.db")
    default_backup_path = str(default_base / "backups")

    # Controls
    db_path_input = ft.TextField(
        label="Database File Path",
        value=default_db_path,
        hint_text="Select location for database file",
    )

    backup_path_input = ft.TextField(
        label="Backup Directory",
        value=default_backup_path,
        hint_text="Select directory for backups",
    )

    progress_bar = ft.ProgressBar(value=0, visible=False)
    progress_label = ft.Text("", size=12, color=colors["text_secondary"], visible=False)

    # Step indicators
    step_indicator = ft.Row(
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=16,
    )

    # Content container (changes per step)
    content_container = ft.Container(expand=True)

    # Navigation buttons
    back_btn = ft.ElevatedButton(
        "← Back",
        visible=False,
    )

    next_btn = ft.ElevatedButton(
        "Next →",
        bgcolor=colors["primary"],
        color=ft.Colors.WHITE,
    )

    def update_step_indicator():
        """Update step indicator UI."""
        step_indicator.controls.clear()
        steps = ["Welcome", "Configure Paths", "Create Database", "Complete"]

        for i, step_name in enumerate(steps):
            is_current = i == current_step
            is_completed = i < current_step

            step_indicator.controls.append(
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Container(
                                content=ft.Text(
                                    "✓" if is_completed else str(i + 1),
                                    size=12,
                                    color=ft.Colors.WHITE if (is_current or is_completed) else colors["text_muted"],
                                    text_align=ft.TextAlign.CENTER,
                                ),
                                width=28,
                                height=28,
                                border_radius=14,
                                bgcolor=colors["primary"] if (is_current or is_completed) else colors["bg_tertiary"],
                                alignment=ft.alignment.center,
                            ),
                            ft.Text(
                                step_name,
                                size=12,
                                color=colors["text_primary"] if is_current else colors["text_muted"],
                                weight=ft.FontWeight.BOLD if is_current else ft.FontWeight.NORMAL,
                            ),
                        ],
                        spacing=8,
                    ),
                )
            )

            # Add connector line between steps (except last)
            if i < len(steps) - 1:
                step_indicator.controls.append(
                    ft.Container(
                        width=40,
                        height=2,
                        bgcolor=colors["primary"] if is_completed else colors["bg_tertiary"],
                    )
                )

    def build_welcome_step() -> ft.Container:
        """Build welcome step content."""
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Icon(ft.Icons.ANALYTICS, size=64, color=colors["primary"]),
                    ft.Container(height=16),
                    ft.Text(
                        "Welcome to FIU Report Management System",
                        size=24,
                        weight=ft.FontWeight.BOLD,
                        color=colors["text_primary"],
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Container(height=16),
                    ft.Text(
                        "This wizard will help you set up the Financial Intelligence Unit\n"
                        "Report Management System.",
                        size=14,
                        color=colors["text_secondary"],
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Container(height=24),
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Text("You will configure:", size=13, color=colors["text_primary"]),
                                ft.Container(height=8),
                                ft.Row([ft.Icon(ft.Icons.CHECK_CIRCLE, size=16, color=colors["success"]), ft.Text("Database location", size=13)], spacing=8),
                                ft.Row([ft.Icon(ft.Icons.CHECK_CIRCLE, size=16, color=colors["success"]), ft.Text("Backup directory", size=13)], spacing=8),
                                ft.Row([ft.Icon(ft.Icons.CHECK_CIRCLE, size=16, color=colors["success"]), ft.Text("Initial system settings", size=13)], spacing=8),
                            ],
                            spacing=4,
                        ),
                        bgcolor=colors["bg_secondary"],
                        padding=20,
                        border_radius=8,
                    ),
                    ft.Container(height=24),
                    ft.Text(
                        "Click 'Next' to continue with the setup.",
                        size=12,
                        color=colors["text_muted"],
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            expand=True,
            alignment=ft.alignment.center,
        )

    def build_paths_step() -> ft.Container:
        """Build path configuration step content."""
        def browse_db(e):
            def on_result(e: ft.FilePickerResultEvent):
                if e.path:
                    db_path_input.value = e.path
                    page.update()

            picker = ft.FilePicker(on_result=on_result)
            page.overlay.append(picker)
            page.update()
            picker.save_file(
                dialog_title="Select Database Location",
                file_name="fiu_reports.db",
                allowed_extensions=["db"],
            )

        def browse_backup(e):
            def on_result(e: ft.FilePickerResultEvent):
                if e.path:
                    backup_path_input.value = e.path
                    page.update()

            picker = ft.FilePicker(on_result=on_result)
            page.overlay.append(picker)
            page.update()
            picker.get_directory_path(
                dialog_title="Select Backup Directory",
            )

        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(
                        "Configure Paths",
                        size=20,
                        weight=ft.FontWeight.BOLD,
                        color=colors["text_primary"],
                    ),
                    ft.Text(
                        "Select locations for the database and backup files.",
                        size=13,
                        color=colors["text_secondary"],
                    ),
                    ft.Container(height=24),

                    # Database path
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Text("Database File Location", weight=ft.FontWeight.W_600, size=13),
                                ft.Text(
                                    "Choose where to store the main database file",
                                    size=11,
                                    color=colors["text_muted"],
                                ),
                                ft.Container(height=8),
                                ft.Row(
                                    controls=[
                                        ft.Container(content=db_path_input, expand=True),
                                        ft.ElevatedButton("Browse...", on_click=browse_db),
                                    ],
                                    spacing=8,
                                ),
                            ],
                            spacing=4,
                        ),
                        bgcolor=colors["bg_secondary"],
                        padding=20,
                        border_radius=8,
                    ),
                    ft.Container(height=16),

                    # Backup path
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Text("Backup Directory", weight=ft.FontWeight.W_600, size=13),
                                ft.Text(
                                    "Choose where to store automatic backups",
                                    size=11,
                                    color=colors["text_muted"],
                                ),
                                ft.Container(height=8),
                                ft.Row(
                                    controls=[
                                        ft.Container(content=backup_path_input, expand=True),
                                        ft.ElevatedButton("Browse...", on_click=browse_backup),
                                    ],
                                    spacing=8,
                                ),
                            ],
                            spacing=4,
                        ),
                        bgcolor=colors["bg_secondary"],
                        padding=20,
                        border_radius=8,
                    ),
                ],
                spacing=8,
            ),
            expand=True,
            padding=20,
        )

    def build_creation_step() -> ft.Container:
        """Build database creation step content."""
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(
                        "Creating Database",
                        size=20,
                        weight=ft.FontWeight.BOLD,
                        color=colors["text_primary"],
                    ),
                    ft.Text(
                        "Please wait while we set up your system...",
                        size=13,
                        color=colors["text_secondary"],
                    ),
                    ft.Container(height=40),

                    ft.Container(
                        content=ft.Column(
                            controls=[
                                progress_label,
                                ft.Container(height=8),
                                progress_bar,
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        bgcolor=colors["bg_secondary"],
                        padding=30,
                        border_radius=8,
                        width=400,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            expand=True,
            alignment=ft.alignment.center,
        )

    def build_complete_step() -> ft.Container:
        """Build completion step content."""
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Icon(ft.Icons.CHECK_CIRCLE, size=80, color=colors["success"]),
                    ft.Container(height=16),
                    ft.Text(
                        "Setup Completed Successfully!",
                        size=24,
                        weight=ft.FontWeight.BOLD,
                        color=colors["text_primary"],
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Container(height=24),
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Text(
                                    "Your FIU Report Management System has been configured.",
                                    size=13,
                                    color=colors["text_secondary"],
                                    text_align=ft.TextAlign.CENTER,
                                ),
                                ft.Container(height=16),
                                ft.Text(
                                    "Default admin credentials:",
                                    size=13,
                                    weight=ft.FontWeight.BOLD,
                                ),
                                ft.Text("Username: admin", size=13, color=colors["text_secondary"]),
                                ft.Text("Password: admin123", size=13, color=colors["text_secondary"]),
                                ft.Container(height=12),
                                ft.Row(
                                    controls=[
                                        ft.Icon(ft.Icons.WARNING, size=16, color=colors["warning"]),
                                        ft.Text(
                                            "Please change these credentials after your first login.",
                                            size=12,
                                            color=colors["warning"],
                                        ),
                                    ],
                                    spacing=8,
                                    alignment=ft.MainAxisAlignment.CENTER,
                                ),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=4,
                        ),
                        bgcolor=colors["bg_secondary"],
                        padding=24,
                        border_radius=8,
                    ),
                    ft.Container(height=24),
                    ft.Text(
                        "Click 'Finish' to proceed to the login screen.",
                        size=12,
                        color=colors["text_muted"],
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            expand=True,
            alignment=ft.alignment.center,
        )

    def update_content():
        """Update content based on current step."""
        nonlocal current_step

        if current_step == 0:
            content_container.content = build_welcome_step()
            back_btn.visible = False
            next_btn.text = "Next →"
        elif current_step == 1:
            content_container.content = build_paths_step()
            back_btn.visible = True
            next_btn.text = "Next →"
        elif current_step == 2:
            content_container.content = build_creation_step()
            back_btn.visible = False
            next_btn.visible = False
            # Start database creation
            page.run_task(create_database)
        elif current_step == 3:
            content_container.content = build_complete_step()
            back_btn.visible = False
            next_btn.visible = True
            next_btn.text = "Finish"

        update_step_indicator()
        page.update()

    def validate_paths() -> tuple:
        """Validate path inputs."""
        nonlocal use_existing_db

        db_path = db_path_input.value.strip() if db_path_input.value else ""
        backup_path = backup_path_input.value.strip() if backup_path_input.value else ""

        if not db_path:
            return False, "Please specify the database file path."
        if not backup_path:
            return False, "Please specify the backup directory."

        # Check if database exists
        db_file = Path(db_path)
        if not str(db_file).lower().endswith('.db'):
            db_file = Path(str(db_file) + '.db')
            db_path_input.value = str(db_file)

        if db_file.exists():
            # Database exists - ask user
            use_existing_db = True  # For now, use existing
            return True, "existing"

        use_existing_db = False
        return True, ""

    async def create_database():
        """Create the database."""
        nonlocal current_step, use_existing_db

        progress_bar.visible = True
        progress_label.visible = True
        progress_bar.value = 0
        progress_label.value = "Initializing..."
        page.update()

        try:
            db_path = db_path_input.value.strip()
            backup_path = backup_path_input.value.strip()

            # Ensure .db extension
            if not db_path.lower().endswith('.db'):
                db_path = db_path + '.db'

            if use_existing_db:
                progress_label.value = "Using existing database..."
                progress_bar.value = 1.0
                page.update()
                await asyncio.sleep(0.5)
            else:
                def do_create():
                    # Create directories
                    db_file = Path(db_path)
                    db_file.parent.mkdir(parents=True, exist_ok=True)
                    Path(backup_path).mkdir(parents=True, exist_ok=True)

                    # Initialize database
                    success, message = initialize_database(db_path)
                    return success, message

                progress_bar.value = 0.1
                progress_label.value = "Creating directories..."
                page.update()

                loop = asyncio.get_event_loop()

                progress_bar.value = 0.4
                progress_label.value = "Initializing database schema..."
                page.update()

                success, message = await loop.run_in_executor(None, do_create)

                if not success:
                    progress_label.value = f"Error: {message}"
                    progress_label.color = colors["danger"]
                    page.update()
                    return

                progress_bar.value = 0.9
                progress_label.value = "Finalizing setup..."
                page.update()
                await asyncio.sleep(0.3)

            progress_bar.value = 1.0
            progress_label.value = "Setup completed successfully!"
            progress_label.color = colors["success"]
            page.update()

            await asyncio.sleep(0.5)

            # Move to completion step
            current_step = 3
            update_content()

        except Exception as e:
            progress_label.value = f"Error: {str(e)}"
            progress_label.color = colors["danger"]
            back_btn.visible = True
            page.update()

    def on_back(e):
        nonlocal current_step
        if current_step > 0:
            current_step -= 1
            update_content()

    def on_next(e):
        nonlocal current_step

        if current_step == 0:
            # Welcome -> Paths
            current_step = 1
            update_content()

        elif current_step == 1:
            # Paths -> Creation
            valid, message = validate_paths()
            if not valid:
                # Show error
                page.snack_bar = ft.SnackBar(
                    content=ft.Text(message, color=ft.Colors.WHITE),
                    bgcolor=colors["danger"],
                )
                page.snack_bar.open = True
                page.update()
                return

            if message == "existing":
                # Ask user about existing database
                def on_use_existing(e):
                    nonlocal use_existing_db, current_step
                    use_existing_db = True
                    confirm_dialog.open = False
                    current_step = 2
                    update_content()

                def on_create_new(e):
                    nonlocal use_existing_db, current_step
                    use_existing_db = False
                    confirm_dialog.open = False
                    current_step = 2
                    update_content()

                def on_cancel(e):
                    confirm_dialog.open = False
                    page.update()

                confirm_dialog = ft.AlertDialog(
                    modal=True,
                    title=ft.Text("Database Exists"),
                    content=ft.Text(
                        f"A database already exists at:\n{db_path_input.value}\n\n"
                        "Do you want to use the existing database or create a new one?"
                    ),
                    actions=[
                        ft.TextButton("Cancel", on_click=on_cancel),
                        ft.ElevatedButton("Create New", on_click=on_create_new),
                        ft.ElevatedButton("Use Existing", on_click=on_use_existing, bgcolor=colors["primary"], color=ft.Colors.WHITE),
                    ],
                )
                page.overlay.append(confirm_dialog)
                confirm_dialog.open = True
                page.update()
                return

            current_step = 2
            update_content()

        elif current_step == 3:
            # Complete -> Finish
            db_path = db_path_input.value.strip()
            if not db_path.lower().endswith('.db'):
                db_path = db_path + '.db'
            backup_path = backup_path_input.value.strip()
            on_complete(db_path, backup_path)

    back_btn.on_click = on_back
    next_btn.on_click = on_next

    # Initialize
    update_step_indicator()
    content_container.content = build_welcome_step()

    return ft.Container(
        content=ft.Column(
            controls=[
                # Header
                ft.Container(
                    content=step_indicator,
                    padding=ft.padding.symmetric(vertical=24),
                ),

                # Content area
                ft.Container(
                    content=content_container,
                    expand=True,
                    padding=ft.padding.symmetric(horizontal=40),
                ),

                # Navigation buttons
                ft.Container(
                    content=ft.Row(
                        controls=[
                            back_btn,
                            ft.Container(expand=True),
                            next_btn,
                        ],
                    ),
                    padding=24,
                    bgcolor=colors["bg_secondary"],
                ),
            ],
            spacing=0,
        ),
        expand=True,
        bgcolor=colors["bg_primary"],
    )
