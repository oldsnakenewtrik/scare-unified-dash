"""
WebSocket server implementation for the SCARE Unified Dashboard
"""
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import List, Dict, Any
import json
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("websocket")

# Create a connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.logger = logging.getLogger("websocket")
        
    async def connect(self, websocket: WebSocket):
        # Log connection attempt with client information
        client = f"{websocket.client.host}:{websocket.client.port}"
        self.logger.info(f"WebSocket connection attempt from {client}")
        
        # Accept the connection
        await websocket.accept()
        self.active_connections.append(websocket)
        self.logger.info(f"WebSocket connection accepted from {client}. Total connections: {len(self.active_connections)}")
        
        # Send a welcome message
        await websocket.send_text(json.dumps({
            "type": "connection_established",
            "message": "Connected to SCARE Unified Dashboard WebSocket server",
            "timestamp": datetime.now().isoformat()
        }))
        
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        self.logger.info(f"WebSocket disconnected. Remaining connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except Exception as e:
            self.logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: str):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                self.logger.error(f"Error broadcasting message: {e}")
                disconnected.append(connection)
        
        # Remove disconnected clients
        for conn in disconnected:
            if conn in self.active_connections:
                self.disconnect(conn)

# Function to add WebSocket endpoints to a FastAPI app
def add_websocket_endpoints(app: FastAPI) -> FastAPI:
    """
    Add WebSocket endpoints to the FastAPI app.
    """
    manager = ConnectionManager()
    
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        # Accept the connection
        await manager.connect(websocket)
        
        try:
            # Handle messages in a loop
            while True:
                # Wait for a message from the client
                data = await websocket.receive_text()
                
                # Log the received message
                logger.info(f"Received message: {data[:100]}...")
                
                try:
                    # Parse the message as JSON
                    message = json.loads(data)
                    
                    # Process the message based on its type
                    if message.get("type") == "ping":
                        # Respond to ping messages
                        await websocket.send_text(json.dumps({
                            "type": "pong",
                            "timestamp": datetime.now().isoformat()
                        }))
                    else:
                        # Broadcast the message to all connected clients
                        await manager.broadcast(data)
                except json.JSONDecodeError:
                    # If the message is not valid JSON, just broadcast it as text
                    await manager.broadcast(data)
                    
        except WebSocketDisconnect:
            # Handle disconnection
            manager.disconnect(websocket)
            await manager.broadcast(json.dumps({
                "type": "client_disconnected",
                "timestamp": datetime.now().isoformat()
            }))
        except Exception as e:
            # Handle other exceptions
            logger.error(f"WebSocket error: {e}")
            manager.disconnect(websocket)

    @app.get("/api/ws-status")
    async def get_websocket_status():
        return {
            "active_connections": len(manager.active_connections),
            "status": "running"
        }

    logger.info("WebSocket endpoints added to the application")
    return app
