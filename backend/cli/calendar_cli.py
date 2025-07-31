#!/usr/bin/env python
"""
Command-line interface for testing Google Calendar API integration.
"""
import os
import sys
import datetime
from pathlib import Path
import click

# Import shared CLI utilities
from backend.cli.cli_utils import (
    console, display_error, display_info, display_warning,
    display_success, check_credentials_file, display_help_markdown,
    create_table, confirm_action
)
from backend.utils.logging_config import get_logger

from google_calendar import GoogleCalendar

# Setup logging
logger = get_logger("calendar_cli")

@click.group()
def cli():
    """Google Calendar CLI - Test your Google Calendar integration."""
    # Check if credentials file exists
    if not check_credentials_file('credentials.json'):
        sys.exit(1)


@cli.command('calendars')
def list_calendars():
    """List all available calendars for your account."""
    try:
        from cli_config import list_available_calendars
        calendars = list_available_calendars()
        
        if not calendars:
            display_info("No calendars found.", "Calendars")
            return
        
        table = create_table("Available Calendars", ["ID", "Name"])
        
        for calendar in calendars:
            table.add_row(calendar['id'], calendar['name'])
        
        console.print(table)
    except Exception as e:
        logger.error(f"Error listing calendars: {e}")
        display_error(str(e))


@cli.command()
@click.option('--max', '-m', default=10, help='Maximum number of events to show')
@click.option('--days', '-d', default=30, help='Number of days to look ahead')
@click.option('--calendar', '-c', default='primary', help='Calendar ID or name to use')
def list(max, days, calendar):
    """List upcoming calendar events."""
    try:
        # Convert calendar name to ID if needed
        from cli_config import get_calendar_by_id_or_name
        calendar_info = get_calendar_by_id_or_name(calendar)
        calendar_id = calendar_info['id']
        calendar_name = calendar_info['name']
        
        calendar = GoogleCalendar(calendar_id=calendar_id)
        time_min = datetime.datetime.utcnow()
        time_max = time_min + datetime.timedelta(days=days)
        
        with console.status(f"[bold green]Fetching events from {calendar_name}...[/bold green]"):
            events = calendar.list_events(max_results=max, time_min=time_min, time_max=time_max)
        
        if not events:
            display_info(f"No upcoming events found in '{calendar_name}'.", "Calendar")
            return
        
        table = create_table(
            f"Upcoming Events (Next {days} days)", 
            ["ID", "Date", "Time", "Summary", "Location"]
        )
        
        for event in events:
            event_id = event['id'][:8] + "..."  # Truncate ID for display
            
            start = event['start'].get('dateTime', event['start'].get('date'))
            is_all_day = 'date' in event['start'] and 'dateTime' not in event['start']
            
            if is_all_day:
                date_str = start
                time_str = "All day"
            else:
                # Parse and format the datetime
                dt = datetime.datetime.fromisoformat(start.replace('Z', '+00:00'))
                date_str = dt.strftime('%Y-%m-%d')
                time_str = dt.strftime('%H:%M %p')
            
            summary = event.get('summary', 'No title')
            location = event.get('location', '')
            
            table.add_row(event_id, date_str, time_str, summary, location)
        
        console.print(table)
    
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")

@cli.command()
@click.argument('title')
@click.option('--start', '-s', required=True, help='Start time (YYYY-MM-DD HH:MM)')
@click.option('--end', '-e', required=True, help='End time (YYYY-MM-DD HH:MM)')
@click.option('--description', '-d', help='Event description')
@click.option('--location', '-l', help='Event location')
@click.option('--calendar', '-c', default='primary', help='Calendar ID or name to use')
def create(title, start, end, description, location, calendar):
    """Create a new calendar event."""
    try:
        # Convert calendar name to ID if needed
        from cli_config import get_calendar_by_id_or_name
        calendar_info = get_calendar_by_id_or_name(calendar)
        calendar_id = calendar_info['id']
        calendar_name = calendar_info['name']
        
        cal = GoogleCalendar(calendar_id=calendar_id)
        
        with console.status(f"[bold green]Creating event in {calendar_name}...[/bold green]"):
            event = cal.create_event(
                summary=title,
                start_time=start,
                end_time=end,
                description=description,
                location=location
            )
        
        display_success(f"Event created: [bold]{title}[/bold]", "Event Created")
    
    except Exception as e:
        logger.error(f"Error creating event: {e}")
        display_error(str(e))
        if "Invalid calendar" in str(e):
            console.print("Run [bold]python cli.py calendars[/bold] to see available calendars.")

@cli.command()
@click.argument('event_id')
def view(event_id):
    """View details of a specific event."""
    try:
        calendar = GoogleCalendar()
        
        with console.status("[bold green]Fetching event details...[/bold green]"):
            event = calendar.get_event(event_id)
        
        # Format start and end times
        start = event['start'].get('dateTime', event['start'].get('date'))
        end = event['end'].get('dateTime', event['end'].get('date'))
        
        # Get attendees if any
        attendees = event.get('attendees', [])
        attendee_list = "\n".join([f"- {a.get('email')} ({a.get('responseStatus')})" 
                                for a in attendees]) if attendees else "None"
        
        # Format output
        event_details = (
            f"[bold]Event:[/bold] {event['summary']}\n\n"
            f"[bold]Start:[/bold] {start}\n"
            f"[bold]End:[/bold] {end}\n"
            + (f"[bold]Location:[/bold] {event['location']}\n" if 'location' in event else "")
            + (f"[bold]Description:[/bold]\n{event['description']}" if 'description' in event else "")
        )
        display_info(event_details, f"Event Details: {event_id}")
    except Exception as e:
        logger.error(f"Error viewing event: {e}")
        display_error(str(e))

