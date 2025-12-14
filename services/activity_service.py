"""
Activity Service - GitHub-style Activity Logging
Tracks and displays user activities like creates, updates, deletes, approvals, etc.
"""

import json
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple, Any


class ActivityService:
    """Service for managing GitHub-style activity logs."""

    # Action type icons for UI display
    ACTION_ICONS = {
        'CREATE': 'add_circle',
        'UPDATE': 'edit',
        'DELETE': 'delete',
        'SOFT_DELETE': 'delete_outline',
        'HARD_DELETE': 'delete_forever',
        'RESTORE': 'restore',
        'UNDELETE': 'restore_from_trash',
        'APPROVE': 'check_circle',
        'REJECT': 'cancel',
        'VERSION_CREATE': 'history',
        'VERSION_DELETE': 'history_toggle_off',
        'VERSION_RESTORE': 'settings_backup_restore',
    }

    # Action type colors for UI display
    ACTION_COLORS = {
        'CREATE': '#00d084',      # Green
        'UPDATE': '#ffa726',      # Orange
        'DELETE': '#f44336',      # Red
        'SOFT_DELETE': '#ff7043', # Light red
        'HARD_DELETE': '#d32f2f', # Dark red
        'RESTORE': '#4caf50',     # Green
        'UNDELETE': '#66bb6a',    # Light green
        'APPROVE': '#00d084',     # Green
        'REJECT': '#f44336',      # Red
        'VERSION_CREATE': '#2196f3',  # Blue
        'VERSION_DELETE': '#ff5722',  # Deep orange
        'VERSION_RESTORE': '#9c27b0', # Purple
    }

    def __init__(self, db_manager, logging_service, auth_service):
        """
        Initialize the activity service.

        Args:
            db_manager: DatabaseManager instance
            logging_service: LoggingService instance
            auth_service: AuthService instance
        """
        self.db_manager = db_manager
        self.logger = logging_service
        self.auth_service = auth_service

    def log_activity(
        self,
        action_type: str,
        description: str,
        report_id: int = None,
        report_number: str = None,
        version_id: int = None,
        version_number: int = None,
        metadata: Dict = None
    ) -> Tuple[bool, Optional[int], str]:
        """
        Log a user activity.

        Args:
            action_type: Type of action (CREATE, UPDATE, DELETE, etc.)
            description: Human-readable description of the activity
            report_id: Related report ID (optional)
            report_number: Related report number (optional)
            version_id: Related version ID (optional)
            version_number: Related version number (optional)
            metadata: Additional metadata as JSON (optional)

        Returns:
            Tuple of (success, activity_id, message)
        """
        try:
            current_user = self.auth_service.get_current_user()
            if not current_user:
                return False, None, "User not authenticated"

            user_id = current_user.get('user_id')
            username = current_user.get('username')

            # Validate action type
            valid_actions = [
                'CREATE', 'UPDATE', 'DELETE', 'RESTORE', 'APPROVE',
                'REJECT', 'VERSION_CREATE', 'VERSION_DELETE', 'VERSION_RESTORE',
                'HARD_DELETE', 'SOFT_DELETE', 'UNDELETE'
            ]
            if action_type not in valid_actions:
                return False, None, f"Invalid action type: {action_type}"

            # Serialize metadata
            metadata_json = json.dumps(metadata, default=str) if metadata else None

            # Insert activity
            insert_query = """
                INSERT INTO activity_log
                (user_id, username, action_type, report_id, report_number,
                 version_id, version_number, description, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            self.db_manager.execute_with_retry(
                insert_query,
                (user_id, username, action_type, report_id, report_number,
                 version_id, version_number, description, metadata_json)
            )

            # Get the activity_id
            result = self.db_manager.execute_with_retry("SELECT last_insert_rowid()")
            activity_id = result[0][0] if result else None

            return True, activity_id, "Activity logged successfully"

        except Exception as e:
            self.logger.error(f"Error logging activity: {str(e)}", exc_info=True)
            return False, None, f"Error logging activity: {str(e)}"

    def get_recent_activities(
        self,
        limit: int = 50,
        offset: int = 0,
        user_id: int = None,
        action_types: List[str] = None,
        report_id: int = None,
        date_from: str = None,
        date_to: str = None
    ) -> Tuple[List[Dict], int]:
        """
        Get recent activities with optional filtering.

        Args:
            limit: Maximum number of activities to return
            offset: Number of activities to skip
            user_id: Filter by user ID
            action_types: Filter by action types
            report_id: Filter by report ID
            date_from: Filter activities from this date
            date_to: Filter activities to this date

        Returns:
            Tuple of (list of activities, total count)
        """
        try:
            conditions = []
            params = []

            if user_id:
                conditions.append("user_id = ?")
                params.append(user_id)

            if action_types:
                placeholders = ', '.join(['?' for _ in action_types])
                conditions.append(f"action_type IN ({placeholders})")
                params.extend(action_types)

            if report_id:
                conditions.append("report_id = ?")
                params.append(report_id)

            if date_from:
                conditions.append("created_at >= ?")
                params.append(date_from)

            if date_to:
                conditions.append("created_at <= ?")
                params.append(date_to)

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            # Get total count
            count_query = f"SELECT COUNT(*) FROM activity_log WHERE {where_clause}"
            count_result = self.db_manager.execute_with_retry(count_query, params)
            total_count = count_result[0][0] if count_result else 0

            # Get activities
            query = f"""
                SELECT activity_id, user_id, username, action_type,
                       report_id, report_number, version_id, version_number,
                       description, metadata, created_at
                FROM activity_log
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """
            params.extend([limit, offset])
            result = self.db_manager.execute_with_retry(query, params)

            activities = []
            for row in result:
                metadata = json.loads(row[9]) if row[9] else None
                activities.append({
                    'activity_id': row[0],
                    'user_id': row[1],
                    'username': row[2],
                    'action_type': row[3],
                    'report_id': row[4],
                    'report_number': row[5],
                    'version_id': row[6],
                    'version_number': row[7],
                    'description': row[8],
                    'metadata': metadata,
                    'created_at': row[10],
                    'icon': self.ACTION_ICONS.get(row[3], 'info'),
                    'color': self.ACTION_COLORS.get(row[3], '#757575'),
                    'relative_time': self._get_relative_time(row[10])
                })

            return activities, total_count

        except Exception as e:
            self.logger.error(f"Error fetching activities: {str(e)}", exc_info=True)
            return [], 0

    def get_report_activities(self, report_id: int, limit: int = 50) -> List[Dict]:
        """
        Get activities for a specific report.

        Args:
            report_id: Report ID
            limit: Maximum number of activities

        Returns:
            List of activity dictionaries
        """
        activities, _ = self.get_recent_activities(
            limit=limit,
            report_id=report_id
        )
        return activities

    def get_user_activities(self, user_id: int, limit: int = 50) -> List[Dict]:
        """
        Get activities by a specific user.

        Args:
            user_id: User ID
            limit: Maximum number of activities

        Returns:
            List of activity dictionaries
        """
        activities, _ = self.get_recent_activities(
            limit=limit,
            user_id=user_id
        )
        return activities

    def get_activity_summary(self, days: int = 7) -> Dict[str, Any]:
        """
        Get activity summary statistics for the dashboard.

        Args:
            days: Number of days to include in summary

        Returns:
            Dictionary with summary statistics
        """
        try:
            date_from = (datetime.now() - timedelta(days=days)).isoformat()

            # Get counts by action type
            query = """
                SELECT action_type, COUNT(*) as count
                FROM activity_log
                WHERE created_at >= ?
                GROUP BY action_type
                ORDER BY count DESC
            """
            result = self.db_manager.execute_with_retry(query, (date_from,))

            action_counts = {}
            total_activities = 0
            for row in result:
                action_counts[row[0]] = row[1]
                total_activities += row[1]

            # Get most active users
            user_query = """
                SELECT username, COUNT(*) as count
                FROM activity_log
                WHERE created_at >= ?
                GROUP BY username
                ORDER BY count DESC
                LIMIT 5
            """
            user_result = self.db_manager.execute_with_retry(user_query, (date_from,))
            top_users = [{'username': row[0], 'count': row[1]} for row in user_result]

            # Get daily activity counts
            daily_query = """
                SELECT DATE(created_at) as date, COUNT(*) as count
                FROM activity_log
                WHERE created_at >= ?
                GROUP BY DATE(created_at)
                ORDER BY date DESC
            """
            daily_result = self.db_manager.execute_with_retry(daily_query, (date_from,))
            daily_counts = [{'date': row[0], 'count': row[1]} for row in daily_result]

            return {
                'total_activities': total_activities,
                'action_counts': action_counts,
                'top_users': top_users,
                'daily_counts': daily_counts,
                'period_days': days
            }

        except Exception as e:
            self.logger.error(f"Error fetching activity summary: {str(e)}", exc_info=True)
            return {
                'total_activities': 0,
                'action_counts': {},
                'top_users': [],
                'daily_counts': [],
                'period_days': days
            }

    def format_activity_description(
        self,
        action_type: str,
        username: str,
        report_number: str = None,
        entity_name: str = None,
        field_name: str = None,
        old_value: str = None,
        new_value: str = None,
        version_number: int = None
    ) -> str:
        """
        Format a GitHub-style activity description.

        Args:
            action_type: Type of action
            username: User who performed the action
            report_number: Related report number
            entity_name: Entity name for context
            field_name: Field that was changed
            old_value: Previous value (for updates)
            new_value: New value (for updates)
            version_number: Version number if applicable

        Returns:
            Formatted description string
        """
        report_ref = f"Report #{report_number}" if report_number else "a report"

        if action_type == 'CREATE':
            desc = f"{username} created {report_ref}"
            if entity_name:
                desc += f" for {entity_name}"

        elif action_type == 'UPDATE':
            if field_name:
                desc = f"{username} updated {field_name} in {report_ref}"
                if old_value and new_value:
                    desc += f': "{old_value}" → "{new_value}"'
            else:
                desc = f"{username} updated {report_ref}"

        elif action_type == 'SOFT_DELETE':
            desc = f"{username} deleted {report_ref} (can be restored)"

        elif action_type == 'HARD_DELETE':
            desc = f"{username} permanently deleted {report_ref}"

        elif action_type == 'RESTORE' or action_type == 'UNDELETE':
            desc = f"{username} restored {report_ref}"

        elif action_type == 'APPROVE':
            desc = f"{username} approved {report_ref}"

        elif action_type == 'REJECT':
            desc = f"{username} rejected {report_ref}"

        elif action_type == 'VERSION_CREATE':
            desc = f"{username} created version {version_number or '?'} of {report_ref}"

        elif action_type == 'VERSION_DELETE':
            desc = f"{username} deleted version {version_number or '?'} of {report_ref}"

        elif action_type == 'VERSION_RESTORE':
            desc = f"{username} restored version {version_number or '?'} of {report_ref}"

        else:
            desc = f"{username} performed {action_type} on {report_ref}"

        return desc

    def _get_relative_time(self, timestamp_str: str) -> str:
        """
        Convert a timestamp to relative time string.

        Args:
            timestamp_str: ISO format timestamp string (stored as UTC in database)

        Returns:
            Relative time string (e.g., "2 hours ago")
        """
        try:
            if not timestamp_str:
                return "Unknown"

            # Parse timestamp - SQLite stores UTC time via datetime('now')
            clean_timestamp = timestamp_str.replace('Z', '').split('+')[0]
            timestamp_utc = datetime.fromisoformat(clean_timestamp)

            # Use UTC now for comparison since database stores UTC
            now_utc = datetime.utcnow()

            # Calculate difference
            diff = now_utc - timestamp_utc

            seconds = diff.total_seconds()
            minutes = seconds / 60
            hours = minutes / 60
            days = hours / 24
            weeks = days / 7
            months = days / 30
            years = days / 365

            if seconds < 60:
                return "Just now"
            elif minutes < 60:
                mins = int(minutes)
                return f"{mins} minute{'s' if mins != 1 else ''} ago"
            elif hours < 24:
                hrs = int(hours)
                return f"{hrs} hour{'s' if hrs != 1 else ''} ago"
            elif days < 7:
                d = int(days)
                return f"{d} day{'s' if d != 1 else ''} ago"
            elif weeks < 4:
                w = int(weeks)
                return f"{w} week{'s' if w != 1 else ''} ago"
            elif months < 12:
                m = int(months)
                return f"{m} month{'s' if m != 1 else ''} ago"
            else:
                y = int(years)
                return f"{y} year{'s' if y != 1 else ''} ago"

        except Exception:
            return "Unknown"

    def delete_old_activities(self, days_to_keep: int = 365) -> Tuple[bool, int, str]:
        """
        Delete activities older than specified days.

        Args:
            days_to_keep: Number of days of activities to keep

        Returns:
            Tuple of (success, deleted_count, message)
        """
        try:
            current_user = self.auth_service.get_current_user()
            if not current_user:
                return False, 0, "User not authenticated"

            if current_user.get('role') != 'admin':
                return False, 0, "Only administrators can delete activity logs"

            cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).isoformat()

            # Get count first
            count_query = "SELECT COUNT(*) FROM activity_log WHERE created_at < ?"
            count_result = self.db_manager.execute_with_retry(count_query, (cutoff_date,))
            delete_count = count_result[0][0] if count_result else 0

            if delete_count == 0:
                return True, 0, "No old activities to delete"

            # Delete old activities
            delete_query = "DELETE FROM activity_log WHERE created_at < ?"
            self.db_manager.execute_with_retry(delete_query, (cutoff_date,))

            self.logger.log_user_action(
                "ACTIVITY_CLEANUP",
                {'deleted_count': delete_count, 'cutoff_date': cutoff_date}
            )

            return True, delete_count, f"Deleted {delete_count} activities older than {days_to_keep} days"

        except Exception as e:
            self.logger.error(f"Error deleting old activities: {str(e)}", exc_info=True)
            return False, 0, f"Error deleting old activities: {str(e)}"
