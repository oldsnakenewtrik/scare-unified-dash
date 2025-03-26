from fastapi import FastAPI, Depends, HTTPException, Query, Path, status, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, SQLAlchemyError # Added SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest

# Import the new db_dependency module
from src.api.db_dependency import get_db, set_session_local

# Importing DB utilities
try:
    from .db_init import initialize_database, connect_with_retry, ensure_network_column_exists
except ImportError:
    # Try absolute import if relative import fails
    from src.api.db_init import initialize_database, connect_with_retry, ensure_network_column_exists

# Import the database monitoring module
try:
    from .db_monitor import initialize_monitor, get_db_status, force_db_reconnect
    from .db_config import get_database_url
except ImportError:
    # Try absolute import if relative import fails
    from src.api.db_monitor import initialize_monitor, get_db_status, force_db_reconnect
    from src.api.db_config import get_database_url

# Set up logging
import datetime
import os
import uuid
import logging
import traceback
import json
import sys
import time
from typing import List, Dict, Any, Optional, Tuple, Union
from pathlib import Path
from dotenv import load_dotenv
import asyncio
import aiohttp

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# EMERGENCY FIX: Hardcode the database URL directly
# This bypasses any issues with variable interpolation
logger.info("EXTREMELY CRITICAL DB FIX: Using existing DATABASE_URL")
database_url = os.getenv("DATABASE_URL")
if database_url:
    # Mask the password for logging (extract just the password part)
    parts = database_url.split('@')
    if len(parts) > 1:
        auth_part = parts[0].split('://')
        if len(auth_part) > 1:
            masked_url = f"{auth_part[0]}://{auth_part[1].split(':')[0]}:****@{parts[1]}"
            logger.info(f"DATABASE_URL already set to: {masked_url}")
        else:
            logger.info(f"DATABASE_URL has unexpected format. Using as is.")
    else:
        logger.info(f"DATABASE_URL has unexpected format. Using as is.")
else:
    logger.error("CRITICAL ERROR: DATABASE_URL environment variable is not set!")
    # Attempt to create it from other environment variables as a last resort
    database_public_url = os.getenv("DATABASE_PUBLIC_URL")
    if database_public_url:
        logger.info("Using DATABASE_PUBLIC_URL as fallback")
        os.environ["DATABASE_URL"] = database_public_url
        masked_url = database_public_url.replace(database_public_url.split("@")[0].split("://")[1], "****")
        logger.info(f"Set DATABASE_URL to: {masked_url}")

