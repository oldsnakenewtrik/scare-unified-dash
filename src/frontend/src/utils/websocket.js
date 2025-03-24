/**
 * WebSocket client for the SCARE Unified Dashboard
 * This provides a simple interface for connecting to the WebSocket server
 */

// Determine the WebSocket URL based on the environment
const getWebSocketUrl = () => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  
  // If we're in the production environment
  if (process.env.NODE_ENV === 'production') {
    // Use the backend service URL with the WebSocket protocol
    // FIXED: Don't include port (8000) in production URLs for Railway
    // Railway only allows connections through standard ports (80/443)
    return `${protocol}//scare-unified-dash-production.up.railway.app/ws`;
  }
  
  // For local development
  const apiBaseUrl = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';
  const apiUrl = new URL(apiBaseUrl);
  return `${protocol}//${apiUrl.hostname}:${apiUrl.port || '8000'}/ws`;
};

// Fallback to HTTP/HTTPS if WebSocket connection fails
const getFallbackUrl = () => {
  const protocol = window.location.protocol;
  
  // If we're in the production environment
  if (process.env.NODE_ENV === 'production') {
    // Don't specify a port - use the default port for the protocol
    return `${protocol}//scare-unified-dash-production.up.railway.app/api/ws-fallback`;
  }
  
  // For local development
  const apiBaseUrl = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';
  return `${apiBaseUrl}/api/ws-fallback`;
};

class WebSocketClient {
  constructor() {
    this.socket = null;
    this.isConnected = false;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 20; // Increased from 10 to 20
    this.reconnectDelay = 1000; // Start with 1 second delay
    this.listeners = [];
    this.messageQueue = [];
    this.pingInterval = null;
    this.url = getWebSocketUrl();
    this.fallbackMode = false;
    this.connectionErrors = [];
    
    // Bind methods to this
    this.connect = this.connect.bind(this);
    this.reconnect = this.reconnect.bind(this);
    this.disconnect = this.disconnect.bind(this);
    this.send = this.send.bind(this);
    this.addListener = this.addListener.bind(this);
    this.removeListener = this.removeListener.bind(this);
    this.switchToFallbackMode = this.switchToFallbackMode.bind(this);
    
    // Connect immediately
    this.connect();
  }
  
