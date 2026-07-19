"""
Configuration Management for FIU Report Management System
Handles database paths and system settings
"""
import json
import os
import socket
import sys
from pathlib import Path
from typing import Optional
from uuid import uuid4

from utils import utf8_console  # noqa: F401 - side effect: UTF-8 console on Windows


def app_base_dir() -> Path:
    """The folder that holds THIS installation's writable data.

    Running from source that is the repo root, as it always was.

    Running as a PyInstaller .exe it must be the folder holding the .exe, NOT
    Path(__file__).parent. In a --onefile build the bundle unpacks to a temp
    directory (…\\Temp\\_MEIxxxxx) that Windows deletes when the app exits, so
    __file__-based paths put config.json and the database somewhere that
    disappears every run: a client would start blank on every launch and lose
    whatever it had queued. Anchoring to sys.executable keeps a client's data
    beside its .exe where an operator can see it, back it up, or wipe it.

    Read-only files that ship INSIDE the bundle (schema.sql, the assets) must
    keep resolving through __file__ -- they live in the temp dir on purpose.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


class Config:
    """Global configuration manager"""
    
    # Database and backup paths (set by admin during first run)
    DATABASE_PATH = None
    BACKUP_PATH = None

    # G1 client mode: launch mode and shared folder path
    MODE = "local"          # "local" | "host" | "client"
    SHARE_PATH = None       # shared-folder root (host & client); None in local mode

    # Host mode: stable id for this PC when it serves as host
    HOST_ID = None

    # Application settings
    APP_NAME = "FIU Report Management System"
    APP_VERSION = "2.0.0"
    SESSION_TIMEOUT = 30  # minutes
    MAX_LOGIN_ATTEMPTS = 5
    RECORDS_PER_PAGE = 50
    DATE_FORMAT = "DD/MM/YYYY"
    
    # Configuration file location - stored beside the app (or the .exe)
    CONFIG_FILE = app_base_dir() / 'config' / 'config.json'
    
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
                    cls.MODE = config_data.get('mode', 'local')
                    cls.SHARE_PATH = config_data.get('share_path')
                    cls.HOST_ID = config_data.get('host_id')
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
                'mode': cls.MODE,
                'share_path': cls.SHARE_PATH,
                'host_id': cls.HOST_ID,
            }

            with open(cls.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2)

            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False
    
    @classmethod
    def get_bus_dir(cls) -> str:
        """Shared folder client/host processes exchange commands through.
        Lives under the configured backup/share path; falls back to a
        folder next to the DB (or the CWD) if that isn't set yet."""
        base = cls.SHARE_PATH or cls.BACKUP_PATH
        if not base:
            base = os.path.dirname(cls.DATABASE_PATH) if cls.DATABASE_PATH else "."
        cls.warn_if_share_looks_local(base)
        bus_dir = os.path.join(base, "str_bus")
        os.makedirs(bus_dir, exist_ok=True)
        return bus_dir

    @classmethod
    def warn_if_share_looks_local(cls, base: str) -> Optional[str]:
        r"""Catch a share path that was MEANT to be a UNC path but isn't.

        `\\SERVER\share` written with one backslash instead of two --
        easy to do when hand-editing config.json, where every backslash has to
        be doubled -- is not an error on Windows. It resolves to a directory on
        the local C: drive. STR then runs happily against a folder nobody else
        can see: the host publishes a replica no client will ever read, and the
        clients queue commands no host will ever answer. Nothing fails, and the
        unit quietly stops sharing data.

        Returns the warning text (also printed), or None when the path is fine.
        """
        if cls.MODE not in ("host", "client") or not base:
            return None
        looks_meant_to_be_unc = (
            base.startswith("\\") and not base.startswith("\\\\")
            and not base.startswith("\\?")
        )
        if not looks_meant_to_be_unc:
            return None
        msg = (f"[CONFIG][WARN] share_path {base!r} starts with a single backslash. "
               f"On Windows that is a LOCAL path ({os.path.abspath(base)!r}), not a "
               f"network share, so no other PC will see this data. A UNC path needs "
               f"two leading backslashes -- in config.json that is four: "
               f'"share_path": "\\\\SERVER\\share".')
        print(msg)
        return msg

    @classmethod
    def get_client_replica_path(cls) -> str:
        """Local file a client keeps its copy of the host replica in."""
        base = os.path.dirname(cls.DATABASE_PATH) if cls.DATABASE_PATH else \
            str(app_base_dir() / "database")
        os.makedirs(base, exist_ok=True)
        return os.path.join(base, "client_replica.db")

    @classmethod
    def ensure_host_id(cls) -> str:
        """Generate and persist a stable id for this PC when it serves as host.
        Returns the cached id if already set, otherwise generates, saves, and returns."""
        if not cls.HOST_ID:
            cls.HOST_ID = f"{socket.gethostname()}-{uuid4().hex[:8]}"
            cls.save()
        return cls.HOST_ID

    @classmethod
    def get_client_outbox_dir(cls) -> str:
        """Local dir (next to the client replica) where the outbox persists queued writes."""
        base = os.path.dirname(cls.DATABASE_PATH) if cls.DATABASE_PATH else \
            str(app_base_dir() / "database")
        d = os.path.join(base, "outbox")
        os.makedirs(d, exist_ok=True)
        return d

    @classmethod
    def is_configured(cls) -> bool:
        """Check if configuration exists and is valid"""
        if cls.MODE == "client":
            return bool(cls.SHARE_PATH) and os.path.isdir(cls.SHARE_PATH)
        # local / host: need a real local DB (existing behavior)
        if cls.DATABASE_PATH is None or cls.BACKUP_PATH is None:
            return False
        return Path(cls.DATABASE_PATH).exists()
    
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
