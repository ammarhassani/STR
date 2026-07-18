"""
Dashboard and statistics service.
Provides aggregated data for dashboard widgets and analytics.

Config-driven widgets run admin-authored SQL. Since this is an AML system,
that SQL is treated as hostile input: every widget query is validated to be a
single read-only SELECT and executed on a READ-ONLY connection so the database
engine itself refuses any write, ATTACH, or PRAGMA — a malicious or fat-fingered
widget can never mutate or exfiltrate data.
"""

import re
import sqlite3
from typing import Dict, List, Any, Optional, Tuple


# Tokens that must never appear in a widget query (defense-in-depth on top of
# the read-only connection). Word-boundary matched, case-insensitive.
_FORBIDDEN = (
    "insert", "update", "delete", "drop", "alter", "create", "replace",
    "attach", "detach", "pragma", "vacuum", "reindex", "trigger", "grant",
    "truncate", "load_extension",
)
_FORBIDDEN_RE = re.compile(r"\b(" + "|".join(_FORBIDDEN) + r")\b", re.IGNORECASE)
_COMMENT_RE = re.compile(r"--[^\n]*|/\*.*?\*/", re.DOTALL)


def validate_widget_query(sql: str) -> Tuple[bool, str]:
    """A widget query must be a single, read-only SELECT (or WITH…SELECT).
    Returns (ok, reason)."""
    if not sql or not sql.strip():
        return False, "Query is empty."
    stripped = _COMMENT_RE.sub(" ", sql).strip().rstrip(";").strip()
    if not stripped:
        return False, "Query is empty."
    if ";" in stripped:
        return False, "Only a single statement is allowed."
    head = stripped.lstrip("(").lstrip()[:6].lower()
    if not (head.startswith("select") or head.startswith("with")):
        return False, "Query must start with SELECT."
    m = _FORBIDDEN_RE.search(stripped)
    if m:
        return False, f"Keyword '{m.group(1).upper()}' is not allowed in a widget query."
    return True, ""


