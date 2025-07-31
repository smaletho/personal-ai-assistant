"""
Unit tests for Google Calendar API wrapper.
"""
import unittest
from unittest.mock import patch, MagicMock
import datetime
from freezegun import freeze_time

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google_calendar import GoogleCalendar
from tests.test_mocks import MockCalendarService


class TestGoogleCalendar(unittest.TestCase):
    """Test the GoogleCalendar class."""
    
    def setUp(self):
        """Set up test environment before each test."""
        self.mock_service = MockCalendarService()
        patcher = patch('auth.get_calendar_service')
        self.mock_get_service = patcher.start()
        self.mock_get_service.return_value = self.mock_service
        self.addCleanup(patcher.stop)
        
        self.calendar = GoogleCalendar(calendar_id='primary')
    
    def test_init(self):
        """Test initialization of GoogleCalendar."""
        self.assertEqual(self.calendar.calendar_id, 'primary')
        self.mock_get_service.assert_called_once()
    
    def test_create_event(self):
        """Test creating a calendar event."""
        start_time = datetime.datetime(2023, 7, 10, 10, 0)
        end_time = datetime.datetime(2023, 7, 10, 11, 0)
        
        event = self.calendar.create_event(
            summary="Test Event",
            start_time=start_time,
            end_time=end_time,
            description="Test Description",
            location="Test Location"
        )
        
        self.assertIsNotNone(event)
        self.assertTrue('id' in event)
        self.assertEqual(event.get('summary'), "Test Event")
    
    def test_get_event(self):
        """Test getting a calendar event."""
        # First create an event
        start_time = datetime.datetime(2023, 7, 10, 10, 0)
        end_time = datetime.datetime(2023, 7, 10, 11, 0)
        event = self.calendar.create_event(
            summary="Test Event",
            start_time=start_time,
            end_time=end_time
        )
        event_id = event.get('id')
        
        # Now get the event
        retrieved_event = self.calendar.get_event(event_id)
        
        self.assertEqual(retrieved_event.get('id'), event_id)
        self.assertEqual(retrieved_event.get('summary'), "Test Event")
    
    def test_update_event(self):
        """Test updating a calendar event."""
        # First create an event
        start_time = datetime.datetime(2023, 7, 10, 10, 0)
        end_time = datetime.datetime(2023, 7, 10, 11, 0)
        event = self.calendar.create_event(
            summary="Test Event",
            start_time=start_time,
            end_time=end_time
        )
        event_id = event.get('id')
        
        # Now update the event
        updated_event = self.calendar.update_event(
            event_id=event_id,
            summary="Updated Event",
            location="New Location"
        )
        
        self.assertEqual(updated_event.get('id'), event_id)
        self.assertEqual(updated_event.get('summary'), "Updated Event")
        self.assertEqual(updated_event.get('location'), "New Location")
    
    def test_delete_event(self):
        """Test deleting a calendar event."""
        # First create an event
        start_time = datetime.datetime(2023, 7, 10, 10, 0)
        end_time = datetime.datetime(2023, 7, 10, 11, 0)
        event = self.calendar.create_event(
            summary="Test Event",
            start_time=start_time,
            end_time=end_time
        )
        event_id = event.get('id')
        
        # Now delete the event
        result = self.calendar.delete_event(event_id)
        
        self.assertTrue(result)
        
        # Try to get the deleted event - should raise an exception
        with self.assertRaises(Exception):
            self.calendar.get_event(event_id)
    
    @freeze_time("2023-07-01")
    def test_list_events(self):
        """Test listing calendar events."""
        # Add some events first
        self.calendar.create_event(
            summary="Event 1",
            start_time=datetime.datetime(2023, 7, 2, 10, 0),
            end_time=datetime.datetime(2023, 7, 2, 11, 0)
        )
        self.calendar.create_event(
            summary="Event 2",
            start_time=datetime.datetime(2023, 7, 3, 14, 0),
            end_time=datetime.datetime(2023, 7, 3, 15, 0)
        )
        
        # List events
        events = self.calendar.list_events(max_results=10)
        
        self.assertIsInstance(events, list)
        self.assertTrue(len(events) >= 2)
    
    def test_get_free_busy(self):
        """Test getting free/busy information."""
        start_time = datetime.datetime(2023, 7, 1, 9, 0)
        end_time = datetime.datetime(2023, 7, 1, 17, 0)
        
        result = self.calendar.get_free_busy(
            start_time=start_time,
            end_time=end_time
        )
        
        self.assertIn('calendars', result)
        self.assertIn(self.calendar.calendar_id, result['calendars'])
        self.assertIn('busy', result['calendars'][self.calendar.calendar_id])


if __name__ == '__main__':
    unittest.main()
