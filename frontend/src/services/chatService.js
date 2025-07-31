/**
 * Chat Service
 * Centralizes all API calls related to chat functionality
 * Provides both REST API and WebSocket communication
 */
import apiClient from './api';
import { v4 as uuidv4 } from 'uuid';

const BASE_PATH = '/chat';

/**
 * Chat service for handling chat API calls and WebSocket communication
 */
export const chatService = {
  // WebSocket connection
  socket: null,
  
  // Connection status
  connected: false,
  
  // Callback functions
  callbacks: {
    onMessage: null,
    onTyping: null,
    onError: null,
    onConnect: null,
    onDisconnect: null
  },
  
  // Session ID
  sessionId: null,
  
  /**
   * Initialize the chat service and store callbacks
   * @param {Object} callbacks - Callback functions
   * @param {Function} callbacks.onMessage - Called when a message is received
   * @param {Function} callbacks.onTyping - Called when typing status changes
   * @param {Function} callbacks.onError - Called when an error occurs
   * @param {Function} callbacks.onConnect - Called when connection is established
   * @param {Function} callbacks.onDisconnect - Called when connection is closed
   * @param {string} [sessionId] - Session ID (optional)
   * @returns {Object} This service instance for chaining
   */
  init(callbacks = {}, sessionId = null) {
    this.callbacks = { ...this.callbacks, ...callbacks };
    this.sessionId = sessionId || localStorage.getItem('chatSessionId') || uuidv4();
    
    // Store session ID for reconnection
    localStorage.setItem('chatSessionId', this.sessionId);
    
    return this;
  },
  
  /**
   * Connect to the WebSocket server
   * @returns {Promise<boolean>} True if connected successfully
   */
  connect() {
    return new Promise((resolve, reject) => {
      if (this.connected && this.socket) {
        resolve(true);
        return;
      }
      
      try {
        // Determine WebSocket URL based on current location
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}${BASE_PATH}/ws/${this.sessionId}`;
        
        this.socket = new WebSocket(wsUrl);
        
        this.socket.onopen = () => {
          this.connected = true;
          if (this.callbacks.onConnect) {
            this.callbacks.onConnect();
          }
          resolve(true);
        };
        
        this.socket.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            
            switch (data.type) {
              case 'message':
                if (this.callbacks.onMessage) {
                  this.callbacks.onMessage(data);
                }
                break;
              case 'typing':
                if (this.callbacks.onTyping) {
                  this.callbacks.onTyping(data.content);
                }
                break;
              case 'error':
                console.error('WebSocket error:', data.content);
                if (this.callbacks.onError) {
                  this.callbacks.onError(data.content);
                }
                break;
              default:
                console.log('Received WebSocket data:', data);
            }
          } catch (error) {
            console.error('Error parsing WebSocket message:', error);
          }
        };
        
        this.socket.onerror = (error) => {
          console.error('WebSocket error:', error);
          if (this.callbacks.onError) {
            this.callbacks.onError('WebSocket connection error');
          }
          reject(error);
        };
        
        this.socket.onclose = () => {
          this.connected = false;
          if (this.callbacks.onDisconnect) {
            this.callbacks.onDisconnect();
          }
        };
      } catch (error) {
        console.error('Error connecting to WebSocket:', error);
        if (this.callbacks.onError) {
          this.callbacks.onError('Failed to connect to chat service');
        }
        reject(error);
      }
    });
  },
  
  /**
   * Disconnect from the WebSocket server
   */
  disconnect() {
    if (this.socket) {
      this.socket.close();
      this.socket = null;
      this.connected = false;
    }
  },
  
  /**
   * Send a message through WebSocket
   * @param {string} message - Message text
   * @returns {boolean} True if sent successfully
   */
  sendMessage(message) {
    if (!this.connected || !this.socket) {
      if (this.callbacks.onError) {
        this.callbacks.onError('Not connected to chat service');
      }
      return false;
    }
    
    try {
      const messageData = {
        content: message,
        message_id: uuidv4(),
        timestamp: new Date().toISOString()
      };
      
      this.socket.send(JSON.stringify(messageData));
      return true;
    } catch (error) {
      console.error('Error sending message:', error);
      if (this.callbacks.onError) {
        this.callbacks.onError('Failed to send message');
      }
      return false;
    }
  },
  
  /**
   * Send a message using REST API (fallback)
   * @param {string} message - Message text
   * @param {string} [sessionId] - Session ID (optional)
   * @returns {Promise<Object>} Response data
   */
  async sendMessageHttp(message, sessionId = null) {
    try {
      const params = {};
      if (sessionId || this.sessionId) {
        params.session_id = sessionId || this.sessionId;
      }
      
      const response = await apiClient.post(BASE_PATH, { message }, { params });
      return response.data;
    } catch (error) {
      console.error('Error sending message via HTTP:', error);
      throw error;
    }
  }
};

export default chatService;
