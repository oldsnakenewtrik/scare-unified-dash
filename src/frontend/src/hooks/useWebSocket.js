import { useState, useEffect, useCallback } from 'react';
import websocketClient from '../utils/websocket';

/**
 * React hook for using WebSocket connections in components
 * @returns {Object} WebSocket state and methods
 */
const useWebSocket = () => {
  const [isConnected, setIsConnected] = useState(false);
  const [messages, setMessages] = useState([]);
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [error, setError] = useState(null);

  // Handle WebSocket messages and status updates
  const handleWebSocketEvent = useCallback((data) => {
    if (data.type === 'connection_status') {
      setConnectionStatus(data.status);
      setIsConnected(data.status === 'connected');
      
      if (data.status === 'error' && data.error) {
        setError(data.error);
      } else if (data.status === 'connected') {
        setError(null);
      }
    } else {
      // Add message to the messages array
      setMessages((prevMessages) => [...prevMessages, data]);
    }
  }, []);

  // Send a message through WebSocket
  const send = useCallback((data) => {
    websocketClient.send(data);
  }, []);

  // Clear received messages
  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  // Set up event listeners when the component mounts
  useEffect(() => {
    // Add event listener
    const removeListener = websocketClient.addListener(handleWebSocketEvent);
    
    // Set initial connection status
    setIsConnected(websocketClient.isConnected);
    
    // Clean up event listener when the component unmounts
    return () => {
      removeListener();
    };
  }, [handleWebSocketEvent]);

  return {
    isConnected,
    connectionStatus,
    messages,
    error,
    send,
    clearMessages
  };
};

export default useWebSocket;
