#!/usr/bin/env python
"""
Agent implementation using llama3.1 model with tool and function calling capabilities.
Extends the functionality of the personal AI assistant with more advanced LLM features.
Includes token usage tracking for monitoring API consumption.
"""
import os
import json
import datetime
import time
from typing import Dict, List, Optional, Tuple, Any, Union, Callable

# External dependencies
import ollama
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from dotenv import load_dotenv
from googleapiclient.errors import HttpError

# Project modules
from backend.services.calendar_service import GoogleCalendar
from backend.services.tasks_service import GoogleTasks
from backend.services.auth_service import direct_get_calendar_manager
from backend.utils.logging_config import get_logger

# Load environment variables
load_dotenv()

# Setup logging using centralized configuration
logger = get_logger("agent")

# Constants
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")

# Token Usage Tracking
class TokenUsageTracker:
    """Track token usage across different API calls"""
    
    def __init__(self):
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_tokens = 0
        self.calls = 0
        self.last_call_tokens = {}
        
    def track_usage(self, response, messages=None):
        """Extract and track token usage from Ollama API response"""
        self.calls += 1
        
        # Extract usage info - Ollama structures this differently than OpenAI
        prompt_tokens = 0
        completion_tokens = 0
        total_tokens = 0
        
        # Debug log the response structure
        logger.debug(f"Token tracking response: {type(response)}")
        if isinstance(response, dict):
            logger.debug(f"Response keys: {list(response.keys())}")
        
        # Check if it's the newer Ollama format
        if isinstance(response, dict):
            # Ollama response format changed across versions
            # Try to get token counts from all possible locations
            
            # Try 'total_duration' format first (newer Ollama versions)
            if 'prompt_eval_count' in response:
                prompt_tokens = int(response.get('prompt_eval_count', 0))
                logger.debug(f"Found prompt_eval_count: {prompt_tokens}")
                
            if 'eval_count' in response:
                completion_tokens = int(response.get('eval_count', 0))
                logger.debug(f"Found eval_count: {completion_tokens}")
                
            # Try 'done' boolean format
            if 'done' in response and isinstance(response.get('done'), bool):
                if 'prompt_eval_count' in response:
                    prompt_tokens = int(response.get('prompt_eval_count', 0))
                    logger.debug(f"Found prompt_eval_count in 'done' format: {prompt_tokens}")
                if 'eval_count' in response:
                    completion_tokens = int(response.get('eval_count', 0))
                    logger.debug(f"Found eval_count in 'done' format: {completion_tokens}")
                    
            # Try usage format (more like OpenAI)
            if 'usage' in response and isinstance(response['usage'], dict):
                usage = response['usage']
                if 'prompt_tokens' in usage:
                    prompt_tokens = int(usage.get('prompt_tokens', 0))
                    logger.debug(f"Found usage.prompt_tokens: {prompt_tokens}")
                if 'completion_tokens' in usage:
                    completion_tokens = int(usage.get('completion_tokens', 0))
                    logger.debug(f"Found usage.completion_tokens: {completion_tokens}")
                if 'total_tokens' in usage:
                    total_tokens = int(usage.get('total_tokens', 0))
                    logger.debug(f"Found usage.total_tokens: {total_tokens}")
                    
            # Get total_duration if available
            if 'total_duration' in response:
                duration_ms = int(response.get('total_duration', 0))
                logger.debug(f"Response processing duration: {duration_ms} ms")    
        
        # If we still have zero counts, estimate based on content length
        if prompt_tokens == 0 and completion_tokens == 0:
            # Estimate tokens from input/output length
            # Approximate using the ~4 chars per token for English text heuristic
            
            # Estimate prompt tokens from messages
            if messages is not None:
                prompt_text = ""
                for msg in messages:
                    if isinstance(msg, dict) and "content" in msg:
                        prompt_text += msg.get("content", "")
                prompt_tokens = max(1, len(prompt_text) // 4)
                logger.debug(f"Estimated prompt tokens from message length: {prompt_tokens}")
            
            # Estimate completion tokens from response
            if isinstance(response, dict) and 'message' in response:
                if isinstance(response['message'], dict) and 'content' in response['message']:
                    msg_content = response['message']['content']
                    completion_tokens = max(1, len(msg_content) // 4)
                    logger.debug(f"Estimated completion tokens from response length: {completion_tokens}")
            
            logger.info(f"Using estimated token counts as Ollama API did not return token usage information")
        
        # Calculate total tokens
        if total_tokens == 0:
            total_tokens = prompt_tokens + completion_tokens
            
        # Store last call info
        self.last_call_tokens = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens
        }
        
        # Update running totals
        self.total_prompt_tokens += self.last_call_tokens["prompt_tokens"]
        self.total_completion_tokens += self.last_call_tokens["completion_tokens"]
        self.total_tokens += self.last_call_tokens["total_tokens"]
        
        return self.last_call_tokens
    
    def log_usage(self, call_type=""):
        """Log the token usage information"""
        if self.last_call_tokens:
            logger.info(
                f"Token Usage [{call_type}]: "
                f"Prompt: {self.last_call_tokens['prompt_tokens']}, "
                f"Completion: {self.last_call_tokens['completion_tokens']}, "
                f"Total: {self.last_call_tokens['total_tokens']}"
            )
    
    def get_summary(self):
        """Get a summary of all token usage"""
        return {
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_tokens,
            "total_calls": self.calls,
            "average_tokens_per_call": self.total_tokens / self.calls if self.calls > 0 else 0
        }
    
    def log_summary(self):
        """Log a summary of all token usage"""
        summary = self.get_summary()
        logger.info(
            f"Token Usage Summary: "
            f"Total Calls: {summary['total_calls']}, "
            f"Total Tokens: {summary['total_tokens']} "
            f"(Prompt: {summary['total_prompt_tokens']}, "
            f"Completion: {summary['total_completion_tokens']}), "
            f"Average per call: {summary['average_tokens_per_call']:.1f}"
        )

# Default system prompt for the agent
def get_default_system_prompt():
    """Generate a system prompt with current date and time and detailed timeframe definitions"""
    # Get current date and time in user's timezone
    now = datetime.datetime.now()
    current_date_str = now.strftime("%A, %B %d, %Y")
    current_time_str = now.strftime("%I:%M %p")
    timezone_str = datetime.datetime.now().astimezone().tzname()
    
    # Calculate date ranges for this week, next week, etc.
    today = now.date()
    day_of_week = today.weekday()  # Monday is 0, Sunday is 6
    
    # Calculate the start date of the current week (Monday)
    start_of_week = today - datetime.timedelta(days=day_of_week)
    end_of_week = start_of_week + datetime.timedelta(days=6)  # Sunday
    
    # Calculate next week
    start_of_next_week = start_of_week + datetime.timedelta(days=7) 
    end_of_next_week = end_of_week + datetime.timedelta(days=7)
    
    # Calculate this month
    current_month = today.month
    current_year = today.year
    
    # Format time references with date ranges
    this_week_str = f"{start_of_week.strftime('%B %d')} to {end_of_week.strftime('%B %d, %Y')}"
    next_week_str = f"{start_of_next_week.strftime('%B %d')} to {end_of_next_week.strftime('%B %d, %Y')}"
    this_month_str = f"{datetime.date(current_year, current_month, 1).strftime('%B %Y')}"
    
    # Format with current date/time context and all time references
    return f"""
You are an intelligent personal assistant with calendar and task management capabilities.
You can help with scheduling events, managing tasks, checking availability, and more.

CURRENT TIME REFERENCE:
- Current date: {current_date_str}
- Current time: {current_time_str} ({timezone_str})

TIME FRAME DEFINITIONS (Always use these specific definitions):
- "Today" means {current_date_str}
- "Tomorrow" means {(today + datetime.timedelta(days=1)).strftime('%A, %B %d, %Y')}
- "This week" means the period from {this_week_str}
- "Next week" means the period from {next_week_str}
- "This month" means {this_month_str}
- "Next month" means {datetime.date(current_year if current_month < 12 else current_year + 1, current_month % 12 + 1, 1).strftime('%B %Y')}

USER CONFIRMATION WORKFLOW:
For all calendar and task operations that modify data (create, update, delete):
1. I will NOT make immediate changes to the user's calendar or tasks
2. Instead, I will propose the action and request confirmation
3. The user will review, possibly edit, and then confirm the action before it's executed
4. I should clearly explain what I'm suggesting but mention it requires confirmation

When interpreting user requests or displaying calendar information:
1. Always use the current date and time as reference point
2. Be precise about which time frame events belong to
3. Never describe an event occurring today as happening in a future time frame
4. Always verify the actual date of events before categorizing them as "this week" or "next week"

You have access to Google Calendar and Tasks tools to help manage the user's schedule.
Use these tools effectively and respond in a helpful, concise manner.
"""

# This is only a fallback and will be replaced by the generated prompt
DEFAULT_SYSTEM_PROMPT = ""


class Agent:
    """
    Advanced agent using llama3.1 model with tool and function calling capabilities.
    Integrates with Google Calendar and Tasks APIs for schedule management.
    """
    
    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        system_prompt: str = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        user = None,
        db = None
    ):
        """
        Initialize the agent with model parameters and API connections.
        
        Args:
            model_name: Name of the Ollama model to use (default: llama3)
            system_prompt: System prompt to guide model behavior
            temperature: Temperature for sampling (0.0-1.0)
            max_tokens: Maximum tokens for model response
            user: Optional User object for authenticated calendar access
            db: Optional database session for token management
        """
        # Model parameters
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Store user and db for service initialization
        self.user = user
        self.db = db
        
        # Generate or use provided system prompt
        if not system_prompt:
            system_prompt = get_default_system_prompt()
        self.system_prompt = system_prompt
        
        # Rich console for CLI output
        self.console = Console()
        
        # Set up conversation history
        self.conversation_history = [
            {"role": "system", "content": system_prompt}
        ]
        
        # Token usage tracking
        self.token_tracker = TokenUsageTracker()
        
        # Initialize API connections
        try:
            # Initialize calendar API with authenticated user if available
            if user and db and hasattr(user, 'id'):
                # Use direct_get_calendar_manager with actual user ID and email
                self.calendar_manager = direct_get_calendar_manager(
                    user_id=user.id,
                    user_email=user.email
                )
                if self.calendar_manager:
                    logger.info(f"Calendar manager initialized for user: {user.email}")
            else:
                # Fallback to minimal initialization for unauthenticated use
                self.calendar_manager = direct_get_calendar_manager(
                    user_id="default",
                    user_email="default@example.com"
                )
                if self.calendar_manager:
                    logger.info("Calendar manager initialized with default credentials (limited functionality)")
                
            # Initialize tasks API similarly - will be expanded for future task integration
            self.tasks_service = None
                
        except Exception as e:
            logger.error(f"Failed to initialize calendar and tasks services: {str(e)}")
            self.calendar_manager = None
            self.tasks_service = None
            
        # Register available tools
        logger.info(f"Ollama is running. Using model: {model_name}")
        self.tools = self._register_tools()
        
        # Get available calendars for this account
        if self.calendar_manager:
            self.available_calendars = self.calendar_manager.list_calendars()
        
        # Initialize tools for function calling
        self.tools = self._register_tools()
        
        # Check if Ollama is running
        try:
            ollama.list()
            logger.info(f"Ollama is running. Using model: {model_name}")
        except Exception as e:
            logger.error(f"Error connecting to Ollama: {e}")
            self.console.print(Panel(
                "[bold red]Error:[/bold red] Could not connect to Ollama.\n\n"
                "Please make sure Ollama is installed and running on your system. "
                "Visit https://github.com/ollama/ollama for installation instructions.",
                title="Ollama Connection Error",
                border_style="red"
            ))
            raise
    
    def _register_tools(self) -> List[Dict[str, Any]]:
        """
        Register all available tools for function calling capabilities.
        
        Returns:
            List of tool definitions in the OpenAI-compatible format
        """
        tools = [
            # Calendar operations
            {
                "type": "function",
                "function": {
                    "name": "list_calendars",
                    "description": "List all available calendars for the user's Google account",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "switch_calendar",
                    "description": "Switch to a different calendar in the user's Google account",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "calendar_name": {
                                "type": "string",
                                "description": "Name or ID of the calendar to switch to"
                            }
                        },
                        "required": ["calendar_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_events",
                    "description": "List events from the calendar for a specified time range",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "time_range": {
                                "type": "string",
                                "description": "Time range to list events for (today, tomorrow, this week, next week, upcoming)",
                                "enum": ["today", "tomorrow", "this week", "next week", "upcoming"]
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum number of events to return"
                            }
                        },
                        "required": ["time_range"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_event",
                    "description": "Create a new event in the calendar",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "summary": {
                                "type": "string",
                                "description": "Title of the event"
                            },
                            "start_time": {
                                "type": "string",
                                "description": "Start time of the event in ISO format (YYYY-MM-DDTHH:MM:SS)"
                            },
                            "end_time": {
                                "type": "string",
                                "description": "End time of the event in ISO format (YYYY-MM-DDTHH:MM:SS)"
                            },
                            "description": {
                                "type": "string",
                                "description": "Description of the event"
                            },
                            "location": {
                                "type": "string",
                                "description": "Location of the event"
                            }
                        },
                        "required": ["summary", "start_time", "end_time"]
                    }
                }
            },
            # Task operations
            {
                "type": "function",
                "function": {
                    "name": "list_task_lists",
                    "description": "List all available task lists for the user's Google account",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_task",
                    "description": "Create a new task in the specified task list",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "Title of the task"
                            },
                            "notes": {
                                "type": "string",
                                "description": "Notes or description for the task"
                            },
                            "due_date": {
                                "type": "string",
                                "description": "Due date for the task in YYYY-MM-DD format"
                            },
                            "tasklist_id": {
                                "type": "string",
                                "description": "ID of the task list to add the task to (default: primary)"
                            }
                        },
                        "required": ["title"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_tasks",
                    "description": "List tasks from a specified task list",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "tasklist_id": {
                                "type": "string",
                                "description": "ID of the task list to get tasks from (default: primary)"
                            },
                            "completed": {
                                "type": "boolean",
                                "description": "Whether to include completed tasks"
                            }
                        },
                        "required": []
                    }
                }
            }
        ]
        
        return tools
    
    def _execute_function(self, function_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a called function with the provided arguments or return a proposed change for confirmation.
        For write operations (create, update, delete), this will return a proposed change that requires user confirmation.
        For read operations, it will execute the function directly and return the result.
        
        Args:
            function_name: Name of the function to execute
            arguments: Arguments to pass to the function
            
        Returns:
            Result of the function execution for read operations,
            or a description of the proposed change for write operations
        """
        # Helper function to safely extract data from events
        def safe_get_event_data(event):
            # Check if event is a valid dictionary
            if not isinstance(event, dict):
                logger.warning(f"Event is not a dictionary: {event}")
                return {
                    "id": f"unknown_{datetime.datetime.now().timestamp()}",
                    "summary": "(Unknown event)",
                    "start": datetime.datetime.now().isoformat(),
                    "end": datetime.datetime.now().isoformat(),
                    "is_all_day": False,
                    "location": "",
                    "description": ""
                }
        logger.info(f"Executing function: {function_name} with arguments: {arguments}")
        
        # Define which operations require confirmation (all write operations)
        write_operations = {
            # Calendar write operations
            "create_event": "Create Calendar Event",
            "update_event": "Update Calendar Event", 
            "delete_event": "Delete Calendar Event",
            # Task write operations
            "create_task": "Create Task",
            "update_task": "Update Task",
            "delete_task": "Delete Task",
            "complete_task": "Complete Task"
        }
        
        # Check if this is a write operation that requires confirmation
        requires_confirmation = function_name in write_operations
        if requires_confirmation:
            logger.info(f"Write operation detected: {function_name}. Preparing confirmation request.")
        
        try:
            # Calendar operations
            if function_name == "list_calendars":
                calendars = self.calendar_manager.list_calendars()
                calendar_info = []
                for cal in calendars:
                    calendar_info.append({
                        "id": cal.get("id"),
                        "summary": cal.get("summary"),
                        "description": cal.get("description", ""),
                        "primary": cal.get("primary", False)
                    })
                return {"calendars": calendar_info}
            
            elif function_name == "switch_calendar":
                calendar_name = arguments.get("calendar_name")
                
                # Find calendar by ID or name
                calendar_found = None
                for calendar in self.available_calendars:
                    if calendar.get("id") == calendar_name:
                        calendar_found = calendar
                        break
                
                # If not found by ID, try to find by name
                if not calendar_found:
                    calendar_name_lower = calendar_name.lower()
                    for calendar in self.available_calendars:
                        summary = calendar.get("summary", "").lower()
                        if calendar_name_lower in summary:
                            calendar_found = calendar
                            break
                
                # Switch to the calendar if found
                if calendar_found:
                    self.current_calendar_id = calendar_found["id"]
                    self.calendar = GoogleCalendar(calendar_id=self.current_calendar_id)
                    return {
                        "success": True,
                        "calendar": {
                            "id": calendar_found.get("id"),
                            "summary": calendar_found.get("summary")
                        }
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Calendar '{calendar_name}' not found."
                    }
            
            elif function_name == "list_events":
                logger.debug(f"Starting list_events with arguments: {arguments}")
                time_range = arguments.get("time_range", "upcoming")
                max_results = arguments.get("max_results", 10)
                
                # Make sure max_results is an integer
                if isinstance(max_results, str):
                    try:
                        max_results = int(max_results)
                        logger.debug(f"Converted max_results string '{arguments.get('max_results')}' to int: {max_results}")
                    except ValueError:
                        logger.warning(f"Invalid max_results value '{max_results}', defaulting to 10")
                        max_results = 10
                
                # Calculate time range boundaries
                now = datetime.datetime.utcnow()
                logger.debug(f"Using time range: {time_range}, max_results: {max_results}")
                
                if time_range == "today":
                    time_min = now.replace(hour=0, minute=0, second=0, microsecond=0)
                    time_max = time_min + datetime.timedelta(days=1)
                elif time_range == "tomorrow":
                    time_min = now.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
                    time_max = time_min + datetime.timedelta(days=1)
                elif time_range == "this week":
                    time_min = now
                    time_max = now + datetime.timedelta(days=7)
                elif time_range == "next week":
                    time_min = now + datetime.timedelta(days=7)
                    time_max = time_min + datetime.timedelta(days=7)
                else:  # upcoming
                    time_min = now
                    time_max = None
                
                # Get events from calendar
                logger.debug(f"Fetching events with time_min={time_min}, time_max={time_max}, max_results={max_results}")
                try:
                    events = self.calendar.list_events(
                        max_results=max_results,
                        time_min=time_min,
                        time_max=time_max
                    )
                    logger.debug(f"Retrieved {len(events)} events from calendar API")
                    # Debug log the first event's structure
                    if events and len(events) > 0:
                        logger.debug(f"First event structure: {events[0]}")
                    else:
                        logger.debug("No events returned from calendar API")
                except Exception as e:
                    logger.error(f"Error fetching events from calendar: {e}")
                    # Return an error response rather than crashing
                    return {"error": f"Failed to fetch calendar events: {str(e)}", "events": []}
                
                # Format events for response
                logger.debug("Starting to format events")
                formatted_events = []
                for i, event in enumerate(events):
                    logger.debug(f"Processing event {i}")
                    try:
                        # Log the raw event for debugging
                        logger.debug(f"Raw event {i}: {event}")
                        
                        # Check if event has required start/end structure
                        if not isinstance(event, dict):
                            logger.warning(f"Event at index {i} is not a dictionary: {type(event)}")
                            continue
                            
                        # Log all keys in the event
                        logger.debug(f"Event {i} keys: {list(event.keys()) if isinstance(event, dict) else 'Not a dict'}")
                            
                        if "start" not in event or "end" not in event:
                            logger.warning(f"Event at index {i} missing start/end: {event}")
                            continue
                        
                        # Safe extraction of start/end times
                        start_data = event.get("start", {})
                        end_data = event.get("end", {})
                        
                        if not isinstance(start_data, dict) or not isinstance(end_data, dict):
                            logger.warning(f"Event start/end not dictionaries: {event}")
                            continue
                            
                        # Get datetime or date from start/end
                        start = start_data.get("dateTime", start_data.get("date", ""))
                        end = end_data.get("dateTime", end_data.get("date", ""))
                        
                        # Skip events with missing time data
                        if not start or not end:
                            logger.warning(f"Event missing start/end times: {event}")
                            continue
                        
                        is_all_day = "date" in start_data and "dateTime" not in start_data
                        
                        # Check ID explicitly and log it
                        try:
                            if "id" in event:
                                event_id = event["id"] 
                                logger.debug(f"Found event ID: {event_id}")
                            else:
                                event_id = f"event_{i}_{datetime.datetime.now().timestamp()}"
                                logger.debug(f"Generated fallback ID: {event_id}")
                        except Exception as e:
                            logger.error(f"Error accessing event ID: {e}")
                            event_id = f"error_{i}_{datetime.datetime.now().timestamp()}"
                        
                        try:
                            new_event = {
                                "id": event_id,
                                "summary": event.get("summary", "(No title)"),
                                "start": start,
                                "end": end,
                                "is_all_day": is_all_day,
                                "location": event.get("location", ""),
                                "description": event.get("description", "")
                            }
                            logger.debug(f"Created formatted event: {new_event}")
                            formatted_events.append(new_event)
                        except Exception as e:
                            logger.error(f"Error creating formatted event dict: {e}")
                    except Exception as e:
                        logger.error(f"Error processing event at index {i}: {e}")
                        continue
                
                # Create final result
                try:
                    result = {
                        "time_range": time_range,
                        "events": formatted_events
                    }
                    logger.debug(f"Returning result with {len(formatted_events)} events")
                    return result
                except Exception as e:
                    logger.error(f"Error creating result dictionary: {e}")
                    return {"error": f"Error formatting events: {str(e)}", "events": []}
            
            elif function_name == "create_event":
                summary = arguments.get("summary")
                start_time_str = arguments.get("start_time")
                end_time_str = arguments.get("end_time")
                description = arguments.get("description", "")
                location = arguments.get("location", "")
                
                # Parse ISO datetime strings with validation for future dates
                try:
                    start_time = datetime.datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
                    end_time = datetime.datetime.fromisoformat(end_time_str.replace("Z", "+00:00"))
                    
                    # Check if date is in the past - this would indicate a date parsing issue
                    now = datetime.datetime.now(datetime.timezone.utc)
                    if start_time < now - datetime.timedelta(days=1):  # Allow some flexibility for timezone differences
                        logger.warning(f"Event start time {start_time} is in the past. Current time: {now}")
                        # Adjust to tomorrow at the same time if date is incorrect
                        tomorrow = now + datetime.timedelta(days=1)
                        # Keep the time but change the date
                        start_time = datetime.datetime.combine(
                            tomorrow.date(),
                            start_time.time(),
                            tzinfo=start_time.tzinfo or datetime.timezone.utc
                        )
                        # Adjust end time to maintain the same duration
                        duration = end_time - datetime.datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
                        end_time = start_time + duration
                        logger.info(f"Adjusted event time to tomorrow: {start_time} to {end_time}")
                except Exception as e:
                    logger.error(f"Error parsing event dates: {e}")
                    # Fallback to current time + 1 day
                    now = datetime.datetime.now(datetime.timezone.utc)
                    start_time = now + datetime.timedelta(days=1)
                    end_time = start_time + datetime.timedelta(hours=1)
                
                # Format the date/time for display
                start_str = start_time.strftime("%A, %B %d, %Y at %I:%M %p")
                end_str = end_time.strftime("%I:%M %p")
                
                # Instead of creating the event directly, return a confirmation request
                if requires_confirmation:
                    return {
                        "requires_confirmation": True,
                        "operation": "create_event",
                        "action_title": "Create Calendar Event",  
                        "summary": f"Would you like to create a calendar event titled '{summary}'?",
                        "details": {
                            "summary": summary,
                            "start_time": start_time.isoformat(),
                            "end_time": end_time.isoformat(),
                            "description": description,
                            "location": location,
                            "calendar_id": self.calendar.calendar_id
                        },
                        "display": {
                            "title": summary,
                            "date": start_time.strftime("%A, %B %d, %Y"),
                            "time": f"{start_time.strftime('%I:%M %p')} - {end_time.strftime('%I:%M %p')}",
                            "description": description if description else "None provided",
                            "location": location if location else "None specified"
                        }
                    }
                
                # This code would only execute if requires_confirmation is False (which shouldn't happen)
                event = self.calendar.create_event(
                    summary=summary,
                    start_time=start_time,
                    end_time=end_time,
                    description=description,
                    location=location
                )
                
                return {
                    "message": f"Event '{summary}' has been created successfully.",
                    "start": start_str,
                    "end": end_str,
                    "description": description if description else "None provided",
                    "location": location if location else "None specified",
                    "calendar": self.calendar.calendar_id
                }
            
            elif function_name == "list_task_lists":
                task_lists = self.tasks.list_task_lists()
                formatted_lists = [
                    {"id": tl["id"], "title": tl["title"]} 
                    for tl in task_lists
                ]
                
                return {"task_lists": formatted_lists}
            
            elif function_name == "create_task":
                title = arguments.get("title")
                notes = arguments.get("notes", "")
                due_date_str = arguments.get("due_date")
                tasklist_id = arguments.get("tasklist_id", "@default")
                
                # Format due date if provided
                due_str = None
                if due_date_str:
                    # Convert YYYY-MM-DD to RFC 3339 format
                    due_date = datetime.datetime.strptime(due_date_str, "%Y-%m-%d")
                    due_str = due_date.isoformat() + "Z"
                
                # Create task
                task = self.tasks.create_task(
                    title=title,
                    notes=notes,
                    due=due_str,
                    tasklist_id=tasklist_id
                )
                
                return {
                    "success": True,
                    "task": {
                        "id": task["id"],
                        "title": task.get("title"),
                        "due": task.get("due", "")
                    }
                }
            
            elif function_name == "list_tasks":
                tasklist_id = arguments.get("tasklist_id", "@default")
                completed = arguments.get("completed", False)
                
                # Get tasks
                tasks = self.tasks.list_tasks(
                    tasklist_id=tasklist_id,
                    completed=completed
                )
                
                # Format tasks for response
                formatted_tasks = []
                for task in tasks:
                    formatted_tasks.append({
                        "id": task["id"],
                        "title": task.get("title", "(Untitled)"),
                        "notes": task.get("notes", ""),
                        "due": task.get("due", ""),
                        "status": task.get("status", "")
                    })
                
                return {"tasks": formatted_tasks}
            
            # If function is not recognized
            return {"error": f"Unknown function: {function_name}"}
            
        except Exception as e:
            logger.error(f"Error executing function {function_name}: {e}")
            return {"error": str(e)}
    
    def generate_response(self, user_input: str) -> str:
        """
        Generate a response using the LLM with function calling capabilities.
        
        Args:
            user_input: The user's input text
            
        Returns:
            The assistant's response
        """
        # Prepare conversation context
        messages = [{"role": "system", "content": self.system_prompt}]
        
        # Add conversation history
        for msg in self.conversation_history[-5:]:  # Include last 5 messages for context
            messages.append(msg)
        
        # Add user input
        messages.append({"role": "user", "content": user_input})
        
        logger.debug(f"Preparing to call Ollama with {len(messages)} messages")
        
        try:
            # Call Ollama for response with tools/function calling
            start_time = time.time()
            response = ollama.chat(
                model=self.model_name,
                messages=messages,
                options={
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens
                },
                tools=self.tools  # Include tool definitions
            )
            end_time = time.time()
            
            # Track and log token usage with message context for estimation
            self.token_tracker.track_usage(response, messages=messages)
            self.token_tracker.log_usage("Initial Request")
            
            # Log response time
            response_time = end_time - start_time
            logger.info(f"Received response from model in {response_time:.2f}s")
            
            # Check if the response includes a tool/function call
            if "tool_calls" in response["message"]:
                tool_calls = response["message"]["tool_calls"]
                logger.info(f"Model requested tool calls: {len(tool_calls)}")
                logger.debug(f"Tool calls: {tool_calls}")
                
                function_responses = []
                
                # Execute each function call
                for tool_call in tool_calls:
                    logger.debug(f"Processing tool call: {tool_call}")
                    
                    try:
                        function_name = tool_call["function"]["name"]
                        logger.debug(f"Function name: {function_name}")
                        
                        arguments_str = tool_call["function"]["arguments"]
                        logger.debug(f"Raw arguments: {arguments_str} (type: {type(arguments_str)})")
                        
                        # Parse arguments - could be string or already a dict
                        if isinstance(arguments_str, dict):
                            # Already a dictionary, no need to parse
                            arguments = arguments_str
                            logger.debug(f"Arguments already a dict: {arguments}")
                        elif isinstance(arguments_str, str):
                            # String that needs to be parsed
                            try:
                                arguments = json.loads(arguments_str)
                                logger.debug(f"Parsed arguments from string: {arguments}")
                            except json.JSONDecodeError:
                                logger.warning(f"Failed to parse arguments: {arguments_str}")
                                arguments = {}
                        else:
                            # Unexpected type
                            logger.warning(f"Unexpected arguments type: {type(arguments_str)}")
                            arguments = {}
                    except Exception as e:
                        logger.error(f"Error extracting function details: {e}")
                        arguments = {}
                        function_name = "unknown"
                    
                    # Execute function
                    try:
                        logger.debug(f"Executing function: {function_name} with arguments: {arguments}")
                        function_result = self._execute_function(function_name, arguments)
                        logger.debug(f"Function result type: {type(function_result)}")
                        logger.debug(f"Function result: {function_result}")
                        
                        # Convert function_result to a string if it's not already
                        if function_result is None:
                            logger.warning("Function returned None")
                            content_str = "null"
                        elif isinstance(function_result, dict) or isinstance(function_result, list):
                            try:
                                content_str = json.dumps(function_result)
                                logger.debug(f"JSON serialized result: {content_str[:100]}..." 
                                            if len(content_str) > 100 else f"JSON serialized result: {content_str}")
                            except Exception as e:
                                logger.error(f"Error serializing function result to JSON: {e}")
                                content_str = str(function_result)
                        else:
                            content_str = str(function_result)
                    except Exception as e:
                        logger.error(f"Error during function execution or serialization: {e}", exc_info=True)
                        content_str = f"{{\"error\": \"{str(e)}\"}}"
                        
                    # Generate a unique ID if missing (Ollama API versions may differ)
                    tool_call_id = None
                    try:
                        if "id" in tool_call:
                            tool_call_id = tool_call["id"]
                            logger.debug(f"Using existing tool call ID: {tool_call_id}")
                        else:
                            # Generate a unique ID for this tool call
                            tool_call_id = f"tc_{function_name}_{datetime.datetime.now().timestamp()}"
                            logger.debug(f"Generated tool call ID: {tool_call_id}")
                    except Exception as e:
                        logger.error(f"Error accessing tool call ID: {e}")
                        tool_call_id = f"tc_fallback_{datetime.datetime.now().timestamp()}"
                    
                    # Add function response to messages
                    function_responses.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "name": function_name,
                        "content": content_str
                    })
                
                # Add LLM message and function responses to conversation history
                self.conversation_history.append(response["message"])
                for func_response in function_responses:
                    self.conversation_history.append(func_response)
                
                # Build a properly formatted messages array for the second API call
                # The original messages + the response message + function responses
                combined_messages = messages.copy()  # Start with the original messages
                combined_messages.append(response["message"])  # Add the original response
                
                # Add function responses with proper formatting
                for func_response in function_responses:
                    # Create a formatted message with tool call response
                    formatted_response = {
                        "role": func_response["role"],
                        "name": func_response["name"],
                        "content": func_response["content"]
                    }
                    
                    # Add tool_call_id if present to maintain compatibility
                    if "tool_call_id" in func_response and func_response["tool_call_id"]:
                        formatted_response["tool_call_id"] = func_response["tool_call_id"]
                        
                    combined_messages.append(formatted_response)
                
                # Get final response from LLM with function results
                start_time = time.time()
                final_response = ollama.chat(
                    model=self.model_name,
                    messages=combined_messages,
                    options={
                        "temperature": self.temperature,
                        "num_predict": self.max_tokens
                    }
                )
                end_time = time.time()
                
                # Track and log token usage with message context for estimation
                self.token_tracker.track_usage(final_response, messages=combined_messages)
                self.token_tracker.log_usage("Function Response")
                
                # Log response time
                response_time = end_time - start_time
                logger.info(f"Received function response in {response_time:.2f}s")
                
                # Add final response to history
                try:
                    self.conversation_history.append(final_response["message"])
                    logger.debug(f"Final response message: {final_response['message']}")
                    return final_response["message"]["content"]
                except Exception as e:
                    logger.error(f"Error processing final response: {e}")
                    return f"Sorry, I encountered an error in the final response: {str(e)}"
            else:
                # No function call, just return the response content
                self.conversation_history.append(response["message"])
                return response["message"]["content"]
                
        except Exception as e:
            logger.error(f"Error generating response: {e}", exc_info=True)  # Include complete traceback
            return f"Sorry, I encountered an error: {str(e)}"
    
    def process_input(self, user_input: str) -> str:
        """
        Process user input and generate a response with tool calling as needed.
        
        Args:
            user_input: The user's input text
            
        Returns:
            The assistant's response
        """
        logger.info(f"User input: {user_input}")
        
        try:
            # Add user input to conversation history
            self.conversation_history.append({"role": "user", "content": user_input})
            
            # Generate response with potential function calls
            response = self.generate_response(user_input)
            
            logger.info(f"Assistant response: {response}")
            
            # Log token usage summary after completing the interaction
            self.token_tracker.log_summary()
            
            return response
        except Exception as e:
            error_msg = f"Error processing input: {str(e)}"
            logger.error(error_msg, exc_info=True)  # Include full traceback
            return f"Sorry, I encountered an unexpected error: {str(e)}"
    
    def run_interactive(self):
        """
        Run the agent in interactive mode with a command-line interface.
        """
        self.console.print(Panel(
            "Your AI assistant is ready to help you manage your calendar and tasks.\n"
            "Type 'quit', 'exit', or 'bye' to end the session.",
            title="AI Assistant",
            border_style="blue"
        ))
        
        while True:
            user_input = Prompt.ask("\n[bold]You[/bold]")
            
            if user_input.lower() in ["quit", "exit", "bye"]:
                self.console.print("[bold]Assistant:[/bold] Goodbye!")
                break
            
            response = self.process_input(user_input)
            self.console.print(f"\n[bold]Assistant:[/bold] {response}")


class AgentCalendarAssistant(Agent):
    """
    Compatibility wrapper for the Agent class that provides the same interface
    as expected by the existing agent_cli.py module.
    
    This class inherits from Agent and maintains backward compatibility with
    any code that expects the AgentCalendarAssistant class.
    """
    def __init__(self, model_name=DEFAULT_MODEL, user=None, db=None):
        """
        Initialize the calendar assistant agent.
        
        Args:
            model_name: Name of the Ollama model to use
            user: Optional User object for authenticated calendar access
            db: Optional database session for token management
        """
        # Enhanced system prompt specifically for calendar operations
        calendar_system_prompt = """
        You are an intelligent AI assistant specialized in managing calendars and tasks.
        You can help with scheduling events, managing tasks, checking availability, and more.
        
        You have access to Google Calendar and Google Tasks to help the user manage their schedule.
        Always prioritize using the appropriate tools when handling calendar and task operations.
        Provide helpful, concise responses about calendar management.
        """
        
        # Store user and db for calendar service initialization
        self.user = user
        self.db = db
        self.calendar = None
        
        # Log the authentication status
        if user and db:
            try:
                logger.info(f"AgentCalendarAssistant initializing with authenticated user: {user.email}")
                # Initialize calendar service with authenticated user
                try:
                    from backend.services.calendar_service import GoogleCalendar
                    self.calendar = GoogleCalendar(user=user, db=db)
                    logger.info(f"Calendar service initialized successfully for user: {user.email}")
                except ImportError as e:
                    logger.error(f"Failed to import calendar service module: {str(e)}")
                    # Continue without calendar functionality
                except Exception as e:
                    logger.error(f"Failed to initialize calendar service: {str(e)}", exc_info=True)
                    # Continue without calendar functionality
            except Exception as e:
                logger.error(f"Unexpected error during agent initialization: {str(e)}", exc_info=True)
        else:
            if not user:
                logger.warning("AgentCalendarAssistant initialized without user - authentication will fail")
            if not db:
                logger.warning("AgentCalendarAssistant initialized without database session - token management will fail")
            # Calendar will be initialized without credentials, which will likely fail for API calls
            
        try:
            # Initialize the base Agent class with calendar-specific settings
            logger.debug(f"Initializing base Agent with model: {model_name}")
            super().__init__(model_name=model_name, system_prompt=calendar_system_prompt, user=user, db=db)
            logger.info("Base agent initialization successful")
        except Exception as e:
            logger.error(f"Failed to initialize base Agent class: {str(e)}", exc_info=True)
            # Re-raise to ensure proper error handling
            raise


def main():
    """
    Main entry point for the agent application.
    """
    try:
        # Initialize the agent with llama3.1 model
        agent = Agent(model_name=os.getenv("OLLAMA_MODEL", "llama3.1"))
        
        # Run the agent in interactive mode
        agent.run_interactive()
        
    except Exception as e:
        console = Console()
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    main()

