"""
Google Tasks API wrapper for CRUD operations.
"""
import datetime
import logging
from typing import Dict, List, Optional, Union
from fastapi import Depends
from sqlalchemy.orm import Session
from googleapiclient.errors import HttpError

from backend.utils.retry_utils import retry_with_backoff
from backend.models.database import get_db
from backend.models.user import User
from backend.api.auth.dependencies import get_current_user_from_token
from backend.services.auth_service import get_tasks_service
from backend.utils.cache_manager import CacheManager

# Set up logging
logger = logging.getLogger(__name__)

class GoogleTasks:
    """Wrapper for Google Tasks API operations."""
    
    # Class-level cache managers for task lists and tasks
    _tasklist_cache_manager = CacheManager(max_items=20, ttl_seconds=300)  # Smaller cache for task lists
    _task_cache_manager = CacheManager(max_items=100, ttl_seconds=300)     # Larger cache for individual tasks
    
    def __init__(self, user: Optional[User] = Depends(get_current_user_from_token), db: Optional[Session] = Depends(get_db)):
        """
        Initialize the Google Tasks wrapper.
        
        Args:
            user: User object for authentication
            db: Database session
        """
        # Get the tasks-specific service for the user
        self.user = user
        self.db = db
        
        if user and db:
            self.service = get_tasks_service(user=user, db=db)
        else:
            # Fallback for compatibility - this will likely fail in web context
            logger.warning("GoogleTasks initialized without user and db - authentication may fail")
            self.service = get_tasks_service()
        
        self.tasks_service = self.service
    
    @classmethod
    def _clear_cache(cls, cache_category=None, user_id=None):
        """Clear cached data.
        
        Args:
            cache_category: Type of cache to clear ('tasklist', 'task', or None for all)
            user_id: Optional user ID to scope the cache clearing by user
        """
        if cache_category is None:
            # Clear all caches
            cls._tasklist_cache_manager.invalidate()
            cls._task_cache_manager.invalidate()
            logger.debug("All task caches cleared")
        elif cache_category == 'tasklist':
            # Clear only tasklist cache
            cls._tasklist_cache_manager.invalidate()
            logger.debug("Task list cache cleared")
        elif cache_category == 'task':
            # Clear only task cache
            cls._task_cache_manager.invalidate()
            logger.debug("Task cache cleared")
    
    @retry_with_backoff(max_attempts=3)
    def list_tasklists(self) -> List[Dict]:
        """
        List all task lists.
        
        Returns:
            List of task list objects
        """
        cache_key = 'all_tasklists'
        
        # Check if we have a valid cached task list
        cached_tasklists = self._tasklist_cache_manager.get(cache_key)
        if cached_tasklists is not None:
            logger.debug("Using cached task lists")
            return cached_tasklists
            
        # Otherwise fetch and cache task lists
        try:
            results = self.tasks_service.tasklists().list().execute()
            tasklists = results.get('items', [])
            return self._tasklist_cache_manager.set(cache_key, tasklists)
        except HttpError as error:
            logger.error(f"API error: {error}")
            raise
    
    @retry_with_backoff(max_attempts=3)
    def get_tasklist(self, tasklist_id: str) -> Optional[Dict]:
        """
        Get a specific task list by ID.
        
        Args:
            tasklist_id: ID of the task list
        
        Returns:
            Task list object
        """
        cache_key = f'tasklist:{tasklist_id}'
        
        # Check if we have a valid cached task list
        cached_tasklist = self._tasklist_cache_manager.get(cache_key)
        if cached_tasklist is not None:
            logger.debug(f"Using cached task list: {tasklist_id}")
            return cached_tasklist
            
        # Otherwise fetch and cache task list
        try:
            tasklist = self.tasks_service.tasklists().get(tasklist=tasklist_id).execute()
            return self._tasklist_cache_manager.set(cache_key, tasklist)
        except HttpError as error:
            # For 404 Not Found, return None
            if hasattr(error, 'resp') and error.resp.status == 404:
                return None
                
            logger.error(f"API error: {error}")
            raise
    
    @retry_with_backoff(max_attempts=3)
    def create_tasklist(self, title: str) -> Dict:
        """
        Create a new task list.
        
        Args:
            title: Title for the task list
            
        Returns:
            The created task list object
        """
        try:
            tasklist = self.tasks_service.tasklists().insert(body={'title': title}).execute()
            
            # Clear the 'all' task lists cache since it's now outdated
            self._tasklist_cache_manager.invalidate('all_tasklists')
            logger.debug("Cleared task lists cache after creating new list")
                
            # Cache the new task list
            cache_key = f'tasklist:{tasklist["id"]}'
            self._tasklist_cache_manager.set(cache_key, tasklist)
            
            return tasklist
        except HttpError as error:
            logger.error(f"API error: {error}")
            raise
    
    @retry_with_backoff(max_attempts=3)
    def update_tasklist(self, tasklist_id: str, title: str) -> Dict:
        """
        Update a task list.
        
        Args:
            tasklist_id: ID of the task list
            title: New title for the task list
        
        Returns:
            The updated task list object
        """
        try:
            updated_tasklist = self.tasks_service.tasklists().update(
                tasklist=tasklist_id,
                body={'id': tasklist_id, 'title': title}
            ).execute()
            
            # Update caches
            cache_key = f'tasklist:{tasklist_id}'
            self._tasklist_cache_manager.set(cache_key, updated_tasklist)
            
            # Clear the 'all' task lists cache since it's now outdated
            self._tasklist_cache_manager.invalidate('all_tasklists')
            logger.debug("Cleared task lists cache after updating list")
                
            return updated_tasklist
        except HttpError as error:
            logger.error(f"API error: {error}")
            raise
    
    @retry_with_backoff(max_attempts=3)
    def delete_tasklist(self, tasklist_id: str) -> bool:
        """
        Delete a task list.
        
        Args:
            tasklist_id: ID of the task list
            
        Returns:
            True if successful
        """
        try:
            self.tasks_service.tasklists().delete(tasklist=tasklist_id).execute()
            
            # Remove from cache
            cache_key = f'tasklist:{tasklist_id}'
            self._tasklist_cache_manager.invalidate(cache_key)
            
            # Clear related task caches
            # Remove any tasks associated with this tasklist
            self._task_cache_manager.invalidate(f'tasks:{tasklist_id}')
            
            # Clear the 'all' task lists cache since it's now outdated
            self._tasklist_cache_manager.invalidate('all_tasklists')
            logger.debug("Removed task list from cache after deletion")
            return True
        except HttpError as error:
            logger.error(f"API error: {error}")
            raise
    
    @retry_with_backoff(max_attempts=3)
    def list_tasks(self, tasklist_id: str = '@default', max_results: int = 100,
                  completed: Optional[bool] = None,
                  due_min: Optional[str] = None,
                  due_max: Optional[str] = None) -> List[Dict]:
        """
        List tasks in a task list.
        
        Args:
            tasklist_id: ID of the task list (default: '@default')
            max_results: Maximum number of tasks to return
            completed: If True, show completed tasks; if False, hide them
            due_min: Minimum due date (ISO format)
            due_max: Maximum due date (ISO format)
            
        Returns:
            List of task objects
        """
        # Create cache key with parameters that affect results
        params = f"{tasklist_id}:{max_results}:{completed}:{due_min}:{due_max}"
        cache_key = f'tasks:{params}'
        
        # Check if we have a valid cached task list
        cached_tasks = self._task_cache_manager.get(cache_key)
        if cached_tasks is not None:
            logger.debug(f"Using cached tasks for {tasklist_id}")
            return cached_tasks
            
        # Otherwise fetch and cache tasks
        try:
            # Prepare parameters
            params = {
                'maxResults': max_results
            }
            
            # Add optional parameters if provided
            if completed is not None:
                params['showCompleted'] = completed
                
            if due_min:
                params['dueMin'] = due_min
                
            if due_max:
                params['dueMax'] = due_max
            
            # Make the API call
            results = self.tasks_service.tasks().list(tasklist=tasklist_id, **params).execute()
            tasks = results.get('items', [])
            return self._task_cache_manager.set(cache_key, tasks)
        except HttpError as error:
            logger.error(f"API error: {error}")
            raise
            
    @retry_with_backoff(max_attempts=3)
    def get_task(self, tasklist_id: str, task_id: str) -> Optional[Dict]:
        """
        Get a specific task by ID.
        
        Args:
            tasklist_id: ID of the task list
            task_id: ID of the task
            
        Returns:
            Task object
        """
        cache_key = f'task:{tasklist_id}:{task_id}'
        
        # Check if we have a valid cached task
        cached_task = self._task_cache_manager.get(cache_key)
        if cached_task is not None:
            logger.debug(f"Using cached task: {task_id}")
            return cached_task
            
        # Otherwise fetch and cache task
        try:
            task = self.tasks_service.tasks().get(
                tasklist=tasklist_id, 
                task=task_id
            ).execute()
            return self._task_cache_manager.set(cache_key, task)
        except HttpError as error:
            if hasattr(error, 'resp') and error.resp.status == 404:
                return None
                
            logger.error(f"API error: {error}")
            raise
    
    @retry_with_backoff(max_attempts=3)
    def create_task(self, 
                   tasklist_id: str = '@default',
                   title: str = None,
                   notes: str = None,
                   due: Optional[Union[str, datetime.datetime]] = None,
                   parent: str = None,
                   previous: str = None,
                   status: str = 'needsAction') -> Dict:
        """
        Create a new task.
        
        Args:
            tasklist_id: ID of the task list (default: '@default')
            title: Title of the task
            notes: Additional notes for the task
            due: Due date (datetime or RFC 3339 timestamp string)
            parent: ID of parent task (for subtasks)
            previous: ID of previous task (for ordering)
            status: Status of the task ('needsAction' or 'completed')
            
        Returns:
            The created task object
        """
        # Create task body
        task_body = {}
        
        if title:
            task_body['title'] = title
        if notes:
            task_body['notes'] = notes
        if status:
            task_body['status'] = status
            
        # Convert datetime to RFC 3339 timestamp if needed
        if due:
            if isinstance(due, datetime.datetime):
                due_str = due.isoformat()
                if '+' not in due_str and 'Z' not in due_str:
                    due_str += 'Z'  # Add UTC marker
                task_body['due'] = due_str
            else:
                task_body['due'] = due
        
        try:
            params = {'tasklist': tasklist_id, 'body': task_body}
            
            # Add optional parameters for positioning
            if parent:
                params['parent'] = parent
            if previous:
                params['previous'] = previous
            
            return self.tasks_service.tasks().insert(**params).execute()
        except HttpError as error:
            logger.error(f"API error: {error}")
            raise
    
    @retry_with_backoff(max_attempts=3)
    def update_task(self,
                   tasklist_id: str,
                   task_id: str,
                   title: Optional[str] = None,
                   notes: Optional[str] = None,
                   due: Optional[Union[str, datetime.datetime]] = None,
                   status: Optional[str] = None,
                   completed: Optional[bool] = None) -> Dict:
        """
        Update an existing task.
        
        Args:
            tasklist_id: ID of the task list
            task_id: ID of the task to update
            title: New title (if changing)
            notes: New notes (if changing)
            due: New due date (if changing)
            status: New status (if changing)
            completed: Set to True to mark as completed
            
        Returns:
            The updated task object
        """
        try:
            # First get the existing task
            task = self.tasks_service.tasks().get(
                tasklist=tasklist_id, 
                task=task_id
            ).execute()
            
            # Update fields if provided
            if title is not None:
                task['title'] = title
                
            if notes is not None:
                task['notes'] = notes
                
            if due is not None:
                if isinstance(due, datetime.datetime):
                    due_str = due.isoformat()
                    if '+' not in due_str and 'Z' not in due_str:
                        due_str += 'Z'  # Add UTC marker
                    task['due'] = due_str
                else:
                    task['due'] = due
            
            # Handle status changes        
            if status is not None:
                task['status'] = status
                
            # Mark as completed if requested
            if completed:
                task['status'] = 'completed'
                task['completed'] = datetime.datetime.utcnow().isoformat() + 'Z'
                
            # Update the task
            return self.tasks_service.tasks().update(
                tasklist=tasklist_id,
                task=task_id,
                body=task
            ).execute()
        except HttpError as error:
            logger.error(f"API error: {error}")
            raise
    
    @retry_with_backoff(max_attempts=3)
    def delete_task(self, tasklist_id: str, task_id: str) -> bool:
        """
        Delete a task.
        
        Args:
            tasklist_id: ID of the task list
            task_id: ID of the task to delete
            
        Returns:
            True if successful
        """
        try:
            self.tasks_service.tasks().delete(
                tasklist=tasklist_id,
                task=task_id
            ).execute()
            return True
        except HttpError as error:
            logger.error(f"API error: {error}")
            raise
    
    @retry_with_backoff(max_attempts=3)
    def complete_task(self, tasklist_id: str, task_id: str) -> Dict:
        """
        Mark a task as completed.
        
        Args:
            tasklist_id: ID of the task list
            task_id: ID of the task to complete
            
        Returns:
            The updated task object
        """
        return self.update_task(
            tasklist_id=tasklist_id,
            task_id=task_id,
            completed=True
        )
    
    @retry_with_backoff(max_attempts=3)
    def move_task(self, 
                 tasklist_id: str, 
                 task_id: str,
                 parent: Optional[str] = None,
                 previous: Optional[str] = None) -> Dict:
        """
        Move a task, changing its position or parent.
        
        Args:
            tasklist_id: ID of the task list
            task_id: ID of the task to move
            parent: ID of new parent task (for subtasks)
            previous: ID of task that should be before this one
            
        Returns:
            The moved task object
        """
        try:
            params = {
                'tasklist': tasklist_id,
                'task': task_id
            }
            
            if parent:
                params['parent'] = parent
            if previous:
                params['previous'] = previous
            
            return self.tasks_service.tasks().move(**params).execute()
        except HttpError as error:
            logger.error(f"API error: {error}")
            raise
    
    @retry_with_backoff(max_attempts=3)
    def clear_completed(self, tasklist_id: str) -> bool:
        """
        Clear all completed tasks from a task list.
        
        Args:
            tasklist_id: ID of the task list
            
        Returns:
            True if successful
        """
        try:
            self.tasks_service.tasks().clear(tasklist=tasklist_id).execute()
            return True
        except HttpError as error:
            logger.error(f"API error: {error}")
            raise
