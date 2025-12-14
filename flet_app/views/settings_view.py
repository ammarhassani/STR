"""
Settings View for FIU Report Management System.
Admin panel for configuring system-wide settings.
"""
import flet as ft
import asyncio
from typing import Any, Dict
from datetime import datetime

from theme.theme_manager import theme_manager
from components.toast import show_success, show_error


def build_settings_view(page: ft.Page, app_state: Any) -> ft.Column:
    """
    Build the settings view.

    Args:
        page: Flet page object
        app_state: Application state

    Returns:
        Settings column
    """
    colors = theme_manager.get_colors()

    # Refs for inputs
    grace_period_ref = ft.Ref[ft.TextField]()
    batch_size_ref = ft.Ref[ft.TextField]()
    reservation_expiry_ref = ft.Ref[ft.TextField]()
    page_size_ref = ft.Ref[ft.TextField]()

    async def load_settings():
        """Load current settings from database."""
        try:
            loop = asyncio.get_event_loop()

            def fetch_settings():
                settings = {}
                queries = [
                    ('month_grace_period', '3'),
                    ('batch_pool_size', '20'),
                    ('reservation_expiry_minutes', '5'),
                    ('records_per_page', '50'),
                ]

                for key, default in queries:
                    result = app_state.db_manager.execute_with_retry(
                        "SELECT config_value FROM system_config WHERE config_key = ? AND is_active = 1",
                        (key,)
                    )
                    settings[key] = result[0][0] if result else default

                return settings

            settings = await loop.run_in_executor(None, fetch_settings)

            # Update UI
            if grace_period_ref.current:
                grace_period_ref.current.value = settings.get('month_grace_period', '3')
            if batch_size_ref.current:
                batch_size_ref.current.value = settings.get('batch_pool_size', '20')
            if reservation_expiry_ref.current:
                reservation_expiry_ref.current.value = settings.get('reservation_expiry_minutes', '5')
            if page_size_ref.current:
                page_size_ref.current.value = settings.get('records_per_page', '50')

            page.update()

        except Exception as e:
            print(f"Error loading settings: {e}")
            show_error(page, f"Error loading settings: {str(e)}")

    def save_setting(key: str, value: str):
        """Save a single setting to database."""
        now = datetime.now().isoformat()
        current_user = app_state.auth_service.get_current_user()
        username = current_user['username'] if current_user else 'system'

        # Check if exists
        result = app_state.db_manager.execute_with_retry(
            "SELECT config_id FROM system_config WHERE config_key = ?",
            (key,)
        )

        if result:
            # Update
            app_state.db_manager.execute_with_retry(
                """UPDATE system_config
                   SET config_value = ?, updated_at = ?, updated_by = ?
                   WHERE config_key = ?""",
                (value, now, username, key)
            )
        else:
            # Insert
            app_state.db_manager.execute_with_retry(
                """INSERT INTO system_config
                   (config_key, config_value, config_type, config_category, updated_at, updated_by, is_active)
                   VALUES (?, ?, ?, ?, ?, ?, 1)""",
                (key, value, 'setting', 'system', now, username)
            )

    def handle_save(e):
        """Save all settings."""
        try:
            # Validate inputs
            grace = grace_period_ref.current.value if grace_period_ref.current else '3'
            batch = batch_size_ref.current.value if batch_size_ref.current else '20'
            expiry = reservation_expiry_ref.current.value if reservation_expiry_ref.current else '5'
            page_size = page_size_ref.current.value if page_size_ref.current else '50'

            # Validate numeric values
            try:
                int(grace)
                int(batch)
                int(expiry)
                int(page_size)
            except ValueError:
                show_error(page, "All values must be valid numbers")
                return

            # Save settings
            save_setting('month_grace_period', grace)
            save_setting('batch_pool_size', batch)
            save_setting('reservation_expiry_minutes', expiry)
            save_setting('records_per_page', page_size)

            # Log change
            if app_state.logging_service:
                current_user = app_state.auth_service.get_current_user()
                app_state.logging_service.info(
                    f"Admin {current_user['username'] if current_user else 'unknown'} updated system settings"
                )

            show_success(page, "Settings saved successfully!")

        except Exception as ex:
            show_error(page, f"Error saving settings: {str(ex)}")

    def handle_reset(e):
        """Reset to default values."""
        def confirm_reset(e):
            reset_dialog.open = False
            page.update()

            if grace_period_ref.current:
                grace_period_ref.current.value = "3"
            if batch_size_ref.current:
                batch_size_ref.current.value = "20"
            if reservation_expiry_ref.current:
                reservation_expiry_ref.current.value = "5"
            if page_size_ref.current:
                page_size_ref.current.value = "50"

            page.update()
            show_success(page, "Settings reset to defaults. Click 'Save Settings' to apply.")

        def cancel_reset(e):
            reset_dialog.open = False
            page.update()

        reset_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Reset to Defaults"),
            content=ft.Text("Are you sure you want to reset all settings to their default values?"),
            actions=[
                ft.TextButton("Cancel", on_click=cancel_reset),
                ft.ElevatedButton(
                    "Reset",
                    bgcolor=colors["warning"],
                    color=ft.Colors.WHITE,
                    on_click=confirm_reset,
                ),
            ],
        )
        page.overlay.append(reset_dialog)
        reset_dialog.open = True
        page.update()

    def create_setting_field(
        label: str,
        ref: ft.Ref,
        default: str,
        suffix: str,
        hint: str,
        min_val: int,
        max_val: int,
    ) -> ft.Column:
        """Create a setting input field with label and hint."""
        return ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text(label, weight=ft.FontWeight.W_500, color=colors["text_primary"], width=180),
                        ft.TextField(
                            ref=ref,
                            value=default,
                            width=100,
                            text_size=13,
                            keyboard_type=ft.KeyboardType.NUMBER,
                            suffix_text=suffix,
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Text(
                    hint,
                    size=11,
                    color=colors["text_muted"],
                    italic=True,
                ),
            ],
            spacing=4,
        )

    # Header
    header_row = ft.Row(
        controls=[
            ft.Text(
                "System Settings",
                size=18,
                weight=ft.FontWeight.BOLD,
                color=colors["text_primary"],
            ),
        ],
    )

    # Info text
    info_text = ft.Text(
        "Configure system-wide settings. Changes take effect immediately after saving.",
        size=13,
        color=colors["text_secondary"],
    )

    # Report Numbering Group
    numbering_group = ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.NUMBERS, color=colors["primary"], size=20),
                        ft.Text(
                            "Report Numbering",
                            size=14,
                            weight=ft.FontWeight.BOLD,
                            color=colors["text_primary"],
                        ),
                    ],
                    spacing=8,
                ),
                ft.Container(height=12),
                create_setting_field(
                    "Month Grace Period:",
                    grace_period_ref,
                    "3",
                    "days",
                    "Days into new month to continue using previous month. Example: Set to 3 means Dec 1st-3rd still use November (2025/11)",
                    0, 15,
                ),
            ],
            spacing=8,
        ),
        padding=ft.padding.all(16),
        bgcolor=colors["card_bg"],
        border_radius=8,
        border=ft.border.all(1, colors["border"]),
    )

    # Batch Reservation Group
    batch_group = ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.REFRESH, color=colors["primary"], size=20),
                        ft.Text(
                            "Batch Reservation",
                            size=14,
                            weight=ft.FontWeight.BOLD,
                            color=colors["text_primary"],
                        ),
                    ],
                    spacing=8,
                ),
                ft.Container(height=12),
                create_setting_field(
                    "Batch Pool Size:",
                    batch_size_ref,
                    "20",
                    "numbers",
                    "Pre-reserved report numbers in batch pool. Higher = faster for concurrent users. Recommended: 10-30",
                    5, 100,
                ),
                ft.Container(height=8),
                create_setting_field(
                    "Reservation Expiry:",
                    reservation_expiry_ref,
                    "5",
                    "minutes",
                    "Time before reserved numbers expire. Longer = more flexibility. Recommended: 5-10 minutes",
                    1, 60,
                ),
            ],
            spacing=8,
        ),
        padding=ft.padding.all(16),
        bgcolor=colors["card_bg"],
        border_radius=8,
        border=ft.border.all(1, colors["border"]),
    )

    # General Settings Group
    general_group = ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.SETTINGS, color=colors["primary"], size=20),
                        ft.Text(
                            "General",
                            size=14,
                            weight=ft.FontWeight.BOLD,
                            color=colors["text_primary"],
                        ),
                    ],
                    spacing=8,
                ),
                ft.Container(height=12),
                create_setting_field(
                    "Default Page Size:",
                    page_size_ref,
                    "50",
                    "records",
                    "Number of records to show per page in tables",
                    10, 200,
                ),
            ],
            spacing=8,
        ),
        padding=ft.padding.all(16),
        bgcolor=colors["card_bg"],
        border_radius=8,
        border=ft.border.all(1, colors["border"]),
    )

    # Buttons
    buttons_row = ft.Row(
        controls=[
            ft.Container(expand=True),
            ft.OutlinedButton(
                "Reset to Defaults",
                icon=ft.Icons.RESTORE,
                on_click=handle_reset,
            ),
            ft.ElevatedButton(
                "Save Settings",
                icon=ft.Icons.SAVE,
                bgcolor=colors["primary"],
                color=ft.Colors.WHITE,
                on_click=handle_save,
            ),
        ],
        spacing=12,
    )

    # Trigger initial load
    page.run_task(load_settings)

    return ft.Column(
        controls=[
            header_row,
            ft.Container(height=8),
            info_text,
            ft.Container(height=16),
            numbering_group,
            ft.Container(height=12),
            batch_group,
            ft.Container(height=12),
            general_group,
            ft.Container(height=24),
            buttons_row,
        ],
        spacing=0,
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )
