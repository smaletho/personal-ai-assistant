"""
Helper module for CLI tools to handle calendar selection.
"""
from typing import Dict, Optional
from auth import get_calendar_manager


def get_calendar_id_from_name(calendar_name: str) -> Optional[str]:
    """
    Get a calendar ID from a name.
    
    Args:
        calendar_name: Name or partial name of the calendar
        
    Returns:
        Calendar ID if found, None otherwise
    """
    manager = get_calendar_manager()
    calendars = manager.list_calendars()
    
    # Try exact match first
    for calendar in calendars:
        if calendar.get('summary', '').lower() == calendar_name.lower():
            return calendar.get('id')
    
    # Try partial match
    for calendar in calendars:
        if calendar_name.lower() in calendar.get('summary', '').lower():
            return calendar.get('id')
    
    return None


def get_calendar_by_id_or_name(value: str) -> Dict:
    """
    Get a calendar by its ID or name.
    
    Args:
        value: Calendar ID or name to look up
        
    Returns:
        Calendar object with ID and displayable name
    """
    manager = get_calendar_manager()
    
    # Try direct ID lookup first
    calendar = manager.get_calendar(value)
    if calendar:
        return {
            'id': calendar.get('id'),
            'name': calendar.get('summary', 'Unknown')
        }
    
    # Try by name
    calendar_id = get_calendar_id_from_name(value)
    if calendar_id:
        calendar = manager.get_calendar(calendar_id)
        if calendar:
            return {
                'id': calendar.get('id'),
                'name': calendar.get('summary', 'Unknown')
            }
    
    # If all else fails, return primary
    return {
        'id': 'primary',
        'name': 'Primary Calendar'
    }


def list_available_calendars():
    """
    Get a list of all available calendars.
    
    Returns:
        List of calendar objects with ID and name
    """
    manager = get_calendar_manager()
    calendars = manager.list_calendars()
    
    return [
        {
            'id': cal.get('id'),
            'name': cal.get('summary', 'Unknown')
        }
        for cal in calendars
    ]
