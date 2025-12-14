"""
Modern Theme System
Professional color schemes and styles with DPI-aware responsive sizing
"""

from ui.utils.responsive_sizing import ResponsiveSize


class ModernTheme:
    """Base theme with modern design principles"""

    # Color palette
    PRIMARY = "#1976D2"
    PRIMARY_DARK = "#1565C0"
    PRIMARY_LIGHT = "#42A5F5"

    SECONDARY = "#424242"
    SECONDARY_DARK = "#212121"
    SECONDARY_LIGHT = "#616161"

    SUCCESS = "#4CAF50"
    WARNING = "#FF9800"
    DANGER = "#F44336"
    INFO = "#2196F3"

    BACKGROUND = "#F5F7FA"
    SURFACE = "#FFFFFF"

    TEXT_PRIMARY = "#212121"
    TEXT_SECONDARY = "#757575"
    TEXT_DISABLED = "#BDBDBD"

    BORDER = "#E0E0E0"
    DIVIDER = "#EEEEEE"

    # Sidebar colors for proper contrast
    SIDEBAR_BG = "#2c3e50"
    SIDEBAR_TEXT = "#ecf0f1"  # Light gray text
    SIDEBAR_HOVER = "#34495e"

    # Table header colors
    HEADER_BG = "#34495e"  # Dark background
    HEADER_TEXT = "#ffffff"  # White text

    # Hover background for cards
    HOVER_BG = "#f8f9fa"  # Light hover background

    # Shadows
    SHADOW_SM = "0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24)"
    SHADOW_MD = "0 3px 6px rgba(0,0,0,0.15), 0 2px 4px rgba(0,0,0,0.12)"
    SHADOW_LG = "0 10px 20px rgba(0,0,0,0.15), 0 3px 6px rgba(0,0,0,0.10)"
    SHADOW_XL = "0 15px 25px rgba(0,0,0,0.15), 0 5px 10px rgba(0,0,0,0.05)"

    @classmethod
    def get_stylesheet(cls):
        # Calculate DPI-aware sizes
        card_radius = ResponsiveSize.get_scaled_size(12)
        card_padding = ResponsiveSize.get_scaled_size(16)
        header_padding = ResponsiveSize.get_scaled_size(8)

        # Button dimensions
        btn_radius = ResponsiveSize.get_scaled_size(8)
        btn_primary_padding_v = ResponsiveSize.get_scaled_size(12)
        btn_primary_padding_h = ResponsiveSize.get_scaled_size(24)
        btn_primary_height = ResponsiveSize.get_scaled_size(40)
        btn_primary_font = ResponsiveSize.get_font_size('large')

        btn_secondary_padding_v = ResponsiveSize.get_scaled_size(10)
        btn_secondary_padding_h = ResponsiveSize.get_scaled_size(20)
        btn_secondary_height = ResponsiveSize.get_scaled_size(36)
        btn_secondary_font = ResponsiveSize.get_font_size('medium')

        return f"""
            /* ========== Global Styles ========== */
            QMainWindow, QDialog, QWidget {{
                background-color: {cls.BACKGROUND};
                font-family: 'Segoe UI', 'Roboto', 'Arial', sans-serif;
            }}

            /* ========== Cards ========== */
            QWidget#card {{
                background-color: {cls.SURFACE};
                border-radius: {card_radius}px;
                border: 1px solid {cls.BORDER};
            }}

            QFrame#card {{
                background-color: {cls.SURFACE};
                border-radius: {card_radius}px;
                border: 1px solid {cls.BORDER};
            }}

            /* KPI Cards - Add visual definition */
            QFrame#kpiCard {{
                background-color: {cls.SURFACE};
                border: 1px solid {cls.BORDER};
                border-radius: {card_radius}px;
                padding: {card_padding}px;
            }}

            QFrame#kpiCard:hover {{
                border-color: {cls.PRIMARY};
                background-color: {cls.HOVER_BG};
            }}

            /* Welcome Section Container */
            QFrame#welcomeSection {{
                background-color: {cls.SURFACE};
                border-radius: {card_radius}px;
                padding: {card_padding}px;
            }}

            QLabel#welcomeTitle {{
                color: {cls.TEXT_PRIMARY};
            }}

            QLabel#welcomeSubtitle {{
                color: {cls.TEXT_SECONDARY};
            }}

            /* ========== Sidebar ========== */
            QWidget#sidebar {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {cls.PRIMARY_DARK}, stop:1 {cls.PRIMARY});
                border: none;
            }}

            /* ========== Buttons ========== */
            QPushButton#primary {{
                background-color: {cls.PRIMARY};
                color: white;
                border: none;
                border-radius: {btn_radius}px;
                padding: {btn_primary_padding_v}px {btn_primary_padding_h}px;
                font-size: {btn_primary_font}pt;
                font-weight: bold;
                min-height: {btn_primary_height}px;
            }}

            QPushButton#primary:hover {{
                background-color: {cls.PRIMARY_DARK};
            }}

            QPushButton#primary:pressed {{
                background-color: {cls.PRIMARY_DARK};
                padding: 13px 23px 11px 25px;
            }}

            QPushButton#secondary {{
                background-color: {cls.SECONDARY_LIGHT};
                color: white;
                border: none;
                border-radius: {btn_radius}px;
                padding: {btn_secondary_padding_v}px {btn_secondary_padding_h}px;
                font-size: {btn_secondary_font}pt;
                font-weight: 600;
                min-height: {btn_secondary_height}px;
            }}

            QPushButton#secondary:hover {{
                background-color: {cls.SECONDARY};
            }}

            QPushButton#success {{
                background-color: {cls.SUCCESS};
                color: white;
                border: none;
                border-radius: {btn_radius}px;
                padding: {btn_primary_padding_v}px {btn_primary_padding_h}px;
                font-size: {btn_primary_font}pt;
                font-weight: bold;
                min-height: {btn_primary_height}px;
            }}

            QPushButton#success:hover {{
                background-color: #45A049;
            }}

            QPushButton#danger {{
                background-color: {cls.DANGER};
                color: white;
                border: none;
                border-radius: {btn_radius}px;
                padding: {btn_secondary_padding_v}px {btn_secondary_padding_h}px;
                font-size: {btn_secondary_font}pt;
                font-weight: 600;
                min-height: {btn_secondary_height}px;
            }}

            QPushButton#danger:hover {{
                background-color: #D32F2F;
            }}

            QPushButton#outline {{
                background-color: transparent;
                color: {cls.PRIMARY};
                border: 2px solid {cls.PRIMARY};
                border-radius: {btn_radius}px;
                padding: {btn_secondary_padding_v}px {btn_secondary_padding_h}px;
                font-size: {btn_secondary_font}pt;
                font-weight: 600;
                min-height: {btn_secondary_height}px;
            }}

            QPushButton#outline:hover {{
                background-color: rgba(25, 118, 210, 0.08);
            }}

            QPushButton#navButton {{
                background-color: transparent;
                color: white;
                border: none;
                text-align: left;
                padding: {btn_primary_padding_v}px {btn_secondary_padding_h}px;
                font-size: {btn_primary_font}pt;
                font-weight: 500;
                border-left: {ResponsiveSize.get_scaled_size(4)}px solid transparent;
            }}

            QPushButton#navButton:hover {{
                background-color: rgba(255, 255, 255, 0.1);
                border-left: 4px solid rgba(255, 255, 255, 0.5);
            }}

            QPushButton#navButton:checked {{
                background-color: rgba(255, 255, 255, 0.15);
                border-left: 4px solid white;
                font-weight: bold;
            }}

            QPushButton#iconButton {{
                background-color: transparent;
                border: none;
                border-radius: 20px;
                padding: 8px;
                min-width: 40px;
                min-height: 40px;
            }}

            QPushButton#iconButton:hover {{
                background-color: rgba(0, 0, 0, 0.05);
            }}

            /* ========== Input Fields ========== */
            QLineEdit {{
                border: 2px solid {cls.BORDER};
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
                background-color: {cls.SURFACE};
                selection-background-color: {cls.PRIMARY_LIGHT};
                min-height: 40px;
            }}

            QLineEdit:focus {{
                border: 2px solid {cls.PRIMARY};
                background-color: white;
            }}

            QLineEdit:disabled {{
                background-color: #F5F5F5;
                color: {cls.TEXT_DISABLED};
            }}

            QTextEdit {{
                border: 2px solid {cls.BORDER};
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
                background-color: {cls.SURFACE};
                selection-background-color: {cls.PRIMARY_LIGHT};
            }}

            QTextEdit:focus {{
                border: 2px solid {cls.PRIMARY};
                background-color: white;
            }}

            /* ========== Dropdown/ComboBox ========== */
            QComboBox {{
                border: 2px solid {cls.BORDER};
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
                background-color: {cls.SURFACE};
                min-height: 40px;
            }}

            QComboBox:focus {{
                border: 2px solid {cls.PRIMARY};
            }}

            QComboBox::drop-down {{
                border: none;
                width: 30px;
            }}

            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid {cls.TEXT_SECONDARY};
                margin-right: 10px;
            }}

            QComboBox QAbstractItemView {{
                border: 1px solid {cls.BORDER};
                border-radius: 8px;
                background-color: white;
                selection-background-color: {cls.PRIMARY_LIGHT};
                padding: 4px;
            }}

            /* ========== Date Edit ========== */
            QDateEdit {{
                border: 2px solid {cls.BORDER};
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
                background-color: {cls.SURFACE};
                min-height: 40px;
            }}

            QDateEdit:focus {{
                border: 2px solid {cls.PRIMARY};
            }}

            QDateEdit::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: center right;
                width: 30px;
                border: none;
            }}

            QDateEdit::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid {cls.TEXT_SECONDARY};
                margin-right: 10px;
            }}

            QCalendarWidget {{
                background-color: white;
                border: 1px solid {cls.BORDER};
                border-radius: 8px;
            }}

            QCalendarWidget QWidget {{
                alternate-background-color: {cls.BACKGROUND};
            }}

            QCalendarWidget QAbstractItemView {{
                selection-background-color: {cls.PRIMARY};
                selection-color: white;
            }}

            /* ========== Tables ========== */
            QTableWidget {{
                background-color: {cls.SURFACE};
                border: 1px solid {cls.BORDER};
                border-radius: 12px;
                gridline-color: {cls.DIVIDER};
                font-size: 13px;
            }}

            QTableWidget::item {{
                padding: 12px;
                border-bottom: 1px solid {cls.DIVIDER};
            }}

            QTableWidget::item:selected {{
                background-color: {cls.PRIMARY_LIGHT};
                color: white;
            }}

            QTableWidget::item:hover {{
                background-color: rgba(25, 118, 210, 0.08);
            }}

            QHeaderView::section {{
                background-color: {cls.HEADER_BG};
                color: {cls.HEADER_TEXT};
                padding: {header_padding}px;
                border: none;
                border-bottom: 2px solid {cls.PRIMARY};
                font-weight: bold;
                font-size: 13px;
            }}

            QHeaderView::section:first {{
                border-top-left-radius: 12px;
            }}

            QHeaderView::section:last {{
                border-top-right-radius: 12px;
            }}

            /* ========== ScrollBar ========== */
            QScrollBar:vertical {{
                background: {cls.BACKGROUND};
                width: 12px;
                border-radius: 6px;
                margin: 0px;
            }}

            QScrollBar::handle:vertical {{
                background: {cls.BORDER};
                border-radius: 6px;
                min-height: 30px;
            }}

            QScrollBar::handle:vertical:hover {{
                background: {cls.TEXT_SECONDARY};
            }}

            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}

            QScrollBar:horizontal {{
                background: {cls.BACKGROUND};
                height: 12px;
                border-radius: 6px;
                margin: 0px;
            }}

            QScrollBar::handle:horizontal {{
                background: {cls.BORDER};
                border-radius: 6px;
                min-width: 30px;
            }}

            QScrollBar::handle:horizontal:hover {{
                background: {cls.TEXT_SECONDARY};
            }}

            /* ========== CheckBox ========== */
            QCheckBox {{
                spacing: 8px;
                font-size: 14px;
            }}

            QCheckBox::indicator {{
                width: 20px;
                height: 20px;
                border: 2px solid {cls.BORDER};
                border-radius: 4px;
                background-color: white;
            }}

            QCheckBox::indicator:hover {{
                border-color: {cls.PRIMARY};
            }}

            QCheckBox::indicator:checked {{
                background-color: {cls.PRIMARY};
                border-color: {cls.PRIMARY};
                image: url(none);
            }}

            /* ========== Labels ========== */
            QLabel#title {{
                font-size: 28px;
                font-weight: bold;
                color: {cls.TEXT_PRIMARY};
                padding: 0px;
            }}

            QLabel#subtitle {{
                font-size: 15px;
                color: {cls.TEXT_SECONDARY};
                padding: 0px;
            }}

            QLabel#sectionTitle {{
                font-size: 18px;
                font-weight: bold;
                color: {cls.TEXT_PRIMARY};
                padding: 8px 0px;
            }}

            QLabel#fieldLabel {{
                font-size: 13px;
                font-weight: 600;
                color: {cls.TEXT_SECONDARY};
                padding: 4px 0px;
            }}

            QLabel#statValue {{
                font-size: 36px;
                font-weight: bold;
                color: {cls.PRIMARY};
            }}

            QLabel#statLabel {{
                font-size: 14px;
                color: {cls.TEXT_SECONDARY};
                font-weight: 500;
            }}

            /* ========== Progress Bar ========== */
            QProgressBar {{
                border: none;
                border-radius: 8px;
                background-color: {cls.BACKGROUND};
                text-align: center;
                height: 24px;
            }}

            QProgressBar::chunk {{
                background-color: {cls.PRIMARY};
                border-radius: 8px;
            }}

            /* ========== Tooltips ========== */
            QToolTip {{
                background-color: {cls.SECONDARY_DARK};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px;
                font-size: 12px;
            }}

            /* ========== Message Boxes ========== */
            QMessageBox {{
                background-color: {cls.SURFACE};
            }}

            QMessageBox QLabel {{
                font-size: 14px;
                color: {cls.TEXT_PRIMARY};
            }}

            /* ========== Group Box ========== */
            QGroupBox {{
                border: 2px solid {cls.BORDER};
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
                font-weight: bold;
                font-size: 14px;
                color: {cls.TEXT_PRIMARY};
            }}

            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 4px 12px;
                background-color: {cls.SURFACE};
                border-radius: 4px;
            }}

            /* ========== Tab Widget ========== */
            QTabWidget::pane {{
                border: 1px solid {cls.BORDER};
                border-radius: 8px;
                background-color: {cls.SURFACE};
            }}

            QTabBar::tab {{
                background-color: {cls.BACKGROUND};
                color: {cls.TEXT_SECONDARY};
                padding: 12px 24px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 4px;
                font-weight: 600;
            }}

            QTabBar::tab:selected {{
                background-color: {cls.SURFACE};
                color: {cls.PRIMARY};
                border-bottom: 3px solid {cls.PRIMARY};
            }}

            QTabBar::tab:hover {{
                background-color: rgba(25, 118, 210, 0.08);
            }}
        """


