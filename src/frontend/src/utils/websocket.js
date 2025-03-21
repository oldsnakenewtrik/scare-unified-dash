/**
 * WebSocket client for the SCARE Unified Dashboard
 * This provides a simple interface for connecting to the WebSocket server
 */

// Determine the WebSocket URL based on the environment
const getWebSocketUrl = () => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  
  // If we're in the Railway production environment
  if (window.location.hostname.includes('railway.app')) {
    // Use the backend service URL with the WebSocket protocol
    // Make sure we're using the correct port (no port in the URL for Railway)
    return `${protocol}//scare-unified-dash-production.up.railway.app/ws`;
  }
  
  // For local development
  const apiBaseUrl = process.env.REACT_APP_API_BASE_URL || 'http://localhost:5000';
  const apiUrl = new URL(apiBaseUrl);
  return `${protocol}//${apiUrl.hostname}:${apiUrl.port || '5000'}/ws`;
};

class WebSocketClient {
  constructor() {
    this.socket = null;
    this.isConnected = false;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 10;
    this.reconnectDelay = 1000; // Start with 1 second delay
    this.listeners = [];
    this.messageQueue = [];
    this.pingInterval = null;
    this.url = getWebSocketUrl();
    
    // Bind methods to this
    this.connect = this.connect.bind(this);
    this.reconnect = this.reconnect.bind(this);
    this.disconnect = this.disconnect.bind(this);
    this.send = this.send.bind(this);
    this.addListener = this.addListener.bind(this);
    this.removeListener = this.removeListener.bind(this);
    
    // Connect immediately
    this.connect();
  }
  
  connect() {
    if (this.socket) {
      // Close any existing connection
      this.disconnect();
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
        this.notifyListeners({
          type: 'connection_status',
          status: 'error',
          error
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
      console.error('Maximum reconnection attempts reached');
      return;
    }
    
    this.reconnectAttempts++;
    const delay = Math.min(this.reconnectDelay * Math.pow(1.5, this.reconnectAttempts - 1), 30000);
    
    console.log(`Attempting to reconnect in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
    
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
}

// Create a singleton instance
const websocketClient = new WebSocketClient();

export default websocketClient;
