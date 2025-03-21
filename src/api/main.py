from fastapi import FastAPI, Depends, HTTPException, Query, Path, status, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, text
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

# Set up logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Function to run database migrations
def run_migrations(engine):
    """Run database migrations during application startup"""
    try:
        logger.info("Checking for database migrations to apply")
        
        # Create migrations table if it doesn't exist
        with engine.connect() as conn:
            conn.execute(text("""
            CREATE TABLE IF NOT EXISTS public.migrations (
                id SERIAL PRIMARY KEY,
                migration_name VARCHAR(255) NOT NULL UNIQUE,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """))
            
            # Get list of applied migrations
            result = conn.execute(text("SELECT migration_name FROM public.migrations"))
            applied_migrations = [row[0] for row in result]
            
            # Get list of migration files
            migrations_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "migrations")
            if os.path.exists(migrations_dir):
                migration_files = sorted([f for f in os.listdir(migrations_dir) if f.endswith('.sql')])
                
                # Apply migrations that haven't been applied yet
                for migration_file in migration_files:
                    if migration_file not in applied_migrations:
                        logger.info(f"Applying migration: {migration_file}")
                        
                        # Read the migration file
                        with open(os.path.join(migrations_dir, migration_file), 'r') as f:
                            migration_sql = f.read()
                        
                        # Execute the migration in a transaction
                        with conn.begin():
                            conn.execute(text(migration_sql))
                            
                            # Record the migration as applied
                            conn.execute(
                                text("INSERT INTO public.migrations (migration_name) VALUES (:name)"),
                                {"name": migration_file}
                            )
                        
                        logger.info(f"Successfully applied migration: {migration_file}")
            else:
                logger.warning(f"Migrations directory not found: {migrations_dir}")
    except Exception as e:
        logger.error(f"Error applying migrations: {str(e)}")
        # Don't raise the exception - we want the app to start even if migrations fail
        # This allows manual intervention if needed

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://scare_user:scare_password@postgres:5432/scare_metrics")
try:
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()
    print(f"Database connection established: {DATABASE_URL}")
except Exception as e:
    print(f"Warning: Failed to connect to database: {str(e)}")
    print("Application will continue to start, but database features will not work")
    engine = None
    SessionLocal = None
    Base = declarative_base()

# Run migrations during startup
if engine is not None:
    run_migrations(engine)

# Run database initialization (creates tables and runs migrations)
if engine is not None:
    try:
        # Use the correct import path for db_init
        from src.api.db_init import init_database
        init_database()
    except ImportError:
        try:
            # Fallback to local import if the package structure isn't recognized
            from db_init import init_database
            init_database()
        except Exception as e:
            print(f"Warning: Failed to initialize database: {str(e)}")
            print("Application will continue to start, but some features may not work correctly")
    except Exception as e:
        print(f"Warning: Failed to initialize database: {str(e)}")
        print("Application will continue to start, but some features may not work correctly")
else:
    print("Skipping database initialization as database connection failed")

app = FastAPI(title="SCARE Unified Metrics API")

print("=====================================================")
print("INITIALIZING FASTAPI APP")
print("=====================================================")

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

# Dependency
def get_db():
    if SessionLocal is None:
        raise HTTPException(status_code=503, detail="Database connection not available")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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

# Health check endpoint to test CORS headers
@app.get("/api/cors-test", tags=["Diagnostics"])
async def test_cors(request: Request):
    """
    Test endpoint to verify CORS configuration
    Returns details about the CORS configuration to help with debugging
    """
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

@app.get("/api/test-cors")
async def test_cors():
    """
    Test endpoint to verify CORS configuration
    Returns details about the CORS configuration to help with debugging
    """
    return {
        "message": "CORS is working correctly!",
        "timestamp": datetime.datetime.now().isoformat(),
        "status": "success"
    }

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

@app.options("/api/campaigns/metrics")
def campaigns_metrics_options():
    """Handle OPTIONS preflight request for the campaigns/metrics endpoint"""
    return {"detail": "CORS preflight request handled"}

