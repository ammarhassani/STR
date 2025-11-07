"""
Security Service
Handles security-related operations including password hashing, input sanitization,
and security utilities.
"""

import bcrypt
import hashlib
import secrets
import re
from typing import Optional, Tuple
from datetime import datetime, timedelta


class SecurityService:
    """
    Service for security operations.

    Features:
    - bcrypt password hashing
    - Password strength validation
    - Input sanitization
    - Session token generation
    - Security headers
    """

    # Password configuration
    BCRYPT_ROUNDS = 12  # Cost factor for bcrypt

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password using bcrypt.

        Args:
            password: Plain text password

        Returns:
            Hashed password (bcrypt hash)
        """
        # Encode password to bytes and hash with bcrypt
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt(rounds=SecurityService.BCRYPT_ROUNDS)
        hashed = bcrypt.hashpw(password_bytes, salt)
        return hashed.decode('utf-8')

    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        """
        Verify a password against a bcrypt hash.

        Args:
            password: Plain text password
            hashed_password: Hashed password (bcrypt)

        Returns:
            True if password matches, False otherwise
        """
        try:
            password_bytes = password.encode('utf-8')
            hashed_bytes = hashed_password.encode('utf-8')
            return bcrypt.checkpw(password_bytes, hashed_bytes)
        except Exception:
            return False

    @staticmethod
    def is_bcrypt_hash(password_hash: str) -> bool:
        """
        Check if a password hash is a valid bcrypt hash.

        Args:
            password_hash: Password hash to check

        Returns:
            True if valid bcrypt hash, False otherwise
        """
        # bcrypt hashes start with $2a$, $2b$, or $2y$ and are 60 characters
        return bool(re.match(r'^\$2[aby]\$\d{2}\$.{53}$', password_hash))

    @staticmethod
    def migrate_plain_password(plain_password: str) -> str:
        """
        Convert a plain text password to bcrypt hash.
        Used for migrating legacy passwords.

        Args:
            plain_password: Plain text password

        Returns:
            bcrypt hashed password
        """
        return SecurityService.hash_password(plain_password)

    @staticmethod
    def generate_session_token(length: int = 32) -> str:
        """
        Generate a secure random session token.

        Args:
            length: Length of the token in bytes (default 32)

        Returns:
            Hexadecimal token string
        """
        return secrets.token_hex(length)

    @staticmethod
    def sanitize_input(text: str, max_length: Optional[int] = None) -> str:
        """
        Sanitize user input to prevent injection attacks.

        Args:
            text: Input text to sanitize
            max_length: Maximum allowed length (optional)

        Returns:
            Sanitized text
        """
        if not text:
            return ""

        # Remove null bytes
        sanitized = text.replace('\x00', '')

        # Trim to max length if specified
        if max_length and len(sanitized) > max_length:
            sanitized = sanitized[:max_length]

        # Strip leading/trailing whitespace
        sanitized = sanitized.strip()

        return sanitized

    @staticmethod
    def sanitize_sql_like_pattern(pattern: str) -> str:
        """
        Sanitize a string for use in SQL LIKE patterns.
        Escapes special characters to prevent SQL injection.

        Args:
            pattern: Search pattern

        Returns:
            Escaped pattern safe for SQL LIKE
        """
        if not pattern:
            return ""

        # Escape special LIKE characters
        pattern = pattern.replace('\\', '\\\\')
        pattern = pattern.replace('%', '\\%')
        pattern = pattern.replace('_', '\\_')
        pattern = pattern.replace('[', '\\[')

        return pattern

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize a filename to prevent path traversal attacks.

        Args:
            filename: Original filename

        Returns:
            Sanitized filename
        """
        if not filename:
            return "unnamed"

        # Remove path separators
        filename = filename.replace('/', '_').replace('\\', '_')

        # Remove null bytes
        filename = filename.replace('\x00', '')

        # Remove special characters
        filename = re.sub(r'[<>:"|?*]', '_', filename)

        # Remove leading/trailing dots and spaces
        filename = filename.strip('. ')

        # Ensure filename is not empty
        if not filename:
            filename = "unnamed"

        return filename

    @staticmethod
    def check_password_strength(password: str) -> Tuple[int, str]:
        """
        Check password strength and return score and feedback.

        Args:
            password: Password to check

        Returns:
            Tuple of (score 0-5, feedback message)
        """
        score = 0
        feedback = []

        if not password:
            return 0, "Password is required"

        # Length check
        length = len(password)
        if length < 8:
            feedback.append("Too short (minimum 8 characters)")
        elif length >= 12:
            score += 2
        else:
            score += 1

        # Character variety checks
        has_lowercase = bool(re.search(r'[a-z]', password))
        has_uppercase = bool(re.search(r'[A-Z]', password))
        has_digit = bool(re.search(r'\d', password))
        has_special = bool(re.search(r'[!@#$%^&*()_+\-=\[\]{};:,.<>?]', password))

        if has_lowercase:
            score += 1
        else:
            feedback.append("Add lowercase letters")

        if has_uppercase:
            score += 1
        else:
            feedback.append("Add uppercase letters")

        if has_digit:
            score += 1
        else:
            feedback.append("Add numbers")

        if has_special:
            score += 1
        else:
            feedback.append("Add special characters")

        # Common password check
        common_passwords = [
            'password', '12345678', 'qwerty', 'abc123', 'letmein',
            'password123', 'admin', 'welcome', 'monkey', '1234567890'
        ]
        if password.lower() in common_passwords:
            score = max(0, score - 3)
            feedback.append("This is a commonly used password")

        # Generate feedback message
        if score <= 1:
            strength = "Very Weak"
        elif score == 2:
            strength = "Weak"
        elif score == 3:
            strength = "Fair"
        elif score == 4:
            strength = "Strong"
        else:
            strength = "Very Strong"

        if feedback:
            message = f"{strength}: {', '.join(feedback)}"
        else:
            message = f"{strength}: Good password!"

        return score, message

    @staticmethod
    def hash_for_audit(sensitive_data: str) -> str:
        """
        Create a one-way hash of sensitive data for audit logging.
        Uses SHA-256 for consistent, irreversible hashing.

        Args:
            sensitive_data: Sensitive data to hash

        Returns:
            SHA-256 hash (hexadecimal)
        """
        return hashlib.sha256(sensitive_data.encode('utf-8')).hexdigest()

    @staticmethod
    def constant_time_compare(a: str, b: str) -> bool:
        """
        Constant-time string comparison to prevent timing attacks.

        Args:
            a: First string
            b: Second string

        Returns:
            True if strings are equal, False otherwise
        """
        return secrets.compare_digest(a.encode('utf-8'), b.encode('utf-8'))

    @staticmethod
    def generate_api_key(prefix: str = "fiu") -> str:
        """
        Generate a secure API key.

        Args:
            prefix: Prefix for the API key (default "fiu")

        Returns:
            API key string
        """
        random_part = secrets.token_urlsafe(32)
        return f"{prefix}_{random_part}"

    @staticmethod
    def is_safe_redirect_url(url: str, allowed_hosts: list) -> bool:
        """
        Check if a redirect URL is safe (prevents open redirect vulnerabilities).

        Args:
            url: URL to check
            allowed_hosts: List of allowed host names

        Returns:
            True if URL is safe, False otherwise
        """
        if not url:
            return False

        # Check for absolute URLs with disallowed hosts
        if url.startswith('http://') or url.startswith('https://'):
            # Extract host from URL
            match = re.match(r'https?://([^/]+)', url)
            if match:
                host = match.group(1)
                return host in allowed_hosts
            return False

        # Relative URLs starting with / are generally safe
        if url.startswith('/'):
            return True

        # URLs without scheme or leading slash are suspicious
        return False

    @staticmethod
    def sanitize_log_message(message: str) -> str:
        """
        Sanitize a log message to prevent log injection attacks.

        Args:
            message: Log message

        Returns:
            Sanitized log message
        """
        if not message:
            return ""

        # Replace newlines and carriage returns to prevent log injection
        message = message.replace('\n', ' ').replace('\r', ' ')

        # Remove ANSI escape codes
        message = re.sub(r'\x1b\[[0-9;]*m', '', message)

        # Limit length
        if len(message) > 1000:
            message = message[:997] + "..."

        return message


