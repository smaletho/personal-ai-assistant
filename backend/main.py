#!/usr/bin/env python
"""
Main entry point for the AI Calendar Assistant backend API.
"""
import os
import uvicorn
from dotenv import load_dotenv
from backend.utils.logging_config import get_logger

# Setup logging using centralized configuration
logger = get_logger("backend")

# Load environment variables
load_dotenv()

# Import the API app
from backend.api import app

def main():
    """Run the API server."""
    # Get port from environment or use default
    port = int(os.getenv("PORT", "8000"))
    
    # Print startup banner
    print(f"""
    ╔══════════════════════════════════════════════╗
    ║   AI Calendar Assistant API                  ║
    ║                                              ║
    ║   API documentation: http://localhost:{port}/docs  ║
    ║   ReDoc: http://localhost:{port}/redoc             ║
    ╚══════════════════════════════════════════════╝
    """)
    
    # Run the app with uvicorn
    uvicorn.run(
        "backend.api:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    main()
