"""
Report management service.
Handles CRUD operations for financial crime reports.
"""

import json
from datetime import datetime
from typing import Optional, Dict, List, Tuple, Any


class ReportService:
    """Service for managing financial crime reports."""

    # Security: Whitelist of allowed report fields to prevent SQL injection
    ALLOWED_FIELDS = {
        'sn', 'report_number', 'report_date', 'outgoing_letter_number',
        'reported_entity_name', 'legal_entity_owner', 'gender', 'nationality',
        'id_cr', 'account_membership', 'branch_id', 'cic',
        'first_reason_for_suspicion', 'second_reason_for_suspicion',
        'type_of_suspected_transaction', 'arb_staff', 'total_transaction',
        'report_classification', 'report_source', 'reporting_entity',
        'reporter_initials', 'sending_date', 'original_copy_confirmation',
        'fiu_number', 'fiu_letter_receive_date', 'fiu_feedback',
        'fiu_letter_number', 'fiu_date', 'current_version',
        'approval_status', 'legal_entity_owner_checkbox', 'acc_membership_checkbox',
        'relationship', 'id_type', 'case_id'
    }

    # Coarse per-field length backstop (characters). Real format rules live in
    # column_settings; this just stops storage/DoS abuse of unbounded TEXT.
    MAX_FIELD_LEN = 10000

    def __init__(self, db_manager, logging_service, auth_service, activity_service=None):
        """
        Initialize the report service.

        Args:
            db_manager: DatabaseManager instance
            logging_service: LoggingService instance
            auth_service: AuthService instance
            activity_service: ActivityService instance (for logging activities)
        """
        self.db_manager = db_manager
        self.logger = logging_service
        self.auth_service = auth_service
        self.activity_service = activity_service
        self._report_number_service = None

    def set_activity_service(self, activity_service):
        """Set activity service (for late binding to avoid circular imports)."""
        self.activity_service = activity_service

    def set_report_number_service(self, svc):
        """Set report number service (for late binding to avoid circular imports)."""
        self._report_number_service = svc

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

            # Authorization: only roles with add_report may create (reporters cannot)
            if not self.auth_service.has_permission('add_report'):
                return False, None, "You do not have permission to create reports"

            # Gate on an owned reserved number unless the caller supplied an
            # explicit report_number (admin/import path bypasses the gate).
            rns = self._report_number_service
            consumed_number = None
            if rns and not report_data.get('report_number'):
                if rns.get_available_count(current_user['username']) < 1:
                    return False, None, "You have no reserved numbers — reserve first"
                # Host is single-writer: the lowest available now is the same
                # one consume_next_available takes after insert below.
                avail = rns.get_available_numbers(current_user['username'])
                consumed_number = avail[0]['report_number']
                report_data = dict(report_data)
                report_data['report_number'] = consumed_number
                report_data['sn'] = avail[0]['serial_number']

            # Reject absurdly long field values (storage/DoS guard). Field-level
            # format rules live in column_settings; this is a coarse backstop.
            for k, v in report_data.items():
                if isinstance(v, str) and len(v) > self.MAX_FIELD_LEN:
                    return False, None, f"Field '{k}' exceeds maximum length"

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

            # CIC uniqueness across NON-deleted reports (a deleted report's CIC
            # is reusable). Data-integrity rule — enforced here, not just the UI.
            cic = report_data.get('cic')
            if cic:
                dup = self.db_manager.execute_with_retry(
                    "SELECT COUNT(*) FROM reports WHERE cic = ? AND is_deleted = 0", (cic,))
                if dup and dup[0][0] > 0:
                    return False, None, "A report already exists for this CIC"

            # Case ID uniqueness (optional field; same non-deleted scope)
            case_id = report_data.get('case_id')
            if case_id:
                dup = self.db_manager.execute_with_retry(
                    "SELECT COUNT(*) FROM reports WHERE case_id = ? AND is_deleted = 0", (case_id,))
                if dup and dup[0][0] > 0:
                    return False, None, "A report already exists for this Case ID"

            # Security: Filter fields against whitelist to prevent SQL injection
            allowed_data = {k: v for k, v in report_data.items() if k in self.ALLOWED_FIELDS}
            invalid_fields = set(report_data.keys()) - self.ALLOWED_FIELDS
            if invalid_fields:
                self.logger.warning(f"Ignored invalid fields in create_report: {invalid_fields}")

            # Build insert query
            fields = list(allowed_data.keys())
            fields.extend(['created_by', 'created_at'])
            placeholders = ', '.join(['?'] * len(fields))
            field_names = ', '.join(fields)

            values = list(allowed_data.values())
            values.extend([
                current_user['username'],
                datetime.now().isoformat()
            ])

            # Note: 'status' field removed per user requirements

            query = f"INSERT INTO reports ({field_names}) VALUES ({placeholders})"
            self.db_manager.execute_with_retry(query, values)

            # Get the inserted report ID by querying with unique report_number
            # Note: last_insert_rowid() doesn't work across different connections
            result = self.db_manager.execute_with_retry(
                "SELECT report_id FROM reports WHERE report_number = ?",
                (report_data['report_number'],)
            )
            report_id = result[0][0] if result else None

            if not report_id:
                self.logger.error("Failed to get report_id after insert")
                return False, None, "Failed to get report ID after creation"

            # Consume the reserved number we injected above, linking it to the
            # new report. This runs immediately after the insert (no throwing
            # user code in between) so the reservation can't be orphaned by a
            # later exception; skipped for explicit report_number.
            if consumed_number and rns:
                consume_ok, _, consume_msg = rns.consume_next_available(current_user['username'], report_id)
                if not consume_ok:
                    self.logger.warning(
                        f"Failed to consume reserved number {consumed_number} "
                        f"for report_id {report_id}: {consume_msg} — number may remain 'available'"
                    )

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

            # Log to activity service for GitHub-style activity feed
            if self.activity_service:
                self.activity_service.log_activity(
                    action_type='CREATE',
                    description=f"{current_user['username']} created Report #{report_data['report_number']}",
                    report_id=report_id,
                    report_number=report_data['report_number'],
                    metadata={
                        'entity_name': report_data.get('reported_entity_name', ''),
                        'approval_status': report_data.get('approval_status', 'draft')
                    }
                )

            # Handle approval workflow based on user role
            user_role = current_user.get('role', '')
            print(f"[DEBUG] Report {report_id} created by '{current_user['username']}' with role: '{user_role}'")
            self.logger.info(f"Report {report_id} approval workflow - user role: '{user_role}'")

            if user_role == 'admin':
                # Admin-created reports are auto-approved
                approval_query = """
                    UPDATE reports
                    SET approval_status = 'approved', updated_by = ?, updated_at = ?
                    WHERE report_id = ?
                """
                self.db_manager.execute_with_retry(
                    approval_query,
                    (current_user['username'], datetime.now().isoformat(), report_id)
                )
                self.logger.info(f"Report {report_id} auto-approved (created by admin)")

            else:
                # Non-admin reports: auto-submit for approval
                # Set report status to pending_approval
                approval_query = """
                    UPDATE reports
                    SET approval_status = 'pending_approval', updated_by = ?, updated_at = ?
                    WHERE report_id = ?
                """
                self.db_manager.execute_with_retry(
                    approval_query,
                    (current_user['username'], datetime.now().isoformat(), report_id)
                )

                # Create approval request in report_approvals table
                insert_approval = """
                    INSERT INTO report_approvals (report_id, version_id, approval_status, requested_by, approval_comment, requested_at)
                    VALUES (?, NULL, 'pending', ?, 'Auto-submitted on creation', datetime('now'))
                """
                self.db_manager.execute_with_retry(
                    insert_approval,
                    (report_id, current_user['username'])
                )

                self.logger.info(f"Report {report_id} auto-submitted for approval (created by {user_role})")

            # Create initial version snapshot (v1) for the newly created report
            try:
                # Get the report data we just created for the snapshot
                report_for_snapshot = self.get_report(report_id)
                if report_for_snapshot:
                    snapshot_data = json.dumps(report_for_snapshot, default=str)
                    version_insert = """
                        INSERT INTO report_versions (report_id, version_number, snapshot_data, change_summary, created_by)
                        VALUES (?, 1, ?, 'Initial creation', ?)
                    """
                    self.db_manager.execute_with_retry(
                        version_insert,
                        (report_id, snapshot_data, current_user['username'])
                    )

                    # Update report's current_version to 1
                    self.db_manager.execute_with_retry(
                        "UPDATE reports SET current_version = 1 WHERE report_id = ?",
                        (report_id,)
                    )
                    self.logger.info(f"Created initial version (v1) for report {report_id}")
            except Exception as ve:
                # Don't fail the entire operation if version creation fails
                self.logger.warning(f"Failed to create initial version for report {report_id}: {ve}")

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
            old_report = self.get_report(report_id)
            if not old_report:
                return False, "Report not found"

            # Authorization: admins edit any report; agents only their own;
            # reporters not at all. Uses the RBAC ownership rule.
            if not self.auth_service.has_permission('edit_report',
                                                    resource_owner=old_report.get('created_by')):
                return False, "You do not have permission to edit this report"

            # Reject absurdly long field values (storage/DoS guard)
            for k, v in report_data.items():
                if isinstance(v, str) and len(v) > self.MAX_FIELD_LEN:
                    return False, f"Field '{k}' exceeds maximum length"

            # CIC / Case ID uniqueness across other non-deleted reports
            if report_data.get('cic'):
                dup = self.db_manager.execute_with_retry(
                    "SELECT COUNT(*) FROM reports WHERE cic = ? AND is_deleted = 0 AND report_id != ?",
                    (report_data['cic'], report_id))
                if dup and dup[0][0] > 0:
                    return False, "A report already exists for this CIC"
            if report_data.get('case_id'):
                dup = self.db_manager.execute_with_retry(
                    "SELECT COUNT(*) FROM reports WHERE case_id = ? AND is_deleted = 0 AND report_id != ?",
                    (report_data['case_id'], report_id))
                if dup and dup[0][0] > 0:
                    return False, "A report already exists for this Case ID"

            # Security: Filter fields against whitelist to prevent SQL injection
            allowed_data = {k: v for k, v in report_data.items() if k in self.ALLOWED_FIELDS}
            invalid_fields = set(report_data.keys()) - self.ALLOWED_FIELDS
            if invalid_fields:
                self.logger.warning(f"Ignored invalid fields in update_report: {invalid_fields}")

            # Only include fields that actually changed
            changed_data = {}
            for field, new_value in allowed_data.items():
                old_value = old_report.get(field)
                # Compare values (handle None vs empty string)
                old_str = str(old_value) if old_value is not None else ''
                new_str = str(new_value) if new_value is not None else ''
                if old_str != new_str:
                    changed_data[field] = new_value

            # Build update query with only changed fields
            fields = list(changed_data.keys())
            if not fields:
                return True, "No changes detected"  # Not an error, just nothing to update

            set_clause = ', '.join([f"{field} = ?" for field in fields])
            values = list(changed_data.values())
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

            # Get report number for activity logging
            report_number_query = "SELECT report_number, reported_entity_name FROM reports WHERE report_id = ?"
            report_info = self.db_manager.execute_with_retry(report_number_query, (report_id,))
            report_number = report_info[0][0] if report_info else str(report_id)
            entity_name = report_info[0][1] if report_info else ''

            # Log to activity service for GitHub-style activity feed
            if self.activity_service:
                # Create a description that shows what fields were changed
                if len(fields) == 1:
                    field_name = fields[0].replace('_', ' ').title()
                    description = f"{current_user['username']} updated {field_name} in Report #{report_number}"
                elif len(fields) <= 3:
                    field_names = ', '.join([f.replace('_', ' ').title() for f in fields])
                    description = f"{current_user['username']} updated {field_names} in Report #{report_number}"
                else:
                    description = f"{current_user['username']} updated {len(fields)} fields in Report #{report_number}"

                self.activity_service.log_activity(
                    action_type='UPDATE',
                    description=description,
                    report_id=report_id,
                    report_number=report_number,
                    metadata={
                        'entity_name': entity_name,
                        'fields_updated': fields,
                        'field_count': len(fields)
                    }
                )

            return True, "Report updated successfully"

        except Exception as e:
            self.logger.error(f"Error updating report: {str(e)}", exc_info=True)
            return False, f"Error updating report: {str(e)}"

    def delete_report(self, report_id: int) -> Tuple[bool, str]:
        """
        Delete a report (soft delete). Admin only.

        Args:
            report_id: Report ID to delete

        Returns:
            Tuple of (success, message)
        """
        try:
            current_user = self.auth_service.get_current_user()
            if not current_user:
                return False, "User not authenticated"

            # Check if user is admin
            if current_user.get('role') != 'admin':
                return False, "Only administrators can delete reports"

            # Check if report exists
            check_query = "SELECT report_number, reported_entity_name, is_deleted, approval_status FROM reports WHERE report_id = ?"
            result = self.db_manager.execute_with_retry(check_query, (report_id,))

            if not result:
                return False, "Report not found"

            report_number = result[0][0]
            entity_name = result[0][1]
            is_deleted = result[0][2]
            approval_status = result[0][3]

            if is_deleted:
                return False, "Report is already deleted"

            # Business rule: a report awaiting a decision must not be deleted out
            # from under the approver — decide (approve/reject/rework) first.
            if approval_status == 'pending_approval':
                return False, "Cannot delete a report that is pending approval; decide it first"

            # Soft delete with tracking
            query = """
                UPDATE reports
                SET is_deleted = 1, updated_by = ?, updated_at = ?,
                    deleted_at = ?, deleted_by = ?
                WHERE report_id = ?
            """
            now = datetime.now().isoformat()
            self.db_manager.execute_with_retry(
                query,
                (current_user['username'], now, now, current_user['username'], report_id)
            )

            self.logger.log_user_action(
                "REPORT_DELETED",
                {'report_id': report_id, 'report_number': report_number}
            )

            # Log to activity service if available
            if self.activity_service:
                self.activity_service.log_activity(
                    action_type='SOFT_DELETE',
                    description=f"{current_user['username']} deleted Report #{report_number}",
                    report_id=report_id,
                    report_number=report_number,
                    metadata={'entity_name': entity_name, 'delete_type': 'soft'}
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
                    offset: int = 0,
                    include_deleted: bool = False) -> Tuple[List[Dict], int]:
        """
        Get reports with optional filtering and pagination.

        Args:
            status: Filter by approval status (draft, pending_approval, approved, rejected, rework)
            search_term: Search in report_number, reported_entity_name, cic
            date_from: Filter by start date (YYYY-MM-DD)
            date_to: Filter by end date (YYYY-MM-DD)
            created_by: Filter by creator
            limit: Maximum number of records to return (None for all)
            offset: Offset for pagination
            include_deleted: Whether to include soft-deleted reports

        Returns:
            Tuple of (list of reports, total count)
        """
        try:
            # Build query
            if include_deleted:
                query = "SELECT * FROM reports WHERE 1=1"
                count_query = "SELECT COUNT(*) FROM reports WHERE 1=1"
            else:
                query = "SELECT * FROM reports WHERE is_deleted = 0"
                count_query = "SELECT COUNT(*) FROM reports WHERE is_deleted = 0"
            params = []

            if status:
                query += " AND approval_status = ?"
                count_query += " AND approval_status = ?"
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

    def hard_delete_report(self, report_id: int, reason: str = "", system: bool = False) -> Tuple[bool, str]:
        """
        Permanently delete a report (admin only). Cascades to versions, approvals, etc.

        Args:
            report_id: Report ID to delete
            reason: Reason for deletion

        Returns:
            Tuple of (success, message)
        """
        try:
            # system=True is the scheduler's auto-purge path (no interactive
            # user); interactive callers still require admin.
            if not system:
                current_user = self.auth_service.get_current_user()
                if not current_user:
                    return False, "User not authenticated"
                if current_user.get('role') != 'admin':
                    return False, "Only administrators can permanently delete reports"

            # Get report info for logging
            check_query = "SELECT report_number, reported_entity_name FROM reports WHERE report_id = ?"
            result = self.db_manager.execute_with_retry(check_query, (report_id,))

            if not result:
                return False, "Report not found"

            report_number = result[0][0]
            entity_name = result[0][1]

            # Get counts for warning
            version_count = self.db_manager.execute_with_retry(
                "SELECT COUNT(*) FROM report_versions WHERE report_id = ?", (report_id,)
            )[0][0]
            approval_count = self.db_manager.execute_with_retry(
                "SELECT COUNT(*) FROM report_approvals WHERE report_id = ?", (report_id,)
            )[0][0]

            # Delete related records first (cascade)
            self.db_manager.execute_with_retry(
                "DELETE FROM report_versions WHERE report_id = ?", (report_id,)
            )
            self.db_manager.execute_with_retry(
                "DELETE FROM report_approvals WHERE report_id = ?", (report_id,)
            )
            self.db_manager.execute_with_retry(
                "DELETE FROM status_history WHERE report_id = ?", (report_id,)
            )
            self.db_manager.execute_with_retry(
                "DELETE FROM change_history WHERE table_name = 'reports' AND record_id = ?", (report_id,)
            )
            self.db_manager.execute_with_retry(
                "DELETE FROM notifications WHERE related_report_id = ?", (report_id,)
            )

            # Delete the report itself
            self.db_manager.execute_with_retry(
                "DELETE FROM reports WHERE report_id = ?", (report_id,)
            )

            self.logger.log_user_action(
                "REPORT_HARD_DELETED",
                {
                    'report_id': report_id,
                    'report_number': report_number,
                    'versions_deleted': version_count,
                    'approvals_deleted': approval_count,
                    'reason': reason
                }
            )

            # Log to activity service if available
            actor = 'SYSTEM' if system else self.auth_service.get_current_user()['username']
            if self.activity_service:
                self.activity_service.log_activity(
                    action_type='HARD_DELETE',
                    description=f"{actor} permanently deleted Report #{report_number}",
                    report_id=None,  # Report no longer exists
                    report_number=report_number,
                    metadata={
                        'entity_name': entity_name,
                        'versions_deleted': version_count,
                        'approvals_deleted': approval_count,
                        'reason': reason
                    }
                )

            return True, f"Report #{report_number} permanently deleted ({version_count} versions, {approval_count} approvals removed)"

        except Exception as e:
            self.logger.error(f"Error hard deleting report: {str(e)}", exc_info=True)
            return False, f"Error deleting report: {str(e)}"

    def restore_report(self, report_id: int) -> Tuple[bool, str]:
        """
        Restore a soft-deleted report (admin only).

        Args:
            report_id: Report ID to restore

        Returns:
            Tuple of (success, message)
        """
        try:
            current_user = self.auth_service.get_current_user()
            if not current_user:
                return False, "User not authenticated"

            # Check if user is admin
            if current_user.get('role') != 'admin':
                return False, "Only administrators can restore deleted reports"

            # Get report info
            check_query = "SELECT report_number, reported_entity_name, is_deleted FROM reports WHERE report_id = ?"
            result = self.db_manager.execute_with_retry(check_query, (report_id,))

            if not result:
                return False, "Report not found"

            report_number = result[0][0]
            entity_name = result[0][1]
            is_deleted = result[0][2]

            if not is_deleted:
                return False, "Report is not deleted"

            # Restore the report
            query = """
                UPDATE reports
                SET is_deleted = 0, deleted_at = NULL, deleted_by = NULL,
                    updated_by = ?, updated_at = ?
                WHERE report_id = ?
            """
            self.db_manager.execute_with_retry(
                query,
                (current_user['username'], datetime.now().isoformat(), report_id)
            )

            self.logger.log_user_action(
                "REPORT_RESTORED",
                {'report_id': report_id, 'report_number': report_number}
            )

            # Log to activity service if available
            if self.activity_service:
                self.activity_service.log_activity(
                    action_type='UNDELETE',
                    description=f"{current_user['username']} restored Report #{report_number}",
                    report_id=report_id,
                    report_number=report_number,
                    metadata={'entity_name': entity_name}
                )

            return True, f"Report #{report_number} restored successfully"

        except Exception as e:
            self.logger.error(f"Error restoring report: {str(e)}", exc_info=True)
            return False, f"Error restoring report: {str(e)}"

    def get_deleted_reports_count(self) -> int:
        """
        Get count of soft-deleted reports.

        Returns:
            Number of deleted reports
        """
        try:
            result = self.db_manager.execute_with_retry(
                "SELECT COUNT(*) FROM reports WHERE is_deleted = 1"
            )
            return result[0][0] if result else 0
        except Exception as e:
            self.logger.error(f"Error getting deleted reports count: {str(e)}", exc_info=True)
            return 0

    def get_report_impact(self, report_id: int) -> Dict[str, int]:
        """
        Get counts of related records that would be affected by hard delete.

        Args:
            report_id: Report ID

        Returns:
            Dictionary with counts of related records
        """
        try:
            versions = self.db_manager.execute_with_retry(
                "SELECT COUNT(*) FROM report_versions WHERE report_id = ?", (report_id,)
            )[0][0]
            approvals = self.db_manager.execute_with_retry(
                "SELECT COUNT(*) FROM report_approvals WHERE report_id = ?", (report_id,)
            )[0][0]
            pending_approvals = self.db_manager.execute_with_retry(
                "SELECT COUNT(*) FROM report_approvals WHERE report_id = ? AND approval_status = 'pending'",
                (report_id,)
            )[0][0]

            return {
                'versions': versions,
                'approvals': approvals,
                'pending_approvals': pending_approvals
            }
        except Exception as e:
            self.logger.error(f"Error getting report impact: {str(e)}", exc_info=True)
            return {'versions': 0, 'approvals': 0, 'pending_approvals': 0}

    # ---- Record-edit locking (R28) -------------------------------------
    # One editor per report at a time. Locks auto-expire after the session
    # window so a crashed/closed client never leaves a report stuck.
    LOCK_MINUTES = 30

    def acquire_edit_lock(self, report_id: int) -> Tuple[bool, Optional[str], str]:
        """Try to lock a report for editing by the current user.
        Returns (acquired, holder_display_name, message). If already held by
        someone else, acquired=False and holder_display_name names them."""
        try:
            user = self.auth_service.get_current_user()
            if not user:
                return False, None, "Not authenticated"
            username = user['username']
            display = user.get('full_name') or username

            # drop expired locks first
            self.db_manager.execute_write(
                "DELETE FROM report_locks WHERE expires_at < datetime('now')")
            # the INSERT is the atomic decision point (report_id is PK)
            n = self.db_manager.execute_write(
                "INSERT OR IGNORE INTO report_locks "
                "(report_id, locked_by, locked_by_name, expires_at) "
                "VALUES (?, ?, ?, datetime('now', '+' || ? || ' minutes'))",
                (report_id, username, display, self.LOCK_MINUTES))
            if n == 1:
                return True, None, "Lock acquired"
            # already locked — is it mine?
            holder = self.db_manager.execute_with_retry(
                "SELECT locked_by, locked_by_name FROM report_locks WHERE report_id = ?",
                (report_id,))
            if holder and holder[0][0] == username:
                self.db_manager.execute_write(
                    "UPDATE report_locks SET expires_at = datetime('now', '+' || ? || ' minutes') "
                    "WHERE report_id = ?", (self.LOCK_MINUTES, report_id))
                return True, None, "Lock refreshed"
            holder_name = holder[0][1] if holder else "another user"
            return False, holder_name, f"This report is currently being edited by {holder_name}"
        except Exception as e:
            self.logger.error(f"Error acquiring edit lock: {str(e)}", exc_info=True)
            # fail-open would allow concurrent edits; fail-closed is safer
            return False, None, "Could not acquire edit lock"

    def release_edit_lock(self, report_id: int) -> bool:
        """Release the current user's lock on a report (no-op if not held)."""
        try:
            user = self.auth_service.get_current_user()
            if not user:
                return False
            self.db_manager.execute_write(
                "DELETE FROM report_locks WHERE report_id = ? AND locked_by = ?",
                (report_id, user['username']))
            return True
        except Exception as e:
            self.logger.error(f"Error releasing edit lock: {str(e)}", exc_info=True)
            return False

    def get_lock_holder(self, report_id: int) -> Optional[str]:
        """Return the display name currently holding an unexpired lock, else None."""
        try:
            self.db_manager.execute_write(
                "DELETE FROM report_locks WHERE expires_at < datetime('now')")
            r = self.db_manager.execute_with_retry(
                "SELECT locked_by_name FROM report_locks WHERE report_id = ?", (report_id,))
            return r[0][0] if r else None
        except Exception:
            return None

    def purge_expired_deleted_reports(self, retention_days: int = 30) -> Tuple[int, str]:
        """Hard-delete reports soft-deleted longer than retention_days (R80).
        Returns (count_purged, message). Meant to be called by the scheduler."""
        try:
            rows = self.db_manager.execute_with_retry(
                "SELECT report_id FROM reports WHERE is_deleted = 1 "
                "AND deleted_at IS NOT NULL "
                "AND deleted_at < datetime('now', '-' || ? || ' days')",
                (retention_days,))
            ids = [r[0] for r in rows] if rows else []
            purged = 0
            for rid in ids:
                # reuse the audited cascade hard-delete
                ok, _ = self.hard_delete_report(rid, reason=f"Auto-purge after {retention_days} days")
                if ok:
                    purged += 1
            if purged:
                self.logger.info(f"Auto-purged {purged} expired deleted report(s)")
            return purged, f"Purged {purged} report(s)"
        except Exception as e:
            self.logger.error(f"Error purging deleted reports: {str(e)}", exc_info=True)
            return 0, f"Purge error: {str(e)}"