class PasswordMigrationService:
    """
    Service for migrating plain text passwords to bcrypt hashes.
    """

    def __init__(self, db_manager, logging_service):
        """
        Initialize password migration service.

        Args:
            db_manager: DatabaseManager instance
            logging_service: LoggingService instance
        """
        self.db_manager = db_manager
        self.logging_service = logging_service

    def needs_migration(self) -> Tuple[bool, int]:
        """
        Check if password migration is needed.

        Returns:
            Tuple of (needs_migration, count_of_plain_passwords)
        """
        try:
            query = "SELECT COUNT(*) FROM users WHERE password NOT LIKE '$2%'"
            result = self.db_manager.execute_with_retry(query)
            count = result[0][0] if result else 0
            return count > 0, count
        except Exception as e:
            self.logging_service.error(f"Error checking migration status: {str(e)}")
            return False, 0

    def migrate_all_passwords(self) -> Tuple[bool, str]:
        """
        Migrate all plain text passwords to bcrypt hashes.

        Returns:
            Tuple of (success, message)
        """
        try:
            # Get all users with plain text passwords
            query = "SELECT user_id, password FROM users WHERE password NOT LIKE '$2%'"
            users = self.db_manager.execute_with_retry(query)

            if not users:
                return True, "No passwords need migration"

            migrated_count = 0

            for user_id, plain_password in users:
                try:
                    # Hash the plain password
                    hashed_password = SecurityService.hash_password(plain_password)

                    # Update in database
                    update_query = "UPDATE users SET password = ? WHERE user_id = ?"
                    self.db_manager.execute_with_retry(update_query, (hashed_password, user_id))

                    migrated_count += 1
                    self.logging_service.info(f"Migrated password for user_id {user_id}")

                except Exception as e:
                    self.logging_service.error(f"Error migrating password for user_id {user_id}: {str(e)}")

            message = f"Successfully migrated {migrated_count} password(s) to bcrypt"
            self.logging_service.info(message)

            return True, message

        except Exception as e:
            error_msg = f"Error during password migration: {str(e)}"
            self.logging_service.error(error_msg, exc_info=True)
            return False, error_msg