class DashboardService:
    """Service for dashboard statistics and analytics."""

    def __init__(self, db_manager, logging_service, auth_service=None):
        """
        Initialize the dashboard service.

        Args:
            db_manager: DatabaseManager instance
            logging_service: LoggingService instance
            auth_service: AuthService (required to manage/configure widgets)
        """
        self.db_manager = db_manager
        self.logger = logging_service
        self.auth_service = auth_service

    def run_widget_query(self, sql: str, limit: int = 500) -> Tuple[bool, List[Any], List[str], str]:
        """Validate + execute a widget query on a READ-ONLY connection.
        Returns (ok, rows, column_names, error). Never mutates the DB."""
        ok, reason = validate_widget_query(sql)
        if not ok:
            return False, [], [], reason
        conn = None
        try:
            conn = sqlite3.connect(f"file:{self.db_manager.db_path}?mode=ro", uri=True, timeout=5)
            conn.execute("PRAGMA query_only = ON")  # belt-and-braces
            cur = conn.execute(sql)
            cols = [d[0] for d in (cur.description or [])]
            rows = cur.fetchmany(limit)
            return True, [list(r) for r in rows], cols, ""
        except sqlite3.Error as e:
            return False, [], [], f"Query error: {e}"
        finally:
            if conn is not None:
                conn.close()

    def get_summary_statistics(self) -> Dict[str, Any]:
        """
        Get summary statistics for the dashboard.

        Returns:
            Dictionary with summary statistics
        """
        try:
            # Optimized: Single query instead of 6 separate queries (N+1 fix)
            query = """
                SELECT
                    COUNT(*) FILTER (WHERE r.is_deleted = 0) as total_reports,
                    COUNT(*) FILTER (WHERE r.approval_status IN ('draft', 'rework') AND r.is_deleted = 0) as open_reports,
                    COUNT(*) FILTER (WHERE r.approval_status = 'pending_approval' AND r.is_deleted = 0) as under_investigation,
                    COUNT(*) FILTER (WHERE r.approval_status = 'approved' AND r.is_deleted = 0) as closed_cases,
                    COUNT(*) FILTER (WHERE strftime('%Y-%m', r.created_at) = strftime('%Y-%m', 'now') AND r.is_deleted = 0) as reports_this_month,
                    (SELECT COUNT(*) FROM users WHERE is_active = 1) as active_users
                FROM reports r
            """

            result = self.db_manager.execute_with_retry(query)

            if result and result[0]:
                row = result[0]
                return {
                    'total_reports': row[0] or 0,
                    'open_reports': row[1] or 0,
                    'under_investigation': row[2] or 0,
                    'closed_cases': row[3] or 0,
                    'reports_this_month': row[4] or 0,
                    'active_users': row[5] or 0
                }

            return {}

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
                SELECT approval_status, COUNT(*) as count
                FROM reports
                WHERE is_deleted = 0
                GROUP BY approval_status
                ORDER BY count DESC
            """
            result = self.db_manager.execute_with_retry(query)

            # Human-readable labels for approval workflow states
            labels = {
                'draft': 'Draft',
                'pending_approval': 'Pending Approval',
                'approved': 'Approved',
                'rejected': 'Rejected',
                'rework': 'Rework',
            }
            data = []
            for row in result:
                data.append({
                    'status': labels.get(row[0], row[0] or 'Unknown'),
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

                # Execute the widget query SAFELY (read-only, validated).
                ok, rows, cols, err = self.run_widget_query(row[4])
                if not ok:
                    widget['data'] = []
                    widget['error'] = err
                    if self.logger:
                        self.logger.warning(f"Widget {row[0]} query rejected/failed: {err}")
                else:
                    widget['data'] = [dict(zip(cols, r)) for r in rows]
                    widget['columns'] = cols
                    widget['error'] = None

                widgets.append(widget)

            return widgets

        except Exception as e:
            self.logger.error(f"Error fetching dashboard widgets: {str(e)}", exc_info=True)
            return []

    # ---------------------------------------------------------------- admin CRUD
    _WIDGET_TYPES = ('kpi_card', 'bar_chart', 'line_chart', 'pie_chart', 'table', 'metric')

    def _require_config(self) -> Tuple[bool, str]:
        if not (self.auth_service and self.auth_service.has_permission('configure_dashboard')):
            return False, "You don't have permission to configure the dashboard."
        return True, ""

    def list_all_widgets(self) -> List[Dict[str, Any]]:
        """All widgets (active or not) for the admin config screen."""
        ok, _ = self._require_config()
        if not ok:
            return []
        try:
            rows = self.db_manager.execute_with_retry(
                "SELECT widget_id, widget_type, title, title_ar, sql_query, color, icon, "
                "visible_to_roles, is_active, display_order FROM dashboard_config "
                "ORDER BY display_order, widget_id")
            keys = ['widget_id', 'widget_type', 'title', 'title_ar', 'sql_query', 'color',
                    'icon', 'visible_to_roles', 'is_active', 'display_order']
            return [dict(zip(keys, r)) for r in (rows or [])]
        except Exception as e:
            self.logger.error(f"Error listing widgets: {e}")
            return []

    def _validate_widget(self, data: Dict[str, Any]) -> Tuple[bool, str]:
        if data.get('widget_type') not in self._WIDGET_TYPES:
            return False, f"Invalid widget type. Choose one of: {', '.join(self._WIDGET_TYPES)}."
        if not (data.get('title') or '').strip():
            return False, "Title is required."
        ok, reason = validate_widget_query(data.get('sql_query', ''))
        if not ok:
            return False, reason
        # the query must actually run (read-only) — reject broken widgets at save
        run_ok, _rows, _cols, err = self.run_widget_query(data['sql_query'])
        if not run_ok:
            return False, err
        return True, ""

    def create_widget(self, data: Dict[str, Any]) -> Tuple[bool, str]:
        ok, msg = self._require_config()
        if not ok:
            return False, msg
        ok, msg = self._validate_widget(data)
        if not ok:
            return False, msg
        try:
            user = self.auth_service.get_current_user() or {}
            self.db_manager.execute_write(
                "INSERT INTO dashboard_config (widget_type, title, title_ar, sql_query, color, "
                "icon, visible_to_roles, is_active, display_order, created_by) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (data['widget_type'], data['title'].strip(), data.get('title_ar'),
                 data['sql_query'], data.get('color') or '#3b82f6', data.get('icon'),
                 data.get('visible_to_roles') or 'admin', int(data.get('is_active', 1)),
                 int(data.get('display_order', 0)), user.get('username', 'admin')))
            return True, "Widget created."
        except Exception as e:
            self.logger.error(f"Error creating widget: {e}")
            return False, f"Failed to create widget: {e}"

    def update_widget(self, widget_id: int, data: Dict[str, Any]) -> Tuple[bool, str]:
        ok, msg = self._require_config()
        if not ok:
            return False, msg
        ok, msg = self._validate_widget(data)
        if not ok:
            return False, msg
        try:
            user = self.auth_service.get_current_user() or {}
            self.db_manager.execute_write(
                "UPDATE dashboard_config SET widget_type=?, title=?, title_ar=?, sql_query=?, "
                "color=?, icon=?, visible_to_roles=?, is_active=?, display_order=?, "
                "updated_by=?, updated_at=datetime('now') WHERE widget_id=?",
                (data['widget_type'], data['title'].strip(), data.get('title_ar'),
                 data['sql_query'], data.get('color') or '#3b82f6', data.get('icon'),
                 data.get('visible_to_roles') or 'admin', int(data.get('is_active', 1)),
                 int(data.get('display_order', 0)), user.get('username', 'admin'), widget_id))
            return True, "Widget updated."
        except Exception as e:
            self.logger.error(f"Error updating widget: {e}")
            return False, f"Failed to update widget: {e}"

    def delete_widget(self, widget_id: int) -> Tuple[bool, str]:
        ok, msg = self._require_config()
        if not ok:
            return False, msg
        try:
            self.db_manager.execute_write(
                "DELETE FROM dashboard_config WHERE widget_id=?", (widget_id,))
            return True, "Widget deleted."
        except Exception as e:
            self.logger.error(f"Error deleting widget: {e}")
            return False, f"Failed to delete widget: {e}"
