"""
Color palette for FIU Report Management System.
Supports both light and dark themes.
"""


class Colors:
    """Color constants for theming."""

    # Dark Theme Colors
    DARK = {
        # Backgrounds
        "bg_primary": "#0d1117",
        "bg_secondary": "#161b22",
        "bg_tertiary": "#1a1f26",
        "bg_elevated": "#21262d",

        # Text
        "text_primary": "#f0f6fc",
        "text_secondary": "#8b949e",
        "text_muted": "#6e7681",

        # Brand / Accent
        "primary": "#0d7377",
        "primary_light": "#14919b",
        "accent": "#32e0c4",

        # Status Colors
        "success": "#00d084",
        "success_bg": "rgba(0, 208, 132, 0.1)",
        "warning": "#ffa726",
        "warning_bg": "rgba(255, 167, 38, 0.1)",
        "danger": "#f44336",
        "danger_bg": "rgba(244, 67, 54, 0.1)",
        "info": "#2196f3",
        "info_bg": "rgba(33, 150, 243, 0.1)",

        # Borders
        "border": "#30363d",
        "border_light": "#21262d",

        # Interactive
        "hover": "#1f2937",
        "active": "#0d7377",
        "disabled": "#484f58",

        # Cards
        "card_bg": "#161b22",
        "card_border": "#30363d",

        # Sidebar
        "sidebar_bg": "#0d1117",
        "sidebar_item_hover": "#21262d",
        "sidebar_item_active": "#0d7377",
    }

    # Light Theme Colors
    LIGHT = {
        # Backgrounds
        "bg_primary": "#f5f7fa",
        "bg_secondary": "#ffffff",
        "bg_tertiary": "#e8eaed",
        "bg_elevated": "#ffffff",

        # Text
        "text_primary": "#212121",
        "text_secondary": "#757575",
        "text_muted": "#9e9e9e",

        # Brand / Accent
        "primary": "#0d7377",
        "primary_light": "#14919b",
        "accent": "#14919b",

        # Status Colors
        "success": "#4caf50",
        "success_bg": "rgba(76, 175, 80, 0.1)",
        "warning": "#ff9800",
        "warning_bg": "rgba(255, 152, 0, 0.1)",
        "danger": "#f44336",
        "danger_bg": "rgba(244, 67, 54, 0.1)",
        "info": "#2196f3",
        "info_bg": "rgba(33, 150, 243, 0.1)",

        # Borders
        "border": "#e0e0e0",
        "border_light": "#eeeeee",

        # Interactive
        "hover": "#f0f0f0",
        "active": "#0d7377",
        "disabled": "#bdbdbd",

        # Cards
        "card_bg": "#ffffff",
        "card_border": "#e0e0e0",

        # Sidebar
        "sidebar_bg": "#ffffff",
        "sidebar_item_hover": "#f5f5f5",
        "sidebar_item_active": "#0d7377",
    }

    @classmethod
    def get(cls, key: str, theme: str = "dark") -> str:
        """
        Get a color value by key.

        Args:
            key: Color key name
            theme: 'dark' or 'light'

        Returns:
            Color value string
        """
        palette = cls.DARK if theme == "dark" else cls.LIGHT
        return palette.get(key, "#000000")

    @classmethod
    def get_palette(cls, theme: str = "dark") -> dict:
        """Get the full color palette for a theme."""
        return cls.DARK if theme == "dark" else cls.LIGHT
