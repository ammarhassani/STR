"""
KPI Card Component for FIU Report Management System.
Displays key performance indicators with icons and styling.
"""
import flet as ft
from typing import Optional

from theme.theme_manager import theme_manager


def create_kpi_card(
    title: str,
    value: str,
    icon: str = ft.Icons.INFO,
    color: str = None,
    subtitle: str = None,
    on_click=None,
) -> ft.Container:
    """
    Create a KPI card component.

    Args:
        title: Card title
        value: Main value to display
        icon: Icon to display
        color: Accent color (defaults to primary)
        subtitle: Optional subtitle text
        on_click: Optional click handler

    Returns:
        KPI card container
    """
    colors = theme_manager.get_colors()
    accent_color = color or colors["primary"]

    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Container(
                            content=ft.Icon(icon, color=accent_color, size=24),
                            width=44,
                            height=44,
                            border_radius=10,
                            bgcolor=f"{accent_color}15",  # 15% opacity
                            alignment=ft.alignment.center,
                        ),
                        ft.Container(expand=True),
                        ft.Icon(
                            ft.Icons.ARROW_FORWARD_IOS,
                            color=colors["text_muted"],
                            size=14,
                        ) if on_click else ft.Container(),
                    ],
                ),
                ft.Container(height=12),
                ft.Text(
                    value,
                    size=32,
                    weight=ft.FontWeight.BOLD,
                    color=colors["text_primary"],
                ),
                ft.Text(
                    title,
                    size=13,
                    color=colors["text_secondary"],
                    weight=ft.FontWeight.W_500,
                ),
                ft.Text(
                    subtitle,
                    size=11,
                    color=colors["text_muted"],
                ) if subtitle else ft.Container(),
            ],
            spacing=4,
        ),
        padding=20,
        border_radius=12,
        bgcolor=colors["card_bg"],
        border=ft.border.all(1, colors["card_border"]),
        on_click=on_click,
        ink=True if on_click else False,
        animate=ft.animation.Animation(200, ft.AnimationCurve.EASE_OUT),
    )


def create_stat_card(
    title: str,
    value: str,
    icon: str = ft.Icons.INFO,
    variant: str = "info",
    change: str = None,
    change_positive: bool = True,
) -> ft.Container:
    """
    Create a stat card with optional change indicator.

    Args:
        title: Card title
        value: Main value
        icon: Icon to display
        variant: Color variant (info, success, warning, danger)
        change: Optional change text (e.g., "+12%")
        change_positive: Whether change is positive

    Returns:
        Stat card container
    """
    colors = theme_manager.get_colors()

    # Get variant color
    variant_colors = {
        "info": colors["info"],
        "success": colors["success"],
        "warning": colors["warning"],
        "danger": colors["danger"],
    }
    accent_color = variant_colors.get(variant, colors["primary"])

    # Change indicator
    change_row = ft.Row(
        controls=[
            ft.Icon(
                ft.Icons.TRENDING_UP if change_positive else ft.Icons.TRENDING_DOWN,
                color=colors["success"] if change_positive else colors["danger"],
                size=14,
            ),
            ft.Text(
                change,
                size=12,
                color=colors["success"] if change_positive else colors["danger"],
            ),
        ],
        spacing=4,
    ) if change else ft.Container()

    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Container(
                            content=ft.Icon(icon, color=accent_color, size=20),
                            width=40,
                            height=40,
                            border_radius=8,
                            bgcolor=f"{accent_color}20",
                            alignment=ft.alignment.center,
                        ),
                        ft.Column(
                            controls=[
                                ft.Text(
                                    title,
                                    size=12,
                                    color=colors["text_secondary"],
                                ),
                                ft.Text(
                                    value,
                                    size=24,
                                    weight=ft.FontWeight.BOLD,
                                    color=colors["text_primary"],
                                ),
                            ],
                            spacing=2,
                            expand=True,
                        ),
                    ],
                    spacing=12,
                ),
                change_row,
            ],
            spacing=8,
        ),
        padding=16,
        border_radius=12,
        bgcolor=colors["card_bg"],
        border=ft.border.all(1, colors["card_border"]),
    )


# Note: UserControl was removed in Flet 0.21+
# Use function-based components (create_kpi_card, create_stat_card) instead
