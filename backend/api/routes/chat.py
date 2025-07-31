"""
Chat API routes.
"""
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Query, status
from typing import Optional, Dict, Any, Union
import json
import uuid
import datetime
import time
import asyncio
import jwt
import logging
import traceback

from backend.services.agent_service import AgentCalendarAssistant
from backend.config.auth_config import get_google_oauth_settings
from backend.models.database import get_db, SessionLocal
from backend.models.user import User
from backend.utils.connection_manager import ConnectionManager
from backend.utils.websocket_session import WebSocketSession, WebSocketSessionState

# Setup logging
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/chat",
    tags=["chat"],
    responses={404: {"description": "Not found"}},
)

# Create a connection manager instance
manager = ConnectionManager()


async def verify_token(token: str, session_id: str) -> Optional[User]:
    """
    Verify the JWT token and return the user if valid.
    
    Args:
        token: The JWT token to verify
        session_id: The session ID for logging purposes
        
    Returns:
        User object if token is valid, None otherwise
    """
    if not token:
        logger.warning(f"Session {session_id[:8]}: No token provided")
        return None
        
    try:
        # Get OAuth settings
        oauth_settings = get_google_oauth_settings()
        
        # Decode the JWT token
        try:
            payload = jwt.decode(
                token, 
                oauth_settings.JWT_SECRET_KEY, 
                algorithms=[oauth_settings.JWT_ALGORITHM]
            )
        except jwt.PyJWTError as e:
            logger.error(f"Session {session_id[:8]}: JWT validation failed: {str(e)}")
            return None
            
        # Extract user information
        user_id = payload.get("sub")
        if not user_id:
            logger.error(f"Session {session_id[:8]}: Missing user ID in token")
            return None
            
        # Get the user from database
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                logger.error(f"Session {session_id[:8]}: User {user_id} not found in database")
                return None
                
            logger.info(f"Session {session_id[:8]}: Authenticated user: {user.email}")
            return user
        except Exception as e:
            logger.error(f"Session {session_id[:8]}: Database error during authentication: {str(e)}")
            return None
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Session {session_id[:8]}: Authentication error: {str(e)}")
        return None


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time chat with the agent.
    
    This endpoint uses the WebSocketSession state machine for connection management.
    The connection flow is:
    1. Accept connection
    2. Wait for authentication message with JWT token
    3. Authenticate user and initialize agent
    4. Process messages
    """
    # Connect to WebSocket
    logger.info(f"WebSocket connection request for session {session_id[:8]}")
    success = await manager.connect(websocket, session_id)
    
    if not success:
        logger.warning(f"Failed to establish WebSocket connection for session {session_id[:8]}")
        return
    
    try:
        # Main message loop
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            # Get the current session
            session = manager.get_session(session_id)
            if not session:
                logger.error(f"No active session found for {session_id[:8]}")
                break
                
            # Parse the message
            try:
                message_data = json.loads(data)
                logger.debug(f"Received message type: {message_data.get('type')} for session {session_id[:8]}")
                if message_data.get('type') == 'authentication':
                    logger.info(f"Authentication message received for session {session_id[:8]}")
                    # Log token info (safely)
                    token = message_data.get('token')
                    if token:
                        token_preview = token[:10] + '...' if len(token) > 10 else token
                        logger.debug(f"Token received: {token_preview}")
                    else:
                        logger.warning(f"No token in authentication message for session {session_id[:8]}")
            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON message for session {session_id[:8]}: {data[:100]}...")
                await session.send_message({
                    "type": "error",
                    "content": "Invalid message format. Expected JSON."
                })
                continue
                
            # Extract message details
            message_type = message_data.get("type", "message")
            message_id = message_data.get("message_id", str(uuid.uuid4()))
            
            # Handle message based on session state and message type
            if message_type == "authentication":
                # Authentication message
                if session.state not in [WebSocketSessionState.CONNECTED, WebSocketSessionState.AUTH_FAILED]:
                    await session.send_message({
                        "type": "error",
                        "content": f"Authentication not expected in current state: {session.state.value}"
                    })
                    continue
                    
                # Extract authentication data
                token = message_data.get("token")
                if not token:
                    await session.send_message({
                        "type": "error",
                        "content": "Authentication failed: No token provided"
                    })
                    continue
                    
                # Verify the token and get user
                user = await verify_token(token, session_id)
                if not user:
                    await session.send_message({
                        "type": "error",
                        "content": "Authentication failed: Invalid token"
                    })
                    continue
                    
                # Create database session for this agent
                db = SessionLocal()
                
                # Authenticate the session with user and db
                logger.info(f"Authenticating session {session_id[:8]} for user {user.email}")
                auth_success = await manager.authenticate(session_id, user, db)
                
                if not auth_success:
                    logger.error(f"Failed to authenticate session {session_id[:8]} for user {user.email}")
                    db.close()
                    
                    # Session will have sent error message in authenticate method
                    continue
                    
                # Authentication and agent initialization is handled by the manager.authenticate method
                logger.info(f"Session {session_id[:8]} authenticated and agent initialized for {user.email}")
            
            elif message_type == "message":
                # Regular chat message
                if session.state != WebSocketSessionState.READY:
                    await session.send_message({
                        "type": "error", 
                        "content": f"Cannot process message: Assistant not ready (state: {session.state.value})"
                    })
                    
                    # If authenticated but not ready, try to initialize agent
                    if session.state == WebSocketSessionState.AUTHENTICATED:
                        logger.info(f"Attempting to initialize agent for session {session_id[:8]}")
                        await session.initialize_agent()
                    continue
                
                # Process the message
                user_message = message_data.get("content", "")
                if not user_message.strip():
                    await session.send_message({
                        "type": "error",
                        "content": "Empty message"
                    })
                    continue
                    
                # Process message and send response
                try:
                    # Start typing indicator
                    await manager.start_typing_indicator(session_id, duration=3)
                    
                    # Process the message
                    logger.info(f"Processing message from session {session_id[:8]}: {user_message[:50]}...")
                    response = await manager.process_message(session_id, user_message)
                    
                    if response:
                        # Send response to client
                        await session.send_message({
                            "type": "message",
                            "content": response,
                            "message_id": message_id,
                            "role": "assistant",
                            "timestamp": datetime.datetime.now().isoformat()
                        })
                except Exception as e:
                    logger.error(f"Error processing message for session {session_id[:8]}: {str(e)}")
                    await session.send_message({
                        "type": "error",
                        "content": f"Error processing message: {str(e)}",
                        "message_id": message_id
                    })
            
            elif message_type == "ping":
                # Handle ping message for keeping connection alive
                await session.send_message({
                    "type": "pong",
                    "timestamp": datetime.datetime.now().isoformat()
                })
                
            else:
                # Unknown message type
                await session.send_message({
                    "type": "error",
                    "content": f"Unknown message type: {message_type}"
                })
    
    except WebSocketDisconnect:
        # Normal disconnect
        logger.info(f"WebSocket disconnected for session {session_id[:8]}")
        await manager.disconnect(session_id)
    
    except Exception as e:
        # Unexpected error
        logger.error(f"Error in WebSocket connection for session {session_id[:8]}: {str(e)}")
        logger.error(traceback.format_exc())
        await manager.disconnect(session_id)
