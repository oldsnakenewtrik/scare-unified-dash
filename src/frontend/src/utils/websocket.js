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
    this.maxReconnectAttempts = 5;
    this.reconnectTimeout = null;
    this.listeners = {
      message: [],
      open: [],
      close: [],
      error: []
    };
  }

  /**
   * Connect to the WebSocket server
   * @returns {Promise} Resolves when connected, rejects if connection fails
   */
  connect() {
    return new Promise((resolve, reject) => {
      if (this.isConnected) {
        resolve();
        return;
      }

      try {
        const wsUrl = getWebSocketUrl();
        console.log(`Connecting to WebSocket at ${wsUrl}`);
        
        this.socket = new WebSocket(wsUrl);
        
        this.socket.onopen = () => {
          console.log('WebSocket connection established');
          this.isConnected = true;
          this.reconnectAttempts = 0;
          this._notifyListeners('open');
          resolve();
        };
        
        this.socket.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            this._notifyListeners('message', data);
          } catch (error) {
            console.error('Error parsing WebSocket message:', error);
            this._notifyListeners('error', { type: 'parse_error', error });
          }
        };
        
        this.socket.onclose = (event) => {
          console.log(`WebSocket connection closed: ${event.code} ${event.reason}`);
          this.isConnected = false;
          this._notifyListeners('close', event);
          
          // Attempt to reconnect if not a normal closure
          if (event.code !== 1000 && event.code !== 1001) {
            this._attemptReconnect();
          }
        };
        
        this.socket.onerror = (error) => {
          console.error('WebSocket error:', error);
          this._notifyListeners('error', error);
          reject(error);
        };
      } catch (error) {
        console.error('Error creating WebSocket connection:', error);
        reject(error);
      }
    });
  }

  /**
   * Disconnect from the WebSocket server
   */
  disconnect() {
    if (this.socket && this.isConnected) {
      this.socket.close(1000, 'Normal closure');
      this.isConnected = false;
    }
    
    // Clear any pending reconnect attempts
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
  }

  /**
   * Send a message to the WebSocket server
   * @param {Object} data Data to send
   * @returns {boolean} True if sent successfully, false otherwise
   */
  send(data) {
    if (!this.isConnected) {
      console.error('Cannot send message: WebSocket is not connected');
      return false;
    }
    
    try {
      const message = typeof data === 'string' ? data : JSON.stringify(data);
      this.socket.send(message);
      return true;
    } catch (error) {
      console.error('Error sending WebSocket message:', error);
      return false;
    }
  }

  /**
   * Add an event listener
   * @param {string} event Event type ('message', 'open', 'close', 'error')
   * @param {Function} callback Callback function
   */
  addEventListener(event, callback) {
    if (this.listeners[event]) {
      this.listeners[event].push(callback);
    }
  }

  /**
   * Remove an event listener
   * @param {string} event Event type
   * @param {Function} callback Callback function to remove
   */
  removeEventListener(event, callback) {
    if (this.listeners[event]) {
      this.listeners[event] = this.listeners[event].filter(cb => cb !== callback);
    }
  }

  /**
   * Attempt to reconnect to the WebSocket server
   * @private
   */
  _attemptReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error(`Maximum reconnect attempts (${this.maxReconnectAttempts}) reached`);
      return;
    }
    
    this.reconnectAttempts++;
    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
    
    console.log(`Attempting to reconnect in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
    
    this.reconnectTimeout = setTimeout(() => {
      this.connect().catch(error => {
        console.error('Reconnect attempt failed:', error);
      });
    }, delay);
  }

  /**
   * Notify all listeners of an event
   * @param {string} event Event type
   * @param {*} data Event data
   * @private
   */
  _notifyListeners(event, data) {
    if (this.listeners[event]) {
      this.listeners[event].forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          console.error(`Error in ${event} listener:`, error);
        }
      });
    }
  }
}

// Create a singleton instance
const websocketClient = new WebSocketClient();

export default websocketClient;
