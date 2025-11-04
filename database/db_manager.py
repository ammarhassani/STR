"""
Database Manager with WAL Mode and Retry Logic
Handles all database operations with concurrent access support
"""
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, List, Tuple, Optional


class DatabaseManager:
    """Manages SQLite database connections with WAL mode enabled"""
    
    def __init__(self, db_path: str):
        """
        Initialize database manager
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.connection_timeout = 10.0  # 10 seconds
        self._init_connection()
    
    def _init_connection(self):
        """Initialize database with WAL mode (one-time setup)"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Enable WAL mode for better concurrency
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=10000")
            conn.execute("PRAGMA temp_store=MEMORY")
            conn.execute("PRAGMA foreign_keys=ON")
            
            conn.close()
        except Exception as e:
            raise Exception(f"Failed to initialize database: {e}")
    
    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections
        Automatically handles commit/rollback
        
        Yields:
            sqlite3.Connection: Database connection
        """
        conn = sqlite3.connect(
            self.db_path,
            timeout=self.connection_timeout,
            isolation_level='DEFERRED'  # Optimal for WAL mode
        )
        conn.row_factory = sqlite3.Row  # Access columns by name
        
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def execute_with_retry(
        self,
        query: str,
        params: tuple = (),
        max_retries: int = 5
    ) -> List[sqlite3.Row]:
        """
        Execute query with exponential backoff retry logic
        
        Args:
            query: SQL query to execute
            params: Query parameters
            max_retries: Maximum number of retry attempts
            
        Returns:
            List of rows for SELECT queries, empty list for others
            
        Raises:
            sqlite3.Error: If query fails after all retries
        """
        for attempt in range(max_retries):
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(query, params)
                    
                    # Return results for SELECT queries
                    if query.strip().upper().startswith('SELECT'):
                        return cursor.fetchall()
                    
                    # Return empty list for other queries
                    return []
                    
            except sqlite3.OperationalError as e:
                # Handle database locked errors
                if "locked" in str(e).lower() and attempt < max_retries - 1:
                    # Exponential backoff: 0.5s, 1s, 1.5s, 2s, 2.5s
                    wait_time = 0.5 * (attempt + 1)
                    time.sleep(wait_time)
                    continue
                raise
            except Exception:
                raise
        
        return []
    
    def execute_many(
        self,
        query: str,
        params_list: List[tuple],
        max_retries: int = 5
    ) -> int:
        """
        Execute query multiple times with different parameters
        
        Args:
            query: SQL query to execute
            params_list: List of parameter tuples
            max_retries: Maximum number of retry attempts
            
        Returns:
            Number of affected rows
        """
        for attempt in range(max_retries):
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.executemany(query, params_list)
                    return cursor.rowcount
                    
            except sqlite3.OperationalError as e:
                if "locked" in str(e).lower() and attempt < max_retries - 1:
                    wait_time = 0.5 * (attempt + 1)
                    time.sleep(wait_time)
                    continue
                raise
            except Exception:
                raise
        
        return 0
    
    def get_last_insert_id(self) -> Optional[int]:
        """Get the last inserted row ID"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT last_insert_rowid()")
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception:
            return None
    
    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists in the database"""
        try:
            query = """
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name=?
            """
            result = self.execute_with_retry(query, (table_name,))
            return len(result) > 0
        except Exception:
            return False
    
    def get_table_columns(self, table_name: str) -> List[str]:
        """Get list of column names for a table"""
        try:
            query = f"PRAGMA table_info({table_name})"
            result = self.execute_with_retry(query)
            return [row['name'] for row in result]
        except Exception:
            return []
    
    def backup_database(self, backup_path: str) -> bool:
        """
        Create a backup of the database
        
        Args:
            backup_path: Path for the backup file
            
        Returns:
            True if backup successful, False otherwise
        """
        try:
            import shutil
            
            # Use SQLite backup API for safe backup
            with self.get_connection() as source:
                dest = sqlite3.connect(backup_path)
                source.backup(dest)
                dest.close()
            
            return True
        except Exception as e:
            print(f"Backup failed: {e}")
            return False
