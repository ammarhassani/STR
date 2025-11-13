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
            # CHECK constraints in ALTER TABLE ADD COLUMN require SQLite 3.25.0+
            # Validation is handled at application level
            cursor.execute("""
                ALTER TABLE users
                ADD COLUMN theme_preference TEXT DEFAULT 'light'
            """)
            conn.commit()
            messages.append("Added theme_preference column to users table")

        # Migration 2: Create report_versions table
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='report_versions'
        """)
        if not cursor.fetchone():
            cursor.execute("""
                CREATE TABLE report_versions (
                    version_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_id INTEGER NOT NULL,
                    version_number INTEGER NOT NULL,
                    snapshot_data TEXT NOT NULL,
                    change_summary TEXT,
                    created_by TEXT NOT NULL,
                    created_at TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (report_id) REFERENCES reports(report_id)
                )
            """)
            conn.commit()
            messages.append("Created report_versions table")

        # Migration 3: Create report_approvals table
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='report_approvals'
        """)
        if not cursor.fetchone():
            cursor.execute("""
                CREATE TABLE report_approvals (
                    approval_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_id INTEGER NOT NULL,
                    version_id INTEGER,
                    approval_status TEXT CHECK(approval_status IN ('pending', 'approved', 'rejected', 'rework')) DEFAULT 'pending',
                    approver_id INTEGER,
                    approval_comment TEXT,
                    requested_by TEXT NOT NULL,
                    requested_at TEXT DEFAULT (datetime('now')),
                    reviewed_at TEXT,
                    FOREIGN KEY (report_id) REFERENCES reports(report_id),
                    FOREIGN KEY (approver_id) REFERENCES users(user_id),
                    FOREIGN KEY (version_id) REFERENCES report_versions(version_id)
                )
            """)
            conn.commit()
            messages.append("Created report_approvals table")

        # Migration 4: Create notifications table
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='notifications'
        """)
        if not cursor.fetchone():
            cursor.execute("""
                CREATE TABLE notifications (
                    notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    notification_type TEXT CHECK(notification_type IN ('info', 'warning', 'approval_request', 'approval_result')),
                    related_report_id INTEGER,
                    is_read INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    FOREIGN KEY (related_report_id) REFERENCES reports(report_id)
                )
            """)
            conn.commit()
            messages.append("Created notifications table")

        # Migration 5: Add versioning columns to reports table
        try:
            cursor.execute("SELECT current_version FROM reports LIMIT 1")
        except sqlite3.OperationalError:
            cursor.execute("""
                ALTER TABLE reports
                ADD COLUMN current_version INTEGER DEFAULT 1
            """)
            conn.commit()
            messages.append("Added current_version column to reports table")

        try:
            cursor.execute("SELECT approval_status FROM reports LIMIT 1")
        except sqlite3.OperationalError:
            # Add approval_status column without CHECK constraint
            # (CHECK constraints in ALTER TABLE ADD COLUMN require SQLite 3.25.0+)
            # Validation is handled at application level
            cursor.execute("""
                ALTER TABLE reports
                ADD COLUMN approval_status TEXT DEFAULT 'draft'
            """)
            conn.commit()
            messages.append("Added approval_status column to reports table")

        # Migration 6: Ensure system_logs table exists
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='system_logs'
        """)
        if not cursor.fetchone():
            cursor.execute("""
                CREATE TABLE system_logs (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT DEFAULT (datetime('now')),
                    log_level TEXT NOT NULL,
                    module TEXT NOT NULL,
                    function_name TEXT,
                    message TEXT NOT NULL,
                    user_id INTEGER,
                    username TEXT,
                    exception_type TEXT,
                    exception_message TEXT,
                    stack_trace TEXT,
                    extra_data TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL
                )
            """)
            conn.commit()
            messages.append("Created system_logs table")

        conn.close()

        if messages:
            return True, "; ".join(messages)
        else:
            return True, "No migrations needed"

    except Exception as e:
        return False, f"Migration failed: {str(e)}"
