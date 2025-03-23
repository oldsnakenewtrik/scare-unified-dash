from fastapi import FastAPI, Depends, HTTPException, Query, Path, status, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import sys
import json
import time
import uuid
import datetime
import logging
import traceback
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel
import asyncio
import aiohttp
from sqlalchemy import inspect

# Import the database initialization module
from .db_init import init_database, connect_with_retry
# Import the database monitoring module
from .db_monitor import initialize_monitor, get_db_status, force_db_reconnect

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Set up the FastAPI application
app = FastAPI(title="SCARE Unified Metrics API")

# Define allowed origins - allow specific domains and Railway frontend
origins = [
    "https://front-production-f6e6.up.railway.app",  # Railway frontend
    "http://localhost:3000",  # Local development frontend
    "http://localhost:5000",  # Local development with dev server
    "http://localhost:5001"   # Local development with alt port
]

# Add CORS middleware directly to the main app
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,  # Allow cookies and credentials
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=86400,  # Cache preflight for 24 hours
)

# Add middleware to log all requests and add CORS headers
@app.middleware("http")
async def add_cors_headers(request, call_next):
    origin = request.headers.get("origin", "")
    
    # For OPTIONS requests, return a response immediately with CORS headers
    if request.method == "OPTIONS":
        response = JSONResponse(content={"detail": "CORS preflight handled"})
        if origin and origin in origins:
            response.headers["access-control-allow-origin"] = origin
            response.headers["access-control-allow-credentials"] = "true"
        else:
            # For non-matching origins, return 403 to prevent cross-site access
            response = JSONResponse(content={"detail": "Origin not allowed"}, status_code=403)
            
        response.headers["access-control-allow-methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        response.headers["access-control-allow-headers"] = "*"
        response.headers["access-control-expose-headers"] = "*"
        response.headers["access-control-max-age"] = "86400"  # Cache preflight for 24 hours
        return response
    
    # Default response in case there's an error
    try:
        response = await call_next(request)
        
        # Add CORS headers if they're not already present
        if "access-control-allow-origin" not in response.headers:
            print(f"CORS headers not found for path: {request.url.path}. Adding them now.")
            
            # If the request has a specific origin header that's in our allowed list,
            # use that exact origin in the response
            if origin and origin in origins:
                response.headers["access-control-allow-origin"] = origin
                response.headers["access-control-allow-credentials"] = "true"
            # Don't set CORS headers for non-allowed origins
                
            response.headers["access-control-allow-methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
            response.headers["access-control-allow-headers"] = "*"
            response.headers["access-control-expose-headers"] = "*"
            response.headers["access-control-max-age"] = "86400"  # Cache preflight for 24 hours
        
        return response
    except Exception as e:
        print(f"Error in CORS middleware: {str(e)}")
        # Create a new response if there was an error
        resp = JSONResponse(content={"detail": "Internal server error"}, status_code=500)
        
        # Apply CORS headers to error response
        if origin and origin in origins:
            resp.headers["access-control-allow-origin"] = origin
            resp.headers["access-control-allow-credentials"] = "true"
        # Don't set CORS headers for non-allowed origins
            
        resp.headers["access-control-allow-methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        resp.headers["access-control-allow-headers"] = "*"
        resp.headers["access-control-expose-headers"] = "*"
        resp.headers["access-control-max-age"] = "86400"  # Cache preflight for 24 hours
        
        return resp

print("CORS middleware configured successfully")

# Add WebSocket support
try:
    from src.api.websocket import add_websocket_endpoints
    app = add_websocket_endpoints(app)
    print("WebSocket support added successfully")
except ImportError as e:
    print(f"Failed to add WebSocket support: {e}")
    # Try to add WebSocket support using a simplified approach
    try:
        from fastapi import WebSocket, WebSocketDisconnect
        import json
        from datetime import datetime
        
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
                
        print("Simplified WebSocket support added successfully")
    except Exception as e:
        print(f"Failed to add simplified WebSocket support: {e}")

# Mount static files for the frontend
try:
    # Get the directory of the current file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Navigate to the frontend build directory
    frontend_dir = os.path.join(os.path.dirname(os.path.dirname(current_dir)), "src", "frontend", "build")
    
    # Check if the directory exists
    if os.path.exists(frontend_dir):
        logger.info(f"Mounting frontend static files from: {frontend_dir}")
        app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
    else:
        # Try alternative path in case we're in a Docker container
        docker_frontend_dir = "/app/src/frontend/build"
        if os.path.exists(docker_frontend_dir):
            logger.info(f"Mounting frontend static files from Docker path: {docker_frontend_dir}")
            app.mount("/", StaticFiles(directory=docker_frontend_dir, html=True), name="frontend")
        else:
            logger.warning(f"Frontend build directory not found at {frontend_dir} or {docker_frontend_dir}")
except Exception as e:
    logger.error(f"Failed to mount frontend static files: {str(e)}")
    logger.error(traceback.format_exc())

# Add a root endpoint to serve the frontend index.html
@app.get("/", include_in_schema=False)
async def serve_frontend():
    """
    Serve the frontend index.html file.
    This is a fallback in case the static file mounting doesn't work.
    """
    try:
        # Try the Docker path first since we're in Railway
        docker_index_path = "/app/src/frontend/build/index.html"
        if os.path.exists(docker_index_path):
            logger.info(f"Serving index.html from Docker path: {docker_index_path}")
            return FileResponse(docker_index_path)
        
        # Try the local path as fallback
        current_dir = os.path.dirname(os.path.abspath(__file__))
        local_index_path = os.path.join(os.path.dirname(os.path.dirname(current_dir)), 
                                       "src", "frontend", "build", "index.html")
        if os.path.exists(local_index_path):
            logger.info(f"Serving index.html from local path: {local_index_path}")
            return FileResponse(local_index_path)
        
        # If neither path exists, return a simple message
        logger.warning("Frontend index.html not found, returning simple response")
        return JSONResponse(
            status_code=200,
            content={
                "message": "API server is running, but frontend files are not available",
                "api_docs": "/docs",
                "health_check": "/api/health"
            }
        )
    except Exception as e:
        logger.error(f"Error serving frontend: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to serve frontend: {str(e)}"}
        )

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://scare_user:scare_password@postgres:5432/scare_metrics")

# Global variable to track if DB monitor was initialized
db_monitor_initialized = False

try:
    # Use the new retry mechanism for establishing the database connection
    logger.info("Attempting to connect to database with retry mechanism")
    engine = connect_with_retry(max_retries=5, delay=5)
    
    # Initialize the database monitor
    try:
        db_monitor = initialize_monitor(
            database_url=DATABASE_URL,
            check_interval=60,  # Check every minute in production
            pool_recycle=300    # Recycle connections every 5 minutes
        )
        db_monitor_initialized = True
        logger.info("Database monitoring initialized and started")
    except Exception as e:
        logger.error(f"Failed to initialize database monitor: {str(e)}")
        logger.warning("Application will continue without database monitoring")
    
    # Startup event to initialize database without blocking app startup
    @app.on_event("startup")
    async def startup_event():
        """Initialize database on startup without blocking the app from starting"""
        try:
            # Run database initialization in a separate thread to avoid blocking
            import threading
            db_thread = threading.Thread(target=init_database)
            db_thread.daemon = True  # Make thread a daemon so it doesn't block app shutdown
            db_thread.start()
            logger.info("Database initialization started in background thread")
        except Exception as e:
            logger.error(f"Error starting database initialization thread: {str(e)}")
            # Continue app startup even if database initialization fails

    # Add a global on_startup handler to verify DB connection when app starts
    @app.on_event("startup")
    def startup_db_client():
        logger.info("FastAPI startup: Checking database connection")
        try:
            # Log the status
            status = get_db_status()
            if status["is_connected"]:
                logger.info(f"Database connection successful at startup")
            else:
                logger.warning(f"Database not connected at startup: {status.get('last_error', 'Unknown error')}")
                # Try to force a reconnect
                reconnect_result = force_db_reconnect()
                logger.info(f"Forced reconnection result: {reconnect_result}")
        except Exception as e:
            logger.error(f"Error during startup database check: {str(e)}")
    
    # Add a global on_shutdown handler to shutdown the DB connection when app stops
    @app.on_event("shutdown")
    def shutdown_db_client():
        logger.info("FastAPI shutdown: Closing database connections")
        try:
            if engine:
                engine.dispose()
            logger.info("Database connections closed")
        except Exception as e:
            logger.error(f"Error closing database connections: {str(e)}")
    
    # Set up the session factory
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Initialize database at startup
    try:
        init_database(engine)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
except Exception as e:
    logger.critical(f"Failed to connect to database: {str(e)}")
    # Note: We don't want to crash the server here, so we'll continue
    # The database connection will be retried in the connect_with_retry function

# Dependency
def get_db():
    if SessionLocal is None:
        # We hit this case when database connection could not be established initially
        # Generate a unique error ID for tracking
        error_id = str(uuid.uuid4())
        logger.error(f"Database connection unavailable. Error ID: {error_id}")
        # Try to reconnect to the database
        try:
            logger.info("Attempting to reconnect to database...")
            force_db_reconnect()
            # If successful, this should update the global SessionLocal
        except Exception as reconnect_error:
            logger.error(f"Failed to reconnect: {str(reconnect_error)}")
        
        # Still raise an exception to inform the client
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database unavailable. Error ID: {error_id}"
        )
    
    db = None
    try:
        db = SessionLocal()
        yield db
    except OperationalError as e:
        # Handle database connection errors
        logger.error(f"Database session error: {str(e)}")
        error_id = str(uuid.uuid4())
        logger.error(f"Error ID: {error_id}")
        
        # Try to reconnect
        try:
            logger.info("Attempting to reconnect to database...")
            force_db_reconnect()
        except Exception as reconnect_error:
            logger.error(f"Failed to reconnect: {str(reconnect_error)}")
        
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection error. Error ID: {error_id}"
        )
    except Exception as e:
        # Handle other database errors
        logger.error(f"Database session exception: {str(e)}")
        raise
    finally:
        if db:
            db.close()

