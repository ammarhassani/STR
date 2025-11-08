"""
Database-backed logging service for FIU Report Management System.
Provides comprehensive logging with database persistence and audit trail.
"""

import logging
import traceback
import json
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path
import sys


class DatabaseLogHandler(logging.Handler):
    """
    Custom logging handler that writes logs to the database.
    Integrates with the existing DatabaseManager for persistence.
    """

    def __init__(self, db_manager, user_context=None):
        """
        Initialize the database log handler.

        Args:
            db_manager: DatabaseManager instance for database operations
            user_context: Optional dict with 'user_id' and 'username' keys
        """
        super().__init__()
        self.db_manager = db_manager
        self.user_context = user_context or {}

    def emit(self, record: logging.LogRecord):
        """
        Emit a log record to the database.

        Args:
            record: LogRecord instance containing log information
        """
        try:
            # Extract exception information if present
            exception_type = None
            exception_message = None
            stack_trace = None

            if record.exc_info:
                exc_type, exc_value, exc_tb = record.exc_info
                exception_type = exc_type.__name__ if exc_type else None
                exception_message = str(exc_value) if exc_value else None
                stack_trace = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))

            # Prepare extra data (custom attributes from log record)
            extra_data = {}
            for key, value in record.__dict__.items():
                if key not in ['name', 'msg', 'args', 'created', 'filename', 'funcName',
                              'levelname', 'levelno', 'lineno', 'module', 'msecs',
                              'message', 'pathname', 'process', 'processName', 'relativeCreated',
                              'thread', 'threadName', 'exc_info', 'exc_text', 'stack_info']:
                    extra_data[key] = value

            # Insert log into database
            query = """
                INSERT INTO system_logs (
                    timestamp, log_level, module, function_name, message,
                    user_id, username, exception_type, exception_message,
                    stack_trace, extra_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            params = (
                datetime.now().isoformat(),
                record.levelname,
                record.module,
                record.funcName,
                self.format(record),
                self.user_context.get('user_id'),
                self.user_context.get('username'),
                exception_type,
                exception_message,
                stack_trace,
                json.dumps(extra_data) if extra_data else None
            )

            # Use the database manager to execute the insert
            self.db_manager.execute_with_retry(query, params)

        except Exception as e:
            # Fallback to stderr if database logging fails
            print(f"Failed to log to database: {e}", file=sys.stderr)
            self.handleError(record)

    def update_user_context(self, user_id: Optional[int] = None, username: Optional[str] = None):
        """
        Update the user context for logging.

        Args:
            user_id: User ID to associate with logs
            username: Username to associate with logs
        """
        if user_id is not None:
            self.user_context['user_id'] = user_id
        if username is not None:
            self.user_context['username'] = username

    def clear_user_context(self):
        """Clear the user context (e.g., on logout)."""
        self.user_context = {}


class LoggingService:
    """
    Centralized logging service that manages both file and database logging.
    Provides convenient methods for logging throughout the application.
    """

    def __init__(self, db_manager, log_dir: Optional[Path] = None):
        """
        Initialize the logging service.

        Args:
            db_manager: DatabaseManager instance
            log_dir: Optional directory for file logs (defaults to ~/.fiu_system/)
        """
        self.db_manager = db_manager
        self.log_dir = log_dir or Path.home() / '.fiu_system'
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Create logger
        self.logger = logging.getLogger('fiu_system')
        self.logger.setLevel(logging.DEBUG)

        # Remove existing handlers
        self.logger.handlers.clear()

        # Add file handler
        file_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / 'app.log',
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

        # Add console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        # Add database handler
        self.db_handler = DatabaseLogHandler(db_manager)
        self.db_handler.setLevel(logging.INFO)
        db_formatter = logging.Formatter('%(message)s')
        self.db_handler.setFormatter(db_formatter)
        self.logger.addHandler(self.db_handler)

        self.logger.info("Logging service initialized")

    def set_user_context(self, user_id: int, username: str):
        """
        Set the current user context for logging.

        Args:
            user_id: User ID
            username: Username
        """
        self.db_handler.update_user_context(user_id, username)
        self.logger.info(f"User context set: {username} (ID: {user_id})")

    def clear_user_context(self):
        """Clear the current user context."""
        self.db_handler.clear_user_context()
        self.logger.info("User context cleared")

    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self.logger.debug(message, extra=kwargs)

    def info(self, message: str, **kwargs):
        """Log info message."""
        self.logger.info(message, extra=kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self.logger.warning(message, extra=kwargs)

    def error(self, message: str, exc_info: bool = False, **kwargs):
        """Log error message."""
        self.logger.error(message, exc_info=exc_info, extra=kwargs)

    def critical(self, message: str, exc_info: bool = False, **kwargs):
        """Log critical message."""
        self.logger.critical(message, exc_info=exc_info, extra=kwargs)

    def log_user_action(self, action: str, details: Optional[Dict[str, Any]] = None):
        """
        Log a user action for audit trail.
        Writes to both system_logs (for general logging) and audit_log (for permanent audit trail).

        Args:
            action: Description of the action
            details: Optional dictionary with additional details
        """
        # Log to system_logs via logger
        message = f"User action: {action}"
        extra = {'action': action}
        if details:
            extra['details'] = details
        self.logger.info(message, extra=extra)

        # Also log to audit_log table for permanent audit trail
        try:
            user_id = self.db_handler.user_context.get('user_id')
            username = self.db_handler.user_context.get('username')

            if user_id and username:
                query = """
                    INSERT INTO audit_log (user_id, username, action_type, action_details, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """
                params = (
                    user_id,
                    username,
                    action,
                    json.dumps(details) if details else None,
                    datetime.now().isoformat()
                )
                self.db_manager.execute_with_retry(query, params)
        except Exception as e:
            # Don't fail if audit logging fails, just log to stderr
            print(f"Failed to log to audit_log: {e}", file=sys.stderr)

    def get_logs(self,
                 level: Optional[str] = None,
                 module: Optional[str] = None,
                 start_date: Optional[str] = None,
                 end_date: Optional[str] = None,
                 limit: int = 1000) -> list:
        """
        Retrieve logs from the database with optional filtering.

        Args:
            level: Filter by log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            module: Filter by module name
            start_date: Start date for filtering (ISO format)
            end_date: End date for filtering (ISO format)
            limit: Maximum number of logs to retrieve

        Returns:
            List of log dictionaries
        """
        query = "SELECT * FROM system_logs WHERE 1=1"
        params = []

        if level:
            query += " AND log_level = ?"
            params.append(level)

        if module:
            query += " AND module = ?"
            params.append(module)

        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date)

        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        result = self.db_manager.execute_with_retry(query, params)

        # Convert to list of dictionaries
        logs = []
        for row in result:
            logs.append({
                'log_id': row[0],
                'timestamp': row[1],
                'log_level': row[2],
                'module': row[3],
                'function_name': row[4],
                'message': row[5],
                'user_id': row[6],
                'username': row[7],
                'exception_type': row[8],
                'exception_message': row[9],
                'stack_trace': row[10],
                'extra_data': row[11]
            })

        return logs

    def clear_logs(self, older_than_days: Optional[int] = None) -> int:
        """
        Clear logs from the database.

        Args:
            older_than_days: If specified, only delete logs older than this many days

        Returns:
            Number of logs deleted
        """
        if older_than_days:
            query = """
                DELETE FROM system_logs
                WHERE timestamp < datetime('now', '-' || ? || ' days')
            """
            params = (older_than_days,)
        else:
            query = "DELETE FROM system_logs"
            params = ()

        self.db_manager.execute_with_retry(query, params)

        # Get the number of deleted rows
        result = self.db_manager.execute_with_retry(
            "SELECT changes()"
        )
        deleted_count = result[0][0] if result else 0

        self.logger.info(f"Cleared {deleted_count} logs from database")
        return deleted_count

    def export_logs_to_file(self,
                           file_path: str,
                           level: Optional[str] = None,
                           module: Optional[str] = None,
                           start_date: Optional[str] = None,
                           end_date: Optional[str] = None) -> int:
        """
        Export logs to a text file.

        Args:
            file_path: Path to the output file
            level: Filter by log level
            module: Filter by module name
            start_date: Start date for filtering
            end_date: End date for filtering

        Returns:
            Number of logs exported
        """
        logs = self.get_logs(level, module, start_date, end_date, limit=100000)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("FIU Report Management System - System Logs\n")
            f.write("=" * 80 + "\n\n")

            for log in logs:
                f.write(f"[{log['timestamp']}] [{log['log_level']}] ")
                f.write(f"[{log['module']}::{log['function_name'] or 'N/A'}]\n")

                if log['username']:
                    f.write(f"User: {log['username']} (ID: {log['user_id']})\n")

                f.write(f"Message: {log['message']}\n")

                if log['exception_type']:
                    f.write(f"Exception: {log['exception_type']}: {log['exception_message']}\n")

                if log['stack_trace']:
                    f.write(f"Stack Trace:\n{log['stack_trace']}\n")

                if log['extra_data']:
                    f.write(f"Extra Data: {log['extra_data']}\n")

                f.write("-" * 80 + "\n\n")

        self.logger.info(f"Exported {len(logs)} logs to {file_path}")
        return len(logs)

    def get_log_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about logs in the database.

        Returns:
            Dictionary with log statistics
        """
        stats = {}

        # Total logs
        result = self.db_manager.execute_with_retry(
            "SELECT COUNT(*) FROM system_logs"
        )
        stats['total_logs'] = result[0][0] if result else 0

        # Logs by level
        result = self.db_manager.execute_with_retry(
            "SELECT log_level, COUNT(*) FROM system_logs GROUP BY log_level"
        )
        stats['by_level'] = {row[0]: row[1] for row in result} if result else {}

        # Logs by module
        result = self.db_manager.execute_with_retry(
            "SELECT module, COUNT(*) FROM system_logs GROUP BY module ORDER BY COUNT(*) DESC LIMIT 10"
        )
        stats['top_modules'] = {row[0]: row[1] for row in result} if result else {}

        # Recent errors
        result = self.db_manager.execute_with_retry(
            "SELECT COUNT(*) FROM system_logs WHERE log_level IN ('ERROR', 'CRITICAL') AND timestamp >= datetime('now', '-24 hours')"
        )
        stats['errors_last_24h'] = result[0][0] if result else 0

        return stats


# Import logging.handlers for RotatingFileHandler
import logging.handlers