# Initialize the FastAPI app
app = FastAPI(
    title="SCARE Unified Dashboard API",
    description="API for the SCARE Unified Dashboard",
    version="0.1.0"
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

# Debug print to verify app initialization
print("DEBUG: FastAPI app initialized!")

# Add CORS middleware - use environment variables for configuration
allowed_origins = os.environ.get("CORS_ALLOW_ORIGINS", "http://localhost:3000")
allowed_origins = [origin.strip() for origin in allowed_origins.split(",")]

# Log the CORS origins for debugging
logger.info(f"CORS allowed origins: {allowed_origins}")

# Add the frontend domain if it's not already in the list
frontend_domain = "https://front-production-f6e6.up.railway.app"
if frontend_domain not in allowed_origins:
    allowed_origins.append(frontend_domain)
    logger.info(f"Added frontend domain to CORS allowed origins: {frontend_domain}")

allow_credentials = os.environ.get("CORS_CREDENTIALS", "true").lower() == "true"
allowed_methods = os.environ.get("CORS_METHODS", "GET,POST,PUT,DELETE,OPTIONS").split(",")
allowed_headers = os.environ.get("CORS_HEADERS", "Content-Type,Authorization,Accept").split(",")

logger.info(f"CORS Configuration: origins={allowed_origins}, credentials={allow_credentials}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=allow_credentials,
    allow_methods=allowed_methods,
    allow_headers=allowed_headers,
)

# Custom middlewares below were removed to simplify header handling and rely on the main CORSMiddleware.

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

# Simple health check endpoint that doesn't depend on database
@app.get("/api/health", tags=["Health"])
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
        is_allowed = origin in ["https://front-production-f6e6.up.railway.app", "http://localhost:3000", "http://localhost:5000", "http://localhost:5001"]
        
        # Return detailed information about the request and CORS configuration
        response = JSONResponse(
            content={
                "message": "CORS test endpoint",
                "timestamp": datetime.datetime.now().isoformat(),
                "request_origin": origin,
                "is_origin_allowed": is_allowed,
                "allowed_origins": ["https://front-production-f6e6.up.railway.app", "http://localhost:3000", "http://localhost:5000", "http://localhost:5001"],
                "cors_middleware": {
                    "allow_credentials": False,
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

# Add the missing endpoints that match what the frontend is expecting
@app.get("/api/campaigns-hierarchical", tags=["Campaigns"])
async def get_campaigns_hierarchical(db=Depends(get_db)):
    """
    Get hierarchical campaign data including metrics 
    """
    # Debug print to confirm this route is registered
    logger.info("DEBUG: campaigns-hierarchical route was called!")
    
    try:
        logger.info("Fetching hierarchical campaign data")
        
        # Check if sm_campaign_name_mapping table exists
        try:
            check_query = text("SELECT COUNT(*) FROM public.sm_campaign_name_mapping LIMIT 1") # Corrected table name
            result = db.execute(check_query)
            count = result.scalar()
            logger.info(f"public.sm_campaign_name_mapping table exists, found {count} records") # Corrected log message
        except Exception as e:
            logger.error(f"Error checking public.sm_campaign_name_mapping table: {str(e)}") # Corrected log message
            return {"error": f"Database error: public.sm_campaign_name_mapping table may not exist. {str(e)}", "status": "error"} # Corrected error message
        
        # Query campaign data using the sm_campaign_performance view which aggregates metrics
        query = text("""
            SELECT
                cm.id,
                cm.source_system,
                cm.external_campaign_id,
                cm.original_campaign_name,
                cm.pretty_campaign_name,
                cm.campaign_category,
                cm.campaign_type,
                cm.network, -- Use network from mapping table
                cm.pretty_network, -- Also include pretty_network
                cm.pretty_source, -- Also include pretty_source
                cm.display_order,
                COALESCE(SUM(perf.impressions), 0) AS impressions,
                COALESCE(SUM(perf.clicks), 0) AS clicks,
                COALESCE(SUM(perf.conversions), 0) AS conversions,
                COALESCE(SUM(perf.cost), 0) AS cost
            FROM public.sm_campaign_name_mapping cm
            LEFT JOIN public.sm_campaign_performance perf
                ON cm.external_campaign_id = perf.campaign_id::VARCHAR -- Ensure type match if campaign_id is not VARCHAR
                AND cm.source_system = perf.platform -- Match source_system with platform from view
            WHERE cm.is_active = TRUE
            GROUP BY
                cm.id, -- Group by all selected non-aggregated columns from cm
                cm.source_system,
                cm.external_campaign_id,
                cm.original_campaign_name,
                cm.pretty_campaign_name,
                cm.campaign_category,
                cm.campaign_type,
                cm.network,
                cm.pretty_network,
                cm.pretty_source,
                cm.display_order
            ORDER BY cm.display_order, cm.pretty_campaign_name
        """)
        
        result = db.execute(query)
        campaigns = []
        
        for row in result:
            campaign = {
                "id": row.id,
                "source_system": row.source_system,
                "external_campaign_id": row.external_campaign_id,
                "original_campaign_name": row.original_campaign_name,
                "pretty_campaign_name": row.pretty_campaign_name,
                "campaign_category": row.campaign_category,
                "campaign_type": row.campaign_type,
                "network": row.network,
                "display_order": row.display_order,
                "impressions": row.impressions,
                "clicks": row.clicks,
                "conversions": float(row.conversions) if row.conversions else 0,
                "cost": float(row.cost) if row.cost else 0
            }
            campaigns.append(campaign)
        
        logger.info(f"Returning {len(campaigns)} campaign records from hierarchical endpoint")
        return campaigns
        
    except SQLAlchemyError as e:
        error_msg = f"Database error fetching hierarchical campaign data: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg, "status": "error"}
    except Exception as e:
        error_msg = f"Error fetching hierarchical campaign data: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg, "status": "error"}

@app.get("/api/campaigns-performance", tags=["Campaigns"])
async def get_campaigns_performance(
    start_date: datetime.date, 
    end_date: datetime.date,
    db=Depends(get_db)
):
    """
    Get campaign performance data for a specific date range
    """
    # Debug print to confirm this route is registered
    logger.info("DEBUG: campaigns-performance route was called!")
    
    try:
        logger.info(f"Fetching campaign performance data for {start_date} to {end_date}")
        
        # Query campaign performance data
        query = text("""
            SELECT 
                cf.campaign_id,
                cf.campaign_name,
                cf.source_system,
                cf.date,
                cf.impressions,
                cf.clicks,
                cf.spend,
                cf.revenue,
                cf.conversions,
                CASE WHEN cf.clicks > 0 THEN cf.spend / cf.clicks ELSE 0 END AS cpc
            FROM campaign_fact cf
            WHERE cf.date BETWEEN :start_date AND :end_date
            ORDER BY cf.date DESC, cf.campaign_name
        """)
        
        result = db.execute(query, {
            "start_date": start_date,
            "end_date": end_date
        })
        
        campaigns = []
        for row in result:
            campaign = {
                "campaign_id": row.campaign_id,
                "campaign_name": row.campaign_name,
                "source_system": row.source_system,
                "date": row.date.isoformat(),
                "impressions": row.impressions,
                "clicks": row.clicks,
                "spend": float(row.spend) if row.spend else 0,
                "revenue": float(row.revenue) if row.revenue else 0,
                "conversions": float(row.conversions) if row.conversions else 0,
                "cpc": float(row.cpc) if row.cpc else 0
            }
            campaigns.append(campaign)
        
        return campaigns
        
    except SQLAlchemyError as e:
        error_msg = f"Database error fetching campaign performance data: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg, "status": "error"}
    except Exception as e:
        error_msg = f"Error fetching campaign performance data: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg, "status": "error"}

@app.get("/api/campaign-metrics", tags=["Campaigns"])
async def get_campaign_metrics(
    start_date: datetime.date, 
    end_date: datetime.date,
    db=Depends(get_db)
):
    """
    Alias for campaigns-performance to match frontend API calls
    """
    # Debug print to confirm this route is registered
    logger.info("DEBUG: campaign-metrics route was called!")
    
    logger.info(f"campaign-metrics endpoint called, forwarding to campaigns-performance")
    # Reuse the campaigns-performance endpoint
    return await get_campaigns_performance(start_date, end_date, db)

@app.get("/api/campaign-mappings", tags=["Campaigns"])
async def get_campaign_mappings(db=Depends(get_db)):
    """
    Get all campaign mappings in the system
    """
    logger.info("Campaign mappings endpoint called")
    try:
        # Check if the table exists
        table_exists_query = text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'sm_campaign_name_mapping'
            )
        """)
        table_exists = db.execute(table_exists_query).scalar()
        
        if not table_exists:
            logger.warning("Campaign mappings table does not exist")
            return []
            
        # Query all mappings, including all relevant fields
        query = text("""
            SELECT
                id,
                source_system,
                external_campaign_id,
                original_campaign_name, -- Use original name from table
                pretty_campaign_name,
                campaign_category,
                campaign_type,
                network,
                pretty_network,
                pretty_source,
                display_order,
                is_active,
                created_at,
                updated_at
            FROM public.sm_campaign_name_mapping
            ORDER BY display_order, source_system, original_campaign_name -- Order by display_order first
        """)
        
        result = db.execute(query).fetchall()
        
        # Convert to list of dictionaries using column names
        mappings = [dict(row._mapping) for row in result]
        
        # Ensure datetime objects are converted to ISO format strings for JSON serialization
        for mapping in mappings:
            if mapping.get('created_at') and isinstance(mapping['created_at'], datetime.datetime):
                mapping['created_at'] = mapping['created_at'].isoformat()
            if mapping.get('updated_at') and isinstance(mapping['updated_at'], datetime.datetime):
                mapping['updated_at'] = mapping['updated_at'].isoformat()

        return mappings
    except Exception as e:
        logger.error(f"Error getting campaign mappings: {str(e)}")
        # Return empty array to prevent frontend errors
        return []

@app.get("/api/unmapped-campaigns", tags=["Campaigns"])
async def get_unmapped_campaigns(db=Depends(get_db)):
    """
    Get all campaigns that don't have a mapping
    """
    logger.info("Unmapped campaigns endpoint called")
    try:
        # First check if required tables exist
        tables_query = text("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public' 
            AND tablename IN ('sm_fact_google_ads', 'sm_fact_bing_ads', 'sm_fact_matomo', 'sm_fact_redtrack', 'sm_campaign_name_mapping')
        """)
        
        existing_tables = [row[0] for row in db.execute(tables_query).fetchall()]
        required_tables = ['sm_fact_google_ads', 'sm_fact_bing_ads', 'sm_fact_matomo', 'sm_fact_redtrack', 'sm_campaign_name_mapping']
        
        missing_tables = [table for table in required_tables if table not in existing_tables]
        
        if missing_tables:
            logger.warning(f"Missing required tables: {missing_tables}")
            return []
            
        # Query unmapped campaigns
        query = text("""
            WITH all_campaigns AS (
                SELECT DISTINCT 'Google Ads' as source, CAST(campaign_id AS VARCHAR) as id, 
                       campaign_name as name
                FROM public.sm_fact_google_ads 
                WHERE campaign_id IS NOT NULL
                
                UNION ALL
                
                SELECT DISTINCT 'Bing Ads' as source, CAST(campaign_id AS VARCHAR) as id,
                       campaign_name as name
                FROM public.sm_fact_bing_ads 
                WHERE campaign_id IS NOT NULL
                
                UNION ALL
                
                SELECT DISTINCT 'Matomo' as source, CAST(campaign_id AS VARCHAR) as id,
                       campaign_name as name 
                FROM public.sm_fact_matomo 
                WHERE campaign_id IS NOT NULL
                
                UNION ALL
                
                SELECT DISTINCT 'RedTrack' as source, CAST(campaign_id AS VARCHAR) as id,
                       campaign_name as name
                FROM public.sm_fact_redtrack 
                WHERE campaign_id IS NOT NULL
            )
            SELECT ac.source, ac.id, ac.name
            FROM all_campaigns ac
            LEFT JOIN public.sm_campaign_name_mapping m 
              ON ac.source = m.source_system AND ac.id = m.external_campaign_id
            WHERE m.id IS NULL
            ORDER BY ac.source, ac.name
        """)
        
        result = db.execute(query).fetchall()
        
        # Convert to list of dictionaries
        unmapped_campaigns = [
            {
                "source_system": row[0],
                "external_campaign_id": row[1],
                "campaign_name": row[2]
            }
            for row in result
        ]
        
        return unmapped_campaigns
    except Exception as e:
        logger.error(f"Error getting unmapped campaigns: {str(e)}")
        # Return empty array to prevent frontend errors
        return []

@app.post("/api/campaign-mappings", tags=["Campaigns"])
async def create_campaign_mapping(mapping: CampaignMappingCreate, db=Depends(get_db)):
    """
    Create a new campaign mapping
    """
    try:
        logger.info(f"Creating campaign mapping for {mapping.source_system}/{mapping.external_campaign_id}")
        
        # Insert the new mapping
        query = text("""
            INSERT INTO public.sm_campaign_name_mapping (
                source_system,
                external_campaign_id,
                original_campaign_name,
                pretty_campaign_name,
                campaign_category,
                campaign_type,
                network,
                pretty_network,
                pretty_source,
                display_order,
                is_active
            ) VALUES (
                :source_system,
                :external_campaign_id,
                :original_campaign_name,
                :pretty_campaign_name,
                :campaign_category,
                :campaign_type,
                :network,
                :pretty_network,
                :pretty_source,
                :display_order,
                TRUE
            )
            RETURNING id
        """)

        # Prepare parameters, excluding the removed fields
        params = {
            "source_system": mapping.source_system,
            "external_campaign_id": mapping.external_campaign_id,
            "original_campaign_name": mapping.original_campaign_name,
            "pretty_campaign_name": mapping.pretty_campaign_name,
            "campaign_category": mapping.campaign_category,
            "campaign_type": mapping.campaign_type,
            "network": mapping.network,
            "pretty_network": mapping.pretty_network, # Re-added
            "pretty_source": mapping.pretty_source,   # Re-added
            "display_order": mapping.display_order or 999 # Default display_order
        }

        logger.info(f"Executing insert with params: {params}")
        result = db.execute(query, params)

        logger.info("Insert executed, attempting commit...")
        db.commit() # Commit happens here
        logger.info("Commit successful.")

        new_id = result.fetchone()[0]
        logger.info(f"Successfully created campaign mapping with ID: {new_id}")
        return {"id": new_id, "message": "Campaign mapping created successfully"}

    except SQLAlchemyError as e:
        db.rollback()
        error_msg = f"Database error creating campaign mapping: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc()) # Log full traceback
        # Raise HTTPException for clearer error reporting
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_msg)
    except Exception as e:
        db.rollback()
        error_msg = f"Unexpected error creating campaign mapping: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc()) # Log full traceback
        # Raise HTTPException for clearer error reporting
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_msg)


