"""
QThread workers for async operations.
Keeps UI responsive during long-running operations.
"""

from PyQt6.QtCore import QThread, pyqtSignal, QObject
from typing import Callable, Any, Optional, Dict, List


class Worker(QThread):
    """
    Generic worker thread for executing tasks asynchronously.

    Signals:
        finished: Emitted when task completes successfully with result
        error: Emitted when task fails with error message
        progress: Emitted to report progress (value, message)
    """

    finished = pyqtSignal(object)  # Result object
    error = pyqtSignal(str)  # Error message
    progress = pyqtSignal(int, str)  # Progress value (0-100), progress message

    def __init__(self, task: Callable, *args, **kwargs):
        """
        Initialize worker thread.

        Args:
            task: Callable to execute in thread
            *args: Positional arguments for task
            **kwargs: Keyword arguments for task
        """
        super().__init__()
        self.task = task
        self.args = args
        self.kwargs = kwargs
        self._is_cancelled = False

    def run(self):
        """Execute the task."""
        try:
            result = self.task(*self.args, **self.kwargs)
            if not self._is_cancelled:
                self.finished.emit(result)
        except Exception as e:
            if not self._is_cancelled:
                self.error.emit(str(e))

    def cancel(self):
        """Cancel the task."""
        self._is_cancelled = True


class DatabaseQueryWorker(QThread):
    """
    Worker for database query operations.

    Signals:
        finished: Emitted with query results
        error: Emitted with error message
    """

    finished = pyqtSignal(list)  # Query results
    error = pyqtSignal(str)  # Error message

    def __init__(self, db_manager, query: str, params: tuple = ()):
        """
        Initialize database query worker.

        Args:
            db_manager: DatabaseManager instance
            query: SQL query to execute
            params: Query parameters
        """
        super().__init__()
        self.db_manager = db_manager
        self.query = query
        self.params = params

    def run(self):
        """Execute the query."""
        try:
            result = self.db_manager.execute_with_retry(self.query, self.params)
            self.finished.emit(result if result else [])
        except Exception as e:
            self.error.emit(str(e))


class ReportLoadWorker(QThread):
    """
    Worker for loading reports with filtering.

    Signals:
        finished: Emitted with (reports_list, total_count)
        error: Emitted with error message
        progress: Emitted with progress updates
    """

    finished = pyqtSignal(list, int)  # Reports list, total count
    error = pyqtSignal(str)
    progress = pyqtSignal(int, str)

    def __init__(self, report_service, status=None, search_term=None,
                 created_by=None, limit=50, offset=0):
        """
        Initialize report load worker.

        Args:
            report_service: ReportService instance
            status: Optional status filter
            search_term: Optional search term
            created_by: Optional creator filter
            limit: Number of records to load
            offset: Offset for pagination
        """
        super().__init__()
        self.report_service = report_service
        self.status = status
        self.search_term = search_term
        self.created_by = created_by
        self.limit = limit
        self.offset = offset

    def run(self):
        """Load reports."""
        try:
            self.progress.emit(0, "Loading reports...")

            reports, total_count = self.report_service.get_reports(
                status=self.status,
                search_term=self.search_term,
                created_by=self.created_by,
                limit=self.limit,
                offset=self.offset
            )

            self.progress.emit(100, f"Loaded {len(reports)} reports")
            self.finished.emit(reports, total_count)

        except Exception as e:
            self.error.emit(str(e))


class DashboardDataWorker(QThread):
    """
    Worker for loading dashboard data.

    Signals:
        finished: Emitted with dashboard data dictionary
        error: Emitted with error message
        progress: Emitted with progress updates
    """

    finished = pyqtSignal(dict)  # Dashboard data
    error = pyqtSignal(str)
    progress = pyqtSignal(int, str)

    def __init__(self, dashboard_service):
        """
        Initialize dashboard data worker.

        Args:
            dashboard_service: DashboardService instance
        """
        super().__init__()
        self.dashboard_service = dashboard_service

    def run(self):
        """Load dashboard data."""
        try:
            self.progress.emit(10, "Loading summary statistics...")
            summary = self.dashboard_service.get_summary_statistics()

            self.progress.emit(30, "Loading status distribution...")
            by_status = self.dashboard_service.get_reports_by_status()

            self.progress.emit(50, "Loading monthly trends...")
            by_month = self.dashboard_service.get_reports_by_month()

            self.progress.emit(70, "Loading top reporters...")
            top_reporters = self.dashboard_service.get_top_reporters()

            self.progress.emit(90, "Loading recent activity...")
            recent_activity = self.dashboard_service.get_recent_activity()

            data = {
                'summary': summary,
                'by_status': by_status,
                'by_month': by_month,
                'top_reporters': top_reporters,
                'recent_activity': recent_activity
            }

            self.progress.emit(100, "Dashboard data loaded")
            self.finished.emit(data)

        except Exception as e:
            self.error.emit(str(e))


