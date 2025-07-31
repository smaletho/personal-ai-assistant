"""
Centralized logging configuration module.
Provides consistent logging setup across all application modules.
"""
import os
import logging
from typing import Optional


def configure_logger(
    name: str,
    log_file: Optional[str] = None,
    level: int = logging.INFO,
    format_str: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
):
    """
    Configure and return a logger with consistent settings.
    
    Args:
        name: Logger name
        log_file: Path to log file (default: name + '.log')
        level: Logging level (default: INFO)
        format_str: Log message format string
        
    Returns:
        Configured logger instance
    """
    # Use name as log file if not specified
    if log_file is None:
        log_file = f"{name}.log"
    
    # Get logger instance
    logger = logging.getLogger(name)
    
    # Skip configuration if logger already has handlers to avoid duplicates
    if logger.handlers:
        return logger
        
    logger.setLevel(level)
    
    # Create formatter
    formatter = logging.Formatter(format_str)
    
    # Add file handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger
    

def get_logger(name: str, **kwargs):
    """
    Get a configured logger by name.
    
    This is the main function to use throughout the application.
    
    Args:
        name: Logger name (usually __name__)
        **kwargs: Additional arguments to pass to configure_logger
        
    Returns:
        Configured logger instance
    """
    return configure_logger(name, **kwargs)