@app.delete("/api/campaign-mappings/{mapping_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Campaigns"])
async def delete_campaign_mapping(mapping_id: int, db=Depends(get_db)):
    """
    Delete a campaign mapping by its ID.
    """
    logger.info(f"Attempting to delete campaign mapping with ID: {mapping_id}")
    try:
        # Check if the mapping exists first
        check_query = text("SELECT id FROM public.sm_campaign_name_mapping WHERE id = :id")
        existing = db.execute(check_query, {"id": mapping_id}).fetchone()

        if not existing:
            logger.warning(f"Campaign mapping with ID {mapping_id} not found for deletion.")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Campaign mapping with ID {mapping_id} not found")

        # Execute the delete operation
        delete_query = text("DELETE FROM public.sm_campaign_name_mapping WHERE id = :id")
        result = db.execute(delete_query, {"id": mapping_id})

        # Verify deletion
        if result.rowcount == 0:
            # This case should ideally not happen if the check above passed, but good to handle
            logger.error(f"Failed to delete campaign mapping ID {mapping_id} even though it was found.")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete campaign mapping after finding it.")

        db.commit()
        logger.info(f"Successfully deleted campaign mapping with ID: {mapping_id}")
        # Return No Content on successful deletion
        return

    except HTTPException:
        # Re-raise HTTPException to return specific status codes (like 404)
        db.rollback()
        raise
    except SQLAlchemyError as e:
        db.rollback()
        error_msg = f"Database error deleting campaign mapping ID {mapping_id}: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_msg)
    except Exception as e:
        db.rollback()
        error_msg = f"Unexpected error deleting campaign mapping ID {mapping_id}: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_msg)

