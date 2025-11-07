"""
Authentication and user management service.
Handles user authentication, session management, and user CRUD operations.
"""

import bcrypt
from datetime import datetime
from typing import Optional, Dict, List, Tuple


class AuthService:
    """Service for handling authentication and user management."""

    def __init__(self, db_manager, logging_service):
        """
        Initialize the authentication service.

        Args:
            db_manager: DatabaseManager instance
            logging_service: LoggingService instance
        """
        self.db_manager = db_manager
        self.logger = logging_service
        self.current_user = None
        self.current_session_id = None

    def authenticate(self, username: str, password: str) -> Tuple[bool, Optional[Dict], str]:
        """
        Authenticate a user with username and password.

        Args:
            username: Username
            password: Password

        Returns:
            Tuple of (success, user_dict, message)
        """
        try:
            # Get user from database
            query = """
                SELECT user_id, username, password, full_name, role, is_active,
                       failed_login_attempts
                FROM users
                WHERE username = ? COLLATE NOCASE
            """
            result = self.db_manager.execute_with_retry(query, (username,))

            if not result:
                self.logger.warning(f"Login attempt for non-existent user: {username}")
                return False, None, "Invalid username or password"

            user = result[0]
            user_id, db_username, db_password, full_name, role, is_active, failed_attempts = user

            # Check if user is active
            if not is_active:
                self.logger.warning(f"Login attempt for inactive user: {username}")
                return False, None, "Account is inactive. Contact administrator."

            # Check if account is locked (5 failed attempts)
            if failed_attempts >= 5:
                self.logger.warning(f"Login attempt for locked account: {username}")
                return False, None, "Account is locked due to too many failed attempts. Contact administrator."

            # Verify password
            # Note: Current system uses plain text passwords
            # TODO: Migrate to bcrypt hashed passwords
            if password != db_password:
                # Increment failed attempts
                self.db_manager.execute_with_retry(
                    "UPDATE users SET failed_login_attempts = failed_login_attempts + 1 WHERE user_id = ?",
                    (user_id,)
                )
                self.logger.warning(f"Failed login attempt for user: {username}")
                return False, None, "Invalid username or password"

            # Successful login - reset failed attempts
            self.db_manager.execute_with_retry(
                """UPDATE users
                   SET failed_login_attempts = 0,
                       last_login = ?
                   WHERE user_id = ?""",
                (datetime.now().isoformat(), user_id)
            )

            # Create session log entry
            session_query = """
                INSERT INTO session_log (user_id, username, login_time)
                VALUES (?, ?, ?)
            """
            self.db_manager.execute_with_retry(
                session_query,
                (user_id, db_username, datetime.now().isoformat())
            )

            # Get the session ID
            session_id_result = self.db_manager.execute_with_retry(
                "SELECT last_insert_rowid()"
            )
            self.current_session_id = session_id_result[0][0] if session_id_result else None

            # Set current user
            self.current_user = {
                'user_id': user_id,
                'username': db_username,
                'full_name': full_name,
                'role': role
            }

            # Update logging service user context
            self.logger.set_user_context(user_id, db_username)

            self.logger.info(f"User logged in: {db_username} (Role: {role})")

            return True, self.current_user, "Login successful"

        except Exception as e:
            self.logger.error(f"Error during authentication: {str(e)}", exc_info=True)
            return False, None, "An error occurred during login"

    def logout(self):
        """Logout the current user."""
        if self.current_user and self.current_session_id:
            try:
                # Update session log with logout time
                logout_query = """
                    UPDATE session_log
                    SET logout_time = ?,
                        session_duration = (
                            (julianday(?) - julianday(login_time)) * 86400
                        )
                    WHERE session_id = ?
                """
                self.db_manager.execute_with_retry(
                    logout_query,
                    (datetime.now().isoformat(), datetime.now().isoformat(), self.current_session_id)
                )

                self.logger.info(f"User logged out: {self.current_user['username']}")

                # Clear user context
                self.logger.clear_user_context()
                self.current_user = None
                self.current_session_id = None

            except Exception as e:
                self.logger.error(f"Error during logout: {str(e)}", exc_info=True)

    def get_current_user(self) -> Optional[Dict]:
        """Get the current authenticated user."""
        return self.current_user

    def is_authenticated(self) -> bool:
        """Check if a user is currently authenticated."""
        return self.current_user is not None

    def has_permission(self, permission: str, resource_owner: Optional[str] = None) -> bool:
        """
        Check if current user has a specific permission.

        Args:
            permission: Permission to check
            resource_owner: Optional username of resource owner (for ownership checks)

        Returns:
            True if user has permission, False otherwise
        """
        if not self.current_user:
            return False

        from utils.permissions import has_permission
        return has_permission(
            self.current_user['role'],
            permission,
            self.current_user['username'],
            resource_owner
        )

    def create_user(self, username: str, password: str, full_name: str, role: str) -> Tuple[bool, str]:
        """
        Create a new user.

        Args:
            username: Username
            password: Password
            full_name: Full name
            role: Role (admin, agent, reporter)

        Returns:
            Tuple of (success, message)
        """
        try:
            # Validate role
            if role not in ['admin', 'agent', 'reporter']:
                return False, "Invalid role"

            # Check if username already exists
            check_query = "SELECT COUNT(*) FROM users WHERE username = ? COLLATE NOCASE"
            result = self.db_manager.execute_with_retry(check_query, (username,))
            if result and result[0][0] > 0:
                return False, "Username already exists"

            # Insert user
            insert_query = """
                INSERT INTO users (username, password, full_name, role, is_active, created_by)
                VALUES (?, ?, ?, ?, 1, ?)
            """
            self.db_manager.execute_with_retry(
                insert_query,
                (username, password, full_name, role, self.current_user['username'] if self.current_user else 'SYSTEM')
            )

            self.logger.log_user_action(
                "USER_CREATED",
                {'username': username, 'role': role, 'created_by': self.current_user['username'] if self.current_user else 'SYSTEM'}
            )

            return True, f"User {username} created successfully"

        except Exception as e:
            self.logger.error(f"Error creating user: {str(e)}", exc_info=True)
            return False, f"Error creating user: {str(e)}"

    def update_user(self, user_id: int, **kwargs) -> Tuple[bool, str]:
        """
        Update user information.

        Args:
            user_id: User ID to update
            **kwargs: Fields to update (password, full_name, role, is_active)

        Returns:
            Tuple of (success, message)
        """
        try:
            # Build update query
            allowed_fields = ['password', 'full_name', 'role', 'is_active']
            updates = []
            params = []

            for field, value in kwargs.items():
                if field in allowed_fields:
                    updates.append(f"{field} = ?")
                    params.append(value)

            if not updates:
                return False, "No valid fields to update"

            # Add updated_by and updated_at
            updates.append("updated_by = ?")
            updates.append("updated_at = ?")
            params.extend([
                self.current_user['username'] if self.current_user else 'SYSTEM',
                datetime.now().isoformat()
            ])

            # Add user_id for WHERE clause
            params.append(user_id)

            query = f"UPDATE users SET {', '.join(updates)} WHERE user_id = ?"
            self.db_manager.execute_with_retry(query, params)

            self.logger.log_user_action(
                "USER_UPDATED",
                {'user_id': user_id, 'fields': list(kwargs.keys())}
            )

            return True, "User updated successfully"

        except Exception as e:
            self.logger.error(f"Error updating user: {str(e)}", exc_info=True)
            return False, f"Error updating user: {str(e)}"

    def delete_user(self, user_id: int) -> Tuple[bool, str]:
        """
        Delete a user (soft delete by setting is_active to 0).

        Args:
            user_id: User ID to delete

        Returns:
            Tuple of (success, message)
        """
        try:
            # Cannot delete yourself
            if self.current_user and user_id == self.current_user['user_id']:
                return False, "Cannot delete your own account"

            # Soft delete
            query = "UPDATE users SET is_active = 0, updated_by = ?, updated_at = ? WHERE user_id = ?"
            self.db_manager.execute_with_retry(
                query,
                (self.current_user['username'] if self.current_user else 'SYSTEM',
                 datetime.now().isoformat(),
                 user_id)
            )

            self.logger.log_user_action("USER_DELETED", {'user_id': user_id})

            return True, "User deleted successfully"

        except Exception as e:
            self.logger.error(f"Error deleting user: {str(e)}", exc_info=True)
            return False, f"Error deleting user: {str(e)}"

    def get_all_users(self) -> List[Dict]:
        """
        Get all users.

        Returns:
            List of user dictionaries
        """
        try:
            query = """
                SELECT user_id, username, full_name, role, is_active, last_login, created_at
                FROM users
                ORDER BY username
            """
            result = self.db_manager.execute_with_retry(query)

            users = []
            for row in result:
                users.append({
                    'user_id': row[0],
                    'username': row[1],
                    'full_name': row[2],
                    'role': row[3],
                    'is_active': bool(row[4]),
                    'last_login': row[5],
                    'created_at': row[6]
                })

            return users

        except Exception as e:
            self.logger.error(f"Error fetching users: {str(e)}", exc_info=True)
            return []

    def reset_password(self, user_id: int, new_password: str) -> Tuple[bool, str]:
        """
        Reset a user's password.

        Args:
            user_id: User ID
            new_password: New password

        Returns:
            Tuple of (success, message)
        """
        try:
            query = "UPDATE users SET password = ?, updated_by = ?, updated_at = ? WHERE user_id = ?"
            self.db_manager.execute_with_retry(
                query,
                (new_password,
                 self.current_user['username'] if self.current_user else 'SYSTEM',
                 datetime.now().isoformat(),
                 user_id)
            )

            self.logger.log_user_action("PASSWORD_RESET", {'user_id': user_id})

            return True, "Password reset successfully"

        except Exception as e:
            self.logger.error(f"Error resetting password: {str(e)}", exc_info=True)
            return False, f"Error resetting password: {str(e)}"

    def unlock_account(self, user_id: int) -> Tuple[bool, str]:
        """
        Unlock a locked user account.

        Args:
            user_id: User ID

        Returns:
            Tuple of (success, message)
        """
        try:
            query = "UPDATE users SET failed_login_attempts = 0 WHERE user_id = ?"
            self.db_manager.execute_with_retry(query, (user_id,))

            self.logger.log_user_action("ACCOUNT_UNLOCKED", {'user_id': user_id})

            return True, "Account unlocked successfully"

        except Exception as e:
            self.logger.error(f"Error unlocking account: {str(e)}", exc_info=True)
            return False, f"Error unlocking account: {str(e)}"
