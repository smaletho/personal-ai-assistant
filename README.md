# Personal AI Assistant

## Overview
This project implements a personal AI assistant that integrates with Google Calendar and Google Tasks APIs. The assistant uses LangChain and Ollama's llama3.1 model to provide a conversational interface with function calling capabilities for calendar operations and task management across multiple calendars in a single Google account.

## Features

- Google Calendar integration with multiple calendar support
  - Create, read, update, and delete calendar events
  - Check availability and schedule meetings
  - Support for multiple calendars in one account

- Google Tasks integration
  - Create, manage, and complete tasks
  - Organize with multiple task lists
  - Set due dates and track progress

- Conversational AI interface
  - Natural language understanding for calendar and task commands
  - Intelligent intent detection via function calling
  - Context-aware conversations

- Local LLM processing with Ollama
  - Privacy-focused (all processing happens locally)
  - Uses llama3.1 for function calling capabilities
  - No data sent to external servers

## AI Agent Architecture

The assistant uses a modern AI agent architecture with the following components:

- **LangChain Framework**: Provides the agent structure, tool definitions, and conversation management.
- **Ollama Integration**: Uses llama3.1 model locally for inference with function calling capabilities.
- **Function Calling**: Enables the AI to identify and call appropriate functions based on user requests.
- **Tool Registry**: Defines calendar and task operations as tools that can be invoked by the AI.
- **Conversation Memory**: Maintains context throughout the interaction session.

### Calendar and Task Tools

The agent has access to the following tools:

- **Calendar Management**
  - `list_calendars`: Display all available calendars
  - `switch_calendar`: Change to a different calendar
  - `list_events`: View upcoming events with filtering options
  - `create_event`: Schedule new calendar events

- **Task Management**
  - `list_task_lists`: Show available task lists
  - `list_tasks`: Display tasks with filtering options
  - `create_task`: Add new tasks with optional due dates

## Setup Instructions

1. **Google Cloud Setup**
   - Create a project in the [Google Cloud Console](https://console.cloud.google.com/)
   - Enable both Google Calendar API and Google Tasks API
   - Create OAuth credentials (Desktop application)
   - Download credentials as `credentials.json` and place in the project root

2. **Environment Setup**
   ```bash
   # Create and activate virtual environment
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Set up Ollama (if not already installed)
   # Follow instructions at https://github.com/ollama/ollama
   ```

3. **First Run**
   ```bash
   # Run the CLI for testing Google Calendar integration
   python cli.py
   
   # Run the CLI for testing Google Tasks integration
   python tasks_cli.py
   
   # Run the main assistant
   python main.py
   ```

## Project Structure

- **Core Modules**
  - `auth.py`: Authentication module for Google API with multi-account support
  - `google_calendar.py`: Google Calendar API wrapper
  - `google_tasks.py`: Google Tasks API wrapper
  - `main.py`: Main application with NLP integration
  - `utils.py`: Shared utility functions

- **Command-line Tools**
  - `cli.py`: Calendar operations CLI
  - `tasks_cli.py`: Tasks operations CLI

- **Testing**
  - `tests/`: Test suite directory
  - `tests/test_utils.py`: Tests for utility functions
  - `tests/test_mocks.py`: Mock objects for API testing
  - `tests/test_google_calendar.py`: Calendar API tests
  - `tests/test_google_tasks.py`: Tasks API tests
  - `tests/test_assistant.py`: Assistant integration tests

- **Configuration**
  - `requirements.txt`: Project dependencies

## Testing

The project includes a comprehensive test suite to ensure reliability.

```bash
# Install test dependencies
pip install pytest freezegun

# Run all tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_utils.py
```

## Multiple Calendar Support

The assistant supports working with multiple calendars that are shared with a single Google account. This means you can view and manage not only your own calendars but also calendars that have been shared with you (like your spouse's or family calendars).

1. **Calendar Access**
   - The application uses a single Google account authentication via OAuth
   - That account can access any calendars that are owned by or shared with it
   - You can manage calendar sharing in Google Calendar web interface

2. **Working with Different Calendars**
   - View all available calendars: `python cli.py calendars`
   - In the assistant, use natural language like: "Switch to my work calendar" or "Use my family calendar"
   - In the CLI tools, specify the calendar: `python cli.py list --calendar "Family Events"`
   - You can use either calendar IDs or names when specifying calendars

## License

MIT
