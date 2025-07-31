"""
WebSocket Session Management for the Chat API.
Implements a state machine for WebSocket connection lifecycle.
"""
import enum
import time
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import WebSocket
from sqlalchemy.orm import Session

from backend.models.user import User
from backend.services.agent_service import AgentCalendarAssistant

# Setup logging
logger = logging.getLogger(__name__)

class WebSocketSessionState(enum.Enum):
    """Enum to track the state of a WebSocket session."""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATING = "authenticating"
    AUTHENTICATED = "authenticated"
    READY = "ready"
    AUTH_FAILED = "auth_failed"
    ERROR = "error"
    RECONNECTING = "reconnecting"
    DISCONNECTING = "disconnecting" 
    DISCONNECTED = "disconnected"
    CLOSED = "closed"

class WebSocketSession:
    """
    Manages the lifecycle of a WebSocket connection with explicit state management.
    
    This class implements a state machine for handling WebSocket connections,
    authentication, and agent initialization in a predictable and recoverable way.
    """
    
    def __init__(self, session_id: str, websocket: WebSocket):
        """
        Initialize a new WebSocket session.
        
        Args:
            session_id: Unique identifier for this session
            websocket: The active WebSocket connection
        """
        self.session_id = session_id
        self.websocket = websocket
        self.state = WebSocketSessionState.CONNECTING
        self.user: Optional[User] = None
        self.agent: Optional[AgentCalendarAssistant] = None
        self.db: Optional[Session] = None
        self.connection_count = 1  # Track number of connection attempts
        self.last_reconnect_time = 0  # Last reconnection timestamp
        
        # Session metadata
        self.created_at = datetime.now()
        self.last_active = datetime.now()
        self.message_count = 0
        self.last_error = None
        
    async def accept_connection(self) -> bool:
        """
        Accept the WebSocket connection and transition to CONNECTED state.
        
        Returns:
            True if connection was accepted successfully, False otherwise
        """
        try:
            await self.websocket.accept()
            self.state = WebSocketSessionState.CONNECTED
            self.last_active = datetime.now()
            logger.debug(f"Session {self.session_id[:8]}: Connection accepted")
            return True
        except Exception as e:
            logger.error(f"Session {self.session_id[:8]}: Failed to accept connection: {str(e)}")
            self.state = WebSocketSessionState.ERROR
            self.last_error = str(e)
            return False
    
    async def send_message(self, message_data: Dict[str, Any]) -> bool:
        """
        Send a message to the client.
        
        Args:
            message_data: The message data to send
            
        Returns:
            True if message was sent successfully, False otherwise
        """
        try:
            await self.websocket.send_json(message_data)
            self.last_active = datetime.now()
            return True
        except Exception as e:
            logger.error(f"Session {self.session_id[:8]}: Error sending message: {str(e)}")
            self.last_error = str(e)
            return False
            
    async def authenticate(self, user: User, db: Session) -> bool:
        """
        Set the authenticated user and transition to AUTHENTICATED state.
        
        Args:
            user: The authenticated user
            db: Database session for this connection
            
        Returns:
            True if authentication was successful, False otherwise
        """
        if self.state not in [WebSocketSessionState.CONNECTED, WebSocketSessionState.AUTH_FAILED]:
            logger.warning(f"Session {self.session_id[:8]}: Cannot authenticate in {self.state} state")
            return False
            
        try:
            self.state = WebSocketSessionState.AUTHENTICATING
            # Store user and db session
            self.user = user
            self.db = db
            
            # Signal successful authentication
            await self.send_message({
                "type": "system",
                "content": "Authentication successful"
            })
            
            self.state = WebSocketSessionState.AUTHENTICATED
            self.last_active = datetime.now()
            logger.info(f"Session {self.session_id[:8]}: User authenticated: {user.email}")
            return True
        except Exception as e:
            logger.error(f"Session {self.session_id[:8]}: Authentication failed: {str(e)}")
            self.state = WebSocketSessionState.AUTH_FAILED
            self.last_error = str(e)
            
            # Send authentication failure message
            await self.send_message({
                "type": "error",
                "content": f"Authentication failed: {str(e)}"
            })
            return False
    
    async def initialize_agent(self) -> bool:
        """
        Initialize the agent with authenticated user and transition to READY state.
        
        This should only be called after successful authentication.
        
        Returns:
            True if agent was initialized successfully, False otherwise
        """
        if self.state != WebSocketSessionState.AUTHENTICATED:
            logger.warning(f"Session {self.session_id[:8]}: Cannot initialize agent in {self.state} state")
            return False
            
        if not self.user or not self.db:
            logger.error(f"Session {self.session_id[:8]}: Missing user or db for agent initialization")
            self.state = WebSocketSessionState.ERROR
            await self.send_message({
                "type": "error",
                "content": "Cannot initialize agent: Missing authentication data"
            })
            return False
            
        try:
            logger.debug(f"Session {self.session_id[:8]}: Initializing agent for user {self.user.email}")
            
            # Initialize the agent with proper authentication
            self.agent = AgentCalendarAssistant(user=self.user, db=self.db)
            
            # Signal successful initialization
            await self.send_message({
                "type": "system",
                "content": "Assistant ready"
            })
            
            self.state = WebSocketSessionState.READY
            self.last_active = datetime.now()
            logger.info(f"Session {self.session_id[:8]}: Agent initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Session {self.session_id[:8]}: Failed to initialize agent: {str(e)}")
            self.state = WebSocketSessionState.ERROR
            self.last_error = str(e)
            
            # Send initialization failure message
            await self.send_message({
                "type": "error",
                "content": f"Failed to initialize assistant: {str(e)}"
            })
            return False
    
    async def process_message(self, message: str) -> Optional[str]:
        """
        Process a message using the agent and return the response.
        
        Args:
            message: The message to process
            
        Returns:
            The agent's response, or None if processing failed
        """
        if self.state != WebSocketSessionState.READY:
            logger.warning(f"Session {self.session_id[:8]}: Cannot process message in {self.state} state")
            await self.send_message({
                "type": "error",
                "content": f"Cannot process message: Assistant not ready (current state: {self.state.value})"
            })
            return None
            
        if not self.agent:
            logger.error(f"Session {self.session_id[:8]}: No agent available to process message")
            self.state = WebSocketSessionState.ERROR
            await self.send_message({
                "type": "error",
                "content": "Assistant not initialized"
            })
            return None
            
        try:
            self.message_count += 1
            self.last_active = datetime.now()
            
            # Process the message and return the response
            response = self.agent.process_input(message)
            return response
        except Exception as e:
            logger.error(f"Session {self.session_id[:8]}: Error processing message: {str(e)}")
            self.last_error = str(e)
            await self.send_message({
                "type": "error",
                "content": f"Error processing message: {str(e)}"
            })
            return None
    
    async def handle_reconnection(self, websocket: WebSocket) -> bool:
        """
        Handle reconnection for this session.
        
        Args:
            websocket: The new WebSocket connection
            
        Returns:
            True if reconnection was handled successfully, False otherwise
        """
        # Track reconnection attempts
        self.connection_count += 1
        current_time = time.time()
        
        # Check if reconnecting too quickly
        if self.last_reconnect_time > 0:
            time_since_reconnect = current_time - self.last_reconnect_time
            
            # Apply backoff for rapid reconnections
            required_wait_time = min(0.5 * (2 ** min(self.connection_count - 1, 5)), 30)
            
            if time_since_reconnect < required_wait_time and self.connection_count > 3:
                logger.warning(f"Session {self.session_id[:8]}: Reconnecting too quickly ({time_since_reconnect:.2f}s)")
                try:
                    await websocket.close(
                        code=1013, 
                        reason=f"Reconnecting too quickly. Please wait {required_wait_time:.1f} seconds."
                    )
                except Exception:
                    pass
                return False
                
        # Update connection
        self.websocket = websocket
        self.last_reconnect_time = current_time
        
        # Accept the new connection
        try:
            await websocket.accept()
            
            # Determine state after reconnection
            if self.agent and self.user and self.db:
                # Was fully initialized before, restore to READY
                self.state = WebSocketSessionState.READY
                await self.send_message({
                    "type": "system",
                    "content": "Reconnected to assistant. Session restored."
                })
            elif self.user and self.db:
                # Was authenticated but agent may need re-initialization
                self.state = WebSocketSessionState.AUTHENTICATED
                # Try to re-initialize agent
                await self.initialize_agent()
            else:
                # Basic connection only
                self.state = WebSocketSessionState.CONNECTED
                await self.send_message({
                    "type": "system",
                    "content": "Reconnected. Please authenticate."
                })
                
            self.last_active = datetime.now()
            logger.info(f"Session {self.session_id[:8]}: Reconnection handled successfully, state: {self.state.value}")
            return True
        except Exception as e:
            logger.error(f"Session {self.session_id[:8]}: Failed to handle reconnection: {str(e)}")
            self.state = WebSocketSessionState.ERROR
            self.last_error = str(e)
            return False
    
    async def close(self, code: int = 1000, reason: str = "Session closed") -> bool:
        """
        Close the WebSocket connection and transition to CLOSED state.
        
        Args:
            code: WebSocket close code
            reason: Close reason
            
        Returns:
            True if closed successfully, False otherwise
        """
        if self.state == WebSocketSessionState.CLOSED:
            return True
            
        self.state = WebSocketSessionState.DISCONNECTING
        logger.debug(f"Session {self.session_id[:8]}: Closing connection")
        
        try:
            # Only try to close the connection if it might be open
            if self.state not in [WebSocketSessionState.DISCONNECTED, WebSocketSessionState.CLOSED]:
                try:
                    await self.websocket.close(code=code, reason=reason)
                except Exception as e:
                    logger.debug(f"Session {self.session_id[:8]}: Error closing WebSocket: {str(e)}")
                    
            # Clean up resources
            if self.db:
                try:
                    self.db.close()
                    logger.debug(f"Session {self.session_id[:8]}: Database connection closed")
                except Exception as e:
                    logger.warning(f"Session {self.session_id[:8]}: Error closing database: {str(e)}")
                    
            self.agent = None
            self.state = WebSocketSessionState.CLOSED
            logger.info(f"Session {self.session_id[:8]}: Connection closed: {reason}")
            return True
        except Exception as e:
            logger.error(f"Session {self.session_id[:8]}: Error during connection close: {str(e)}")
            self.state = WebSocketSessionState.ERROR
            self.last_error = str(e)
            return False
            
    def to_dict(self) -> Dict[str, Any]:
        """Return a dictionary representation of this session."""
        return {
            "session_id": self.session_id,
            "state": self.state.value,
            "user": self.user.email if self.user else None,
            "created_at": self.created_at.isoformat(),
            "last_active": self.last_active.isoformat(),
            "message_count": self.message_count,
            "connection_count": self.connection_count,
            "has_error": self.last_error is not None,
            "last_error": self.last_error
        }
