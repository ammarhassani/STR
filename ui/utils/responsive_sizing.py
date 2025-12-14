"""
Responsive Sizing Utility Module

Provides DPI-aware sizing calculations for all UI components.
Ensures the application scales properly across different screen resolutions and DPI settings.
"""

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QSize


class ResponsiveSize:
    """
    Central responsive sizing calculator for DPI-aware UI components.

    All sizing should go through this class to ensure consistent scaling
    across different screen DPIs (100%, 125%, 150%, 200% scaling).
    """

    # Base DPI for Windows (standard)
    BASE_DPI = 96.0

    # Cache for calculated values to improve performance
    _cache = {}
    _last_dpi = None

    @classmethod
    def _get_current_dpi(cls):
        """Get current screen DPI."""
        screen = QApplication.primaryScreen()
        if screen:
            return screen.logicalDotsPerInch()
        return cls.BASE_DPI

    @classmethod
    def get_dpi_scale_factor(cls):
        """
        Get DPI scale factor relative to base DPI.

        Returns:
            float: Scale factor (1.0 for 96 DPI, 1.25 for 120 DPI, 1.5 for 144 DPI, etc.)
        """
        current_dpi = cls._get_current_dpi()

        # Clear cache if DPI changed
        if cls._last_dpi != current_dpi:
            cls._cache.clear()
            cls._last_dpi = current_dpi

        return current_dpi / cls.BASE_DPI

    @classmethod
    def get_scaled_size(cls, base_size, context=''):
        """
        Scale a pixel value by current DPI.

        Args:
            base_size: Base size in pixels (at 96 DPI)
            context: Optional context string for caching

        Returns:
            int: Scaled size in pixels
        """
        cache_key = f"{base_size}_{context}"

        if cache_key not in cls._cache:
            scale_factor = cls.get_dpi_scale_factor()
            scaled = int(base_size * scale_factor)
            cls._cache[cache_key] = scaled

        return cls._cache[cache_key]

    @classmethod
    def get_button_size(cls, context='medium'):
        """
        Get recommended button size for given context.

        Args:
            context: Button size context
                - 'table_action': Buttons in table action columns
                - 'small': Small buttons (28px height)
                - 'medium': Standard buttons (36px height)
                - 'large': Large primary buttons (40px height)

        Returns:
            tuple: (min_width, min_height) in pixels
        """
        sizes = {
            'table_action': (80, 32),
            'small': (70, 28),
            'medium': (90, 36),
            'large': (100, 40),
        }

        base_width, base_height = sizes.get(context, sizes['medium'])

        return (
            cls.get_scaled_size(base_width, f'btn_w_{context}'),
            cls.get_scaled_size(base_height, f'btn_h_{context}')
        )

    @classmethod
    def get_spacing(cls, level='normal'):
        """
        Get spacing value for layouts.

        Args:
            level: Spacing level
                - 'none': 0px
                - 'tight': 4px
                - 'normal': 8px
                - 'comfortable': 12px
                - 'spacious': 16px

        Returns:
            int: Spacing in pixels
        """
        spacings = {
            'none': 0,
            'tight': 4,
            'normal': 8,
            'comfortable': 12,
            'spacious': 16,
        }

        base_spacing = spacings.get(level, spacings['normal'])
        return cls.get_scaled_size(base_spacing, f'spacing_{level}')

    @classmethod
    def get_margin(cls, level='normal'):
        """
        Get margin value for containers.

        Args:
            level: Margin level
                - 'none': 0px
                - 'tight': 8px
                - 'normal': 16px
                - 'comfortable': 24px

        Returns:
            int: Margin in pixels
        """
        margins = {
            'none': 0,
            'tight': 8,
            'normal': 16,
            'comfortable': 24,
        }

        base_margin = margins.get(level, margins['normal'])
        return cls.get_scaled_size(base_margin, f'margin_{level}')

    @classmethod
    def get_margins(cls, level='normal'):
        """
        Get margins as tuple for setContentsMargins.

        Args:
            level: Margin level (same as get_margin)

        Returns:
            tuple: (left, top, right, bottom) margins
        """
        margin = cls.get_margin(level)
        return (margin, margin, margin, margin)

    @classmethod
    def get_row_height(cls, context='normal'):
        """
        Get recommended row height for tables.

        Args:
            context: Row context
                - 'compact': 40px
                - 'normal': 48px
                - 'comfortable': 56px

        Returns:
            int: Row height in pixels
        """
        heights = {
            'compact': 40,
            'normal': 48,
            'comfortable': 56,
        }

        base_height = heights.get(context, heights['normal'])
        return cls.get_scaled_size(base_height, f'row_{context}')

    @classmethod
    def get_icon_size(cls, size='medium'):
        """
        Get icon size.

        Args:
            size: Icon size
                - 'small': 16px
                - 'medium': 24px
                - 'large': 32px
                - 'xlarge': 48px
                - 'xxlarge': 80px

        Returns:
            QSize: Icon size
        """
        sizes = {
            'small': 16,
            'medium': 24,
            'large': 32,
            'xlarge': 48,
            'xxlarge': 80,
        }

        base_size = sizes.get(size, sizes['medium'])
        scaled_size = cls.get_scaled_size(base_size, f'icon_{size}')
        return QSize(scaled_size, scaled_size)

    @classmethod
    def get_font_size(cls, size='normal'):
        """
        Get font size in points.

        Args:
            size: Font size
                - 'small': 9pt
                - 'normal': 11pt
                - 'medium': 13pt
                - 'large': 14pt
                - 'xlarge': 16pt
                - 'title': 18pt

        Returns:
            int: Font size in points
        """
        sizes = {
            'small': 9,
            'normal': 11,
            'medium': 13,
            'large': 14,
            'xlarge': 16,
            'title': 18,
        }

        base_size = sizes.get(size, sizes['normal'])

        # Font sizes scale differently than pixel sizes
        # Use a more conservative scaling for fonts
        scale_factor = cls.get_dpi_scale_factor()
        if scale_factor > 1.5:
            # For very high DPI, cap font scaling at 1.3x
            font_scale = 1.0 + (scale_factor - 1.0) * 0.6
        else:
            font_scale = scale_factor

        return int(base_size * font_scale)

    @classmethod
    def get_screen_size(cls):
        """
        Get current screen size.

        Returns:
            tuple: (width, height) in pixels
        """
        screen = QApplication.primaryScreen()
        if screen:
            geometry = screen.geometry()
            return (geometry.width(), geometry.height())
        return (1920, 1080)  # Default fallback

    @classmethod
    def get_dialog_size(cls, size_category='medium'):
        """
        Get recommended dialog size based on screen size.

        Args:
            size_category: Dialog size category
                - 'small': 40% width × 50% height
                - 'medium': 60% width × 70% height
                - 'large': 75% width × 80% height
                - 'xlarge': 85% width × 85% height

        Returns:
            tuple: (width, height, min_width, min_height)
        """
        screen_width, screen_height = cls.get_screen_size()

        ratios = {
            'small': (0.4, 0.5, 400, 300),
            'medium': (0.6, 0.7, 600, 400),
            'large': (0.75, 0.8, 700, 500),
            'xlarge': (0.85, 0.85, 900, 600),
        }

        width_ratio, height_ratio, min_w, min_h = ratios.get(size_category, ratios['medium'])

        dialog_width = int(screen_width * width_ratio)
        dialog_height = int(screen_height * height_ratio)

        # Scale minimum sizes by DPI
        min_width = cls.get_scaled_size(min_w, f'dlg_min_w_{size_category}')
        min_height = cls.get_scaled_size(min_h, f'dlg_min_h_{size_category}')

        # Ensure we don't exceed screen bounds
        max_width = int(screen_width * 0.95)
        max_height = int(screen_height * 0.95)

        dialog_width = max(min_width, min(dialog_width, max_width))
        dialog_height = max(min_height, min(dialog_height, max_height))

        return (dialog_width, dialog_height, min_width, min_height)

    @classmethod
    def clear_cache(cls):
        """Clear the size cache. Call this when DPI changes."""
        cls._cache.clear()
        cls._last_dpi = None
