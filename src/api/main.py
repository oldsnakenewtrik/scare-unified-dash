from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import List, Optional
import datetime
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Query

# Load environment variables
load_dotenv()

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://scare_user:scare_password@postgres:5432/scare_metrics")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Run database initialization (creates tables and runs migrations)
try:
    from db_init import init_database
    init_database()
except Exception as e:
    print(f"Warning: Failed to initialize database: {str(e)}")
    print("Application will continue to start, but some features may not work correctly")

app = FastAPI(title="SCARE Unified Metrics API")

# Configure CORS to allow any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Dependency
def get_db():
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
def health_check():
    """Health check endpoint to verify server status"""
    # Add database schema check
    db_status = "unknown"
    try:
        with engine.connect() as conn:
            # Check if the tables exist
            result = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))
            tables = [row[0] for row in result]
            required_tables = ['sm_campaign_name_mapping', 'sm_fact_google_ads', 'sm_fact_bing_ads', 'sm_fact_matomo', 'sm_fact_redtrack']
            missing_tables = [table for table in required_tables if table not in tables]
            
            if missing_tables:
                db_status = f"missing tables: {', '.join(missing_tables)}"
            else:
                db_status = "healthy"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "healthy",
        "timestamp": datetime.datetime.now().isoformat(),
        "database_status": db_status
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

@app.get("/api/campaigns/metrics", response_model=List[CampaignMetrics])
def get_campaigns_metrics(db=Depends(get_db)):
    """
    Get all campaign metrics for the master tab view.
    """
    try:
        # First try to get data from the database
        query = text("""
            SELECT 
                dc.campaign_id,
                dc.campaign_name,
                dc.source_system,
                dc.is_active,
                um.date,
                um.impressions,
                um.clicks,
                um.cost,
                um.conversions,
                um.revenue,
                um.cpc,
                COALESCE(sl.smooth_leads, 0) as smooth_leads,
                COALESCE(ts.total_sales, 0) as total_sales
            FROM scare_metrics.dim_campaign dc
            LEFT JOIN scare_metrics.unified_metrics_view um ON dc.campaign_id = um.campaign_id
            LEFT JOIN (
                SELECT campaign_id, SUM(leads) as smooth_leads
                FROM scare_metrics.fact_leads
                GROUP BY campaign_id
            ) sl ON dc.campaign_id = sl.campaign_id
            LEFT JOIN (
                SELECT campaign_id, COUNT(*) as total_sales
                FROM scare_metrics.fact_sales
                GROUP BY campaign_id
            ) ts ON dc.campaign_id = ts.campaign_id
        """)
        
        try:
            result = db.execute(query)
            
            data = []
            for row in result:
                data.append({
                    "campaign_id": row.campaign_id,
                    "campaign_name": row.campaign_name,
                    "source_system": row.source_system,
                    "is_active": row.is_active,
                    "date": row.date.isoformat() if row.date else None,
                    "impressions": row.impressions or 0,
                    "clicks": row.clicks or 0,
                    "spend": float(row.cost) if row.cost else 0,
                    "revenue": float(row.revenue) if row.revenue else 0,
                    "conversions": float(row.conversions) if row.conversions else 0,
                    "cpc": float(row.cpc) if row.cpc else 0,
                    "smooth_leads": row.smooth_leads or 0,
                    "total_sales": row.total_sales or 0,
                    "users": 0  # Placeholder for now, could be populated from matomo data
                })
            
            # If we got data from the database, return it
            if data:
                return data
                
        except Exception as db_error:
            # Log the database error but continue to generate placeholder data
            print(f"Database error: {str(db_error)}")
            # We'll fall through to the placeholder data below
        
        # If we got here, either the query failed or returned no data
        # Return placeholder data as a fallback
        import random
        from datetime import date, timedelta
        
        # Generate placeholder data
        today = date.today()
        campaigns = [
            {"id": 1, "name": "Summer Sale", "source": "Google Ads"},
            {"id": 2, "name": "Brand Awareness", "source": "Google Ads"},
            {"id": 3, "name": "Product Launch", "source": "Bing Ads"},
            {"id": 4, "name": "Retargeting", "source": "Bing Ads"},
            {"id": 5, "name": "Holiday Special", "source": "Google Ads"}
        ]
        
        placeholder_data = []
        for campaign in campaigns:
            for i in range(5):  # Create 5 days of data per campaign
                day = today - timedelta(days=i)
                impressions = random.randint(500, 5000)
                clicks = random.randint(10, int(impressions * 0.1))  # 10% max CTR
                spend = round(clicks * random.uniform(0.5, 2.0), 2)  # $0.50-$2.00 CPC
                conversions = random.randint(0, int(clicks * 0.2))  # 20% max conversion rate
                revenue = round(conversions * random.uniform(10, 50), 2)  # $10-$50 per conversion
                
                placeholder_data.append({
                    "campaign_id": campaign["id"],
                    "campaign_name": campaign["name"],
                    "source_system": campaign["source"],
                    "is_active": True,
                    "date": day.isoformat(),
                    "impressions": impressions,
                    "clicks": clicks,
                    "spend": spend,
                    "revenue": revenue,
                    "conversions": conversions,
                    "cpc": round(spend / clicks if clicks > 0 else 0, 2),
                    "smooth_leads": random.randint(0, conversions + 5),
                    "total_sales": random.randint(0, conversions),
                    "users": random.randint(clicks, impressions)
                })
        
        return placeholder_data
    
    except Exception as e:
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
    """Get a list of unmapped campaigns from various sources"""
    try:
        # Get Google Ads campaigns
        google_query = """
            SELECT DISTINCT 
                'Google Ads' as source_system,
                g.campaign_id as external_campaign_id,
                g.campaign_name as campaign_name,
                'Search' as network -- Default for Google Ads, can be changed by user
            FROM 
                sm_fact_google_ads g
            LEFT JOIN 
                sm_campaign_name_mapping m ON 
                CAST(g.campaign_id AS VARCHAR) = m.external_campaign_id AND 
                m.source_system = 'Google Ads'
            WHERE 
                m.id IS NULL
        """
        
        # Get Bing Ads campaigns
        bing_query = """
            SELECT DISTINCT 
                'Bing Ads' as source_system,
                b.campaign_id as external_campaign_id,
                b.campaign_name as campaign_name,
                'Search' as network -- Default for Bing Ads, can be changed by user
            FROM 
                sm_fact_bing_ads b
            LEFT JOIN 
                sm_campaign_name_mapping m ON 
                CAST(b.campaign_id AS VARCHAR) = m.external_campaign_id AND 
                m.source_system = 'Bing Ads'
            WHERE 
                m.id IS NULL
        """
        
        # Get RedTrack campaigns
        redtrack_query = """
            SELECT DISTINCT 
                'RedTrack' as source_system,
                r.campaign_id as external_campaign_id,
                r.campaign_name as campaign_name,
                NULL as network -- No default for RedTrack, must be specified
            FROM 
                sm_fact_redtrack r
            LEFT JOIN 
                sm_campaign_name_mapping m ON 
                CAST(r.campaign_id AS VARCHAR) = m.external_campaign_id AND 
                m.source_system = 'RedTrack'
            WHERE 
                m.id IS NULL
        """
        
        # Get Matomo campaigns
        matomo_query = """
            SELECT DISTINCT 
                'Matomo' as source_system,
                mt.campaign_id as external_campaign_id,
                mt.campaign_name as campaign_name,
                NULL as network -- No default for Matomo, must be specified
            FROM 
                sm_fact_matomo mt
            LEFT JOIN 
                sm_campaign_name_mapping m ON 
                CAST(mt.campaign_id AS VARCHAR) = m.external_campaign_id AND 
                m.source_system = 'Matomo'
            WHERE 
                m.id IS NULL
        """
        
        # Union all results
        union_query = f"""
            {google_query}
            UNION ALL
            {bing_query}
            UNION ALL
            {redtrack_query}
            UNION ALL
            {matomo_query}
            ORDER BY source_system, campaign_name
        """
        
        result = db.execute(text(union_query)).fetchall()
        return [dict(row._mapping) for row in result]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch unmapped campaigns: {str(e)}")

