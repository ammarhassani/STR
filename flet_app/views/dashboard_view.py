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
    }

    # Refs for updating
    loading_ref = ft.Ref[ft.Container]()
    content_ref = ft.Ref[ft.Column]()
    total_ref = ft.Ref[ft.Text]()
    open_ref = ft.Ref[ft.Text]()
    investigation_ref = ft.Ref[ft.Text]()
    closed_ref = ft.Ref[ft.Text]()
    pie_chart_ref = ft.Ref[ft.Container]()
    bar_chart_ref = ft.Ref[ft.Container]()
    line_chart_ref = ft.Ref[ft.Container]()
    activity_ref = ft.Ref[ft.Container]()

    async def load_dashboard_data():
        """Load dashboard data asynchronously."""
        try:
            loop = asyncio.get_event_loop()

            # Load summary statistics
            state["stats"] = await loop.run_in_executor(
                None,
                app_state.dashboard_service.get_summary_statistics
            )

            # Load reports by status
            state["status_data"] = await loop.run_in_executor(
                None,
                app_state.dashboard_service.get_reports_by_status
            )

            # Load reports by month
            state["monthly_data"] = await loop.run_in_executor(
                None,
                app_state.dashboard_service.get_reports_by_month,
                12
            )

            # Load top reporters
            state["top_reporters"] = await loop.run_in_executor(
                None,
                app_state.dashboard_service.get_top_reporters,
                5
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
            print(f"Error loading dashboard data: {e}")
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

        # Update KPI values
        if total_ref.current:
            total_ref.current.value = str(state["stats"].get('total_reports', 0))
        if open_ref.current:
            open_ref.current.value = str(state["stats"].get('open_reports', 0))
        if investigation_ref.current:
            investigation_ref.current.value = str(state["stats"].get('under_investigation', 0))
        if closed_ref.current:
            closed_ref.current.value = str(state["stats"].get('closed_cases', 0))

        # Update pie chart with status data
        if pie_chart_ref.current and state["status_data"]:
            pie_chart_data = [{"label": d.get('status', 'Unknown'), "value": d.get('count', 0)} for d in state["status_data"]]
            new_pie = create_pie_chart(
                data=pie_chart_data,
                title="Reports by Status",
                height=250,
            )
            pie_chart_ref.current.content = new_pie.content

        # Update line chart with monthly trend
        if line_chart_ref.current and state["monthly_data"]:
            line_chart_data = [{"x": d.get('month', ''), "y": d.get('count', 0)} for d in state["monthly_data"]]
            new_line = create_line_chart(
                data=line_chart_data,
                title="Reports Trend (12 Months)",
                height=250,
                x_key="x",
                y_key="y",
            )
            line_chart_ref.current.content = new_line.content

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
                                "Recent Activity",
                                size=16,
                                weight=ft.FontWeight.BOLD,
                                color=colors["text_primary"],
                            ),
                            ft.Container(expand=True),
                            ft.TextButton(
                                "View All",
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
                                    "No recent activity",
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
                            "Recent Activity",
                            size=16,
                            weight=ft.FontWeight.BOLD,
                            color=colors["text_primary"],
                        ),
                        ft.Container(expand=True),
                        ft.TextButton(
                            "View All",
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
                content=ft.Text("Navigate to Activity Log in the sidebar"),
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
                ft.Text("Loading dashboard...", color=colors["text_secondary"]),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=16,
        ),
        alignment=ft.alignment.center,
        expand=True,
        visible=True,
    )

    # KPI Cards Row
    kpi_row = ft.Row(
        controls=[
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Container(
                                    content=ft.Icon(ft.Icons.DESCRIPTION, color=colors["info"], size=24),
                                    width=44,
                                    height=44,
                                    border_radius=10,
                                    bgcolor=f"{colors['info']}15",
                                    alignment=ft.alignment.center,
                                ),
                            ],
                        ),
                        ft.Container(height=12),
                        ft.Text(
                            ref=total_ref,
                            value="0",
                            size=32,
                            weight=ft.FontWeight.BOLD,
                            color=colors["text_primary"],
                        ),
                        ft.Text(
                            "Total Reports",
                            size=13,
                            color=colors["text_secondary"],
                            weight=ft.FontWeight.W_500,
                        ),
                    ],
                    spacing=4,
                ),
                padding=20,
                border_radius=12,
                bgcolor=colors["card_bg"],
                border=ft.border.all(1, colors["card_border"]),
                expand=True,
            ),
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Container(
                                    content=ft.Icon(ft.Icons.FOLDER_OPEN, color=colors["success"], size=24),
                                    width=44,
                                    height=44,
                                    border_radius=10,
                                    bgcolor=f"{colors['success']}15",
                                    alignment=ft.alignment.center,
                                ),
                            ],
                        ),
                        ft.Container(height=12),
                        ft.Text(
                            ref=open_ref,
                            value="0",
                            size=32,
                            weight=ft.FontWeight.BOLD,
                            color=colors["text_primary"],
                        ),
                        ft.Text(
                            "Open Reports",
                            size=13,
                            color=colors["text_secondary"],
                            weight=ft.FontWeight.W_500,
                        ),
                    ],
                    spacing=4,
                ),
                padding=20,
                border_radius=12,
                bgcolor=colors["card_bg"],
                border=ft.border.all(1, colors["card_border"]),
                expand=True,
            ),
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Container(
                                    content=ft.Icon(ft.Icons.SEARCH, color=colors["warning"], size=24),
                                    width=44,
                                    height=44,
                                    border_radius=10,
                                    bgcolor=f"{colors['warning']}15",
                                    alignment=ft.alignment.center,
                                ),
                            ],
                        ),
                        ft.Container(height=12),
                        ft.Text(
                            ref=investigation_ref,
                            value="0",
                            size=32,
                            weight=ft.FontWeight.BOLD,
                            color=colors["text_primary"],
                        ),
                        ft.Text(
                            "Under Investigation",
                            size=13,
                            color=colors["text_secondary"],
                            weight=ft.FontWeight.W_500,
                        ),
                    ],
                    spacing=4,
                ),
                padding=20,
                border_radius=12,
                bgcolor=colors["card_bg"],
                border=ft.border.all(1, colors["card_border"]),
                expand=True,
            ),
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Container(
                                    content=ft.Icon(ft.Icons.CHECK_CIRCLE, color=colors["danger"], size=24),
                                    width=44,
                                    height=44,
                                    border_radius=10,
                                    bgcolor=f"{colors['danger']}15",
                                    alignment=ft.alignment.center,
                                ),
                            ],
                        ),
                        ft.Container(height=12),
                        ft.Text(
                            ref=closed_ref,
                            value="0",
                            size=32,
                            weight=ft.FontWeight.BOLD,
                            color=colors["text_primary"],
                        ),
                        ft.Text(
                            "Closed Cases",
                            size=13,
                            color=colors["text_secondary"],
                            weight=ft.FontWeight.W_500,
                        ),
                    ],
                    spacing=4,
                ),
                padding=20,
                border_radius=12,
                bgcolor=colors["card_bg"],
                border=ft.border.all(1, colors["card_border"]),
                expand=True,
            ),
        ],
        spacing=16,
    )

    # Charts Row - will be updated after data loads
    charts_row = ft.Row(
        controls=[
            ft.Container(
                ref=pie_chart_ref,
                content=ft.Column(
                    controls=[
                        ft.Text("Reports by Status", size=14, weight=ft.FontWeight.W_500, color=colors["text_primary"]),
                        ft.Container(
                            content=ft.Text("Loading...", color=colors["text_muted"]),
                            alignment=ft.alignment.center,
                            height=200,
                        ),
                    ],
                ),
                bgcolor=colors["card_bg"],
                border_radius=12,
                border=ft.border.all(1, colors["card_border"]),
                padding=16,
                expand=True,
            ),
            ft.Container(
                ref=line_chart_ref,
                content=ft.Column(
                    controls=[
                        ft.Text("Reports Trend (12 Months)", size=14, weight=ft.FontWeight.W_500, color=colors["text_primary"]),
                        ft.Container(
                            content=ft.Text("Loading...", color=colors["text_muted"]),
                            alignment=ft.alignment.center,
                            height=200,
                        ),
                    ],
                ),
                bgcolor=colors["card_bg"],
                border_radius=12,
                border=ft.border.all(1, colors["card_border"]),
                padding=16,
                expand=True,
            ),
        ],
        spacing=16,
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
                            "Recent Activity",
                            size=16,
                            weight=ft.FontWeight.BOLD,
                            color=colors["text_primary"],
                        ),
                        ft.Container(expand=True),
                        ft.TextButton(
                            "View All",
                            style=ft.ButtonStyle(color=colors["primary"]),
                        ),
                    ],
                ),
                ft.Container(height=12),
                ft.Text(
                    "Loading activity...",
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
                        f"Welcome back, {app_state.get_user_display_name()}!",
                        size=16,
                        color=colors["text_secondary"],
                    ),
                    ft.Container(expand=True),
                    ft.ElevatedButton(
                        "Refresh",
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

            # KPI Cards
            kpi_row,
            ft.Container(height=24),

            # Charts
            charts_row,
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
