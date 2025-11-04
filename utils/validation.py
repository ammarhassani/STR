"""
Input Validation Utilities
Provides comprehensive validation for all form inputs
"""
import re
from datetime import datetime
from typing import Tuple, List, Dict, Any


class ReportValidator:
    """Comprehensive report validation"""
    
    @staticmethod
    def validate_required_fields(
        data: Dict[str, Any],
        column_settings: List[Dict]
    ) -> List[str]:
        """
        Validate required fields
        
        Args:
            data: Form data dictionary
            column_settings: List of column configuration dictionaries
            
        Returns:
            List of error messages
        """
        errors = []
        
        for col in column_settings:
            if col['is_required']:
                field_name = col['column_name']
                value = data.get(field_name)
                
                if not value or (isinstance(value, str) and not value.strip()):
                    errors.append(
                        f"{col['display_name_en']} is required"
                    )
        
        return errors
    
    @staticmethod
    def validate_report_number(report_number: str) -> Tuple[bool, str]:
        """
        Validate report number format: YYYY/MM/XXX
        
        Args:
            report_number: Report number string
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not report_number:
            return False, "Report number is required"
        
        pattern = r'^\d{4}/\d{2}/\d{3}$'
        
        if not re.match(pattern, report_number):
            return False, (
                "Invalid format. Expected: YYYY/MM/XXX (e.g., 2025/11/001)"
            )
        
        # Check year is reasonable
        try:
            year = int(report_number[:4])
            current_year = datetime.now().year
            
            if year < 2000 or year > current_year + 1:
                return False, (
                    f"Year must be between 2000 and {current_year + 1}"
                )
        except ValueError:
            return False, "Invalid year in report number"
        
        return True, ""
    
    @staticmethod
    def validate_date(date_str: str) -> Tuple[bool, str]:
        """
        Validate date format DD/MM/YYYY and check not future
        
        Args:
            date_str: Date string
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not date_str:
            return False, "Date is required"
        
        try:
            date_obj = datetime.strptime(date_str, "%d/%m/%Y")
            
            # Check not future date
            if date_obj > datetime.now():
                return False, "Date cannot be in the future"
            
            return True, ""
        except ValueError:
            return False, "Invalid date format. Expected: DD/MM/YYYY"
    
    @staticmethod
    def validate_total_transaction(value: str) -> Tuple[bool, str]:
        """
        Validate total transaction format: XXXXX SAR
        
        Args:
            value: Transaction value string
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not value:
            return True, ""  # Optional field
        
        pattern = r'^\d+\s*SAR$'
        
        if not re.match(pattern, value.strip()):
            return False, (
                "Invalid format. Expected: XXXXX SAR (e.g., 605040 SAR)"
            )
        
        return True, ""
    
    @staticmethod
    def validate_reporter_initials(value: str) -> Tuple[bool, str]:
        """
        Validate reporter initials: 2 uppercase letters
        
        Args:
            value: Initials string
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not value:
            return True, ""  # Optional field
        
        pattern = r'^[A-Z]{2}$'
        
        if not re.match(pattern, value.strip()):
            return False, (
                "Invalid format. Expected: 2 uppercase letters (e.g., ZM)"
            )
        
        return True, ""
    
    @staticmethod
    def validate_serial_number(sn: int) -> Tuple[bool, str]:
        """
        Validate serial number
        
        Args:
            sn: Serial number
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            sn_int = int(sn) if not isinstance(sn, int) else sn
            
            if sn_int < 1:
                return False, "Serial number must be positive"
            
            return True, ""
        except (ValueError, TypeError):
            return False, "Serial number must be a valid integer"


def validate_required(value: Any, field_name: str) -> Tuple[bool, str]:
    """
    Validate required field
    
    Args:
        value: Field value
        field_name: Name of field for error message
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if value is None:
        return False, f"{field_name} is required"
    
    if isinstance(value, str) and not value.strip():
        return False, f"{field_name} is required"
    
    return True, ""


def validate_report_number(report_number: str) -> Tuple[bool, str]:
    """Convenience function for report number validation"""
    return ReportValidator.validate_report_number(report_number)


def validate_date(date_str: str) -> Tuple[bool, str]:
    """Convenience function for date validation"""
    return ReportValidator.validate_date(date_str)


def sanitize_input(value: str, max_length: int = None) -> str:
    """
    Sanitize user input
    
    Args:
        value: Input string
        max_length: Maximum allowed length
        
    Returns:
        Sanitized string
    """
    if value is None:
        return ""
    
    # Strip whitespace
    value = value.strip()
    
    # Limit length
    if max_length:
        value = value[:max_length]
    
    # Remove control characters (except newline, carriage return, tab)
    value = ''.join(
        char for char in value 
        if ord(char) >= 32 or char in '\n\r\t'
    )
    
    return value
