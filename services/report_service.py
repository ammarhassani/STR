"""
Report management service.
Handles CRUD operations for financial crime reports.
"""

from datetime import datetime
from typing import Optional, Dict, List, Tuple, Any


class ReportService:
    """Service for managing financial crime reports."""

    def __init__(self, db_manager, logging_service, auth_service):
        """
        Initialize the report service.

        Args:
            db_manager: DatabaseManager instance
            logging_service: LoggingService instance
            auth_service: AuthService instance
        """
        self.db_manager = db_manager
        self.logger = logging_service
        self.auth_service = auth_service

    def create_report(self, report_data: Dict[str, Any]) -> Tuple[bool, Optional[int], str]:
        """
        Create a new report.

        Args:
            report_data: Dictionary containing report fields

        Returns:
            Tuple of (success, report_id, message)
        """
        try:
            current_user = self.auth_service.get_current_user()
            if not current_user:
                return False, None, "User not authenticated"

            # Validate required fields
            required_fields = ['sn', 'report_number', 'report_date', 'reported_entity_name']
            for field in required_fields:
                if field not in report_data or not report_data[field]:
                    return False, None, f"Missing required field: {field}"

            # Check if report number already exists
            check_query = "SELECT COUNT(*) FROM reports WHERE report_number = ?"
            result = self.db_manager.execute_with_retry(check_query, (report_data['report_number'],))
            if result and result[0][0] > 0:
                return False, None, "Report number already exists"

            # Check if serial number already exists
            check_sn_query = "SELECT COUNT(*) FROM reports WHERE sn = ?"
            result = self.db_manager.execute_with_retry(check_sn_query, (report_data['sn'],))
            if result and result[0][0] > 0:
                return False, None, "Serial number already exists"

            # Build insert query
            fields = list(report_data.keys())
            fields.extend(['created_by', 'created_at', 'status'])
            placeholders = ', '.join(['?'] * len(fields))
            field_names = ', '.join(fields)

            values = list(report_data.values())
            values.extend([
                current_user['username'],
                datetime.now().isoformat(),
                report_data.get('status', 'Open')
            ])

            query = f"INSERT INTO reports ({field_names}) VALUES ({placeholders})"
            self.db_manager.execute_with_retry(query, values)

            # Get the inserted report ID
            result = self.db_manager.execute_with_retry("SELECT last_insert_rowid()")
            report_id = result[0][0] if result else None

            # Log the creation in change history
            change_query = """
                INSERT INTO change_history (table_name, record_id, field_name, old_value, new_value, change_type, changed_by)
                VALUES ('reports', ?, 'report_created', NULL, ?, 'INSERT', ?)
            """
            self.db_manager.execute_with_retry(
                change_query,
                (report_id, report_data['report_number'], current_user['username'])
            )

            self.logger.log_user_action(
                "REPORT_CREATED",
                {'report_id': report_id, 'report_number': report_data['report_number']}
            )

            return True, report_id, "Report created successfully"

        except Exception as e:
            self.logger.error(f"Error creating report: {str(e)}", exc_info=True)
            return False, None, f"Error creating report: {str(e)}"

    def update_report(self, report_id: int, report_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Update an existing report.

        Args:
            report_id: Report ID to update
            report_data: Dictionary containing fields to update

        Returns:
            Tuple of (success, message)
        """
        try:
            current_user = self.auth_service.get_current_user()
            if not current_user:
                return False, "User not authenticated"

            # Get existing report data for change tracking
            old_data_query = "SELECT * FROM reports WHERE report_id = ?"
            old_result = self.db_manager.execute_with_retry(old_data_query, (report_id,))

            if not old_result:
                return False, "Report not found"

            # Build update query
            fields = list(report_data.keys())
            if not fields:
                return False, "No fields to update"

            set_clause = ', '.join([f"{field} = ?" for field in fields])
            values = list(report_data.values())
            values.extend([current_user['username'], datetime.now().isoformat(), report_id])

            query = f"""
                UPDATE reports
                SET {set_clause}, updated_by = ?, updated_at = ?
                WHERE report_id = ?
            """
            self.db_manager.execute_with_retry(query, values)

            # Log changes in change history
            # This is simplified - in production, you'd track each field change
            change_query = """
                INSERT INTO change_history (table_name, record_id, field_name, old_value, new_value, change_type, changed_by)
                VALUES ('reports', ?, 'report_updated', NULL, ?, 'UPDATE', ?)
            """
            self.db_manager.execute_with_retry(
                change_query,
                (report_id, f"Updated {len(fields)} fields", current_user['username'])
            )

            self.logger.log_user_action(
                "REPORT_UPDATED",
                {'report_id': report_id, 'fields_updated': fields}
            )

            return True, "Report updated successfully"

        except Exception as e:
            self.logger.error(f"Error updating report: {str(e)}", exc_info=True)
            return False, f"Error updating report: {str(e)}"

    def delete_report(self, report_id: int) -> Tuple[bool, str]:
        """
        Delete a report (soft delete).

        Args:
            report_id: Report ID to delete

        Returns:
            Tuple of (success, message)
        """
        try:
            current_user = self.auth_service.get_current_user()
            if not current_user:
                return False, "User not authenticated"

            # Check if report exists
            check_query = "SELECT report_number FROM reports WHERE report_id = ?"
            result = self.db_manager.execute_with_retry(check_query, (report_id,))

            if not result:
                return False, "Report not found"

            report_number = result[0][0]

            # Soft delete
            query = """
                UPDATE reports
                SET is_deleted = 1, updated_by = ?, updated_at = ?
                WHERE report_id = ?
            """
            self.db_manager.execute_with_retry(
                query,
                (current_user['username'], datetime.now().isoformat(), report_id)
            )

            self.logger.log_user_action(
                "REPORT_DELETED",
                {'report_id': report_id, 'report_number': report_number}
            )

            return True, "Report deleted successfully"

        except Exception as e:
            self.logger.error(f"Error deleting report: {str(e)}", exc_info=True)
            return False, f"Error deleting report: {str(e)}"

    def get_report(self, report_id: int) -> Optional[Dict]:
        """
        Get a single report by ID.

        Args:
            report_id: Report ID

        Returns:
            Report dictionary or None if not found
        """
        try:
            query = "SELECT * FROM reports WHERE report_id = ? AND is_deleted = 0"
            result = self.db_manager.execute_with_retry(query, (report_id,))

            if not result:
                return None

            # Get column names
            columns_query = "PRAGMA table_info(reports)"
            columns_result = self.db_manager.execute_with_retry(columns_query)
            column_names = [col[1] for col in columns_result]

            # Build dictionary
            report = dict(zip(column_names, result[0]))
            return report

        except Exception as e:
            self.logger.error(f"Error fetching report: {str(e)}", exc_info=True)
            return None

    def get_reports(self,
                    status: Optional[str] = None,
                    search_term: Optional[str] = None,
                    created_by: Optional[str] = None,
                    limit: int = 50,
                    offset: int = 0) -> Tuple[List[Dict], int]:
        """
        Get reports with optional filtering and pagination.

        Args:
            status: Filter by status
            search_term: Search in report_number, reported_entity_name, cic
            created_by: Filter by creator
            limit: Maximum number of records to return
            offset: Offset for pagination

        Returns:
            Tuple of (list of reports, total count)
        """
        try:
            # Build query
            query = "SELECT * FROM reports WHERE is_deleted = 0"
            count_query = "SELECT COUNT(*) FROM reports WHERE is_deleted = 0"
            params = []

            if status:
                query += " AND status = ?"
                count_query += " AND status = ?"
                params.append(status)

            if search_term:
                query += """ AND (
                    report_number LIKE ? OR
                    reported_entity_name LIKE ? OR
                    cic LIKE ?
                )"""
                count_query += """ AND (
                    report_number LIKE ? OR
                    reported_entity_name LIKE ? OR
                    cic LIKE ?
                )"""
                search_pattern = f"%{search_term}%"
                params.extend([search_pattern, search_pattern, search_pattern])

            if created_by:
                query += " AND created_by = ?"
                count_query += " AND created_by = ?"
                params.append(created_by)

            # Get total count
            count_result = self.db_manager.execute_with_retry(count_query, params)
            total_count = count_result[0][0] if count_result else 0

            # Add ordering and pagination
            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            # Execute query
            result = self.db_manager.execute_with_retry(query, params)

            # Get column names
            columns_query = "PRAGMA table_info(reports)"
            columns_result = self.db_manager.execute_with_retry(columns_query)
            column_names = [col[1] for col in columns_result]

            # Build list of dictionaries
            reports = []
            for row in result:
                reports.append(dict(zip(column_names, row)))

            return reports, total_count

        except Exception as e:
            self.logger.error(f"Error fetching reports: {str(e)}", exc_info=True)
            return [], 0

    def update_report_status(self, report_id: int, new_status: str, comment: Optional[str] = None) -> Tuple[bool, str]:
        """
        Update report status.

        Args:
            report_id: Report ID
            new_status: New status value
            comment: Optional comment for the status change

        Returns:
            Tuple of (success, message)
        """
        try:
            current_user = self.auth_service.get_current_user()
            if not current_user:
                return False, "User not authenticated"

            # Validate status
            valid_statuses = ['Open', 'Case Review', 'Under Investigation',
                            'Case Validation', 'Close Case', 'Closed with STR']
            if new_status not in valid_statuses:
                return False, f"Invalid status: {new_status}"

            # Get current status
            query = "SELECT status FROM reports WHERE report_id = ?"
            result = self.db_manager.execute_with_retry(query, (report_id,))

            if not result:
                return False, "Report not found"

            old_status = result[0][0]

            # Update status
            update_query = """
                UPDATE reports
                SET status = ?, updated_by = ?, updated_at = ?
                WHERE report_id = ?
            """
            self.db_manager.execute_with_retry(
                update_query,
                (new_status, current_user['username'], datetime.now().isoformat(), report_id)
            )

            # Status history is automatically logged by trigger
            # But we can add a comment if provided
            if comment:
                comment_query = """
                    UPDATE status_history
                    SET comment = ?
                    WHERE report_id = ? AND to_status = ?
                    ORDER BY changed_at DESC
                    LIMIT 1
                """
                self.db_manager.execute_with_retry(
                    comment_query,
                    (comment, report_id, new_status)
                )

            self.logger.log_user_action(
                "STATUS_CHANGED",
                {
                    'report_id': report_id,
                    'old_status': old_status,
                    'new_status': new_status,
                    'comment': comment
                }
            )

            return True, f"Status updated from '{old_status}' to '{new_status}'"

        except Exception as e:
            self.logger.error(f"Error updating status: {str(e)}", exc_info=True)
            return False, f"Error updating status: {str(e)}"

    def get_report_history(self, report_id: int) -> List[Dict]:
        """
        Get change history for a report.

        Args:
            report_id: Report ID

        Returns:
            List of change history dictionaries
        """
        try:
            query = """
                SELECT change_id, field_name, old_value, new_value,
                       change_type, change_reason, changed_by, changed_at
                FROM change_history
                WHERE table_name = 'reports' AND record_id = ?
                ORDER BY changed_at DESC
            """
            result = self.db_manager.execute_with_retry(query, (report_id,))

            history = []
            for row in result:
                history.append({
                    'change_id': row[0],
                    'field_name': row[1],
                    'old_value': row[2],
                    'new_value': row[3],
                    'change_type': row[4],
                    'change_reason': row[5],
                    'changed_by': row[6],
                    'changed_at': row[7]
                })

            return history

        except Exception as e:
            self.logger.error(f"Error fetching report history: {str(e)}", exc_info=True)
            return []

    def get_status_history(self, report_id: int) -> List[Dict]:
        """
        Get status change history for a report.

        Args:
            report_id: Report ID

        Returns:
            List of status history dictionaries
        """
        try:
            query = """
                SELECT status_history_id, from_status, to_status, comment,
                       changed_by, changed_at
                FROM status_history
                WHERE report_id = ?
                ORDER BY changed_at DESC
            """
            result = self.db_manager.execute_with_retry(query, (report_id,))

            history = []
            for row in result:
                history.append({
                    'status_history_id': row[0],
                    'from_status': row[1],
                    'to_status': row[2],
                    'comment': row[3],
                    'changed_by': row[4],
                    'changed_at': row[5]
                })

            return history

        except Exception as e:
            self.logger.error(f"Error fetching status history: {str(e)}", exc_info=True)
            return []
