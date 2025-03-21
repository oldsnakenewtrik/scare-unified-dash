import { useState, useEffect, useCallback } from 'react';
import websocketClient from '../utils/websocket';

/**
 * React hook for using WebSocket connections in components
 * @returns {Object} WebSocket state and methods
 */
const useWebSocket = () => {
  const [isConnected, setIsConnected] = useState(websocketClient.isConnected);
  const [messages, setMessages] = useState([]);
  const [error, setError] = useState(null);

  // Handle WebSocket open event
  const handleOpen = useCallback(() => {
    setIsConnected(true);
    setError(null);
  }, []);

  // Handle WebSocket close event
  const handleClose = useCallback(() => {
    setIsConnected(false);
  }, []);

  // Handle WebSocket error event
  const handleError = useCallback((err) => {
    setError(err);
  }, []);

  // Handle WebSocket message event
  const handleMessage = useCallback((data) => {
    setMessages((prevMessages) => [...prevMessages, data]);
  }, []);

  // Connect to WebSocket
  const connect = useCallback(() => {
    websocketClient.connect().catch((err) => {
      setError(err);
    });
  }, []);

  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    websocketClient.disconnect();
  }, []);

  // Send a message through WebSocket
  const send = useCallback((data) => {
    return websocketClient.send(data);
  }, []);

  // Clear received messages
  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  // Set up event listeners when the component mounts
  useEffect(() => {
    // Add event listeners
    websocketClient.addEventListener('open', handleOpen);
    websocketClient.addEventListener('close', handleClose);
    websocketClient.addEventListener('error', handleError);
    websocketClient.addEventListener('message', handleMessage);

    // Connect if not already connected
    if (!websocketClient.isConnected) {
      connect();
    } else {
      setIsConnected(true);
    }

    // Clean up event listeners when the component unmounts
    return () => {
      websocketClient.removeEventListener('open', handleOpen);
      websocketClient.removeEventListener('close', handleClose);
      websocketClient.removeEventListener('error', handleError);
      websocketClient.removeEventListener('message', handleMessage);
    };
  }, [handleOpen, handleClose, handleError, handleMessage, connect]);

  return {
    isConnected,
    messages,
    error,
    connect,
    disconnect,
    send,
    clearMessages
  };
};

export default useWebSocket;
