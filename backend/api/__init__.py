from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
import os
from backend.utils.logging_config import get_logger
from backend.config.auth_config import get_google_oauth_settings

# Setup logging using centralized configuration
logger = get_logger("api")

# Create FastAPI app
app = FastAPI(
    title="AI Calendar Assistant API",
    description="API for interacting with the AI Calendar Assistant",
    version="1.0.0"
)

# Get settings for secret key
settings = get_google_oauth_settings()

# Add session middleware (must be added before CORS middleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.JWT_SECRET,  # Use the same secret as JWT for simplicity
    max_age=3600,  # 1 hour session
)

# Configure CORS with proper settings for cookies and authentication
frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")

# For development, allow both localhost origins with different ports
allow_origins = [frontend_url]
if "localhost" in frontend_url or "127.0.0.1" in frontend_url:
    # Add common development ports
    for port in ["3000", "3001", "8000", "8080"]:
        if f"localhost:{port}" not in allow_origins and f"127.0.0.1:{port}" not in allow_origins:
            allow_origins.append(f"http://localhost:{port}")
            allow_origins.append(f"http://127.0.0.1:{port}")

logger.info(f"Configuring CORS with origins: {allow_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,  # Important for cookies
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=["Content-Type", "Set-Cookie", "Authorization", "Accept", 
                  "Origin", "X-Requested-With", "Access-Control-Request-Method", 
                  "Access-Control-Request-Headers", "X-CSRF-Token"],
    expose_headers=["Content-Type", "Set-Cookie", "Authorization", "Access-Control-Allow-Credentials"],
    max_age=600,  # Cache preflight requests for 10 minutes
)

# Import and include routers
from backend.api.routes import chat, calendar, tasks, auth

# Include routers with proper prefixes
app.include_router(auth.router)  # Auth router has its own prefix ('/auth')
app.include_router(chat.router)
app.include_router(calendar.router, prefix="/calendar")
app.include_router(tasks.router, prefix="/tasks")

@app.get("/")
async def root():
    """Root endpoint providing API information."""
    return {
        "status": "ok",
        "message": "AI Calendar Assistant API is running",
        "version": "1.0.0",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "endpoints": {
            "chat": "/chat",
            "websocket": "/chat/ws/{session_id}",
            "calendars": "/calendar",
            "events": "/calendar/events",
            "tasks": "/tasks"
        }
    }