class DarkTheme(ModernTheme):
    """Modern dark theme"""

    PRIMARY = "#64B5F6"
    PRIMARY_DARK = "#42A5F5"
    PRIMARY_LIGHT = "#90CAF9"

    SECONDARY = "#B0BEC5"
    SECONDARY_DARK = "#90A4AE"
    SECONDARY_LIGHT = "#CFD8DC"

    SUCCESS = "#66BB6A"
    WARNING = "#FFA726"
    DANGER = "#EF5350"
    INFO = "#42A5F5"

    BACKGROUND = "#1E1E1E"
    SURFACE = "#2D2D2D"

    TEXT_PRIMARY = "#FFFFFF"
    TEXT_SECONDARY = "#B0BEC5"
    TEXT_DISABLED = "#757575"

    BORDER = "#424242"
    DIVIDER = "#383838"

    # Sidebar colors for proper contrast
    SIDEBAR_BG = "#1e2936"
    SIDEBAR_TEXT = "#e1e4e8"
    SIDEBAR_HOVER = "#2d3748"

    # Table header colors
    HEADER_BG = "#1e2936"
    HEADER_TEXT = "#e1e4e8"

    # Hover background for cards
    HOVER_BG = "#3d5170"  # Darker hover background


class OceanTheme(ModernTheme):
    """Cool ocean blue theme"""

    PRIMARY = "#00ACC1"
    PRIMARY_DARK = "#00838F"
    PRIMARY_LIGHT = "#26C6DA"

    SUCCESS = "#26A69A"
    WARNING = "#FFA726"
    DANGER = "#EF5350"
    INFO = "#29B6F6"


class ForestTheme(ModernTheme):
    """Nature-inspired green theme"""

    PRIMARY = "#66BB6A"
    PRIMARY_DARK = "#43A047"
    PRIMARY_LIGHT = "#81C784"

    SUCCESS = "#66BB6A"
    WARNING = "#FFA726"
    DANGER = "#EF5350"
    INFO = "#42A5F5"


class SunsetTheme(ModernTheme):
    """Warm sunset orange theme"""

    PRIMARY = "#FF7043"
    PRIMARY_DARK = "#F4511E"
    PRIMARY_LIGHT = "#FF8A65"

    SUCCESS = "#66BB6A"
    WARNING = "#FFA726"
    DANGER = "#EF5350"
    INFO = "#42A5F5"


# Theme registry
THEMES = {
    'Modern Blue': ModernTheme,
    'Dark': DarkTheme,
    'Ocean': OceanTheme,
    'Forest': ForestTheme,
    'Sunset': SunsetTheme,
}


def get_theme(theme_name='Modern Blue'):
    """Get theme by name"""
    return THEMES.get(theme_name, ModernTheme)