@app.post("/api/campaign-order", tags=["Campaigns"])
async def update_campaign_order(orders: List[CampaignOrderUpdate], db=Depends(get_db)):
    """
    Update display order for multiple campaigns
    """
    try:
        logger.info(f"Updating display order for {len(orders)} campaigns")
        
        # Update each campaign's display order
        for order in orders:
            query = text("""
                UPDATE campaign_mappings
                SET display_order = :display_order
                WHERE id = :id
            """)
            
            db.execute(query, {
                "id": order.id,
                "display_order": order.display_order
            })
        
        # Commit the transaction
        db.commit()
        
        return {"message": f"Updated display order for {len(orders)} campaigns"}
        
    except SQLAlchemyError as e:
        db.rollback()
        error_msg = f"Database error updating campaign display order: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg, "status": "error"}
    except Exception as e:
        db.rollback()
        error_msg = f"Error updating campaign display order: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg, "status": "error"}

@app.post("/api/campaign-mappings/archive", tags=["Campaigns"])
async def archive_campaign_mapping(mapping_id: int = Body(..., embed=True), db=Depends(get_db)):
    """
    Archive a campaign mapping
    """
    try:
        logger.info(f"Archiving campaign mapping with ID {mapping_id}")
        
        # Update the mapping to set is_active = FALSE
        query = text("""
            UPDATE campaign_mappings
            SET is_active = FALSE
            WHERE id = :id
            RETURNING id
        """)
        
        result = db.execute(query, {"id": mapping_id})
        
        # Check if any row was affected
        if result.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Campaign mapping with ID {mapping_id} not found"
            )
        
        # Commit the transaction
        db.commit()
        
        return {"message": f"Campaign mapping with ID {mapping_id} archived successfully"}
        
    except SQLAlchemyError as e:
        db.rollback()
        error_msg = f"Database error archiving campaign mapping with ID {mapping_id}: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg, "status": "error"}
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        error_msg = f"Error archiving campaign mapping: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg, "status": "error"}