# Add error handling middleware
@app.middleware("http")
async def db_error_handler(request, call_next):
    """Middleware to handle database errors globally"""
    try:
        # Check for certain endpoints that should skip this middleware
        skip_db_error_check = any([
            request.url.path.endswith("/api/db-test"),
            request.url.path.endswith("/api/db-status"),
            request.url.path.endswith("/api/db-reconnect"),
            request.url.path.endswith("/health"),
            request.url.path.endswith("/api/health"),
            request.url.path.endswith("/api/cors-test")  
        ])
        
        if skip_db_error_check:
            # Skip DB checking for diagnostics endpoints
            return await call_next(request)
        
        # Check if database monitor is initialized
        if not db_monitor_initialized:
            # If monitor isn't initialized, allow the request to proceed
            # but log a warning for non-diagnostic endpoints
            logger.warning(f"Database monitor not initialized for request to {request.url.path}")
            return await call_next(request)
            
        # Check if database is connected
        db_status = get_db_status()
        if not db_status.get("is_connected", False):
            # Database is not connected, try to reconnect
            logger.warning(f"Database connection lost before request to {request.url.path}. Attempting reconnect.")
            reconnect_success = force_db_reconnect()
            
            if not reconnect_success:
                # If reconnection failed, return a service unavailable response
                error_id = str(uuid.uuid4())
                logger.error(f"Database reconnection failed for request to {request.url.path}. Error ID: {error_id}")
                
                return JSONResponse(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    content={
                        "status": "error",
                        "message": "Database connection is unavailable. Please try again later.",
                        "error_id": error_id,
                        "error_code": "DATABASE_UNAVAILABLE"
                    }
                )
        
        # Continue with the request if database is connected
        return await call_next(request)
    except Exception as e:
        # Log the error
        error_id = str(uuid.uuid4())
        logger.error(f"Error in database middleware: {str(e)}. Error ID: {error_id}")
        
        # Return a generic error response
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "message": "Internal server error occurred while processing the request.",
                "error_id": error_id,
                "error_code": "INTERNAL_SERVER_ERROR"
            }
        )

