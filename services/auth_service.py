"""
Authentication and user management service.
Handles user authentication, session management, and user CRUD operations.
"""

import bcrypt
from datetime import datetime
from typing import Optional, Dict, List, Tuple
from services.security_service import SecurityService


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
                       failed_login_attempts,
                       COALESCE(must_change_password, 0),
                       COALESCE(onboarding_pending, 0),
                       COALESCE(language, 'en')
                FROM users
                WHERE username = ? COLLATE NOCASE
            """
            result = self.db_manager.execute_with_retry(query, (username,))

            if not result:
                self.logger.warning(f"Login attempt for non-existent user: {username}")
                return False, None, "Invalid username or password"

            user = result[0]
            (user_id, db_username, db_password, full_name, role, is_active,
             failed_attempts, must_change_password, onboarding_pending, language) = user

            # Onboarding handshake (#1): a pending user has no password yet — never
            # let them "log in" (an empty stored password would otherwise match an
            # empty entry via the legacy path). Route them to self-registration.
            if onboarding_pending:
                return False, None, "ONBOARDING_REQUIRED"

            # Check if user is active
            if not is_active:
                self.logger.warning(f"Login attempt for inactive user: {username}")
                return False, None, "Account is inactive. Contact administrator."

            # Check if account is locked (5 failed attempts)
            if failed_attempts >= 5:
                self.logger.warning(f"Login attempt for locked account: {username}")
                return False, None, "Account is locked due to too many failed attempts. Contact administrator."

            # Verify password (supports both bcrypt and legacy plain text)
            password_valid = False

            if SecurityService.is_bcrypt_hash(db_password):
                # Use bcrypt verification
                password_valid = SecurityService.verify_password(password, db_password)
            else:
                # Legacy plain text password (backward compatibility)
                password_valid = (password == db_password)

                # Auto-migrate to bcrypt on successful login
                if password_valid:
                    try:
                        hashed_password = SecurityService.hash_password(password)
                        self.db_manager.execute_with_retry(
                            "UPDATE users SET password = ? WHERE user_id = ?",
                            (hashed_password, user_id)
                        )
                        self.logger.info(f"Auto-migrated password to bcrypt for user: {username}")
                    except Exception as e:
                        self.logger.error(f"Error auto-migrating password: {str(e)}")

            if not password_valid:
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

            # Get the session ID (last_insert_rowid() is useless here — the
            # db_manager opens a fresh connection per statement, so it always
            # returns 0; fetch the row we just inserted instead)
            session_id_result = self.db_manager.execute_with_retry(
                "SELECT session_id FROM session_log WHERE user_id = ? ORDER BY session_id DESC LIMIT 1",
                (user_id,)
            )
            self.current_session_id = session_id_result[0][0] if session_id_result else None

            # Set current user (include the last_login we just set)
            self.current_user = {
                'user_id': user_id,
                'username': db_username,
                'full_name': full_name,
                'role': role,
                'last_login': datetime.now().isoformat(),
                'must_change_password': bool(must_change_password),
                'language': language or 'en',
            }

            # Update logging service user context
            self.logger.set_user_context(user_id, db_username)

            self.logger.info(f"User logged in: {db_username} (Role: {role})")

            return True, self.current_user, "Login successful"

        except Exception as e:
            self.logger.error(f"Error during authentication: {str(e)}", exc_info=True)
            return False, None, "An error occurred during login"

    def logout(self):
        """Logout the current user. Always clears session state, even if
        the session-log bookkeeping fails — a user must never stay
        authenticated after logout."""
        try:
            if self.current_user and self.current_session_id:
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

            if self.current_user:
                self.logger.info(f"User logged out: {self.current_user['username']}")

        except Exception as e:
            self.logger.error(f"Error during logout: {str(e)}", exc_info=True)
        finally:
            self.logger.clear_user_context()
            self.current_user = None
            self.current_session_id = None

    def get_current_user(self) -> Optional[Dict]:
        """Get the current authenticated user."""
        return self.current_user

    def is_authenticated(self) -> bool:
        """Check if a user is currently authenticated."""
        return self.current_user is not None

    def _require_admin(self, action: str) -> Tuple[bool, str]:
        """Authorization gate for privileged user-management operations.
        The service layer is the security boundary — never rely on the UI
        hiding a button, since a lower-privileged session that reaches the
        method directly would otherwise escalate."""
        if not self.current_user:
            return False, "Not authenticated"
        if self.current_user.get('role') != 'admin':
            self.logger.warning(
                f"Unauthorized {action} attempt by "
                f"{self.current_user.get('username')} (role={self.current_user.get('role')})"
            )
            return False, "Administrator privileges required"
        return True, ""

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
            resource_owner=resource_owner,
            current_user=self.current_user['username']
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
            allowed, why = self._require_admin("create_user")
            if not allowed:
                return False, why

            # Validate role
            if role not in ['admin', 'supervisor', 'agent', 'reporter']:
                return False, "Invalid role"

            # Check if username already exists
            check_query = "SELECT COUNT(*) FROM users WHERE username = ? COLLATE NOCASE"
            result = self.db_manager.execute_with_retry(check_query, (username,))
            if result and result[0][0] > 0:
                return False, "Username already exists"

            # Insert user (always store a bcrypt hash, never the plain password)
            insert_query = """
                INSERT INTO users (username, password, full_name, role, is_active, created_by)
                VALUES (?, ?, ?, ?, 1, ?)
            """
            self.db_manager.execute_with_retry(
                insert_query,
                (username, SecurityService.hash_password(password), full_name, role,
                 self.current_user['username'] if self.current_user else 'SYSTEM')
            )

            self.logger.log_user_action(
                "USER_CREATED",
                {'username': username, 'role': role, 'created_by': self.current_user['username'] if self.current_user else 'SYSTEM'}
            )

            return True, f"User {username} created successfully"

        except Exception as e:
            self.logger.error(f"Error creating user: {str(e)}", exc_info=True)
            return False, f"Error creating user: {str(e)}"

    # ---------------------------------------------------- two-way handshake (#1)
    def create_pending_user(self, username: str, role: str) -> Tuple[bool, str]:
        """Admin creates a user ID + role only. The user self-registers their
        own full name + password at first login (onboarding handshake), so the
        admin never knows an FIU reporter's password."""
        try:
            allowed, why = self._require_admin("create_pending_user")
            if not allowed:
                return False, why
            username = (username or "").strip()
            if not username:
                return False, "User ID is required"
            if role not in ['admin', 'supervisor', 'agent', 'reporter']:
                return False, "Invalid role"
            exists = self.db_manager.execute_with_retry(
                "SELECT COUNT(*) FROM users WHERE username = ? COLLATE NOCASE", (username,))
            if exists and exists[0][0] > 0:
                return False, "User ID already exists"
            # password/full_name stay empty until the user completes onboarding
            self.db_manager.execute_with_retry(
                "INSERT INTO users (username, password, full_name, role, is_active, "
                "onboarding_pending, created_by) VALUES (?, '', '', ?, 1, 1, ?)",
                (username, role, self.current_user['username'] if self.current_user else 'SYSTEM'))
            self.logger.log_user_action(
                "USER_PENDING_CREATED",
                {'username': username, 'role': role,
                 'created_by': self.current_user['username'] if self.current_user else 'SYSTEM'})
            return True, f"User ID '{username}' created — the user completes registration at first login."
        except Exception as e:
            self.logger.error(f"Error creating pending user: {str(e)}", exc_info=True)
            return False, f"Error creating user: {str(e)}"

    def get_onboarding_status(self, username: str) -> str:
        """'pending' (needs self-registration), 'active' (normal login), or
        'unknown' (no such user / inactive). Used by the login screen to route."""
        try:
            rows = self.db_manager.execute_with_retry(
                "SELECT COALESCE(onboarding_pending, 0), is_active FROM users "
                "WHERE username = ? COLLATE NOCASE", ((username or "").strip(),))
            if not rows:
                return "unknown"
            pending, is_active = rows[0]
            if not is_active:
                return "unknown"
            return "pending" if pending else "active"
        except Exception as e:
            self.logger.error(f"Error checking onboarding status: {str(e)}")
            return "unknown"

    def complete_onboarding(self, username: str, full_name: str, password: str) -> Tuple[bool, str]:
        """The USER (not the admin) sets their own name + password. Only works
        for a user still in the pending state. Not admin-gated — runs pre-login."""
        try:
            username = (username or "").strip()
            full_name = (full_name or "").strip()
            rows = self.db_manager.execute_with_retry(
                "SELECT user_id, COALESCE(onboarding_pending, 0), is_active FROM users "
                "WHERE username = ? COLLATE NOCASE", (username,))
            if not rows:
                return False, "Unknown user ID."
            user_id, pending, is_active = rows[0]
            if not is_active:
                return False, "This account is inactive. Contact your administrator."
            if not pending:
                return False, "This user is already registered. Please log in."
            if not full_name:
                return False, "Full name is required."
            score, feedback = SecurityService.check_password_strength(password)
            if not password or len(password) < 8:
                return False, feedback or "Password must be at least 8 characters."
            self.db_manager.execute_with_retry(
                "UPDATE users SET password = ?, full_name = ?, onboarding_pending = 0, "
                "must_change_password = 0, failed_login_attempts = 0, "
                "updated_at = datetime('now'), updated_by = ? WHERE user_id = ?",
                (SecurityService.hash_password(password), full_name, username, user_id))
            self.logger.log_user_action("USER_ONBOARDED", {'username': username})
            return True, "Registration complete — you can now use the application."
        except Exception as e:
            self.logger.error(f"Error completing onboarding: {str(e)}", exc_info=True)
            return False, f"Error completing registration: {str(e)}"

    def reset_onboarding(self, username: str) -> Tuple[bool, str]:
        """Admin re-arms the handshake for a user (e.g. forgotten password):
        clears their password + name so they self-register again."""
        try:
            allowed, why = self._require_admin("reset_onboarding")
            if not allowed:
                return False, why
            username = (username or "").strip()
            rows = self.db_manager.execute_with_retry(
                "SELECT user_id, role FROM users WHERE username = ? COLLATE NOCASE", (username,))
            if not rows:
                return False, "Unknown user ID."
            self.db_manager.execute_with_retry(
                "UPDATE users SET password = '', onboarding_pending = 1, "
                "failed_login_attempts = 0, updated_at = datetime('now'), updated_by = ? "
                "WHERE username = ? COLLATE NOCASE",
                (self.current_user['username'] if self.current_user else 'SYSTEM', username))
            self.logger.log_user_action("USER_ONBOARDING_RESET", {'username': username})
            return True, f"'{username}' must re-register (name + password) at next login."
        except Exception as e:
            self.logger.error(f"Error resetting onboarding: {str(e)}", exc_info=True)
            return False, f"Error: {str(e)}"

    def set_user_language(self, language: str) -> Tuple[bool, str]:
        """A user sets their OWN UI language (#3). Self-service — not admin-gated."""
        if not self.current_user:
            return False, "Not authenticated"
        if language not in ('en', 'ar'):
            return False, "Unsupported language"
        try:
            self.db_manager.execute_with_retry(
                "UPDATE users SET language = ?, updated_at = datetime('now') WHERE user_id = ?",
                (language, self.current_user['user_id']))
            self.current_user['language'] = language
            return True, "Language updated"
        except Exception as e:
            self.logger.error(f"Error setting language: {str(e)}")
            return False, f"Error: {str(e)}"

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
            allowed, why = self._require_admin("update_user")
            if not allowed:
                return False, why

            # Guard against an admin locking themselves out of admin
            if self.current_user and user_id == self.current_user.get('user_id'):
                if 'role' in kwargs and kwargs['role'] != 'admin':
                    return False, "You cannot remove your own administrator role"
                if 'is_active' in kwargs and not kwargs['is_active']:
                    return False, "You cannot deactivate your own account"

            # System must always retain at least one active admin: block a change
            # that would demote or deactivate the last one.
            demoting = ('role' in kwargs and kwargs['role'] != 'admin') or \
                       ('is_active' in kwargs and not kwargs['is_active'])
            if demoting:
                target = self.db_manager.execute_with_retry(
                    "SELECT role, is_active FROM users WHERE user_id = ?", (user_id,))
                if target and target[0][0] == 'admin' and target[0][1]:
                    n_admins = self.db_manager.execute_with_retry(
                        "SELECT COUNT(*) FROM users WHERE role = 'admin' AND is_active = 1")
                    if n_admins and n_admins[0][0] <= 1:
                        return False, "Cannot remove the last active administrator"

            # Build update query
            allowed_fields = ['password', 'full_name', 'role', 'is_active']
            updates = []
            params = []

            for field, value in kwargs.items():
                if field in allowed_fields:
                    # Never store a plaintext password
                    if field == 'password' and value and not SecurityService.is_bcrypt_hash(str(value)):
                        value = SecurityService.hash_password(str(value))
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
            allowed, why = self._require_admin("delete_user")
            if not allowed:
                return False, why

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
            allowed, why = self._require_admin("reset_password")
            if not allowed:
                return False, why

            # Always store a bcrypt hash, never the plaintext password
            hashed = SecurityService.hash_password(new_password)
            query = "UPDATE users SET password = ?, updated_by = ?, updated_at = ? WHERE user_id = ?"
            self.db_manager.execute_with_retry(
                query,
                (hashed,
                 self.current_user['username'] if self.current_user else 'SYSTEM',
                 datetime.now().isoformat(),
                 user_id)
            )

            self.logger.log_user_action("PASSWORD_RESET", {'user_id': user_id})

            return True, "Password reset successfully"

        except Exception as e:
            self.logger.error(f"Error resetting password: {str(e)}", exc_info=True)
            return False, f"Error resetting password: {str(e)}"

    def verify_password(self, username: str, password: str) -> bool:
        """
        Verify a user's password without logging in.

        Args:
            username: Username
            password: Password to verify

        Returns:
            True if password is correct
        """
        try:
            query = "SELECT password FROM users WHERE username = ? COLLATE NOCASE"
            result = self.db_manager.execute_with_retry(query, (username,))

            if not result:
                return False

            db_password = result[0][0]

            # Support both bcrypt and legacy plain text passwords
            if SecurityService.is_bcrypt_hash(db_password):
                return SecurityService.verify_password(password, db_password)
            else:
                # Legacy plain text comparison
                return password == db_password

        except Exception as e:
            self.logger.error(f"Error verifying password: {str(e)}", exc_info=True)
            return False

    def change_password(self, user_id: int, new_password: str) -> bool:
        """
        Change a user's password (user-initiated).

        Args:
            user_id: User ID
            new_password: New password (plain text, will be hashed)

        Returns:
            True if successful
        """
        try:
            # Hash the new password with bcrypt
            hashed_password = SecurityService.hash_password(new_password)

            query = ("UPDATE users SET password = ?, must_change_password = 0, "
                     "updated_by = ?, updated_at = ? WHERE user_id = ?")
            self.db_manager.execute_with_retry(
                query,
                (hashed_password,
                 self.current_user['username'] if self.current_user else 'SYSTEM',
                 datetime.now().isoformat(),
                 user_id)
            )
            # keep the in-memory session flag in sync so the login flow stops nagging
            if self.current_user and self.current_user.get('user_id') == user_id:
                self.current_user['must_change_password'] = False

            self.logger.log_user_action("PASSWORD_CHANGED", {'user_id': user_id})
            self.logger.info(f"Password changed successfully for user_id: {user_id}")

            return True

        except Exception as e:
            self.logger.error(f"Error changing password: {str(e)}", exc_info=True)
            return False

    def unlock_account(self, user_id: int) -> Tuple[bool, str]:
        """
        Unlock a locked user account.

        Args:
            user_id: User ID

        Returns:
            Tuple of (success, message)
        """
        try:
            allowed, why = self._require_admin("unlock_account")
            if not allowed:
                return False, why

            query = "UPDATE users SET failed_login_attempts = 0 WHERE user_id = ?"
            self.db_manager.execute_with_retry(query, (user_id,))

            self.logger.log_user_action("ACCOUNT_UNLOCKED", {'user_id': user_id})

            return True, "Account unlocked successfully"

        except Exception as e:
            self.logger.error(f"Error unlocking account: {str(e)}", exc_info=True)
            return False, f"Error unlocking account: {str(e)}"
