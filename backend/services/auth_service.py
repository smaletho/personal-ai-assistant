"""
Authentication module for Google API access.
Handles OAuth 2.0 flow and token management for web application.
Also provides calendar management for accessing multiple calendars within one account.
"""
import os
import json
from typing import Dict, List, Optional, Union
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleRequest
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from backend.models.database import get_db
from backend.models.user import User, OAuthToken
from backend.config.auth_config import get_google_oauth_settings, GoogleOAuthSettings
from backend.api.auth.dependencies import get_current_user

class GoogleAuth:
    """Handles authentication with Google APIs for web applications."""
    
    def __init__(self, scopes: List[str], user: Optional[User] = None, db: Optional[Session] = None):
        """
        Initialize the authentication handler.
        
        Args:
            scopes: List of API scopes needed for access
            user: Optional user object to associate credentials with
            db: Optional database session for retrieving/storing tokens
        """
        self.scopes = scopes
        self.user = user
        self.db = db
        self.credentials = None
        self.settings = get_google_oauth_settings()
    
    def authenticate(self):
        """
        Authenticate with Google API using database stored tokens.
        
        Returns:
            The authenticated credentials object
            
        Raises:
            HTTPException: If no valid credentials are available
        """
        if not self.user or not self.db:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication requires a user and database session",
            )
        
        # Check for stored token in database
        token = self.db.query(OAuthToken).filter(
            OAuthToken.user_id == self.user.id,
            OAuthToken.provider == "google"
        ).first()
        
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="No OAuth token found. Please log in with your Google account."
            )
        
        # Prepare credentials using the token
        token_info = token.to_dict()
        token_info["client_id"] = self.settings.CLIENT_ID
        token_info["client_secret"] = self.settings.CLIENT_SECRET
        
        self.credentials = Credentials(**token_info)
        
        # Refresh token if expired
        if not self.credentials.valid:
            if self.credentials.expired and self.credentials.refresh_token:
                try:
                    # Use Request from google.auth.transport.requests
                    self.credentials.refresh(GoogleRequest())
                    
                    # Update token in database
                    token.access_token = self.credentials.token
                    token.expires_at = datetime.utcnow() + timedelta(seconds=self.credentials.expires_in)
                    self.db.commit()
                except Exception as e:
                    self.db.rollback()
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail=f"Failed to refresh token: {str(e)}"
                    )
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token and no refresh token available. Please log in again."
                )
        
        return self.credentials
    
    def build_service(self, api_name, api_version):
        """
        Build and return a service for the requested API.
        
        Args:
            api_name: The name of the API (e.g., 'calendar')
            api_version: The version of the API (e.g., 'v3')
            
        Returns:
            A service object for interacting with the specified API
        """
        if not self.credentials:
            self.authenticate()
        
        return build(api_name, api_version, credentials=self.credentials)


