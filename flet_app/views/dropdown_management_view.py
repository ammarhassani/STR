"""
Dropdown Management View for FIU Report Management System.
Admin panel for managing dropdown values (CRUD operations).
"""
import flet as ft
import asyncio
from typing import Any, Dict, List

from theme.theme_manager import theme_manager
from components.toast import show_success, show_error


def build_dropdown_management_view(page: ft.Page, app_state: Any) -> ft.Column:
    """
    Build the dropdown management view.

    Args:
        page: Flet page object
        app_state: Application state

    Returns:
        Dropdown management column
    """
    colors = theme_manager.get_colors()

    # State
    current_category = None
    dropdown_values = []
    is_loading = False

    # Admin-manageable categories (from dropdown_service)
    admin_manageable = []
    try:
        admin_manageable = app_state.dropdown_service.ADMIN_MANAGEABLE_CATEGORIES
    except:
        admin_manageable = ['source_of_fund', 'type_of_business', 'predicate_offense', 'other_category']

    # Refs
    category_ref = ft.Ref[ft.Dropdown]()
    table_ref = ft.Ref[ft.Container]()
    loading_ref = ft.Ref[ft.Container]()
    status_ref = ft.Ref[ft.Text]()
    add_btn_ref = ft.Ref[ft.ElevatedButton]()

    async def load_categories():
        """Load all dropdown categories."""
        try:
            loop = asyncio.get_event_loop()

            def fetch_categories():
                if app_state.dropdown_service:
                    return app_state.dropdown_service.get_all_categories()
                return []

            categories = await loop.run_in_executor(None, fetch_categories)

            if category_ref.current:
                options = [ft.dropdown.Option("-- Select Category --", "")]
                for cat in categories:
                    # Mark admin-manageable with icon
                    display = f"[Editable] {cat}" if cat in admin_manageable else cat
                    options.append(ft.dropdown.Option(display, cat))
                category_ref.current.options = options
                category_ref.current.value = ""

            page.update()

        except Exception as e:
            print(f"Error loading categories: {e}")
            show_error(page, f"Error loading categories: {str(e)}")

    async def load_values():
        """Load values for current category."""
        nonlocal dropdown_values, is_loading

        if not current_category:
            return

        is_loading = True
        if loading_ref.current:
            loading_ref.current.visible = True
        if table_ref.current:
            table_ref.current.visible = False
        page.update()

        try:
            loop = asyncio.get_event_loop()

            def fetch_values():
                if app_state.dropdown_service:
                    return app_state.dropdown_service.get_all_dropdown_values(current_category)
                return []

            dropdown_values = await loop.run_in_executor(None, fetch_values)
            update_table_ui()

        except Exception as e:
            print(f"Error loading values: {e}")
            show_error(page, f"Error loading values: {str(e)}")

        finally:
            is_loading = False
            if loading_ref.current:
                loading_ref.current.visible = False
            if table_ref.current:
                table_ref.current.visible = True
            page.update()

    def update_table_ui():
        """Update table with current data."""
        # Update status
        if status_ref.current and current_category:
            active_count = sum(1 for v in dropdown_values if v.get('is_active', True))
            inactive_count = len(dropdown_values) - active_count
            is_admin = current_category in admin_manageable
            manageable_text = "[Editable]" if is_admin else "[Read-Only]"

            status_ref.current.value = f"{current_category} - {manageable_text} | Active: {active_count} | Inactive: {inactive_count}"

        # Update add button
        if add_btn_ref.current:
            add_btn_ref.current.disabled = current_category not in admin_manageable

        # Rebuild table
        if table_ref.current:
            table_ref.current.content = build_table()

        page.update()

    def build_table() -> ft.Control:
        """Build the dropdown values data table."""
        if not dropdown_values:
            return ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Icon(ft.Icons.LIST, size=48, color=colors["text_muted"]),
                        ft.Text("No values found", color=colors["text_muted"]),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                expand=True,
                alignment=ft.alignment.center,
            )

        is_admin = current_category in admin_manageable

        # Build data rows
        rows = []
        for val in dropdown_values:
            # Status
            is_active = val.get('is_active', True)
            status_color = colors["success"] if is_active else colors["danger"]
            status_text = "Active" if is_active else "Inactive"

            # Action buttons
            action_controls = []
            if is_admin:
                action_controls.append(
                    ft.IconButton(
                        icon=ft.Icons.EDIT,
                        icon_color=colors["primary"],
                        tooltip="Edit",
                        on_click=lambda e, v=val: handle_edit(v),
                    )
                )
                if is_active:
                    action_controls.append(
                        ft.IconButton(
                            icon=ft.Icons.DELETE,
                            icon_color=colors["danger"],
                            tooltip="Delete",
                            on_click=lambda e, v=val: handle_delete(v),
                        )
                    )
                else:
                    action_controls.append(
                        ft.IconButton(
                            icon=ft.Icons.RESTORE,
                            icon_color=colors["success"],
                            tooltip="Restore",
                            on_click=lambda e, v=val: handle_restore(v),
                        )
                    )
            else:
                action_controls.append(
                    ft.Text("Read-Only", size=11, color=colors["text_muted"], italic=True)
                )

            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(val.get('value', ''), size=12, color=colors["text_primary"])),
                        ft.DataCell(ft.Text(str(val.get('display_order', 0)), size=12, color=colors["text_secondary"])),
                        ft.DataCell(
                            ft.Container(
                                content=ft.Text(status_text, size=10, color=ft.Colors.WHITE),
                                bgcolor=status_color,
                                border_radius=4,
                                padding=ft.padding.symmetric(horizontal=8, vertical=2),
                            )
                        ),
                        ft.DataCell(ft.Text(val.get('updated_by', '-'), size=12, color=colors["text_secondary"])),
                        ft.DataCell(ft.Row(controls=action_controls, spacing=0)),
                    ],
                )
            )

        columns = [
            ft.DataColumn(ft.Text("Value", weight=ft.FontWeight.BOLD, size=12, color=colors["text_primary"])),
            ft.DataColumn(ft.Text("Order", weight=ft.FontWeight.BOLD, size=12, color=colors["text_primary"])),
            ft.DataColumn(ft.Text("Status", weight=ft.FontWeight.BOLD, size=12, color=colors["text_primary"])),
            ft.DataColumn(ft.Text("Updated By", weight=ft.FontWeight.BOLD, size=12, color=colors["text_primary"])),
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

    def handle_category_change(e):
        """Handle category selection change."""
        nonlocal current_category
        selected = category_ref.current.value if category_ref.current else ""

        if selected:
            current_category = selected
            page.run_task(load_values)
        else:
            current_category = None
            dropdown_values.clear()
            if table_ref.current:
                table_ref.current.content = ft.Text("Select a category to view values", color=colors["text_muted"])
            if status_ref.current:
                status_ref.current.value = ""
            if add_btn_ref.current:
                add_btn_ref.current.disabled = True
            page.update()

    def show_value_dialog(value_data: Dict = None):
        """Show dialog to add/edit dropdown value."""
        is_edit = value_data is not None

        value_input = ft.TextField(
            label="Value",
            value=value_data.get('value', '') if value_data else '',
            autofocus=True,
        )
        order_input = ft.TextField(
            label="Display Order",
            value=str(value_data.get('display_order', len(dropdown_values))) if value_data else str(len(dropdown_values)),
            keyboard_type=ft.KeyboardType.NUMBER,
            width=100,
        )

        def save_value(e):
            value = value_input.value.strip()
            if not value:
                show_error(page, "Value cannot be empty")
                return

            try:
                order = int(order_input.value or 0)
            except ValueError:
                show_error(page, "Display order must be a number")
                return

            current_user = app_state.auth_service.get_current_user()
            username = current_user['username'] if current_user else 'admin'

            try:
                if is_edit:
                    success, message = app_state.dropdown_service.update_dropdown_value(
                        value_data['config_id'],
                        value,
                        username,
                        order
                    )
                else:
                    success, message = app_state.dropdown_service.add_dropdown_value(
                        current_category,
                        value,
                        username,
                        order
                    )

                if success:
                    dialog.open = False
                    page.update()
                    show_success(page, message)
                    page.run_task(load_values)
                else:
                    show_error(page, message)

            except Exception as ex:
                show_error(page, f"Error: {str(ex)}")

        def close_dialog(e):
            dialog.open = False
            page.update()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"{'Edit' if is_edit else 'Add'} Value - {current_category}"),
            content=ft.Column(
                controls=[
                    ft.Text(f"Category: {current_category}", weight=ft.FontWeight.BOLD),
                    ft.Container(height=8),
                    value_input,
                    ft.Container(height=8),
                    order_input,
                    ft.Text("Lower numbers appear first", size=11, color=colors["text_muted"]),
                ],
                spacing=4,
                tight=True,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=close_dialog),
                ft.ElevatedButton(
                    "Save",
                    bgcolor=colors["primary"],
                    color=ft.Colors.WHITE,
                    on_click=save_value,
                ),
            ],
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def handle_add(e):
        """Handle add value button."""
        if not current_category:
            show_error(page, "Please select a category first")
            return
        show_value_dialog()

    def handle_edit(value_data: Dict):
        """Handle edit value."""
        show_value_dialog(value_data)

    def handle_delete(value_data: Dict):
        """Handle delete value (soft delete)."""
        def confirm_delete(e):
            dialog.open = False
            page.update()

            current_user = app_state.auth_service.get_current_user()
            username = current_user['username'] if current_user else 'admin'

            try:
                success, message = app_state.dropdown_service.delete_dropdown_value(
                    value_data['config_id'],
                    username
                )

                if success:
                    show_success(page, message)
                    page.run_task(load_values)
                else:
                    show_error(page, message)

            except Exception as ex:
                show_error(page, f"Error: {str(ex)}")

        def cancel_delete(e):
            dialog.open = False
            page.update()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirm Delete"),
            content=ft.Text(
                f"Are you sure you want to delete '{value_data.get('value')}'?\n\n"
                "This will be a soft delete - the value will be hidden but existing data is preserved."
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
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def handle_restore(value_data: Dict):
        """Handle restore value."""
        current_user = app_state.auth_service.get_current_user()
        username = current_user['username'] if current_user else 'admin'

        try:
            success, message = app_state.dropdown_service.restore_dropdown_value(
                value_data['config_id'],
                username
            )

            if success:
                show_success(page, message)
                page.run_task(load_values)
            else:
                show_error(page, message)

        except Exception as ex:
            show_error(page, f"Error: {str(ex)}")

    def handle_refresh(e):
        """Refresh values."""
        if current_category:
            page.run_task(load_values)

    # Header row
    header_row = ft.Row(
        controls=[
            ft.Text(
                "Dropdown Management",
                size=18,
                weight=ft.FontWeight.BOLD,
                color=colors["text_primary"],
            ),
            ft.Container(expand=True),
            ft.IconButton(
                icon=ft.Icons.REFRESH,
                icon_color=colors["text_secondary"],
                tooltip="Refresh",
                on_click=handle_refresh,
            ),
        ],
    )

    # Info text
    info_text = ft.Text(
        "Manage dropdown values for various fields. [Editable] categories can be freely modified.",
        size=13,
        color=colors["text_secondary"],
    )

    # Category selection
    category_row = ft.Container(
        content=ft.Row(
            controls=[
                ft.Text("Category:", color=colors["text_secondary"]),
                ft.Dropdown(
                    ref=category_ref,
                    value="",
                    options=[ft.dropdown.Option("-- Select Category --", "")],
                    width=350,
                    text_size=13,
                    on_change=handle_category_change,
                ),
                ft.Container(expand=True),
                ft.ElevatedButton(
                    ref=add_btn_ref,
                    text="Add Value",
                    icon=ft.Icons.ADD,
                    bgcolor=colors["primary"],
                    color=ft.Colors.WHITE,
                    on_click=handle_add,
                    disabled=True,
                ),
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.all(12),
        bgcolor=colors["bg_tertiary"],
        border_radius=8,
    )

    # Status row
    status_row = ft.Text(
        ref=status_ref,
        value="",
        size=13,
        color=colors["text_secondary"],
    )

    # Loading indicator
    loading_container = ft.Container(
        ref=loading_ref,
        content=ft.Column(
            controls=[
                ft.ProgressRing(width=32, height=32, color=colors["primary"]),
                ft.Text("Loading values...", color=colors["text_secondary"]),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=8,
        ),
        expand=True,
        alignment=ft.alignment.center,
        visible=False,
    )

    # Table container
    table_container = ft.Container(
        ref=table_ref,
        content=ft.Text("Select a category to view values", color=colors["text_muted"]),
        expand=True,
    )

    # Admin-manageable notice
    notice = ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(ft.Icons.INFO_OUTLINE, color=colors["info"], size=16),
                ft.Text(
                    f"Admin-Manageable Categories: {', '.join(admin_manageable)}",
                    size=12,
                    color=colors["text_secondary"],
                ),
            ],
            spacing=8,
        ),
        padding=ft.padding.all(10),
        bgcolor=colors["bg_tertiary"],
        border_radius=4,
    )

    # Trigger initial load
    page.run_task(load_categories)

    return ft.Column(
        controls=[
            header_row,
            ft.Container(height=8),
            info_text,
            ft.Container(height=16),
            category_row,
            ft.Container(height=8),
            status_row,
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
            ft.Container(height=8),
            notice,
        ],
        spacing=0,
        expand=True,
    )
