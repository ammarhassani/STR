"""
Chart Components for FIU Report Management System.
Uses lightweight Flet-native visualizations for fast rendering.
"""
import flet as ft
from typing import List, Dict, Any, Optional

from theme.theme_manager import theme_manager


def create_pie_chart(
    data: List[Dict[str, Any]],
    title: str = "",
    height: int = 250,
) -> ft.Container:
    """
    Create a lightweight pie chart visualization using Flet controls.

    Args:
        data: List of dicts with 'label' and 'value' keys
        title: Chart title
        height: Chart height

    Returns:
        Container with chart visualization
    """
    colors = theme_manager.get_colors()

    # Color palette
    chart_colors = [
        colors["primary"],
        colors["accent"],
        colors["info"],
        colors["warning"],
        colors["success"],
        colors["danger"],
        "#9c27b0",
        "#ff5722",
    ]

    if not data or all(d.get('value', 0) == 0 for d in data):
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(title, size=14, weight=ft.FontWeight.W_500, color=colors["text_primary"]),
                    ft.Container(
                        content=ft.Text("No data available", color=colors["text_muted"]),
                        alignment=ft.alignment.center,
                        expand=True,
                    ),
                ],
            ),
            height=height,
        )

    total = sum(d.get('value', 0) for d in data)

    # Build legend items with percentage bars
    legend_items = []
    for i, d in enumerate(data):
        label = d.get('label', 'Unknown')
        value = d.get('value', 0)
        percentage = (value / total * 100) if total > 0 else 0
        color = chart_colors[i % len(chart_colors)]

        legend_items.append(
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Container(
                                    width=12,
                                    height=12,
                                    bgcolor=color,
                                    border_radius=3,
                                ),
                                ft.Text(
                                    label,
                                    size=11,
                                    color=colors["text_primary"],
                                    expand=True,
                                ),
                                ft.Text(
                                    f"{value} ({percentage:.1f}%)",
                                    size=11,
                                    color=colors["text_secondary"],
                                ),
                            ],
                            spacing=8,
                        ),
                        # Progress bar showing percentage
                        ft.Container(
                            content=ft.Row(
                                controls=[
                                    ft.Container(
                                        width=percentage * 2,  # Scale to 200px max
                                        height=8,
                                        bgcolor=color,
                                        border_radius=4,
                                    ),
                                ],
                            ),
                            bgcolor=colors["bg_tertiary"],
                            border_radius=4,
                            height=8,
                            width=200,
                        ),
                    ],
                    spacing=4,
                ),
                padding=ft.padding.symmetric(vertical=4),
            )
        )

    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(title, size=14, weight=ft.FontWeight.W_500, color=colors["text_primary"]),
                ft.Container(height=8),
                ft.Column(
                    controls=legend_items,
                    spacing=8,
                    scroll=ft.ScrollMode.AUTO,
                ),
            ],
        ),
        height=height,
        padding=8,
    )


def create_bar_chart(
    data: List[Dict[str, Any]],
    title: str = "",
    height: int = 250,
    horizontal: bool = True,
) -> ft.Container:
    """
    Create a lightweight bar chart visualization using Flet controls.

    Args:
        data: List of dicts with 'label' and 'value' keys
        title: Chart title
        height: Chart height
        horizontal: Whether to use horizontal bars (always True for this impl)

    Returns:
        Container with chart visualization
    """
    colors = theme_manager.get_colors()

    if not data:
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(title, size=14, weight=ft.FontWeight.W_500, color=colors["text_primary"]),
                    ft.Container(
                        content=ft.Text("No data available", color=colors["text_muted"]),
                        alignment=ft.alignment.center,
                        expand=True,
                    ),
                ],
            ),
            height=height,
        )

    max_value = max(d.get('value', 0) for d in data) if data else 1
    if max_value == 0:
        max_value = 1

    bar_items = []
    for d in data:
        label = d.get('label', 'Unknown')
        value = d.get('value', 0)
        bar_width = (value / max_value) * 180  # Scale to 180px max

        bar_items.append(
            ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Container(
                            content=ft.Text(
                                label[:15] + "..." if len(label) > 15 else label,
                                size=11,
                                color=colors["text_secondary"],
                            ),
                            width=100,
                        ),
                        ft.Container(
                            content=ft.Row(
                                controls=[
                                    ft.Container(
                                        width=max(bar_width, 4),
                                        height=20,
                                        bgcolor=colors["primary"],
                                        border_radius=4,
                                    ),
                                    ft.Text(
                                        str(value),
                                        size=11,
                                        color=colors["text_primary"],
                                        weight=ft.FontWeight.W_500,
                                    ),
                                ],
                                spacing=8,
                            ),
                            expand=True,
                        ),
                    ],
                    spacing=8,
                ),
                padding=ft.padding.symmetric(vertical=2),
            )
        )

    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(title, size=14, weight=ft.FontWeight.W_500, color=colors["text_primary"]),
                ft.Container(height=8),
                ft.Column(
                    controls=bar_items,
                    spacing=4,
                    scroll=ft.ScrollMode.AUTO,
                ),
            ],
        ),
        height=height,
        padding=8,
    )


