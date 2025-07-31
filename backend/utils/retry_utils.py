"""
Retry utilities for API calls with exponential backoff.
"""
import functools
import logging
import random
import time
from typing import Callable, Type, Optional, List, Union, Any

# Set up logging
logger = logging.getLogger(__name__)

def retry_with_backoff(
    max_attempts: int = 3,
    retryable_exceptions: List[Type[Exception]] = None,
    retriable_status_codes: List[int] = None,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
    backoff_factor: float = 2.0
):
    """
    Decorator for retrying API calls with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        retryable_exceptions: List of exception types to retry on
        retriable_status_codes: List of status codes to retry on (for HttpError-like exceptions)
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        backoff_factor: Multiplier for delay after each retry
        
    Usage:
        @retry_with_backoff(max_attempts=3)
        def make_api_call():
            # Function that might fail temporarily
            pass
        
    Returns:
        Decorated function with retry logic
    """
    # Default to common exceptions if none provided
    if retryable_exceptions is None:
        # Don't import at module level to avoid circular imports
        from googleapiclient.errors import HttpError
        retryable_exceptions = [ConnectionError, TimeoutError, HttpError]
        
    # Default to common retriable status codes if none provided
    if retriable_status_codes is None:
        # 429: Too Many Requests, 500-504: Server errors
        retriable_status_codes = [429, 500, 501, 502, 503, 504]
        
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    # Check if this exception is one we should retry
                    should_retry = False
                    
                    # Check if it's a retryable exception type
                    if any(isinstance(e, ex_type) for ex_type in retryable_exceptions):
                        # For HttpError-like exceptions, check if status code is retryable
                        if hasattr(e, 'status_code') and retriable_status_codes:
                            if e.status_code in retriable_status_codes:
                                should_retry = True
                            else:
                                # Non-retryable status code
                                raise
                        # For HttpError with resp object
                        elif hasattr(e, 'resp') and hasattr(e.resp, 'status') and retriable_status_codes:
                            if e.resp.status in retriable_status_codes:
                                should_retry = True
                            else:
                                # Non-retryable status code
                                raise
                        else:
                            # Retryable exception without status code
                            should_retry = True
                    
                    if not should_retry or attempt == max_attempts - 1:
                        # If not retryable or this is the last attempt, re-raise
                        raise
                    
                    # Calculate delay with exponential backoff and jitter
                    delay = min(base_delay * (backoff_factor ** attempt) + random.uniform(0, 0.5), max_delay)
                    
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_attempts} for {func.__name__} failed "
                        f"with {type(e).__name__}: {str(e)}. Retrying in {delay:.2f}s"
                    )
                    
                    time.sleep(delay)
            
            # This should never happen, but just in case
            if last_exception:
                raise last_exception
            
        return wrapper
    
    return decorator