# Pydantic models for API response
class MetricsSummary(BaseModel):
    date: datetime.date
    total_clicks: int
    total_impressions: int
    total_cost: float
    total_conversions: float
    total_revenue: float
    website_visitors: int
    salesforce_leads: int
    opportunities: int
    closed_won: int

class DateRangeParams(BaseModel):
    start_date: datetime.date
    end_date: datetime.date
    campaign_name: Optional[str] = None
    source_system: Optional[str] = None

class CampaignMetrics(BaseModel):
    campaign_id: int
    campaign_name: str
    source_system: str
    is_active: bool
    date: datetime.date
    impressions: int
    clicks: int
    spend: float
    revenue: float
    conversions: float
    cpc: float
    smooth_leads: int
    total_sales: int
    users: int

class CampaignMappingCreate(BaseModel):
    source_system: str
    external_campaign_id: str
    original_campaign_name: str
    pretty_campaign_name: str
    campaign_category: Optional[str] = None
    campaign_type: Optional[str] = None
    network: Optional[str] = None
    pretty_network: Optional[str] = None
    pretty_source: Optional[str] = None
    display_order: Optional[int] = None

class CampaignMapping(CampaignMappingCreate):
    id: int
    is_active: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime

class CampaignSource(BaseModel):
    source_system: str
    external_campaign_id: str
    original_campaign_name: str
    network: Optional[str] = None