@app.get("/api/campaigns/metrics", response_model=List[Dict])
def get_campaigns_metrics(db=Depends(get_db)):
    """
    Get all campaign metrics for the master tab view.
    Respects the campaign mapping infrastructure to unify metrics across data sources.
    """
    try:
        # First get all active mappings to ensure we include all configured campaigns
        mapping_query = text("""
            SELECT 
                id,
                source_system,
                external_campaign_id,
                pretty_campaign_name,
                pretty_network,
                pretty_source,
                campaign_category,
                campaign_type,
                network,
                is_active
            FROM public.sm_campaign_name_mapping
            WHERE is_active = TRUE
            ORDER BY display_order, pretty_campaign_name
        """)
        
        print("Fetching campaign mappings...")
        mappings = {
            # Use tuple of (source_system, external_campaign_id) as key
            (row.source_system, row.external_campaign_id): dict(row._mapping)
            for row in db.execute(mapping_query)
        }
        
        print(f"Found {len(mappings)} active campaign mappings")
        
        # Now query Google Ads metrics (currently the only source with data)
        metrics_query = text("""
            SELECT 
                campaign_id,
                campaign_name,
                date,
                impressions,
                clicks,
                cost,
                conversions
            FROM public.sm_fact_google_ads
            ORDER BY date DESC
        """)
        
        print("Fetching Google Ads metrics...")
        google_metrics = {}
        for row in db.execute(metrics_query):
            campaign_id = row.campaign_id
            if campaign_id not in google_metrics:
                google_metrics[campaign_id] = dict(row._mapping)
        
        print(f"Found metrics for {len(google_metrics)} Google Ads campaigns")
        
        # Combine mapping data with metrics
        results = []
        for (source, campaign_id), mapping in mappings.items():
            metrics = None
            
            if source == 'Google Ads' and campaign_id in google_metrics:
                metrics = google_metrics[campaign_id]
            
            if metrics:
                # Build a combined result with both mapping and metrics data
                result = {
                    'mapping_id': mapping['id'],
                    'campaign_id': campaign_id,
                    'campaign_name': mapping['pretty_campaign_name'],
                    'source_system': source,
                    'pretty_source': mapping['pretty_source'],
                    'pretty_network': mapping['pretty_network'],
                    'is_active': mapping['is_active'],
                    'date': metrics.get('date'),
                    'impressions': metrics.get('impressions', 0),
                    'clicks': metrics.get('clicks', 0),
                    'spend': metrics.get('cost', 0.0),  # Rename cost to spend for model compatibility
                    'conversions': metrics.get('conversions', 0),
                    'revenue': 0.0,  # Not available for Google Ads
                    'cpc': metrics.get('clicks', 0) and (metrics.get('cost', 0) / metrics.get('clicks', 0)) or 0,
                    'smooth_leads': 0,  # Not available yet
                    'total_sales': 0,   # Not available yet
                    'users': 0,         # Not available yet
                }
                results.append(result)
        
        print(f"Returning {len(results)} combined campaign metrics results")
        
        if not results:
            print("No campaigns found with metrics, returning empty list")
            return []
        
        return results
    except Exception as e:
        print(f"Error in campaign metrics: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/api/campaign-metrics")
