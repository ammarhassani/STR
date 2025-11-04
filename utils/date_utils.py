"""Date formatting and parsing utilities"""
from datetime import datetime
from typing import Optional


def format_date(date_obj: datetime, format_str: str = "%d/%m/%Y") -> str:
    """
    Format datetime object to string
    
    Args:
        date_obj: datetime object
        format_str: Format string (default: DD/MM/YYYY)
        
    Returns:
        Formatted date string
    """
    if date_obj is None:
        return ""
    
    try:
        return date_obj.strftime(format_str)
    except Exception:
        return ""


def parse_date(date_str: str, format_str: str = "%d/%m/%Y") -> Optional[datetime]:
    """
    Parse date string to datetime object
    
    Args:
        date_str: Date string
        format_str: Format string (default: DD/MM/YYYY)
        
    Returns:
        datetime object or None if invalid
    """
    if not date_str:
        return None
    
    try:
        return datetime.strptime(date_str, format_str)
    except ValueError:
        return None


def get_current_date(format_str: str = "%d/%m/%Y") -> str:
    """
    Get current date as formatted string
    
    Args:
        format_str: Format string (default: DD/MM/YYYY)
        
    Returns:
        Current date string
    """
    return datetime.now().strftime(format_str)


def get_current_datetime() -> str:
    """Get current datetime in ISO format"""
    return datetime.now().isoformat()
