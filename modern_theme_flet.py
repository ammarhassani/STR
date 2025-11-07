"""
Modern Theme System for Flet
Beautiful color schemes and modern styling
"""
import flet as ft


class ModernTheme:
    """Modern color palette and styling"""

    # Primary colors
    PRIMARY = "#1976D2"
    PRIMARY_DARK = "#1565C0"
    PRIMARY_LIGHT = "#42A5F5"

    # Accent colors
    ACCENT = "#FF4081"
    SUCCESS = "#4CAF50"
    WARNING = "#FF9800"
    DANGER = "#F44336"
    INFO = "#2196F3"

    # Neutral colors
    BACKGROUND = "#F5F7FA"
    SURFACE = "#FFFFFF"
    TEXT_PRIMARY = "#212121"
    TEXT_SECONDARY = "#757575"
    BORDER = "#E0E0E0"

    @staticmethod
    def apply_to_page(page: ft.Page):
        """Apply modern theme to Flet page"""
        page.theme = ft.Theme(
            color_scheme_seed=ModernTheme.PRIMARY,
            use_material3=True,
        )
        page.bgcolor = ModernTheme.BACKGROUND
        page.padding = 0
        page.spacing = 0


def create_modern_card(**kwargs):
    """Create modern card with shadow"""
    return ft.Card(
        elevation=2,
        surface_tint_color=ft.Colors.BLUE_50,
        **kwargs
    )


def create_primary_button(text, icon=None, on_click=None, **kwargs):
    """Create modern primary button"""
    return ft.ElevatedButton(
        text=text,
        icon=icon,
        on_click=on_click,
        style=ft.ButtonStyle(
            bgcolor=ModernTheme.PRIMARY,
            color=ft.Colors.WHITE,
            padding=ft.padding.symmetric(horizontal=24, vertical=16),
            shape=ft.RoundedRectangleBorder(radius=8),
            elevation={"": 2, "hovered": 4},
        ),
        **kwargs
    )


def create_secondary_button(text, icon=None, on_click=None, **kwargs):
    """Create modern secondary button"""
    return ft.OutlinedButton(
        text=text,
        icon=icon,
        on_click=on_click,
        style=ft.ButtonStyle(
            color=ModernTheme.PRIMARY,
            padding=ft.padding.symmetric(horizontal=20, vertical=14),
            shape=ft.RoundedRectangleBorder(radius=8),
            side=ft.BorderSide(2, ModernTheme.PRIMARY),
        ),
        **kwargs
    )


def create_icon_button(icon, tooltip, on_click, color=None):
    """Create modern icon button"""
    return ft.IconButton(
        icon=icon,
        tooltip=tooltip,
        on_click=on_click,
        icon_color=color or ModernTheme.PRIMARY,
        style=ft.ButtonStyle(
            shape=ft.CircleBorder(),
            padding=12,
        )
    )


def create_text_field(label, hint_text="", prefix_icon=None, **kwargs):
    """Create modern text field"""
    return ft.TextField(
        label=label,
        hint_text=hint_text,
        prefix_icon=prefix_icon,
        border_radius=8,
        border_color=ModernTheme.BORDER,
        focused_border_color=ModernTheme.PRIMARY,
        **kwargs
    )


def create_dropdown(label, options, **kwargs):
    """Create modern dropdown"""
    return ft.Dropdown(
        label=label,
        options=options,
        border_radius=8,
        border_color=ModernTheme.BORDER,
        focused_border_color=ModernTheme.PRIMARY,
        **kwargs
    )


def create_section_header(title, subtitle=None):
    """Create modern section header"""
    controls = [
        ft.Text(
            title,
            size=24,
            weight=ft.FontWeight.BOLD,
            color=ModernTheme.TEXT_PRIMARY
        )
    ]

    if subtitle:
        controls.append(
            ft.Text(
                subtitle,
                size=14,
                color=ModernTheme.TEXT_SECONDARY
            )
        )

    return ft.Column(
        controls=controls,
        spacing=4,
    )


def create_stat_card(title, value, icon, color):
    """Create animated stat card"""
    return create_modern_card(
        content=ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(
                                icon,
                                size=40,
                                color=color
                            ),
                            ft.Text(
                                str(value),
                                size=36,
                                weight=ft.FontWeight.BOLD,
                                color=color
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Text(
                        title,
                        size=14,
                        color=ModernTheme.TEXT_SECONDARY,
                        weight=ft.FontWeight.W_500
                    ),
                ],
                spacing=8,
            ),
            padding=20,
            width=220,
            height=140,
            border_radius=12,
            gradient=ft.LinearGradient(
                begin=ft.alignment.top_left,
                end=ft.alignment.bottom_right,
                colors=[ft.Colors.WHITE, f"{color}10"],
            ),
        ),
    )


def create_status_badge(status):
    """Create colored status badge"""
    status_colors = {
        'Open': (ModernTheme.SUCCESS, "#E8F5E9"),
        'Under Investigation': (ModernTheme.WARNING, "#FFF3E0"),
        'Case Review': (ModernTheme.INFO, "#E3F2FD"),
        'Close Case': (ModernTheme.DANGER, "#FFEBEE"),
        'Closed with STR': (ModernTheme.TEXT_SECONDARY, "#F5F5F5"),
    }

    color, bgcolor = status_colors.get(status, (ModernTheme.TEXT_SECONDARY, "#F5F5F5"))

    return ft.Container(
        content=ft.Text(
            status,
            size=11,
            weight=ft.FontWeight.BOLD,
            color=color
        ),
        padding=ft.padding.symmetric(horizontal=12, vertical=6),
        bgcolor=bgcolor,
        border_radius=12,
    )


def create_search_bar(hint_text="Search...", on_submit=None, **kwargs):
    """Create modern search bar"""
    return ft.TextField(
        hint_text=f"🔍 {hint_text}",
        border_radius=24,
        border_color=ModernTheme.BORDER,
        focused_border_color=ModernTheme.PRIMARY,
        on_submit=on_submit,
        content_padding=ft.padding.symmetric(horizontal=20, vertical=14),
        **kwargs
    )


def create_app_bar(title, actions=None):
    """Create modern app bar"""
    return ft.Container(
        content=ft.Row(
            [
                ft.Text(
                    title,
                    size=20,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.WHITE
                ),
                ft.Row(
                    actions or [],
                    spacing=8,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        ),
        padding=16,
        bgcolor=ModernTheme.PRIMARY,
        gradient=ft.LinearGradient(
            begin=ft.alignment.center_left,
            end=ft.alignment.center_right,
            colors=[ModernTheme.PRIMARY_DARK, ModernTheme.PRIMARY],
        ),
    )
