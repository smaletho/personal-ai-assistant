"""
Tests for the assistant's natural language processing and intent detection.
"""
import unittest
from unittest.mock import patch, MagicMock
import datetime
from freezegun import freeze_time

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import CalendarAssistant
from tests.test_mocks import MockCalendarService, MockTasksService


class TestAssistantIntentParsing(unittest.TestCase):
    """Test the assistant's intent parsing capabilities."""
    
    def setUp(self):
        """Set up test environment before each test."""
        # Patch Ollama
        patcher_ollama = patch('ollama.list')
        self.mock_ollama_list = patcher_ollama.start()
        self.addCleanup(patcher_ollama.stop)
        
        patcher_chat = patch('ollama.chat')
        self.mock_ollama_chat = patcher_chat.start()
        self.mock_ollama_chat.return_value = {"message": {"content": "This is a mock response from Ollama."}}
        self.addCleanup(patcher_chat.stop)
        
        # Patch Google API services
        patcher_service = patch('auth.get_calendar_service')
        self.mock_get_service = patcher_service.start()
        self.mock_service = MockCalendarService()
        self.mock_get_service.return_value = self.mock_service
        self.addCleanup(patcher_service.stop)
        
        # Patch calendar manager
        patcher_manager = patch('auth.get_calendar_manager')
        self.mock_get_manager = patcher_manager.start()
        manager_mock = MagicMock()
        manager_mock.get_account_names.return_value = ['default', 'work', 'family']
        self.mock_get_manager.return_value = manager_mock
        self.addCleanup(patcher_manager.stop)
        
        # Create the assistant
        self.assistant = CalendarAssistant()
    
    @freeze_time("2023-07-01 10:00:00")
    def test_parse_create_event_intent(self):
        """Test parsing create event intent."""
        text = "Create a meeting called Team Sync tomorrow at 2pm"
        intent = self.assistant._parse_intent(text)
        
        self.assertEqual(intent["intent"], "create_event")
        self.assertIn("parameters", intent)
        
    @freeze_time("2023-07-01 10:00:00")
    def test_parse_list_events_intent(self):
        """Test parsing list events intent."""
        text = "What's on my calendar this week?"
        intent = self.assistant._parse_intent(text)
        
        self.assertEqual(intent["intent"], "list_events")
        self.assertIn("parameters", intent)
    
    @freeze_time("2023-07-01 10:00:00")
    def test_parse_create_task_intent(self):
        """Test parsing create task intent."""
        text = "Add a task to buy groceries by tomorrow"
        intent = self.assistant._parse_intent(text)
        
        self.assertEqual(intent["intent"], "create_task")
        self.assertIn("parameters", intent)
    
    @freeze_time("2023-07-01 10:00:00")
    def test_parse_list_tasks_intent(self):
        """Test parsing list tasks intent."""
        text = "Show me my todo list"
        intent = self.assistant._parse_intent(text)
        
        self.assertEqual(intent["intent"], "list_tasks")
        self.assertIn("parameters", intent)
    
    @freeze_time("2023-07-01 10:00:00")
    def test_parse_switch_account_intent(self):
        """Test parsing switch account intent."""
        text = "Switch to my work account"
        intent = self.assistant._parse_intent(text)
        
        self.assertEqual(intent["intent"], "switch_account")
        self.assertIn("parameters", intent)
        self.assertEqual(intent["parameters"]["account_name"], "work")
    
    @freeze_time("2023-07-01 10:00:00")
    def test_parse_general_query_intent(self):
        """Test parsing general query intent."""
        text = "How's the weather today?"
        intent = self.assistant._parse_intent(text)
        
        self.assertEqual(intent["intent"], "general_query")
        self.assertIn("parameters", intent)
        self.assertEqual(intent["parameters"]["query"], "how's the weather today?")


class TestAssistantProcessing(unittest.TestCase):
    """Test the assistant's end-to-end processing capabilities."""
    
    def setUp(self):
        """Set up test environment before each test."""
        # Patch Ollama
        patcher_ollama = patch('ollama.list')
        self.mock_ollama_list = patcher_ollama.start()
        self.addCleanup(patcher_ollama.stop)
        
        patcher_chat = patch('ollama.chat')
        self.mock_ollama_chat = patcher_chat.start()
        self.mock_ollama_chat.return_value = {"message": {"content": "This is a mock response from Ollama."}}
        self.addCleanup(patcher_chat.stop)
        
        # Patch Google API services
        patcher_service = patch('auth.get_calendar_service')
        self.mock_get_service = patcher_service.start()
        self.mock_service = MockCalendarService()
        self.mock_get_service.return_value = self.mock_service
        self.addCleanup(patcher_service.stop)
        
        # Patch calendar manager
        patcher_manager = patch('auth.get_calendar_manager')
        self.mock_get_manager = patcher_manager.start()
        manager_mock = MagicMock()
        manager_mock.get_account_names.return_value = ['default', 'work', 'family']
        self.mock_get_manager.return_value = manager_mock
        self.addCleanup(patcher_manager.stop)
        
        # Mock logging to avoid file creation during tests
        patcher_logging = patch('main.logger')
        self.mock_logger = patcher_logging.start()
        self.addCleanup(patcher_logging.stop)
        
        # Create the assistant
        self.assistant = CalendarAssistant()
        
        # Mock the calendar and tasks methods
        self.assistant.calendar.create_event = MagicMock(return_value={"id": "event123", "summary": "Test Event"})
        self.assistant.calendar.list_events = MagicMock(return_value=[])
        self.assistant.tasks.create_task = MagicMock(return_value={"id": "task123", "title": "Test Task"})
        self.assistant.tasks.list_tasks = MagicMock(return_value=[])
    
    @freeze_time("2023-07-01 10:00:00")
    def test_process_create_event_request(self):
        """Test processing a request to create an event."""
        response = self.assistant.process_input("Create a team meeting for tomorrow at 2pm")
        
        # Verify event creation was attempted
        self.assistant.calendar.create_event.assert_called_once()
        
        # Response should indicate event was created
        self.assertIn("created", response.lower())
    
    @freeze_time("2023-07-01 10:00:00")
    def test_process_list_events_request(self):
        """Test processing a request to list events."""
        response = self.assistant.process_input("What's on my calendar this week?")
        
        # Verify event listing was attempted
        self.assistant.calendar.list_events.assert_called_once()
    
    @freeze_time("2023-07-01 10:00:00")
    def test_process_create_task_request(self):
        """Test processing a request to create a task."""
        response = self.assistant.process_input("Add a task to buy groceries by tomorrow")
        
        # Verify task creation was attempted
        self.assistant.tasks.create_task.assert_called_once()
        
        # Response should indicate task was created
        self.assertIn("created", response.lower())
    
    @freeze_time("2023-07-01 10:00:00")
    def test_process_switch_account_request(self):
        """Test processing a request to switch accounts."""
        self.assistant.switch_account = MagicMock(return_value=True)
        
        response = self.assistant.process_input("Switch to my work account")
        
        # Verify account switching was attempted
        self.assistant.switch_account.assert_called_once_with("work")
        
        # Response should confirm account switch
        self.assertIn("switched", response.lower())
    
    @freeze_time("2023-07-01 10:00:00")
    def test_process_general_query(self):
        """Test processing a general query that doesn't match specific intents."""
        response = self.assistant.process_input("How's the weather today?")
        
        # Verify Ollama chat was called for general query
        self.mock_ollama_chat.assert_called_once()
        
        # Response should be the mock response from Ollama
        self.assertEqual(response, "This is a mock response from Ollama.")


if __name__ == '__main__':
    unittest.main()