class CampaignOrderUpdate(BaseModel):
    id: int
    display_order: int

class MetricsSummaryHierarchical(BaseModel):
    impressions: Optional[int] = None
    clicks: Optional[int] = None
    conversions: Optional[float] = None
    cost: Optional[float] = None

class CampaignHierarchical(BaseModel):
    id: int
    source_system: str
    external_campaign_id: str
    original_campaign_name: str
    pretty_campaign_name: str
    campaign_category: Optional[str] = None
    campaign_type: Optional[str] = None
    network: Optional[str] = None
    display_order: int
    impressions: Optional[int] = None
    clicks: Optional[int] = None
    conversions: Optional[float] = None
    cost: Optional[float] = None

class UnmappedCampaign(BaseModel):
    source_system: str
    external_campaign_id: str
    campaign_name: str
    network: Optional[str] = None

# Health check endpoint for verifying server status
@app.get("/health")
def health_check(db=Depends(get_db)):
    """
    Health check endpoint that verifies the status of:
    - Database connection
    - Required tables
    - Campaign mappings
    - Data in fact tables
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.datetime.now().isoformat(),
        "components": {}
    }
    
    # Check database connection
    try:
        db.execute(text("SELECT 1")).fetchone()
        health_status["components"]["database"] = {
            "status": "healthy",
            "message": "Database connection successful"
        }
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["components"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        return health_status
    
    # Check required tables
    required_tables = [
        "sm_campaign_name_mapping",
        "sm_fact_google_ads",
        "sm_fact_bing_ads",
        "sm_fact_matomo",
        "sm_fact_redtrack"
    ]
    
    try:
        # Query to check which tables exist
        table_query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('sm_campaign_name_mapping', 'sm_fact_google_ads', 'sm_fact_bing_ads', 'sm_fact_matomo', 'sm_fact_redtrack')
        """
        existing_tables = [row[0] for row in db.execute(text(table_query)).fetchall()]
        
        missing_tables = [table for table in required_tables if table not in existing_tables]
        
        if missing_tables:
            health_status["status"] = "degraded"
            health_status["components"]["tables"] = {
                "status": "degraded",
                "error": f"Missing tables: {', '.join(missing_tables)}",
                "existing_tables": existing_tables,
                "missing_tables": missing_tables
            }
        else:
            health_status["components"]["tables"] = {
                "status": "healthy",
                "message": "All required tables exist",
                "tables": existing_tables
            }
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["components"]["tables"] = {
            "status": "unhealthy",
            "error": f"Error checking tables: {str(e)}"
        }
    
    # Check data in fact tables
    fact_tables = [
        "sm_fact_google_ads",
        "sm_fact_bing_ads",
        "sm_fact_matomo",
        "sm_fact_redtrack"
    ]
    
    try:
        fact_table_counts = {}
        empty_tables = []
        
        for table in fact_tables:
            if table in existing_tables:
                count_query = f"SELECT COUNT(*) FROM public.{table}"
                count = db.execute(text(count_query)).scalar() or 0
                fact_table_counts[table] = count
                
                if count == 0:
                    empty_tables.append(table)
        
        if empty_tables:
            health_status["components"]["fact_data"] = {
                "status": "degraded",
                "error": f"Empty fact tables: {', '.join(empty_tables)}",
                "counts": fact_table_counts
            }
            
            if health_status["status"] == "healthy":
                health_status["status"] = "degraded"
        else:
            health_status["components"]["fact_data"] = {
                "status": "healthy",
                "message": "All fact tables have data",
                "counts": fact_table_counts
            }
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["components"]["fact_data"] = {
            "status": "unhealthy",
            "error": f"Error checking fact data: {str(e)}"
        }
    
    # Check campaign mappings
    try:
        if "sm_campaign_name_mapping" in existing_tables:
            # Get count of mappings
            mapping_count = db.execute(text("SELECT COUNT(*) FROM public.sm_campaign_name_mapping")).scalar() or 0
            
            # Get count of unmapped campaigns
            unmapped_query = """
                WITH all_campaigns AS (
                    SELECT DISTINCT 'Google Ads' as source, CAST(campaign_id AS VARCHAR) as id FROM public.sm_fact_google_ads WHERE campaign_id IS NOT NULL
                    UNION ALL
                    SELECT DISTINCT 'Bing Ads' as source, CAST(campaign_id AS VARCHAR) as id FROM public.sm_fact_bing_ads WHERE campaign_id IS NOT NULL
                    UNION ALL
                    SELECT DISTINCT 'Matomo' as source, CAST(campaign_id AS VARCHAR) as id FROM public.sm_fact_matomo WHERE campaign_id IS NOT NULL
                    UNION ALL
                    SELECT DISTINCT 'RedTrack' as source, CAST(campaign_id AS VARCHAR) as id FROM public.sm_fact_redtrack WHERE campaign_id IS NOT NULL
                )
                SELECT COUNT(*) FROM all_campaigns ac
                LEFT JOIN public.sm_campaign_name_mapping m ON ac.source = m.source_system AND ac.id = m.external_campaign_id
                WHERE m.id IS NULL
            """
            
            try:
                unmapped_count = db.execute(text(unmapped_query)).scalar() or 0
                
                # Get counts by source
                source_counts = {}
                for source in ["Google Ads", "Bing Ads", "Matomo", "RedTrack"]:
                    source_query = f"""
                        SELECT COUNT(*) FROM public.sm_campaign_name_mapping 
                        WHERE source_system = '{source}'
                    """
                    source_count = db.execute(text(source_query)).scalar() or 0
                    source_counts[source] = source_count
                
                if mapping_count == 0:
                    health_status["components"]["campaign_mappings"] = {
                        "status": "degraded",
                        "error": "No campaign mappings found",
                        "unmapped_count": unmapped_count,
                        "by_source": source_counts
                    }
                    
                    if health_status["status"] == "healthy":
                        health_status["status"] = "degraded"
                elif unmapped_count > 0:
                    health_status["components"]["campaign_mappings"] = {
                        "status": "degraded",
                        "message": f"Found {unmapped_count} unmapped campaigns",
                        "mapping_count": mapping_count,
                        "unmapped_count": unmapped_count,
                        "by_source": source_counts
                    }
                    
                    if health_status["status"] == "healthy":
                        health_status["status"] = "degraded"
                else:
                    health_status["components"]["campaign_mappings"] = {
                        "status": "healthy",
                        "message": "All campaigns are mapped",
                        "mapping_count": mapping_count,
                        "by_source": source_counts
                    }
            except Exception as e:
                health_status["components"]["campaign_mappings"] = {
                    "status": "degraded",
                    "error": f"Error checking unmapped campaigns: {str(e)}",
                    "mapping_count": mapping_count
                }
                
                if health_status["status"] == "healthy":
                    health_status["status"] = "degraded"
        else:
            health_status["components"]["campaign_mappings"] = {
                "status": "degraded",
                "error": "Campaign mapping table does not exist"
            }
            
            if health_status["status"] == "healthy":
                health_status["status"] = "degraded"
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["components"]["campaign_mappings"] = {
            "status": "unhealthy",
            "error": f"Error checking campaign mappings: {str(e)}"
        }
    
    return health_status

