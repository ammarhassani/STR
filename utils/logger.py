"""
Logging Utilities Module
Application logging configuration
"""
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(log_level=logging.INFO) -> logging.Logger:
    """
    Configure application logging
    
    Args:
        log_level: Logging level (default: INFO)
        
    Returns:
        Configured logger instance
    """
    # Create logs directory
    log_dir = Path.home() / '.fiu_system' / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / 'application.log'
    
    # Create rotating file handler (max 10MB, keep 5 backups)
    handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    
    # Create logger
    logger = logging.getLogger('fiu_system')
    logger.setLevel(log_level)
    logger.addHandler(handler)
    
    # Also log to console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger


# Global logger instance
logger = setup_logging()


def log_info(message: str):
    """Log info message"""
    logger.info(message)


def log_error(message: str, exc_info=False):
    """Log error message"""
    logger.error(message, exc_info=exc_info)


def log_warning(message: str):
    """Log warning message"""
    logger.warning(message)


def log_debug(message: str):
    """Log debug message"""
    logger.debug(message)
