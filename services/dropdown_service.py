"""
Dropdown Management Service
Handles CRUD operations for admin-managed dropdown values in system_config table.
"""

from typing import List, Dict, Tuple, Optional
from datetime import datetime


class DropdownService:
    """Service for managing dropdown values that admins can customize."""

    # Admin-manageable dropdown categories (per requirements #7, #8, #11, #18)
    ADMIN_MANAGEABLE_CATEGORIES = [
        'second_reason_for_suspicion',
        'type_of_suspected_transaction',
        'report_classification',
        'fiu_feedback',
        'nationality',
        'report_source',
        'reporting_entity',
        'gender',
        'arb_staff',
    ]

    # Fixed dropdown categories (populated but not editable) - now empty, all are manageable
    FIXED_CATEGORIES = [
    ]

    def __init__(self, db_manager, logging_service):
        """
        Initialize the dropdown service.

        Args:
            db_manager: DatabaseManager instance
            logging_service: LoggingService instance
        """
        self.db_manager = db_manager
        self.logger = logging_service

    def get_dropdown_values(self, category: str) -> List[Dict]:
        """
        Get all dropdown values for a specific category.

        Args:
            category: Category name (e.g., 'nationality', 'report_source')

        Returns:
            List of dictionaries with dropdown values
        """
        try:
            query = """
                SELECT config_id, config_key, config_value, display_order, is_active
                FROM system_config
                WHERE config_type = 'dropdown' AND config_category = ?
                ORDER BY display_order, config_value
            """
            results = self.db_manager.execute_with_retry(query, (category,))

            if not results:
                return []

            dropdowns = []
            for row in results:
                dropdowns.append({
                    'id': row[0],
                    'key': row[1],
                    'value': row[2],
                    'display_order': row[3],
                    'is_active': row[4],
                })

            return dropdowns

        except Exception as e:
            self.logger.error(f"Error getting dropdown values for {category}: {str(e)}")
            return []

    def get_active_dropdown_values(self, category: str) -> List[str]:
        """
        Get only active dropdown values for a specific category (for UI display).

        Args:
            category: Category name

        Returns:
            List of string values
        """
        try:
            query = """
                SELECT config_value
                FROM system_config
                WHERE config_type = 'dropdown'
                  AND config_category = ?
                  AND is_active = 1
                ORDER BY display_order, config_value
            """
            results = self.db_manager.execute_with_retry(query, (category,))

            if not results:
                return []

            return [row[0] for row in results]

        except Exception as e:
            self.logger.error(f"Error getting active dropdown values for {category}: {str(e)}")
            return []

    def get_all_categories(self) -> Dict[str, List[str]]:
        """
        Get all dropdown categories with their value counts.

        Returns:
            Dictionary with category names as keys and value lists
        """
        try:
            query = """
                SELECT DISTINCT config_category,
                       COUNT(*) as value_count,
                       SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active_count
                FROM system_config
                WHERE config_type = 'dropdown'
                GROUP BY config_category
                ORDER BY config_category
            """
            results = self.db_manager.execute_with_retry(query)

            if not results:
                return {}

            categories = {}
            for row in results:
                category, total_count, active_count = row
                categories[category] = {
                    'total': total_count,
                    'active': active_count,
                    'is_admin_manageable': category in self.ADMIN_MANAGEABLE_CATEGORIES,
                    'is_fixed': category in self.FIXED_CATEGORIES,
                }

            return categories

        except Exception as e:
            self.logger.error(f"Error getting all categories: {str(e)}")
            return {}

    def add_dropdown_value(self, category: str, value: str, username: str, display_order: Optional[int] = None) -> Tuple[bool, str]:
        """
        Add a new dropdown value to a category.

        Args:
            category: Category name
            value: Dropdown value to add
            username: User performing the action
            display_order: Optional display order (defaults to max + 1)

        Returns:
            Tuple of (success, message)
        """
        try:
            # Check if value already exists
            query = """
                SELECT COUNT(*)
                FROM system_config
                WHERE config_type = 'dropdown'
                  AND config_category = ?
                  AND config_value = ?
            """
            result = self.db_manager.execute_with_retry(query, (category, value))

            if result and result[0][0] > 0:
                return False, "This value already exists in the dropdown."

            # Get the next display order if not provided
            if display_order is None:
                query = """
                    SELECT COALESCE(MAX(display_order), 0) + 1
                    FROM system_config
                    WHERE config_type = 'dropdown' AND config_category = ?
                """
                result = self.db_manager.execute_with_retry(query, (category,))
                display_order = result[0][0] if result else 1

            # Generate config key
            config_key = f"{category}_{value.lower().replace(' ', '_').replace('-', '_').replace('/', '_')}"

            # Insert new dropdown value
            insert_query = """
                INSERT INTO system_config
                (config_key, config_value, config_type, config_category, display_order, is_active, updated_at, updated_by)
                VALUES (?, ?, 'dropdown', ?, ?, 1, ?, ?)
            """
            self.db_manager.execute_with_retry(
                insert_query,
                (config_key, value, category, display_order, datetime.now().isoformat(), username)
            )

            self.logger.info(f"User {username} added dropdown value '{value}' to category '{category}'")
            return True, "Dropdown value added successfully."

        except Exception as e:
            self.logger.error(f"Error adding dropdown value: {str(e)}")
            return False, f"Error adding dropdown value: {str(e)}"

    def update_dropdown_value(self, config_id: int, new_value: str, username: str, display_order: Optional[int] = None) -> Tuple[bool, str]:
        """
        Update an existing dropdown value.

        Args:
            config_id: ID of the config entry to update
            new_value: New value
            username: User performing the action
            display_order: Optional new display order

        Returns:
            Tuple of (success, message)
        """
        try:
            # Build update query
            if display_order is not None:
                update_query = """
                    UPDATE system_config
                    SET config_value = ?, display_order = ?, updated_at = ?, updated_by = ?
                    WHERE config_id = ? AND config_type = 'dropdown'
                """
                params = (new_value, display_order, datetime.now().isoformat(), username, config_id)
            else:
                update_query = """
                    UPDATE system_config
                    SET config_value = ?, updated_at = ?, updated_by = ?
                    WHERE config_id = ? AND config_type = 'dropdown'
                """
                params = (new_value, datetime.now().isoformat(), username, config_id)

            self.db_manager.execute_with_retry(update_query, params)

            self.logger.info(f"User {username} updated dropdown value (ID: {config_id}) to '{new_value}'")
            return True, "Dropdown value updated successfully."

        except Exception as e:
            self.logger.error(f"Error updating dropdown value: {str(e)}")
            return False, f"Error updating dropdown value: {str(e)}"

    def delete_dropdown_value(self, config_id: int, username: str) -> Tuple[bool, str]:
        """
        Delete (deactivate) a dropdown value.
        We soft-delete to preserve data integrity.

        Args:
            config_id: ID of the config entry to delete
            username: User performing the action

        Returns:
            Tuple of (success, message)
        """
        try:
            # Soft delete by setting is_active = 0
            update_query = """
                UPDATE system_config
                SET is_active = 0, updated_at = ?, updated_by = ?
                WHERE config_id = ? AND config_type = 'dropdown'
            """
            self.db_manager.execute_with_retry(
                update_query,
                (datetime.now().isoformat(), username, config_id)
            )

            self.logger.info(f"User {username} deleted dropdown value (ID: {config_id})")
            return True, "Dropdown value deleted successfully."

        except Exception as e:
            self.logger.error(f"Error deleting dropdown value: {str(e)}")
            return False, f"Error deleting dropdown value: {str(e)}"

    def reorder_dropdown_values(self, category: str, ordered_ids: List[int], username: str) -> Tuple[bool, str]:
        """
        Reorder dropdown values for a category.

        Args:
            category: Category name
            ordered_ids: List of config_ids in the desired order
            username: User performing the action

        Returns:
            Tuple of (success, message)
        """
        try:
            # Update display order for each item
            for order, config_id in enumerate(ordered_ids, start=1):
                update_query = """
                    UPDATE system_config
                    SET display_order = ?, updated_at = ?, updated_by = ?
                    WHERE config_id = ? AND config_category = ? AND config_type = 'dropdown'
                """
                self.db_manager.execute_with_retry(
                    update_query,
                    (order, datetime.now().isoformat(), username, config_id, category)
                )

            self.logger.info(f"User {username} reordered dropdown values for category '{category}'")
            return True, "Dropdown values reordered successfully."

        except Exception as e:
            self.logger.error(f"Error reordering dropdown values: {str(e)}")
            return False, f"Error reordering dropdown values: {str(e)}"

    def restore_dropdown_value(self, config_id: int, username: str) -> Tuple[bool, str]:
        """
        Restore a previously deleted (deactivated) dropdown value.

        Args:
            config_id: ID of the config entry to restore
            username: User performing the action

        Returns:
            Tuple of (success, message)
        """
        try:
            update_query = """
                UPDATE system_config
                SET is_active = 1, updated_at = ?, updated_by = ?
                WHERE config_id = ? AND config_type = 'dropdown'
            """
            self.db_manager.execute_with_retry(
                update_query,
                (datetime.now().isoformat(), username, config_id)
            )

            self.logger.info(f"User {username} restored dropdown value (ID: {config_id})")
            return True, "Dropdown value restored successfully."

        except Exception as e:
            self.logger.error(f"Error restoring dropdown value: {str(e)}")
            return False, f"Error restoring dropdown value: {str(e)}"

    def is_category_admin_manageable(self, category: str) -> bool:
        """
        Check if a category is admin-manageable.

        Args:
            category: Category name

        Returns:
            True if admin can manage this category
        """
        return category in self.ADMIN_MANAGEABLE_CATEGORIES

    def bulk_import_dropdown_values(self, category: str, values: List[str], username: str, replace_existing: bool = False) -> Tuple[bool, str]:
        """
        Bulk import dropdown values for a category.

        Args:
            category: Category name
            values: List of values to import
            username: User performing the action
            replace_existing: If True, deactivate existing values first

        Returns:
            Tuple of (success, message)
        """
        try:
            if replace_existing:
                # Deactivate all existing values in this category
                deactivate_query = """
                    UPDATE system_config
                    SET is_active = 0, updated_at = ?, updated_by = ?
                    WHERE config_type = 'dropdown' AND config_category = ?
                """
                self.db_manager.execute_with_retry(
                    deactivate_query,
                    (datetime.now().isoformat(), username, category)
                )

            # Import new values
            added_count = 0
            for order, value in enumerate(values, start=1):
                success, message = self.add_dropdown_value(category, value, username, display_order=order)
                if success:
                    added_count += 1

            self.logger.info(f"User {username} bulk imported {added_count} values to category '{category}'")
            return True, f"Successfully imported {added_count} of {len(values)} values."

        except Exception as e:
            self.logger.error(f"Error bulk importing dropdown values: {str(e)}")
            return False, f"Error bulk importing values: {str(e)}"

    def get_all_dropdown_values(self, category: str) -> List[Dict]:
        """
        Get ALL dropdown values for a category (including inactive ones).
        Used for admin management view.

        Args:
            category: Dropdown category name

        Returns:
            List of dictionaries with value details
        """
        try:
            query = """
                SELECT config_id, config_value, display_order, is_active, updated_by
                FROM system_config
                WHERE config_type = 'dropdown' AND config_category = ?
                ORDER BY display_order, config_value
            """
            results = self.db_manager.execute_with_retry(query, (category,))

            values = []
            for row in results:
                values.append({
                    'config_id': row[0],
                    'value': row[1],
                    'display_order': row[2],
                    'is_active': row[3],
                    'updated_by': row[4]
                })

            return values

        except Exception as e:
            self.logger.error(f"Error getting all dropdown values for '{category}': {str(e)}")
            return []
