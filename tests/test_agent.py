"""
Tests for the LangChain agent implementation.
"""
import unittest
from unittest.mock import patch, MagicMock, Mock

import pytest
from langchain.agents import AgentExecutor
from langchain_core.tools import Tool

from agent import AgentCalendarAssistant
from google_calendar import GoogleCalendar
from google_tasks import GoogleTasks


class TestAgentCalendarAssistant(unittest.TestCase):
    """Test the LangChain agent implementation."""
    
    @patch('agent.get_calendar_manager')
    @patch('agent.GoogleCalendar')
    @patch('agent.GoogleTasks')
    @patch('agent.ChatOllama')
    def setUp(self, mock_chat_ollama, mock_google_tasks, mock_google_calendar, mock_get_calendar_manager):
        """Set up test fixtures."""
        # Configure mocks
        self.mock_calendar_manager = MagicMock()
        self.mock_calendar_manager.list_calendars.return_value = [
            {'id': 'primary', 'summary': 'Primary Calendar'},
            {'id': 'family', 'summary': 'Family Calendar'}
        ]
        mock_get_calendar_manager.return_value = self.mock_calendar_manager
        
        self.mock_calendar = mock_google_calendar.return_value
        self.mock_tasks = mock_google_tasks.return_value
        self.mock_llm = mock_chat_ollama.return_value
        
        # Create assistant for testing
        self.assistant = AgentCalendarAssistant(model_name="test_model")
    
    def test_initialization(self):
        """Test that the assistant initializes correctly."""
        self.assertIsNotNone(self.assistant)
        self.assertIsNotNone(self.assistant.tools)
        self.assertIsNotNone(self.assistant.agent)
        self.assertEqual(self.assistant.current_calendar_id, 'primary')
    
    def test_create_tools(self):
        """Test that tools are created correctly."""
        tools = self.assistant._create_tools()
        
        # Check that all expected tools are present
        tool_names = [tool.name for tool in tools]
        expected_tools = [
            'list_calendars', 
            'switch_calendar', 
            'list_events',
            'create_event',
            'list_task_lists',
            'list_tasks',
            'create_task'
        ]
        
        for expected_tool in expected_tools:
            self.assertIn(expected_tool, tool_names)
        
        # Check tool count
        self.assertEqual(len(tools), len(expected_tools))
        
        # Verify all tools are Tool instances
        for tool in tools:
            self.assertIsInstance(tool, Tool)
    
    @patch('agent.create_openai_tools_agent')
    def test_create_agent(self, mock_create_agent):
        """Test agent creation."""
        # Configure mock
        mock_agent = MagicMock()
        mock_create_agent.return_value = mock_agent
        
        # Call method
        agent_executor = self.assistant._create_agent()
        
        # Verify agent executor is created
        self.assertIsInstance(agent_executor, AgentExecutor)
        
        # Verify agent was created with tools
        mock_create_agent.assert_called_once()
        
        # Extract args
        _, kwargs = mock_create_agent.call_args
        
        # Check llm was passed
        self.assertEqual(kwargs.get('llm'), self.mock_llm)
        
        # Check tools were passed
        self.assertEqual(kwargs.get('tools'), self.assistant.tools)
        
        # Check prompt was passed
        self.assertIsNotNone(kwargs.get('prompt'))
    
    def test_list_calendars(self):
        """Test list_calendars tool."""
        # Configure mock
        expected_result = "Here are your available calendars:\n- Primary Calendar\n- Family Calendar\n\nCurrently using: Primary Calendar"
        
        # Call method
        result = self.assistant._list_calendars()
        
        # Verify result
        self.assertEqual(result, expected_result)
    
    @patch('agent.parse')
    def test_create_event(self, mock_parse):
        """Test create_event tool."""
        # Configure mocks
        start_time_str = "2025-06-25 10:00"
        end_time_str = "2025-06-25 11:00"
        
        import datetime
        mock_start = datetime.datetime(2025, 6, 25, 10, 0)
        mock_end = datetime.datetime(2025, 6, 25, 11, 0)
        mock_parse.side_effect = [mock_start, mock_end]
        
        self.mock_calendar_manager.list_calendars.return_value = [
            {'id': 'primary', 'summary': 'Primary Calendar'}
        ]
        
        mock_event = {
            'id': 'event123',
            'summary': 'Test Meeting',
            'start': {'dateTime': '2025-06-25T10:00:00'},
            'end': {'dateTime': '2025-06-25T11:00:00'}
        }
        self.mock_calendar.create_event.return_value = mock_event
        
        # Call method
        result = self.assistant._create_event(
            summary="Test Meeting",
            start_time=start_time_str,
            end_time=end_time_str,
            description="Test Description",
            location="Conference Room"
        )
        
        # Verify mock calls
        self.mock_calendar.create_event.assert_called_with(
            summary="Test Meeting",
            start_time=mock_start,
            end_time=mock_end,
            description="Test Description",
            location="Conference Room"
        )
        
        # Verify result contains correct information
        self.assertIn("Test Meeting", result)
        self.assertIn("created successfully", result)
        self.assertIn("Primary Calendar", result)
    
    @patch('agent.parse')
    def test_switch_calendar(self, mock_parse):
        """Test switch_calendar tool."""
        # Configure mocks
        self.mock_calendar_manager.list_calendars.return_value = [
            {'id': 'primary', 'summary': 'Primary Calendar'},
            {'id': 'family', 'summary': 'Family Calendar'}
        ]
        
        # Call method
        result = self.assistant._switch_calendar(calendar_name="Family")
        
        # Verify new calendar instance was created
        self.mock_calendar_manager.get_calendar_by_name.assert_called()
        self.assertEqual(self.assistant.current_calendar_id, 'family')
        self.assertIn("Switched to calendar: Family Calendar", result)


@pytest.mark.asyncio
async def test_async_agent_execution():
    """Test async execution of the agent."""
    with patch('agent.get_calendar_manager'), \
         patch('agent.GoogleCalendar'), \
         patch('agent.GoogleTasks'), \
         patch('agent.ChatOllama'), \
         patch('agent.AgentExecutor'):
         
        # Create assistant with mocked components
        assistant = AgentCalendarAssistant(model_name="test_model")
        
        # Mock process_input method
        assistant.agent.invoke = MagicMock(return_value={"output": "Event created successfully!"})
        
        # Call process_input method
        result = assistant.process_input("Create a meeting tomorrow at 3pm")
        
        # Verify result
        assert result == "Event created successfully!"
        assistant.agent.invoke.assert_called_once()
        

if __name__ == '__main__':
    unittest.main()
