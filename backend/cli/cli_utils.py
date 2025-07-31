"""
Shared utilities for CLI modules.
Provides common functionality to reduce duplication across CLI interfaces.
"""
import os
import sys
from typing import Optional, Any, Dict, List, Callable
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table
from rich.prompt import Prompt, Confirm

# Console instance for rich output
console = Console()

def check_credentials_file(file_path: str = 'credentials.json') -> bool:
    """
    Check if credentials file exists and show error if missing.
    
    Args:
        file_path: Path to the credentials file
        
    Returns:
        True if file exists, False otherwise
    """
    if not os.path.exists(file_path):
        console.print(Panel(
            "[bold red]Error:[/bold red] credentials.json file not found.\n\n"
            f"Please download your OAuth credentials from Google Cloud Console and save as [bold]{file_path}[/bold] "
            "in the project directory.",
            title="Missing Credentials",
            border_style="red"
        ))
        return False
    return True

def display_error(error: Any, title: str = "Error") -> None:
    """
    Display error message consistently.
    
    Args:
        error: Error object or message
        title: Panel title
    """
    console.print(Panel(
        f"[bold red]Error:[/bold red] {str(error)}",
        title=title,
        border_style="red"
    ))

def display_success(message: str, title: str = "Success") -> None:
    """
    Display success message consistently.
    
    Args:
        message: Success message
        title: Panel title
    """
    console.print(Panel(
        message,
        title=title,
        border_style="green"
    ))

def display_info(message: str, title: str = "Information") -> None:
    """
    Display informational message consistently.
    
    Args:
        message: Information message
        title: Panel title
    """
    console.print(Panel(
        message,
        title=title,
        border_style="blue"
    ))

def display_warning(message: str, title: str = "Warning") -> None:
    """
    Display warning message consistently.
    
    Args:
        message: Warning message
        title: Panel title
    """
    console.print(Panel(
        message,
        title=title,
        border_style="yellow"
    ))

def confirm_action(message: str) -> bool:
    """
    Request user confirmation for an action with consistent styling.
    
    Args:
        message: Confirmation message
        
    Returns:
        True if confirmed, False otherwise
    """
    return Confirm.ask(f"[bold yellow]{message}[/bold yellow]")

def display_help_markdown(help_text: str) -> None:
    """
    Display help text as markdown with consistent styling.
    
    Args:
        help_text: Markdown-formatted help text
    """
    console.print(Markdown(help_text))

def create_table(title: str, columns: List[str], 
                 caption: Optional[str] = None) -> Table:
    """
    Create a consistently styled rich table.
    
    Args:
        title: Table title
        columns: List of column names
        caption: Optional table caption
        
    Returns:
        Styled Table object ready for rows to be added
    """
    table = Table(title=title, caption=caption)
    
    # Add columns with appropriate styling
    for i, column in enumerate(columns):
        # Alternate column styles for better readability
        style = "green" if i % 2 == 0 else "cyan"
        table.add_column(column, style=style)
    
    return table

def safe_execution(func: Callable, error_message: str = "Operation failed", 
                   success_message: Optional[str] = None) -> Any:
    """
    Execute a function with consistent error handling.
    
    Args:
        func: Function to execute
        error_message: Message to display on error
        success_message: Optional message to display on success
        
    Returns:
        Result of the function if successful
    """
    try:
        result = func()
        if success_message:
            display_success(success_message)
        return result
    except Exception as e:
        display_error(f"{error_message}: {str(e)}")
        return None

def initialize_app(title: str, description: str) -> None:
    """
    Initialize CLI application with consistent header.
    
    Args:
        title: Application title
        description: Application description
    """
    console.print(Panel(
        f"{description}\n\n"
        "Type 'quit', 'exit', or 'bye' to end the session.",
        title=title,
        border_style="blue"
    ))