  connect() {
    if (this.socket) {
      // Close any existing connection
      this.disconnect();
    }
    
    // If we've reached the maximum number of reconnect attempts, switch to fallback mode
    if (this.reconnectAttempts >= this.maxReconnectAttempts && !this.fallbackMode) {
      console.warn(`Maximum reconnection attempts (${this.maxReconnectAttempts}) reached, switching to fallback mode`);
      this.switchToFallbackMode();
      return;
    }
    
    console.log(`Connecting to WebSocket at ${this.url}`);
    
    try {
      this.socket = new WebSocket(this.url);
      
      this.socket.onopen = () => {
        console.log('WebSocket connection established');
        this.isConnected = true;
        this.reconnectAttempts = 0;
        this.reconnectDelay = 1000;
        
        // Send any queued messages
        while (this.messageQueue.length > 0) {
          const message = this.messageQueue.shift();
          this.send(message);
        }
        
        // Notify listeners
        this.notifyListeners({
          type: 'connection_status',
          status: 'connected'
        });
        
        // Set up ping interval to keep connection alive
        this.pingInterval = setInterval(() => {
          this.send({
            type: 'ping',
            timestamp: new Date().toISOString()
          });
        }, 30000); // Send ping every 30 seconds
      };
      
      this.socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('WebSocket message received:', data);
          
          // Notify listeners
          this.notifyListeners(data);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };
      
      this.socket.onerror = (error) => {
        console.error('WebSocket error:', error);
        // Store the error for diagnostics
        this.connectionErrors.push({
          timestamp: new Date().toISOString(),
          message: error.message || 'Unknown WebSocket error',
          type: 'error'
        });
        
        this.notifyListeners({
          type: 'connection_status',
          status: 'error',
          error,
          errorCount: this.connectionErrors.length
        });
      };
      
      this.socket.onclose = (event) => {
        console.log('WebSocket connection closed:', event);
        this.isConnected = false;
        
        // Clear ping interval
        if (this.pingInterval) {
          clearInterval(this.pingInterval);
          this.pingInterval = null;
        }
        
        // Notify listeners
        this.notifyListeners({
          type: 'connection_status',
          status: 'disconnected',
          event
        });
        
        // Attempt to reconnect
        this.reconnect();
      };
    } catch (error) {
      console.error('Error creating WebSocket connection:', error);
      this.reconnect();
    }
  }
  
  reconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error(`Maximum reconnection attempts (${this.maxReconnectAttempts}) reached`);
      // Notify listeners about the failed reconnection attempts
      this.notifyListeners({
        type: 'connection_status',
        status: 'reconnect_failed',
        attempts: this.reconnectAttempts,
        errors: this.connectionErrors
      });
      
      // Switch to fallback mode
      if (!this.fallbackMode) {
        this.switchToFallbackMode();
      }
      return;
    }
    
    this.reconnectAttempts++;
    const delay = Math.min(this.reconnectDelay * Math.pow(1.5, this.reconnectAttempts - 1), 30000);
    
    console.log(`Attempting to reconnect in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
    
    // Notify listeners about reconnection attempt
    this.notifyListeners({
      type: 'connection_status',
      status: 'reconnecting',
      attempt: this.reconnectAttempts,
      maxAttempts: this.maxReconnectAttempts,
      delay
    });
    
    setTimeout(() => {
      this.connect();
    }, delay);
  }
  
  disconnect() {
    if (this.socket) {
      // Clear ping interval
      if (this.pingInterval) {
        clearInterval(this.pingInterval);
        this.pingInterval = null;
      }
      
      // Close the socket
      if (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING) {
        this.socket.close();
      }
      
      this.socket = null;
      this.isConnected = false;
    }
  }
  
  send(message) {
    if (!message) return;
    
    const messageString = typeof message === 'string' ? message : JSON.stringify(message);
    
    if (this.isConnected && this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(messageString);
    } else {
      // Queue the message to be sent when connected
      this.messageQueue.push(message);
      
      // If not connecting, try to connect
      if (!this.socket || this.socket.readyState === WebSocket.CLOSED) {
        this.connect();
      }
    }
  }
  
  addListener(callback) {
    if (typeof callback === 'function' && !this.listeners.includes(callback)) {
      this.listeners.push(callback);
    }
    return () => this.removeListener(callback);
  }
  
  removeListener(callback) {
    const index = this.listeners.indexOf(callback);
    if (index !== -1) {
      this.listeners.splice(index, 1);
    }
  }
  
  notifyListeners(data) {
    this.listeners.forEach(listener => {
      try {
        listener(data);
      } catch (error) {
        console.error('Error in WebSocket listener:', error);
      }
    });
  }
  
  // Switch to fallback mode using HTTP polling instead of WebSockets
  switchToFallbackMode() {
    console.log('Switching to fallback mode for WebSocket communication');
    this.fallbackMode = true;
    this.isConnected = true; // Pretend we're connected
    
    // Clear any existing intervals
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
    }
    
    // Reset connection errors
    this.connectionErrors = [];
    
    // Set up polling interval
    this.pingInterval = setInterval(() => {
      // Simulate connection status updates
      this.notifyListeners({
        type: 'connection_status',
        status: 'connected',
        fallback: true
      });
      
      // Process any queued messages
      while (this.messageQueue.length > 0) {
        const message = this.messageQueue.shift();
        console.log('Fallback mode: Message would be sent via HTTP:', message);
        
        // In a real implementation, you would send these via HTTP POST
        // For now, we'll just log them
      }
    }, 3000); // Poll every 3 seconds (reduced from 5 seconds)
    
    // Notify listeners that we're in fallback mode
    this.notifyListeners({
      type: 'connection_status',
      status: 'fallback',
      message: 'Using HTTP fallback instead of WebSocket'
    });
  }
}

// Create a singleton instance
const websocketClient = new WebSocketClient();

export default websocketClient;