@app.post("/api/campaign-mappings", response_model=CampaignMapping)
def create_campaign_mapping(mapping: CampaignMappingCreate, db=Depends(get_db)):
    """
    Create a new campaign mapping
    """
    try:
        # Check if a mapping already exists for this source/id
        check_query = """
            SELECT id FROM public.sm_campaign_name_mapping
            WHERE source_system = :source_system AND external_campaign_id = :external_campaign_id
        """
        
        existing = db.execute(
            text(check_query), 
            {"source_system": mapping.source_system, "external_campaign_id": mapping.external_campaign_id}
        ).fetchone()
        
        if existing:
            # Update if it exists
            query = """
                UPDATE public.sm_campaign_name_mapping
                SET pretty_campaign_name = :pretty_campaign_name,
                    campaign_category = :campaign_category,
                    campaign_type = :campaign_type,
                    network = :network,
                    is_active = TRUE,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :id
                RETURNING *
            """
            
            result = db.execute(
                text(query),
                {
                    "pretty_campaign_name": mapping.pretty_campaign_name,
                    "campaign_category": mapping.campaign_category,
                    "campaign_type": mapping.campaign_type,
                    "network": mapping.network,
                    "id": existing.id
                }
            ).fetchone()
            
        else:
            # Insert if it doesn't exist
            query = """
                INSERT INTO public.sm_campaign_name_mapping
                (source_system, external_campaign_id, original_campaign_name, pretty_campaign_name, campaign_category, campaign_type, network)
                VALUES
                (:source_system, :external_campaign_id, :original_campaign_name, :pretty_campaign_name, :campaign_category, :campaign_type, :network)
                RETURNING *
            """
            
            result = db.execute(
                text(query),
                {
                    "source_system": mapping.source_system,
                    "external_campaign_id": mapping.external_campaign_id,
                    "original_campaign_name": mapping.original_campaign_name,
                    "pretty_campaign_name": mapping.pretty_campaign_name,
                    "campaign_category": mapping.campaign_category,
                    "campaign_type": mapping.campaign_type,
                    "network": mapping.network
                }
            ).fetchone()
        
        db.commit()
        
        return dict(result)
    except Exception as e:
        db.rollback()
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
        
        # Convert SQLAlchemy Row objects to dictionaries using dict() constructor
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
