"""
Approval & Notification Service
Handles report approval workflow and user notifications.
"""

from datetime import datetime
from typing import Optional, Dict, List, Tuple


class ApprovalService:
    """Service for managing report approvals and notifications."""

    def __init__(self, db_manager, logging_service, auth_service, version_service, report_service):
        """
        Initialize the approval service.

        Args:
            db_manager: DatabaseManager instance
            logging_service: LoggingService instance
            auth_service: AuthService instance
            version_service: VersionService instance (for creating snapshots)
            report_service: ReportService instance (for getting report data)
        """
        self.db_manager = db_manager
        self.logger = logging_service
        self.auth_service = auth_service
        self.version_service = version_service
        self.report_service = report_service

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
            report = self.report_service.get_report(report_id)
            if not report:
                return False, None, "Report not found"

            # Check current approval status
            current_approval_status = report.get('approval_status', 'draft')
            if current_approval_status == 'pending_approval':
                return False, None, "Report is already pending approval"
            elif current_approval_status == 'approved':
                return False, None, "Report is already approved"

            # Create version snapshot before submitting for approval
            success, version_id, msg = self.version_service.create_version_snapshot(
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
            if current_user.get('role') != 'admin':
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
            if current_user.get('role') != 'admin':
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

    def get_all_approvals(self, status_filter: Optional[str] = None, limit: int = 100, offset: int = 0) -> Tuple[List[Dict], int]:
        """
        Get all approval requests with optional filtering (admin only).

        Args:
            status_filter: Filter by status ('pending', 'approved', 'rejected', 'rework', or None for all)
            limit: Maximum number of records to return
            offset: Number of records to skip (for pagination)

        Returns:
            Tuple of (list of approval dictionaries, total count)
        """
        try:
            current_user = self.auth_service.get_current_user()
            if not current_user:
                return [], 0

            # Check if user is admin
            if current_user.get('role') != 'admin':
                return [], 0

            # Build query with optional status filter
            where_clause = ""
            params = []
            if status_filter:
                where_clause = "WHERE ra.approval_status = ?"
                params.append(status_filter)

            # Get total count
            count_query = f"""
                SELECT COUNT(*)
                FROM report_approvals ra
                {where_clause}
            """
            count_result = self.db_manager.execute_with_retry(count_query, tuple(params))
            total_count = count_result[0][0] if count_result else 0

            # Get approvals with details
            query = f"""
                SELECT
                    ra.approval_id,
                    ra.report_id,
                    r.report_number,
                    r.reported_entity_name,
                    ra.approval_status,
                    ra.requested_by,
                    ra.requested_at,
                    ra.reviewed_at,
                    ra.approval_comment,
                    u.username as approver_name,
                    u.full_name as approver_full_name,
                    r.status as report_status
                FROM report_approvals ra
                JOIN reports r ON ra.report_id = r.report_id
                LEFT JOIN users u ON ra.approver_id = u.user_id
                {where_clause}
                ORDER BY ra.requested_at DESC
                LIMIT ? OFFSET ?
            """
            params.extend([limit, offset])
            result = self.db_manager.execute_with_retry(query, tuple(params))

            approvals = []
            for row in result:
                approvals.append({
                    'approval_id': row[0],
                    'report_id': row[1],
                    'report_number': row[2],
                    'reported_entity_name': row[3],
                    'approval_status': row[4],
                    'requested_by': row[5],
                    'requested_at': row[6],
                    'reviewed_at': row[7],
                    'comment': row[8],
                    'approver_name': row[9],
                    'approver_full_name': row[10],
                    'report_status': row[11]
                })

            return approvals, total_count

        except Exception as e:
            self.logger.error(f"Error fetching all approvals: {str(e)}", exc_info=True)
            return [], 0

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
            query = "SELECT user_id, username, full_name FROM users WHERE role = 'admin' AND is_active = 1"
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
