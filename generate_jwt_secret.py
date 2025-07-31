"""
Generate a secure JWT secret key for your application.
Run this script to create a random secret and update your .env file.
"""
import secrets
import os
import re
from pathlib import Path

def generate_secret(length=64):
    """Generate a secure random string of specified length."""
    return secrets.token_urlsafe(length)

def update_env_file(env_file_path, new_secret):
    """Update the JWT_SECRET in the .env file."""
    # Read the current .env file
    with open(env_file_path, 'r') as file:
        content = file.read()
    
    # Replace the JWT_SECRET line
    pattern = r'(JWT_SECRET=)(.+)'
    updated_content = re.sub(pattern, f'\\1{new_secret}', content)
    
    # Write the updated content back
    with open(env_file_path, 'w') as file:
        file.write(updated_content)

if __name__ == "__main__":
    # Generate a new secret
    new_secret = generate_secret()
    print(f"Generated new JWT secret: {new_secret}")
    
    # Find and update .env file
    env_path = Path(__file__).parent / '.env'
    
    if env_path.exists():
        update_env_file(env_path, new_secret)
        print(f"Updated JWT_SECRET in {env_path}")
    else:
        print(f"Error: .env file not found at {env_path}")
        print(f"Please manually add this secret to your environment: JWT_SECRET={new_secret}")
