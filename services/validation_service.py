"""
Validation Service
Provides reusable validation rules and form validation utilities.
"""

import re
from typing import Callable, List, Optional, Dict, Any, Tuple
from datetime import datetime
from decimal import Decimal, InvalidOperation


class ValidationRule:
    """Base class for validation rules."""

    def __init__(self, error_message: str):
        """
        Initialize validation rule.

        Args:
            error_message: Error message to display on failure
        """
        self.error_message = error_message

    def validate(self, value: Any) -> Tuple[bool, str]:
        """
        Validate a value.

        Args:
            value: Value to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        raise NotImplementedError


class RequiredRule(ValidationRule):
    """Validation rule for required fields."""

    def __init__(self, error_message: str = "This field is required"):
        super().__init__(error_message)

    def validate(self, value: Any) -> Tuple[bool, str]:
        if value is None or (isinstance(value, str) and not value.strip()):
            return False, self.error_message
        return True, ""


class MinLengthRule(ValidationRule):
    """Validation rule for minimum string length."""

    def __init__(self, min_length: int, error_message: Optional[str] = None):
        self.min_length = min_length
        if error_message is None:
            error_message = f"Must be at least {min_length} characters"
        super().__init__(error_message)

    def validate(self, value: Any) -> Tuple[bool, str]:
        if value and len(str(value)) < self.min_length:
            return False, self.error_message
        return True, ""


class MaxLengthRule(ValidationRule):
    """Validation rule for maximum string length."""

    def __init__(self, max_length: int, error_message: Optional[str] = None):
        self.max_length = max_length
        if error_message is None:
            error_message = f"Must be no more than {max_length} characters"
        super().__init__(error_message)

    def validate(self, value: Any) -> Tuple[bool, str]:
        if value and len(str(value)) > self.max_length:
            return False, self.error_message
        return True, ""


class EmailRule(ValidationRule):
    """Validation rule for email addresses."""

    EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

    def __init__(self, error_message: str = "Invalid email address"):
        super().__init__(error_message)

    def validate(self, value: Any) -> Tuple[bool, str]:
        if value and not self.EMAIL_REGEX.match(str(value)):
            return False, self.error_message
        return True, ""


class NumericRule(ValidationRule):
    """Validation rule for numeric values."""

    def __init__(self, error_message: str = "Must be a valid number"):
        super().__init__(error_message)

    def validate(self, value: Any) -> Tuple[bool, str]:
        if value:
            try:
                float(value)
            except (ValueError, TypeError):
                return False, self.error_message
        return True, ""


class IntegerRule(ValidationRule):
    """Validation rule for integer values."""

    def __init__(self, error_message: str = "Must be a valid integer"):
        super().__init__(error_message)

    def validate(self, value: Any) -> Tuple[bool, str]:
        if value:
            try:
                int(value)
            except (ValueError, TypeError):
                return False, self.error_message
        return True, ""


class MinValueRule(ValidationRule):
    """Validation rule for minimum numeric value."""

    def __init__(self, min_value: float, error_message: Optional[str] = None):
        self.min_value = min_value
        if error_message is None:
            error_message = f"Must be at least {min_value}"
        super().__init__(error_message)

    def validate(self, value: Any) -> Tuple[bool, str]:
        if value:
            try:
                if float(value) < self.min_value:
                    return False, self.error_message
            except (ValueError, TypeError):
                return False, "Invalid number format"
        return True, ""


class MaxValueRule(ValidationRule):
    """Validation rule for maximum numeric value."""

    def __init__(self, max_value: float, error_message: Optional[str] = None):
        self.max_value = max_value
        if error_message is None:
            error_message = f"Must be no more than {max_value}"
        super().__init__(error_message)

    def validate(self, value: Any) -> Tuple[bool, str]:
        if value:
            try:
                if float(value) > self.max_value:
                    return False, self.error_message
            except (ValueError, TypeError):
                return False, "Invalid number format"
        return True, ""


class RangeRule(ValidationRule):
    """Validation rule for numeric range."""

    def __init__(self, min_value: float, max_value: float, error_message: Optional[str] = None):
        self.min_value = min_value
        self.max_value = max_value
        if error_message is None:
            error_message = f"Must be between {min_value} and {max_value}"
        super().__init__(error_message)

    def validate(self, value: Any) -> Tuple[bool, str]:
        if value:
            try:
                num_value = float(value)
                if num_value < self.min_value or num_value > self.max_value:
                    return False, self.error_message
            except (ValueError, TypeError):
                return False, "Invalid number format"
        return True, ""


class RegexRule(ValidationRule):
    """Validation rule using regular expressions."""

    def __init__(self, pattern: str, error_message: str = "Invalid format"):
        self.pattern = re.compile(pattern)
        super().__init__(error_message)

    def validate(self, value: Any) -> Tuple[bool, str]:
        if value and not self.pattern.match(str(value)):
            return False, self.error_message
        return True, ""


class DateRule(ValidationRule):
    """Validation rule for dates."""

    def __init__(self, date_format: str = "%Y-%m-%d", error_message: str = "Invalid date format"):
        self.date_format = date_format
        super().__init__(error_message)

    def validate(self, value: Any) -> Tuple[bool, str]:
        if value:
            try:
                datetime.strptime(str(value), self.date_format)
            except ValueError:
                return False, self.error_message
        return True, ""


class DateRangeRule(ValidationRule):
    """Validation rule for date ranges."""

    def __init__(self, min_date: datetime = None, max_date: datetime = None,
                 date_format: str = "%Y-%m-%d", error_message: Optional[str] = None):
        self.min_date = min_date
        self.max_date = max_date
        self.date_format = date_format

        if error_message is None:
            if min_date and max_date:
                error_message = f"Date must be between {min_date.strftime(date_format)} and {max_date.strftime(date_format)}"
            elif min_date:
                error_message = f"Date must be after {min_date.strftime(date_format)}"
            elif max_date:
                error_message = f"Date must be before {max_date.strftime(date_format)}"
            else:
                error_message = "Invalid date"

        super().__init__(error_message)

    def validate(self, value: Any) -> Tuple[bool, str]:
        if value:
            try:
                date_value = datetime.strptime(str(value), self.date_format)

                if self.min_date and date_value < self.min_date:
                    return False, self.error_message

                if self.max_date and date_value > self.max_date:
                    return False, self.error_message

            except ValueError:
                return False, "Invalid date format"

        return True, ""


class CustomRule(ValidationRule):
    """Custom validation rule using a callback function."""

    def __init__(self, validator_func: Callable[[Any], bool], error_message: str):
        """
        Initialize custom rule.

        Args:
            validator_func: Function that takes a value and returns True if valid
            error_message: Error message to display on failure
        """
        self.validator_func = validator_func
        super().__init__(error_message)

    def validate(self, value: Any) -> Tuple[bool, str]:
        try:
            if not self.validator_func(value):
                return False, self.error_message
        except Exception:
            return False, self.error_message
        return True, ""


class PasswordStrengthRule(ValidationRule):
    """Validation rule for password strength."""

    def __init__(self,
                 min_length: int = 8,
                 require_uppercase: bool = True,
                 require_lowercase: bool = True,
                 require_digit: bool = True,
                 require_special: bool = False,
                 error_message: Optional[str] = None):
        self.min_length = min_length
        self.require_uppercase = require_uppercase
        self.require_lowercase = require_lowercase
        self.require_digit = require_digit
        self.require_special = require_special

        if error_message is None:
            requirements = [f"{min_length}+ characters"]
            if require_uppercase:
                requirements.append("uppercase")
            if require_lowercase:
                requirements.append("lowercase")
            if require_digit:
                requirements.append("digit")
            if require_special:
                requirements.append("special character")
            error_message = f"Password must contain: {', '.join(requirements)}"

        super().__init__(error_message)

    def validate(self, value: Any) -> Tuple[bool, str]:
        if not value:
            return False, self.error_message

        password = str(value)

        if len(password) < self.min_length:
            return False, self.error_message

        if self.require_uppercase and not any(c.isupper() for c in password):
            return False, self.error_message

        if self.require_lowercase and not any(c.islower() for c in password):
            return False, self.error_message

        if self.require_digit and not any(c.isdigit() for c in password):
            return False, self.error_message

        if self.require_special and not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            return False, self.error_message

        return True, ""


class ValidationService:
    """
    Service for validating form data and providing validation feedback.

    Features:
    - Pre-built validation rules
    - Custom validation rules
    - Form-level validation
    - Real-time validation support
    - Database-backed admin-manageable validation rules
    """

    # Fields that support admin-manageable validation
    VALIDATABLE_FIELDS = [
        'id_cr',              # ID/CR number field
        'account_membership', # Account/Membership number field
    ]

    def __init__(self, db_manager=None, logging_service=None):
        """
        Initialize the validation service.

        Args:
            db_manager: Optional DatabaseManager instance for DB-backed validation
            logging_service: Optional LoggingService instance for logging
        """
        self.db_manager = db_manager
        self.logger = logging_service

    @staticmethod
    def validate_field(value: Any, rules: List[ValidationRule]) -> Tuple[bool, str]:
        """
        Validate a single field against multiple rules.

        Args:
            value: Value to validate
            rules: List of validation rules

        Returns:
            Tuple of (is_valid, error_message)
        """
        for rule in rules:
            is_valid, error_message = rule.validate(value)
            if not is_valid:
                return False, error_message
        return True, ""

    @staticmethod
    def validate_form(form_data: Dict[str, Any],
                     validation_rules: Dict[str, List[ValidationRule]]) -> Tuple[bool, Dict[str, str]]:
        """
        Validate an entire form.

        Args:
            form_data: Dictionary of field_name -> value
            validation_rules: Dictionary of field_name -> list of rules

        Returns:
            Tuple of (is_valid, dict of field_name -> error_message)
        """
        errors = {}
        is_valid = True

        for field_name, rules in validation_rules.items():
            value = form_data.get(field_name)
            field_valid, error_message = ValidationService.validate_field(value, rules)

            if not field_valid:
                errors[field_name] = error_message
                is_valid = False

        return is_valid, errors

    @staticmethod
    def create_report_validation_rules() -> Dict[str, List[ValidationRule]]:
        """
        Create validation rules for report forms.

        Returns:
            Dictionary of field_name -> list of validation rules
        """
        return {
            'report_number': [
                RequiredRule("Report number is required"),
                MinLengthRule(3, "Report number must be at least 3 characters"),
                MaxLengthRule(50, "Report number must be no more than 50 characters")
            ],
            'report_date': [
                RequiredRule("Report date is required"),
                DateRule("%Y-%m-%d", "Invalid date format (use YYYY-MM-DD)")
            ],
            'reported_entity_name': [
                RequiredRule("Entity name is required"),
                MinLengthRule(2, "Entity name must be at least 2 characters"),
                MaxLengthRule(200, "Entity name must be no more than 200 characters")
            ],
            'cic': [
                MaxLengthRule(50, "CIC must be no more than 50 characters")
            ],
            'transaction_amount': [
                NumericRule("Transaction amount must be a valid number"),
                MinValueRule(0, "Transaction amount must be positive")
            ],
            'nature_of_report': [
                RequiredRule("Nature of report is required"),
                MinLengthRule(10, "Please provide more details (at least 10 characters)")
            ]
        }

    @staticmethod
    def create_user_validation_rules() -> Dict[str, List[ValidationRule]]:
        """
        Create validation rules for user forms.

        Returns:
            Dictionary of field_name -> list of validation rules
        """
        return {
            'username': [
                RequiredRule("Username is required"),
                MinLengthRule(3, "Username must be at least 3 characters"),
                MaxLengthRule(50, "Username must be no more than 50 characters"),
                RegexRule(r'^[a-zA-Z0-9_]+$', "Username can only contain letters, numbers, and underscores")
            ],
            'email': [
                EmailRule("Please enter a valid email address")
            ],
            'full_name': [
                RequiredRule("Full name is required"),
                MinLengthRule(2, "Full name must be at least 2 characters"),
                MaxLengthRule(100, "Full name must be no more than 100 characters")
            ],
            'password': [
                RequiredRule("Password is required"),
                PasswordStrengthRule(min_length=8, require_uppercase=True,
                                    require_lowercase=True, require_digit=True)
            ]
        }

    # ==================================================
    # Database-backed Admin-Manageable Validation Rules
    # ==================================================

    def get_validation_rules(self, field_name: str) -> Optional[Dict]:
        """
        Get validation rules for a specific field from database.

        Args:
            field_name: Column name in column_settings table

        Returns:
            Dictionary with validation rules, or None if not found
        """
        if not self.db_manager:
            return None

        try:
            import json
            query = """
                SELECT validation_rules
                FROM column_settings
                WHERE column_name = ?
            """
            result = self.db_manager.execute_with_retry(query, (field_name,))

            if not result or not result[0][0]:
                return None

            # Parse JSON validation rules
            rules_json = result[0][0]
            return json.loads(rules_json) if rules_json else None

        except Exception as e:
            if self.logger:
                self.logger.error(f"Error getting validation rules for {field_name}: {str(e)}")
            return None

    def update_validation_rules(self, field_name: str, rules: Dict, username: str) -> Tuple[bool, str]:
        """
        Update validation rules for a field in database.

        Args:
            field_name: Column name in column_settings table
            rules: Dictionary with validation rules
            username: User performing the action

        Returns:
            Tuple of (success, message)
        """
        if not self.db_manager:
            return False, "Database manager not available"

        try:
            import json
            # Convert rules to JSON
            rules_json = json.dumps(rules)

            # Update validation rules
            update_query = """
                UPDATE column_settings
                SET validation_rules = ?, updated_at = ?, updated_by = ?
                WHERE column_name = ?
            """
            self.db_manager.execute_with_retry(
                update_query,
                (rules_json, datetime.now().isoformat(), username, field_name)
            )

            if self.logger:
                self.logger.info(f"User {username} updated validation rules for field '{field_name}'")
            return True, "Validation rules updated successfully."

        except Exception as e:
            if self.logger:
                self.logger.error(f"Error updating validation rules: {str(e)}")
            return False, f"Error updating validation rules: {str(e)}"

    def get_all_field_settings(self) -> List[Dict]:
        """
        Get all field settings including validation rules and required status.

        Returns:
            List of dictionaries with field settings
        """
        if not self.db_manager:
            return []

        try:
            import json
            query = """
                SELECT column_name, display_name_en, display_name_ar,
                       is_required, validation_rules, updated_by
                FROM column_settings
                WHERE column_name IN ('id_cr', 'account_membership')
                ORDER BY column_name
            """
            results = self.db_manager.execute_with_retry(query)

            if not results:
                return []

            fields = []
            for row in results:
                # Parse validation rules JSON
                validation_rules = None
                if row[4]:
                    try:
                        validation_rules = json.loads(row[4])
                    except:
                        validation_rules = None

                fields.append({
                    'column_name': row[0],
                    'display_name_en': row[1],
                    'display_name_ar': row[2],
                    'is_required': row[3],
                    'validation_rules': validation_rules,
                    'updated_by': row[5]
                })

            return fields

        except Exception as e:
            if self.logger:
                self.logger.error(f"Error getting all field settings: {str(e)}")
            return []

    def update_required_status(self, field_name: str, is_required: bool, username: str) -> Tuple[bool, str]:
        """
        Update required status for a field.

        Args:
            field_name: Column name in column_settings table
            is_required: Whether field is required
            username: User performing the action

        Returns:
            Tuple of (success, message)
        """
        if not self.db_manager:
            return False, "Database manager not available"

        try:
            update_query = """
                UPDATE column_settings
                SET is_required = ?, updated_at = ?, updated_by = ?
                WHERE column_name = ?
            """
            self.db_manager.execute_with_retry(
                update_query,
                (1 if is_required else 0, datetime.now().isoformat(), username, field_name)
            )

            status = "required" if is_required else "optional"
            if self.logger:
                self.logger.info(f"User {username} set field '{field_name}' as {status}")
            return True, f"Field marked as {status} successfully."

        except Exception as e:
            if self.logger:
                self.logger.error(f"Error updating required status: {str(e)}")
            return False, f"Error updating required status: {str(e)}"

    def validate_field_from_db(self, field_name: str, value: str, nationality: Optional[str] = None,
                              is_cr: bool = False, is_membership: bool = False) -> Tuple[bool, str]:
        """
        Validate a field value against database-stored validation rules.

        Args:
            field_name: Field name (id_cr or account_membership)
            value: Value to validate
            nationality: Nationality (for ID validation)
            is_cr: Whether ID/CR field is a CR number
            is_membership: Whether Account/Membership field is membership

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Get validation rules from database
            rules = self.get_validation_rules(field_name)
            if not rules:
                return True, ""  # No rules = always valid

            # Strip whitespace
            value = value.strip()

            # Check if empty (required check should be done separately)
            if not value:
                return True, ""

            # Validate based on field type
            if field_name == 'id_cr':
                return self._validate_id_cr(value, rules, nationality, is_cr)
            elif field_name == 'account_membership':
                return self._validate_account_membership(value, rules, is_membership)
            else:
                return True, ""

        except Exception as e:
            if self.logger:
                self.logger.error(f"Error validating field {field_name}: {str(e)}")
            return False, f"Validation error: {str(e)}"

    def _validate_id_cr(self, value: str, rules: Dict, nationality: Optional[str], is_cr: bool) -> Tuple[bool, str]:
        """Validate ID or CR number."""
        # Check length
        required_length = rules.get('length', 10)
        if len(value) != required_length:
            return False, f"Must be {required_length} digits"

        # Check if all digits
        pattern = rules.get('pattern', r'^[0-9]{10}$')
        if not re.match(pattern, value):
            return False, "Must contain only digits"

        # Check starting digit based on type
        if is_cr:
            # CR must start with 7
            cr_starts_with = rules.get('cr_starts_with', '7')
            if not value.startswith(cr_starts_with):
                return False, f"CR number must start with {cr_starts_with}"
        else:
            # ID - check if Saudi
            if nationality and 'Saudi' in nationality:
                saudi_starts_with = rules.get('saudi_starts_with', '1')
                if not value.startswith(saudi_starts_with):
                    return False, f"Saudi ID must start with {saudi_starts_with}"

        return True, ""

    def _validate_account_membership(self, value: str, rules: Dict, is_membership: bool) -> Tuple[bool, str]:
        """Validate Account or Membership number."""
        # Check if all digits
        if not value.isdigit():
            return False, "Must contain only digits"

        # Check length based on type
        if is_membership:
            required_length = rules.get('membership_length', 8)
            if len(value) != required_length:
                return False, f"Membership must be {required_length} digits"
        else:
            required_length = rules.get('account_length', 21)
            if len(value) != required_length:
                return False, f"Account number must be {required_length} digits"

        return True, ""

    def is_field_required(self, field_name: str) -> bool:
        """
        Check if a field is marked as required in database.

        Args:
            field_name: Column name in column_settings table

        Returns:
            True if field is required
        """
        if not self.db_manager:
            return False

        try:
            query = """
                SELECT is_required
                FROM column_settings
                WHERE column_name = ?
            """
            result = self.db_manager.execute_with_retry(query, (field_name,))

            if not result:
                return False

            return bool(result[0][0])

        except Exception as e:
            if self.logger:
                self.logger.error(f"Error checking if field is required: {str(e)}")
            return False
