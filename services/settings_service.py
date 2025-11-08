"""
Settings Service
Manages application settings and preferences with database persistence.
"""

import json
from typing import Any, Dict, Optional


class SettingsService:
    """
    Service for managing application settings.

    Settings are stored per-user in the database with JSON serialization.
    Provides defaults and type-safe access to settings.
    """

    # Default settings
    DEFAULTS = {
        # General
        'theme': 'dark',
        'auto_theme': False,
        'language': 'english',
        'date_format': 'DD/MM/YYYY',
        'time_format': '24 Hour',
        'remember_window': True,
        'start_maximized': True,
        'show_dashboard': True,
        'auto_refresh': False,
        'refresh_interval': 60,

        # Appearance
        'font_size': 'medium',
        'table_font_size': 'medium',
        'show_tooltips': True,
        'show_icons': True,
        'compact_mode': False,
        'animations': True,
        'rows_per_page': 25,
        'alternate_rows': True,
        'grid_lines': False,

        # Notifications
        'enable_toasts': True,
        'toast_position': 'top_right',
        'toast_duration': 3,
        'notify_success': True,
        'notify_warning': True,
        'notify_error': True,
        'notify_info': True,
        'enable_sounds': False,
        'sound_volume': 50,

        # Security
        'require_strong_password': True,
        'session_timeout': 30,
        'remember_session': False,
        'log_all_actions': True,
        'log_failed_logins': True,
        'log_data_changes': True,
        'auto_backup': True,
        'backup_frequency': 'weekly',

        # Advanced
        'enable_wal': True,
        'cache_size': 10,
        'query_limit': 1000,
        'lazy_loading': True,
        'export_format': 'CSV (UTF-8 BOM)',
        'include_headers': True,
        'enable_debug': False,
        'verbose_logging': False,
    }

    def __init__(self, db_manager, auth_service):
        """
        Initialize settings service.

        Args:
            db_manager: DatabaseManager instance
            auth_service: AuthService instance
        """
        self.db_manager = db_manager
        self.auth_service = auth_service
        self._ensure_settings_table()

    def _ensure_settings_table(self):
        """Ensure settings table exists in database."""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER PRIMARY KEY,
            settings_json TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
        """
        self.db_manager.execute_with_retry(create_table_sql)

    def get_all_settings(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get all settings for a user.

        Args:
            user_id: User ID (if None, uses current user)

        Returns:
            Dictionary of all settings with defaults for missing values
        """
        if user_id is None:
            current_user = self.auth_service.get_current_user()
            if not current_user:
                return self.DEFAULTS.copy()
            user_id = current_user['user_id']

        query = "SELECT settings_json FROM user_settings WHERE user_id = ?"
        result = self.db_manager.execute_with_retry(query, (user_id,))

        if result and len(result) > 0:
            try:
                # result is a list of tuples, get first row, first column
                user_settings = json.loads(result[0][0])
                # Merge with defaults (defaults for missing keys)
                settings = self.DEFAULTS.copy()
                settings.update(user_settings)
                return settings
            except json.JSONDecodeError:
                return self.DEFAULTS.copy()

        return self.DEFAULTS.copy()

    def get_setting(self, key: str, default: Any = None, user_id: Optional[int] = None) -> Any:
        """
        Get a specific setting value.

        Args:
            key: Setting key
            default: Default value if not found
            user_id: User ID (if None, uses current user)

        Returns:
            Setting value or default
        """
        settings = self.get_all_settings(user_id)
        return settings.get(key, default if default is not None else self.DEFAULTS.get(key))

    def save_settings(self, settings: Dict[str, Any], user_id: Optional[int] = None) -> bool:
        """
        Save settings for a user.

        Args:
            settings: Dictionary of settings to save
            user_id: User ID (if None, uses current user)

        Returns:
            True if successful
        """
        if user_id is None:
            current_user = self.auth_service.get_current_user()
            if not current_user:
                return False
            user_id = current_user['user_id']

        # Get existing settings and merge
        existing = self.get_all_settings(user_id)
        existing.update(settings)

        settings_json = json.dumps(existing)

        # Insert or update
        query = """
        INSERT INTO user_settings (user_id, settings_json, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id) DO UPDATE SET
            settings_json = excluded.settings_json,
            updated_at = CURRENT_TIMESTAMP
        """

        try:
            self.db_manager.execute_with_retry(query, (user_id, settings_json))
            return True
        except Exception as e:
            print(f"Error saving settings: {e}")
            return False

    def save_setting(self, key: str, value: Any, user_id: Optional[int] = None) -> bool:
        """
        Save a single setting.

        Args:
            key: Setting key
            value: Setting value
            user_id: User ID (if None, uses current user)

        Returns:
            True if successful
        """
        return self.save_settings({key: value}, user_id)

    def reset_to_defaults(self, user_id: Optional[int] = None) -> bool:
        """
        Reset all settings to defaults for a user.

        Args:
            user_id: User ID (if None, uses current user)

        Returns:
            True if successful
        """
        return self.save_settings(self.DEFAULTS.copy(), user_id)

    def delete_settings(self, user_id: int) -> bool:
        """
        Delete all settings for a user.

        Args:
            user_id: User ID

        Returns:
            True if successful
        """
        query = "DELETE FROM user_settings WHERE user_id = ?"
        try:
            self.db_manager.execute_with_retry(query, (user_id,))
            return True
        except Exception as e:
            print(f"Error deleting settings: {e}")
            return False

    def get_theme(self, user_id: Optional[int] = None) -> str:
        """
        Get the theme preference for a user.

        Args:
            user_id: User ID (if None, uses current user)

        Returns:
            Theme name ('dark', 'light', or 'system')
        """
        return self.get_setting('theme', 'dark', user_id)

    def set_theme(self, theme: str, user_id: Optional[int] = None) -> bool:
        """
        Set the theme preference for a user.

        Args:
            theme: Theme name ('dark', 'light', or 'system')
            user_id: User ID (if None, uses current user)

        Returns:
            True if successful
        """
        if theme not in ['dark', 'light', 'system']:
            return False
        return self.save_setting('theme', theme, user_id)

    def get_rows_per_page(self, user_id: Optional[int] = None) -> int:
        """
        Get rows per page setting.

        Args:
            user_id: User ID (if None, uses current user)

        Returns:
            Number of rows per page
        """
        return int(self.get_setting('rows_per_page', 25, user_id))

    def is_animations_enabled(self, user_id: Optional[int] = None) -> bool:
        """
        Check if animations are enabled.

        Args:
            user_id: User ID (if None, uses current user)

        Returns:
            True if animations are enabled
        """
        return bool(self.get_setting('animations', True, user_id))

    def are_toasts_enabled(self, user_id: Optional[int] = None) -> bool:
        """
        Check if toast notifications are enabled.

        Args:
            user_id: User ID (if None, uses current user)

        Returns:
            True if toasts are enabled
        """
        return bool(self.get_setting('enable_toasts', True, user_id))

    def get_toast_duration(self, user_id: Optional[int] = None) -> int:
        """
        Get toast notification duration in seconds.

        Args:
            user_id: User ID (if None, uses current user)

        Returns:
            Duration in seconds
        """
        return int(self.get_setting('toast_duration', 3, user_id))

    def get_session_timeout(self, user_id: Optional[int] = None) -> int:
        """
        Get session timeout in minutes.

        Args:
            user_id: User ID (if None, uses current user)

        Returns:
            Timeout in minutes
        """
        return int(self.get_setting('session_timeout', 30, user_id))