def get_campaign_metrics(
    start_date: datetime.date = Query(..., description="Start date for metrics"),
    end_date: datetime.date = Query(..., description="End date for metrics"),
    platform: Optional[str] = Query(None, description="Filter by platform (e.g., google_ads, bing_ads)"),
    network: Optional[str] = Query(None, description="Filter by network (e.g., Search, Display)"),
    db=Depends(get_db)
):
    """
    Get campaign metrics for the specified date range
    """
    try:
        query = """
            SELECT 
                platform,
                network,
                campaign_id,
                campaign_name,
                original_campaign_name,
                campaign_category,
                campaign_type,
                SUM(impressions) as impressions,
                SUM(clicks) as clicks,
                SUM(cost) as cost,
                SUM(conversions) as conversions,
                AVG(ctr) as ctr,
                AVG(conversion_rate) as conversion_rate,
                AVG(cost_per_conversion) as cost_per_conversion
            FROM public.sm_campaign_performance
            WHERE date BETWEEN :start_date AND :end_date
        """
        
        params = {"start_date": start_date, "end_date": end_date}
        
        if platform:
            query += " AND platform = :platform"
            params["platform"] = platform
            
        if network:
            query += " AND network = :network"
            params["network"] = network
            
        query += """ 
            GROUP BY 
                platform, 
                network,
                campaign_id, 
                campaign_name, 
                original_campaign_name,
                campaign_category,
                campaign_type
            ORDER BY cost DESC
        """
        
        result = db.execute(text(query), params)
        campaigns = []
        
        for row in result:
            campaign = dict(row._mapping)
            # Format numeric values for JSON response
            campaign["impressions"] = int(campaign["impressions"]) if campaign["impressions"] else 0
            campaign["clicks"] = int(campaign["clicks"]) if campaign["clicks"] else 0
            campaign["cost"] = float(campaign["cost"]) if campaign["cost"] else 0.0
            campaign["conversions"] = float(campaign["conversions"]) if campaign["conversions"] else 0.0
            campaign["ctr"] = float(campaign["ctr"]) if campaign["ctr"] else 0.0
            campaign["conversion_rate"] = float(campaign["conversion_rate"]) if campaign["conversion_rate"] else 0.0
            campaign["cost_per_conversion"] = float(campaign["cost_per_conversion"]) if campaign["cost_per_conversion"] else 0.0
            
            campaigns.append(campaign)
            
        return campaigns
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Campaign mapping endpoints
@app.get("/api/campaign-mappings", response_model=List[CampaignMapping])
def get_campaign_mappings(source_system: Optional[str] = None, db=Depends(get_db)):
    """
    Get all campaign mappings with optional filtering by source system
    """
    try:
        query = """
            SELECT * FROM public.sm_campaign_name_mapping
            WHERE is_active = TRUE
        """
        
        if source_system:
            query += f" AND source_system = '{source_system}'"
            
        query += " ORDER BY source_system, original_campaign_name"
        
        result = db.execute(text(query))
        mappings = [dict(row._mapping) for row in result]
        
        return mappings
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/unmapped-campaigns", response_model=List[UnmappedCampaign])
def get_unmapped_campaigns(db=Depends(get_db)):
    """
    Get list of campaigns that haven't been mapped yet
    """
    try:
        # First, log counts from each fact table for debugging
        table_counts = {}
        for table in ["sm_fact_google_ads", "sm_fact_bing_ads", "sm_fact_matomo", "sm_fact_redtrack"]:
            try:
                count_query = f"SELECT COUNT(*) FROM public.{table}"
                count = db.execute(text(count_query)).scalar() or 0
                table_counts[table] = count
                
                # Also check unique campaigns
                unique_query = f"SELECT COUNT(DISTINCT campaign_id) FROM public.{table}"
                unique_count = db.execute(text(unique_query)).scalar() or 0
                table_counts[f"{table}_unique"] = unique_count
            except Exception as e:
                logger.error(f"Error checking table {table}: {str(e)}")
                table_counts[table] = f"ERROR: {str(e)}"
        
        logger.info(f"Table row counts: {table_counts}")
        
        # Check if tables exist
        table_exists_query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('sm_fact_google_ads', 'sm_fact_bing_ads', 'sm_fact_matomo', 'sm_fact_redtrack', 'sm_campaign_name_mapping')
        """
        existing_tables = [row[0] for row in db.execute(text(table_exists_query)).fetchall()]
        logger.info(f"Existing tables: {existing_tables}")
        
        # If any tables are missing, create them
        missing_tables = []
        for table in ["sm_fact_google_ads", "sm_fact_bing_ads", "sm_fact_matomo", "sm_fact_redtrack", "sm_campaign_name_mapping"]:
            if table not in existing_tables:
                missing_tables.append(table)
        
        if missing_tables:
            logger.warning(f"Missing tables: {missing_tables}")
            logger.info("Running database initialization to create missing tables")
            from src.api.db_init import create_tables_if_not_exist
            create_tables_if_not_exist(db)
        
        # Create a list to store all unmapped campaigns
        unmapped_campaigns = []
        
        # Check if the mapping table exists
        if "sm_campaign_name_mapping" not in existing_tables:
            logger.warning("Campaign mapping table does not exist, creating it")
            from src.api.db_init import create_tables_if_not_exist
            create_tables_if_not_exist(db)
        
        # Process each data source if its table exists
        if "sm_fact_google_ads" in existing_tables:
            # Query for unmapped Google Ads campaigns
            google_query = """
                SELECT DISTINCT 
                    'Google Ads' as source_system,
                    CAST(g.campaign_id AS VARCHAR) as external_campaign_id,
                    g.campaign_name as campaign_name,
                    g.network as network
                FROM 
                    public.sm_fact_google_ads g
                LEFT JOIN 
                    public.sm_campaign_name_mapping m ON 
                    CAST(g.campaign_id AS VARCHAR) = m.external_campaign_id 
                    AND m.source_system = 'Google Ads'
                WHERE 
                    m.id IS NULL
            """
            
            try:
                google_results = db.execute(text(google_query)).fetchall()
                logger.info(f"Found {len(google_results)} unmapped Google Ads campaigns")
                
                for row in google_results:
                    unmapped_campaigns.append({
                        "source_system": row[0],
                        "external_campaign_id": row[1],
                        "campaign_name": row[2],
                        "network": row[3] if len(row) > 3 else None
                    })
            except Exception as e:
                logger.error(f"Error querying unmapped Google Ads campaigns: {str(e)}")
        
        if "sm_fact_bing_ads" in existing_tables:
            # Query for unmapped Bing Ads campaigns
            bing_query = """
                SELECT DISTINCT 
                    'Bing Ads' as source_system,
                    CAST(b.campaign_id AS VARCHAR) as external_campaign_id,
                    b.campaign_name as campaign_name,
                    b.network as network
                FROM 
                    public.sm_fact_bing_ads b
                LEFT JOIN 
                    public.sm_campaign_name_mapping m ON 
                    CAST(b.campaign_id AS VARCHAR) = m.external_campaign_id 
                    AND m.source_system = 'Bing Ads'
                WHERE 
                    m.id IS NULL
            """
            
            try:
                bing_results = db.execute(text(bing_query)).fetchall()
                logger.info(f"Found {len(bing_results)} unmapped Bing Ads campaigns")
                
                for row in bing_results:
                    unmapped_campaigns.append({
                        "source_system": row[0],
                        "external_campaign_id": row[1],
                        "campaign_name": row[2],
                        "network": row[3] if len(row) > 3 else None
                    })
            except Exception as e:
                logger.error(f"Error querying unmapped Bing Ads campaigns: {str(e)}")
        
        if "sm_fact_matomo" in existing_tables:
            # Query for unmapped Matomo campaigns
            matomo_query = """
                SELECT DISTINCT 
                    'Matomo' as source_system,
                    CAST(m.campaign_id AS VARCHAR) as external_campaign_id,
                    m.campaign_name as campaign_name,
                    m.network as network
                FROM 
                    public.sm_fact_matomo m
                LEFT JOIN 
                    public.sm_campaign_name_mapping mm ON 
                    CAST(m.campaign_id AS VARCHAR) = mm.external_campaign_id 
                    AND mm.source_system = 'Matomo'
                WHERE 
                    mm.id IS NULL
            """
            
            try:
                matomo_results = db.execute(text(matomo_query)).fetchall()
                logger.info(f"Found {len(matomo_results)} unmapped Matomo campaigns")
                
                for row in matomo_results:
                    unmapped_campaigns.append({
                        "source_system": row[0],
                        "external_campaign_id": row[1],
                        "campaign_name": row[2],
                        "network": row[3] if len(row) > 3 else None
                    })
            except Exception as e:
                logger.error(f"Error querying unmapped Matomo campaigns: {str(e)}")
        
        if "sm_fact_redtrack" in existing_tables:
            # Query for unmapped RedTrack campaigns
            redtrack_query = """
                SELECT DISTINCT 
                    'RedTrack' as source_system,
                    CAST(r.campaign_id AS VARCHAR) as external_campaign_id,
                    r.campaign_name as campaign_name,
                    r.network as network
                FROM 
                    public.sm_fact_redtrack r
                LEFT JOIN 
                    public.sm_campaign_name_mapping m ON 
                    CAST(r.campaign_id AS VARCHAR) = m.external_campaign_id 
                    AND m.source_system = 'RedTrack'
                WHERE 
                    m.id IS NULL
            """
            
            try:
                redtrack_results = db.execute(text(redtrack_query)).fetchall()
                logger.info(f"Found {len(redtrack_results)} unmapped RedTrack campaigns")
                
                for row in redtrack_results:
                    unmapped_campaigns.append({
                        "source_system": row[0],
                        "external_campaign_id": row[1],
                        "campaign_name": row[2],
                        "network": row[3] if len(row) > 3 else None
                    })
            except Exception as e:
                logger.error(f"Error querying unmapped RedTrack campaigns: {str(e)}")
        
        # Log the total number of unmapped campaigns found
        logger.info(f"Total unmapped campaigns found: {len(unmapped_campaigns)}")
        
        return unmapped_campaigns
    except Exception as e:
        logger.error(f"Error getting unmapped campaigns: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/campaign-mappings", response_model=CampaignMapping)
def create_campaign_mapping(mapping: CampaignMappingCreate, db=Depends(get_db)):
    """
    Create a new campaign mapping
    """
    try:
        # Check if mapping exists
        existing_query = """
            SELECT * FROM public.sm_campaign_name_mapping
            WHERE source_system = :source_system
            AND external_campaign_id = :external_campaign_id
        """
        existing = db.execute(text(existing_query), {
            "source_system": mapping.source_system,
            "external_campaign_id": mapping.external_campaign_id
        }).fetchone()
        
        if existing:
            # Update existing mapping
            query = """
                UPDATE public.sm_campaign_name_mapping
                SET 
                    pretty_campaign_name = :pretty_campaign_name,
                    campaign_category = :campaign_category,
                    campaign_type = :campaign_type,
                    network = :network,
                    pretty_network = :pretty_network,
                    pretty_source = :pretty_source,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :id
                RETURNING *
            """
            result = db.execute(text(query), {
                "id": existing.id,
                "pretty_campaign_name": mapping.pretty_campaign_name,
                "campaign_category": mapping.campaign_category,
                "campaign_type": mapping.campaign_type,
                "network": mapping.network,
                "pretty_network": mapping.pretty_network,
                "pretty_source": mapping.pretty_source
            }).fetchone()
            
            db.commit()
            return dict(result._mapping)
        else:
            # Insert new mapping with ON CONFLICT clause as recommended by senior dev
            query = """
                INSERT INTO public.sm_campaign_name_mapping (
                    source_system, 
                    external_campaign_id, 
                    original_campaign_name, 
                    pretty_campaign_name, 
                    campaign_category, 
                    campaign_type, 
                    network, 
                    display_order,
                    pretty_network,
                    pretty_source
                )
                VALUES (
                    :source_system, 
                    :external_campaign_id, 
                    :original_campaign_name, 
                    :pretty_campaign_name, 
                    :campaign_category, 
                    :campaign_type, 
                    :network, 
                    :display_order,
                    :pretty_network,
                    :pretty_source
                )
                ON CONFLICT (source_system, external_campaign_id)
                DO UPDATE SET
                    original_campaign_name = EXCLUDED.original_campaign_name,
                    pretty_campaign_name = EXCLUDED.pretty_campaign_name,
                    campaign_category = EXCLUDED.campaign_category,
                    campaign_type = EXCLUDED.campaign_type,
                    network = EXCLUDED.network,
                    pretty_network = EXCLUDED.pretty_network,
                    pretty_source = EXCLUDED.pretty_source,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING *
            """
            
            result = db.execute(text(query), {
                "source_system": mapping.source_system,
                "external_campaign_id": mapping.external_campaign_id,
                "original_campaign_name": mapping.original_campaign_name,
                "pretty_campaign_name": mapping.pretty_campaign_name,
                "campaign_category": mapping.campaign_category,
                "campaign_type": mapping.campaign_type,
                "network": mapping.network,
                "display_order": mapping.display_order or 0,
                "pretty_network": mapping.pretty_network,
                "pretty_source": mapping.pretty_source
            })
            
            db.commit()
            return dict(result.fetchone()._mapping)
    
    except Exception as e:
        logger.error(f"Error creating campaign mapping: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/campaign-mappings/{mapping_id}")
def delete_campaign_mapping(mapping_id: int, db=Depends(get_db)):
    """
    Delete a campaign mapping (soft delete by setting is_active to false)
    """
    try:
        query = """
            UPDATE public.sm_campaign_name_mapping
            SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
            WHERE id = :id
        """
        
        db.execute(text(query), {"id": mapping_id})
        db.commit()
        
        return {"message": "Mapping deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/campaigns-hierarchical", response_model=List[CampaignHierarchical])
def get_hierarchical_campaigns(db=Depends(get_db)):
    """Get all campaign data in a hierarchical structure with metrics"""
    try:
        # First check if display_order column exists
        check_column_query = """
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'sm_campaign_name_mapping' 
        AND column_name = 'display_order'
        """
        
        has_display_order = db.execute(text(check_column_query)).fetchone() is not None
        
        # Adjust query based on whether display_order exists
        if has_display_order:
            order_by_clause = "m.source_system, m.network, m.display_order, m.pretty_campaign_name"
            display_order_col = "m.display_order as display_order,"
        else:
            order_by_clause = "m.source_system, m.network, m.pretty_campaign_name"
            display_order_col = "0 as display_order,"
        
        query = f"""
            SELECT 
                m.id,
                m.source_system,
                m.external_campaign_id,
                m.original_campaign_name,
                m.pretty_campaign_name,
                m.campaign_category,
                m.campaign_type,
                m.network,
                {display_order_col}
                0 as impressions,
                0 as clicks,
                0 as conversions,
                0 as cost
            FROM 
                sm_campaign_name_mapping m
            WHERE 
                m.is_active = TRUE
            ORDER BY 
                {order_by_clause}
        """
        
        result = db.execute(text(query)).fetchall()
        
        # Convert to list of dictionaries
        return [dict(row._mapping) for row in result]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/campaign-order")
def update_campaign_order(orders: List[CampaignOrderUpdate], db=Depends(get_db)):
    """Update the display order of campaigns"""
    try:
        # First check if display_order column exists
        check_column_query = """
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'sm_campaign_name_mapping' 
        AND column_name = 'display_order'
        """
        
        has_display_order = db.execute(text(check_column_query)).fetchone() is not None
        
        # If display_order doesn't exist, create it
        if not has_display_order:
            add_column_query = """
            ALTER TABLE public.sm_campaign_name_mapping
            ADD COLUMN display_order INT DEFAULT 0
            """
            db.execute(text(add_column_query))
            db.commit()
        
        # Update the display_order for each campaign
        for order in orders:
            query = """
                UPDATE sm_campaign_name_mapping
                SET display_order = :display_order,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :id
            """
            
            db.execute(
                text(query),
                {
                    "id": order.id,
                    "display_order": order.display_order
                }
            )
        
        db.commit()
        return {"success": True, "message": "Campaign orders updated successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.options("/api/admin/clear_google_ads_mappings")
async def options_clear_google_ads_mappings():
    return handle_cors_preflight()

@app.options("/api/admin/import_real_google_ads_data")
async def options_import_real_google_ads_data():
    return handle_cors_preflight()

def handle_cors_preflight():
    """Handle CORS preflight requests with appropriate headers"""
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
        "Access-Control-Max-Age": "3600",
    }
    return JSONResponse(content={}, headers=headers)

@app.post("/api/admin/clear_google_ads_mappings")
def admin_clear_google_ads_mappings(db=Depends(get_db)):
    """Clear all Google Ads campaign mappings"""
    from admin_commands import clear_google_ads_mappings
    
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization"
    }
    
    try:
        logger.info("Admin endpoint: clear_google_ads_mappings called")
        success = clear_google_ads_mappings(db)
        return JSONResponse(
            content={"success": success},
            headers=headers
        )
    except Exception as e:
        logger.error(f"Error in clear_google_ads_mappings endpoint: {str(e)}")
        return JSONResponse(
            content={"success": False, "error": str(e)},
            status_code=500,
            headers=headers
        )

@app.post("/api/admin/import_real_google_ads_data")
def admin_import_real_google_ads_data(data: dict = Body(None), db=Depends(get_db)):
    """Import real Google Ads data"""
    from admin_commands import import_real_google_ads_data
    
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization"
    }
    
    try:
        logger.info(f"Admin endpoint: import_real_google_ads_data called with data: {type(data)}")
        success = import_real_google_ads_data(db, data)
        return JSONResponse(
            content={"success": success},
            headers=headers
        )
    except Exception as e:
        logger.error(f"Error in import_real_google_ads_data endpoint: {str(e)}")
        return JSONResponse(
            content={"success": False, "error": str(e)},
            status_code=500,
            headers=headers
        )

@app.get("/api/google-ads/campaigns")
def get_google_ads_campaigns(db=Depends(get_db)):
    """Get all Google Ads campaigns"""
    logger.info("Endpoint called: get_google_ads_campaigns")
    try:
        # Query Google Ads campaigns from the database
        query = text("""
        SELECT 
            id, 
            campaign_id, 
            campaign_name,
            COALESCE(campaign_name, '') as pretty_campaign_name,
            '' as campaign_type,
            '' as network
        FROM (
            SELECT DISTINCT
                id,
                campaign_id,
                campaign_name
            FROM sm_fact_google_ads
        ) c
        ORDER BY campaign_name
        """)
        
        result = db.execute(query).fetchall()
        
        # Convert to list of dictionaries
        campaigns = []
        for row in result:
            campaign = {
                "id": row[0],
                "campaign_id": row[1],
                "campaign_name": row[2],
                "pretty_campaign_name": row[3],
                "campaign_type": row[4],
                "network": row[5]
            }
            campaigns.append(campaign)
        
        logger.info(f"Retrieved {len(campaigns)} Google Ads campaigns")
        return campaigns
    except Exception as e:
        logger.error(f"Error retrieving Google Ads campaigns: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/websocket-status", tags=["Diagnostics"])
async def websocket_status():
    """
    Endpoint to check the status of the WebSocket server.
    Returns information about the WebSocket configuration and active connections.
    """
    try:
        active_connections = len(manager.active_connections) if 'manager' in globals() else 0
        
        return {
            "status": "running",
            "active_connections": active_connections,
            "websocket_endpoint": "/ws",
            "fallback_endpoint": "/api/ws-fallback",
            "server_time": datetime.datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "server_time": datetime.datetime.now().isoformat()
        }

# Fallback OPTIONS handler for all routes
@app.options("/{path:path}")
async def options_handler(path: str, request: Request):
    """
    Global OPTIONS handler to ensure CORS preflight requests are handled for all routes
    This is a fallback in case FastAPI's built-in CORS handling fails
    """
    print(f"Handling OPTIONS request for path: /{path}")
    
    # Get the origin from the request
    origin = request.headers.get("origin", "")
    
    # Create a response
    response = JSONResponse(content={"detail": "CORS preflight request handled"})
    
    # Set CORS headers
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

@app.get("/api/health")
def api_health_check():
    """
    Simple health check endpoint for Railway
    """
    return {"status": "OK"}

# Mount the React frontend static files
frontend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "src", "frontend", "build")
app.mount("/static", StaticFiles(directory=os.path.join(frontend_path, "static")), name="static")

@app.get("/api/test-cors", tags=["Diagnostics"])
async def test_cors_detailed(request: Request):
    """
    Alias for /api/cors-test endpoint.
    """
    return await test_cors(request)

# This must be the last route to avoid conflicts with API routes
@app.get("/{path:path}")
async def catch_all_routes(path: str):
    if path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API route not found")
    return FileResponse(os.path.join(frontend_path, "index.html"))

if __name__ == "__main__":
    import uvicorn
    # Get port from environment variable or use 5000 as default
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