# Add a test endpoint that doesn't require database access
@app.get("/api/test", tags=["Test"])
async def test_endpoint():
    """
    Simple test endpoint that doesn't require database access.
    Use this to verify the API is responding properly.
    """
    return {
        "status": "success",
        "message": "API is working",
        "timestamp": datetime.datetime.now().isoformat()
    }

# Add unmapped campaigns endpoint to surface campaigns that need mapping
@app.get("/api/unmapped-campaigns", tags=["Campaigns"])
async def get_unmapped_campaigns(db=Depends(get_db)):
    """
    Get campaigns that don't have mappings yet so they can be mapped manually.
    This endpoint is used by the mapping UI to surface new campaigns.
    """
    try:
        logger.info("Fetching unmapped campaigns")
        
        # First check if Google Ads data exists
        check_google_data = text("SELECT COUNT(*) FROM sm_fact_google_ads")
        google_count = db.execute(check_google_data).scalar()
        logger.info(f"Total records in sm_fact_google_ads: {google_count}")
        
        # Log a sample of Google Ads data to verify what's available
        if google_count > 0:
            sample_query = text("SELECT campaign_id, campaign_name, network FROM sm_fact_google_ads LIMIT 3")
            sample_rows = db.execute(sample_query).fetchall()
            for row in sample_rows:
                logger.info(f"Sample Google Ads row: {row}")
        
        # Check campaign_mappings table
        check_mappings = text("SELECT COUNT(*) FROM campaign_mappings")
        mappings_count = db.execute(check_mappings).scalar()
        logger.info(f"Total records in campaign_mappings: {mappings_count}")
        
        # Check if the unique campaigns query works as expected
        test_unique = text("""
            SELECT COUNT(*) FROM (
                SELECT DISTINCT
                    campaign_id,
                    campaign_name,
                    network
                FROM sm_fact_google_ads
            ) AS unique_count
        """)
        unique_count = db.execute(test_unique).scalar()
        logger.info(f"Total unique campaigns in Google Ads: {unique_count}")
        
        # Now proceed with the original query for unmapped campaigns from Google Ads
        google_query = text("""
            WITH unique_campaigns AS (
                SELECT DISTINCT
                    campaign_id,
                    campaign_name,
                    network
                FROM sm_fact_google_ads
            )
            SELECT DISTINCT
                'Google Ads' as source_system,
                uc.campaign_id as external_campaign_id,
                uc.campaign_name as campaign_name,
                uc.network as network
            FROM unique_campaigns uc
            LEFT JOIN campaign_mappings cm ON uc.campaign_id = cm.external_campaign_id 
                AND cm.source_system = 'Google Ads'
            WHERE cm.id IS NULL
            ORDER BY uc.campaign_name
            LIMIT 100
        """)
        
        # Log that we're about to execute the Google Ads query
        logger.info("Executing Google Ads query for unmapped campaigns")
        
        # Execute query with full error catching
        try:
            google_results = db.execute(google_query)
            
            # Log Google query results
            google_list = []
            for row in google_results:
                campaign = {
                    "source_system": row.source_system,
                    "external_campaign_id": row.external_campaign_id,
                    "campaign_name": row.campaign_name,
                    "network": row.network
                }
                google_list.append(campaign)
                
            logger.info(f"Found {len(google_list)} unmapped Google Ads campaigns")
            if google_list:
                logger.info(f"First unmapped campaign: {google_list[0]}")
        except Exception as query_error:
            logger.error(f"Error executing Google Ads query: {str(query_error)}")
            # Log the exception details
            import traceback
            logger.error(traceback.format_exc())
            google_list = []
        
        # Similar debugging for Bing Ads
        check_bing_data = text("SELECT COUNT(*) FROM sm_fact_bing_ads")
        bing_count = db.execute(check_bing_data).scalar()
        logger.info(f"Total records in sm_fact_bing_ads: {bing_count}")
            
        # Query for unmapped campaigns from Bing Ads
        bing_query = text("""
            WITH unique_campaigns AS (
                SELECT DISTINCT
                    campaign_id,
                    campaign_name,
                    network
                FROM sm_fact_bing_ads
            )
            SELECT DISTINCT
                'Bing Ads' as source_system,
                uc.campaign_id as external_campaign_id,
                uc.campaign_name as campaign_name,
                uc.network as network
            FROM unique_campaigns uc
            LEFT JOIN campaign_mappings cm ON uc.campaign_id = cm.external_campaign_id 
                AND cm.source_system = 'Bing Ads'
            WHERE cm.id IS NULL
            ORDER BY uc.campaign_name
            LIMIT 100
        """)
        
        # Log that we're about to execute the Bing Ads query
        logger.info("Executing Bing Ads query for unmapped campaigns")
        
        try:
            bing_results = db.execute(bing_query)
            
            # Log Bing query results
            bing_list = []
            for row in bing_results:
                campaign = {
                    "source_system": row.source_system,
                    "external_campaign_id": row.external_campaign_id,
                    "campaign_name": row.campaign_name,
                    "network": row.network
                }
                bing_list.append(campaign)
                
            logger.info(f"Found {len(bing_list)} unmapped Bing Ads campaigns")
        except Exception as query_error:
            logger.error(f"Error executing Bing Ads query: {str(query_error)}")
            # Log the exception details
            import traceback
            logger.error(traceback.format_exc())
            bing_list = []
        
        # Combine results
        unmapped_campaigns = google_list + bing_list
        
        # Return combined result
        logger.info(f"Returning a total of {len(unmapped_campaigns)} unmapped campaigns")
        return unmapped_campaigns
    except SQLAlchemyError as e:
        error_msg = f"Database error fetching unmapped campaigns: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg, "status": "error"}
    except Exception as e:
        error_msg = f"Error fetching unmapped campaigns: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg, "status": "error"}

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

