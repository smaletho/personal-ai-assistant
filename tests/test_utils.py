"""
Unit tests for utility functions.
"""
import unittest
import datetime
from freezegun import freeze_time

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import format_datetime, to_rfc3339, format_date_for_display, extract_dates_from_text, ApiError


class TestDateFunctions(unittest.TestCase):
    """Test date handling utility functions."""
    
    def test_format_datetime_string(self):
        """Test formatting datetime from string."""
        dt_str = "2023-05-15T10:30:00"
        dt_obj = format_datetime(dt_str)
        self.assertEqual(dt_obj.year, 2023)
        self.assertEqual(dt_obj.month, 5)
        self.assertEqual(dt_obj.day, 15)
        self.assertEqual(dt_obj.hour, 10)
        self.assertEqual(dt_obj.minute, 30)
    
    def test_format_datetime_object(self):
        """Test formatting datetime from datetime object."""
        original_dt = datetime.datetime(2023, 5, 15, 10, 30)
        dt_obj = format_datetime(original_dt)
        self.assertEqual(dt_obj, original_dt)
    
    def test_to_rfc3339_from_string(self):
        """Test converting string to RFC 3339 format."""
        dt_str = "2023-05-15T10:30:00"
        rfc_str = to_rfc3339(dt_str)
        self.assertTrue(rfc_str.endswith('Z'))
    
    def test_to_rfc3339_from_datetime(self):
        """Test converting datetime to RFC 3339 format."""
        dt_obj = datetime.datetime(2023, 5, 15, 10, 30)
        rfc_str = to_rfc3339(dt_obj)
        self.assertTrue(rfc_str.endswith('Z'))
    
    def test_format_date_for_display(self):
        """Test formatting date for human-readable display."""
        dt_str = "2023-05-15T10:30:00"
        display = format_date_for_display(dt_str)
        self.assertEqual(display, "2023-05-15 10:30")
    
    @freeze_time("2023-05-15 10:30:00")
    def test_extract_dates_from_text(self):
        """Test extracting dates from text."""
        text = "Schedule a meeting tomorrow"
        start_time, end_time = extract_dates_from_text(text)
        
        # This is testing the placeholder implementation
        self.assertEqual(start_time.year, 2023)
        self.assertEqual(start_time.month, 5)
        self.assertEqual(start_time.day, 15)
        
        # End time should be start_time + 1 hour
        self.assertEqual(end_time, start_time + datetime.timedelta(hours=1))


class TestApiError(unittest.TestCase):
    """Test ApiError exception."""
    
    def test_api_error_init(self):
        """Test ApiError initialization."""
        error = ApiError("Test error", 404, {"reason": "Not found"})
        self.assertEqual(str(error), "Test error")
        self.assertEqual(error.status_code, 404)
        self.assertEqual(error.details, {"reason": "Not found"})
    
    def test_api_error_default_values(self):
        """Test ApiError with default values."""
        error = ApiError("Test error")
        self.assertEqual(str(error), "Test error")
        self.assertIsNone(error.status_code)
        self.assertEqual(error.details, {})


if __name__ == '__main__':
    unittest.main()
