# AI Calendar Assistant API Documentation

## Overview

This documentation covers the REST API and WebSocket endpoints for the AI Calendar Assistant. The API provides access to conversational AI capabilities, Google Calendar integration, and Google Tasks management through both REST endpoints and real-time WebSocket connections.

## Table of Contents

- [Getting Started](#getting-started)
- [Authentication](#authentication)
- [REST Endpoints](#rest-endpoints)
  - [Root Endpoint](#root-endpoint)
  - [Chat Endpoint](#chat-endpoint)
  - [Calendar Endpoints](#calendar-endpoints)
  - [Task Endpoints](#task-endpoints)
- [WebSocket Communication](#websocket-communication)
  - [Connection](#connection)
  - [Message Format](#message-format)
  - [Message Types](#message-types)
  - [Typing Indicators](#typing-indicators)
  - [Error Handling](#error-handling)
- [Data Models](#data-models)
- [Example Usage](#example-usage)

## Getting Started

### Prerequisites

- Python 3.8+
- FastAPI
- Uvicorn
- Ollama with llama3.1 model
- Google OAuth credentials in `credentials.json`

### Running the Server

```bash
python -m uvicorn api:app --reload
```

The server will start on http://localhost:8000 by default. Interactive API documentation is available at:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Authentication

Currently, the API does not implement authentication. For production use, consider implementing OAuth2 or API keys for secure access.

The API does use session IDs to maintain conversation context, but these are not authenticated. In a production environment, you should implement proper authentication and session management.

## REST Endpoints

### Root Endpoint

**GET /**

Returns basic information about the API.

```http
GET /
```

**Response**:

```json
{
  "status": "ok",
  "message": "AI Calendar Assistant API is running",
  "version": "1.0.0",
  "docs_url": "/docs",
  "endpoints": {
    "chat": "/chat",
    "websocket": "/ws/{session_id}",
    "calendars": "/calendars",
    "events": "/events",
    "tasks": "/tasks"
  }
}
```

### Chat Endpoint

**POST /chat**

Send a message to the AI assistant.

```http
POST /chat
```

**Request Body**:

```json
{
  "message": "What meetings do I have today?",
  "session_id": "user123"
}
```

**Response**:

```json
{
  "response": "You have a team meeting at 2:00 PM and a doctor's appointment at 4:30 PM today.",
  "session_id": "user123"
}
```

### Calendar Endpoints

**GET /calendars**

List available calendars.

```http
GET /calendars?session_id=user123
```

**Response**:

```json
{
  "calendars": [
    {
      "id": "primary",
      "summary": "John Doe",
      "description": "Personal Calendar",
      "timeZone": "America/New_York"
    },
    {
      "id": "work@group.calendar.google.com",
      "summary": "Work Calendar",
      "description": "Work-related events",
      "timeZone": "America/New_York"
    }
  ]
}
```

**GET /events**

List calendar events.

```http
GET /events?calendar_id=primary&max_results=10&session_id=user123
```

**Optional Parameters**:

- `calendar_id`: Calendar ID (default: "primary")
- `max_results`: Maximum number of events to return (default: 10)
- `time_min`: Start time for events (ISO format)
- `time_max`: End time for events (ISO format)

**Response**:

```json
{
  "events": [
    {
      "id": "event123",
      "summary": "Team Meeting",
      "description": "Weekly team sync",
      "start": {
        "dateTime": "2025-06-22T14:00:00-04:00",
        "timeZone": "America/New_York"
      },
      "end": {
        "dateTime": "2025-06-22T15:00:00-04:00",
        "timeZone": "America/New_York"
      },
      "location": "Conference Room 3"
    }
  ]
}
```

**POST /events**

Create a calendar event.

```http
POST /events?session_id=user123
```

**Request Body**:

```json
{
  "summary": "Project Review",
  "start_time": "2025-06-23T10:00:00-04:00",
  "end_time": "2025-06-23T11:00:00-04:00",
  "description": "Review project milestones",
  "location": "Virtual Meeting",
  "calendar_id": "primary"
}
```

**Response**:

```json
{
  "event": {
    "id": "event456",
    "summary": "Project Review",
    "description": "Review project milestones",
    "start": {
      "dateTime": "2025-06-23T10:00:00-04:00",
      "timeZone": "America/New_York"
    },
    "end": {
      "dateTime": "2025-06-23T11:00:00-04:00",
      "timeZone": "America/New_York"
    },
    "location": "Virtual Meeting",
    "htmlLink": "https://www.google.com/calendar/event?eid=..."
  }
}
```

### Task Endpoints

**GET /tasks**

List tasks from a task list.

```http
GET /tasks?tasklist_id=@default&session_id=user123
```

**Optional Parameters**:

- `tasklist_id`: Task list ID (if not specified, uses the default list)

**Response**:

```json
{
  "tasks": [
    {
      "id": "task123",
      "title": "Complete API documentation",
      "notes": "Include all endpoints and examples",
      "due": "2025-06-23T23:59:59Z",
      "status": "needsAction"
    }
  ]
}
```

**POST /tasks**

Create a task.

```http
POST /tasks?session_id=user123
```

**Request Body**:

```json
{
  "title": "Review pull request",
  "notes": "Check the new feature implementation",
  "due_date": "2025-06-24T17:00:00Z",
  "tasklist_id": "@default"
}
```

**Response**:

```json
{
  "task": {
    "id": "task456",
    "title": "Review pull request",
    "notes": "Check the new feature implementation",
    "due": "2025-06-24T17:00:00Z",
    "status": "needsAction"
  }
}
```

## WebSocket Communication

### Connection

Connect to the WebSocket endpoint to establish a real-time chat session:

```
ws://localhost:8000/ws/{session_id}
```

Where `{session_id}` is a unique identifier for the user session. This can be any string, but should be consistent for the same user session.

### Message Format

**Sending Messages:**

```json
{
  "content": "What's my schedule for today?",
  "message_id": "msg123",
  "role": "user"
}
```

- `content`: The message text
- `message_id` (optional): A unique identifier for the message
- `role` (optional): Default is "user"

**Receiving Messages:**

```json
{
  "type": "message",
  "content": "Today you have a meeting at 2 PM with the design team.",
  "message_id": "msg123",
  "role": "assistant",
  "timestamp": "2025-06-22T17:30:45.123456"
}
```

### Message Types

The API sends messages with the following types:

- `message`: Regular message from the assistant
- `error`: Error message
- `typing`: Typing indicator
- `system`: System message (connection status, etc.)

### Typing Indicators

The server sends typing indicators to provide feedback while the assistant is processing:

```json
// Typing started
{
  "type": "typing",
  "content": true
}

// Typing stopped
{
  "type": "typing",
  "content": false
}
```

### Error Handling

WebSocket error messages follow this format:

```json
{
  "type": "error",
  "content": "Error message describing what went wrong",
  "message_id": "msg123"
}
```

## Data Models

### Message Request

```json
{
  "message": "string",
  "session_id": "string (optional)"
}
```

### Message Response

```json
{
  "response": "string",
  "session_id": "string"
}
```

### Chat Message

```json
{
  "content": "string",
  "role": "user|assistant",
  "timestamp": "ISO datetime string (optional)",
  "message_id": "string (optional)"
}
```

### Calendar Event Request

```json
{
  "summary": "string",
  "start_time": "ISO datetime string",
  "end_time": "ISO datetime string",
  "description": "string (optional)",
  "location": "string (optional)",
  "calendar_id": "string (optional, default: primary)"
}
```

### Task Request

```json
{
  "title": "string",
  "notes": "string (optional)",
  "due_date": "ISO datetime string (optional)",
  "tasklist_id": "string (optional)"
}
```

## Example Usage

### REST API Example (JavaScript)

```javascript
// Example: Send a chat message
async function sendChatMessage(message, sessionId) {
  const response = await fetch('http://localhost:8000/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      message: message,
      session_id: sessionId
    }),
  });
  return await response.json();
}

// Example: List calendar events
async function getEvents(sessionId) {
  const response = await fetch(`http://localhost:8000/events?session_id=${sessionId}`);
  return await response.json();
}
```

### WebSocket Example (JavaScript)

```javascript
// Connect to WebSocket
const sessionId = 'user123'; // Can be any unique identifier for the session
const socket = new WebSocket(`ws://localhost:8000/ws/${sessionId}`);

// Connection opened
socket.onopen = (event) => {
  console.log('Connected to AI Assistant');
  
  // Send a message
  const message = {
    content: "What meetings do I have today?",
    message_id: generateUUID(), // Function to generate a unique ID
    role: "user"
  };
  socket.send(JSON.stringify(message));
};

// Listen for messages
socket.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  switch (data.type) {
    case 'message':
      console.log(`Assistant: ${data.content}`);
      break;
    case 'typing':
      if (data.content) {
        console.log('Assistant is typing...');
      } else {
        console.log('Assistant stopped typing.');
      }
      break;
    case 'error':
      console.error(`Error: ${data.content}`);
      break;
    case 'system':
      console.info(`System: ${data.content}`);
      break;
  }
};

// Connection closed
socket.onclose = (event) => {
  if (event.wasClean) {
    console.log(`Connection closed cleanly, code=${event.code}, reason=${event.reason}`);
  } else {
    console.error('Connection died');
  }
};

// Handle errors
socket.onerror = (error) => {
  console.error(`WebSocket error: ${error.message}`);
};

// Helper function to generate UUID
function generateUUID() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}
```

### Python WebSocket Client Example

```python
import asyncio
import websockets
import json
import uuid

async def chat_with_assistant():
    session_id = "user456"  # Unique session identifier
    uri = f"ws://localhost:8000/ws/{session_id}"
    
    async with websockets.connect(uri) as websocket:
        print("Connected to AI Assistant")
        
        # Send a message
        message = {
            "content": "What's my schedule for tomorrow?",
            "message_id": str(uuid.uuid4()),
            "role": "user"
        }
        await websocket.send(json.dumps(message))
        
        # Receive and process messages
        while True:
            response = await websocket.recv()
            data = json.loads(response)
            
            if data["type"] == "message":
                print(f"Assistant: {data['content']}")
            elif data["type"] == "typing":
                if data["content"]:
                    print("Assistant is typing...")
                else:
                    print("Assistant stopped typing.")
            elif data["type"] == "error":
                print(f"Error: {data['content']}")
            elif data["type"] == "system":
                print(f"System: {data['content']}")

asyncio.run(chat_with_assistant())
```
