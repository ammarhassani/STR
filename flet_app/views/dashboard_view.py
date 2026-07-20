"""
Dashboard View for FIU Report Management System.
Displays KPIs, charts, system overview, and GitHub-style activity feed.
"""
import flet as ft
import asyncio
from typing import Any, Optional, List

from theme.theme_manager import theme_manager
from components.kpi_card import create_kpi_card, create_stat_card
from components.charts import create_pie_chart, create_bar_chart, create_line_chart
from components.activity_timeline import create_activity_timeline, ACTION_ICONS, ACTION_COLORS
from components.widget_renderer import render_widget_grid
from i18n import t


def build_dashboard_content(
    page: ft.Page,
    app_state: Any,
    on_navigate: Optional[callable] = None,
) -> ft.Column:
    """
    Build the dashboard content with GitHub-style activity feed.

    Args:
        page: Flet page object
        app_state: Application state
        on_navigate: Optional callback for navigation (route -> None)

    Returns:
        Dashboard content column
    """
    colors = theme_manager.get_colors()

    # State
    state = {
        "is_loading": True,
        "stats": {
            "total_reports": 0,
            "open_reports": 0,
            "under_investigation": 0,
            "closed_cases": 0,
            "reports_this_month": 0,
            "active_users": 0,
        },
        "status_data": [],
        "monthly_data": [],
        "top_reporters": [],
        "recent_activities": [],
        "widgets": [],
    }

    # Refs for updating
    loading_ref = ft.Ref[ft.Container]()
    content_ref = ft.Ref[ft.Column]()
    widgets_ref = ft.Ref[ft.Container]()
    activity_ref = ft.Ref[ft.Container]()

    async def load_dashboard_data():
        """Load dashboard data asynchronously."""
        try:
            loop = asyncio.get_event_loop()

            # Config-driven widgets: whatever the admin has configured for this
            # role, each query run safely (read-only) by the service.
            role = app_state.get_user_role() or 'reporter'
            state["widgets"] = await loop.run_in_executor(
                None,
                app_state.dashboard_service.get_dashboard_widgets,
                role
            )

            # Load recent activities
            if app_state.activity_service:
                activities_result = await loop.run_in_executor(
                    None,
                    lambda: app_state.activity_service.get_recent_activities(limit=10)
                )
                state["recent_activities"] = activities_result[0] if activities_result else []
            else:
                state["recent_activities"] = []

            # Update UI
            state["is_loading"] = False
            update_dashboard_ui()

        except Exception as e:
            # Not print(): the packaged exe is windowed, so sys.stdout is None
            # and a dashboard that failed to load left no trace anywhere.
            try:
                app_state.logging_service.error(f"Error loading dashboard data: {e}")
            except Exception:
                pass
            state["is_loading"] = False
            if loading_ref.current:
                loading_ref.current.visible = False
            page.update()

    def update_dashboard_ui():
        """Update dashboard UI with loaded data."""
        if loading_ref.current:
            loading_ref.current.visible = False
        if content_ref.current:
            content_ref.current.visible = True

        # Render the config-driven widget grid
        if widgets_ref.current:
            widgets_ref.current.content = render_widget_grid(state["widgets"])

        # Update activity section
        if activity_ref.current:
            activity_ref.current.content = build_activity_section()

        page.update()

    def build_activity_section() -> ft.Column:
        """Build the activity section content."""
        activities = state["recent_activities"]

        if not activities:
            return ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.TIMELINE, color=colors["primary"], size=20),
                            ft.Text(
                                t("dash.recent_activity"),
                                size=16,
                                weight=ft.FontWeight.BOLD,
                                color=colors["text_primary"],
                            ),
                            ft.Container(expand=True),
                            ft.TextButton(
                                t("dash.view_all"),
                                style=ft.ButtonStyle(color=colors["primary"]),
                                on_click=lambda e: navigate_to_activity(),
                            ),
                        ],
                    ),
                    ft.Container(height=16),
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Icon(ft.Icons.HISTORY, color=colors["text_muted"], size=40),
                                ft.Text(
                                    t("dash.no_activity"),
                                    color=colors["text_muted"],
                                    size=14,
                                ),
                                ft.Text(
                                    "Activity will appear here as users perform actions",
                                    color=colors["text_muted"],
                                    size=12,
                                ),
                            ],
                            spacing=8,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        alignment=ft.alignment.center,
                        padding=24,
                    ),
                ],
            )

        # Build activity items
        activity_items = []
        for activity in activities[:10]:  # Show max 10 items
            action_type = activity.get('action_type', 'UPDATE')
            username = activity.get('username', 'Unknown')
            description = activity.get('description', '')
            report_number = activity.get('report_number')
            relative_time = activity.get('relative_time', '')
            created_at = activity.get('created_at', '')

            icon = ACTION_ICONS.get(action_type, ft.Icons.INFO_OUTLINE)
            color = ACTION_COLORS.get(action_type, colors["text_secondary"])

            activity_items.append(
                ft.Container(
                    content=ft.Row(
                        controls=[
                            # Icon
                            ft.Container(
                                content=ft.Icon(icon, color=color, size=16),
                                width=32,
                                height=32,
                                border_radius=16,
                                bgcolor=f"{color}20",
                                alignment=ft.alignment.center,
                            ),
                            # Content
                            ft.Column(
                                controls=[
                                    ft.Text(
                                        description,
                                        size=13,
                                        color=colors["text_primary"],
                                        max_lines=2,
                                        overflow=ft.TextOverflow.ELLIPSIS,
                                    ),
                                    ft.Text(
                                        relative_time or created_at,
                                        size=11,
                                        color=colors["text_muted"],
                                    ),
                                ],
                                spacing=2,
                                expand=True,
                            ),
                        ],
                        spacing=12,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                    ),
                    padding=ft.padding.symmetric(vertical=8),
                    border=ft.border.only(bottom=ft.BorderSide(1, colors["border"])),
                )
            )

        return ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.TIMELINE, color=colors["primary"], size=20),
                        ft.Text(
                            t("dash.recent_activity"),
                            size=16,
                            weight=ft.FontWeight.BOLD,
                            color=colors["text_primary"],
                        ),
                        ft.Container(expand=True),
                        ft.TextButton(
                            t("dash.view_all"),
                            style=ft.ButtonStyle(color=colors["primary"]),
                            on_click=lambda e: navigate_to_activity(),
                        ),
                    ],
                ),
                ft.Container(height=8),
                ft.Column(
                    controls=activity_items,
                    spacing=0,
                ),
            ],
        )

    def navigate_to_activity():
        """Navigate to the activity page."""
        if on_navigate:
            on_navigate("/activity")
        else:
            # Fallback - show a message to use the sidebar
            page.snack_bar = ft.SnackBar(
                content=ft.Text(t("dash.nav_activity_hint")),
                bgcolor=colors["info"],
            )
            page.snack_bar.open = True
            page.update()

    def handle_refresh(e):
        """Handle refresh button click."""
        state["is_loading"] = True
        if loading_ref.current:
            loading_ref.current.visible = True
        if content_ref.current:
            content_ref.current.visible = False
        page.update()
        page.run_task(load_dashboard_data)

    # Loading indicator
    loading_container = ft.Container(
        ref=loading_ref,
        content=ft.Column(
            controls=[
                ft.ProgressRing(width=48, height=48, color=colors["primary"]),
                ft.Text(t("dash.loading"), color=colors["text_secondary"]),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=16,
        ),
        alignment=ft.alignment.center,
        expand=True,
        visible=True,
    )

    # Activity section container
    activity_container = ft.Container(
        ref=activity_ref,
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.TIMELINE, color=colors["primary"], size=20),
                        ft.Text(
                            t("dash.recent_activity"),
                            size=16,
                            weight=ft.FontWeight.BOLD,
                            color=colors["text_primary"],
                        ),
                        ft.Container(expand=True),
                        ft.TextButton(
                            t("dash.view_all"),
                            style=ft.ButtonStyle(color=colors["primary"]),
                        ),
                    ],
                ),
                ft.Container(height=12),
                ft.Text(
                    t("dash.loading_activity"),
                    color=colors["text_muted"],
                    size=13,
                ),
            ],
        ),
        bgcolor=colors["card_bg"],
        border_radius=12,
        border=ft.border.all(1, colors["card_border"]),
        padding=20,
    )

    # Main content
    main_content = ft.Column(
        ref=content_ref,
        controls=[
            # Header row with refresh button
            ft.Row(
                controls=[
                    ft.Text(
                        t("dash.welcome", name=app_state.get_user_display_name()),
                        size=16,
                        color=colors["text_secondary"],
                    ),
                    ft.Container(expand=True),
                    ft.ElevatedButton(
                        t("dash.refresh"),
                        icon=ft.Icons.REFRESH,
                        on_click=handle_refresh,
                        style=ft.ButtonStyle(
                            bgcolor=colors["primary"],
                            color=ft.Colors.WHITE,
                        ),
                    ),
                ],
            ),
            ft.Container(height=16),

            # Config-driven widgets (KPIs, charts, tables — from dashboard_config)
            ft.Container(
                ref=widgets_ref,
                content=ft.Container(
                    content=ft.Text(t("dash.loading_widgets"), color=colors["text_muted"]),
                    alignment=ft.alignment.center, height=120,
                ),
            ),
            ft.Container(height=24),

            # Recent Activity
            activity_container,
        ],
        spacing=0,
        visible=False,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    # Trigger data load
    page.run_task(load_dashboard_data)

    return ft.Column(
        controls=[
            loading_container,
            main_content,
        ],
        expand=True,
    )


class DashboardView:
    """Dashboard view class for more complex state management."""

    def __init__(self, page: ft.Page, app_state: Any):
        self.page = page
        self.app_state = app_state
        self.is_loading = True
        self.stats = {}
        self.status_data = []
        self.monthly_data = []
        self.top_reporters = []

    async def load_data(self):
        """Load dashboard data."""
        try:
            loop = asyncio.get_event_loop()

            self.stats = await loop.run_in_executor(
                None,
                self.app_state.dashboard_service.get_summary_statistics
            )

            self.status_data = await loop.run_in_executor(
                None,
                self.app_state.dashboard_service.get_reports_by_status
            )

            self.monthly_data = await loop.run_in_executor(
                None,
                self.app_state.dashboard_service.get_reports_by_month,
                12
            )

            self.top_reporters = await loop.run_in_executor(
                None,
                self.app_state.dashboard_service.get_top_reporters,
                5
            )

            self.is_loading = False

        except Exception as e:
            print(f"Dashboard error: {e}")
            self.is_loading = False

    def build(self) -> ft.Control:
        """Build the dashboard view."""
        return build_dashboard_content(self.page, self.app_state)
