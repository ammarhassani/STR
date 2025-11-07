"""
Dashboard and statistics service.
Provides aggregated data for dashboard widgets and analytics.
"""

from typing import Dict, List, Any, Optional


class DashboardService:
    """Service for dashboard statistics and analytics."""

    def __init__(self, db_manager, logging_service):
        """
        Initialize the dashboard service.

        Args:
            db_manager: DatabaseManager instance
            logging_service: LoggingService instance
        """
        self.db_manager = db_manager
        self.logger = logging_service

    def get_summary_statistics(self) -> Dict[str, Any]:
        """
        Get summary statistics for the dashboard.

        Returns:
            Dictionary with summary statistics
        """
        try:
            stats = {}

            # Total reports
            result = self.db_manager.execute_with_retry(
                "SELECT COUNT(*) FROM reports WHERE is_deleted = 0"
            )
            stats['total_reports'] = result[0][0] if result else 0

            # Open reports
            result = self.db_manager.execute_with_retry(
                "SELECT COUNT(*) FROM reports WHERE status = 'Open' AND is_deleted = 0"
            )
            stats['open_reports'] = result[0][0] if result else 0

            # Under investigation
            result = self.db_manager.execute_with_retry(
                "SELECT COUNT(*) FROM reports WHERE status = 'Under Investigation' AND is_deleted = 0"
            )
            stats['under_investigation'] = result[0][0] if result else 0

            # Closed cases
            result = self.db_manager.execute_with_retry(
                """SELECT COUNT(*) FROM reports
                   WHERE status IN ('Close Case', 'Closed with STR') AND is_deleted = 0"""
            )
            stats['closed_cases'] = result[0][0] if result else 0

            # Active users
            result = self.db_manager.execute_with_retry(
                "SELECT COUNT(*) FROM users WHERE is_active = 1"
            )
            stats['active_users'] = result[0][0] if result else 0

            # Reports this month
            result = self.db_manager.execute_with_retry(
                """SELECT COUNT(*) FROM reports
                   WHERE strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now')
                   AND is_deleted = 0"""
            )
            stats['reports_this_month'] = result[0][0] if result else 0

            return stats

        except Exception as e:
            self.logger.error(f"Error fetching summary statistics: {str(e)}", exc_info=True)
            return {}

    def get_reports_by_status(self) -> List[Dict[str, Any]]:
        """
        Get report counts grouped by status.

        Returns:
            List of dictionaries with status and count
        """
        try:
            query = """
                SELECT status, COUNT(*) as count
                FROM reports
                WHERE is_deleted = 0
                GROUP BY status
                ORDER BY count DESC
            """
            result = self.db_manager.execute_with_retry(query)

            data = []
            for row in result:
                data.append({
                    'status': row[0],
                    'count': row[1]
                })

            return data

        except Exception as e:
            self.logger.error(f"Error fetching reports by status: {str(e)}", exc_info=True)
            return []

    def get_reports_by_month(self, months: int = 12) -> List[Dict[str, Any]]:
        """
        Get report counts by month.

        Args:
            months: Number of months to include

        Returns:
            List of dictionaries with month and count
        """
        try:
            query = f"""
                SELECT strftime('%Y-%m', created_at) as month, COUNT(*) as count
                FROM reports
                WHERE is_deleted = 0
                  AND created_at >= date('now', '-{months} months')
                GROUP BY month
                ORDER BY month
            """
            result = self.db_manager.execute_with_retry(query)

            data = []
            for row in result:
                data.append({
                    'month': row[0],
                    'count': row[1]
                })

            return data

        except Exception as e:
            self.logger.error(f"Error fetching reports by month: {str(e)}", exc_info=True)
            return []

    def get_top_reporters(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get top reporters by number of reports created.

        Args:
            limit: Maximum number of reporters to return

        Returns:
            List of dictionaries with reporter and count
        """
        try:
            query = f"""
                SELECT created_by, COUNT(*) as count
                FROM reports
                WHERE is_deleted = 0
                GROUP BY created_by
                ORDER BY count DESC
                LIMIT {limit}
            """
            result = self.db_manager.execute_with_retry(query)

            data = []
            for row in result:
                data.append({
                    'username': row[0],
                    'count': row[1]
                })

            return data

        except Exception as e:
            self.logger.error(f"Error fetching top reporters: {str(e)}", exc_info=True)
            return []

    def get_recent_activity(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent activity (report changes).

        Args:
            limit: Maximum number of activities to return

        Returns:
            List of activity dictionaries
        """
        try:
            query = f"""
                SELECT ch.change_type, ch.changed_by, ch.changed_at,
                       r.report_number, ch.field_name, ch.new_value
                FROM change_history ch
                JOIN reports r ON ch.record_id = r.report_id
                WHERE ch.table_name = 'reports'
                ORDER BY ch.changed_at DESC
                LIMIT {limit}
            """
            result = self.db_manager.execute_with_retry(query)

            activities = []
            for row in result:
                activities.append({
                    'change_type': row[0],
                    'changed_by': row[1],
                    'changed_at': row[2],
                    'report_number': row[3],
                    'field_name': row[4],
                    'new_value': row[5]
                })

            return activities

        except Exception as e:
            self.logger.error(f"Error fetching recent activity: {str(e)}", exc_info=True)
            return []

    def get_user_statistics(self, username: str) -> Dict[str, Any]:
        """
        Get statistics for a specific user.

        Args:
            username: Username to get statistics for

        Returns:
            Dictionary with user statistics
        """
        try:
            stats = {}

            # Reports created
            result = self.db_manager.execute_with_retry(
                "SELECT COUNT(*) FROM reports WHERE created_by = ? AND is_deleted = 0",
                (username,)
            )
            stats['reports_created'] = result[0][0] if result else 0

            # Reports updated
            result = self.db_manager.execute_with_retry(
                """SELECT COUNT(DISTINCT record_id) FROM change_history
                   WHERE table_name = 'reports' AND changed_by = ?""",
                (username,)
            )
            stats['reports_updated'] = result[0][0] if result else 0

            # Last login
            result = self.db_manager.execute_with_retry(
                "SELECT last_login FROM users WHERE username = ?",
                (username,)
            )
            stats['last_login'] = result[0][0] if result and result[0][0] else 'Never'

            # Session count
            result = self.db_manager.execute_with_retry(
                "SELECT COUNT(*) FROM session_log WHERE username = ?",
                (username,)
            )
            stats['session_count'] = result[0][0] if result else 0

            return stats

        except Exception as e:
            self.logger.error(f"Error fetching user statistics: {str(e)}", exc_info=True)
            return {}

    def get_dashboard_widgets(self, role: str) -> List[Dict[str, Any]]:
        """
        Get dashboard widgets configured for a specific role.

        Args:
            role: User role (admin, agent, reporter)

        Returns:
            List of widget configurations
        """
        try:
            query = """
                SELECT widget_id, widget_type, title, title_ar, sql_query,
                       position_row, position_col, width, height, color, icon
                FROM dashboard_config
                WHERE is_active = 1
                  AND (visible_to_roles LIKE '%' || ? || '%')
                ORDER BY display_order
            """
            result = self.db_manager.execute_with_retry(query, (role,))

            widgets = []
            for row in result:
                widget = {
                    'widget_id': row[0],
                    'widget_type': row[1],
                    'title': row[2],
                    'title_ar': row[3],
                    'sql_query': row[4],
                    'position_row': row[5],
                    'position_col': row[6],
                    'width': row[7],
                    'height': row[8],
                    'color': row[9],
                    'icon': row[10]
                }

                # Execute widget query to get data
                try:
                    widget_data = self.db_manager.execute_with_retry(row[4])
                    widget['data'] = widget_data
                except Exception as e:
                    self.logger.warning(f"Error executing widget query: {str(e)}")
                    widget['data'] = []

                widgets.append(widget)

            return widgets

        except Exception as e:
            self.logger.error(f"Error fetching dashboard widgets: {str(e)}", exc_info=True)
            return []
