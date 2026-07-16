"""
Theme Manager for FIU Report Management System.
Handles light/dark theme switching with persistence.
"""
import flet as ft
from typing import Callable, List, Optional
from .colors import Colors


class ThemeManager:
    """
    Centralized theme management with persistence.
    Implements singleton pattern for global access.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._current_theme: str = "light"  # light-only (dark mode removed)
        self._listeners: List[Callable[[str], None]] = []
        self._page: Optional[ft.Page] = None
        self._settings_service = None
        self._auth_service = None
        self._initialized = True

    @property
    def current_theme(self) -> str:
        """Get the current theme name."""
        return self._current_theme

    @property
    def is_dark(self) -> bool:
        """Check if current theme is dark."""
        return self._current_theme == "dark"

    def initialize(self, page: ft.Page, settings_service=None, auth_service=None):
        """
        Initialize the theme manager with page and services.

        Args:
            page: Flet page object
            settings_service: Optional settings service for persistence
            auth_service: Optional auth service for user context
        """
        self._page = page
        self._settings_service = settings_service
        self._auth_service = auth_service

        # Load saved preference
        self.load_preference()

        # Apply theme to page
        self._apply_theme()

    def toggle_theme(self):
        """Dark mode removed — always light."""
        self.set_theme("light")

    def set_theme(self, theme_name: str):
        """Dark mode removed — force light regardless of the request."""
        self._current_theme = "light"
        self._apply_theme()
        for cb in self._listeners:
            try:
                cb("light")
            except Exception:
                pass

    def _apply_theme(self):
        """Apply the flat, light-only enterprise theme."""
        if not self._page:
            return
        self._current_theme = "light"
        self._page.theme_mode = ft.ThemeMode.LIGHT
        colors = Colors.get_palette("light")
        r = colors.get("radius", 4)
        none_tx = ft.PageTransitionsTheme(
            android=ft.PageTransitionTheme.NONE, ios=ft.PageTransitionTheme.NONE,
            macos=ft.PageTransitionTheme.NONE, windows=ft.PageTransitionTheme.NONE,
            linux=ft.PageTransitionTheme.NONE,
        )
        flat_button_theme = ft.ButtonTheme(
            shape=ft.RoundedRectangleBorder(radius=r),
            splash_color=ft.Colors.TRANSPARENT,
        )
        self._page.theme = ft.Theme(
            use_material3=True,
            visual_density=ft.VisualDensity.COMPACT,
            splash_color=ft.Colors.TRANSPARENT,
            highlight_color=ft.Colors.TRANSPARENT,
            hover_color=colors["hover"],
            shadow_color=ft.Colors.TRANSPARENT,
            page_transitions=none_tx,
            elevated_button_theme=flat_button_theme,
            text_button_theme=flat_button_theme,
            outlined_button_theme=flat_button_theme,
            filled_button_theme=flat_button_theme,
            color_scheme=ft.ColorScheme(
                primary=colors["primary"],
                secondary=colors["accent"],
                surface=colors["bg_secondary"],
                background=colors["bg_primary"],
                error=colors["danger"],
                on_primary=ft.Colors.WHITE,
                on_secondary=ft.Colors.WHITE,
                on_surface=colors["text_primary"],
                on_background=colors["text_primary"],
                surface_variant=colors["bg_tertiary"],
                outline=colors["border"],
            ),
            divider_theme=ft.DividerTheme(thickness=1, color=colors["border"]),
            dialog_theme=ft.DialogTheme(
                elevation=0, shadow_color=ft.Colors.TRANSPARENT,
                shape=ft.RoundedRectangleBorder(radius=r)),
            card_theme=ft.CardTheme(
                elevation=0, shadow_color=ft.Colors.TRANSPARENT,
                shape=ft.RoundedRectangleBorder(radius=r)),
            data_table_theme=ft.DataTableTheme(
                divider_thickness=1, heading_row_height=40,
                data_row_min_height=34, data_row_max_height=44),
        )
        self._page.dark_theme = self._page.theme
        self._page.update()

    def add_listener(self, callback: Callable[[str], None]):
        """
        Add a theme change listener.

        Args:
            callback: Function that receives the new theme name
        """
        if callback not in self._listeners:
            self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[str], None]):
        """Remove a theme change listener."""
        if callback in self._listeners:
            self._listeners.remove(callback)

    def _notify_listeners(self):
        """Notify all listeners of theme change."""
        for callback in self._listeners:
            try:
                callback(self._current_theme)
            except Exception as e:
                print(f"Error notifying theme listener: {e}")

    def _persist_preference(self):
        """Save theme preference to settings."""
        if not self._settings_service or not self._auth_service:
            return

        try:
            current_user = self._auth_service.get_current_user()
            if current_user:
                self._settings_service.save_setting(
                    'theme',
                    self._current_theme,
                    current_user['user_id']
                )
        except Exception as e:
            print(f"Error saving theme preference: {e}")

    def load_preference(self):
        """Load saved theme preference."""
        if not self._settings_service or not self._auth_service:
            return

        try:
            current_user = self._auth_service.get_current_user()
            if current_user:
                # Dark mode removed: ignore any stored 'dark' preference, stay light
                self._current_theme = "light"
        except Exception as e:
            print(f"Error loading theme preference: {e}")

    def get_color(self, key: str) -> str:
        """
        Get a color from the current theme.

        Args:
            key: Color key name

        Returns:
            Color value string
        """
        return Colors.get(key, self._current_theme)

    def get_colors(self) -> dict:
        """Get the full color palette for the current theme."""
        return Colors.get_palette(self._current_theme)


# Global instance
theme_manager = ThemeManager()