# Root endpoint for quick testing
@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint for testing basic connectivity
    """
    logger.info("Root endpoint called")
    return {
        "message": "SCARE Unified Dashboard API is running",
        "version": "0.1.0",
        "timestamp": datetime.datetime.now().isoformat()
    }

# Additional health check without the /api prefix
@app.get("/health", tags=["Health"])
async def root_health_check():
    """
    Simple health check without the /api prefix
    """
    logger.info("Root health check called")
    return {
        "status": "healthy",
        "timestamp": datetime.datetime.now().isoformat()
    }

DATABASE_URL = get_database_url()

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
    
    # Set up the session factory
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Set the SessionLocal in our db_dependency module
    set_session_local(SessionLocal)
    
    # Initialize database at startup
    try:
        initialize_database()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
except Exception as e:
    logger.critical(f"Failed to connect to database: {str(e)}")
    # Note: We don't want to crash the server here, so we'll continue
    # The database connection will be retried in the connect_with_retry function

# Startup event to initialize database without blocking app startup
@app.on_event("startup")
async def startup_event():
    """
    Initialize database on startup without blocking the app from starting
    """
    logger.info("Application starting up...")
    
    # Run in a separate thread to avoid blocking the app startup
    def init_db_async():
        try:
            # First, ensure the network column exists in the sm_fact_bing_ads table
            # This is a critical fix that needs to run before other operations
            logger.info("Checking for network column in sm_fact_bing_ads table...")
            network_column_exists = ensure_network_column_exists()
            if network_column_exists:
                logger.info("Network column check completed successfully")
            else:
                logger.warning("Failed to ensure network column exists - application may encounter errors")
            
            # Then initialize the database normally
            logger.info("Initializing database...")
            engine, connection = initialize_database()
            if engine and connection:
                logger.info("Database initialized successfully")
            else:
                logger.error("Failed to initialize database")
        except Exception as e:
            logger.error(f"Error during database initialization: {e}")
            logger.error(traceback.format_exc())
    
    # Start the initialization in a separate thread
    import threading
    db_thread = threading.Thread(target=init_db_async)
    db_thread.daemon = True  # Allow the thread to exit when the main thread exits
    db_thread.start()
    logger.info("Database initialization started in background thread")
    
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

# Health check endpoint for verifying server status
@app.get("/health")
def health_check():
    """
    Simple health check endpoint that doesn't depend on the database.
    This is used for basic health checks to verify the service is running.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.datetime.now().isoformat(),
        "message": "API server is running. For detailed diagnostics, use /api/health or /api/db-status"
    }