class CalendarManager:
    """Manages Google Calendar integration with access to multiple calendars."""
    
    def __init__(self, user: Optional[User] = None, db: Optional[Session] = None):
        """
        Initialize the calendar manager.
        
        Args:
            user: User object for authentication
            db: Database session
        """
        self.user = user
        self.db = db
        self.auth = GoogleAuth(
            scopes=['https://www.googleapis.com/auth/calendar'],
            user=user,
            db=db
        )
        self.service = self.auth.build_service('calendar', 'v3')
        self.calendars_cache = None
        self.default_calendar_id = 'primary'
    
    def list_calendars(self) -> List[Dict]:
        """
        List all calendars available to the authenticated account.
        This includes calendars owned by the user and calendars shared with the user.
        
        Returns:
            List of calendar objects with id, summary, description, etc.
        """
        try:
            if self.calendars_cache is None:
                result = self.service.calendarList().list().execute()
                self.calendars_cache = result.get('items', [])
            return self.calendars_cache
        except HttpError as error:
            print(f"An error occurred listing calendars: {error}")
            raise
    
    def get_calendar(self, calendar_id: str) -> Optional[Dict]:
        """
        Get a specific calendar by ID.
        
        Args:
            calendar_id: ID of the calendar to retrieve
            
        Returns:
            Calendar object if found, None otherwise
        """
        try:
            # Try to get from cache first
            if self.calendars_cache is not None:
                for calendar in self.calendars_cache:
                    if calendar.get('id') == calendar_id:
                        return calendar
            
            # If not in cache or cache is empty, fetch directly
            return self.service.calendars().get(calendarId=calendar_id).execute()
        except HttpError as error:
            if error.status_code == 404:
                return None
            print(f"An error occurred getting calendar: {error}")
            raise
    
    def set_default_calendar(self, calendar_id: str) -> bool:
        """
        Set the default calendar ID for operations.
        
        Args:
            calendar_id: ID of the calendar to set as default
            
        Returns:
            True if successful, False if calendar not found
        """
        calendar = self.get_calendar(calendar_id)
        if calendar:
            self.default_calendar_id = calendar_id
            return True
        return False
    
    def get_calendar_by_name(self, name: str) -> Optional[Dict]:
        """
        Find a calendar by name (case-insensitive partial match).
        
        Args:
            name: Calendar name/summary to search for
            
        Returns:
            First matching calendar or None if not found
        """
        calendars = self.list_calendars()
        name_lower = name.lower()
        
        for calendar in calendars:
            summary = calendar.get('summary', '').lower()
            if name_lower in summary:
                return calendar
        
        return None
    
    def get_service(self):
        """
        Get the authenticated Google Calendar service.
        
        Returns:
            Google Calendar service object
        """
        return self.service


# Session-based calendar manager dictionary
_calendar_managers = {}

# A direct dictionary for managers created without FastAPI dependencies
_direct_calendar_managers = {}


def get_calendar_manager(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get or initialize a calendar manager for the current user.
    
    Args:
        user: Authenticated user from the session
        db: Database session
        
    Returns:
        CalendarManager instance
    """
    # Use user ID as the key in our managers dictionary
    user_id = user.id
    
    if user_id not in _calendar_managers:
        _calendar_managers[user_id] = CalendarManager(user=user, db=db)
        
    return _calendar_managers[user_id]


def get_calendar_service(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Helper function to quickly get an authenticated Google Calendar service.
    
    Args:
        user: Authenticated user from the session
        db: Database session
        
    Returns:
        A service object for the Google Calendar API
    """
    manager = get_calendar_manager(user=user, db=db)
    return manager.get_service()


def direct_get_calendar_manager(user_id: str, user_email: str = None):
    """
    Get or create a calendar manager without using FastAPI dependencies.
    This should be used when accessing from a context where FastAPI dependencies aren't available.
    
    Args:
        user_id: ID of the user to get a calendar manager for
        user_email: Optional email of the user for logging purposes
        
    Returns:
        A minimal CalendarManager instance that can handle basic calendar operations
        or None if initialization fails
    """
    if not user_id:
        print(f"[ERROR] Cannot create calendar manager without user_id")
        return None
        
    # Check if we already have a manager for this user
    if user_id in _direct_calendar_managers:
        return _direct_calendar_managers[user_id]
    
    try:
        # Create a minimal CalendarManager without database interaction
        # This is suitable for read-only operations but won't be able to refresh tokens
        manager = CalendarManager()
        manager.user_id = user_id  # Just store the ID since we don't have a User object
        
        # Set up minimal logging info
        if user_email:
            print(f"[INFO] Creating direct calendar manager for user: {user_email}")
        
        # Store in our direct managers dictionary
        _direct_calendar_managers[user_id] = manager
        return manager
    except Exception as e:
        print(f"[ERROR] Failed to create direct calendar manager: {str(e)}")
        return None


def get_tasks_service(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Helper function to quickly get an authenticated Google Tasks service.
    
    Args:
        user: Authenticated user from the session
        db: Database session
        
    Returns:
        A service object for the Google Tasks API
    """
    # Use the same auth but build a different service
    auth = GoogleAuth(
        scopes=['https://www.googleapis.com/auth/tasks'],
        user=user,
        db=db
    )
    return auth.build_service('tasks', 'v1')
