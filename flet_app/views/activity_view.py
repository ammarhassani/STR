"""
Activity View for FIU Report Management System.
Displays GitHub-style activity feed with filtering and pagination.
"""
import flet as ft
import asyncio
from typing import Any, Optional, List
from datetime import datetime, timedelta

from theme.theme_manager import theme_manager
from components.activity_timeline import create_activity_timeline, ACTION_ICONS, ACTION_COLORS


# Action type options for filtering
ACTION_TYPE_OPTIONS = [
    ('All', None),
    ('Creates', ['CREATE']),
    ('Updates', ['UPDATE']),
    ('Deletes', ['SOFT_DELETE', 'HARD_DELETE', 'DELETE']),
    ('Restores', ['RESTORE', 'UNDELETE']),
    ('Approvals', ['APPROVE', 'REJECT']),
    ('Versions', ['VERSION_CREATE', 'VERSION_DELETE', 'VERSION_RESTORE']),
]


def build_activity_view(
    page: ft.Page,
    app_state: Any,
) -> ft.Column:
    """
    Build the activity view.

    Args:
        page: Flet page object
        app_state: Application state

    Returns:
        Activity view column
    """
    colors = theme_manager.get_colors()

    # State
    activities = []
    total_count = 0
    current_page = 1
    page_size = 50
    is_loading = True

    # Filters
    action_type_filter = None
    user_filter = None
    date_from = datetime.now() - timedelta(days=30)
    date_to = datetime.now()
    date_filter_enabled = False

    # Refs
    loading_ref = ft.Ref[ft.Container]()
    content_ref = ft.Ref[ft.Container]()
    stats_ref = ft.Ref[ft.Text]()
    page_ref = ft.Ref[ft.Text]()
    prev_btn_ref = ft.Ref[ft.IconButton]()
    next_btn_ref = ft.Ref[ft.IconButton]()

    async def load_activities():
        """Load activities asynchronously."""
        nonlocal activities, total_count, is_loading

        is_loading = True
        if loading_ref.current:
            loading_ref.current.visible = True
        if content_ref.current:
            content_ref.current.visible = False
        page.update()

        try:
            loop = asyncio.get_event_loop()

            # Build filters
            df = date_from.strftime('%Y-%m-%d') if date_filter_enabled else None
            dt = date_to.strftime('%Y-%m-%d') if date_filter_enabled else None
            offset = (current_page - 1) * page_size

            # Load activities
            activities, total_count = await loop.run_in_executor(
                None,
                lambda: app_state.activity_service.get_recent_activities(
                    limit=page_size,
                    offset=offset,
                    user_id=user_filter,
                    action_types=action_type_filter,
                    date_from=df,
                    date_to=dt,
                ) if app_state.activity_service else ([], 0)
            )

            is_loading = False
            update_ui()

        except Exception as e:
            is_loading = False
            activities = []
            total_count = 0
            show_error(f"Failed to load activities: {str(e)}")
            update_ui()

    def update_ui():
        """Update the UI with loaded data."""
        if loading_ref.current:
            loading_ref.current.visible = False
        if content_ref.current:
            content_ref.current.visible = True

        # Update stats
        if stats_ref.current:
            stats_ref.current.value = f"Showing {len(activities)} of {total_count} activities"

        # Update pagination
        total_pages = max(1, (total_count + page_size - 1) // page_size)
        if page_ref.current:
            page_ref.current.value = f"Page {current_page} of {total_pages}"
        if prev_btn_ref.current:
            prev_btn_ref.current.disabled = current_page <= 1
        if next_btn_ref.current:
            next_btn_ref.current.disabled = current_page >= total_pages

        # Update activity list
        activity_list.controls.clear()

        if not activities:
            activity_list.controls.append(
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Icon(ft.Icons.HISTORY, color=colors["text_muted"], size=48),
                            ft.Text(
                                "No activity found",
                                size=16,
                                color=colors["text_secondary"],
                            ),
                            ft.Text(
                                "Activities will appear here when users perform actions",
                                size=13,
                                color=colors["text_muted"],
                            ),
                        ],
                        spacing=8,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    alignment=ft.alignment.center,
                    padding=40,
                )
            )
        else:
            for activity in activities:
                activity_list.controls.append(create_activity_row(activity))

        page.update()

    def create_activity_row(activity: dict) -> ft.Container:
        """Create a single activity row."""
        action_type = activity.get('action_type', 'UPDATE')
        username = activity.get('username', 'Unknown')
        description = activity.get('description', '')
        report_number = activity.get('report_number')
        report_id = activity.get('report_id')
        relative_time = activity.get('relative_time', '')
        created_at = activity.get('created_at', '')
        metadata = activity.get('metadata', {})

        icon = ACTION_ICONS.get(action_type, ft.Icons.INFO_OUTLINE)
        color = ACTION_COLORS.get(action_type, colors["text_secondary"])

        def open_report(e):
            if report_id:
                # Fetch report data and open dialog
                from dialogs.report_dialog import show_report_dialog
                report_data = app_state.report_service.get_report(report_id) if app_state.report_service else None
                if report_data:
                    show_report_dialog(
                        page=page,
                        app_state=app_state,
                        report_data=report_data,
                        on_save=lambda: page.run_task(load_activities),
                    )

        # Build metadata display
        metadata_text = ""
        if metadata:
            parts = []
            if metadata.get('reason'):
                parts.append(f"Reason: {metadata['reason']}")
            if metadata.get('delete_type'):
                parts.append(f"Type: {metadata['delete_type']}")
            if metadata.get('versions_deleted'):
                parts.append(f"Versions: {metadata['versions_deleted']}")
            metadata_text = " • ".join(parts)

        return ft.Container(
            content=ft.Row(
                controls=[
                    # Icon
                    ft.Container(
                        content=ft.Icon(icon, color=color, size=20),
                        width=40,
                        height=40,
                        border_radius=20,
                        bgcolor=f"{color}20",
                        alignment=ft.alignment.center,
                    ),
                    # Content
                    ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Text(
                                        description,
                                        size=14,
                                        color=colors["text_primary"],
                                        expand=True,
                                    ),
                                    ft.Container(
                                        content=ft.Text(
                                            action_type.replace('_', ' '),
                                            size=11,
                                            color=color,
                                        ),
                                        padding=ft.padding.symmetric(horizontal=8, vertical=2),
                                        border_radius=4,
                                        bgcolor=f"{color}20",
                                    ),
                                ],
                                spacing=8,
                            ),
                            ft.Row(
                                controls=[
                                    ft.Text(
                                        relative_time or created_at,
                                        size=12,
                                        color=colors["text_muted"],
                                    ),
                                    ft.Text(
                                        metadata_text,
                                        size=11,
                                        color=colors["text_secondary"],
                                        italic=True,
                                    ) if metadata_text else ft.Container(),
                                ],
                                spacing=16,
                            ),
                        ],
                        spacing=4,
                        expand=True,
                    ),
                    # Actions
                    ft.IconButton(
                        icon=ft.Icons.OPEN_IN_NEW,
                        icon_color=colors["primary"],
                        tooltip="Open Report",
                        on_click=open_report,
                        visible=report_id is not None,
                    ),
                ],
                spacing=16,
                vertical_alignment=ft.CrossAxisAlignment.START,
            ),
            padding=16,
            border=ft.border.only(bottom=ft.BorderSide(1, colors["border"])),
        )

    def handle_action_filter_change(e):
        nonlocal action_type_filter, current_page
        selected = e.control.value
        for label, types in ACTION_TYPE_OPTIONS:
            if label == selected:
                action_type_filter = types
                break
        current_page = 1
        page.run_task(load_activities)

    def handle_date_filter_toggle(e):
        nonlocal date_filter_enabled, current_page
        date_filter_enabled = e.control.value
        date_from_picker.visible = date_filter_enabled
        date_to_picker.visible = date_filter_enabled
        current_page = 1
        page.update()
        page.run_task(load_activities)

    def handle_prev_page(e):
        nonlocal current_page
        if current_page > 1:
            current_page -= 1
            page.run_task(load_activities)

    def handle_next_page(e):
        nonlocal current_page
        total_pages = max(1, (total_count + page_size - 1) // page_size)
        if current_page < total_pages:
            current_page += 1
            page.run_task(load_activities)

    def handle_refresh(e):
        nonlocal current_page
        current_page = 1
        page.run_task(load_activities)

    def show_error(message: str):
        page.snack_bar = ft.SnackBar(
            content=ft.Text(message),
            bgcolor=colors["danger"],
        )
        page.snack_bar.open = True
        page.update()

    # Date pickers (hidden by default)
    date_from_picker = ft.Container(visible=False)
    date_to_picker = ft.Container(visible=False)

    # Activity list
    activity_list = ft.Column(
        controls=[],
        spacing=0,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    # Build the view
    view = ft.Column(
        controls=[
            # Header
            ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.HISTORY, color=colors["primary"], size=28),
                        ft.Text(
                            "Activity Log",
                            size=24,
                            weight=ft.FontWeight.BOLD,
                            color=colors["text_primary"],
                        ),
                        ft.Container(expand=True),
                        ft.IconButton(
                            icon=ft.Icons.REFRESH,
                            icon_color=colors["primary"],
                            tooltip="Refresh",
                            on_click=handle_refresh,
                        ),
                    ],
                    spacing=12,
                ),
                padding=ft.padding.only(bottom=16),
            ),
            # Filters
            ft.Container(
                content=ft.Row(
                    controls=[
                        # Action type filter
                        ft.Dropdown(
                            label="Action Type",
                            width=180,
                            options=[ft.dropdown.Option(key=label, text=label) for label, _ in ACTION_TYPE_OPTIONS],
                            value="All",
                            on_change=handle_action_filter_change,
                            border_color=colors["border"],
                            focused_border_color=colors["primary"],
                        ),
                        # Date filter toggle
                        ft.Switch(
                            label="Date Filter",
                            value=False,
                            on_change=handle_date_filter_toggle,
                            active_color=colors["primary"],
                        ),
                        date_from_picker,
                        date_to_picker,
                        ft.Container(expand=True),
                        # Stats
                        ft.Text(
                            "Loading...",
                            ref=stats_ref,
                            size=13,
                            color=colors["text_secondary"],
                        ),
                    ],
                    spacing=16,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=ft.padding.only(bottom=16),
            ),
            # Loading indicator
            ft.Container(
                ref=loading_ref,
                content=ft.Column(
                    controls=[
                        ft.ProgressRing(width=32, height=32),
                        ft.Text("Loading activities...", color=colors["text_secondary"]),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=16,
                ),
                alignment=ft.alignment.center,
                padding=40,
                visible=True,
            ),
            # Content
            ft.Container(
                ref=content_ref,
                content=ft.Column(
                    controls=[
                        # Activity list container
                        ft.Container(
                            content=activity_list,
                            border=ft.border.all(1, colors["border"]),
                            border_radius=8,
                            expand=True,
                        ),
                        # Pagination
                        ft.Container(
                            content=ft.Row(
                                controls=[
                                    ft.IconButton(
                                        ref=prev_btn_ref,
                                        icon=ft.Icons.CHEVRON_LEFT,
                                        icon_color=colors["text_primary"],
                                        on_click=handle_prev_page,
                                        disabled=True,
                                    ),
                                    ft.Text(
                                        ref=page_ref,
                                        value="Page 1 of 1",
                                        size=13,
                                        color=colors["text_secondary"],
                                    ),
                                    ft.IconButton(
                                        ref=next_btn_ref,
                                        icon=ft.Icons.CHEVRON_RIGHT,
                                        icon_color=colors["text_primary"],
                                        on_click=handle_next_page,
                                        disabled=True,
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.CENTER,
                                spacing=8,
                            ),
                            padding=ft.padding.only(top=16),
                        ),
                    ],
                    expand=True,
                ),
                visible=False,
                expand=True,
            ),
        ],
        expand=True,
        spacing=0,
    )

    # Trigger initial load
    page.run_task(load_activities)

    return view
