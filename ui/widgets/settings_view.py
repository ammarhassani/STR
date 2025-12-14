"""
Settings View Widget
View that opens the settings dialog when shown.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton,
                             QFrame)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from services.icon_service import get_icon
from ui.dialogs.settings_dialog import SettingsDialog
from ui.theme_colors import ThemeColors


class SettingsView(QWidget):
    """
    Settings view widget.

    Provides access to the application settings dialog.
    """

    def __init__(self, settings_service, auth_service, main_window, db_manager=None, logging_service=None, parent=None):
        """
        Initialize settings view.

        Args:
            settings_service: SettingsService instance
            auth_service: AuthService instance
            main_window: Main window reference for applying settings
            db_manager: DatabaseManager instance (optional)
            logging_service: LoggingService instance (optional)
            parent: Parent widget
        """
        super().__init__(parent)
        self.settings_service = settings_service
        self.auth_service = auth_service
        self.main_window = main_window
        self.db_manager = db_manager
        self.logging_service = logging_service

        self.setup_ui()

    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        # Welcome section
        welcome_label = QLabel("Settings & Preferences")
        welcome_font = QFont()
        welcome_font.setPointSize(18)
        welcome_font.setWeight(QFont.Weight.Bold)
        welcome_label.setFont(welcome_font)
        layout.addWidget(welcome_label)

        desc_label = QLabel(
            "Configure application settings, appearance, notifications, security, and advanced options."
        )
        desc_label.setWordWrap(True)
        desc_label.setObjectName("subtitleLabel")
        layout.addWidget(desc_label)

        layout.addSpacing(20)

        # Settings card
        card = QFrame()
        card.setObjectName("card")
        card.setMinimumWidth(500)
        card.setMaximumWidth(600)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(16)

        # Icon and title
        card_title = QLabel("System Settings")
        card_title_font = QFont()
        card_title_font.setPointSize(14)
        card_title_font.setWeight(QFont.Weight.Bold)
        card_title.setFont(card_title_font)
        card_layout.addWidget(card_title)

        # Description
        settings_desc = QLabel(
            "Click the button below to open the comprehensive settings dialog where you can:\n\n"
            "• Configure appearance and layout\n"
            "• Configure notifications\n"
            "• Manage security settings\n"
            "• Adjust advanced options\n"
            "• Set user preferences"
        )
        settings_desc.setWordWrap(True)
        settings_desc.setObjectName("subtitleLabel")
        card_layout.addWidget(settings_desc)

        card_layout.addSpacing(10)

        # Open settings button
        open_settings_btn = QPushButton("Open Settings")
        open_settings_btn.setIcon(get_icon('cog', color=ThemeColors.ICON_DEFAULT))
        open_settings_btn.setObjectName("primaryButton")
        open_settings_btn.setMinimumHeight(40)
        open_settings_btn.clicked.connect(self.open_settings_dialog)
        card_layout.addWidget(open_settings_btn)

        layout.addWidget(card)
        layout.addStretch()

    def open_settings_dialog(self):
        """Open the settings dialog."""
        dialog = SettingsDialog(
            self.settings_service,
            self.auth_service,
            self.db_manager,
            self.logging_service,
            self
        )

        # Connect signals
        dialog.settings_changed.connect(self.on_settings_changed)

        dialog.exec()

    def on_settings_changed(self, settings: dict):
        """
        Handle settings change.

        Args:
            settings: New settings dictionary
        """
        # Settings have been saved, any additional processing can go here
        pass

    def refresh(self):
        """Refresh the view (called from main window)."""
        # Nothing to refresh in this view
        pass
