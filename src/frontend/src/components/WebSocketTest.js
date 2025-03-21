import React, { useState, useEffect } from 'react';
import useWebSocket from '../hooks/useWebSocket';

const WebSocketTest = () => {
  const { isConnected, connectionStatus, messages, error, send, clearMessages } = useWebSocket();
  const [message, setMessage] = useState('');

  // Display the last 10 messages
  const displayMessages = messages.slice(-10);

  // Send a message
  const handleSendMessage = () => {
    if (message.trim()) {
      send({
        type: 'message',
        content: message,
        timestamp: new Date().toISOString()
      });
      setMessage('');
    }
  };

  // Send a ping message
  const handleSendPing = () => {
    send({
      type: 'ping',
      timestamp: new Date().toISOString()
    });
  };

  // Format connection status with color
  const getStatusColor = () => {
    switch (connectionStatus) {
      case 'connected':
        return 'green';
      case 'disconnected':
        return 'red';
      case 'error':
        return 'orange';
      default:
        return 'gray';
    }
  };

  return (
    <div style={{ padding: '20px', maxWidth: '600px', margin: '0 auto' }}>
      <h2>WebSocket Test</h2>
      
      {/* Connection Status */}
      <div style={{ marginBottom: '20px' }}>
        <p>
          <strong>Connection Status:</strong>{' '}
          <span style={{ color: getStatusColor() }}>
            {connectionStatus} {isConnected ? '(Connected)' : '(Disconnected)'}
          </span>
        </p>
        {error && (
          <p style={{ color: 'red' }}>
            <strong>Error:</strong> {error.message || JSON.stringify(error)}
          </p>
        )}
      </div>
      
      {/* Message Input */}
      <div style={{ marginBottom: '20px', display: 'flex', gap: '10px' }}>
        <input
          type="text"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
          placeholder="Type a message..."
          style={{ 
            padding: '8px', 
            borderRadius: '4px', 
            border: '1px solid #ccc',
            flexGrow: 1
          }}
          disabled={!isConnected}
        />
        <button
          onClick={handleSendMessage}
          disabled={!isConnected || !message.trim()}
          style={{ 
            padding: '8px 16px', 
            backgroundColor: isConnected ? '#4CAF50' : '#ccc',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: isConnected ? 'pointer' : 'not-allowed'
          }}
        >
          Send
        </button>
      </div>
      
      {/* Action Buttons */}
      <div style={{ marginBottom: '20px', display: 'flex', gap: '10px' }}>
        <button
          onClick={handleSendPing}
          disabled={!isConnected}
          style={{ 
            padding: '8px 16px', 
            backgroundColor: isConnected ? '#2196F3' : '#ccc',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: isConnected ? 'pointer' : 'not-allowed'
          }}
        >
          Send Ping
        </button>
        <button
          onClick={clearMessages}
          style={{ 
            padding: '8px 16px', 
            backgroundColor: '#f44336',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer'
          }}
        >
          Clear Messages
        </button>
      </div>
      
      {/* Messages */}
      <div>
        <h3>Messages ({messages.length})</h3>
        {displayMessages.length === 0 ? (
          <p>No messages yet</p>
        ) : (
          <ul style={{ 
            listStyleType: 'none', 
            padding: 0,
            maxHeight: '300px',
            overflowY: 'auto',
            border: '1px solid #eee',
            borderRadius: '4px'
          }}>
            {displayMessages.map((msg, index) => (
              <li 
                key={index}
                style={{ 
                  padding: '10px', 
                  borderBottom: index < displayMessages.length - 1 ? '1px solid #eee' : 'none',
                  backgroundColor: msg.type === 'pong' ? '#f0f8ff' : 'white'
                }}
              >
                <div><strong>Type:</strong> {msg.type}</div>
                {msg.content && <div><strong>Content:</strong> {msg.content}</div>}
                {msg.timestamp && (
                  <div>
                    <strong>Time:</strong> {new Date(msg.timestamp).toLocaleTimeString()}
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};

export default WebSocketTest;
