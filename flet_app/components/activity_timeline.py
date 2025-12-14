"""
Activity Timeline Component for FIU Report Management System.
GitHub-style activity timeline showing user actions.
"""
import flet as ft
from typing import Optional, Any, Callable, List, Dict

from theme.theme_manager import theme_manager


# Action icons mapping
ACTION_ICONS = {
    'CREATE': ft.Icons.ADD_CIRCLE_OUTLINE,
    'UPDATE': ft.Icons.EDIT_NOTE,
    'DELETE': ft.Icons.DELETE_OUTLINE,
    'SOFT_DELETE': ft.Icons.DELETE_OUTLINE,
    'HARD_DELETE': ft.Icons.DELETE_FOREVER,
    'RESTORE': ft.Icons.RESTORE,
    'UNDELETE': ft.Icons.RESTORE_FROM_TRASH,
    'APPROVE': ft.Icons.CHECK_CIRCLE_OUTLINE,
    'REJECT': ft.Icons.CANCEL_OUTLINED,
    'VERSION_CREATE': ft.Icons.HISTORY,
    'VERSION_DELETE': ft.Icons.HISTORY_TOGGLE_OFF,
    'VERSION_RESTORE': ft.Icons.SETTINGS_BACKUP_RESTORE,
}

# Action colors mapping
ACTION_COLORS = {
    'CREATE': '#00d084',      # Green
    'UPDATE': '#ffa726',      # Orange
    'DELETE': '#f44336',      # Red
    'SOFT_DELETE': '#ff7043', # Light red
    'HARD_DELETE': '#d32f2f', # Dark red
    'RESTORE': '#4caf50',     # Green
    'UNDELETE': '#66bb6a',    # Light green
    'APPROVE': '#00d084',     # Green
    'REJECT': '#f44336',      # Red
    'VERSION_CREATE': '#2196f3',  # Blue
    'VERSION_DELETE': '#ff5722',  # Deep orange
    'VERSION_RESTORE': '#9c27b0', # Purple
}


