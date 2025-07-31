"""
Calendar API routes.
"""
from fastapi import APIRouter, HTTPException, Depends, Body
from pydantic import BaseModel
from typing import Optional, Dict, List, Any, Union
from datetime import datetime

from backend.services.calendar_service import GoogleCalendar

router = APIRouter(
    prefix="/calendar",
    tags=["calendar"],
    responses={404: {"description": "Not found"}},
)

# Calendar service instance cache
calendar_instances: Dict[str, GoogleCalendar] = {}

def get_calendar_service(session_id: str = "default") -> GoogleCalendar:
    """Get or create a GoogleCalendar instance for the session."""
    if session_id not in calendar_instances:
        try:
            calendar_instances[session_id] = GoogleCalendar()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to initialize calendar service: {str(e)}")
    
    return calendar_instances[session_id]

@router.get("/")
async def list_calendars(session_id: str = "default"):
    """List available calendars."""
    calendar = get_calendar_service(session_id)
    
    try:
        calendars = calendar.available_calendars
        return {"calendars": calendars}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing calendars: {str(e)}")

@router.get("/events")
async def list_events(
    calendar_id: str = "primary",
    max_results: int = 10,
    time_min: Optional[str] = None,
    time_max: Optional[str] = None,
    session_id: str = "default"
):
    """List calendar events."""
    calendar = get_calendar_service(session_id)
    
    try:
        events = calendar.list_events(
            calendar_id=calendar_id,
            max_results=max_results,
            time_min=time_min,
            time_max=time_max
        )
        return {"events": events}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing events: {str(e)}")

@router.post("/events")
async def create_event(
    summary: str,
    start_time: str,
    end_time: str,
    description: Optional[str] = None,
    location: Optional[str] = None,
    calendar_id: str = "primary",
    session_id: str = "default"
):
    """Create a calendar event."""
    calendar = get_calendar_service(session_id)
    
    try:
        event = calendar.create_event(
            summary=summary,
            start_time=start_time,
            end_time=end_time,
            description=description,
            location=location,
            calendar_id=calendar_id
        )
        return {"event": event}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating event: {str(e)}")

@router.delete("/events/{event_id}")
async def delete_event(
    event_id: str,
    calendar_id: str = "primary",
    session_id: str = "default"
):
    """Delete a calendar event."""
    calendar = get_calendar_service(session_id)
    
    try:
        success = calendar.delete_event(
            event_id=event_id,
            calendar_id=calendar_id
        )
        
        if success:
            return {"status": "success", "message": "Event deleted successfully"}
        else:
            return {"status": "error", "message": "Failed to delete event"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting event: {str(e)}")

@router.get("/next")
async def get_next_event(
    calendar_id: str = "primary",
    session_id: str = "default"
):
    """Get the next upcoming event."""
    calendar = get_calendar_service(session_id)
    
    try:
        # Use the current time as time_min
        time_min = datetime.now().isoformat() + 'Z'  # 'Z' indicates UTC time
        events = calendar.list_events(
            calendar_id=calendar_id,
            max_results=1,
            time_min=time_min,
            order_by="startTime"
        )
        
        if events and len(events) > 0:
            return {"event": events[0]}
        else:
            return {"event": None, "message": "No upcoming events found"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting next event: {str(e)}")


# Define models for confirmed operations
class ConfirmedEventOperation(BaseModel):
    """Model for a confirmed event operation from the confirmation flow"""
    operation: str  # create_event, update_event, delete_event
    details: Dict[str, Any]  # The original parameters passed to the operation


@router.post("/confirmed-operation")
async def execute_confirmed_operation(operation_data: ConfirmedEventOperation = Body(...), session_id: str = "default"):
    """Execute a calendar operation that has been confirmed by the user.
    This bypasses the agent and directly calls the appropriate calendar service method.
    """
    calendar = get_calendar_service(session_id)
    operation = operation_data.operation
    details = operation_data.details
    
    try:
        # Handle different operations
        if operation == "create_event":
            # Extract parameters from details
            summary = details.get("summary")
            start_time = details.get("start_time")
            end_time = details.get("end_time")
            description = details.get("description", "")
            location = details.get("location", "")
            calendar_id = details.get("calendar_id", "primary")
            
            # Validate required parameters
            if not summary:
                raise HTTPException(status_code=400, detail="Event summary is required")
            if not start_time:
                raise HTTPException(status_code=400, detail="Event start time is required")
            if not end_time:
                raise HTTPException(status_code=400, detail="Event end time is required")
            
            # Create the event
            event = calendar.create_event(
                summary=summary,
                start_time=start_time,
                end_time=end_time,
                description=description,
                location=location
            )
            
            return {
                "status": "success",
                "message": f"Event '{summary}' has been created successfully.",
                "event": event
            }
            
        elif operation == "update_event":
            # Extract parameters
            event_id = details.get("event_id")
            summary = details.get("summary")
            start_time = details.get("start_time")
            end_time = details.get("end_time")
            description = details.get("description")
            location = details.get("location")
            calendar_id = details.get("calendar_id", "primary")
            
            # Validate required parameters
            if not event_id:
                raise HTTPException(status_code=400, detail="Event ID is required")
            if not summary and not start_time and not end_time and not description and not location:
                raise HTTPException(status_code=400, detail="At least one field must be updated")
            
            # Update the event
            event = calendar.update_event(
                event_id=event_id,
                summary=summary,
                start_time=start_time,
                end_time=end_time,
                description=description,
                location=location
            )
            
            return {
                "status": "success",
                "message": f"Event '{summary}' has been updated successfully.",
                "event": event
            }
            
        elif operation == "delete_event":
            # Extract parameters
            event_id = details.get("event_id")
            calendar_id = details.get("calendar_id", "primary")
            
            # Validate required parameters
            if not event_id:
                raise HTTPException(status_code=400, detail="Event ID is required")
            
            # Delete the event
            success = calendar.delete_event(
                event_id=event_id,
                calendar_id=calendar_id
            )
            
            if success:
                return {
                    "status": "success",
                    "message": "Event deleted successfully."
                }
            else:
                return {
                    "status": "error",
                    "message": "Failed to delete event."
                }
        
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported operation: {operation}")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error executing confirmed operation: {str(e)}")
