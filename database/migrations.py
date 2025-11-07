"""
Database Migrations
Handles schema updates for existing databases.
"""

import sqlite3
from typing import Tuple


def migrate_database(db_path: str) -> Tuple[bool, str]:
    """
    Run all necessary migrations on the database.

    Args:
        db_path: Path to database file

    Returns:
        Tuple of (success, message)
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        messages = []

        # Migration 1: Add theme_preference column to users table
        try:
            cursor.execute("SELECT theme_preference FROM users LIMIT 1")
        except sqlite3.OperationalError:
            # Column doesn't exist, add it
            cursor.execute("""
                ALTER TABLE users
                ADD COLUMN theme_preference TEXT DEFAULT 'light'
                CHECK(theme_preference IN ('light', 'dark'))
            """)
            conn.commit()
            messages.append("Added theme_preference column to users table")

        conn.close()

        if messages:
            return True, "; ".join(messages)
        else:
            return True, "No migrations needed"

    except Exception as e:
        return False, f"Migration failed: {str(e)}"
