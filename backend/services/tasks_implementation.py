"""
Tasks module for managing reminders and to-do items.
Can be used independently or integrated with Google Calendar for reminders.
"""
import os
import json
import datetime
from typing import Dict, List, Optional, Union
from pathlib import Path
from pydantic import BaseModel, Field

# Define the data models for tasks
class Task(BaseModel):
    """Model representing a task/reminder."""
    id: str = Field(..., description="Unique identifier for the task")
    title: str = Field(..., description="Title of the task")
    description: Optional[str] = Field(None, description="Optional description")
    due_date: Optional[datetime.datetime] = Field(None, description="Due date/time for the task")
    completed: bool = Field(False, description="Whether the task is completed")
    priority: int = Field(0, description="Priority level (0-3, 0 being lowest)")
    calendar_id: Optional[str] = Field(None, description="Calendar ID if linked to a calendar")
    event_id: Optional[str] = Field(None, description="Event ID if linked to a calendar event")
    tags: List[str] = Field(default_factory=list, description="Custom tags for categorizing")
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    
    def __str__(self):
        """String representation of a task."""
        status = "✓" if self.completed else "☐"
        priority_str = "!" * self.priority if self.priority > 0 else ""
        due_str = f" (Due: {self.due_date.strftime('%Y-%m-%d %H:%M')})" if self.due_date else ""
        return f"{status} {self.title} {priority_str}{due_str}"


