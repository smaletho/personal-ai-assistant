"""
Authentication module initializer.
"""
from backend.api.auth.dependencies import get_current_user_from_token, get_optional_user

# Export the dependencies
__all__ = ['get_current_user_from_token', 'get_optional_user']
