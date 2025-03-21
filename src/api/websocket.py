"""
WebSocket server implementation for the SCARE Unified Dashboard
"""
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import List, Dict, Any
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("websocket")

# Create a connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"New WebSocket connection. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Remaining connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: str):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")
                disconnected.append(connection)
        
        # Remove disconnected clients
        for conn in disconnected:
            if conn in self.active_connections:
                self.disconnect(conn)

# Create a connection manager instance
manager = ConnectionManager()

# Function to add WebSocket endpoints to a FastAPI app
def add_websocket_endpoints(app: FastAPI):
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await manager.connect(websocket)
        try:
            while True:
                data = await websocket.receive_text()
                try:
                    message = json.loads(data)
                    logger.info(f"Received message: {message}")
                    
                    # Echo the message back to the client
                    await manager.send_personal_message(json.dumps({
                        "type": "echo",
                        "data": message
                    }), websocket)
                    
                except json.JSONDecodeError:
                    logger.warning(f"Received invalid JSON: {data}")
                    await manager.send_personal_message(json.dumps({
                        "type": "error",
                        "message": "Invalid JSON format"
                    }), websocket)
        except WebSocketDisconnect:
            manager.disconnect(websocket)
        except Exception as e:
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