class TaskManager:
    """Manager for CRUD operations on tasks."""
    
    def __init__(self, storage_file: str = "tasks.json"):
        """
        Initialize the task manager.
        
        Args:
            storage_file: File to store tasks in
        """
        self.storage_file = storage_file
        self._ensure_storage()
    
    def _ensure_storage(self) -> None:
        """Ensure the storage file exists."""
        if not os.path.exists(self.storage_file):
            # Create empty tasks file
            with open(self.storage_file, "w") as f:
                json.dump([], f)
    
    def _load_tasks(self) -> List[Task]:
        """Load tasks from storage."""
        with open(self.storage_file, "r") as f:
            data = json.load(f)
            return [Task.model_validate(task_data) for task_data in data]
    
    def _save_tasks(self, tasks: List[Task]) -> None:
        """Save tasks to storage."""
        with open(self.storage_file, "w") as f:
            json.dump([task.model_dump() for task in tasks], f, default=str)
    
    def create_task(self,
                    title: str,
                    description: Optional[str] = None,
                    due_date: Optional[Union[str, datetime.datetime]] = None,
                    priority: int = 0,
                    calendar_id: Optional[str] = None,
                    tags: Optional[List[str]] = None) -> Task:
        """
        Create a new task.
        
        Args:
            title: Task title
            description: Optional task description
            due_date: Optional due date (datetime or ISO format string)
            priority: Priority level (0-3)
            calendar_id: Optional calendar ID if linked to a calendar
            tags: Optional list of tags for categorization
            
        Returns:
            The created task
        """
        # Convert string date to datetime if needed
        if isinstance(due_date, str):
            due_date = datetime.datetime.fromisoformat(due_date)
            
        # Generate a unique ID (using timestamp + first 8 chars of title)
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        title_part = "".join(c for c in title[:8] if c.isalnum()).lower()
        task_id = f"task_{timestamp}_{title_part}"
        
        # Create task
        task = Task(
            id=task_id,
            title=title,
            description=description,
            due_date=due_date,
            priority=priority,
            calendar_id=calendar_id,
            tags=tags or []
        )
        
        # Load existing tasks, add new task, and save
        tasks = self._load_tasks()
        tasks.append(task)
        self._save_tasks(tasks)
        
        return task
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """
        Get a task by ID.
        
        Args:
            task_id: ID of the task to retrieve
            
        Returns:
            The task if found, None otherwise
        """
        tasks = self._load_tasks()
        for task in tasks:
            if task.id == task_id:
                return task
        return None
    
    def update_task(self,
                    task_id: str,
                    title: Optional[str] = None,
                    description: Optional[str] = None,
                    due_date: Optional[Union[str, datetime.datetime]] = None,
                    completed: Optional[bool] = None,
                    priority: Optional[int] = None,
                    event_id: Optional[str] = None,
                    tags: Optional[List[str]] = None) -> Optional[Task]:
        """
        Update an existing task.
        
        Args:
            task_id: ID of the task to update
            title: New title (if changing)
            description: New description (if changing)
            due_date: New due date (if changing)
            completed: New completion status (if changing)
            priority: New priority level (if changing)
            event_id: New event ID (if changing)
            tags: New tags (if changing)
            
        Returns:
            The updated task if found, None otherwise
        """
        tasks = self._load_tasks()
        for i, task in enumerate(tasks):
            if task.id == task_id:
                # Update fields if provided
                if title is not None:
                    task.title = title
                if description is not None:
                    task.description = description
                if due_date is not None:
                    if isinstance(due_date, str):
                        due_date = datetime.datetime.fromisoformat(due_date)
                    task.due_date = due_date
                if completed is not None:
                    task.completed = completed
                if priority is not None:
                    task.priority = priority
                if event_id is not None:
                    task.event_id = event_id
                if tags is not None:
                    task.tags = tags
                
                # Update the timestamp
                task.updated_at = datetime.datetime.now()
                
                # Save changes
                tasks[i] = task
                self._save_tasks(tasks)
                
                return task
        
        return None
    
    def delete_task(self, task_id: str) -> bool:
        """
        Delete a task.
        
        Args:
            task_id: ID of the task to delete
            
        Returns:
            True if successful, False if task not found
        """
        tasks = self._load_tasks()
        initial_count = len(tasks)
        tasks = [task for task in tasks if task.id != task_id]
        
        if len(tasks) < initial_count:
            self._save_tasks(tasks)
            return True
        
        return False
    
    def list_tasks(self,
                   completed: Optional[bool] = None,
                   due_before: Optional[Union[str, datetime.datetime]] = None,
                   due_after: Optional[Union[str, datetime.datetime]] = None,
                   priority: Optional[int] = None,
                   calendar_id: Optional[str] = None,
                   tags: Optional[List[str]] = None) -> List[Task]:
        """
        List tasks with optional filtering.
        
        Args:
            completed: Filter by completion status
            due_before: Filter tasks due before this time
            due_after: Filter tasks due after this time
            priority: Filter by priority level
            calendar_id: Filter by calendar ID
            tags: Filter by tags (matches if task has ANY of the specified tags)
            
        Returns:
            List of matching tasks
        """
        tasks = self._load_tasks()
        filtered_tasks = []
        
        # Convert string dates to datetime if needed
        if isinstance(due_before, str):
            due_before = datetime.datetime.fromisoformat(due_before)
        if isinstance(due_after, str):
            due_after = datetime.datetime.fromisoformat(due_after)
        
        for task in tasks:
            # Apply filters
            if completed is not None and task.completed != completed:
                continue
            
            if due_before is not None and (task.due_date is None or task.due_date > due_before):
                continue
                
            if due_after is not None and (task.due_date is None or task.due_date < due_after):
                continue
                
            if priority is not None and task.priority != priority:
                continue
                
            if calendar_id is not None and task.calendar_id != calendar_id:
                continue
                
            if tags is not None and not any(tag in task.tags for tag in tags):
                continue
            
            filtered_tasks.append(task)
        
        # Sort by due date (None values at the end)
        sorted_tasks = sorted(filtered_tasks, 
                             key=lambda t: (t.due_date is None, t.due_date, -t.priority))
        
        return sorted_tasks
    
    def get_upcoming_tasks(self, days: int = 7) -> List[Task]:
        """
        Get tasks due in the upcoming days.
        
        Args:
            days: Number of days to look ahead
            
        Returns:
            List of upcoming tasks
        """
        now = datetime.datetime.now()
        future = now + datetime.timedelta(days=days)
        
        return self.list_tasks(
            completed=False,
            due_after=now,
            due_before=future
        )
    
    def get_overdue_tasks(self) -> List[Task]:
        """
        Get tasks that are overdue.
        
        Returns:
            List of overdue tasks
        """
        now = datetime.datetime.now()
        
        return self.list_tasks(
            completed=False,
            due_before=now
        )
    
    def sync_with_calendar(self, calendar, calendar_id: str = 'primary') -> int:
        """
        Sync tasks as calendar events.
        
        Args:
            calendar: GoogleCalendar instance
            calendar_id: ID of the calendar to sync with
            
        Returns:
            Number of tasks synced
        """
        synced_count = 0
        tasks = self.list_tasks(completed=False)
        
        for task in tasks:
            if task.due_date and not task.event_id:
                # Create an event for this task
                try:
                    # Set end time to 30 minutes after due date
                    end_time = task.due_date + datetime.timedelta(minutes=30)
                    
                    event = calendar.create_event(
                        summary=f"Task: {task.title}",
                        start_time=task.due_date,
                        end_time=end_time,
                        description=task.description or "",
                        calendar_id=calendar_id
                    )
                    
                    # Update task with event ID
                    self.update_task(
                        task_id=task.id,
                        event_id=event['id'],
                        calendar_id=calendar_id
                    )
                    
                    synced_count += 1
                except Exception as e:
                    print(f"Error syncing task {task.id}: {e}")
        
        return synced_count
