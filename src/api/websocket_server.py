"""
Simplified WebSocket server for testing WebSocket functionality
"""
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import json
from datetime import datetime
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("websocket")

# Create a FastAPI app
app = FastAPI(title="SCARE WebSocket Test Server")

# Configure CORS to allow any origin
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Create a connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections = []
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
        if websocket in self.active_connections:
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
        
        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)

# Create a connection manager instance
manager = ConnectionManager()

# Define WebSocket endpoint
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
        # Handle client disconnect
        manager.disconnect(websocket)
    except Exception as e:
        # Handle other errors
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

# Define a simple health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "WebSocket server is running"}

# Define a simple CORS test endpoint
@app.get("/api/cors-test")
async def test_cors():
    """
    Test endpoint to verify CORS configuration
    """
    return {
        "message": "CORS is working correctly!",
        "timestamp": datetime.now().isoformat(),
        "status": "success"
    }

# Run the server
if __name__ == "__main__":
    print("Starting WebSocket server on port 5001...")
    uvicorn.run(app, host="0.0.0.0", port=5001)
