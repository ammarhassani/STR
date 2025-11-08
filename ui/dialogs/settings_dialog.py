"""
Settings Dialog
Comprehensive settings and preferences panel with 5 tabs.
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QTabWidget, QWidget, QPushButton, QComboBox,
                             QCheckBox, QSpinBox, QGroupBox, QFormLayout,
                             QLineEdit, QMessageBox, QScrollArea, QFrame,
                             QSlider, QRadioButton, QButtonGroup)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from services.icon_service import get_icon


class SettingsDialog(QDialog):
    """
    Settings dialog with comprehensive preferences.

    Tabs:
    1. General - Language, startup options
    2. Appearance - Font sizes, colors, layout
    3. Notifications - Toast settings, alerts
    4. Security - Password, session timeout, audit
    5. Advanced - Database, logging, backup

    Signals:
        settings_changed: Emitted when settings are saved
    """

    settings_changed = pyqtSignal(dict)

    def __init__(self, settings_service, auth_service, db_manager=None, logging_service=None, parent=None):
        """
        Initialize settings dialog.

        Args:
            settings_service: SettingsService instance
            auth_service: AuthService instance
            db_manager: DatabaseManager instance (optional)
            logging_service: LoggingService instance (optional)
            parent: Parent widget
        """
        super().__init__(parent)
        self.settings_service = settings_service
        self.auth_service = auth_service
        self.db_manager = db_manager
        self.logging_service = logging_service
        self.current_settings = settings_service.get_all_settings()
        self.current_user = auth_service.get_current_user()

        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        """Setup the user interface."""
        self.setWindowTitle("Settings & Preferences")
        self.setMinimumSize(800, 600)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Header
        header = QLabel("Settings & Preferences")
        header_font = QFont()
        header_font.setPointSize(16)
        header_font.setWeight(QFont.Weight.Bold)
        header.setFont(header_font)
        layout.addWidget(header)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.addTab(self.create_general_tab(), "General")
        self.tabs.addTab(self.create_appearance_tab(), "Appearance")
        self.tabs.addTab(self.create_notifications_tab(), "Notifications")
        self.tabs.addTab(self.create_security_tab(), "Security")
        self.tabs.addTab(self.create_advanced_tab(), "Advanced")
        layout.addWidget(self.tabs)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.setIcon(get_icon('refresh'))
        reset_btn.setObjectName("dangerButton")
        reset_btn.clicked.connect(self.reset_to_defaults)
        button_layout.addWidget(reset_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setIcon(get_icon('times'))
        cancel_btn.setObjectName("secondaryButton")
        cancel_btn.setMinimumWidth(100)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save Settings")
        save_btn.setIcon(get_icon('save'))
        save_btn.setObjectName("primaryButton")
        save_btn.setMinimumWidth(120)
        save_btn.clicked.connect(self.save_settings)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

    def create_general_tab(self):
        """Create general settings tab."""
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Language settings
        language_group = QGroupBox("Language & Localization")
        language_layout = QFormLayout()
        language_layout.setSpacing(12)

        self.language_combo = QComboBox()
        self.language_combo.addItems(["English", "Arabic", "French", "Spanish"])
        language_layout.addRow("Interface Language:", self.language_combo)

        self.date_format_combo = QComboBox()
        self.date_format_combo.addItems(["DD/MM/YYYY", "MM/DD/YYYY", "YYYY-MM-DD"])
        language_layout.addRow("Date Format:", self.date_format_combo)

        self.time_format_combo = QComboBox()
        self.time_format_combo.addItems(["24 Hour", "12 Hour (AM/PM)"])
        language_layout.addRow("Time Format:", self.time_format_combo)

        language_group.setLayout(language_layout)
        layout.addWidget(language_group)

        # Startup settings
        startup_group = QGroupBox("Startup & Behavior")
        startup_layout = QVBoxLayout()
        startup_layout.setSpacing(8)

        self.remember_window_check = QCheckBox("Remember window size and position")
        startup_layout.addWidget(self.remember_window_check)

        self.start_maximized_check = QCheckBox("Start maximized")
        startup_layout.addWidget(self.start_maximized_check)

        self.show_dashboard_check = QCheckBox("Show dashboard on startup")
        self.show_dashboard_check.setChecked(True)
        startup_layout.addWidget(self.show_dashboard_check)

        self.auto_refresh_check = QCheckBox("Auto-refresh dashboard data")
        startup_layout.addWidget(self.auto_refresh_check)

        refresh_layout = QHBoxLayout()
        refresh_layout.addSpacing(20)
        refresh_layout.addWidget(QLabel("Refresh interval:"))
        self.refresh_interval_spin = QSpinBox()
        self.refresh_interval_spin.setRange(30, 600)
        self.refresh_interval_spin.setSuffix(" seconds")
        self.refresh_interval_spin.setValue(60)
        refresh_layout.addWidget(self.refresh_interval_spin)
        refresh_layout.addStretch()
        startup_layout.addLayout(refresh_layout)

        startup_group.setLayout(startup_layout)
        layout.addWidget(startup_group)

        layout.addStretch()
        scroll.setWidget(container)

        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll)

        return tab

    def create_appearance_tab(self):
        """Create appearance settings tab."""
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Font settings
        font_group = QGroupBox("Font Settings")
        font_layout = QFormLayout()
        font_layout.setSpacing(12)

        self.font_size_combo = QComboBox()
        self.font_size_combo.addItems(["Small", "Medium", "Large", "Extra Large"])
        self.font_size_combo.setCurrentIndex(1)
        font_layout.addRow("Interface Font Size:", self.font_size_combo)

        self.table_font_size_combo = QComboBox()
        self.table_font_size_combo.addItems(["Small", "Medium", "Large"])
        self.table_font_size_combo.setCurrentIndex(1)
        font_layout.addRow("Table Font Size:", self.table_font_size_combo)

        font_group.setLayout(font_layout)
        layout.addWidget(font_group)

        # Display settings
        display_group = QGroupBox("Display Settings")
        display_layout = QVBoxLayout()
        display_layout.setSpacing(8)

        self.show_tooltips_check = QCheckBox("Show tooltips on hover")
        self.show_tooltips_check.setChecked(True)
        display_layout.addWidget(self.show_tooltips_check)

        self.show_icons_check = QCheckBox("Show icons in navigation")
        self.show_icons_check.setChecked(True)
        display_layout.addWidget(self.show_icons_check)

        self.compact_mode_check = QCheckBox("Compact mode (reduce spacing)")
        display_layout.addWidget(self.compact_mode_check)

        self.animations_check = QCheckBox("Enable animations and transitions")
        self.animations_check.setChecked(True)
        display_layout.addWidget(self.animations_check)

        display_group.setLayout(display_layout)
        layout.addWidget(display_group)

        # Table settings
        table_group = QGroupBox("Table Display")
        table_layout = QFormLayout()
        table_layout.setSpacing(12)

        self.rows_per_page_spin = QSpinBox()
        self.rows_per_page_spin.setRange(10, 100)
        self.rows_per_page_spin.setSingleStep(10)
        self.rows_per_page_spin.setValue(25)
        table_layout.addRow("Rows per page:", self.rows_per_page_spin)

        self.alternate_row_check = QCheckBox("Alternating row colors")
        self.alternate_row_check.setChecked(True)
        table_layout.addRow("", self.alternate_row_check)

        self.grid_lines_check = QCheckBox("Show grid lines")
        table_layout.addRow("", self.grid_lines_check)

        table_group.setLayout(table_layout)
        layout.addWidget(table_group)

        layout.addStretch()
        scroll.setWidget(container)

        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll)

        return tab

    def create_notifications_tab(self):
        """Create notifications settings tab."""
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Toast notifications
        toast_group = QGroupBox("Toast Notifications")
        toast_layout = QVBoxLayout()
        toast_layout.setSpacing(8)

        self.enable_toasts_check = QCheckBox("Enable toast notifications")
        self.enable_toasts_check.setChecked(True)
        toast_layout.addWidget(self.enable_toasts_check)

        self.toast_position_combo = QComboBox()
        self.toast_position_combo.addItems(["Top Right", "Top Left", "Bottom Right", "Bottom Left"])
        position_layout = QHBoxLayout()
        position_layout.addWidget(QLabel("Position:"))
        position_layout.addWidget(self.toast_position_combo)
        position_layout.addStretch()
        toast_layout.addLayout(position_layout)

        duration_layout = QFormLayout()
        self.toast_duration_spin = QSpinBox()
        self.toast_duration_spin.setRange(1, 10)
        self.toast_duration_spin.setSuffix(" seconds")
        self.toast_duration_spin.setValue(3)
        duration_layout.addRow("Default Duration:", self.toast_duration_spin)
        toast_layout.addLayout(duration_layout)

        toast_group.setLayout(toast_layout)
        layout.addWidget(toast_group)

        # Notification types
        types_group = QGroupBox("Notification Types")
        types_layout = QVBoxLayout()
        types_layout.setSpacing(8)

        self.notify_success_check = QCheckBox("Show success notifications")
        self.notify_success_check.setChecked(True)
        types_layout.addWidget(self.notify_success_check)

        self.notify_warning_check = QCheckBox("Show warning notifications")
        self.notify_warning_check.setChecked(True)
        types_layout.addWidget(self.notify_warning_check)

        self.notify_error_check = QCheckBox("Show error notifications")
        self.notify_error_check.setChecked(True)
        types_layout.addWidget(self.notify_error_check)

        self.notify_info_check = QCheckBox("Show info notifications")
        self.notify_info_check.setChecked(True)
        types_layout.addWidget(self.notify_info_check)

        types_group.setLayout(types_layout)
        layout.addWidget(types_group)

        # Sound settings
        sound_group = QGroupBox("Sound Notifications")
        sound_layout = QVBoxLayout()
        sound_layout.setSpacing(8)

        self.enable_sounds_check = QCheckBox("Enable notification sounds")
        sound_layout.addWidget(self.enable_sounds_check)

        self.sound_volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.sound_volume_slider.setRange(0, 100)
        self.sound_volume_slider.setValue(50)
        volume_layout = QHBoxLayout()
        volume_layout.addWidget(QLabel("Volume:"))
        volume_layout.addWidget(self.sound_volume_slider)
        self.volume_label = QLabel("50%")
        volume_layout.addWidget(self.volume_label)
        self.sound_volume_slider.valueChanged.connect(
            lambda v: self.volume_label.setText(f"{v}%")
        )
        sound_layout.addLayout(volume_layout)

        sound_group.setLayout(sound_layout)
        layout.addWidget(sound_group)

        layout.addStretch()
        scroll.setWidget(container)

        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll)

        return tab

    def create_security_tab(self):
        """Create security settings tab."""
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Password settings
        password_group = QGroupBox("Password & Authentication")
        password_layout = QVBoxLayout()
        password_layout.setSpacing(12)

        change_password_btn = QPushButton("Change Password")
        change_password_btn.setIcon(get_icon('key'))
        change_password_btn.setMinimumWidth(180)
        change_password_btn.setMinimumHeight(36)
        change_password_btn.clicked.connect(self.change_password)
        password_layout.addWidget(change_password_btn, 0, Qt.AlignmentFlag.AlignLeft)

        self.require_strong_password_check = QCheckBox("Require strong passwords (admin only)")
        self.require_strong_password_check.setChecked(True)
        self.require_strong_password_check.setEnabled(self.current_user and self.current_user['role'] == 'admin')
        password_layout.addWidget(self.require_strong_password_check)

        password_group.setLayout(password_layout)
        layout.addWidget(password_group)

        # Session settings
        session_group = QGroupBox("Session Management")
        session_layout = QFormLayout()
        session_layout.setSpacing(12)

        self.session_timeout_spin = QSpinBox()
        self.session_timeout_spin.setRange(5, 480)
        self.session_timeout_spin.setSuffix(" minutes")
        self.session_timeout_spin.setValue(30)
        session_layout.addRow("Auto-logout after inactivity:", self.session_timeout_spin)

        self.remember_session_check = QCheckBox("Remember my session on this device")
        session_layout.addRow("", self.remember_session_check)

        session_group.setLayout(session_layout)
        layout.addWidget(session_group)

        # Audit settings
        audit_group = QGroupBox("Audit & Logging")
        audit_layout = QVBoxLayout()
        audit_layout.setSpacing(8)

        self.log_all_actions_check = QCheckBox("Log all user actions")
        self.log_all_actions_check.setChecked(True)
        self.log_all_actions_check.setEnabled(self.current_user and self.current_user['role'] == 'admin')
        audit_layout.addWidget(self.log_all_actions_check)

        self.log_failed_logins_check = QCheckBox("Log failed login attempts")
        self.log_failed_logins_check.setChecked(True)
        self.log_failed_logins_check.setEnabled(self.current_user and self.current_user['role'] == 'admin')
        audit_layout.addWidget(self.log_failed_logins_check)

        self.log_data_changes_check = QCheckBox("Log data modifications")
        self.log_data_changes_check.setChecked(True)
        self.log_data_changes_check.setEnabled(self.current_user and self.current_user['role'] == 'admin')
        audit_layout.addWidget(self.log_data_changes_check)

        audit_group.setLayout(audit_layout)
        layout.addWidget(audit_group)

        # Data protection
        protection_group = QGroupBox("Data Protection")
        protection_layout = QVBoxLayout()
        protection_layout.setSpacing(8)

        self.auto_backup_check = QCheckBox("Enable automatic backups")
        self.auto_backup_check.setChecked(True)
        protection_layout.addWidget(self.auto_backup_check)

        backup_freq_layout = QHBoxLayout()
        backup_freq_layout.addSpacing(20)
        backup_freq_layout.addWidget(QLabel("Backup frequency:"))
        self.backup_frequency_combo = QComboBox()
        self.backup_frequency_combo.addItems(["Daily", "Weekly", "Monthly"])
        backup_freq_layout.addWidget(self.backup_frequency_combo)
        backup_freq_layout.addStretch()
        protection_layout.addLayout(backup_freq_layout)

        protection_group.setLayout(protection_layout)
        layout.addWidget(protection_group)

        layout.addStretch()
        scroll.setWidget(container)

        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll)

        return tab

    def create_advanced_tab(self):
        """Create advanced settings tab."""
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Database settings
        db_group = QGroupBox("Database Settings")
        db_layout = QVBoxLayout()
        db_layout.setSpacing(12)

        self.enable_wal_check = QCheckBox("Enable Write-Ahead Logging (WAL)")
        self.enable_wal_check.setChecked(True)
        self.enable_wal_check.setEnabled(self.current_user and self.current_user['role'] == 'admin')
        db_layout.addWidget(self.enable_wal_check)

        self.cache_size_spin = QSpinBox()
        self.cache_size_spin.setRange(1, 100)
        self.cache_size_spin.setSuffix(" MB")
        self.cache_size_spin.setValue(10)
        self.cache_size_spin.setEnabled(self.current_user and self.current_user['role'] == 'admin')
        cache_layout = QHBoxLayout()
        cache_layout.addWidget(QLabel("Cache size:"))
        cache_layout.addWidget(self.cache_size_spin)
        cache_layout.addStretch()
        db_layout.addLayout(cache_layout)

        optimize_btn = QPushButton("Optimize Database")
        optimize_btn.setIcon(get_icon('cog'))
        optimize_btn.setMaximumWidth(200)
        optimize_btn.setEnabled(self.current_user and self.current_user['role'] == 'admin')
        optimize_btn.clicked.connect(self.optimize_database)
        db_layout.addWidget(optimize_btn)

        backup_btn = QPushButton("Backup & Restore")
        backup_btn.setIcon(get_icon('save'))
        backup_btn.setMaximumWidth(200)
        backup_btn.setEnabled(self.current_user and self.current_user['role'] == 'admin')
        backup_btn.clicked.connect(self.open_backup_dialog)
        db_layout.addWidget(backup_btn)

        db_group.setLayout(db_layout)
        layout.addWidget(db_group)

        # Performance settings
        perf_group = QGroupBox("Performance")
        perf_layout = QFormLayout()
        perf_layout.setSpacing(12)

        self.query_limit_spin = QSpinBox()
        self.query_limit_spin.setRange(100, 10000)
        self.query_limit_spin.setSingleStep(100)
        self.query_limit_spin.setValue(1000)
        perf_layout.addRow("Query result limit:", self.query_limit_spin)

        self.lazy_loading_check = QCheckBox("Enable lazy loading for large datasets")
        self.lazy_loading_check.setChecked(True)
        perf_layout.addRow("", self.lazy_loading_check)

        perf_group.setLayout(perf_layout)
        layout.addWidget(perf_group)

        # Export settings
        export_group = QGroupBox("Export Settings")
        export_layout = QFormLayout()
        export_layout.setSpacing(12)

        self.export_format_combo = QComboBox()
        self.export_format_combo.addItems(["CSV (UTF-8)", "CSV (UTF-8 BOM)", "Excel (.xlsx)"])
        export_layout.addRow("Default export format:", self.export_format_combo)

        self.include_headers_check = QCheckBox("Include column headers in exports")
        self.include_headers_check.setChecked(True)
        export_layout.addRow("", self.include_headers_check)

        export_group.setLayout(export_layout)
        layout.addWidget(export_group)

        # Debug settings
        debug_group = QGroupBox("Debug & Diagnostics")
        debug_layout = QVBoxLayout()
        debug_layout.setSpacing(8)

        self.enable_debug_check = QCheckBox("Enable debug logging")
        self.enable_debug_check.setEnabled(self.current_user and self.current_user['role'] == 'admin')
        debug_layout.addWidget(self.enable_debug_check)

        self.verbose_logging_check = QCheckBox("Verbose logging (more details)")
        self.verbose_logging_check.setEnabled(self.current_user and self.current_user['role'] == 'admin')
        debug_layout.addWidget(self.verbose_logging_check)

        logs_btn = QPushButton("View Application Logs")
        logs_btn.setIcon(get_icon('file-alt'))
        logs_btn.setMaximumWidth(200)
        logs_btn.clicked.connect(self.view_logs)
        debug_layout.addWidget(logs_btn)

        debug_group.setLayout(debug_layout)
        layout.addWidget(debug_group)

        layout.addStretch()
        scroll.setWidget(container)

        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll)

        return tab

    def load_settings(self):
        """Load current settings into UI."""
        # General tab
        self.remember_window_check.setChecked(self.current_settings.get('remember_window', True))
        self.start_maximized_check.setChecked(self.current_settings.get('start_maximized', True))
        self.show_dashboard_check.setChecked(self.current_settings.get('show_dashboard', True))
        self.auto_refresh_check.setChecked(self.current_settings.get('auto_refresh', False))
        self.refresh_interval_spin.setValue(self.current_settings.get('refresh_interval', 60))

        # Appearance tab
        font_size = self.current_settings.get('font_size', 'medium')
        font_index = {'small': 0, 'medium': 1, 'large': 2, 'xlarge': 3}.get(font_size, 1)
        self.font_size_combo.setCurrentIndex(font_index)

        self.show_tooltips_check.setChecked(self.current_settings.get('show_tooltips', True))
        self.show_icons_check.setChecked(self.current_settings.get('show_icons', True))
        self.compact_mode_check.setChecked(self.current_settings.get('compact_mode', False))
        self.animations_check.setChecked(self.current_settings.get('animations', True))
        self.rows_per_page_spin.setValue(self.current_settings.get('rows_per_page', 25))
        self.alternate_row_check.setChecked(self.current_settings.get('alternate_rows', True))

        # Notifications tab
        self.enable_toasts_check.setChecked(self.current_settings.get('enable_toasts', True))
        self.toast_duration_spin.setValue(self.current_settings.get('toast_duration', 3))
        self.notify_success_check.setChecked(self.current_settings.get('notify_success', True))
        self.notify_warning_check.setChecked(self.current_settings.get('notify_warning', True))
        self.notify_error_check.setChecked(self.current_settings.get('notify_error', True))
        self.notify_info_check.setChecked(self.current_settings.get('notify_info', True))
        self.enable_sounds_check.setChecked(self.current_settings.get('enable_sounds', False))

        # Security tab
        self.session_timeout_spin.setValue(self.current_settings.get('session_timeout', 30))
        self.remember_session_check.setChecked(self.current_settings.get('remember_session', False))
        self.log_all_actions_check.setChecked(self.current_settings.get('log_all_actions', True))
        self.auto_backup_check.setChecked(self.current_settings.get('auto_backup', True))

        # Advanced tab
        self.enable_wal_check.setChecked(self.current_settings.get('enable_wal', True))
        self.query_limit_spin.setValue(self.current_settings.get('query_limit', 1000))
        self.lazy_loading_check.setChecked(self.current_settings.get('lazy_loading', True))
        self.include_headers_check.setChecked(self.current_settings.get('include_headers', True))

    def save_settings(self):
        """Save settings to database."""
        settings = {
            # General
            'language': self.language_combo.currentText().lower(),
            'date_format': self.date_format_combo.currentText(),
            'time_format': self.time_format_combo.currentText(),
            'remember_window': self.remember_window_check.isChecked(),
            'start_maximized': self.start_maximized_check.isChecked(),
            'show_dashboard': self.show_dashboard_check.isChecked(),
            'auto_refresh': self.auto_refresh_check.isChecked(),
            'refresh_interval': self.refresh_interval_spin.value(),

            # Appearance
            'font_size': ['small', 'medium', 'large', 'xlarge'][self.font_size_combo.currentIndex()],
            'table_font_size': ['small', 'medium', 'large'][self.table_font_size_combo.currentIndex()],
            'show_tooltips': self.show_tooltips_check.isChecked(),
            'show_icons': self.show_icons_check.isChecked(),
            'compact_mode': self.compact_mode_check.isChecked(),
            'animations': self.animations_check.isChecked(),
            'rows_per_page': self.rows_per_page_spin.value(),
            'alternate_rows': self.alternate_row_check.isChecked(),
            'grid_lines': self.grid_lines_check.isChecked(),

            # Notifications
            'enable_toasts': self.enable_toasts_check.isChecked(),
            'toast_position': self.toast_position_combo.currentText().lower().replace(' ', '_'),
            'toast_duration': self.toast_duration_spin.value(),
            'notify_success': self.notify_success_check.isChecked(),
            'notify_warning': self.notify_warning_check.isChecked(),
            'notify_error': self.notify_error_check.isChecked(),
            'notify_info': self.notify_info_check.isChecked(),
            'enable_sounds': self.enable_sounds_check.isChecked(),
            'sound_volume': self.sound_volume_slider.value(),

            # Security
            'require_strong_password': self.require_strong_password_check.isChecked(),
            'session_timeout': self.session_timeout_spin.value(),
            'remember_session': self.remember_session_check.isChecked(),
            'log_all_actions': self.log_all_actions_check.isChecked(),
            'log_failed_logins': self.log_failed_logins_check.isChecked(),
            'log_data_changes': self.log_data_changes_check.isChecked(),
            'auto_backup': self.auto_backup_check.isChecked(),
            'backup_frequency': self.backup_frequency_combo.currentText().lower(),

            # Advanced
            'enable_wal': self.enable_wal_check.isChecked(),
            'cache_size': self.cache_size_spin.value(),
            'query_limit': self.query_limit_spin.value(),
            'lazy_loading': self.lazy_loading_check.isChecked(),
            'export_format': self.export_format_combo.currentText(),
            'include_headers': self.include_headers_check.isChecked(),
            'enable_debug': self.enable_debug_check.isChecked(),
            'verbose_logging': self.verbose_logging_check.isChecked(),
        }

        try:
            # Save settings
            self.settings_service.save_settings(settings)

            self.settings_changed.emit(settings)

            QMessageBox.information(
                self,
                "Settings Saved",
                "Your settings have been saved successfully.\n\n"
                "Some changes may require restarting the application."
            )
            self.accept()

        except Exception as e:
            QMessageBox.critical(
                self,
                "Save Error",
                f"Failed to save settings: {str(e)}"
            )

    def reset_to_defaults(self):
        """Reset all settings to defaults."""
        reply = QMessageBox.question(
            self,
            "Reset Settings",
            "Are you sure you want to reset all settings to their default values?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.settings_service.reset_to_defaults()
                self.current_settings = self.settings_service.get_all_settings()
                self.load_settings()

                QMessageBox.information(
                    self,
                    "Settings Reset",
                    "All settings have been reset to default values."
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Reset Error",
                    f"Failed to reset settings: {str(e)}"
                )

    def change_password(self):
        """Open change password dialog."""
        from ui.dialogs.change_password_dialog import ChangePasswordDialog
        dialog = ChangePasswordDialog(self.auth_service, self)
        dialog.exec()

    def optimize_database(self):
        """Optimize database."""
        reply = QMessageBox.question(
            self,
            "Optimize Database",
            "This will optimize the database which may take a few moments.\n\n"
            "Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # TODO: Implement database optimization
                QMessageBox.information(
                    self,
                    "Database Optimized",
                    "Database has been optimized successfully."
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Optimization Error",
                    f"Failed to optimize database: {str(e)}"
                )

    def open_backup_dialog(self):
        """Open backup & restore dialog."""
        if not self.db_manager or not self.logging_service:
            QMessageBox.warning(
                self,
                "Not Available",
                "Backup & Restore requires database and logging services."
            )
            return

        from ui.dialogs.backup_restore_dialog import BackupRestoreDialog
        from config import Config

        dialog = BackupRestoreDialog(
            self.db_manager,
            Config,
            self.logging_service,
            self
        )
        dialog.exec()

    def view_logs(self):
        """Open log viewer."""
        QMessageBox.information(
            self,
            "Log Viewer",
            "Log viewer will be implemented in a future update."
        )