def create_line_chart(
    data: List[Dict[str, Any]],
    title: str = "",
    height: int = 250,
    x_key: str = "x",
    y_key: str = "y",
) -> ft.Container:
    """
    Create a lightweight line chart visualization using Flet controls.
    Shows data as a series of points with values.

    Args:
        data: List of dicts with x and y values
        title: Chart title
        height: Chart height
        x_key: Key for x values in data
        y_key: Key for y values in data

    Returns:
        Container with chart visualization
    """
    colors = theme_manager.get_colors()

    if not data:
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(title, size=14, weight=ft.FontWeight.W_500, color=colors["text_primary"]),
                    ft.Container(
                        content=ft.Text("No data available", color=colors["text_muted"]),
                        alignment=ft.alignment.center,
                        expand=True,
                    ),
                ],
            ),
            height=height,
        )

    max_value = max(d.get(y_key, 0) for d in data) if data else 1
    if max_value == 0:
        max_value = 1

    # Create a visual representation with dots and values
    points = []
    for d in data:
        x_val = str(d.get(x_key, ''))
        y_val = d.get(y_key, 0)
        bar_height = (y_val / max_value) * 100  # Scale to 100px max

        # Show only month part if it looks like a date
        display_x = x_val[-5:] if len(x_val) > 5 else x_val

        points.append(
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text(
                            str(y_val),
                            size=10,
                            color=colors["text_primary"],
                            weight=ft.FontWeight.W_500,
                        ),
                        ft.Container(
                            width=24,
                            height=max(bar_height, 4),
                            bgcolor=colors["primary"],
                            border_radius=ft.border_radius.only(top_left=4, top_right=4),
                        ),
                        ft.Text(
                            display_x,
                            size=8,
                            color=colors["text_muted"],
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=2,
                ),
                padding=2,
            )
        )

    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(title, size=14, weight=ft.FontWeight.W_500, color=colors["text_primary"]),
                ft.Container(height=8),
                ft.Container(
                    content=ft.Row(
                        controls=points,
                        alignment=ft.MainAxisAlignment.SPACE_EVENLY,
                        scroll=ft.ScrollMode.AUTO,
                    ),
                    height=140,
                    alignment=ft.alignment.bottom_center,
                ),
            ],
        ),
        height=height,
        padding=8,
    )


def create_multi_line_chart(
    datasets: List[Dict[str, Any]],
    title: str = "",
    height: int = 250,
) -> ft.Container:
    """
    Create a lightweight multi-series chart.

    Args:
        datasets: List of dicts with 'name', 'x', and 'y' keys
        title: Chart title
        height: Chart height

    Returns:
        Container with chart visualization
    """
    colors = theme_manager.get_colors()

    chart_colors = [
        colors["primary"],
        colors["accent"],
        colors["info"],
        colors["warning"],
    ]

    if not datasets:
        return ft.Container(
            content=ft.Text("No data available", color=colors["text_muted"]),
            height=height,
            alignment=ft.alignment.center,
        )

    # Build legend and summary
    items = []
    for i, dataset in enumerate(datasets):
        name = dataset.get('name', f'Series {i+1}')
        y_values = dataset.get('y', [])
        total = sum(y_values) if y_values else 0
        color = chart_colors[i % len(chart_colors)]

        items.append(
            ft.Row(
                controls=[
                    ft.Container(width=12, height=12, bgcolor=color, border_radius=3),
                    ft.Text(name, size=12, color=colors["text_primary"]),
                    ft.Text(f"Total: {total}", size=11, color=colors["text_secondary"]),
                ],
                spacing=8,
            )
        )

    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(title, size=14, weight=ft.FontWeight.W_500, color=colors["text_primary"]),
                ft.Container(height=8),
                ft.Column(controls=items, spacing=8),
            ],
        ),
        height=height,
        padding=8,
    )


def create_stat_display(
    label: str,
    value: Any,
    color: str = None,
    icon: str = None,
) -> ft.Container:
    """
    Create a simple stat display widget.

    Args:
        label: Stat label
        value: Stat value
        color: Optional color
        icon: Optional icon name

    Returns:
        Container with stat display
    """
    colors = theme_manager.get_colors()
    display_color = color or colors["primary"]

    controls = []
    if icon:
        controls.append(ft.Icon(icon, size=20, color=display_color))

    controls.extend([
        ft.Text(str(value), size=24, weight=ft.FontWeight.BOLD, color=colors["text_primary"]),
        ft.Text(label, size=11, color=colors["text_secondary"]),
    ])

    return ft.Container(
        content=ft.Column(
            controls=controls,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=4,
        ),
        padding=12,
        bgcolor=colors["card_bg"],
        border_radius=8,
        border=ft.border.all(1, colors["card_border"]),
    )
