"""
Database initialization script.
Run this script to create all necessary tables in the database.
"""
from sqlalchemy import create_engine
import logging
import os
from pathlib import Path

# Add parent directory to path so we can import our modules
import sys
parent_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(parent_dir))

from models.database import Base, engine
from models.user import User, OAuthToken
from config.env import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_db():
    """
    Initialize the database by creating all tables.
    """
    try:
        # Create tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully.")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise

if __name__ == "__main__":
    # Initialize the database
    init_db()
    logger.info("Database initialization complete.")
