"""
Google Calendar API wrapper for CRUD operations.
"""
import datetime
import logging
from typing import Dict, List, Optional, Union
from dateutil.parser import parse
from fastapi import Depends
from sqlalchemy.orm import Session
from googleapiclient.errors import HttpError

from backend.utils.retry_utils import retry_with_backoff
from backend.models.database import get_db
from backend.models.user import User
from backend.api.auth.dependencies import get_current_user_from_token
from backend.services.auth_service import get_calendar_service, get_calendar_manager
from backend.utils.cache_manager import CacheManager

# Set up logging
logger = logging.getLogger(__name__)

class GoogleCalendar:
    """Wrapper for Google Calendar API operations."""
    
    # Class-level cache manager for calendar data
    _calendar_cache_manager = CacheManager(max_items=50, ttl_seconds=300)
    
    def __init__(self, calendar_id='primary', calendar_name=None, 
                 user: Optional[User] = None, db: Optional[Session] = None):
        """
        Initialize the Google Calendar wrapper.
        
        Args:
            calendar_id: ID of the calendar to use (default: 'primary')
            calendar_name: Name of calendar to search for and use (overrides calendar_id if provided)
            user: User object for authentication
            db: Database session
        """
        self.user = user
        self.db = db
        
        if user and db:
            self.calendar_manager = get_calendar_manager(user=user, db=db)
            self.service = self.calendar_manager.get_service()
        else:
            # Fallback for compatibility - this will likely fail in web context
            logger.warning("GoogleCalendar initialized without user and db - authentication may fail")
            self.calendar_manager = get_calendar_manager()
            self.service = self.calendar_manager.get_service()
        
        # Get available calendars for this account
        self.available_calendars = self._get_calendars_with_cache()
        
        # Set the calendar ID based on name if provided, otherwise use the given ID
        if calendar_name:
            calendar = self.calendar_manager.get_calendar_by_name(calendar_name)
            if calendar:
                self.calendar_id = calendar['id']
            else:
                # Fall back to default if name not found
                logger.warning(f"Calendar '{calendar_name}' not found. Using '{calendar_id}' instead.")
                self.calendar_id = calendar_id
        else:
            self.calendar_id = calendar_id
        
        # Verify the calendar exists to prevent issues later
        try:
            self.service.calendars().get(calendarId=self.calendar_id).execute()
        except HttpError as e:
            if e.status_code == 404:
                if self.calendar_id != 'primary':
                    logger.warning(f"Calendar ID '{self.calendar_id}' not found. Falling back to primary calendar.")
                    self.calendar_id = 'primary'
                else:
                    logger.error("Primary calendar not found. User may not have proper access.")
                    raise Exception("Primary calendar not found. Please check your Google Calendar access.")
            else:
                raise
    
    @retry_with_backoff(max_attempts=3)
    def create_event(self, 
                     summary: str, 
                     start_time: Union[str, datetime.datetime],
                     end_time: Union[str, datetime.datetime],
                     description: Optional[str] = None,
                     location: Optional[str] = None,
                     attendees: Optional[List[Dict[str, str]]] = None,
                     timezone: str = 'America/New_York') -> Dict:
        """
        Create a new calendar event.
        
        Args:
            summary: Title of the event
            start_time: Start time (datetime or ISO format string)
            end_time: End time (datetime or ISO format string)
            description: Optional description for the event
            location: Optional location for the event
            attendees: Optional list of attendees [{'email': 'person@example.com'}, ...]
            timezone: Timezone for the event (default: 'America/New_York')
            
        Returns:
            The created event object
        """
        # Convert string times to datetime if needed
        if isinstance(start_time, str):
            start_time = parse(start_time)
        if isinstance(end_time, str):
            end_time = parse(end_time)
        
        # Create event body
        event_body = {
            'summary': summary,
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': timezone,
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': timezone,
            }
        }
        
        # Add optional fields if provided
        if description:
            event_body['description'] = description
        if location:
            event_body['location'] = location
        if attendees:
            event_body['attendees'] = attendees
        
        try:
            event = self.service.events().insert(
                calendarId=self.calendar_id,
                body=event_body
            ).execute()
            return event
        except HttpError as error:
            logger.error(f"API error: {error}")
            raise
    
    @retry_with_backoff(max_attempts=3)
    def get_event(self, event_id: str) -> Dict:
        """
        Get a specific calendar event by ID.
        
        Args:
            event_id: ID of the event to retrieve
            
        Returns:
            The event object
        """
        try:
            event = self.service.events().get(
                calendarId=self.calendar_id,
                eventId=event_id
            ).execute()
            return event
        except HttpError as error:
            logger.error(f"API error: {error}")
            raise
    
    @retry_with_backoff(max_attempts=3)
    def update_event(self, 
                     event_id: str,
                     summary: Optional[str] = None, 
                     start_time: Optional[Union[str, datetime.datetime]] = None,
                     end_time: Optional[Union[str, datetime.datetime]] = None,
                     description: Optional[str] = None,
                     location: Optional[str] = None,
                     attendees: Optional[List[Dict[str, str]]] = None,
                     timezone: str = 'America/New_York') -> Dict:
        """
        Update an existing calendar event.
        
        Args:
            event_id: ID of the event to update
            summary: New title of the event (if changing)
            start_time: New start time (if changing)
            end_time: New end time (if changing)
            description: New description (if changing)
            location: New location (if changing)
            attendees: New attendees list (if changing)
            timezone: Timezone for the event (default: 'America/New_York')
            
        Returns:
            The updated event object
        """
        # First get the existing event
        try:
            event = self.service.events().get(
                calendarId=self.calendar_id, 
                eventId=event_id
            ).execute()
            
            # Update fields if provided
            if summary:
                event['summary'] = summary
                
            if start_time:
                if isinstance(start_time, str):
                    start_time = parse(start_time)
                event['start'] = {
                    'dateTime': start_time.isoformat(),
                    'timeZone': timezone
                }
                
            if end_time:
                if isinstance(end_time, str):
                    end_time = parse(end_time)
                event['end'] = {
                    'dateTime': end_time.isoformat(),
                    'timeZone': timezone
                }
                
            if description:
                event['description'] = description
                
            if location:
                event['location'] = location
                
            if attendees:
                event['attendees'] = attendees
            
            # Update the event
            updated_event = self.service.events().update(
                calendarId=self.calendar_id,
                eventId=event_id,
                body=event
            ).execute()
            
            return updated_event
            
        except HttpError as error:
            logger.error(f"API error: {error}")
            raise
    
    @retry_with_backoff(max_attempts=3)
    def delete_event(self, event_id: str) -> bool:
        """
        Delete a calendar event.
        
        Args:
            event_id: ID of the event to delete
            
        Returns:
            True if successful
        """
        try:
            self.service.events().delete(
                calendarId=self.calendar_id,
                eventId=event_id
            ).execute()
            return True
        except HttpError as error:
            logger.error(f"API error: {error}")
            raise
    
    @retry_with_backoff(max_attempts=3)
    def _get_calendars_with_cache(self):
        """Get available calendars with caching."""
        cache_key = 'all_calendars'
        
        # Check if we have a valid cached calendar list
        cached_calendars = self._calendar_cache_manager.get(cache_key)
        if cached_calendars is not None:
            logger.debug("Using cached calendar list")
            return cached_calendars
            
        # Otherwise fetch and cache calendar list
        try:
            calendar_list = self.service.calendarList().list().execute()
            calendars = calendar_list.get('items', [])
            return self._calendar_cache_manager.set(cache_key, calendars)
        except HttpError as error:
            logger.error(f"API error: {error}")
            raise
    
    @classmethod
    def _clear_cache(cls, user_id=None):
        """
        Clear all cached data.
        
        Args:
            user_id: Optional user ID to scope the cache clearing by user
        """
        cls._calendar_cache_manager.invalidate()
        logger.debug("Calendar cache cleared")
    
    @retry_with_backoff(max_attempts=3)
    def list_events(self, 
                   max_results: int = 10, 
                   time_min: Optional[Union[str, datetime.datetime]] = None,
                   time_max: Optional[Union[str, datetime.datetime]] = None,
                   query: Optional[str] = None,
                   timezone: str = 'America/New_York') -> List[Dict]:
        """
        List calendar events based on criteria.
        
        Args:
            max_results: Maximum number of events to return
            time_min: Start time for filtering (default: now)
            time_max: End time for filtering (default: none)
            query: Free text search term
            timezone: Timezone for the query (default: 'America/New_York')
            
        Returns:
            List of event objects
        """
        # Set default time_min to now if not provided
        if time_min is None:
            time_min = datetime.datetime.utcnow()
        
        # Convert string times to datetime if needed
        if isinstance(time_min, str):
            time_min = parse(time_min)
        if time_max and isinstance(time_max, str):
            time_max = parse(time_max)
        
        # Format parameters for API call
        params = {
            'calendarId': self.calendar_id,
            'maxResults': max_results,
            'timeMin': time_min.isoformat() + 'Z',  # 'Z' indicates UTC time
            'singleEvents': True,
            'orderBy': 'startTime'
        }
        
        if time_max:
            params['timeMax'] = time_max.isoformat() + 'Z'
        
        if query:
            params['q'] = query
        
        try:
            events_result = self.service.events().list(**params).execute()
            events = events_result.get('items', [])
            return events
        except HttpError as error:
            logger.error(f"API error: {error}")
            raise
    
    @retry_with_backoff(max_attempts=3)
    def get_free_busy(self, 
                     start_time: Union[str, datetime.datetime],
                     end_time: Union[str, datetime.datetime],
                     timezone: str = 'America/New_York') -> Dict:
        """
        Get free/busy information for the calendar.
        
        Args:
            start_time: Start time for the query
            end_time: End time for the query
            timezone: Timezone for the query (default: 'America/New_York')
            
        Returns:
            Free/busy information
        """
        # Convert string times to datetime if needed
        if isinstance(start_time, str):
            start_time = parse(start_time)
        if isinstance(end_time, str):
            end_time = parse(end_time)
        
        body = {
            "timeMin": start_time.isoformat(),
            "timeMax": end_time.isoformat(),
            "timeZone": timezone,
            "items": [{"id": self.calendar_id}]
        }
        
        try:
            freebusy = self.service.freebusy().query(body=body).execute()
            return freebusy
        except HttpError as error:
            logger.error(f"API error: {error}")
            raise
