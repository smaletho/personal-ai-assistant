"""
Fixed implementations for agent.py methods to properly support function calling with llama3.1
"""
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta, time
from dateutil.parser import parse

def _list_events(self, time_range: str, max_results: str = "10") -> str:
    """List calendar events for a specific time range.
    
    Args:
        time_range: Time range to search (e.g., 'today', 'tomorrow', 'week', 'month', or 'upcoming')
        max_results: Maximum number of events to return as string (will be converted to int)
        
    Returns:
        String representation of the events
    """
    try:
        # Convert max_results to int with validation
        try:
            max_results_int = int(max_results)
            if max_results_int < 1:
                max_results_int = 10
            elif max_results_int > 100:
                max_results_int = 100
        except (ValueError, TypeError):
            max_results_int = 10  # Default value if conversion fails
        
        # Get the current calendar name
        calendar_name = "Unknown"
        for cal in self.available_calendars:
            if cal.get('id') == self.current_calendar_id:
                calendar_name = cal.get('summary', "Unknown Calendar")
        
        # Set time filters
        now = datetime.now()
        if time_range == "today":
            start_time = datetime.combine(now.date(), time.min).astimezone()
            end_time = datetime.combine(now.date(), time.max).astimezone()
        elif time_range == "tomorrow":
            tomorrow = now.date() + timedelta(days=1)
            start_time = datetime.combine(tomorrow, time.min).astimezone()
            end_time = datetime.combine(tomorrow, time.max).astimezone()
        elif time_range == "week":
            start_of_week = now.date() - timedelta(days=now.weekday())
            end_of_week = start_of_week + timedelta(days=6)
            start_time = datetime.combine(start_of_week, time.min).astimezone()
            end_time = datetime.combine(end_of_week, time.max).astimezone()
        elif time_range == "month":
            start_of_month = now.date().replace(day=1)
            if now.month == 12:
                end_of_month = now.date().replace(year=now.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end_of_month = now.date().replace(month=now.month + 1, day=1) - timedelta(days=1)
            start_time = datetime.combine(start_of_month, time.min).astimezone()
            end_time = datetime.combine(end_of_month, time.max).astimezone()
        else:  # 'upcoming' or any other value
            start_time = now.astimezone()
            end_time = (now + timedelta(days=30)).astimezone()  # Next 30 days
        
        # Get events
        events = self.calendar.list_events(
            calendar_id=self.current_calendar_id,
            start_time=start_time,
            end_time=end_time,
            max_results=max_results_int
        )
        
        if not events:
            return f"No events found for {time_range} in calendar: {calendar_name}"
        
        # Format events for response
        response = f"Events for {time_range} in calendar {calendar_name}:\n\n"
        
        for i, event in enumerate(events, 1):
            event_time = ""
            if event.get('start', {}).get('dateTime'):
                # This is a timed event
                start = parse(event['start']['dateTime']).strftime("%a, %b %d, %Y at %I:%M %p")
                end = ""
                if event.get('end', {}).get('dateTime'):
                    end = parse(event['end']['dateTime']).strftime("%I:%M %p")
                    event_time = f"{start} to {end}"
                else:
                    event_time = start
            elif event.get('start', {}).get('date'):
                # This is an all-day event
                start_date = parse(event['start']['date']).strftime("%a, %b %d, %Y")
                event_time = f"{start_date} (all day)"
            
            summary = event.get('summary', 'Untitled Event')
            location = f"Location: {event.get('location', 'Not specified')}"
            
            response += f"{i}. {summary}\n   {event_time}\n   {location}\n\n"
        
        return response
        
    except Exception as e:
        return f"Error retrieving events: {str(e)}"


def _create_event(
    self, 
    summary: str, 
    start_time: str, 
    end_time: str,
    description: str = "",
    location: str = ""
) -> str:
    """Create a calendar event.
        
    Args:
        summary: Event title
        start_time: Start time (string)
        end_time: End time (string)
        description: Event description (optional)
        location: Event location (optional)
    """
    try:
        # Parse start time
        try:
            start_dt = parse(start_time)
        except Exception:
            return f"Could not understand the start time: {start_time}. Please provide a clearer time format."
        
        # Parse end time
        try:
            end_dt = parse(end_time)
        except Exception:
            return f"Could not understand the end time: {end_time}. Please provide a clearer time format."
        
        # Create the event
        event = self.calendar.create_event(
            summary=summary,
            start_time=start_dt,
            end_time=end_dt,
            description=description,
            location=location
        )
        
        calendar_name = next((cal.get('summary') for cal in self.available_calendars if cal.get('id') == self.current_calendar_id), 'Primary')
        return f"Event '{summary}' created successfully in calendar '{calendar_name}'.\n" \
               f"Start: {start_dt.strftime('%Y-%m-%d %H:%M')}\n" \
               f"End: {end_dt.strftime('%Y-%m-%d %H:%M')}\n" \
               f"Description: {description}\n" \
               f"Location: {location}"
               
    except Exception as e:
        return f"Error creating event: {str(e)}"


def _list_tasks(self, task_list_name: str = "", max_results: str = "10") -> str:
    """Lists all tasks in the specified task list.
        
    Args:
        task_list_name: Name of the task list to list tasks from
        max_results: Maximum number of tasks to return (as string)
    """
    try:
        # Convert max_results to int with validation
        try:
            max_results_int = int(max_results)
            if max_results_int < 1:
                max_results_int = 10
            elif max_results_int > 100:
                max_results_int = 100
        except (ValueError, TypeError):
            max_results_int = 10  # Default value if conversion fails
            
        # Get available task lists
        task_lists = self.tasks.list_task_lists()
        task_list_id = None
        
        # Find the requested task list or use default
        if not task_list_name and task_lists:
            task_list_id = task_lists[0]['id']
            task_list_name = task_lists[0]['title']
        else:
            # Find the task list by name
            for task_list in task_lists:
                if task_list['title'].lower() == task_list_name.lower():
                    task_list_id = task_list['id']
                    task_list_name = task_list['title']  # Use actual title with correct case
                    break
        
        if not task_list_id:
            available_lists = ", ".join([tl['title'] for tl in task_lists])
            return f"Could not find task list '{task_list_name}'. Available lists: {available_lists}"
        
        # Get tasks in the task list
        tasks = self.tasks.list_tasks(task_list_id=task_list_id)
        
        if not tasks:
            return f"No tasks found in '{task_list_name}'"
        
        result = f"Tasks in '{task_list_name}':\n\n"
        
        # Limit number of tasks
        for i, task in enumerate(tasks[:max_results_int], 1):
            status = "[x]" if task.get('status') == 'completed' else "[ ]"
            title = task.get('title', 'Untitled task')
            
            # Format due date if available
            due_str = ""
            if 'due' in task:
                due_date = parse(task['due'])
                due_str = f" (Due: {due_date.strftime('%Y-%m-%d')})"
            
            result += f"{i}. {status} {title}{due_str}\n"
            
            # Add notes if available
            if 'notes' in task and task['notes']:
                result += f"   Notes: {task['notes']}\n"
            
            result += "\n"
        
        return result
    except Exception as e:
        return f"Error listing tasks: {str(e)}"


def _create_task(self, title: str, task_list_name: str = "", due_date: str = "") -> str:
    """Create a new task in a task list.
        
    Args:
        title: Title of the task
        task_list_name: Name of the task list to add the task to (empty for default)
        due_date: Due date for the task in YYYY-MM-DD format (optional)
    """
    try:
        # Get available task lists
        task_lists = self.tasks.list_task_lists()
        task_list_id = None
        list_title = "Default"
        
        # Find the requested task list or use default
        if not task_list_name and task_lists:
            task_list_id = task_lists[0]['id']
            list_title = task_lists[0]['title']
        else:
            # Find the task list by name
            for task_list in task_lists:
                if task_list['title'].lower() == task_list_name.lower():
                    task_list_id = task_list['id']
                    list_title = task_list['title']  # Use actual title with correct case
                    break
        
        if not task_list_id:
            available_lists = ", ".join([tl['title'] for tl in task_lists])
            return f"Could not find task list '{task_list_name}'. Available lists: {available_lists}"
            
        # Parse due date if provided
        due_dt = None
        if due_date:
            try:
                due_dt = parse(due_date)
            except Exception:
                return f"Could not understand the due date: {due_date}. Please provide a date in YYYY-MM-DD format."
            
        # Create the task
        task = self.tasks.create_task(
            task_list_id=task_list_id,
            title=title, 
            due=due_dt
        )
        
        response = f"Task '{title}' created successfully in list '{list_title}'."
        
        if due_dt:
            response += f"\nDue date: {due_dt.strftime('%Y-%m-%d')}"
            
        return response
        
    except Exception as e:
        return f"Error creating task: {str(e)}"


def _list_task_lists(self) -> str:
    """List all available task lists."""
    try:
        task_lists = self.tasks.list_task_lists()
        
        if not task_lists:
            return "You don't have any task lists."
        
        result = "Your task lists:\n\n"
        
        for i, task_list in enumerate(task_lists, 1):
            title = task_list.get('title', 'Unnamed List')
            result += f"{i}. {title}\n"
            
        return result
        
    except Exception as e:
        return f"Error listing task lists: {str(e)}"
