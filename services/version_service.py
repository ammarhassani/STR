"""
Version Management Service
Handles report version snapshots, restoration, and comparison.
"""

import json
from datetime import datetime
from typing import Optional, Dict, List, Tuple


class VersionService:
    """Service for managing report version history."""

    def __init__(self, db_manager, logging_service, auth_service, report_service):
        """
        Initialize the version service.

        Args:
            db_manager: DatabaseManager instance
            logging_service: LoggingService instance
            auth_service: AuthService instance
            report_service: ReportService instance (for getting report data)
        """
        self.db_manager = db_manager
        self.logger = logging_service
        self.auth_service = auth_service
        self.report_service = report_service

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
            report = self.report_service.get_report(report_id)
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
            if current_user.get('role') != 'admin':
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
