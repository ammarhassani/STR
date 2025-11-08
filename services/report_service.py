"""
Report management service.
Handles CRUD operations for financial crime reports.
"""

import json
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

            # Convert sqlite3.Row to dictionary using keys() method
            row = result[0]
            report = {key: row[key] for key in row.keys()}
            return report

        except Exception as e:
            self.logger.error(f"Error fetching report: {str(e)}", exc_info=True)
            return None

    def get_reports(self,
                    status: Optional[str] = None,
                    search_term: Optional[str] = None,
                    date_from: Optional[str] = None,
                    date_to: Optional[str] = None,
                    created_by: Optional[str] = None,
                    limit: Optional[int] = 50,
                    offset: int = 0) -> Tuple[List[Dict], int]:
        """
        Get reports with optional filtering and pagination.

        Args:
            status: Filter by status
            search_term: Search in report_number, reported_entity_name, cic
            date_from: Filter by start date (YYYY-MM-DD)
            date_to: Filter by end date (YYYY-MM-DD)
            created_by: Filter by creator
            limit: Maximum number of records to return (None for all)
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

            if date_from:
                query += " AND report_date >= ?"
                count_query += " AND report_date >= ?"
                params.append(date_from)

            if date_to:
                query += " AND report_date <= ?"
                count_query += " AND report_date <= ?"
                params.append(date_to)

            if created_by:
                query += " AND created_by = ?"
                count_query += " AND created_by = ?"
                params.append(created_by)

            # Get total count
            count_result = self.db_manager.execute_with_retry(count_query, params)
            total_count = count_result[0][0] if count_result else 0

            # Add ordering and pagination
            query += " ORDER BY created_at DESC"
            if limit is not None:
                query += " LIMIT ? OFFSET ?"
                params.extend([limit, offset])

            # Execute query
            result = self.db_manager.execute_with_retry(query, params)

            # Convert sqlite3.Row objects to dictionaries
            # sqlite3.Row objects have keys() method that returns actual column names
            reports = []
            for row in result:
                # Create dict from sqlite3.Row using keys() - this preserves all column names correctly
                report_dict = {key: row[key] for key in row.keys()}
                reports.append(report_dict)

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

    # ==================== Version Management Methods ====================

    def create_version_snapshot(self, report_id: int, change_summary: str = "") -> Tuple[bool, Optional[int], str]:
        """
        Create a version snapshot of the current report state.

        Args:
            report_id: Report ID to snapshot
            change_summary: Summary of changes made

        Returns:
            Tuple of (success, version_id, message)
        """
        try:
            current_user = self.auth_service.get_current_user()
            if not current_user:
                return False, None, "User not authenticated"

            # Get current report data
            report = self.get_report(report_id)
            if not report:
                return False, None, "Report not found"

            # Convert report to JSON snapshot
            snapshot_data = json.dumps(report, default=str)

            # Get current version number
            current_version = report.get('current_version', 1)
            new_version_number = current_version + 1

            # Insert version snapshot
            insert_query = """
                INSERT INTO report_versions (report_id, version_number, snapshot_data, change_summary, created_by)
                VALUES (?, ?, ?, ?, ?)
            """
            self.db_manager.execute_with_retry(
                insert_query,
                (report_id, new_version_number, snapshot_data, change_summary, current_user['username'])
            )

            # Get the version_id
            result = self.db_manager.execute_with_retry("SELECT last_insert_rowid()")
            version_id = result[0][0] if result else None

            # Update report's current_version
            update_query = "UPDATE reports SET current_version = ? WHERE report_id = ?"
            self.db_manager.execute_with_retry(update_query, (new_version_number, report_id))

            self.logger.log_user_action(
                "VERSION_CREATED",
                {'report_id': report_id, 'version_number': new_version_number, 'version_id': version_id}
            )

            return True, version_id, f"Version {new_version_number} created successfully"

        except Exception as e:
            self.logger.error(f"Error creating version snapshot: {str(e)}", exc_info=True)
            return False, None, f"Error creating version snapshot: {str(e)}"

    def get_report_versions(self, report_id: int) -> List[Dict]:
        """
        Get all version history for a report.

        Args:
            report_id: Report ID

        Returns:
            List of version dictionaries
        """
        try:
            query = """
                SELECT version_id, version_number, change_summary, created_by, created_at
                FROM report_versions
                WHERE report_id = ?
                ORDER BY version_number DESC
            """
            result = self.db_manager.execute_with_retry(query, (report_id,))

            versions = []
            for row in result:
                versions.append({
                    'version_id': row[0],
                    'version_number': row[1],
                    'change_summary': row[2],
                    'created_by': row[3],
                    'created_at': row[4]
                })

            return versions

        except Exception as e:
            self.logger.error(f"Error fetching report versions: {str(e)}", exc_info=True)
            return []

    def get_version_snapshot(self, version_id: int) -> Optional[Dict]:
        """
        Get the full snapshot data for a specific version.

        Args:
            version_id: Version ID

        Returns:
            Report data dictionary or None
        """
        try:
            query = "SELECT snapshot_data FROM report_versions WHERE version_id = ?"
            result = self.db_manager.execute_with_retry(query, (version_id,))

            if not result:
                return None

            snapshot_data = json.loads(result[0][0])
            return snapshot_data

        except Exception as e:
            self.logger.error(f"Error fetching version snapshot: {str(e)}", exc_info=True)
            return None

    def restore_version(self, version_id: int, restore_reason: str = "") -> Tuple[bool, str]:
        """
        Restore a report to a previous version.

        Args:
            version_id: Version ID to restore
            restore_reason: Reason for restoring this version

        Returns:
            Tuple of (success, message)
        """
        try:
            current_user = self.auth_service.get_current_user()
            if not current_user:
                return False, "User not authenticated"

            # Check if user is admin
            if current_user.get('role') != 'Admin':
                return False, "Only administrators can restore versions"

            # Get version snapshot
            snapshot = self.get_version_snapshot(version_id)
            if not snapshot:
                return False, "Version not found"

            report_id = snapshot.get('report_id')
            if not report_id:
                return False, "Invalid version data"

            # Create a snapshot of current state before restoring
            self.create_version_snapshot(
                report_id,
                f"Backup before restoring to version {snapshot.get('current_version', 'unknown')}"
            )

            # Build update query with all fields from snapshot
            # Exclude system fields that shouldn't be restored
            exclude_fields = {'report_id', 'created_at', 'created_by', 'is_deleted', 'current_version'}
            fields_to_restore = {k: v for k, v in snapshot.items() if k not in exclude_fields}

            if not fields_to_restore:
                return False, "No fields to restore"

            set_clause = ', '.join([f"{field} = ?" for field in fields_to_restore.keys()])
            values = list(fields_to_restore.values())
            values.extend([current_user['username'], datetime.now().isoformat(), report_id])

            query = f"""
                UPDATE reports
                SET {set_clause}, updated_by = ?, updated_at = ?
                WHERE report_id = ?
            """
            self.db_manager.execute_with_retry(query, values)

            # Log the restoration
            change_query = """
                INSERT INTO change_history (table_name, record_id, field_name, old_value, new_value, change_type, change_reason, changed_by)
                VALUES ('reports', ?, 'version_restored', NULL, ?, 'RESTORE', ?, ?)
            """
            self.db_manager.execute_with_retry(
                change_query,
                (report_id, f"Version {version_id}", restore_reason, current_user['username'])
            )

            self.logger.log_user_action(
                "VERSION_RESTORED",
                {'report_id': report_id, 'version_id': version_id, 'reason': restore_reason}
            )

            return True, "Version restored successfully"

        except Exception as e:
            self.logger.error(f"Error restoring version: {str(e)}", exc_info=True)
            return False, f"Error restoring version: {str(e)}"

    def compare_versions(self, version_id_1: int, version_id_2: int) -> Optional[Dict[str, Dict]]:
        """
        Compare two versions and return the differences.

        Args:
            version_id_1: First version ID (typically older)
            version_id_2: Second version ID (typically newer)

        Returns:
            Dictionary with field differences or None on error
        """
        try:
            snapshot1 = self.get_version_snapshot(version_id_1)
            snapshot2 = self.get_version_snapshot(version_id_2)

            if not snapshot1 or not snapshot2:
                return None

            differences = {}
            all_keys = set(snapshot1.keys()) | set(snapshot2.keys())

            for key in all_keys:
                val1 = snapshot1.get(key)
                val2 = snapshot2.get(key)

                if val1 != val2:
                    differences[key] = {
                        'old_value': val1,
                        'new_value': val2
                    }

            return differences

        except Exception as e:
            self.logger.error(f"Error comparing versions: {str(e)}", exc_info=True)
            return None

    # ==================== Approval Workflow Methods ====================

    def request_approval(self, report_id: int, comment: str = "") -> Tuple[bool, Optional[int], str]:
        """
        Submit a report for admin approval.

        Args:
            report_id: Report ID to submit for approval
            comment: Optional comment for the approval request

        Returns:
            Tuple of (success, approval_id, message)
        """
        try:
            current_user = self.auth_service.get_current_user()
            if not current_user:
                return False, None, "User not authenticated"

            # Check if report exists
            report = self.get_report(report_id)
            if not report:
                return False, None, "Report not found"

            # Check current approval status
            current_approval_status = report.get('approval_status', 'draft')
            if current_approval_status == 'pending_approval':
                return False, None, "Report is already pending approval"
            elif current_approval_status == 'approved':
                return False, None, "Report is already approved"

            # Create version snapshot before submitting for approval
            success, version_id, msg = self.create_version_snapshot(
                report_id,
                "Submitted for approval"
            )

            if not success:
                return False, None, f"Failed to create version snapshot: {msg}"

            # Update report approval status
            update_query = """
                UPDATE reports
                SET approval_status = 'pending_approval', updated_by = ?, updated_at = ?
                WHERE report_id = ?
            """
            self.db_manager.execute_with_retry(
                update_query,
                (current_user['username'], datetime.now().isoformat(), report_id)
            )

            # Create approval request
            insert_query = """
                INSERT INTO report_approvals (report_id, version_id, approval_status, requested_by, approval_comment)
                VALUES (?, ?, 'pending', ?, ?)
            """
            self.db_manager.execute_with_retry(
                insert_query,
                (report_id, version_id, current_user['username'], comment)
            )

            # Get approval_id
            result = self.db_manager.execute_with_retry("SELECT last_insert_rowid()")
            approval_id = result[0][0] if result else None

            # Notify all admins
            admins = self.get_admin_users()
            for admin in admins:
                self.create_notification(
                    admin['user_id'],
                    "New Approval Request",
                    f"Report #{report.get('report_number', report_id)} has been submitted for approval by {current_user['username']}",
                    "approval_request",
                    report_id
                )

            self.logger.log_user_action(
                "APPROVAL_REQUESTED",
                {'report_id': report_id, 'approval_id': approval_id}
            )

            return True, approval_id, "Report submitted for approval successfully"

        except Exception as e:
            self.logger.error(f"Error requesting approval: {str(e)}", exc_info=True)
            return False, None, f"Error requesting approval: {str(e)}"

    def approve_report(self, approval_id: int, comment: str = "") -> Tuple[bool, str]:
        """
        Approve a report (admin only).

        Args:
            approval_id: Approval request ID
            comment: Optional approval comment

        Returns:
            Tuple of (success, message)
        """
        try:
            current_user = self.auth_service.get_current_user()
            if not current_user:
                return False, "User not authenticated"

            # Check if user is admin
            if current_user.get('role') != 'Admin':
                return False, "Only administrators can approve reports"

            # Get approval request
            approval_query = """
                SELECT report_id, approval_status, requested_by
                FROM report_approvals
                WHERE approval_id = ?
            """
            result = self.db_manager.execute_with_retry(approval_query, (approval_id,))

            if not result:
                return False, "Approval request not found"

            report_id, current_status, requested_by = result[0]

            if current_status != 'pending':
                return False, f"Approval request is already {current_status}"

            # Update approval request
            update_approval = """
                UPDATE report_approvals
                SET approval_status = 'approved',
                    approver_id = (SELECT user_id FROM users WHERE username = ?),
                    approval_comment = ?,
                    reviewed_at = ?
                WHERE approval_id = ?
            """
            self.db_manager.execute_with_retry(
                update_approval,
                (current_user['username'], comment, datetime.now().isoformat(), approval_id)
            )

            # Update report status
            update_report = """
                UPDATE reports
                SET approval_status = 'approved', updated_by = ?, updated_at = ?
                WHERE report_id = ?
            """
            self.db_manager.execute_with_retry(
                update_report,
                (current_user['username'], datetime.now().isoformat(), report_id)
            )

            # Notify the user who requested approval
            user_query = "SELECT user_id FROM users WHERE username = ?"
            user_result = self.db_manager.execute_with_retry(user_query, (requested_by,))
            if user_result:
                user_id = user_result[0][0]
                self.create_notification(
                    user_id,
                    "Report Approved",
                    f"Your report has been approved by {current_user['username']}: {comment}",
                    "approval_result",
                    report_id
                )

            self.logger.log_user_action(
                "REPORT_APPROVED",
                {'report_id': report_id, 'approval_id': approval_id, 'comment': comment}
            )

            return True, "Report approved successfully"

        except Exception as e:
            self.logger.error(f"Error approving report: {str(e)}", exc_info=True)
            return False, f"Error approving report: {str(e)}"

    def reject_report(self, approval_id: int, comment: str = "", request_rework: bool = False) -> Tuple[bool, str]:
        """
        Reject a report or request rework (admin only).

        Args:
            approval_id: Approval request ID
            comment: Rejection/rework comment
            request_rework: If True, set status to 'rework', otherwise 'rejected'

        Returns:
            Tuple of (success, message)
        """
        try:
            current_user = self.auth_service.get_current_user()
            if not current_user:
                return False, "User not authenticated"

            # Check if user is admin
            if current_user.get('role') != 'Admin':
                return False, "Only administrators can reject reports"

            # Get approval request
            approval_query = """
                SELECT report_id, approval_status, requested_by
                FROM report_approvals
                WHERE approval_id = ?
            """
            result = self.db_manager.execute_with_retry(approval_query, (approval_id,))

            if not result:
                return False, "Approval request not found"

            report_id, current_status, requested_by = result[0]

            if current_status != 'pending':
                return False, f"Approval request is already {current_status}"

            new_status = 'rework' if request_rework else 'rejected'

            # Update approval request
            update_approval = """
                UPDATE report_approvals
                SET approval_status = ?,
                    approver_id = (SELECT user_id FROM users WHERE username = ?),
                    approval_comment = ?,
                    reviewed_at = ?
                WHERE approval_id = ?
            """
            self.db_manager.execute_with_retry(
                update_approval,
                (new_status, current_user['username'], comment, datetime.now().isoformat(), approval_id)
            )

            # Update report status
            update_report = """
                UPDATE reports
                SET approval_status = ?, updated_by = ?, updated_at = ?
                WHERE report_id = ?
            """
            self.db_manager.execute_with_retry(
                update_report,
                (new_status, current_user['username'], datetime.now().isoformat(), report_id)
            )

            # Notify the user who requested approval
            user_query = "SELECT user_id FROM users WHERE username = ?"
            user_result = self.db_manager.execute_with_retry(user_query, (requested_by,))
            if user_result:
                user_id = user_result[0][0]
                action_text = "requires rework" if request_rework else "has been rejected"
                self.create_notification(
                    user_id,
                    "Report Needs Attention",
                    f"Your report {action_text} by {current_user['username']}: {comment}",
                    "approval_result",
                    report_id
                )

            self.logger.log_user_action(
                "REPORT_REJECTED" if not request_rework else "REPORT_REWORK_REQUESTED",
                {'report_id': report_id, 'approval_id': approval_id, 'comment': comment}
            )

            action_msg = "marked for rework" if request_rework else "rejected"
            return True, f"Report {action_msg} successfully"

        except Exception as e:
            self.logger.error(f"Error rejecting report: {str(e)}", exc_info=True)
            return False, f"Error rejecting report: {str(e)}"

    def get_pending_approvals(self, approver_id: Optional[int] = None) -> List[Dict]:
        """
        Get list of pending approval requests.

        Args:
            approver_id: Optional filter by approver (admin) ID

        Returns:
            List of pending approval dictionaries with report details
        """
        try:
            query = """
                SELECT
                    ra.approval_id,
                    ra.report_id,
                    r.report_number,
                    r.reported_entity_name,
                    ra.requested_by,
                    ra.requested_at,
                    ra.approval_comment,
                    r.status
                FROM report_approvals ra
                JOIN reports r ON ra.report_id = r.report_id
                WHERE ra.approval_status = 'pending'
                ORDER BY ra.requested_at DESC
            """
            result = self.db_manager.execute_with_retry(query)

            approvals = []
            for row in result:
                approvals.append({
                    'approval_id': row[0],
                    'report_id': row[1],
                    'report_number': row[2],
                    'reported_entity_name': row[3],
                    'requested_by': row[4],
                    'requested_at': row[5],
                    'comment': row[6],
                    'report_status': row[7]
                })

            return approvals

        except Exception as e:
            self.logger.error(f"Error fetching pending approvals: {str(e)}", exc_info=True)
            return []

    def get_user_approval_requests(self, user_id: Optional[int] = None) -> List[Dict]:
        """
        Get approval requests submitted by a specific user or current user.

        Args:
            user_id: User ID (None for current user)

        Returns:
            List of approval request dictionaries
        """
        try:
            current_user = self.auth_service.get_current_user()
            if not current_user:
                return []

            username = current_user['username']
            if user_id:
                # Get username from user_id
                user_query = "SELECT username FROM users WHERE user_id = ?"
                user_result = self.db_manager.execute_with_retry(user_query, (user_id,))
                if user_result:
                    username = user_result[0][0]

            query = """
                SELECT
                    ra.approval_id,
                    ra.report_id,
                    r.report_number,
                    r.reported_entity_name,
                    ra.approval_status,
                    ra.requested_at,
                    ra.reviewed_at,
                    ra.approval_comment,
                    u.username as approver_name
                FROM report_approvals ra
                JOIN reports r ON ra.report_id = r.report_id
                LEFT JOIN users u ON ra.approver_id = u.user_id
                WHERE ra.requested_by = ?
                ORDER BY ra.requested_at DESC
            """
            result = self.db_manager.execute_with_retry(query, (username,))

            requests = []
            for row in result:
                requests.append({
                    'approval_id': row[0],
                    'report_id': row[1],
                    'report_number': row[2],
                    'reported_entity_name': row[3],
                    'approval_status': row[4],
                    'requested_at': row[5],
                    'reviewed_at': row[6],
                    'comment': row[7],
                    'approver_name': row[8]
                })

            return requests

        except Exception as e:
            self.logger.error(f"Error fetching user approval requests: {str(e)}", exc_info=True)
            return []

    # ==================== Notification Methods ====================

    def create_notification(self, user_id: int, title: str, message: str,
                          notification_type: str = "info", related_report_id: Optional[int] = None) -> Tuple[bool, Optional[int]]:
        """
        Create a notification for a user.

        Args:
            user_id: User ID to notify
            title: Notification title
            message: Notification message
            notification_type: Type (info, warning, approval_request, approval_result)
            related_report_id: Optional related report ID

        Returns:
            Tuple of (success, notification_id)
        """
        try:
            query = """
                INSERT INTO notifications (user_id, title, message, notification_type, related_report_id)
                VALUES (?, ?, ?, ?, ?)
            """
            self.db_manager.execute_with_retry(
                query,
                (user_id, title, message, notification_type, related_report_id)
            )

            result = self.db_manager.execute_with_retry("SELECT last_insert_rowid()")
            notification_id = result[0][0] if result else None

            return True, notification_id

        except Exception as e:
            self.logger.error(f"Error creating notification: {str(e)}", exc_info=True)
            return False, None

    def get_user_notifications(self, user_id: Optional[int] = None, unread_only: bool = False) -> List[Dict]:
        """
        Get notifications for a user.

        Args:
            user_id: User ID (None for current user)
            unread_only: If True, only return unread notifications

        Returns:
            List of notification dictionaries
        """
        try:
            current_user = self.auth_service.get_current_user()
            if not current_user:
                return []

            target_user_id = user_id or current_user.get('user_id')
            if not target_user_id:
                return []

            query = """
                SELECT notification_id, title, message, notification_type,
                       related_report_id, is_read, created_at
                FROM notifications
                WHERE user_id = ?
            """

            if unread_only:
                query += " AND is_read = 0"

            query += " ORDER BY created_at DESC LIMIT 50"

            result = self.db_manager.execute_with_retry(query, (target_user_id,))

            notifications = []
            for row in result:
                notifications.append({
                    'notification_id': row[0],
                    'title': row[1],
                    'message': row[2],
                    'notification_type': row[3],
                    'related_report_id': row[4],
                    'is_read': bool(row[5]),
                    'created_at': row[6]
                })

            return notifications

        except Exception as e:
            self.logger.error(f"Error fetching notifications: {str(e)}", exc_info=True)
            return []

    def mark_notification_read(self, notification_id: int) -> Tuple[bool, str]:
        """
        Mark a notification as read.

        Args:
            notification_id: Notification ID

        Returns:
            Tuple of (success, message)
        """
        try:
            query = "UPDATE notifications SET is_read = 1 WHERE notification_id = ?"
            self.db_manager.execute_with_retry(query, (notification_id,))
            return True, "Notification marked as read"

        except Exception as e:
            self.logger.error(f"Error marking notification as read: {str(e)}", exc_info=True)
            return False, f"Error: {str(e)}"

    def get_unread_notification_count(self, user_id: Optional[int] = None) -> int:
        """
        Get count of unread notifications for a user.

        Args:
            user_id: User ID (None for current user)

        Returns:
            Count of unread notifications
        """
        try:
            current_user = self.auth_service.get_current_user()
            if not current_user:
                return 0

            target_user_id = user_id or current_user.get('user_id')
            if not target_user_id:
                return 0

            query = "SELECT COUNT(*) FROM notifications WHERE user_id = ? AND is_read = 0"
            result = self.db_manager.execute_with_retry(query, (target_user_id,))
            return result[0][0] if result else 0

        except Exception as e:
            self.logger.error(f"Error getting unread count: {str(e)}", exc_info=True)
            return 0

    # ==================== Helper Methods ====================

    def get_admin_users(self) -> List[Dict]:
        """
        Get list of all admin users.

        Returns:
            List of admin user dictionaries
        """
        try:
            query = "SELECT user_id, username, full_name FROM users WHERE role = 'Admin' AND is_active = 1"
            result = self.db_manager.execute_with_retry(query)

            admins = []
            for row in result:
                admins.append({
                    'user_id': row[0],
                    'username': row[1],
                    'full_name': row[2]
                })

            return admins

        except Exception as e:
            self.logger.error(f"Error fetching admin users: {str(e)}", exc_info=True)
            return []
