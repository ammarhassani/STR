"""
Version Management Service
Handles report version snapshots, restoration, and comparison.
"""

import json
from datetime import datetime
from typing import Optional, Dict, List, Tuple, Any


# System fields to exclude from diff comparison
SYSTEM_FIELDS = {
    'report_id', 'created_at', 'created_by', 'updated_at', 'updated_by',
    'is_deleted', 'current_version', 'deleted_at', 'deleted_by'
}


class VersionService:
    """Service for managing report version history."""

    def __init__(self, db_manager, logging_service, auth_service, report_service, activity_service=None):
        """
        Initialize the version service.

        Args:
            db_manager: DatabaseManager instance
            logging_service: LoggingService instance
            auth_service: AuthService instance
            report_service: ReportService instance (for getting report data)
            activity_service: ActivityService instance (for logging activities)
        """
        self.db_manager = db_manager
        self.logger = logging_service
        self.auth_service = auth_service
        self.report_service = report_service
        self.activity_service = activity_service

    def set_activity_service(self, activity_service):
        """Set activity service (for late binding to avoid circular imports)."""
        self.activity_service = activity_service

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

            # Log to activity service for GitHub-style activity feed
            if self.activity_service:
                report_number = report.get('report_number', str(report_id))
                self.activity_service.log_activity(
                    action_type='VERSION_CREATE',
                    description=f"{current_user['username']} created version {new_version_number} of Report #{report_number}",
                    report_id=report_id,
                    report_number=report_number,
                    version_id=version_id,
                    version_number=new_version_number,
                    metadata={
                        'change_summary': change_summary,
                        'entity_name': report.get('reported_entity_name', '')
                    }
                )

            return True, version_id, f"Version {new_version_number} created successfully"

        except Exception as e:
            self.logger.error(f"Error creating version snapshot: {str(e)}", exc_info=True)
            return False, None, f"Error creating version snapshot: {str(e)}"

    def get_report_versions(self, report_id: int, include_deleted: bool = False) -> List[Dict]:
        """
        Get all version history for a report.

        Args:
            report_id: Report ID
            include_deleted: Whether to include soft-deleted versions

        Returns:
            List of version dictionaries
        """
        try:
            if include_deleted:
                query = """
                    SELECT version_id, version_number, change_summary, created_by, created_at,
                           COALESCE(is_deleted, 0) as is_deleted, deleted_at, deleted_by
                    FROM report_versions
                    WHERE report_id = ?
                    ORDER BY version_number DESC
                """
            else:
                query = """
                    SELECT version_id, version_number, change_summary, created_by, created_at,
                           0 as is_deleted, NULL as deleted_at, NULL as deleted_by
                    FROM report_versions
                    WHERE report_id = ? AND COALESCE(is_deleted, 0) = 0
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
                    'created_at': row[4],
                    'is_deleted': bool(row[5]),
                    'deleted_at': row[6],
                    'deleted_by': row[7]
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

    def compare_versions_detailed(
        self,
        version_id_1: int,
        version_id_2: int,
        skip_system_fields: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Enhanced version comparison for diff view with detailed change information.

        Args:
            version_id_1: First version ID (typically older)
            version_id_2: Second version ID (typically newer)
            skip_system_fields: Whether to skip system fields in comparison

        Returns:
            Dictionary with detailed comparison info:
            {
                'version_1': {'version_id': ..., 'version_number': ..., 'created_by': ..., 'created_at': ...},
                'version_2': {...},
                'differences': {
                    'field_name': {
                        'old_value': ...,
                        'new_value': ...,
                        'change_type': 'added' | 'removed' | 'modified'
                    }
                },
                'unchanged_fields': [...]
            }
        """
        try:
            # Get version metadata
            meta_query = """
                SELECT version_id, version_number, created_by, created_at, report_id
                FROM report_versions
                WHERE version_id IN (?, ?)
            """
            meta_result = self.db_manager.execute_with_retry(meta_query, (version_id_1, version_id_2))

            if len(meta_result) != 2:
                return None

            version_meta = {}
            for row in meta_result:
                version_meta[row[0]] = {
                    'version_id': row[0],
                    'version_number': row[1],
                    'created_by': row[2],
                    'created_at': row[3],
                    'report_id': row[4]
                }

            # Get snapshots
            snapshot1 = self.get_version_snapshot(version_id_1)
            snapshot2 = self.get_version_snapshot(version_id_2)

            if not snapshot1 or not snapshot2:
                return None

            # Filter out system fields if requested
            fields_to_skip = SYSTEM_FIELDS if skip_system_fields else set()

            differences = {}
            unchanged_fields = []
            all_keys = set(snapshot1.keys()) | set(snapshot2.keys())

            for key in all_keys:
                if key in fields_to_skip:
                    continue

                val1 = snapshot1.get(key)
                val2 = snapshot2.get(key)

                # Normalize values for comparison
                val1_str = str(val1) if val1 is not None else ""
                val2_str = str(val2) if val2 is not None else ""

                if val1 != val2:
                    # Determine change type
                    if val1 is None or val1_str == "":
                        change_type = 'added'
                    elif val2 is None or val2_str == "":
                        change_type = 'removed'
                    else:
                        change_type = 'modified'

                    differences[key] = {
                        'old_value': val1,
                        'new_value': val2,
                        'change_type': change_type
                    }
                else:
                    if val1 is not None and val1_str != "":
                        unchanged_fields.append(key)

            return {
                'version_1': version_meta.get(version_id_1),
                'version_2': version_meta.get(version_id_2),
                'differences': differences,
                'unchanged_fields': sorted(unchanged_fields),
                'total_changes': len(differences)
            }

        except Exception as e:
            self.logger.error(f"Error in detailed version comparison: {str(e)}", exc_info=True)
            return None

    def soft_delete_version(self, version_id: int, reason: str = "") -> Tuple[bool, str]:
        """
        Soft delete a version (admin only). Sets is_deleted=1.

        Args:
            version_id: Version ID to delete
            reason: Reason for deletion

        Returns:
            Tuple of (success, message)
        """
        try:
            current_user = self.auth_service.get_current_user()
            if not current_user:
                return False, "User not authenticated"

            # Check if user is admin
            if current_user.get('role') != 'admin':
                return False, "Only administrators can delete versions"

            # Get version info for logging
            query = """
                SELECT v.version_id, v.version_number, v.report_id, r.report_number
                FROM report_versions v
                LEFT JOIN reports r ON v.report_id = r.report_id
                WHERE v.version_id = ?
            """
            result = self.db_manager.execute_with_retry(query, (version_id,))
            if not result:
                return False, "Version not found"

            version_number = result[0][1]
            report_id = result[0][2]
            report_number = result[0][3]

            # Check if it's already deleted
            check_query = "SELECT COALESCE(is_deleted, 0) FROM report_versions WHERE version_id = ?"
            check_result = self.db_manager.execute_with_retry(check_query, (version_id,))
            if check_result and check_result[0][0] == 1:
                return False, "Version is already deleted"

            # Soft delete the version
            update_query = """
                UPDATE report_versions
                SET is_deleted = 1, deleted_at = ?, deleted_by = ?
                WHERE version_id = ?
            """
            self.db_manager.execute_with_retry(
                update_query,
                (datetime.now().isoformat(), current_user['username'], version_id)
            )

            # Log the action
            self.logger.log_user_action(
                "VERSION_SOFT_DELETED",
                {
                    'version_id': version_id,
                    'version_number': version_number,
                    'report_id': report_id,
                    'reason': reason
                }
            )

            # Log to activity service if available
            if self.activity_service:
                self.activity_service.log_activity(
                    action_type='VERSION_DELETE',
                    description=f"{current_user['username']} deleted version {version_number} of Report #{report_number}",
                    report_id=report_id,
                    report_number=report_number,
                    version_id=version_id,
                    version_number=version_number,
                    metadata={'reason': reason, 'delete_type': 'soft'}
                )

            return True, f"Version {version_number} soft deleted successfully"

        except Exception as e:
            self.logger.error(f"Error soft deleting version: {str(e)}", exc_info=True)
            return False, f"Error deleting version: {str(e)}"

    def hard_delete_version(self, version_id: int, reason: str = "") -> Tuple[bool, str]:
        """
        Permanently delete a version (admin only). Removes from DB.

        Args:
            version_id: Version ID to delete
            reason: Reason for deletion

        Returns:
            Tuple of (success, message)
        """
        try:
            current_user = self.auth_service.get_current_user()
            if not current_user:
                return False, "User not authenticated"

            # Check if user is admin
            if current_user.get('role') != 'admin':
                return False, "Only administrators can permanently delete versions"

            # Get version info for logging
            query = """
                SELECT v.version_id, v.version_number, v.report_id, r.report_number
                FROM report_versions v
                LEFT JOIN reports r ON v.report_id = r.report_id
                WHERE v.version_id = ?
            """
            result = self.db_manager.execute_with_retry(query, (version_id,))
            if not result:
                return False, "Version not found"

            version_number = result[0][1]
            report_id = result[0][2]
            report_number = result[0][3]

            # Check if this is the only version (don't allow deleting the last version)
            count_query = """
                SELECT COUNT(*) FROM report_versions
                WHERE report_id = ? AND COALESCE(is_deleted, 0) = 0
            """
            count_result = self.db_manager.execute_with_retry(count_query, (report_id,))
            if count_result and count_result[0][0] <= 1:
                return False, "Cannot delete the only remaining version of a report"

            # Permanently delete the version
            delete_query = "DELETE FROM report_versions WHERE version_id = ?"
            self.db_manager.execute_with_retry(delete_query, (version_id,))

            # Log the action
            self.logger.log_user_action(
                "VERSION_HARD_DELETED",
                {
                    'version_id': version_id,
                    'version_number': version_number,
                    'report_id': report_id,
                    'reason': reason
                }
            )

            # Log to activity service if available
            if self.activity_service:
                self.activity_service.log_activity(
                    action_type='VERSION_DELETE',
                    description=f"{current_user['username']} permanently deleted version {version_number} of Report #{report_number}",
                    report_id=report_id,
                    report_number=report_number,
                    version_id=version_id,
                    version_number=version_number,
                    metadata={'reason': reason, 'delete_type': 'hard'}
                )

            return True, f"Version {version_number} permanently deleted"

        except Exception as e:
            self.logger.error(f"Error hard deleting version: {str(e)}", exc_info=True)
            return False, f"Error deleting version: {str(e)}"

    def restore_deleted_version(self, version_id: int) -> Tuple[bool, str]:
        """
        Restore a soft-deleted version (admin only).

        Args:
            version_id: Version ID to restore

        Returns:
            Tuple of (success, message)
        """
        try:
            current_user = self.auth_service.get_current_user()
            if not current_user:
                return False, "User not authenticated"

            # Check if user is admin
            if current_user.get('role') != 'admin':
                return False, "Only administrators can restore deleted versions"

            # Get version info
            query = """
                SELECT v.version_id, v.version_number, v.report_id, r.report_number,
                       COALESCE(v.is_deleted, 0) as is_deleted
                FROM report_versions v
                LEFT JOIN reports r ON v.report_id = r.report_id
                WHERE v.version_id = ?
            """
            result = self.db_manager.execute_with_retry(query, (version_id,))
            if not result:
                return False, "Version not found"

            version_number = result[0][1]
            report_id = result[0][2]
            report_number = result[0][3]
            is_deleted = result[0][4]

            if not is_deleted:
                return False, "Version is not deleted"

            # Restore the version
            update_query = """
                UPDATE report_versions
                SET is_deleted = 0, deleted_at = NULL, deleted_by = NULL
                WHERE version_id = ?
            """
            self.db_manager.execute_with_retry(update_query, (version_id,))

            # Log the action
            self.logger.log_user_action(
                "VERSION_RESTORED",
                {
                    'version_id': version_id,
                    'version_number': version_number,
                    'report_id': report_id
                }
            )

            # Log to activity service if available
            if self.activity_service:
                self.activity_service.log_activity(
                    action_type='VERSION_RESTORE',
                    description=f"{current_user['username']} restored version {version_number} of Report #{report_number}",
                    report_id=report_id,
                    report_number=report_number,
                    version_id=version_id,
                    version_number=version_number
                )

            return True, f"Version {version_number} restored successfully"

        except Exception as e:
            self.logger.error(f"Error restoring version: {str(e)}", exc_info=True)
            return False, f"Error restoring version: {str(e)}"

    def get_version_count(self, report_id: int, include_deleted: bool = False) -> int:
        """
        Get the count of versions for a report.

        Args:
            report_id: Report ID
            include_deleted: Whether to include soft-deleted versions

        Returns:
            Number of versions
        """
        try:
            if include_deleted:
                query = "SELECT COUNT(*) FROM report_versions WHERE report_id = ?"
            else:
                query = "SELECT COUNT(*) FROM report_versions WHERE report_id = ? AND COALESCE(is_deleted, 0) = 0"

            result = self.db_manager.execute_with_retry(query, (report_id,))
            return result[0][0] if result else 0

        except Exception as e:
            self.logger.error(f"Error getting version count: {str(e)}", exc_info=True)
            return 0
