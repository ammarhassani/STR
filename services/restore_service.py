"""
Restore Service - Auditable Report Restoration
Handles restoration of deleted reports with full audit trail and restore numbers.
"""

import json
from typing import Tuple, Optional, Dict, List
from datetime import datetime


class RestoreService:
    """
    Service for restoring deleted reports with complete audit trail.

    Features:
    - Generate unique restore numbers (RST-YYYY-NNNN)
    - Log full restore metadata
    - Capture previous state as JSON
    - Track restore reason and admin user
    - Display in change history
    """

    def __init__(self, db_manager, logging_service):
        """
        Initialize the restore service.

        Args:
            db_manager: DatabaseManager instance
            logging_service: LoggingService instance
        """
        self.db_manager = db_manager
        self.logger = logging_service

    def restore_report(self, report_id: int, admin_username: str, restore_reason: Optional[str] = None) -> Tuple[bool, str]:
        """
        Restore a deleted report with full audit trail.

        Args:
            report_id: ID of the report to restore
            admin_username: Admin user performing the restore
            restore_reason: Optional reason for restoration

        Returns:
            Tuple of (success, message)
        """
        try:
            # Step 1: Get the deleted report
            query = """
                SELECT report_id, report_number, sn, is_deleted, updated_at, updated_by
                FROM reports
                WHERE report_id = ?
            """
            result = self.db_manager.execute_with_retry(query, (report_id,))

            if not result:
                return False, "Report not found."

            report = result[0]
            report_number, serial_number, is_deleted = report[1], report[2], report[3]

            if not is_deleted:
                return False, "Report is not deleted. Nothing to restore."

            # Step 2: Get full report state before restoration
            full_report_query = "SELECT * FROM reports WHERE report_id = ?"
            full_report = self.db_manager.execute_with_retry(full_report_query, (report_id,))

            if not full_report:
                return False, "Unable to retrieve report data."

            # Get column names
            columns_query = "PRAGMA table_info(reports)"
            columns = self.db_manager.execute_with_retry(columns_query)
            column_names = [col[1] for col in columns]

            # Create previous state JSON
            previous_state = {}
            for i, col_name in enumerate(column_names):
                previous_state[col_name] = full_report[0][i]

            previous_state_json = json.dumps(previous_state, ensure_ascii=False)

            # Step 3: Generate restore number
            restore_number = self._generate_restore_number()

            # Step 4: Restore the report (set is_deleted = 0)
            restore_query = """
                UPDATE reports
                SET is_deleted = 0,
                    updated_at = datetime('now'),
                    updated_by = ?
                WHERE report_id = ?
            """
            self.db_manager.execute_with_retry(restore_query, (admin_username, report_id))

            # Step 5: Log the restoration in restore_log table
            log_query = """
                INSERT INTO restore_log
                (restore_number, report_id, report_number, serial_number,
                 previous_state, restored_by, restored_at, restore_reason)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now'), ?)
            """
            self.db_manager.execute_with_retry(
                log_query,
                (restore_number, report_id, report_number, serial_number,
                 previous_state_json, admin_username, restore_reason)
            )

            # Step 6: Log in change_history for audit trail
            change_query = """
                INSERT INTO change_history
                (table_name, record_id, field_name, old_value, new_value,
                 change_type, change_reason, changed_by, changed_at)
                VALUES ('reports', ?, 'is_deleted', '1', '0', 'REOPEN', ?, ?, datetime('now'))
            """
            change_reason = f"Restore #{restore_number}" + (f": {restore_reason}" if restore_reason else "")
            self.db_manager.execute_with_retry(
                change_query,
                (report_id, change_reason, admin_username)
            )

            self.logger.info(
                f"Admin {admin_username} restored report {report_number} (ID: {report_id}) "
                f"with restore number {restore_number}"
            )

            return True, f"Report restored successfully. Restore number: {restore_number}"

        except Exception as e:
            self.logger.error(f"Error restoring report {report_id}: {str(e)}")
            return False, f"Error restoring report: {str(e)}"

    def _generate_restore_number(self) -> str:
        """
        Generate a unique restore number in format: RST-YYYY-NNNN

        Returns:
            Restore number string
        """
        year = datetime.now().year

        # Get the count of restores this year
        query = """
            SELECT COUNT(*)
            FROM restore_log
            WHERE restore_number LIKE ?
        """
        result = self.db_manager.execute_with_retry(query, (f"RST-{year}-%",))
        count = result[0][0] if result else 0

        # Generate next number
        next_num = count + 1
        restore_number = f"RST-{year}-{next_num:04d}"

        return restore_number

    def get_restore_history(self, report_id: Optional[int] = None, limit: int = 100) -> List[Dict]:
        """
        Get restore history for all reports or a specific report.

        Args:
            report_id: Optional report ID to filter by
            limit: Maximum number of records to return

        Returns:
            List of restore history dictionaries
        """
        try:
            if report_id:
                query = """
                    SELECT restore_id, restore_number, report_id, report_number,
                           serial_number, restored_by, restored_at, restore_reason
                    FROM restore_log
                    WHERE report_id = ?
                    ORDER BY restored_at DESC
                    LIMIT ?
                """
                results = self.db_manager.execute_with_retry(query, (report_id, limit))
            else:
                query = """
                    SELECT restore_id, restore_number, report_id, report_number,
                           serial_number, restored_by, restored_at, restore_reason
                    FROM restore_log
                    ORDER BY restored_at DESC
                    LIMIT ?
                """
                results = self.db_manager.execute_with_retry(query, (limit,))

            history = []
            for row in results:
                history.append({
                    'restore_id': row[0],
                    'restore_number': row[1],
                    'report_id': row[2],
                    'report_number': row[3],
                    'serial_number': row[4],
                    'restored_by': row[5],
                    'restored_at': row[6],
                    'restore_reason': row[7],
                })

            return history

        except Exception as e:
            self.logger.error(f"Error getting restore history: {str(e)}")
            return []

    def get_restore_details(self, restore_number: str) -> Optional[Dict]:
        """
        Get detailed information about a specific restore operation.

        Args:
            restore_number: Restore number to look up

        Returns:
            Dictionary with restore details including previous state, or None
        """
        try:
            query = """
                SELECT restore_id, restore_number, report_id, report_number,
                       serial_number, previous_state, restored_by, restored_at, restore_reason
                FROM restore_log
                WHERE restore_number = ?
            """
            result = self.db_manager.execute_with_retry(query, (restore_number,))

            if not result:
                return None

            row = result[0]

            # Parse previous state JSON
            previous_state = json.loads(row[5]) if row[5] else {}

            return {
                'restore_id': row[0],
                'restore_number': row[1],
                'report_id': row[2],
                'report_number': row[3],
                'serial_number': row[4],
                'previous_state': previous_state,
                'restored_by': row[6],
                'restored_at': row[7],
                'restore_reason': row[8],
            }

        except Exception as e:
            self.logger.error(f"Error getting restore details for {restore_number}: {str(e)}")
            return None

    def get_restore_stats(self) -> Dict:
        """
        Get statistics about report restorations.

        Returns:
            Dictionary with restore statistics
        """
        try:
            stats = {}

            # Total restores
            query = "SELECT COUNT(*) FROM restore_log"
            result = self.db_manager.execute_with_retry(query)
            stats['total_restores'] = result[0][0] if result else 0

            # Restores this year
            year = datetime.now().year
            query = "SELECT COUNT(*) FROM restore_log WHERE restore_number LIKE ?"
            result = self.db_manager.execute_with_retry(query, (f"RST-{year}-%",))
            stats['restores_this_year'] = result[0][0] if result else 0

            # Restores this month
            now = datetime.now()
            month_start = f"{year}-{now.month:02d}-01"
            query = "SELECT COUNT(*) FROM restore_log WHERE restored_at >= ?"
            result = self.db_manager.execute_with_retry(query, (month_start,))
            stats['restores_this_month'] = result[0][0] if result else 0

            # Top restorers (admins who restore most often)
            query = """
                SELECT restored_by, COUNT(*) as restore_count
                FROM restore_log
                GROUP BY restored_by
                ORDER BY restore_count DESC
                LIMIT 5
            """
            results = self.db_manager.execute_with_retry(query)
            stats['top_restorers'] = [{'username': row[0], 'count': row[1]} for row in results] if results else []

            return stats

        except Exception as e:
            self.logger.error(f"Error getting restore stats: {str(e)}")
            return {}

    def bulk_restore_reports(self, report_ids: List[int], admin_username: str, restore_reason: Optional[str] = None) -> Tuple[int, int, str]:
        """
        Restore multiple reports at once.

        Args:
            report_ids: List of report IDs to restore
            admin_username: Admin user performing the bulk restore
            restore_reason: Optional reason for restoration

        Returns:
            Tuple of (success_count, failure_count, message)
        """
        success_count = 0
        failure_count = 0
        errors = []

        for report_id in report_ids:
            success, message = self.restore_report(report_id, admin_username, restore_reason)
            if success:
                success_count += 1
            else:
                failure_count += 1
                errors.append(f"Report {report_id}: {message}")

        if failure_count == 0:
            return success_count, 0, f"Successfully restored {success_count} report(s)."
        elif success_count == 0:
            return 0, failure_count, f"Failed to restore all {failure_count} report(s). Errors: " + "; ".join(errors[:3])
        else:
            return success_count, failure_count, f"Restored {success_count} report(s), {failure_count} failed. Errors: " + "; ".join(errors[:3])