# Simple health check endpoint that doesn't depend on database
@app.get("/api/health")
async def simple_health_check():
    """
    A simple health check endpoint that doesn't depend on the database.
    This is used by Railway for health checks to ensure the service is running.
    """
    try:
        # Return basic health information
        return {
            "status": "ok",
            "message": "API server is running",
            "timestamp": datetime.datetime.now().isoformat(),
            "database_status": "checking in background"
        }
    except Exception as e:
        # Even if there's an error, still return 200 for health check
        logger.error(f"Error in health check: {str(e)}")
        return {
            "status": "ok",
            "message": "API server is running but encountered an error",
            "error": str(e),
            "timestamp": datetime.datetime.now().isoformat()
        }

# Health check endpoint to test CORS headers
@app.get("/api/cors-test", tags=["Diagnostics"])
async def test_cors(request: Request):
    """
    Test endpoint to verify CORS configuration
    Returns details about the CORS configuration to help with debugging
    """
    try:
        # Get the origin from the request
        origin = request.headers.get("origin", "No origin provided")
        is_allowed = origin in origins
        
        # Return detailed information about the request and CORS configuration
        response = JSONResponse(
            content={
                "message": "CORS test endpoint",
                "timestamp": datetime.datetime.now().isoformat(),
                "request_origin": origin,
                "is_origin_allowed": is_allowed,
                "allowed_origins": origins,
                "cors_middleware": {
                    "allow_credentials": True,
                    "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
                    "max_age": 86400
                },
                "status": "success" if is_allowed else "rejected"
            }
        )
        
        # Set CORS headers manually for this test endpoint
        if is_allowed:
            response.headers["access-control-allow-origin"] = origin
            response.headers["access-control-allow-credentials"] = "true"
        
        response.headers["access-control-allow-methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        response.headers["access-control-allow-headers"] = "*"
        response.headers["access-control-expose-headers"] = "*"
        response.headers["access-control-max-age"] = "86400"  # Cache preflight for 24 hours
        
        return response
    except Exception as e:
        # Even if there's an error, still return 200 for health check
        logger.error(f"Error in CORS test endpoint: {str(e)}")
        return JSONResponse(
            status_code=200,
            content={
                "message": "CORS test endpoint (error handled)",
                "timestamp": datetime.datetime.now().isoformat(),
                "error": str(e),
                "status": "error_handled"
            }
        )

# API endpoints
@app.get("/api/metrics/summary", response_model=List[MetricsSummary])
def get_metrics_summary(start_date: datetime.date, end_date: datetime.date, db=Depends(get_db)):
    """
    Get unified metrics summary for a given date range
    """
    try:
        query = text("""
            SELECT 
                full_date as date,
                SUM(total_clicks) as total_clicks,
                SUM(total_impressions) as total_impressions,
                SUM(total_cost) as total_cost,
                SUM(total_conversions) as total_conversions,
                SUM(total_revenue) as total_revenue,
                SUM(website_visitors) as website_visitors,
                SUM(salesforce_leads) as salesforce_leads,
                SUM(salesforce_opportunities) as opportunities,
                SUM(salesforce_closed_won) as closed_won
            FROM view_unified_metrics
            WHERE full_date BETWEEN :start_date AND :end_date
            GROUP BY full_date
            ORDER BY full_date
        """)
        
        result = db.execute(query, {"start_date": start_date, "end_date": end_date})
        metrics = [dict(row._mapping) for row in result]
        
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/api/metrics/by-source")
def get_metrics_by_source(start_date: datetime.date, end_date: datetime.date, db=Depends(get_db)):
    """
    Get metrics broken down by source system
    """
    try:
        query = text("""
            SELECT 
                source_system,
                SUM(total_clicks) as total_clicks,
                SUM(total_impressions) as total_impressions,
                SUM(total_cost) as total_cost,
                SUM(total_conversions) as total_conversions,
                SUM(total_revenue) as total_revenue
            FROM view_unified_metrics
            WHERE full_date BETWEEN :start_date AND :end_date
            GROUP BY source_system
            ORDER BY source_system
        """)
        
        result = db.execute(query, {"start_date": start_date, "end_date": end_date})
        metrics = [dict(row._mapping) for row in result]
        
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/api/metrics/by-campaign")
def get_metrics_by_campaign(start_date: datetime.date, end_date: datetime.date, db=Depends(get_db)):
    """
    Get metrics broken down by campaign
    """
    try:
        query = text("""
            SELECT 
                campaign_name,
                source_system,
                SUM(total_clicks) as total_clicks,
                SUM(total_impressions) as total_impressions,
                SUM(total_cost) as total_cost,
                SUM(total_conversions) as total_conversions,
                SUM(total_revenue) as total_revenue
            FROM view_unified_metrics
            WHERE full_date BETWEEN :start_date AND :end_date
            GROUP BY campaign_name, source_system
            ORDER BY campaign_name, source_system
        """)
        
        result = db.execute(query, {"start_date": start_date, "end_date": end_date})
        metrics = [dict(row._mapping) for row in result]
        
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# Create a function to handle database errors consistently
def handle_db_error(error: Exception, operation: str):
    """Handle database errors consistently across endpoints"""
    error_id = str(uuid.uuid4())
    error_msg = str(error)
    logger.error(f"Database error during {operation} [ID: {error_id}]: {error_msg}")
    logger.error(traceback.format_exc())
    
    if "Network is unreachable" in error_msg or "Could not connect to server" in error_msg:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "detail": "Database connection failed. This may be due to network connectivity issues.",
                "error_id": error_id,
                "error_type": "database_unreachable"
            }
        )
    elif "does not exist" in error_msg and ("relation" in error_msg or "table" in error_msg):
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "detail": "Required database tables do not exist. Database initialization may not have completed.",
                "error_id": error_id,
                "error_type": "missing_tables"
            }
        )
    else:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "An unexpected database error occurred. Please try again later.",
                "error_id": error_id,
                "error_type": "database_error"
            }
        )

