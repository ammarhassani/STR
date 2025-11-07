"""
Icon Service
Centralized icon management with QtAwesome integration and fallbacks.
"""

from typing import Optional
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import QStyle, QApplication


class IconService:
    """
    Service for managing icons throughout the application.

    Features:
    - QtAwesome integration for Font Awesome icons
    - SVG fallback support
    - Built-in Qt icons fallback
    - Consistent icon sizing
    - Theme-aware icons (dark/light mode)
    """

    # Icon size constants
    SMALL = 16
    MEDIUM = 24
    LARGE = 32
    XLARGE = 48

    def __init__(self):
        """Initialize icon service."""
        self._qtawesome = None
        self._init_qtawesome()

        # Icon mappings for fallback
        self._fallback_icons = {
            # Dashboard
            'dashboard': QStyle.StandardPixmap.SP_ComputerIcon,
            'chart-line': QStyle.StandardPixmap.SP_FileDialogDetailedView,
            'chart-bar': QStyle.StandardPixmap.SP_FileDialogDetailedView,
            'chart-pie': QStyle.StandardPixmap.SP_FileDialogDetailedView,

            # Reports
            'file-alt': QStyle.StandardPixmap.SP_FileIcon,
            'file-invoice': QStyle.StandardPixmap.SP_FileIcon,
            'clipboard-list': QStyle.StandardPixmap.SP_FileDialogListView,
            'plus': QStyle.StandardPixmap.SP_FileDialogNewFolder,
            'edit': QStyle.StandardPixmap.SP_FileDialogDetailedView,
            'trash': QStyle.StandardPixmap.SP_TrashIcon,
            'search': QStyle.StandardPixmap.SP_FileDialogContentsView,

            # Export
            'download': QStyle.StandardPixmap.SP_ArrowDown,
            'file-export': QStyle.StandardPixmap.SP_DialogSaveButton,
            'file-excel': QStyle.StandardPixmap.SP_FileIcon,
            'file-pdf': QStyle.StandardPixmap.SP_FileIcon,
            'file-csv': QStyle.StandardPixmap.SP_FileIcon,

            # Users & Admin
            'users': QStyle.StandardPixmap.SP_DesktopIcon,
            'user': QStyle.StandardPixmap.SP_DirIcon,
            'user-plus': QStyle.StandardPixmap.SP_FileDialogNewFolder,
            'user-edit': QStyle.StandardPixmap.SP_FileDialogDetailedView,
            'user-shield': QStyle.StandardPixmap.SP_DialogApplyButton,
            'lock': QStyle.StandardPixmap.SP_BrowserStop,
            'unlock': QStyle.StandardPixmap.SP_DialogOkButton,

            # Actions
            'save': QStyle.StandardPixmap.SP_DialogSaveButton,
            'check': QStyle.StandardPixmap.SP_DialogApplyButton,
            'times': QStyle.StandardPixmap.SP_DialogCloseButton,
            'refresh': QStyle.StandardPixmap.SP_BrowserReload,
            'filter': QStyle.StandardPixmap.SP_FileDialogDetailedView,
            'sort': QStyle.StandardPixmap.SP_FileDialogDetailedView,
            'print': QStyle.StandardPixmap.SP_DriveFDIcon,

            # Settings
            'cog': QStyle.StandardPixmap.SP_FileDialogInfoView,
            'sliders-h': QStyle.StandardPixmap.SP_FileDialogDetailedView,
            'palette': QStyle.StandardPixmap.SP_DesktopIcon,
            'bell': QStyle.StandardPixmap.SP_MessageBoxInformation,
            'shield-alt': QStyle.StandardPixmap.SP_MessageBoxWarning,

            # Navigation
            'arrow-left': QStyle.StandardPixmap.SP_ArrowLeft,
            'arrow-right': QStyle.StandardPixmap.SP_ArrowRight,
            'arrow-up': QStyle.StandardPixmap.SP_ArrowUp,
            'arrow-down': QStyle.StandardPixmap.SP_ArrowDown,
            'home': QStyle.StandardPixmap.SP_DirHomeIcon,
            'folder': QStyle.StandardPixmap.SP_DirIcon,
            'folder-open': QStyle.StandardPixmap.SP_DirOpenIcon,

            # Status
            'info-circle': QStyle.StandardPixmap.SP_MessageBoxInformation,
            'exclamation-triangle': QStyle.StandardPixmap.SP_MessageBoxWarning,
            'exclamation-circle': QStyle.StandardPixmap.SP_MessageBoxCritical,
            'check-circle': QStyle.StandardPixmap.SP_DialogApplyButton,
            'times-circle': QStyle.StandardPixmap.SP_DialogCloseButton,
            'question-circle': QStyle.StandardPixmap.SP_MessageBoxQuestion,

            # Misc
            'calendar': QStyle.StandardPixmap.SP_FileDialogDetailedView,
            'clock': QStyle.StandardPixmap.SP_BrowserReload,
            'history': QStyle.StandardPixmap.SP_BrowserReload,
            'key': QStyle.StandardPixmap.SP_DialogOkButton,
            'book': QStyle.StandardPixmap.SP_FileDialogDetailedView,
            'question': QStyle.StandardPixmap.SP_MessageBoxQuestion,
            'sign-out-alt': QStyle.StandardPixmap.SP_DialogCloseButton,
            'moon': QStyle.StandardPixmap.SP_DesktopIcon,
            'sun': QStyle.StandardPixmap.SP_DesktopIcon,
        }

    def _init_qtawesome(self):
        """Try to initialize QtAwesome."""
        try:
            import qtawesome as qta
            self._qtawesome = qta
        except ImportError:
            self._qtawesome = None

    def get_icon(self, name: str, color: Optional[str] = None, size: int = MEDIUM) -> QIcon:
        """
        Get an icon by name.

        Args:
            name: Icon name (Font Awesome icon name)
            color: Icon color (hex string)
            size: Icon size in pixels

        Returns:
            QIcon object
        """
        # Try QtAwesome first
        if self._qtawesome:
            try:
                options = {}
                if color:
                    options['color'] = color

                # Map common icon names to Font Awesome
                fa_name = self._map_to_fontawesome(name)
                return self._qtawesome.icon(fa_name, **options)
            except Exception:
                pass

        # Fallback to Qt standard icons
        return self._get_fallback_icon(name, color, size)

    def _map_to_fontawesome(self, name: str) -> str:
        """
        Map icon names to Font Awesome icon names.

        Args:
            name: Icon name

        Returns:
            Font Awesome icon name (e.g., 'fa5s.home')
        """
        # Font Awesome 5 solid icons
        fa_mapping = {
            # Dashboard
            'dashboard': 'fa5s.tachometer-alt',
            'chart-line': 'fa5s.chart-line',
            'chart-bar': 'fa5s.chart-bar',
            'chart-pie': 'fa5s.chart-pie',

            # Reports
            'file-alt': 'fa5s.file-alt',
            'file-invoice': 'fa5s.file-invoice',
            'clipboard-list': 'fa5s.clipboard-list',
            'plus': 'fa5s.plus',
            'edit': 'fa5s.edit',
            'trash': 'fa5s.trash',
            'search': 'fa5s.search',

            # Export
            'download': 'fa5s.download',
            'file-export': 'fa5s.file-export',
            'file-excel': 'fa5s.file-excel',
            'file-pdf': 'fa5s.file-pdf',
            'file-csv': 'fa5s.file-csv',

            # Users & Admin
            'users': 'fa5s.users',
            'user': 'fa5s.user',
            'user-plus': 'fa5s.user-plus',
            'user-edit': 'fa5s.user-edit',
            'user-shield': 'fa5s.user-shield',
            'lock': 'fa5s.lock',
            'unlock': 'fa5s.unlock',

            # Actions
            'save': 'fa5s.save',
            'check': 'fa5s.check',
            'times': 'fa5s.times',
            'refresh': 'fa5s.sync',
            'filter': 'fa5s.filter',
            'sort': 'fa5s.sort',
            'print': 'fa5s.print',

            # Settings
            'cog': 'fa5s.cog',
            'sliders-h': 'fa5s.sliders-h',
            'palette': 'fa5s.palette',
            'bell': 'fa5s.bell',
            'shield-alt': 'fa5s.shield-alt',

            # Navigation
            'arrow-left': 'fa5s.arrow-left',
            'arrow-right': 'fa5s.arrow-right',
            'arrow-up': 'fa5s.arrow-up',
            'arrow-down': 'fa5s.arrow-down',
            'home': 'fa5s.home',
            'folder': 'fa5s.folder',
            'folder-open': 'fa5s.folder-open',

            # Status
            'info-circle': 'fa5s.info-circle',
            'exclamation-triangle': 'fa5s.exclamation-triangle',
            'exclamation-circle': 'fa5s.exclamation-circle',
            'check-circle': 'fa5s.check-circle',
            'times-circle': 'fa5s.times-circle',
            'question-circle': 'fa5s.question-circle',

            # Misc
            'calendar': 'fa5s.calendar-alt',
            'clock': 'fa5s.clock',
            'history': 'fa5s.history',
            'key': 'fa5s.key',
            'book': 'fa5s.book',
            'question': 'fa5s.question',
            'sign-out-alt': 'fa5s.sign-out-alt',
            'moon': 'fa5s.moon',
            'sun': 'fa5s.sun',
        }

        return fa_mapping.get(name, f'fa5s.{name}')

    def _get_fallback_icon(self, name: str, color: Optional[str] = None, size: int = MEDIUM) -> QIcon:
        """
        Get fallback icon using Qt standard icons.

        Args:
            name: Icon name
            color: Icon color (hex string)
            size: Icon size in pixels

        Returns:
            QIcon object
        """
        app = QApplication.instance()
        if not app:
            return QIcon()

        style = app.style()

        # Get standard pixmap
        standard_pixmap = self._fallback_icons.get(name, QStyle.StandardPixmap.SP_FileIcon)
        icon = style.standardIcon(standard_pixmap)

        # If color specified, create colored version
        if color:
            pixmap = icon.pixmap(QSize(size, size))
            colored_pixmap = self._colorize_pixmap(pixmap, color)
            return QIcon(colored_pixmap)

        return icon

    def _colorize_pixmap(self, pixmap: QPixmap, color: str) -> QPixmap:
        """
        Colorize a pixmap.

        Args:
            pixmap: Source pixmap
            color: Target color (hex string)

        Returns:
            Colorized pixmap
        """
        colored_pixmap = QPixmap(pixmap.size())
        colored_pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(colored_pixmap)
        painter.setCompositionMode(QPainter.CompositionMode.SourceOver)
        painter.drawPixmap(0, 0, pixmap)
        painter.setCompositionMode(QPainter.CompositionMode.SourceIn)
        painter.fillRect(colored_pixmap.rect(), QColor(color))
        painter.end()

        return colored_pixmap

    def has_qtawesome(self) -> bool:
        """
        Check if QtAwesome is available.

        Returns:
            True if QtAwesome is available
        """
        return self._qtawesome is not None


# Global icon service instance
_icon_service = None


def get_icon_service() -> IconService:
    """
    Get the global icon service instance.

    Returns:
        IconService instance
    """
    global _icon_service
    if _icon_service is None:
        _icon_service = IconService()
    return _icon_service


def get_icon(name: str, color: Optional[str] = None, size: int = IconService.MEDIUM) -> QIcon:
    """
    Convenience function to get an icon.

    Args:
        name: Icon name
        color: Icon color (hex string)
        size: Icon size in pixels

    Returns:
        QIcon object
    """
    return get_icon_service().get_icon(name, color, size)
