"""
Report Number Reservation Dialog.

Owned-block model: a user reserves a block of numbers (they become "available"
and owned by that user), sees their own available numbers, and can transfer
selected numbers to another active agent. All data access goes through
report_number_service / approval_service — no raw SQL here.
"""
import flet as ft
from typing import Any

from theme.theme_manager import theme_manager
from components.app_button import app_button
from components.toast import show_success, show_error


def show_reservation_dialog(page: ft.Page, app_state: Any):
    """
    Show the "My Report Numbers" reservation dialog.

    Args:
        page: Flet page object
        app_state: Application state
    """
    colors = theme_manager.get_colors()
    report_number_service = app_state.report_number_service
    approval_service = app_state.approval_service
    current_user = app_state.current_user
    username = current_user['username']

    # State
    selected_numbers = set()  # report_numbers checked for transfer

    # Controls
    reserve_count_input = ft.TextField(
        label="Count",
        value="10",
        keyboard_type=ft.KeyboardType.NUMBER,
        width=100,
    )

    count_text = ft.Text("", size=12, color=colors["text_secondary"])

    numbers_list = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO)

    target_dropdown = ft.Dropdown(
        label="Transfer To",
        width=260,
        options=[],
    )

    def refresh_numbers():
        """Reload this user's available numbers from the service and rebuild the list."""
        nonlocal selected_numbers
        numbers_data = report_number_service.get_available_numbers(username)
        selected_numbers &= {n['report_number'] for n in numbers_data}
        count_text.value = f"You have {len(numbers_data)} available number(s)."

        numbers_list.controls.clear()
        if not numbers_data:
            numbers_list.controls.append(
                ft.Text("No available numbers. Reserve some above.", size=12, color=colors["text_muted"])
            )
        for n in numbers_data:
            rn = n['report_number']

            def on_check(e, rn=rn):
                if e.control.value:
                    selected_numbers.add(rn)
                else:
                    selected_numbers.discard(rn)

            label = f"{rn}   (SN {n['serial_number']})"
            if n.get('transferred_from'):
                label += f"   — received from {n['transferred_from']}"

            numbers_list.controls.append(
                ft.Row(
                    controls=[
                        ft.Checkbox(value=rn in selected_numbers, on_change=on_check),
                        ft.Text(label, size=12),
                    ],
                    spacing=4,
                )
            )

    def load_agents():
        """Populate the transfer-target dropdown from active agents (excluding self)."""
        agents = approval_service.get_active_agents() if approval_service else []
        target_dropdown.options = [
            ft.dropdown.Option(key=a['username'], text=f"{a['full_name']} ({a['username']})")
            for a in agents if a['username'] != username
        ]

    def do_reserve(e):
        try:
            count = int(reserve_count_input.value or "0")
        except ValueError:
            show_error(page, "Enter a valid number.")
            return

        success, allocated, message = report_number_service.reserve_block(username, count)
        if success:
            show_success(page, message)
            refresh_numbers()
        else:
            show_error(page, message)
        page.update()

    def do_transfer(e):
        target = target_dropdown.value
        if not target:
            show_error(page, "Select a recipient.")
            return
        if not selected_numbers:
            show_error(page, "Select at least one number to transfer.")
            return

        success, message = report_number_service.transfer_numbers(
            username, target, list(selected_numbers)
        )
        if success:
            show_success(page, message)
            selected_numbers.clear()
            refresh_numbers()
        else:
            show_error(page, message)
        page.update()

    def close_dialog(e):
        dialog.open = False
        page.update()

    load_agents()
    refresh_numbers()

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Row(
            controls=[
                ft.Icon(ft.Icons.NUMBERS, color=colors["primary"]),
                ft.Text("My Report Numbers", weight=ft.FontWeight.BOLD),
            ],
            spacing=12,
        ),
        content=ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            reserve_count_input,
                            app_button("Reserve", icon=ft.Icons.ADD, on_click=do_reserve, variant="primary"),
                        ],
                        spacing=12,
                    ),
                    ft.Divider(height=1, color=colors["border"]),
                    count_text,
                    ft.Container(
                        content=numbers_list,
                        height=200,
                        border=ft.border.all(1, colors["border"]),
                        border_radius=6,
                        padding=8,
                    ),
                    ft.Divider(height=1, color=colors["border"]),
                    ft.Text("Transfer Selected Numbers", size=13, weight=ft.FontWeight.BOLD),
                    ft.Row(
                        controls=[
                            target_dropdown,
                            app_button("Transfer", icon=ft.Icons.SEND, on_click=do_transfer, variant="secondary"),
                        ],
                        spacing=12,
                    ),
                ],
                spacing=12,
                tight=True,
            ),
            width=480,
            padding=8,
        ),
        actions=[
            ft.TextButton("Close", on_click=close_dialog),
        ],
    )

    page.overlay.append(dialog)
    dialog.open = True
    page.update()
