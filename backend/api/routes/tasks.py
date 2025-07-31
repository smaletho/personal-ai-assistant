"""
Tasks API routes.
"""
from fastapi import APIRouter, HTTPException, Depends, Body
from pydantic import BaseModel
from typing import Optional, Dict, List, Any, Union

from backend.services.tasks_service import GoogleTasks

router = APIRouter(
    prefix="/tasks",
    tags=["tasks"],
    responses={404: {"description": "Not found"}},
)

# Tasks service instance cache
tasks_instances: Dict[str, GoogleTasks] = {}

def get_tasks_service(session_id: str = "default") -> GoogleTasks:
    """Get or create a GoogleTasks instance for the session."""
    if session_id not in tasks_instances:
        try:
            tasks_instances[session_id] = GoogleTasks()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to initialize tasks service: {str(e)}")
    
    return tasks_instances[session_id]

@router.get("/lists")
async def list_tasklists(session_id: str = "default"):
    """List available task lists."""
    tasks_service = get_tasks_service(session_id)
    
    try:
        tasklists = tasks_service.list_tasklists()
        return {"tasklists": tasklists}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing task lists: {str(e)}")

@router.get("/")
async def list_tasks(
    tasklist_id: Optional[str] = None,
    session_id: str = "default"
):
    """List tasks from a task list."""
    tasks_service = get_tasks_service(session_id)
    
    try:
        # If no tasklist specified, get the default one
        if not tasklist_id:
            tasklists = tasks_service.list_tasklists()
            if not tasklists:
                return {"tasks": []}
            tasklist_id = tasklists[0].get("id")
        
        tasks = tasks_service.list_tasks(tasklist_id=tasklist_id)
        return {"tasks": tasks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing tasks: {str(e)}")

@router.post("/")
async def create_task(
    title: str,
    notes: Optional[str] = None,
    due_date: Optional[str] = None,
    tasklist_id: Optional[str] = None,
    session_id: str = "default"
):
    """Create a task."""
    tasks_service = get_tasks_service(session_id)
    
    try:
        # If no tasklist specified, get the default one
        if not tasklist_id:
            tasklists = tasks_service.list_tasklists()
            if not tasklists:
                raise HTTPException(status_code=404, detail="No task lists found")
            tasklist_id = tasklists[0].get("id")
        
        task = tasks_service.create_task(
            tasklist_id=tasklist_id,
            title=title,
            notes=notes,
            due_date=due_date
        )
        return {"task": task}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating task: {str(e)}")

@router.delete("/{tasklist_id}/{task_id}")
async def delete_task(
    tasklist_id: str,
    task_id: str,
    session_id: str = "default"
):
    """Delete a task."""
    tasks_service = get_tasks_service(session_id)
    
    try:
        success = tasks_service.delete_task(
            tasklist_id=tasklist_id,
            task_id=task_id
        )
        
        if success:
            return {"status": "success", "message": "Task deleted successfully"}
        else:
            return {"status": "error", "message": "Failed to delete task"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting task: {str(e)}")

@router.put("/{tasklist_id}/{task_id}")
async def update_task(
    tasklist_id: str,
    task_id: str,
    title: Optional[str] = None,
    notes: Optional[str] = None,
    due_date: Optional[str] = None,
    status: Optional[str] = None,
    session_id: str = "default"
):
    """Update a task."""
    tasks_service = get_tasks_service(session_id)
    
    try:
        task = tasks_service.update_task(
            tasklist_id=tasklist_id,
            task_id=task_id,
            title=title,
            notes=notes,
            due_date=due_date,
            status=status
        )
        return {"task": task}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating task: {str(e)}")

@router.get("/upcoming")
async def get_upcoming_tasks(
    days: int = 7,
    tasklist_id: Optional[str] = None,
    session_id: str = "default"
):
    """Get upcoming tasks for the next X days."""
    tasks_service = get_tasks_service(session_id)
    
    try:
        # If no tasklist specified, get the default one
        if not tasklist_id:
            tasklists = tasks_service.list_tasklists()
            if not tasklists:
                return {"tasks": []}
            tasklist_id = tasklists[0].get("id")
        
        # Get all tasks and then filter locally
        tasks = tasks_service.list_tasks(tasklist_id=tasklist_id)
        
        # Filter tasks by due date
        from datetime import datetime, timedelta
        
        # Calculate cutoff date (today + specified days)
        today = datetime.now().date()
        cutoff_date = (today + timedelta(days=days)).isoformat()
        
        # Filter tasks that are upcoming (due date <= cutoff date)
        upcoming_tasks = []
        for task in tasks:
            # Skip completed tasks
            if task.get("status") == "completed":
                continue
                
            # Include tasks with no due date (they're always relevant)
            if "due" not in task:
                upcoming_tasks.append(task)
                continue
                
            # Check if due date is within the cutoff range
            # Google Tasks API returns due date in RFC 3339 format: YYYY-MM-DDThh:mm:ss.sssZ
            # We need to extract just the date part
            if "due" in task:
                due_date = task["due"].split("T")[0]  # Extract just YYYY-MM-DD
                if due_date <= cutoff_date:
                    upcoming_tasks.append(task)
        
        return {"tasks": upcoming_tasks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting upcoming tasks: {str(e)}")


# Define models for confirmed operations
class ConfirmedTaskOperation(BaseModel):
    """Model for a confirmed task operation from the confirmation flow"""
    operation: str  # create_task, update_task, delete_task, complete_task
    details: Dict[str, Any]  # The original parameters passed to the operation


@router.post("/confirmed-operation")
async def execute_confirmed_operation(operation_data: ConfirmedTaskOperation = Body(...), session_id: str = "default"):
    """Execute a task operation that has been confirmed by the user.
    This bypasses the agent and directly calls the appropriate tasks service method.
    """
    tasks_service = get_tasks_service(session_id)
    operation = operation_data.operation
    details = operation_data.details
    
    try:
        # If no tasklist specified, get the default one
        tasklist_id = details.get("tasklist_id")
        if not tasklist_id:
            tasklists = tasks_service.list_tasklists()
            if not tasklists:
                raise HTTPException(status_code=404, detail="No task lists found")
            tasklist_id = tasklists[0].get("id")
        
        # Handle different operations
        if operation == "create_task":
            # Extract parameters from details
            title = details.get("title")
            notes = details.get("notes")
            due_date = details.get("due_date")
            
            # Validate required parameters
            if not title:
                raise HTTPException(status_code=400, detail="Task title is required")
            
            # Create the task
            task = tasks_service.create_task(
                tasklist_id=tasklist_id,
                title=title,
                notes=notes,
                due_date=due_date
            )
            
            return {
                "status": "success",
                "message": f"Task '{title}' has been created successfully.",
                "task": task
            }
            
        elif operation == "update_task":
            # Extract parameters
            task_id = details.get("task_id")
            title = details.get("title")
            notes = details.get("notes")
            due_date = details.get("due_date")
            status = details.get("status")
            
            # Validate required parameters
            if not task_id:
                raise HTTPException(status_code=400, detail="Task ID is required")
            # Ensure at least one field is being updated
            if not title and not notes and not due_date and not status:
                raise HTTPException(status_code=400, detail="At least one field must be updated")
            
            # Update the task
            task = tasks_service.update_task(
                tasklist_id=tasklist_id,
                task_id=task_id,
                title=title,
                notes=notes,
                due_date=due_date,
                status=status
            )
            
            return {
                "status": "success",
                "message": f"Task has been updated successfully.",
                "task": task
            }
            
        elif operation == "delete_task":
            # Extract parameters
            task_id = details.get("task_id")
            
            # Validate required parameters
            if not task_id:
                raise HTTPException(status_code=400, detail="Task ID is required")
            
            # Delete the task
            success = tasks_service.delete_task(
                tasklist_id=tasklist_id,
                task_id=task_id
            )
            
            if success:
                return {
                    "status": "success",
                    "message": "Task deleted successfully."
                }
            else:
                return {
                    "status": "error",
                    "message": "Failed to delete task."
                }
                
        elif operation == "complete_task":
            # Extract parameters
            task_id = details.get("task_id")
            
            # Validate required parameters
            if not task_id:
                raise HTTPException(status_code=400, detail="Task ID is required")
            
            # Complete the task by updating its status to "completed"
            task = tasks_service.update_task(
                tasklist_id=tasklist_id,
                task_id=task_id,
                status="completed"
            )
            
            return {
                "status": "success",
                "message": "Task marked as completed.",
                "task": task
            }
        
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported operation: {operation}")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error executing confirmed operation: {str(e)}")