@cli.command()
@click.argument('event_id')
@click.option('--title', '-t', help='New title')
@click.option('--start', '-s', help='New start time (YYYY-MM-DD HH:MM)')
@click.option('--end', '-e', help='New end time (YYYY-MM-DD HH:MM)')
@click.option('--description', '-d', help='New description')
@click.option('--location', '-l', help='New location')
def update(event_id, title, start, end, description, location):
    """Update an existing calendar event."""
    try:
        calendar = GoogleCalendar()
        
        # Check if at least one field is being updated
        if not any([title, start, end, description, location]):
            console.print("[bold yellow]Warning:[/bold yellow] No fields specified for update.")
            return
        
        with console.status("[bold green]Updating event...[/bold green]"):
            event = calendar.update_event(
                event_id=event_id,
                summary=title,
                start_time=start,
                end_time=end,
                description=description,
                location=location
            )
        
        console.print(Panel(
            f"[bold]Event updated:[/bold] {event.get('summary')}\n"
            f"[bold]Start:[/bold] {event.get('start', {}).get('dateTime', 'N/A')}\n"
            f"[bold]End:[/bold] {event.get('end', {}).get('dateTime', 'N/A')}\n"
            f"[bold]ID:[/bold] {event.get('id')}",
            title="Event Updated",
            border_style="green"
        ))
    
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")

@cli.command()
@click.argument('event_id')
@click.option('--force/--no-force', default=False, help='Skip confirmation')
def delete(event_id, force):
    """Delete a calendar event."""
    try:
        calendar = GoogleCalendar()
        
        # First get the event to show what's being deleted
        with console.status("[bold green]Fetching event details...[/bold green]"):
            event = calendar.get_event(event_id)
        
        summary = event.get('summary', 'Unknown Event')
        start = event['start'].get('dateTime', event['start'].get('date'))
        
        # Confirm deletion
        if not force:
            message = f"You are about to delete: [bold]{summary}[/bold] on [bold]{start}[/bold]"
            if not confirm_action(message):
                display_warning("Deletion cancelled.")
                return
        
        # Delete the event
        with console.status("[bold green]Deleting event...[/bold green]"):
            success = calendar.delete_event(event_id)
        
        if success:
            display_success(f"Event '[bold]{summary}[/bold]' has been deleted.", "Event Deleted")
    
    except Exception as e:
        logger.error(f"Error deleting event: {e}")
        display_error(str(e))

@cli.command()
@click.option('--start', '-s', required=True, help='Start date (YYYY-MM-DD)')
@click.option('--end', '-e', required=True, help='End date (YYYY-MM-DD)')
def free_busy(start, end):
    """Check free/busy status for a date range."""
    try:
        calendar = GoogleCalendar()
        
        with console.status("[bold green]Checking availability...[/bold green]"):
            result = calendar.get_free_busy(start_time=start, end_time=end)
        
        calendars = result.get('calendars', {})
        primary_calendar = calendars.get(calendar.calendar_id, {})
        busy_periods = primary_calendar.get('busy', [])
        
        if not busy_periods:
            display_success(
                f"You are completely free from [bold]{start}[/bold] to [bold]{end}[/bold]", 
                "Availability"
            )
        else:
            table = create_table(f"Busy Periods from {start} to {end}", ["Start", "End"])
            
            for period in busy_periods:
                start_time = period.get('start')
                end_time = period.get('end')
                
                # Format times for better readability
                start_dt = datetime.datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                end_dt = datetime.datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                
                start_str = start_dt.strftime('%Y-%m-%d %H:%M')
                end_str = end_dt.strftime('%Y-%m-%d %H:%M')
                
                table.add_row(start_str, end_str)
            
            console.print(table)
    
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")

@cli.command()
def help():
    """Show detailed help instructions."""
    help_text = """
# Google Calendar CLI Help

This tool helps you interact with your Google Calendar from the command line.

## Setup

Before using this tool, make sure you have:
1. Created a project in Google Cloud Console
2. Enabled the Google Calendar API
3. Created OAuth credentials (Desktop application)
4. Downloaded credentials as `credentials.json` in this directory

## Examples

### List your upcoming events
```
python cli.py list
python cli.py list --max 5 --days 7
```

### Create a new event
```
python cli.py create "Meeting with Team" --start "2023-01-01 10:00" --end "2023-01-01 11:00" --location "Conference Room" --description "Weekly team sync"
```

### View event details
```
python cli.py view EVENT_ID
```

### Update an event
```
python cli.py update EVENT_ID --title "New Title" --start "2023-01-01 11:00" --end "2023-01-01 12:00"
```

### Delete an event
```
python cli.py delete EVENT_ID
```

### Check free/busy status
```
python cli.py free-busy --start "2023-01-01" --end "2023-01-07"
```
"""
    display_help_markdown(help_text)

if __name__ == '__main__':
    cli()
