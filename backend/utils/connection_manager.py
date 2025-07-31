"""
Connection Manager for WebSocket connections.
Manages active WebSocket sessions using the WebSocketSession state machine.
"""
import asyncio
import logging
from typing import Dict, Optional, Any, List

from fastapi import WebSocket
from sqlalchemy.orm import Session

from backend.models.user import User
from backend.services.agent_service import AgentCalendarAssistant
from backend.utils.websocket_session import WebSocketSession, WebSocketSessionState

# Setup logging
logger = logging.getLogger(__name__)

class ConnectionManager:
    """
    Manages WebSocket connections and session state.
    
    This class maintains a registry of active WebSocket sessions and provides
    methods for connection management, authentication, and message handling.
    """
    
    def __init__(self):
        """Initialize the connection manager."""
        self.sessions: Dict[str, WebSocketSession] = {}
        self.typing_tasks: Dict[str, asyncio.Task] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str) -> bool:
        """
        Connect a WebSocket client and create or update a session.
        
        Args:
            websocket: The WebSocket connection
            session_id: Unique identifier for this session
            
        Returns:
            True if connection was successful, False otherwise
        """
        logger.debug(f"Connection request for session {session_id[:8]}")
        
        if session_id in self.sessions:
            # Existing session - handle reconnection
            logger.info(f"Handling reconnection for session {session_id[:8]}")
            session = self.sessions[session_id]
            return await session.handle_reconnection(websocket)
        else:
            # New session - create and initialize
            logger.info(f"Creating new session for {session_id[:8]}")
            session = WebSocketSession(session_id, websocket)
            success = await session.accept_connection()
            
            if success:
                self.sessions[session_id] = session
                # Send welcome message
                await session.send_message({
                    "type": "system",
                    "content": "Connected to assistant. Please authenticate to continue."
                })
                
            return success
    
    async def disconnect(self, session_id: str) -> None:
        """
        Disconnect a client and clean up resources.
        
        Args:
            session_id: ID of the session to disconnect
        """
        if session_id not in self.sessions:
            logger.warning(f"Cannot disconnect non-existent session {session_id[:8]}")
            return
            
        session = self.sessions[session_id]
        
        # Cancel any typing indicators
        if session_id in self.typing_tasks and not self.typing_tasks[session_id].done():
            self.typing_tasks[session_id].cancel()
            
        # Close the session
        await session.close()
        
        # Remove from active sessions if fully closed
        if session.state == WebSocketSessionState.CLOSED:
            self.sessions.pop(session_id, None)
            logger.info(f"Session {session_id[:8]} removed from active sessions")
    
    async def authenticate(self, session_id: str, user: User, db: Session) -> bool:
        """
        Authenticate a session with user credentials.
        
        Args:
            session_id: ID of the session to authenticate
            user: The authenticated user
            db: Database session
            
        Returns:
            True if authentication was successful, False otherwise
        """
        if session_id not in self.sessions:
            logger.warning(f"Cannot authenticate non-existent session {session_id[:8]}")
            return False
            
        session = self.sessions[session_id]
        success = await session.authenticate(user, db)
        
        if success:
            # If authentication successful, initialize the agent
            await session.initialize_agent()
            
        return success
    
    async def send_message(self, session_id: str, data: Dict[str, Any]) -> bool:
        """
        Send a message to a specific session.
        
        Args:
            session_id: ID of the session to send to
            data: Message data to send
            
        Returns:
            True if message was sent successfully, False otherwise
        """
        if session_id not in self.sessions:
            logger.warning(f"Cannot send message to non-existent session {session_id[:8]}")
            return False
            
        return await self.sessions[session_id].send_message(data)
    
    async def process_message(self, session_id: str, message: str) -> Optional[str]:
        """
        Process a message for a session and return the response.
        
        Args:
            session_id: ID of the session
            message: The message to process
            
        Returns:
            The agent's response, or None if processing failed
        """
        if session_id not in self.sessions:
            logger.warning(f"Cannot process message for non-existent session {session_id[:8]}")
            return None
            
        # Start typing indicator for better UX
        await self.start_typing_indicator(session_id)
            
        # Process message with the session's agent
        return await self.sessions[session_id].process_message(message)
    
    async def send_typing_indicator(self, session_id: str, duration: int = 2) -> None:
        """
        Send a typing indicator to the client that lasts for the specified duration.
        
        Args:
            session_id: ID of the session to send to
            duration: Duration in seconds for the typing indicator
        """
        if session_id not in self.sessions:
            return
            
        try:
            # Start typing indicator
            await self.sessions[session_id].send_message({
                "type": "typing",
                "content": "start"
            })
            
            # Wait for specified duration
            await asyncio.sleep(duration)
            
            # Stop typing indicator
            if session_id in self.sessions:
                await self.sessions[session_id].send_message({
                    "type": "typing",
                    "content": "stop"
                })
        except Exception as e:
            logger.error(f"Error in typing indicator for {session_id[:8]}: {str(e)}")
    
    async def start_typing_indicator(self, session_id: str, duration: int = 2) -> None:
        """
        Start a typing indicator as a background task.
        
        Args:
            session_id: ID of the session to send to
            duration: Duration in seconds for the typing indicator
        """
        if session_id in self.typing_tasks and not self.typing_tasks[session_id].done():
            self.typing_tasks[session_id].cancel()
            
        self.typing_tasks[session_id] = asyncio.create_task(
            self.send_typing_indicator(session_id, duration)
        )
    
    def get_session(self, session_id: str) -> Optional[WebSocketSession]:
        """
        Get a session by ID.
        
        Args:
            session_id: ID of the session
            
        Returns:
            The session if found, None otherwise
        """
        return self.sessions.get(session_id)
    
    def get_session_count(self) -> int:
        """Get the number of active sessions."""
        return len(self.sessions)
    
    def get_session_states(self) -> Dict[str, Dict[str, Any]]:
        """Get a dictionary of all session states."""
        return {
            session_id: session.to_dict()
            for session_id, session in self.sessions.items()
        }
    
    async def close_all_sessions(self) -> None:
        """Close all active sessions."""
        session_ids = list(self.sessions.keys())
        for session_id in session_ids:
            await self.disconnect(session_id)
            
        logger.info(f"Closed all {len(session_ids)} active sessions")
