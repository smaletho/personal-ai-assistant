#!/usr/bin/env python
"""
Command-line interface for testing Google Tasks API integration.
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

from google_tasks import GoogleTasks

# Setup logging
logger = get_logger("tasks_cli")

@click.group()
def cli():
    """Google Tasks CLI - Test your Google Tasks integration."""
    # Check if credentials file exists
    if not check_credentials_file('credentials.json'):
        sys.exit(1)

@cli.group()
def tasklists():
    """Manage task lists."""
    pass

@tasklists.command('list')
@click.option('--account', '-a', default='default', help='Account name to use')
def list_tasklists(account):
    """List all task lists."""
    try:
        tasks_api = GoogleTasks(account_name=account)
        
        with console.status("[bold green]Fetching task lists...[/bold green]"):
            tasklists = tasks_api.list_tasklists()
        
        if not tasklists:
            display_info("No task lists found.", "Task Lists")
            return
        
        table = create_table(f"Task Lists ({account} account)", ["ID", "Title", "Updated"])
        
        for tasklist in tasklists:
            updated = tasklist.get('updated', '')
            if updated:
                # Format date
                updated = updated.split('T')[0]  # Simple format: YYYY-MM-DD
            
            table.add_row(
                tasklist.get('id', ''),
                tasklist.get('title', 'Untitled'),
                updated
            )
        
        console.print(table)
    
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")

@tasklists.command('create')
@click.argument('title')
@click.option('--account', '-a', default='default', help='Account name to use')
def create_tasklist(title, account):
    """Create a new task list."""
    try:
        tasks_api = GoogleTasks(account_name=account)
        
        with console.status("[bold green]Creating task list...[/bold green]"):
            tasklist = tasks_api.create_tasklist(title)
        
        display_success(
            f"[bold]Task List Created:[/bold] {tasklist.get('title')}\n"
            f"[bold]ID:[/bold] {tasklist.get('id')}",
            "Task List Created"
        )
    
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")

@tasklists.command('delete')
@click.argument('tasklist_id')
@click.option('--account', '-a', default='default', help='Account name to use')
@click.option('--force/--no-force', default=False, help='Skip confirmation')
def delete_tasklist(tasklist_id, account, force):
    """Delete a task list."""
    try:
        tasks_api = GoogleTasks(account_name=account)
        
        if not force:
            # Get task list details first
            with console.status("[bold green]Fetching task list details...[/bold green]"):
                tasklist = tasks_api.get_tasklist(tasklist_id)
            
            title = tasklist.get('title', 'Unknown task list')
            
            message = f"You are about to delete task list: [bold]{title}[/bold]"
            if not confirm_action(message):
                display_warning("Deletion cancelled.")
                return
        
        # Delete the task list
        with console.status("[bold green]Deleting task list...[/bold green]"):
            success = tasks_api.delete_tasklist(tasklist_id)
        
        if success:
            console.print(Panel(
                f"Task list has been deleted.",
                title="Task List Deleted",
                border_style="green"
            ))
    
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")

@cli.group()
def tasks():
    """Manage tasks."""
    pass

@tasks.command('list')
@click.option('--tasklist', '-l', default='@default', help='Task list ID')
@click.option('--account', '-a', default='default', help='Account name to use')
@click.option('--all/--no-all', default=False, help='Show all tasks including completed')
@click.option('--max', '-m', default=100, help='Maximum number of tasks to show')
def list_tasks(tasklist, account, all, max):
    """List tasks in a task list."""
    try:
        tasks_api = GoogleTasks(account_name=account)
        
        # Show different sets based on flag
        completed = None if all else False
        
        with console.status("[bold green]Fetching tasks...[/bold green]"):
            tasks = tasks_api.list_tasks(
                tasklist_id=tasklist,
                max_results=max,
                completed=completed
            )
        
        if not tasks:
            display_info(f"No tasks found in list '{tasklist}'.", "Tasks")
            return
        
        table = create_table(
            f"Tasks in '{tasklist}'", 
            ["ID", "Title", "Status", "Due Date"]
        )
        
        for task in tasks:
            # Extract data fields
            title = task.get('title', 'Untitled')
            notes = task.get('notes', '')
            status = task.get('status', 'needsAction')
            due_date = task.get('due', '')
            
            # Format due date if present
            if due_date:
                # Strip time part and 'Z' if present
                due_date = due_date.split('T')[0]
            
            # Format status for display
            status_disp = "✓" if status == 'completed' else "☐"
            
            table.add_row(
                task.get('id', ''),
                title,
                status_disp,
                due_date
            )
        
        console.print(table)
    
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")

@tasks.command('create')
@click.argument('title')
@click.option('--tasklist', '-l', default='@default', help='Task list ID')
@click.option('--account', '-a', default='default', help='Account name to use')
@click.option('--notes', '-n', help='Task notes/description')
@click.option('--due', '-d', help='Due date (YYYY-MM-DD)')
def create_task(title, tasklist, account, notes, due):
    """Create a new task."""
    try:
        tasks_api = GoogleTasks(account_name=account)
        
        # Format due date if provided
        due_str = None
        if due:
            due_date = datetime.datetime.strptime(due, "%Y-%m-%d")
            # Google Tasks API expects RFC 3339 format
            due_str = due_date.isoformat() + 'Z'
        
        with console.status("[bold green]Creating task...[/bold green]"):
            task = tasks_api.create_task(
                tasklist_id=tasklist,
                title=title,
                notes=notes,
                due=due_str
            )
        
        display_success(
            f"[bold]Task Created:[/bold] {task.get('title')}\n"
            f"[bold]ID:[/bold] {task.get('id')}",
            "Task Created"
        )
    
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        display_error(str(e))

@tasks.command('complete')
@click.argument('task_id')
@click.option('--tasklist', '-l', default='@default', help='Task list ID')
@click.option('--account', '-a', default='default', help='Account name to use')
def complete_task(task_id, tasklist, account):
    """Mark a task as completed."""
    try:
        tasks_api = GoogleTasks(account_name=account)
        
        with console.status("[bold green]Completing task...[/bold green]"):
            task = tasks_api.complete_task(
                tasklist_id=tasklist,
                task_id=task_id
            )
        
        display_success(
            f"Task '{task.get('title')}' has been updated.",
            "Task Updated"
        )
    
    except Exception as e:
        logger.error(f"Error updating task: {e}")
        display_error(str(e))

@tasks.command('update')
@click.argument('task_id')
@click.option('--tasklist', '-l', default='@default', help='Task list ID')
@click.option('--account', '-a', default='default', help='Account name to use')
@click.option('--title', '-t', help='New task title')
@click.option('--notes', '-n', help='New task notes/description')
@click.option('--due', '-d', help='New due date (YYYY-MM-DD)')
def update_task(task_id, tasklist, account, title, notes, due):
    """Update an existing task."""
    try:
        tasks_api = GoogleTasks(account_name=account)
        
        # Check if at least one field is being updated
        if not any([title, notes, due]):
            console.print("[bold yellow]Warning:[/bold yellow] No fields specified for update.")
            return
        
        # Format due date if provided
        due_str = None
        if due:
            due_date = datetime.datetime.strptime(due, "%Y-%m-%d")
            # Google Tasks API expects RFC 3339 format
            due_str = due_date.isoformat() + 'Z'
        
        with console.status("[bold green]Updating task...[/bold green]"):
            task = tasks_api.update_task(
                tasklist_id=tasklist,
                task_id=task_id,
                title=title,
                notes=notes,
                due=due_str
            )
        
        console.print(Panel(
            f"[bold]Task Updated:[/bold] {task.get('title')}\n"
            f"[bold]Due:[/bold] {task.get('due', 'Not set')}\n"
            f"[bold]ID:[/bold] {task.get('id')}",
            title="Task Updated",
            border_style="green"
        ))
    
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")

@tasks.command('delete')
@click.argument('task_id')
@click.option('--tasklist', '-l', default='@default', help='Task list ID')
@click.option('--account', '-a', default='default', help='Account name to use')
@click.option('--force/--no-force', default=False, help='Skip confirmation')
def delete_task(task_id, tasklist, account, force):
    """Delete a task."""
    try:
        tasks_api = GoogleTasks(account_name=account)
        
        if not force:
            # Get task details first
            with console.status("[bold green]Fetching task details...[/bold green]"):
                task = tasks_api.get_task(tasklist_id=tasklist, task_id=task_id)
            
            title = task.get('title', 'Unknown task')
            
            message = f"You are about to delete task: [bold]{title}[/bold]"
            if not confirm_action(message):
                display_warning("Deletion cancelled.")
                return
        
        # Delete the task
        with console.status("[bold green]Deleting task...[/bold green]"):
            success = tasks_api.delete_task(tasklist_id=tasklist, task_id=task_id)
        
        if success:
            display_success("Task has been deleted.", "Task Deleted")
    
    except Exception as e:
        logger.error(f"Error deleting task: {e}")
        display_error(str(e))

@tasks.command('clear')
@click.option('--tasklist', '-l', default='@default', help='Task list ID')
@click.option('--account', '-a', default='default', help='Account name to use')
@click.option('--force/--no-force', default=False, help='Skip confirmation')
def clear_completed(tasklist, account, force):
    """Clear all completed tasks."""
    try:
        tasks_api = GoogleTasks(account_name=account)
        
        if not force:
            message = f"You are about to clear all completed tasks from list '{tasklist}'."
            if not confirm_action(message):
                display_warning("Operation cancelled.")
                return
        
        with console.status("[bold green]Clearing completed tasks...[/bold green]"):
            success = tasks_api.clear_completed(tasklist_id=tasklist)
        
        if success:
            display_success(
                f"All completed tasks have been cleared from list '{tasklist}'.",
                "Tasks Cleared"
            )
    
    except Exception as e:
        logger.error(f"Error clearing completed tasks: {e}")
        display_error(str(e))

@cli.command()
def help():
    """Show detailed help instructions."""
    help_text = """
# Google Tasks CLI Help

This tool helps you interact with Google Tasks from the command line.

## Setup

Before using this tool, make sure you have:
1. Created a project in Google Cloud Console
2. Enabled the Google Tasks API
3. Created OAuth credentials (Desktop application)
4. Downloaded credentials as `credentials.json` in this directory

## Examples

### List task lists
```
python tasks_cli.py tasklists list
python tasks_cli.py tasklists list --account work
```

### Create a new task list
```
python tasks_cli.py tasklists create "Personal Tasks"
```

### List tasks in a task list
```
python tasks_cli.py tasks list
python tasks_cli.py tasks list --tasklist "TASKLIST_ID" --all
```

### Create a new task
```
python tasks_cli.py tasks create "Buy groceries" --due "2023-06-30" --notes "Need milk and eggs"
```

### Mark a task as completed
```
python tasks_cli.py tasks complete TASK_ID
```

### Update a task
```
python tasks_cli.py tasks update TASK_ID --title "New title" --due "2023-07-01"
```

### Delete a task
```
python tasks_cli.py tasks delete TASK_ID
```

### Clear all completed tasks
```
python tasks_cli.py tasks clear
```
"""
    display_help_markdown(help_text)

if __name__ == '__main__':
    cli()