# Add a new database test endpoint
@app.get("/api/db-test", tags=["Diagnostics"])
def test_db_connection():
    """Test the database connection and return diagnostic information"""
    try:
        start_time = time.time()
        
        # Check if database monitor is initialized
        if not db_monitor_initialized:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "status": "error",
                    "message": "Database monitor is not initialized",
                    "monitor_initialized": False,
                    "test_time": time.time() - start_time,
                    "timestamp": datetime.datetime.now().isoformat()
                }
            )
            
        # Get monitoring status
        monitor_status = get_db_status()
        
        # If not connected, try to reconnect
        if not monitor_status["is_connected"]:
            logger.warning("Db test: Monitor reports database not connected, attempting reconnect")
            force_db_reconnect()
            monitor_status = get_db_status()  # Get updated status
        
        # Test direct connection
        with engine.connect() as conn:
            # Run a basic query to test the connection
            result = conn.execute(text("SELECT 1"))
            basic_query_result = result.scalar()
            
            # Get table information
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            
            # Test more complex query if tables exist
            campaign_count = 0
            google_ads_data = False
            if "sm_campaign_name_mapping" in tables:
                result = conn.execute(text("SELECT COUNT(*) FROM sm_campaign_name_mapping"))
                campaign_count = result.scalar()
            
            if "sm_fact_google_ads" in tables:
                result = conn.execute(text("SELECT COUNT(*) > 0 FROM sm_fact_google_ads LIMIT 1"))
                google_ads_data = result.scalar()
            
        elapsed_time = time.time() - start_time
        
        return {
            "status": "success",
            "message": "Database connection successful",
            "monitor_status": monitor_status,
            "test_query_result": basic_query_result,
            "database_host": DATABASE_URL.split("@")[1].split("/")[0] if "@" in DATABASE_URL else "unknown",
            "tables_found": len(tables),
            "table_names": tables[:10],  # List first 10 tables only
            "campaign_mappings_count": campaign_count,
            "has_google_ads_data": google_ads_data,
            "query_time_ms": round(elapsed_time * 1000, 2),
            "railway_private_networking": "railway.internal" in DATABASE_URL
        }
    except Exception as e:
        error_msg = str(e)
        error_id = str(uuid.uuid4())
        logger.error(f"Database test failed: {error_msg}. Error ID: {error_id}")
        logger.error(traceback.format_exc())
        
        # Try to get monitor status even if connection failed
        try:
            monitor_status = get_db_status()
        except Exception as monitor_error:
            monitor_status = {"status": "error", "error": str(monitor_error)}
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "message": f"Database connection failed: {error_msg}",
                "error_id": error_id,
                "monitor_status": monitor_status,
                "database_url": DATABASE_URL.split("@")[1] if "@" in DATABASE_URL else "unknown",
                "error_details": traceback.format_exc(),
                "railway_private_networking": "railway.internal" in DATABASE_URL
            }
        )

