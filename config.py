"""
Configuration Management for FIU Report Management System
Handles database paths and system settings
"""
import json
import os
from pathlib import Path


class Config:
    """Global configuration manager"""
    
    # Database and backup paths (set by admin during first run)
    DATABASE_PATH = None
    BACKUP_PATH = None
    
    # Application settings
    APP_NAME = "FIU Report Management System"
    APP_VERSION = "2.0.0"
    SESSION_TIMEOUT = 30  # minutes
    MAX_LOGIN_ATTEMPTS = 5
    RECORDS_PER_PAGE = 50
    DATE_FORMAT = "DD/MM/YYYY"
    
    # Configuration file location
    CONFIG_FILE = Path.home() / '.fiu_system' / 'config.json'
    
    @classmethod
    def load(cls):
        """Load configuration from file"""
        if cls.CONFIG_FILE.exists():
            try:
                with open(cls.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    cls.DATABASE_PATH = config_data.get('database_path')
                    cls.BACKUP_PATH = config_data.get('backup_path')
                    cls.SESSION_TIMEOUT = config_data.get('session_timeout', 30)
                    cls.MAX_LOGIN_ATTEMPTS = config_data.get('max_login_attempts', 5)
                    return True
            except Exception as e:
                print(f"Error loading config: {e}")
                return False
        return False
    
    @classmethod
    def save(cls):
        """Save configuration to file"""
        try:
            cls.CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            
            config_data = {
                'database_path': cls.DATABASE_PATH,
                'backup_path': cls.BACKUP_PATH,
                'session_timeout': cls.SESSION_TIMEOUT,
                'max_login_attempts': cls.MAX_LOGIN_ATTEMPTS,
            }
            
            with open(cls.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False
    
    @classmethod
    def is_configured(cls) -> bool:
        """Check if configuration exists and is valid"""
        return cls.DATABASE_PATH is not None and cls.BACKUP_PATH is not None
    
    @classmethod
    def validate_paths(cls) -> tuple[bool, str]:
        """Validate configured paths"""
        if not cls.DATABASE_PATH:
            return False, "Database path not configured"
        
        db_path = Path(cls.DATABASE_PATH)
        
        # Check if database file exists
        if not db_path.exists():
            # Check if parent directory exists
            if not db_path.parent.exists():
                return False, f"Database directory does not exist: {db_path.parent}"
            return False, f"Database file not found: {cls.DATABASE_PATH}"
        
        # Check if database is accessible
        if not os.access(db_path, os.R_OK | os.W_OK):
            return False, "Database file is not readable/writable"
        
        # Validate backup path
        if not cls.BACKUP_PATH:
            return False, "Backup path not configured"
        
        backup_path = Path(cls.BACKUP_PATH)
        if not backup_path.exists():
            try:
                backup_path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                return False, f"Cannot create backup directory: {e}"
        
        return True, "Configuration is valid"