def create_activity_timeline(
    page: ft.Page,
    app_state: Any,
    activities: List[Dict],
    show_report_link: bool = True,
    max_items: int = 10,
    on_report_click: Optional[Callable[[int], None]] = None,
    on_view_all: Optional[Callable[[], None]] = None,
    title: str = "Recent Activity",
    show_title: bool = True,
    compact: bool = False,
) -> ft.Container:
    """
    Create a GitHub-style activity timeline.

    Args:
        page: Flet page object
        app_state: Application state with services
        activities: List of activity dictionaries
        show_report_link: Whether to show clickable report links
        max_items: Maximum number of items to display
        on_report_click: Callback when a report link is clicked
        on_view_all: Callback for "View All" button
        title: Title for the timeline section
        show_title: Whether to show the title
        compact: Use compact mode for smaller displays

    Returns:
        Container with activity timeline
    """
    colors = theme_manager.get_colors()

    def create_activity_item(activity: Dict, is_last: bool = False) -> ft.Container:
        """Create a single activity item."""
        action_type = activity.get('action_type', 'UPDATE')
        username = activity.get('username', 'Unknown')
        description = activity.get('description', '')
        report_number = activity.get('report_number')
        report_id = activity.get('report_id')
        relative_time = activity.get('relative_time', '')
        metadata = activity.get('metadata', {})
        created_at = activity.get('created_at', '')

        # Get icon and color for action type
        icon = ACTION_ICONS.get(action_type, ft.Icons.INFO_OUTLINE)
        color = ACTION_COLORS.get(action_type, colors["text_secondary"])

        def handle_report_click(e):
            if on_report_click and report_id:
                on_report_click(report_id)

        # Build description with optional report link
        description_controls = []

        if description:
            description_controls.append(
                ft.Text(
                    description,
                    size=13 if not compact else 12,
                    color=colors["text_primary"],
                    expand=True,
                )
            )

        # Add metadata details if available
        if metadata and not compact:
            detail_texts = []
            if metadata.get('field_changes'):
                detail_texts.append(f"Changed: {', '.join(metadata['field_changes'][:3])}")
            if metadata.get('reason'):
                detail_texts.append(f"Reason: {metadata['reason']}")
            if metadata.get('delete_type'):
                detail_texts.append(f"Type: {metadata['delete_type']}")

            if detail_texts:
                description_controls.append(
                    ft.Text(
                        " • ".join(detail_texts),
                        size=11,
                        color=colors["text_secondary"],
                        italic=True,
                    )
                )

        # Main content
        content = ft.Row(
            controls=[
                # Timeline indicator (icon + line)
                ft.Column(
                    controls=[
                        ft.Container(
                            content=ft.Icon(icon, color=color, size=20 if not compact else 16),
                            width=36 if not compact else 28,
                            height=36 if not compact else 28,
                            border_radius=18 if not compact else 14,
                            bgcolor=f"{color}20",
                            alignment=ft.alignment.center,
                        ),
                        # Vertical line (not shown for last item)
                        ft.Container(
                            width=2,
                            height=20 if not compact else 12,
                            bgcolor=colors["border"] if not is_last else "transparent",
                        ) if not is_last else ft.Container(),
                    ],
                    spacing=0,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                # Content
                ft.Column(
                    controls=[
                        # Description
                        ft.Column(
                            controls=description_controls,
                            spacing=2,
                        ),
                        # Timestamp
                        ft.Text(
                            relative_time or created_at,
                            size=11 if not compact else 10,
                            color=colors["text_muted"],
                        ),
                    ],
                    spacing=4 if not compact else 2,
                    expand=True,
                ),
            ],
            spacing=12 if not compact else 8,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

        return ft.Container(
            content=content,
            padding=ft.padding.only(bottom=8 if not compact else 4),
        )

    # Build timeline items
    items = []
    display_activities = activities[:max_items] if max_items else activities

    for i, activity in enumerate(display_activities):
        is_last = (i == len(display_activities) - 1)
        items.append(create_activity_item(activity, is_last))

    # Empty state
    if not items:
        items.append(
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Icon(
                            ft.Icons.HISTORY,
                            color=colors["text_muted"],
                            size=32,
                        ),
                        ft.Text(
                            "No activity yet",
                            color=colors["text_secondary"],
                            size=13,
                        ),
                    ],
                    spacing=8,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                alignment=ft.alignment.center,
                padding=20,
            )
        )

    # Build header if needed
    header_controls = []
    if show_title:
        header_controls.append(
            ft.Row(
                controls=[
                    ft.Icon(ft.Icons.HISTORY, color=colors["primary"], size=20),
                    ft.Text(
                        title,
                        size=16 if not compact else 14,
                        weight=ft.FontWeight.W_600,
                        color=colors["text_primary"],
                        expand=True,
                    ),
                    ft.TextButton(
                        "View All",
                        on_click=lambda e: on_view_all() if on_view_all else None,
                        visible=on_view_all is not None and len(activities) > max_items,
                    ) if on_view_all else ft.Container(),
                ],
                spacing=8,
            )
        )
        header_controls.append(ft.Divider(color=colors["border"], height=1))

    # Combine all controls
    all_controls = header_controls + items

    # Show "more items" indicator if truncated
    if max_items and len(activities) > max_items:
        remaining = len(activities) - max_items
        all_controls.append(
            ft.Container(
                content=ft.Text(
                    f"+ {remaining} more activit{'y' if remaining == 1 else 'ies'}",
                    size=12,
                    color=colors["text_secondary"],
                    text_align=ft.TextAlign.CENTER,
                ),
                alignment=ft.alignment.center,
                padding=8,
            )
        )

    return ft.Container(
        content=ft.Column(
            controls=all_controls,
            spacing=8 if not compact else 4,
        ),
        padding=16 if not compact else 8,
        border_radius=8,
        bgcolor=colors["bg_secondary"],
        border=ft.border.all(1, colors["border"]),
    )


def create_activity_item_simple(
    activity: Dict,
    colors: Dict,
    on_click: Optional[Callable] = None,
) -> ft.Container:
    """
    Create a simple activity item for use in lists.

    Args:
        activity: Activity dictionary
        colors: Theme colors
        on_click: Click handler

    Returns:
        Container with activity item
    """
    action_type = activity.get('action_type', 'UPDATE')
    description = activity.get('description', '')
    relative_time = activity.get('relative_time', '')
    created_at = activity.get('created_at', '')

    icon = ACTION_ICONS.get(action_type, ft.Icons.INFO_OUTLINE)
    color = ACTION_COLORS.get(action_type, colors["text_secondary"])

    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Container(
                    content=ft.Icon(icon, color=color, size=16),
                    width=28,
                    height=28,
                    border_radius=14,
                    bgcolor=f"{color}20",
                    alignment=ft.alignment.center,
                ),
                ft.Column(
                    controls=[
                        ft.Text(
                            description,
                            size=12,
                            color=colors["text_primary"],
                        ),
                        ft.Text(
                            relative_time or created_at,
                            size=10,
                            color=colors["text_muted"],
                        ),
                    ],
                    spacing=2,
                    expand=True,
                ),
            ],
            spacing=8,
        ),
        padding=8,
        border_radius=4,
        on_click=on_click,
        ink=on_click is not None,
    )