class ExportWorker(QThread):
    """
    Worker for exporting data to files.

    Signals:
        finished: Emitted with file path when export completes
        error: Emitted with error message
        progress: Emitted with progress updates
    """

    finished = pyqtSignal(str)  # File path
    error = pyqtSignal(str)
    progress = pyqtSignal(int, str)

    def __init__(self, export_function: Callable, file_path: str, *args, **kwargs):
        """
        Initialize export worker.

        Args:
            export_function: Function to call for export
            file_path: Path to export file
            *args: Additional arguments for export function
            **kwargs: Additional keyword arguments
        """
        super().__init__()
        self.export_function = export_function
        self.file_path = file_path
        self.args = args
        self.kwargs = kwargs

    def run(self):
        """Execute export."""
        try:
            self.progress.emit(0, "Starting export...")

            result = self.export_function(self.file_path, *self.args, **self.kwargs)

            self.progress.emit(100, f"Export complete: {result} records")
            self.finished.emit(self.file_path)

        except Exception as e:
            self.error.emit(str(e))


class BackupWorker(QThread):
    """
    Worker for database backup operations.

    Signals:
        finished: Emitted with backup file path
        error: Emitted with error message
        progress: Emitted with progress updates
    """

    finished = pyqtSignal(str)  # Backup file path
    error = pyqtSignal(str)
    progress = pyqtSignal(int, str)

    def __init__(self, db_manager, backup_path: str):
        """
        Initialize backup worker.

        Args:
            db_manager: DatabaseManager instance
            backup_path: Path for backup file
        """
        super().__init__()
        self.db_manager = db_manager
        self.backup_path = backup_path

    def run(self):
        """Execute backup."""
        try:
            self.progress.emit(0, "Starting backup...")

            # Perform backup
            self.db_manager.backup_database(self.backup_path)

            self.progress.emit(100, "Backup complete")
            self.finished.emit(self.backup_path)

        except Exception as e:
            self.error.emit(str(e))


class LogExportWorker(QThread):
    """
    Worker for exporting logs to file.

    Signals:
        finished: Emitted with (file_path, count)
        error: Emitted with error message
        progress: Emitted with progress updates
    """

    finished = pyqtSignal(str, int)  # File path, count
    error = pyqtSignal(str)
    progress = pyqtSignal(int, str)

    def __init__(self, logging_service, file_path: str, level=None,
                 module=None, start_date=None, end_date=None):
        """
        Initialize log export worker.

        Args:
            logging_service: LoggingService instance
            file_path: Path to export file
            level: Optional log level filter
            module: Optional module filter
            start_date: Optional start date
            end_date: Optional end date
        """
        super().__init__()
        self.logging_service = logging_service
        self.file_path = file_path
        self.level = level
        self.module = module
        self.start_date = start_date
        self.end_date = end_date

    def run(self):
        """Export logs."""
        try:
            self.progress.emit(0, "Exporting logs...")

            count = self.logging_service.export_logs_to_file(
                self.file_path,
                level=self.level,
                module=self.module,
                start_date=self.start_date,
                end_date=self.end_date
            )

            self.progress.emit(100, f"Exported {count} logs")
            self.finished.emit(self.file_path, count)

        except Exception as e:
            self.error.emit(str(e))


class AuthenticationWorker(QThread):
    """
    Worker for authentication operations.

    Signals:
        finished: Emitted with (success, user_dict, message)
        error: Emitted with error message
    """

    finished = pyqtSignal(bool, object, str)  # success, user, message
    error = pyqtSignal(str)

    def __init__(self, auth_service, username: str, password: str):
        """
        Initialize authentication worker.

        Args:
            auth_service: AuthService instance
            username: Username
            password: Password
        """
        super().__init__()
        self.auth_service = auth_service
        self.username = username
        self.password = password

    def run(self):
        """Authenticate user."""
        try:
            success, user, message = self.auth_service.authenticate(
                self.username, self.password
            )
            self.finished.emit(success, user, message)
        except Exception as e:
            self.error.emit(str(e))
