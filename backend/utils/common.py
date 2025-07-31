"""
Utility functions for the personal AI assistant.
Contains shared functionality used across multiple modules.
"""
import datetime
from typing import Dict, List, Optional, Tuple, Union
from dateutil.parser import parse


def format_datetime(dt_value: Union[str, datetime.datetime], timezone: str = 'America/New_York') -> datetime.datetime:
    """
    Format and standardize datetime objects.
    
    Args:
        dt_value: Datetime as string or datetime object
        timezone: Timezone to use
        
    Returns:
        Standardized datetime object
    """
    if isinstance(dt_value, str):
        dt_obj = parse(dt_value)
    else:
        dt_obj = dt_value
        
    return dt_obj


def to_rfc3339(dt_value: Union[str, datetime.datetime]) -> str:
    """
    Convert a datetime to RFC 3339 format required by Google APIs.
    
    Args:
        dt_value: Datetime as string or datetime object
        
    Returns:
        RFC 3339 formatted datetime string
    """
    dt_obj = format_datetime(dt_value)
    
    # Format to RFC 3339
    rfc3339 = dt_obj.isoformat()
    
    # Add Z if no timezone specified
    if '+' not in rfc3339 and 'Z' not in rfc3339:
        rfc3339 += 'Z'
        
    return rfc3339


def format_date_for_display(dt_value: Union[str, datetime.datetime]) -> str:
    """
    Format a date for human-readable display.
    
    Args:
        dt_value: Datetime as string or datetime object
        
    Returns:
        Human-readable date string
    """
    dt_obj = format_datetime(dt_value)
    return dt_obj.strftime("%Y-%m-%d %H:%M")


def extract_dates_from_text(text: str) -> Tuple[Optional[datetime.datetime], Optional[datetime.datetime]]:
    """
    Extract start and end dates from natural language text using dateparser.
    Recognizes common time range patterns and returns appropriate datetime objects.
    
    Args:
        text: Natural language text containing date references
        
    Returns:
        Tuple of (start_time, end_time) as datetime objects
    """
    import re
    import dateparser
    import logging
    
    logger = logging.getLogger(__name__)
    
    if not text:
        # Default fallback for empty text
        now = datetime.datetime.now()
        start_time = now.replace(microsecond=0)
        end_time = start_time + datetime.timedelta(hours=1)
        return start_time, end_time
        
    # Common patterns for date/time extraction
    time_patterns = [
        # "from X to Y" pattern
        r'from\s+(.+?)\s+to\s+(.+?)(?:\s|$|\.|,)',
        # "between X and Y" pattern
        r'between\s+(.+?)\s+and\s+(.+?)(?:\s|$|\.|,)',
        # "X to Y" or "X until Y" pattern
        r'([^\s]+(?:\s+[^\s]+){0,3})\s*(?:-|to|until)\s*([^\s]+(?:\s+[^\s]+){0,3})(?:\s|$|\.|,)'
    ]
    
    # Settings for dateparser to prefer future dates and be more flexible
    parse_settings = {
        'PREFER_DATES_FROM': 'future',
        'DATE_ORDER': 'MDY',  # Month-Day-Year for US format
        'PREFER_DAY_OF_MONTH': 'current',
        'RELATIVE_BASE': datetime.datetime.now()
    }
    
    # First try to extract date ranges using patterns
    for pattern in time_patterns:
        matches = re.search(pattern, text, re.IGNORECASE)
        if matches:
            start_text = matches.group(1).strip()
            end_text = matches.group(2).strip()
            
            logger.debug(f"Found date pattern match: '{start_text}' to '{end_text}'")
            
            # Parse the extracted text into datetime objects
            start_time = dateparser.parse(start_text, settings=parse_settings)
            end_time = dateparser.parse(end_text, settings=parse_settings)
            
            if start_time and end_time:
                # Ensure end_time is after start_time
                if end_time <= start_time:
                    # If parsing resulted in end time before start time,
                    # assume it's the same day but later time
                    if end_time.time() > start_time.time():
                        end_time = start_time.replace(
                            hour=end_time.hour, 
                            minute=end_time.minute, 
                            second=end_time.second
                        )
                    else:
                        # Otherwise, add a default duration (1 hour)
                        end_time = start_time + datetime.timedelta(hours=1)
                
                return start_time, end_time
    
    # If no pattern matched, try to find a single date/time
    possible_date = dateparser.parse(text, settings=parse_settings)
    
    if possible_date:
        logger.debug(f"Found single date: {possible_date}")
        # Default to 1 hour duration if only one time is found
        start_time = possible_date
        end_time = start_time + datetime.timedelta(hours=1)
        return start_time, end_time
    
    # If all else fails, fall back to current time + 1hr
    logger.debug(f"No dates found in: '{text}', using current time")
    now = datetime.datetime.now()
    start_time = now.replace(microsecond=0)
    end_time = start_time + datetime.timedelta(hours=1)
    
    return start_time, end_time


class ApiError(Exception):
    """Custom exception for API errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, details: Optional[Dict] = None):
        """
        Initialize API error.
        
        Args:
            message: Error message
            status_code: HTTP status code if applicable
            details: Additional error details
        """
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)
