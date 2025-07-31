import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { v4 as uuidv4 } from 'uuid';

// Import auth context
import { useAuth } from './AuthContext';

// Create the chat context
const ChatContext = createContext();

// Custom hook for using the chat context
export const useChat = () => useContext(ChatContext);

export const ChatProvider = ({ children }) => {
  const { user, isAuthenticated } = useAuth();
  const [messages, setMessages] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [socket, setSocket] = useState(null);
  const [sessionId, setSessionId] = useState(() => {
    // Get sessionId from localStorage or create a new one
    const savedSessionId = localStorage.getItem('chatSessionId');
    return savedSessionId || uuidv4();
  });

  // Track reconnection attempts and backoff
  const [reconnectAttempts, setReconnectAttempts] = useState(0);
  const [reconnectTimer, setReconnectTimer] = useState(null);
  const [isReconnecting, setIsReconnecting] = useState(false);
  const [lastDisconnectReason, setLastDisconnectReason] = useState(null);
  const MAX_RECONNECT_ATTEMPTS = 10;
  
  // Calculate backoff time based on attempts (exponential with jitter)
  const calculateBackoffTime = useCallback((attempts) => {
    // Base is 500ms, with exponential increase and maximum of 30 seconds
    const base = 500;
    const exponential = Math.min(Math.pow(2, attempts), 60) * base;
    // Add random jitter (±15%)
    const jitter = exponential * (0.85 + (Math.random() * 0.3));
    return Math.min(jitter, 30000); // Cap at 30 seconds
  }, []);
  
  // Connect to WebSocket with improved reconnection strategy
  const connectWebSocket = useCallback(() => {
    // Don't attempt connection if currently in reconnecting state
    if (isReconnecting) {
      console.log('Already in reconnection process, skipping new attempt');
      return;
    }
    
    // More robust connection check
    if (!isAuthenticated) {
      console.log('Not connecting WebSocket - user not authenticated');
      return; // Not authenticated
    }
    
    // Check if we already have a valid connection
    if (socket !== null) {
      if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) {
        console.log('WebSocket already connected or connecting - skipping reconnection');
        return; // Already connected or connecting
      } else {
        // Clean up existing socket that's closing or closed
        console.log('Cleaning up existing socket before creating a new one');
        try {
          // Important: Remove all handlers before closing to prevent reconnection loops
          socket.onclose = null; // Remove existing handlers
          socket.onerror = null;
          socket.onmessage = null;
          socket.onopen = null;
          socket.close();
        } catch (e) {
          console.warn('Error cleaning up socket:', e);
        }
      }
    }
    
    // Apply exponential backoff based on reconnection attempts
    const backoffTime = reconnectAttempts > 0 ? calculateBackoffTime(reconnectAttempts) : 0;
    
    console.log(`Scheduling connection attempt in ${backoffTime}ms (attempt #${reconnectAttempts + 1})`);
    setIsReconnecting(true);
    
    // Clear any existing reconnect timer
    if (reconnectTimer !== null) {
      clearTimeout(reconnectTimer);
    }
    
    // Set new reconnect timer with exponential backoff
    const timerId = setTimeout(() => {
      _createNewWebSocketConnection();
      setIsReconnecting(false);
    }, backoffTime);
    
    setReconnectTimer(timerId);
  }, [isAuthenticated, socket, reconnectAttempts, reconnectTimer, isReconnecting, calculateBackoffTime]);
  
  // Log auth tokens in all possible locations to help debug where they're stored
  useEffect(() => {
    if (isAuthenticated) {
      console.log('=== AUTH DEBUG INFO ===');
      console.log('auth_token:', localStorage.getItem('auth_token'));
      console.log('token:', localStorage.getItem('token'));
      console.log('session_token:', localStorage.getItem('session_token'));
      
      const sessionTokenCookie = document.cookie.split('; ').find(row => row.startsWith('session_token='));
      console.log('session_token cookie:', sessionTokenCookie);
      console.log('=== END AUTH DEBUG INFO ===');
    }
  }, [isAuthenticated]);

  // Extract actual connection creation to a separate function
  const _createNewWebSocketConnection = useCallback(() => {
    // Don't create a connection if we're not authenticated
    if (!isAuthenticated) {
      console.log('Not creating WebSocket - not authenticated');
      return;
    }
    
    // Clear any existing reconnect timers
    if (reconnectTimer !== null) {
      clearTimeout(reconnectTimer);
      setReconnectTimer(null);
    }
    
    console.log('Creating new WebSocket connection...');
    // Only include session in URL path, no longer sending user email as query param
    const ws = new WebSocket(`ws://localhost:8000/chat/ws/${sessionId}`);
    
    // Track when the connection was initiated
    const connectionStartTime = Date.now();

    ws.onopen = () => {
      const connectionTime = Date.now() - connectionStartTime;
      console.log(`WebSocket connected in ${connectionTime}ms`);
      setIsConnected(true);
      // Reset reconnection attempts on successful connection
      setReconnectAttempts(0);
      
      // Send authentication message as the first message after connection
      // This is more secure than including the token in the URL
      if (isAuthenticated && user) {
        try {
          // Get auth token from various possible sources in order of precedence
          let authToken = localStorage.getItem('auth_token');
          
          // If no token in localStorage, try to extract from cookies as fallback
          if (!authToken) {
            console.log('No token in localStorage, attempting to extract from cookies');
            const cookieToken = document.cookie
              .split('; ')
              .find(row => row.startsWith('session_token='))?.split('=')[1];
            
            if (cookieToken) {
              console.log('Found token in cookies, will use for WebSocket auth');
              authToken = cookieToken;
              // Save it to localStorage for future use
              try {
                localStorage.setItem('auth_token', cookieToken);
                console.log('Saved cookie token to localStorage for consistent auth');
              } catch (e) {
                console.warn('Failed to save token to localStorage:', e);
                // Continue using the token for this session even if storage fails
              }
            }
          }
          
          if (authToken) {
            console.log('Sending authentication message with token');
            // Small delay to ensure the connection is fully established
            setTimeout(() => {
              if (ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({
                  type: 'authentication',
                  token: authToken,
                  email: user.email
                }));
                console.log('WebSocket authentication message sent successfully');
              } else {
                console.warn('Unable to send WebSocket auth message - connection not open');
              }
            }, 100);
          } else {
            console.error('No auth token available from any source for WebSocket authentication');
            // Notify user about authentication issue
            setMessages(prev => [...prev, {
              content: 'Authentication error: Unable to authenticate with the assistant. Please try logging out and back in.',
              role: 'system',
              timestamp: new Date().toISOString(),
              isError: true
            }]);
          }
        } catch (error) {
          console.error('Error sending authentication message:', error);
        }
      }
    };

    ws.onclose = (event) => {
      console.log('WebSocket disconnected', event.code, event.reason);
      setIsConnected(false);
      console.log(`WebSocket connection closed. Code: ${event.code}, Reason: ${event.reason || 'No reason provided'}`);
      
      // Store the disconnect reason for user feedback and debugging
      setLastDisconnectReason(event.reason || 'Connection closed');
      
      const connectionTime = Date.now() - connectionStartTime;
      
      // If the connection lasted a reasonable time, reset the reconnection attempts
      // This prevents eventual reconnection lockout if the server is temporarily unavailable
      if (connectionTime > 10000) {  // More than 10 seconds is considered stable - increased from 5 to match backend
        setReconnectAttempts(0);
        console.log('Connection was stable (10+ seconds), resetting reconnection attempts');
      } else {
        console.log(`Short-lived connection (${connectionTime}ms), may indicate problems`);
      }
      
      // Don't auto-reconnect for certain close codes
      if (event.code === 1008 || event.code === 1011) {
        console.log(`Not reconnecting due to policy violation or server error: code ${event.code}`);
        setMessages(prev => [...prev, {
          id: uuidv4(),
          content: `Connection closed: ${event.reason || 'Server error'}. Please refresh the page.`,
          role: "system",
          timestamp: new Date().toISOString(),
          isError: true
        }]);
        return;
      }
      
      // Handle reconnection policy feedback from server (code 1013)
      if (event.code === 1013) {
        console.log(`Server requested delayed reconnection: ${event.reason}`);
        // Extract any suggested wait time from the reason
        const waitMatch = event.reason?.match(/(\d+(\.\d+)?)\s*seconds/);
        const suggestedWaitTime = waitMatch ? parseFloat(waitMatch[1]) * 1000 : null;
        
        // Use suggested wait time from server if available, otherwise use our own backoff
        const currentAttempts = reconnectAttempts + 1;
        setReconnectAttempts(currentAttempts);
        
        // Use either server-suggested wait time or our calculated backoff, with a minimum threshold
        const reconnectDelay = Math.max(
          suggestedWaitTime || calculateBackoffTime(currentAttempts),
          1000 // Minimum 1 second
        );
        
        console.log(`Will reconnect in ${reconnectDelay}ms per server guidance`);
        
        const timerId = setTimeout(() => {
          connectWebSocket();
        }, reconnectDelay);
        
        setReconnectTimer(timerId);
        return;
      }
      
      // Standard reconnection logic with exponential backoff
      const currentAttempts = reconnectAttempts + 1;
      if (currentAttempts <= MAX_RECONNECT_ATTEMPTS) {
        setReconnectAttempts(currentAttempts);
        
        // Use exponential backoff function
        const reconnectDelay = calculateBackoffTime(currentAttempts);
        console.log(`Attempting reconnection in ${reconnectDelay}ms (attempt ${currentAttempts}/${MAX_RECONNECT_ATTEMPTS})`);
        
        const timerId = setTimeout(() => {
          console.log(`Reconnecting now (attempt ${currentAttempts}/${MAX_RECONNECT_ATTEMPTS})`);
          connectWebSocket();
        }, reconnectDelay);
        
        setReconnectTimer(timerId);
      } else {
        console.log('Maximum reconnection attempts reached. Please refresh the page.');
        // Add an error message for the user
        setMessages(prev => [...prev, {
          id: uuidv4(),
          content: "Connection lost after multiple reconnection attempts. Please refresh the page.",
          role: "system",
          timestamp: new Date().toISOString(),
          isError: true
        }]);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      ws.close();
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log('Received message:', data);

      switch (data.type) {
        case 'message':
          // Add assistant message to chat
          setMessages(prev => [...prev, {
            id: data.message_id || uuidv4(),
            content: data.content,
            role: data.role || 'assistant',
            timestamp: data.timestamp || new Date().toISOString()
          }]);
          break;

        case 'typing':
          setIsTyping(Boolean(data.content));
          break;

        case 'error':
          console.error('Error from server:', data.content);
          // Add error message to chat
          setMessages(prev => [...prev, {
            id: data.message_id || uuidv4(),
            content: `Error: ${data.content}`,
            role: 'system',
            timestamp: new Date().toISOString(),
            isError: true
          }]);
          break;

        case 'system':
          console.log('System message:', data.content);
          break;

        default:
          console.warn('Unknown message type:', data.type);
      }
    };

    setSocket(ws);
  }, [isAuthenticated, sessionId, user, reconnectTimer, reconnectAttempts, socket]);

  // Save session ID when user changes
  useEffect(() => {
    if (isAuthenticated && user?.email) {
      const userSessionKey = `chatSessionId_${user.email}`;
      localStorage.setItem(userSessionKey, sessionId);
      localStorage.setItem('chatSessionId', sessionId); // Keep for compatibility
      console.log(`Session ID ${sessionId.substring(0, 8)}... saved for user ${user.email}`);
    } else if (isAuthenticated) {
      localStorage.setItem('chatSessionId', sessionId);
      console.log(`Session ID ${sessionId.substring(0, 8)}... saved (no user email)`);
    }
  }, [isAuthenticated, user, sessionId]);
  
  // Separate useEffect for connection management
  // This prevents race conditions and multiple connection attempts
  useEffect(() => {
    let mounted = true; // Track if component is mounted
    
    const initConnection = async () => {
      // Only connect if user is authenticated and component is still mounted
      if (isAuthenticated && mounted) {
        console.log('User authenticated, initializing WebSocket connection');
        // Reset reconnect attempts when intentionally connecting
        setReconnectAttempts(0);
        await connectWebSocket();
      }
    };
    
    // Only attempt connection if authenticated and we don't already have a valid socket
    if (isAuthenticated && (!socket || 
        (socket && socket.readyState !== WebSocket.OPEN && 
         socket.readyState !== WebSocket.CONNECTING))) {
      initConnection();
    } else if (!isAuthenticated && socket) {
      // Disconnect if not authenticated
      console.log('User not authenticated, closing any existing WebSocket connections');
      socket.close();
      setSocket(null);
    }
    
    // Cleanup function to prevent memory leaks and race conditions
    return () => {
      mounted = false; // Mark component as unmounted

      // Clean up any pending timers and close socket
      if (reconnectTimer !== null) {
        clearTimeout(reconnectTimer);
      }
      if (socket) {
        // Make sure to remove all handlers first
        try {
          socket.onclose = null;
          socket.onerror = null;
          socket.onmessage = null;
          socket.onopen = null;
          socket.close();
        } catch (e) {
          console.warn('Error during socket cleanup:', e);
        }
      }
    };
  }, [connectWebSocket, sessionId, isAuthenticated, user, reconnectTimer]);

  // Send a message
  const sendMessage = useCallback((content) => {
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      console.error('WebSocket not connected');
      return false;
    }

    const messageId = uuidv4();
    const message = {
      content,
      id: messageId,          // Use 'id' to match what ChatWindow expects
      message_id: messageId,  // Keep message_id for WebSocket protocol compatibility
      role: 'user',
      timestamp: new Date().toISOString()
    };

    // Add message to state immediately for better UX
    setMessages(prev => [...prev, message]);

    // Send message through WebSocket
    socket.send(JSON.stringify(message));
    return true;
  }, [socket]);

  // Clear conversation history
  const clearChat = useCallback(() => {
    setMessages([]);
  }, []);

  // The context value
  const value = {
    messages,
    isConnected,
    isTyping,
    isReconnecting,
    reconnectAttempts,
    lastDisconnectReason,
    sessionId,
    sendMessage,
    clearChat,
    connectWebSocket
  };

  return (
    <ChatContext.Provider value={value}>
      {children}
    </ChatContext.Provider>
  );
};

export default ChatContext;
