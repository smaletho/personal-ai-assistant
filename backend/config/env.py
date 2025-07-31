"""
Environment configuration loader.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Find the .env file in parent directories
BASE_DIR = Path(__file__).resolve().parent.parent.parent
env_path = BASE_DIR / '.env'

# Load environment variables from .env file
load_dotenv(dotenv_path=env_path)

# Helper function to get environment variables with defaults
def get_env_variable(var_name, default=None):
    """
    Get an environment variable or return the default.
    
    Args:
        var_name: Name of the environment variable
        default: Default value to return if not found
        
    Returns:
        The environment variable value or default
    """
    return os.environ.get(var_name, default)

# Ensure critical environment variables are set
def validate_env():
    """
    Validate that all required environment variables are set.
    Raises ValueError if any required variable is missing.
    """
    required_vars = [
        'GOOGLE_CLIENT_ID',
        'GOOGLE_CLIENT_SECRET',
        'JWT_SECRET'
    ]
    
    missing = []
    for var in required_vars:
        if not get_env_variable(var):
            missing.append(var)
    
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
