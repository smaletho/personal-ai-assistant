"""
Authentication configuration for Google OAuth.
"""
import os
from typing import Dict, List, Optional
from pydantic_settings import BaseSettings
from backend.config.env import get_env_variable, validate_env


class GoogleOAuthSettings(BaseSettings):
    """Settings for Google OAuth."""
    
    # Google OAuth client credentials
    # These are loaded from environment variables
    CLIENT_ID: str = get_env_variable("GOOGLE_CLIENT_ID", "")
    CLIENT_SECRET: str = get_env_variable("GOOGLE_CLIENT_SECRET", "")
    
    # OAuth endpoints
    AUTHORIZATION_ENDPOINT: str = "https://accounts.google.com/o/oauth2/auth"
    TOKEN_ENDPOINT: str = "https://oauth2.googleapis.com/token"
    USERINFO_ENDPOINT: str = "https://www.googleapis.com/oauth2/v3/userinfo"
    
    # OAuth scopes required for the app
    SCOPES: List[str] = [
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/tasks"
    ]
    
    # Redirect URI for the OAuth callback
    # This MUST match exactly what's configured in the Google OAuth console
    REDIRECT_URI: str = get_env_variable(
        "OAUTH_REDIRECT_URI", 
        "http://localhost:3000/auth/callback"
    )
    
    # JWT settings for session tokens
    JWT_SECRET: str = get_env_variable(
        "JWT_SECRET", 
        "temporary_secret_key_change_in_production"
    )
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRES_MINUTES: int = 60 * 24  # 24 hours
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "allow",  # Allow extra fields from environment variables
    }


# Create an instance of the settings
google_oauth_settings = GoogleOAuthSettings()


def get_google_oauth_settings() -> GoogleOAuthSettings:
    """
    Get the Google OAuth settings.
    This function is provided as a dependency for FastAPI routes.
    """
    return google_oauth_settings