# Add a database status endpoint
@app.get("/api/db-status", tags=["Diagnostics"])
def get_database_status():
    """Get the current database connection status"""
    try:
        # Check if database monitor is initialized
        if not db_monitor_initialized:
            return {
                "status": "not_initialized",
                "message": "Database monitor has not been initialized",
                "is_connected": False,
                "database_url": DATABASE_URL.split("@")[1].split("/")[0] if "@" in DATABASE_URL else "unknown",
                "railway_private_networking": "railway.internal" in DATABASE_URL,
                "request_time": datetime.datetime.now().isoformat()
            }
            
        # Get the status from the database monitor
        status = get_db_status()
        
        # Enhance the status with additional information
        enhanced_status = {
            **status,
            "database_url": DATABASE_URL.split("@")[1].split("/")[0] if "@" in DATABASE_URL else "unknown",
            "railway_private_networking": "railway.internal" in DATABASE_URL,
            "request_time": datetime.datetime.now().isoformat()
        }
        
        return enhanced_status
    except Exception as e:
        error_msg = str(e)
        error_id = str(uuid.uuid4())
        logger.error(f"Error getting database status: {error_msg}. Error ID: {error_id}")
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "message": f"Failed to get database status: {error_msg}",
                "error_id": error_id
            }
        )

# Add a database reconnect endpoint
@app.post("/api/db-reconnect", tags=["Diagnostics"])
def reconnect_database():
    """Force a database reconnection"""
    try:
        # Check if database monitor is initialized
        if not db_monitor_initialized:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status": "error",
                    "message": "Database monitor is not initialized, cannot reconnect",
                    "success": False
                }
            )
        
        # Log the reconnection attempt
        logger.info("Manual database reconnection requested")
        
        # Force a reconnection
        result = force_db_reconnect()
        
        # Get the updated status
        status = get_db_status()
        
        return {
            "status": "success" if result else "failed",
            "message": "Database reconnection successful" if result else "Database reconnection failed",
            "db_status": status,
            "request_time": datetime.datetime.now().isoformat()
        }
    except Exception as e:
        error_msg = str(e)
        error_id = str(uuid.uuid4())
        logger.error(f"Error reconnecting to database: {error_msg}. Error ID: {error_id}")
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "message": f"Failed to reconnect to database: {error_msg}",
                "error_id": error_id
            }
        )

# ... rest of your code remains the same ...
