"""
Settings View for FIU Report Management System.
Admin panel for configuring system-wide settings.
"""
import flet as ft
import asyncio
from typing import Any, Dict
from datetime import datetime

from theme.theme_manager import theme_manager
from i18n import t
from components.toast import show_success, show_error
from components.app_button import app_button


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
            batch = batch_size_ref.current.value if batch_size_ref.current else '20'
            expiry = reservation_expiry_ref.current.value if reservation_expiry_ref.current else '5'
            page_size = page_size_ref.current.value if page_size_ref.current else '50'

            # Validate numeric values
            try:
                int(batch)
                int(expiry)
                int(page_size)
            except ValueError:
                show_error(page, "All values must be valid numbers")
                return

            # Save settings
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
            title=ft.Text(t("set.reset")),
            content=ft.Text("Are you sure you want to reset all settings to their default values?"),
            actions=[
                ft.TextButton(t("common.cancel"), on_click=cancel_reset),
                ft.ElevatedButton(
                    t("set.reset"),
                    bgcolor=colors["warning"],
                    color=ft.Colors.WHITE,
                    on_click=confirm_reset,
                ),
            ],
        )
        page.overlay.append(reset_dialog)
        reset_dialog.open = True
        page.update()

    active_month_ref = ft.Ref[ft.Text]()

    def refresh_active_month():
        svc = getattr(app_state, 'report_number_service', None)
        if svc and active_month_ref.current:
            try:
                active_month_ref.current.value = f"Current numbering month: {svc.get_active_numbering_month()}"
            except Exception:
                active_month_ref.current.value = "Current numbering month: unknown"


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
                t("set.title"),
                size=18,
                weight=ft.FontWeight.BOLD,
                color=colors["text_primary"],
            ),
        ],
    )

    # Info text
    info_text = ft.Text(
        t("set.info"),
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
                            t("set.group.numbering"),
                            size=14,
                            weight=ft.FontWeight.BOLD,
                            color=colors["text_primary"],
                        ),
                    ],
                    spacing=8,
                ),
                ft.Container(height=12),
                ft.Text(ref=active_month_ref, value="Current numbering month: …",
                        size=13, color=colors["text_primary"], weight=ft.FontWeight.W_600),
                ft.Text(t("set.numbering_help"),
                        size=11, italic=True, color=colors["text_muted"]),
            ],
            spacing=8,
        ),
        padding=ft.padding.all(16),
        bgcolor=colors["card_bg"],
        border_radius=4,
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
                            t("set.group.batch"),
                            size=14,
                            weight=ft.FontWeight.BOLD,
                            color=colors["text_primary"],
                        ),
                    ],
                    spacing=8,
                ),
                ft.Container(height=12),
                create_setting_field(
                    t("set.batch_pool"),
                    batch_size_ref,
                    "20",
                    "numbers",
                    t("set.batch_pool_hint"),
                    5, 100,
                ),
                ft.Container(height=8),
                create_setting_field(
                    t("set.expiry"),
                    reservation_expiry_ref,
                    "5",
                    t("set.suffix_minutes"),
                    t("set.expiry_hint"),
                    1, 60,
                ),
            ],
            spacing=8,
        ),
        padding=ft.padding.all(16),
        bgcolor=colors["card_bg"],
        border_radius=4,
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
                            t("set.group.general"),
                            size=14,
                            weight=ft.FontWeight.BOLD,
                            color=colors["text_primary"],
                        ),
                    ],
                    spacing=8,
                ),
                ft.Container(height=12),
                create_setting_field(
                    t("set.page_size"),
                    page_size_ref,
                    "50",
                    t("set.suffix_records"),
                    t("set.page_size_hint"),
                    10, 200,
                ),
            ],
            spacing=8,
        ),
        padding=ft.padding.all(16),
        bgcolor=colors["card_bg"],
        border_radius=4,
        border=ft.border.all(1, colors["border"]),
    )

    # Buttons
    buttons_row = ft.Row(
        controls=[
            ft.Container(expand=True),
            ft.OutlinedButton(
                t("set.reset"),
                icon=ft.Icons.RESTORE,
                on_click=handle_reset,
            ),
            app_button(
                t("set.save"),
                icon=ft.Icons.SAVE,
                on_click=handle_save,
                variant="primary",
            ),
        ],
        spacing=12,
    )

    # Trigger initial load
    page.run_task(load_settings)
    refresh_active_month()

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
