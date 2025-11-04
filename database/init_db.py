"""
Database Initialization Module
Creates and initializes the database from schema
"""
import sqlite3
from pathlib import Path


def initialize_database(db_path: str) -> tuple[bool, str]:
    """
    Initialize database from schema file
    
    Args:
        db_path: Path where database should be created
        
    Returns:
        Tuple of (success, message)
    """
    try:
        # Read schema file
        schema_file = Path(__file__).parent / 'schema.sql'
        
        if not schema_file.exists():
            return False, "Schema file not found"
        
        with open(schema_file, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        
        # Create database
        conn = sqlite3.connect(db_path)
        
        # Enable WAL mode
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA foreign_keys=ON")
        
        # Execute schema
        conn.executescript(schema_sql)
        
        conn.close()
        
        return True, "Database initialized successfully"
        
    except Exception as e:
        return False, f"Failed to initialize database: {e}"


def validate_database(db_path: str) -> tuple[bool, str]:
    """
    Comprehensive database validation
    
    Args:
        db_path: Path to database file
        
    Returns:
        Tuple of (is_valid, message)
    """
    try:
        # Check file exists
        if not Path(db_path).exists():
            return False, f"Database file not found: {db_path}"
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check schema version
        try:
            cursor.execute(
                "SELECT value FROM system_metadata WHERE key = 'schema_version'"
            )
            result = cursor.fetchone()
            
            if not result:
                conn.close()
                return False, "Database missing schema_version metadata"
            
            db_version = result[0]
            expected_version = "2.0.0"
            
            if db_version != expected_version:
                conn.close()
                return False, (
                    f"Schema version mismatch: "
                    f"found {db_version}, expected {expected_version}"
                )
        except sqlite3.OperationalError:
            conn.close()
            return False, "Database missing system_metadata table"
        
        # Verify required tables exist
        required_tables = [
            'users', 'reports', 'change_history', 'status_history',
            'dashboard_config', 'system_config', 'column_settings',
            'saved_filters', 'backup_log', 'session_log', 'audit_log',
            'system_metadata'
        ]
        
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        missing_tables = set(required_tables) - set(existing_tables)
        if missing_tables:
            conn.close()
            return False, (
                f"Missing required tables: {', '.join(missing_tables)}"
            )
        
        # Verify critical data exists
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
        admin_count = cursor.fetchone()[0]
        
        if admin_count == 0:
            conn.close()
            return False, "No admin user found in database"
        
        cursor.execute("SELECT COUNT(*) FROM system_config")
        config_count = cursor.fetchone()[0]
        
        if config_count == 0:
            conn.close()
            return False, "No system configuration found"
        
        cursor.execute("SELECT COUNT(*) FROM column_settings")
        column_count = cursor.fetchone()[0]
        
        if column_count == 0:
            conn.close()
            return False, "No column settings found"
        
        # Check WAL mode is enabled
        cursor.execute("PRAGMA journal_mode")
        journal_mode = cursor.fetchone()[0]
        
        if journal_mode.upper() != 'WAL':
            # Try to enable WAL mode
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA journal_mode")
            journal_mode = cursor.fetchone()[0]
            
            if journal_mode.upper() != 'WAL':
                conn.close()
                return False, "Failed to enable WAL mode"
        
        conn.close()
        
        return True, "Database validation successful"
        
    except sqlite3.DatabaseError as e:
        return False, f"Database error: {str(e)}"
    except Exception as e:
        return False, f"Validation error: {str(e)}"