# Simple health check endpoint that doesn't depend on database
@app.get("/api/simple-health")
def simple_health_check():
    """
    A simple health check endpoint that doesn't depend on the database.
    This is used by Railway for health checks to ensure the service is running.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.datetime.now().isoformat(),
        "message": "API server is running"
    }

# Health check endpoint to test CORS headers
@app.get("/api/cors-test")
def test_cors(request: Request):
    """
    Test endpoint to verify CORS configuration
    Returns details about the CORS configuration to help with debugging
    """
    headers = dict(request.headers)
    
    # Mask sensitive headers for security
    for sensitive_header in ['authorization', 'cookie', 'sec-websocket-key']:
        if sensitive_header in headers:
            headers[sensitive_header] = "[REDACTED]"
    
    # Get the origin from the request headers if present
    origin = headers.get('origin', None)
    
    # Determine if this origin is allowed
    origin_allowed = False
    if origin:
        origin_allowed = origin in allowed_origins or "*" in allowed_origins
    
    # Create a detailed CORS report
    cors_details = {
        "configured_allowed_origins": allowed_origins,
        "request_origin": origin,
        "origin_allowed": origin_allowed,
        "allow_credentials": allow_credentials,
        "allowed_methods": allowed_methods,
        "allowed_headers": allowed_headers
    }
    
    # Include current CORS settings
    response = {
        "status": "ok",
        "timestamp": datetime.datetime.now().isoformat(),
        "message": "CORS test endpoint",
        "request_headers": headers,
        "cors_configuration": cors_details,
        "server_info": {
            "frontend_build_path": os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                      "src", "frontend", "build"),
            "environment": os.environ.get("ENVIRONMENT", "unknown"),
            "port": os.environ.get("PORT", "8080"),
            "database_url_format": get_safe_db_url_for_display()
        }
    }
    
    # Add CORS headers to the response
    return response
